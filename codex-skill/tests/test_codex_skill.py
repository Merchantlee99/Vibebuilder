from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "vibebuilder-codex-skill-router"
SKILL = PLUGIN / "skills" / "codex-skill-router"


class CodexSkillPackageTest(unittest.TestCase):
    def test_plugin_manifest_points_to_skills(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "vibebuilder-codex-skill-router")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertIn("routing", manifest["interface"]["capabilities"])

    def test_router_requires_explicit_invocation(self) -> None:
        metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('default_prompt: "Use $codex-skill-router', metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)

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
        self.assertNotIn("tdd-implementation", payload["suggested_skills"])

    def test_analysis_is_read_only_without_magic_words(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "classify_task.py"),
                "gpt 5.6에서 기존 Codex 스킬 조합이 의미가 있는지 분석해줘",
            ],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["routing_policy"], "native-first")
        self.assertTrue(payload["constraints"]["read_only"])
        self.assertIn("openai-docs", payload["suggested_skills"])
        self.assertIn("harness-doctor", payload["suggested_skills"])
        self.assertNotIn("tdd-implementation", payload["suggested_skills"])

    def test_small_edit_does_not_load_tdd_or_evidence_loop(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "classify_task.py"), "작은 오타 하나 고쳐줘"],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["suggested_skills"], [])

    def test_openai_current_work_selects_official_docs(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "classify_task.py"),
                "오늘 OpenAI 모델 릴리즈 노트 확인해줘",
            ],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["suggested_skills"], ["openai-docs"])

    def test_cli_product_requires_artifact_and_claim_evidence(self) -> None:
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
        self.assertIn("claim_to_evidence_matrix", payload["evidence_required"])
        self.assertEqual(payload["suggested_skills"], ["evidence-loop"])

    def test_read_only_release_assessment_keeps_release_gate_mode(self) -> None:
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
        self.assertTrue(payload["constraints"]["read_only"])
        self.assertEqual(payload["constraints"]["completion_mode"], "release_gate")
        self.assertIn("gate_checklist", payload["evidence_required"])
        self.assertIn("claim_to_evidence_matrix", payload["evidence_required"])

    def test_global_installer_creates_lean_gpt56_setup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            codex_home = temp / ".codex"
            agents_home = temp / ".agents"
            codex_home.mkdir()
            legacy_paths = [
                codex_home / "skills" / "codex-extreme-operator",
                codex_home / "skills" / "design-impact-router",
                agents_home / "skills" / "apex",
            ]
            for legacy_path in legacy_paths:
                legacy_path.mkdir(parents=True, exist_ok=True)
                (legacy_path / "SKILL.md").write_text("legacy skill\n", encoding="utf-8")
            (codex_home / "AGENTS.md").write_text(
                """<!-- LAZYWEB:ROUTER:BEGIN — managed by Lazyweb; delete this block to opt out -->
old lazyweb rule
<!-- LAZYWEB:ROUTER:END -->

<!-- CODEX-EXTREME-OPERATOR:BEGIN — managed personal routing block; delete to opt out -->
old extreme rule
<!-- CODEX-EXTREME-OPERATOR:END -->

Keep this unrelated personal note.
""",
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                'model = "gpt-5.6-sol"\n'
                'model_reasoning_effort = "xhigh"\n'
                'service_tier = "default"\n\n'
                'network_access = "enabled"\n\n'
                '[features]\n'
                'child_agents_md = true\n'
                'plugin_hooks = true\n'
                'codex_hooks = true\n\n'
                '[[skills.config]]\n'
                'path = "/tmp/keep-skill"\n'
                'enabled = true\n\n'
                '[plugins."documents@example"]\n'
                'enabled = true\n',
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "install_global.py"),
                    "--codex-home",
                    str(codex_home),
                    "--agents-home",
                    str(agents_home),
                ],
                cwd=SKILL,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["effort"], "high")
            self.assertEqual(set(report["archived_legacy_skills"]), {str(path.resolve()) for path in legacy_paths})
            self.assertEqual(
                set(report["removed_legacy_config_keys"]),
                {"network_access", "features.child_agents_md", "features.plugin_hooks", "features.codex_hooks"},
            )

            installed_skill = agents_home / "skills" / "codex-skill-router"
            self.assertTrue((installed_skill / "SKILL.md").is_file())
            self.assertFalse(any(installed_skill.rglob("*.pyc")))
            for legacy_path in legacy_paths:
                self.assertFalse(legacy_path.exists())
            backup_root = Path(report["backup"])
            self.assertTrue((backup_root / "legacy-skills" / "codex-extreme-operator" / "SKILL.md").is_file())
            self.assertTrue((backup_root / "legacy-skills" / "design-impact-router" / "SKILL.md").is_file())
            self.assertTrue((backup_root / "legacy-skills" / "apex" / "SKILL.md").is_file())

            agents_text = (codex_home / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("VIBEBUILDER:CODEX-5-6:BEGIN", agents_text)
            self.assertNotIn("LAZYWEB:ROUTER:BEGIN", agents_text)
            self.assertNotIn("CODEX-EXTREME-OPERATOR:BEGIN", agents_text)
            self.assertIn("Keep this unrelated personal note.", agents_text)

            config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
            self.assertIn('model_reasoning_effort = "high"', config_text)
            self.assertIn(str(codex_home / "skills" / "codex-extreme-operator"), config_text)
            self.assertIn(str(codex_home / "skills" / "design-impact-router"), config_text)
            self.assertIn(str(agents_home / "skills" / "apex"), config_text)
            self.assertIn(str(installed_skill), config_text)
            self.assertIn('/tmp/keep-skill', config_text)
            self.assertIn('[plugins."documents@example"]', config_text)
            self.assertIn('service_tier = "default"', config_text)
            self.assertIn('hooks = true', config_text)
            self.assertNotIn('network_access =', config_text)
            self.assertNotIn('child_agents_md =', config_text)
            self.assertNotIn('plugin_hooks =', config_text)
            self.assertNotIn('codex_hooks =', config_text)
            self.assertTrue((codex_home / "backups" / "vibebuilder-codex-5-6").is_dir())

            second = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "install_global.py"),
                    "--codex-home",
                    str(codex_home),
                    "--agents-home",
                    str(agents_home),
                ],
                cwd=SKILL,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            agents_text = (codex_home / "AGENTS.md").read_text(encoding="utf-8")
            config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
            self.assertEqual(agents_text.count("VIBEBUILDER:CODEX-5-6:BEGIN"), 1)
            self.assertEqual(config_text.count("[[skills.config]]"), 5)

    def test_global_installer_dry_run_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            codex_home = temp / ".codex"
            agents_home = temp / ".agents"
            codex_home.mkdir()
            agents_path = codex_home / "AGENTS.md"
            config_path = codex_home / "config.toml"
            agents_path.write_text("original agents\n", encoding="utf-8")
            config_path.write_text('model_reasoning_effort = "xhigh"\n', encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "install_global.py"),
                    "--codex-home",
                    str(codex_home),
                    "--agents-home",
                    str(agents_home),
                    "--dry-run",
                ],
                cwd=SKILL,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(agents_path.read_text(encoding="utf-8"), "original agents\n")
            self.assertEqual(config_path.read_text(encoding="utf-8"), 'model_reasoning_effort = "xhigh"\n')
            self.assertFalse((agents_home / "skills" / "codex-skill-router").exists())


if __name__ == "__main__":
    unittest.main()
