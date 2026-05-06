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
            ROOT / "harness/evidence/evidence.jsonl",
            ROOT / "harness/memory/proposed-learnings.jsonl",
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
        self.assertEqual(runtime.get("framework_version"), "v5")
        self.assertEqual(runtime.get("default_adoption_profile"), "implementation-first-evidence")
        self.assertTrue(runtime.get("review", {}).get("high_risk_requires_hmac_approval"))
        self.assertTrue(runtime.get("review", {}).get("prepared_event_required"))

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
        simplicity = self.run_cmd("scripts/harness/harness.py", "simplicity", "--template", "--json")
        self.assertEqual(simplicity.returncode, 0, simplicity.stdout + simplicity.stderr)
        design = self.run_cmd("scripts/harness/harness.py", "design", "--template", "--json")
        self.assertEqual(design.returncode, 0, design.stdout + design.stderr)
        profile = self.run_cmd("scripts/harness/harness.py", "task-profile", "--template", "--json")
        self.assertEqual(profile.returncode, 0, profile.stdout + profile.stderr)
        implementation = self.run_cmd("scripts/harness/harness.py", "implementation", "--template", "--json")
        self.assertEqual(implementation.returncode, 0, implementation.stdout + implementation.stderr)
        ui = self.run_cmd("scripts/harness/harness.py", "ui-evidence", "--template", "--json")
        self.assertEqual(ui.returncode, 0, ui.stdout + ui.stderr)
        strict = self.run_cmd("scripts/harness/harness.py", "strict", "--template", "--json")
        self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)

    def test_v5_task_profile_blocks_security_misclassification(self) -> None:
        profile = ROOT / "harness/context/test-task-profile.json"
        old = profile.read_text(encoding="utf-8") if profile.exists() else None
        try:
            profile.write_text(json.dumps({
                "kind": "security",
                "tier": "normal",
                "surface": "backend",
                "changed_paths": ["src/auth/session.ts"],
                "required_gates": ["implementation_gate"],
                "ui_evidence": "not-applicable",
                "strict_required": False,
                "not_applicable_reason": "backend-only security test",
                "residual_risk": "strict gate intentionally omitted for test",
            }), encoding="utf-8")
            proc = self.run_cmd("scripts/harness/task_profile_gate.py", "check", "--profile", str(profile.relative_to(ROOT)), "--json")
            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("security work must be high-risk", "\n".join(payload["errors"]))
        finally:
            if old is None:
                if profile.exists():
                    profile.unlink()
            else:
                profile.write_text(old, encoding="utf-8")

    def test_v5_high_risk_profile_requires_strict_gate(self) -> None:
        profile = ROOT / "harness/context/test-high-risk-profile.json"
        old = profile.read_text(encoding="utf-8") if profile.exists() else None
        try:
            profile.write_text(json.dumps({
                "kind": "feature",
                "tier": "high-risk",
                "surface": "backend",
                "changed_paths": ["src/payments/charge.ts"],
                "required_gates": ["implementation_gate"],
                "ui_evidence": "not-applicable",
                "strict_required": True,
                "not_applicable_reason": "backend-only payment test",
                "residual_risk": "strict gate intentionally omitted for test",
            }), encoding="utf-8")
            proc = self.run_cmd("scripts/harness/task_profile_gate.py", "check", "--profile", str(profile.relative_to(ROOT)), "--json")
            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("requires a strict gate", "\n".join(payload["errors"]))
        finally:
            if old is None:
                if profile.exists():
                    profile.unlink()
            else:
                profile.write_text(old, encoding="utf-8")

    def test_v5_main_gate_runs_implementation_evidence_gate(self) -> None:
        current = ROOT / "docs/ai/current"
        review_dir = ROOT / "harness/reviews"
        files = {
            current / "Plan.md": "# Plan\n\n## Goal\n\nTest normal gate.\n\n## Scope\n\nBackend only.\n\n## Validation\n\nRun command evidence.\n\n## Rollback\n\nRevert test change.\n",
            current / "Implement.md": "# Implement\n\n## Current Slice\n\nTest.\n\n## Files Changed\n\nsrc/server.ts\n\n## Commands Run\n\n| Command | Result | Notes |\n| --- | --- | --- |\n\n## Validation\n\nCommand should be recorded in evidence log.\n\n## Findings\n\nNone.\n\n## Deviations From Plan\n\nNone.\n\n## Next Step\n\nNone.\n",
            current / "Task-Profile.json": json.dumps({
                "kind": "bugfix",
                "tier": "normal",
                "surface": "backend",
                "changed_paths": ["src/server.ts"],
                "required_gates": ["implementation_gate"],
                "ui_evidence": "not-applicable",
                "strict_required": False,
                "not_applicable_reason": "backend-only gate wiring test",
                "residual_risk": "no runtime app exists in template test",
            }),
            review_dir / "review-v5-main-gate-test.md": "Reviewer: reviewer\nReviewer-Session: reviewer-session\nProducer: main-codex\nProducer-Session: main\nVerdict: accept\n\n## Scope Reviewed\n\nReviewed gate wiring fixture.\n\n## Validation Reviewed\n\nReviewed expected command/test evidence requirement.\n\n## Residual Risk\n\nTemplate fixture only.\n",
        }
        old_values = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in files}
        try:
            current.mkdir(parents=True, exist_ok=True)
            review_dir.mkdir(parents=True, exist_ok=True)
            for path, text in files.items():
                path.write_text(text, encoding="utf-8")
            proc = self.run_cmd("scripts/harness/gate.py", "all", "--tier", "normal", "--json")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("implementation_gate", proc.stdout + proc.stderr)
            self.assertIn("requires --task-id", proc.stdout + proc.stderr)
        finally:
            for path, old in old_values.items():
                if old is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(old, encoding="utf-8")

    def test_v5_ui_evidence_rejects_screenshot_only_normal_work(self) -> None:
        evidence = ROOT / "harness/evidence/evidence.jsonl"
        old = evidence.read_text(encoding="utf-8") if evidence.exists() else None
        artifact_dir = ROOT / "harness/evidence/artifacts/test-v5-ui"
        screenshot = artifact_dir / "settings-error.png"
        try:
            if evidence.exists():
                evidence.unlink()
            artifact_dir.mkdir(parents=True, exist_ok=True)
            screenshot.write_text("fake screenshot bytes", encoding="utf-8")
            visual = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-v5-ui",
                "--kind",
                "visual",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--route",
                "/settings",
                "--viewport",
                "390x844",
                "--state",
                "error",
                "--artifact",
                f"screenshot:{screenshot.relative_to(ROOT)}",
                "--summary",
                "Settings error state screenshot captured.",
            )
            self.assertEqual(visual.returncode, 0, visual.stdout + visual.stderr)
            blocked = self.run_cmd(
                "scripts/harness/ui_evidence_gate.py",
                "--task-id",
                "task-v5-ui",
                "--tier",
                "normal",
                "--required",
                "--json",
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("screenshot-only", blocked.stdout)

            layout = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-v5-ui",
                "--kind",
                "layout",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--route",
                "/settings",
                "--viewport",
                "390x844",
                "--state",
                "error",
                "--summary",
                "Layout map shows no horizontal overflow or clipped primary action.",
            )
            self.assertEqual(layout.returncode, 0, layout.stdout + layout.stderr)
            passed = self.run_cmd(
                "scripts/harness/ui_evidence_gate.py",
                "--task-id",
                "task-v5-ui",
                "--tier",
                "normal",
                "--required",
                "--json",
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        finally:
            if screenshot.exists():
                screenshot.unlink()
            if artifact_dir.exists():
                shutil.rmtree(artifact_dir)
            if old is None:
                if evidence.exists():
                    evidence.unlink()
            else:
                evidence.write_text(old, encoding="utf-8")

    def test_v5_sensitive_ui_requires_redaction_or_no_screenshot_reason(self) -> None:
        evidence = ROOT / "harness/evidence/evidence.jsonl"
        old = evidence.read_text(encoding="utf-8") if evidence.exists() else None
        artifact_dir = ROOT / "harness/evidence/artifacts/test-v5-sensitive"
        screenshot = artifact_dir / "billing.png"
        redacted = artifact_dir / "billing-redacted.png"
        try:
            if evidence.exists():
                evidence.unlink()
            artifact_dir.mkdir(parents=True, exist_ok=True)
            screenshot.write_text("sensitive screenshot", encoding="utf-8")
            redacted.write_text("redacted screenshot", encoding="utf-8")
            unredacted = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-sensitive-bad",
                "--kind",
                "visual",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--route",
                "/billing",
                "--viewport",
                "1440x900",
                "--state",
                "default",
                "--artifact",
                f"screenshot:{screenshot.relative_to(ROOT)}",
                "--summary",
                "Billing screenshot captured without redaction.",
            )
            self.assertEqual(unredacted.returncode, 0, unredacted.stdout + unredacted.stderr)
            bad_layout = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-sensitive-bad",
                "--kind",
                "layout",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--summary",
                "Layout evidence exists.",
            )
            self.assertEqual(bad_layout.returncode, 0, bad_layout.stdout + bad_layout.stderr)
            blocked = self.run_cmd(
                "scripts/harness/ui_evidence_gate.py",
                "--task-id",
                "task-sensitive-bad",
                "--tier",
                "normal",
                "--required",
                "--sensitive",
                "--json",
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("sensitive UI must be redacted", blocked.stdout)

            ok_visual = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-sensitive-ok",
                "--kind",
                "visual",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--route",
                "/billing",
                "--viewport",
                "1440x900",
                "--state",
                "default",
                "--artifact",
                f"screenshot:{redacted.relative_to(ROOT)}",
                "--redacted",
                "--summary",
                "Billing screenshot captured after redaction.",
            )
            self.assertEqual(ok_visual.returncode, 0, ok_visual.stdout + ok_visual.stderr)
            ok_layout = self.run_cmd(
                "scripts/harness/evidence_log.py",
                "append",
                "--task-id",
                "task-sensitive-ok",
                "--kind",
                "layout",
                "--tier",
                "normal",
                "--status",
                "pass",
                "--summary",
                "Layout evidence exists.",
            )
            self.assertEqual(ok_layout.returncode, 0, ok_layout.stdout + ok_layout.stderr)
            passed = self.run_cmd(
                "scripts/harness/ui_evidence_gate.py",
                "--task-id",
                "task-sensitive-ok",
                "--tier",
                "normal",
                "--required",
                "--sensitive",
                "--json",
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        finally:
            if artifact_dir.exists():
                shutil.rmtree(artifact_dir)
            if old is None:
                if evidence.exists():
                    evidence.unlink()
            else:
                evidence.write_text(old, encoding="utf-8")

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

    def test_high_risk_review_requires_hmac_by_default(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            "high-risk",
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
            text = text.replace("## Scope Reviewed\n", "## Scope Reviewed\n\nReviewed high-risk HMAC protected scope.\n", 1)
            text = text.replace("## Validation Reviewed\n", "## Validation Reviewed\n\nReviewed high-risk HMAC protected validation.\n", 1)
            text = text.replace("## Residual Risk\n", "## Residual Risk\n\nNo residual risk in high-risk HMAC review test.\n", 1)
            path.write_text(text, encoding="utf-8")

            missing = self.run_cmd("scripts/harness/review_gate.py", "finalize", "--review-file", review_path)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("HMAC", missing.stderr)

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
                "--approval-token",
                token,
                env={"HARNESS_REVIEW_SECRET": "secret"},
            )
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        finally:
            if path.exists():
                path.unlink()

    def test_harness_check_forwards_artifact_dir_and_review_file(self) -> None:
        artifact_dir = ROOT / "docs/ai/custom-check"
        review_file = ROOT / "harness/reviews/review-custom-check.md"
        files = {
            artifact_dir / "Plan.md": "# Plan\n\n## Goal\n\nCustom check.\n\n## Scope\n\nBackend only.\n\n## Validation\n\nRun command evidence.\n\n## Rollback\n\nRevert custom check.\n",
            artifact_dir / "Implement.md": "# Implement\n\n## Current Slice\n\nCustom check.\n\n## Files Changed\n\nsrc/custom.ts\n\n## Commands Run\n\n| Command | Result | Notes |\n| --- | --- | --- |\n\n## Validation\n\nCommand evidence should exist for the task.\n\n## Findings\n\nNone.\n\n## Deviations From Plan\n\nNone.\n\n## Next Step\n\nNone.\n",
            artifact_dir / "Task-Profile.json": json.dumps({
                "kind": "bugfix",
                "tier": "normal",
                "surface": "backend",
                "changed_paths": ["src/custom.ts"],
                "required_gates": ["implementation_gate"],
                "ui_evidence": "not-applicable",
                "strict_required": False,
                "not_applicable_reason": "backend-only wrapper forwarding test",
                "residual_risk": "no runtime app exists in template test",
            }),
            review_file: "Reviewer: reviewer\nReviewer-Session: reviewer-session\nProducer: main-codex\nProducer-Session: main\nTier: normal\nVerdict: accept\n\n## Scope Reviewed\n\nReviewed custom artifact directory.\n\n## Validation Reviewed\n\nReviewed expected command/test evidence requirement.\n\n## Residual Risk\n\nTemplate fixture only.\n",
        }
        old_values = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in files}
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            review_file.parent.mkdir(parents=True, exist_ok=True)
            for path, text in files.items():
                path.write_text(text, encoding="utf-8")
            proc = self.run_cmd(
                "scripts/harness/harness.py",
                "check",
                "--tier",
                "normal",
                "--artifact-dir",
                str(artifact_dir.relative_to(ROOT)),
                "--review-file",
                str(review_file.relative_to(ROOT)),
            )
            combined = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("implementation_gate", combined)
            self.assertNotIn("Missing plan artifact", combined)
            self.assertNotIn("Missing independent review artifact", combined)
        finally:
            for path, old in old_values.items():
                if old is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(old, encoding="utf-8")
            if artifact_dir.exists() and not any(artifact_dir.iterdir()):
                artifact_dir.rmdir()

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

    def test_v5_simplicity_gate_template_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/simplicity_gate.py", "--template", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_v5_simplicity_gate_missing_optional_is_warning(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/simplicity_gate.py",
            "--artifact-dir",
            "docs/ai/missing-simplicity-artifacts",
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["warnings"])

    def test_v5_design_gate_template_passes(self) -> None:
        proc = self.run_cmd("scripts/harness/design_gate.py", "--template", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_v5_design_gate_blocks_ui_scope_without_artifacts(self) -> None:
        proc = self.run_cmd(
            "scripts/harness/design_gate.py",
            "--ui",
            "--artifact-dir",
            "docs/ai/missing-ui-artifacts",
            "--json",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
