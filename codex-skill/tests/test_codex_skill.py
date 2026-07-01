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
        self.assertNotIn("tdd-implementation", payload["suggested_skills"])


if __name__ == "__main__":
    unittest.main()
