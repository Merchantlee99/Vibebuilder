from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "vibebuilder-codex-skill-router"
SKILL = PLUGIN / "skills" / "codex-skill-router"


class CodexSkillPackageTest(unittest.TestCase):
    def test_plugin_manifest_points_to_skills(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "vibebuilder-codex-skill-router")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertIn("routing", manifest["interface"]["capabilities"])

    def test_skill_has_no_todo_placeholders(self) -> None:
        paths = [
            ROOT / "README.md",
            PLUGIN / "README.md",
            SKILL / "SKILL.md",
            SKILL / "references" / "routing-contract.md",
            SKILL / "references" / "ouroboros-lite-gates.md",
            SKILL / "references" / "plugin-adoption.md",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("TODO", text, path)
            self.assertNotIn("[TODO", text, path)

    def test_skill_self_test_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "self_test.py")],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_read_only_route_suppresses_tdd(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "classify_task.py"),
                "수정하지 말고 현재 구조만 분석해줘",
            ],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["route"], "deep")
        self.assertTrue(payload["constraints"]["read_only"])
        self.assertEqual(payload["constraints"]["completion_mode"], "supporting_or_read_only")
        self.assertNotIn("tdd-implementation", payload["suggested_skills"])

    def test_cli_request_requires_product_evidence(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "classify_task.py"),
                "할 일 관리 CLI 만들어줘. 실행 예시까지 검증해줘",
            ],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["constraints"]["artifact_class"], "cli")
        self.assertEqual(payload["constraints"]["completion_mode"], "product_complete")
        self.assertIn("headless_cli_run_or_golden_output", payload["evidence_required"])
        self.assertIn("safe_but_wrong_artifact_class_check", payload["evidence_required"])

    def test_release_gate_overrides_read_only_completion_mode(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "classify_task.py"),
                "배포하지 말고 릴리즈 게이트만 검수해줘",
            ],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["route"], "release")
        self.assertEqual(payload["constraints"]["completion_mode"], "release_gate")
        self.assertIn("gate_checklist", payload["evidence_required"])
        self.assertIn("claim_to_evidence_matrix", payload["evidence_required"])


if __name__ == "__main__":
    unittest.main()
