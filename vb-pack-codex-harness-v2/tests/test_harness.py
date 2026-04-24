from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_config(path: Path) -> dict:
    data: dict = {}
    current: dict = data
    in_multiline = False
    multiline_key = ""
    buffer: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if in_multiline:
            if line.endswith('"""'):
                buffer.append(raw_line.rsplit('"""', 1)[0])
                current[multiline_key] = "\n".join(buffer)
                in_multiline = False
                multiline_key = ""
                buffer = []
            else:
                buffer.append(raw_line)
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            current = data
            for part in section.split("."):
                current = current.setdefault(part, {})
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if value == '"""':
            in_multiline = True
            multiline_key = key
            buffer = []
        elif value.startswith('"') and value.endswith('"'):
            current[key] = value.strip('"')
        elif value in {"true", "false"}:
            current[key] = value == "true"
        else:
            try:
                current[key] = int(value)
            except ValueError:
                current[key] = value
    return data


class HarnessStructureTest(unittest.TestCase):
    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_runtime_is_outside_codex(self) -> None:
        self.assertTrue((ROOT / "harness/runtime.json").exists())
        self.assertFalse((ROOT / ".codex/runtime.json").exists())

    def test_config_agent_limits(self) -> None:
        config = parse_config(ROOT / ".codex/config.toml")
        self.assertEqual(config["agents"]["max_depth"], 1)
        self.assertGreaterEqual(config["agents"]["max_threads"], 2)

    def test_custom_agents_are_read_only(self) -> None:
        agent_files = sorted((ROOT / ".codex/agents").glob("*.toml"))
        self.assertGreaterEqual(len(agent_files), 6)
        for path in agent_files:
            data = parse_config(path)
            self.assertIn("name", data)
            self.assertIn("description", data)
            self.assertIn("developer_instructions", data)
            self.assertEqual(data.get("sandbox_mode"), "read-only")

    def test_gate_trivial_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/gate.py", "all", "--tier", "trivial", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_gate_normal_template_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/gate.py", "all", "--tier", "normal", "--template", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_self_test_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/self_test.py")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_review_prepare_and_finalize_blocks_pending(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            "normal",
            "--producer",
            "test-producer",
            "--producer-session",
            "main",
            "--reviewer",
            "test-reviewer",
            "--reviewer-session",
            "reviewer-session",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        review_path = proc.stdout.strip()
        finalize = self.run_cmd("scripts/harness/review_gate.py", "finalize", "--review-file", review_path)
        self.assertNotEqual(finalize.returncode, 0)

        path = ROOT / review_path
        try:
            text = path.read_text(encoding="utf-8")
            text = text.replace("Verdict: pending", "Verdict: accept")
            text = text.replace("## Scope Reviewed\n", "## Scope Reviewed\n\nReviewed test scope.\n", 1)
            text = text.replace("## Validation Reviewed\n", "## Validation Reviewed\n\nReviewed test validation.\n", 1)
            text = text.replace("## Residual Risk\n", "## Residual Risk\n\nNo residual risk in test artifact.\n", 1)
            path.write_text(text, encoding="utf-8")
            finalize = self.run_cmd("scripts/harness/review_gate.py", "finalize", "--review-file", review_path)
            self.assertEqual(finalize.returncode, 0, finalize.stdout + finalize.stderr)
        finally:
            if path.exists():
                path.unlink()

    def test_subagent_claim_conflict_detection(self) -> None:
        claims = ROOT / "harness/context/ownership-claims.json"
        telemetry = ROOT / "harness/telemetry/subagent-events.jsonl"
        old = claims.read_text(encoding="utf-8") if claims.exists() else None
        old_telemetry = telemetry.read_text(encoding="utf-8") if telemetry.exists() else None
        try:
            if claims.exists():
                claims.unlink()
            first = self.run_cmd(
                "scripts/harness/subagent_planner.py",
                "plan",
                "--role",
                "worker",
                "--owner",
                "worker-a",
                "--goal",
                "first",
                "--write-scope",
                "src/auth",
                "--claim",
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_cmd(
                "scripts/harness/subagent_planner.py",
                "plan",
                "--role",
                "worker",
                "--owner",
                "worker-b",
                "--goal",
                "second",
                "--write-scope",
                "src/auth/session",
                "--claim",
            )
            self.assertNotEqual(second.returncode, 0)
            release = self.run_cmd("scripts/harness/subagent_planner.py", "release", "--owner", "worker-a")
            self.assertEqual(release.returncode, 0, release.stdout + release.stderr)
        finally:
            if old is None:
                if claims.exists():
                    claims.unlink()
            else:
                claims.write_text(old, encoding="utf-8")
            if old_telemetry is None:
                if telemetry.exists():
                    telemetry.unlink()
            else:
                telemetry.write_text(old_telemetry, encoding="utf-8")

    def test_automation_audit_and_skillify_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env["TMPDIR"] = str(tmp_path)
            auto = self.run_cmd("scripts/harness/automation_planner.py", "audit")
            self.assertEqual(auto.returncode, 0, auto.stdout + auto.stderr)
            skill = self.run_cmd("scripts/harness/skillify_audit.py", "all", "--json")
            self.assertEqual(skill.returncode, 0, skill.stdout + skill.stderr)
            payload = json.loads(skill.stdout)
            self.assertTrue(payload["ok"])

    def test_score_and_session_close_template(self) -> None:
        score = self.run_cmd("scripts/harness/score.py", "--min-score", "95", "--json")
        self.assertEqual(score.returncode, 0, score.stdout + score.stderr)
        payload = json.loads(score.stdout)
        self.assertGreaterEqual(payload["score"], 95)

        close = self.run_cmd("scripts/harness/session_close.py", "--tier", "high-risk", "--template", "--json")
        self.assertEqual(close.returncode, 0, close.stdout + close.stderr)

    def test_high_risk_subagent_requires_claim(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/subagent_planner.py",
            "plan",
            "--role",
            "worker",
            "--owner",
            "risky-worker",
            "--goal",
            "risky",
            "--tier",
            "high-risk",
            "--write-scope",
            "src/risk",
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_korean_risk_classifier(self) -> None:
        proc = self.run_cmd("scripts/harness/risk_classifier.py", "권한 결제 로직 수정", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["tier"], "high-risk")

    def test_quality_gate_template_and_index_metrics(self) -> None:
        quality = self.run_cmd("scripts/harness/quality_gate.py", "--tier", "high-risk", "--template", "--json")
        self.assertEqual(quality.returncode, 0, quality.stdout + quality.stderr)
        index = self.run_cmd("scripts/harness/session_index.py", "rebuild")
        self.assertEqual(index.returncode, 0, index.stdout + index.stderr)
        metrics = self.run_cmd("scripts/harness/ops_metrics.py", "--json")
        self.assertEqual(metrics.returncode, 0, metrics.stdout + metrics.stderr)
        payload = json.loads(metrics.stdout)
        self.assertIn("events_total", payload)

    def test_harness_entrypoint(self) -> None:
        proc = self.run_cmd("scripts/harness/harness.py", "classify", "권한", "결제", "수정")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "high-risk")


if __name__ == "__main__":
    unittest.main()
