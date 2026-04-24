from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "harness"))

from event_log import canonical_event  # noqa: E402


def parse_config(path: Path) -> dict:
    if tomllib is not None:
        with path.open("rb") as fh:
            return tomllib.load(fh)
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
    @classmethod
    def setUpClass(cls) -> None:
        for path in [
            ROOT / "harness/telemetry/events.jsonl",
            ROOT / "harness/telemetry/learnings.jsonl",
            ROOT / "harness/telemetry/events.lock",
            ROOT / "harness/telemetry/events.manifest.json",
            ROOT / "harness/context/ownership-claims.json",
            ROOT / "harness/context/automation-intents.json",
            ROOT / "harness/context/session-index.sqlite3",
            ROOT / "harness/context/session-index.sqlite3.tmp",
        ]:
            if path.exists():
                path.unlink()
        segments = ROOT / "harness/telemetry/segments"
        if segments.exists():
            shutil.rmtree(segments)
        for path in (ROOT / "harness/reviews").glob("review-*.md"):
            path.unlink()

    def run_cmd(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=proc_env,
        )

    def test_runtime_is_outside_codex(self) -> None:
        self.assertTrue((ROOT / "harness/runtime.json").exists())
        self.assertFalse((ROOT / ".codex/runtime.json").exists())
        runtime = json.loads((ROOT / "harness/runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(runtime["framework_version"], "v3")
        self.assertEqual(runtime["default_adoption_profile"], "strict")

    def test_config_agent_limits(self) -> None:
        config = parse_config(ROOT / ".codex/config.toml")
        self.assertEqual(config["agents"]["max_depth"], 1)
        self.assertGreaterEqual(config["agents"]["max_threads"], 2)
        self.assertTrue(config["features"]["codex_hooks"])

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

    def test_risk_classifier_avoids_auth_substring_false_positive(self) -> None:
        proc = self.run_cmd("scripts/harness/risk_classifier.py", "authority figure updates", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertNotEqual(payload["tier"], "high-risk")

    def test_risk_manifest_audit(self) -> None:
        proc = self.run_cmd("scripts/harness/risk_classifier.py", "--audit-manifest", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

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
        verify = self.run_cmd("scripts/harness/harness.py", "events", "verify")
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        quality = self.run_cmd("scripts/harness/harness.py", "quality", "--tier", "high-risk", "--template", "--json")
        self.assertEqual(quality.returncode, 0, quality.stdout + quality.stderr)
        strict = self.run_cmd("scripts/harness/harness.py", "strict", "--template", "--json")
        self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)

    def test_learning_detector_canonicalizes_error_order(self) -> None:
        events = ROOT / "harness/telemetry/events.jsonl"
        manifest = ROOT / "harness/telemetry/events.manifest.json"
        old = events.read_text(encoding="utf-8") if events.exists() else None
        old_manifest = manifest.read_text(encoding="utf-8") if manifest.exists() else None
        try:
            if events.exists():
                events.unlink()
            if manifest.exists():
                manifest.unlink()
            self.run_cmd(
                "scripts/harness/event_log.py",
                "event",
                "--kind",
                "quality.gate",
                "--status",
                "blocked",
                "--data-json",
                '{"errors":["B failed","A failed"]}',
            )
            self.run_cmd(
                "scripts/harness/event_log.py",
                "event",
                "--kind",
                "quality.gate",
                "--status",
                "blocked",
                "--data-json",
                '{"errors":["A failed","B failed"]}',
            )
            detect = self.run_cmd("scripts/harness/learning_detector.py", "--threshold", "2", "--json")
            self.assertEqual(detect.returncode, 0, detect.stdout + detect.stderr)
            payload = json.loads(detect.stdout)
            self.assertEqual(len(payload["findings"]), 1)
        finally:
            if old is None:
                if events.exists():
                    events.unlink()
            else:
                events.write_text(old, encoding="utf-8")
            if old_manifest is None:
                if manifest.exists():
                    manifest.unlink()
            else:
                manifest.write_text(old_manifest, encoding="utf-8")

    def test_automation_scan_ignores_accepted_review(self) -> None:
        review_dir = ROOT / "harness/reviews"
        events = ROOT / "harness/telemetry/events.jsonl"
        old_events = events.read_text(encoding="utf-8") if events.exists() else None
        review_dir.mkdir(parents=True, exist_ok=True)
        review = review_dir / "review-test-accepted.md"
        try:
            if events.exists():
                events.unlink()
            review.write_text("Verdict: accept\n", encoding="utf-8")
            scan = self.run_cmd("scripts/harness/automation_planner.py", "scan")
            self.assertEqual(scan.returncode, 0, scan.stdout + scan.stderr)
            self.assertNotIn("pending-review", scan.stdout)
        finally:
            if review.exists():
                review.unlink()
            if old_events is None:
                if events.exists():
                    events.unlink()
            else:
                events.write_text(old_events, encoding="utf-8")

    def test_event_log_hash_chain_detects_tamper(self) -> None:
        events = ROOT / "harness/telemetry/events.jsonl"
        manifest = ROOT / "harness/telemetry/events.manifest.json"
        old = events.read_text(encoding="utf-8") if events.exists() else None
        old_manifest = manifest.read_text(encoding="utf-8") if manifest.exists() else None
        try:
            if events.exists():
                events.unlink()
            if manifest.exists():
                manifest.unlink()
            self.run_cmd("scripts/harness/event_log.py", "event", "--kind", "test.event")
            verify = self.run_cmd("scripts/harness/event_log.py", "verify")
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            text = events.read_text(encoding="utf-8").replace("test.event", "test.tampered")
            events.write_text(text, encoding="utf-8")
            verify = self.run_cmd("scripts/harness/event_log.py", "verify")
            self.assertNotEqual(verify.returncode, 0)
        finally:
            if old is None:
                if events.exists():
                    events.unlink()
            else:
                events.write_text(old, encoding="utf-8")
            if old_manifest is None:
                if manifest.exists():
                    manifest.unlink()
            else:
                manifest.write_text(old_manifest, encoding="utf-8")

    def test_event_log_canonicalizes_unicode_nfc(self) -> None:
        base = {
            "id": "event-1",
            "ts": "20260101T000000Z",
            "kind": "unicode.test",
            "actor": "test",
            "status": "ok",
            "data": {"value": "cafe\u0301"},
            "prev_hash": "",
        }
        equivalent = {**base, "data": {"value": "café"}}
        self.assertEqual(canonical_event(base), canonical_event(equivalent))

    def test_event_log_rotation_preserves_and_verifies_segment_chain(self) -> None:
        events = ROOT / "harness/telemetry/events.jsonl"
        manifest = ROOT / "harness/telemetry/events.manifest.json"
        segments = ROOT / "harness/telemetry/segments"
        for path in [events, manifest]:
            if path.exists():
                path.unlink()
        if segments.exists():
            shutil.rmtree(segments)
        try:
            first = self.run_cmd("scripts/harness/event_log.py", "event", "--kind", "rotate.first")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            rotated = self.run_cmd("scripts/harness/event_log.py", "rotate", "--force")
            self.assertEqual(rotated.returncode, 0, rotated.stdout + rotated.stderr)
            second = self.run_cmd("scripts/harness/event_log.py", "event", "--kind", "rotate.second")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            verify = self.run_cmd("scripts/harness/event_log.py", "verify")
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            segment_files = sorted(segments.glob("*.jsonl"))
            self.assertEqual(len(segment_files), 1)
            text = segment_files[0].read_text(encoding="utf-8").replace("rotate.first", "rotate.tampered")
            segment_files[0].write_text(text, encoding="utf-8")
            verify = self.run_cmd("scripts/harness/event_log.py", "verify")
            self.assertNotEqual(verify.returncode, 0)
        finally:
            for path in [events, manifest]:
                if path.exists():
                    path.unlink()
            if segments.exists():
                shutil.rmtree(segments)

    def test_review_finalize_can_require_hmac_approval(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            "normal",
            "--producer",
            "hmac-producer",
            "--producer-session",
            "main",
            "--reviewer",
            "hmac-reviewer",
            "--reviewer-session",
            "reviewer-session",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        review_path = proc.stdout.strip()
        path = ROOT / review_path
        try:
            text = path.read_text(encoding="utf-8")
            nonce = text.split("Review-Nonce: `", 1)[1].split("`", 1)[0]
            text = text.replace("Verdict: pending", "Verdict: accept")
            text = text.replace("## Scope Reviewed\n", "## Scope Reviewed\n\nReviewed HMAC protected scope.\n", 1)
            text = text.replace("## Validation Reviewed\n", "## Validation Reviewed\n\nReviewed HMAC protected validation.\n", 1)
            text = text.replace("## Residual Risk\n", "## Residual Risk\n\nNo residual risk in HMAC review test.\n", 1)
            path.write_text(text, encoding="utf-8")
            bad = self.run_cmd(
                "scripts/harness/review_gate.py",
                "finalize",
                "--review-file",
                review_path,
                "--hmac-secret-env",
                "HARNESS_REVIEW_SECRET",
                env={"HARNESS_REVIEW_SECRET": "secret"},
            )
            self.assertNotEqual(bad.returncode, 0)
            token = hmac.new(
                b"secret",
                f"{review_path}:{nonce}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            ok = self.run_cmd(
                "scripts/harness/review_gate.py",
                "finalize",
                "--review-file",
                review_path,
                "--hmac-secret-env",
                "HARNESS_REVIEW_SECRET",
                "--approval-token",
                token,
                env={"HARNESS_REVIEW_SECRET": "secret"},
            )
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        finally:
            if path.exists():
                path.unlink()

    def test_subagent_plan_records_planned_model(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/subagent_planner.py",
            "plan",
            "--role",
            "reviewer",
            "--owner",
            "model-reviewer",
            "--goal",
            "model policy check",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("planned_model: gpt-5.5", proc.stdout)

    def test_strict_gate_template_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/strict_gate.py", "--template", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["profile"], "strict")

    def test_enforced_high_risk_review_requires_hmac(self) -> None:
        runtime = ROOT / "harness/runtime.json"
        old_runtime = runtime.read_text(encoding="utf-8")
        proc = self.run_cmd(
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            "high-risk",
            "--producer",
            "strict-producer",
            "--producer-session",
            "main",
            "--reviewer",
            "strict-reviewer",
            "--reviewer-session",
            "reviewer-session",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        review_path = proc.stdout.strip()
        path = ROOT / review_path
        try:
            data = json.loads(old_runtime)
            data["enforcement_mode"] = "enforced"
            data["review"]["high_risk_requires_hmac_approval"] = True
            runtime.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

            text = path.read_text(encoding="utf-8")
            text = text.replace("Verdict: pending", "Verdict: accept")
            text = text.replace("## Scope Reviewed\n", "## Scope Reviewed\n\nReviewed strict high-risk scope.\n", 1)
            text = text.replace("## Validation Reviewed\n", "## Validation Reviewed\n\nReviewed strict high-risk validation.\n", 1)
            text = text.replace("## Residual Risk\n", "## Residual Risk\n\nResidual identity risk requires HMAC.\n", 1)
            path.write_text(text, encoding="utf-8")

            finalize = self.run_cmd("scripts/harness/review_gate.py", "finalize", "--review-file", review_path)
            self.assertNotEqual(finalize.returncode, 0)
            self.assertIn("HMAC review approval is required", finalize.stderr)
        finally:
            runtime.write_text(old_runtime, encoding="utf-8")
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
