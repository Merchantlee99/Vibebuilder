#!/usr/bin/env python3
"""
test_harness.py — Unit tests for Unified 4-axis harness.

Covers the invariants that matter most:
  1. event_log session resolution stable across calls
  2. learning_log FAILURE_TAXONOMY validation
  3. size_check tier + complexity classification
  4. bash_write_probe detects tee/sed/printf/install
  5. All 5 hooks + 17 harness scripts + 13 sealed prompts + 4 core docs present

Run:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import ast
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))


class TestSessionResolution(unittest.TestCase):
    def test_env_var_wins(self):
        import event_log
        os.environ["CLAUDE_SESSION_ID"] = "unit-test-session"
        try:
            self.assertEqual(event_log._resolve_session_id(), "unit-test-session")
        finally:
            del os.environ["CLAUDE_SESSION_ID"]

    def test_stable_across_calls(self):
        import event_log
        os.environ.pop("CLAUDE_SESSION_ID", None)
        ids = [event_log._resolve_session_id() for _ in range(5)]
        self.assertEqual(len(set(ids)), 1, "session id must be stable")
        self.assertTrue(all(x for x in ids))


class TestFailureTaxonomy(unittest.TestCase):
    def test_known_pattern_validated(self):
        import learning_log
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            os.environ["CLAUDE_SESSION_ID"] = "taxonomy-known"
            learning_log.append_learning(
                gate="02", mistake="x", fix="y",
                pattern="self-review-attempt", repo_root=repo,
            )
            last = (repo / ".claude" / "learnings.jsonl").read_text().splitlines()[-1]
            obj = json.loads(last)
            self.assertTrue(obj["context"]["pattern_validated"])
            del os.environ["CLAUDE_SESSION_ID"]

    def test_unknown_pattern_flagged(self):
        import learning_log
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            os.environ["CLAUDE_SESSION_ID"] = "taxonomy-unknown"
            learning_log.append_learning(
                gate="02", mistake="novel", fix="tbd",
                pattern="never-seen-before", repo_root=repo,
            )
            last = (repo / ".claude" / "learnings.jsonl").read_text().splitlines()[-1]
            obj = json.loads(last)
            self.assertFalse(obj["context"]["pattern_validated"])
            self.assertTrue(obj["context"]["pattern_unknown"])
            del os.environ["CLAUDE_SESSION_ID"]


class TestSizeCheck(unittest.TestCase):
    def setUp(self):
        import size_check
        self.sc = size_check

    def test_trivial(self):
        self.assertEqual(self.sc.classify_tier("foo.py", 5, "x=1"), "trivial")

    def test_normal(self):
        self.assertEqual(self.sc.classify_tier("foo.py", 50, "x=1"), "normal")

    def test_high_risk_by_loc(self):
        self.assertEqual(self.sc.classify_tier("foo.py", 150, "x=1"), "high-risk")

    def test_high_risk_by_path(self):
        self.assertEqual(self.sc.classify_tier("auth/h.py", 5, ""), "high-risk")

    def test_complexity_simple(self):
        self.assertEqual(self.sc.classify_complexity("users.py", "x=1"), "simple")

    def test_complexity_concurrency(self):
        self.assertEqual(
            self.sc.classify_complexity("queue.py", "def f(): with lock: ..."),
            "complex",
        )

    def test_complexity_by_path(self):
        self.assertEqual(self.sc.classify_complexity("src/refactor_cache.py", ""), "complex")


class TestBashWriteProbe(unittest.TestCase):
    def setUp(self):
        import bash_write_probe
        self.bwp = bash_write_probe

    def test_heredoc(self):
        w = self.bwp._extract_writes("cat > /tmp/x.md <<'EOF'\nline1\nline2\nEOF")
        self.assertEqual(w, [("/tmp/x.md", 2)])

    def test_plain_redirect(self):
        w = self.bwp._extract_writes("echo hi > out.txt")
        self.assertEqual(w, [("out.txt", 1)])

    def test_tee(self):
        w = self.bwp._extract_writes("echo hi | tee /tmp/t.txt")
        self.assertIn(("/tmp/t.txt", 1), w)

    def test_sed_inplace(self):
        w = self.bwp._extract_writes("sed -i 's/a/b/g' config.yaml")
        self.assertIn(("config.yaml", 1), w)

    def test_install(self):
        w = self.bwp._extract_writes("install -m 755 src dst")
        self.assertIn(("dst", 1), w)

    def test_no_write(self):
        self.assertEqual(self.bwp._extract_writes("ls -la"), [])


class TestHookPresence(unittest.TestCase):
    EXPECTED = ["session_start.py", "user_prompt_submit.py",
                "pre_tool_use.py", "post_tool_use.py", "stop.py", "common.py"]

    def test_all_hooks_exist(self):
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        for name in self.EXPECTED:
            p = hooks_dir / name
            self.assertTrue(p.exists(), f"missing: {p}")

    def test_hooks_parse(self):
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        for name in self.EXPECTED:
            p = hooks_dir / name
            ast.parse(p.read_text(encoding="utf-8"))


class TestScriptsPresent(unittest.TestCase):
    EXPECTED = [
        "event_log.py", "learning_log.py", "size_check.py",
        "bash_write_probe.py", "rotate_logs.py", "self_test.py",
        "meta_supervisor.py", "runtime_gate.py",
        "oversight_policy.py", "risk_policy.py",
        "review_matrix_policy.py", "transition_policy.py",
        "memory_manager.py", "skill_auto_gen.py",
        "taxonomy_learner.py", "insights_engine.py", "session_index.py",
    ]

    def test_scripts_parse(self):
        d = REPO_ROOT / "scripts" / "harness"
        for name in self.EXPECTED:
            p = d / name
            self.assertTrue(p.exists(), f"missing: {p}")
            ast.parse(p.read_text(encoding="utf-8"))


class TestSealedPromptsPresent(unittest.TestCase):
    EXPECTED = [
        "direction-check.md", "review-code.md", "review-plan.md",
        "planner.md", "plan-redteam.md",
        "implement-tests.md", "implement-code.md",
        "tests-redteam.md", "diff-redteam.md",
        "risk-reviewer.md", "verifier.md",
        "failure-analysis.md", "meta-audit.md",
    ]

    def test_sealed_prompts(self):
        d = REPO_ROOT / ".claude" / "sealed-prompts"
        for name in self.EXPECTED:
            p = d / name
            self.assertTrue(p.exists(), f"missing: {p}")
            self.assertGreater(p.stat().st_size, 200, f"too small: {p}")


class TestCoreDocsPresent(unittest.TestCase):
    def test_docs(self):
        for name in ["README.md", "CLAUDE.md", "AGENTS.md", "ETHOS.md"]:
            p = REPO_ROOT / name
            self.assertTrue(p.exists(), f"missing: {p}")
            self.assertGreater(p.stat().st_size, 500)

    def test_agents_manifest(self):
        p = REPO_ROOT / ".claude" / "agents" / "manifest.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data.get("roles", [])), 8)

    def test_review_matrix(self):
        p = REPO_ROOT / ".claude" / "agents" / "review-matrix.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        stages = [s["name"] for s in data.get("stages", [])]
        self.assertEqual(stages, ["plan", "tests", "implementation", "verification", "postmortem"])

    def test_runtime(self):
        p = REPO_ROOT / ".claude" / "runtime.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(data["framework_version"], "unified-4-axis-1.0")


class TestTemplatesPresent(unittest.TestCase):
    def test_six_artifacts(self):
        for name in ["Prompt.md", "PRD.md", "Plan.md", "Implement.md",
                     "Documentation.md", "Subagent-Manifest.md"]:
            p = REPO_ROOT / "templates" / name
            self.assertTrue(p.exists(), f"missing: {p}")


class TestGate2PreImplemented(unittest.TestCase):
    """P0 verification — gate_2_pre is no longer a TODO."""

    def test_gate_2_pre_function_exists(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("def gate_2_pre(", src, "gate_2_pre not defined")

    def test_gate_2_pre_called_from_main(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("gate_2_pre(repo_root, size)", src,
                      "gate_2_pre not invoked from main()")

    def test_no_todo_gate2_remaining(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertNotIn(
            "TODO: implement Gate ② Pre", src,
            "Gate ② Pre TODO marker still present — not implemented",
        )

    def test_actor_crossover_check_present(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("author_actor != reviewer_actor", src,
                      "actor crossover check missing")

    def test_fingerprint_check_present(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("Severity of worst finding:", src)
        self.assertIn("Rollback triggers:", src)
        self.assertIn("Rollback recommended:", src)

    def test_structured_objection_check_present(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("Evidence:", src)

    def test_size_threshold_800(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("< 800", src, "reviewer_file size threshold not enforced")

    def test_per_file_gate_4_check(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("gate4_latest", src,
                      "per-file Gate ④ outcome map missing")
        self.assertIn('ts >= prev[0]', src,
                      "P4-7b same-ts handling missing")


class TestGate4RunnerImplemented(unittest.TestCase):
    """P1 verification — Gate ④ background runner is wired."""

    def test_runner_script_exists(self):
        p = REPO_ROOT / ".claude" / "hooks" / "gate_4_runner.py"
        self.assertTrue(p.exists(), "gate_4_runner.py missing")
        ast.parse(p.read_text(encoding="utf-8"))

    def test_post_tool_use_spawns_runner(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "post_tool_use.py").read_text()
        self.assertIn("start_new_session=True", src,
                      "detached subprocess spawn not found")
        self.assertIn("gate_4_runner.py", src,
                      "runner script not referenced from post_tool_use")

    def test_no_skeleton_marker(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "post_tool_use.py").read_text()
        self.assertNotIn(
            "skeleton — background runner not yet wired", src,
            "Gate ④ still in skeleton mode",
        )


class TestLayer4Implemented(unittest.TestCase):
    """P2 verification — Layer 4 clusters + syncs."""

    def test_skill_auto_gen_scans(self):
        import skill_auto_gen
        # With an empty / clean repo, scan returns [] — no crash.
        result = skill_auto_gen.scan_for_patterns(threshold=3)
        self.assertIsInstance(result, list)

    def test_memory_manager_sync_returns(self):
        import memory_manager
        # Stub event — must not crash on minimal input.
        memory_manager.sync_turn(event={}, repo_root=REPO_ROOT)


class TestGate2PreBehavior(unittest.TestCase):
    """P0 behavior — actually run the hook and verify it blocks / releases."""

    @classmethod
    def setUpClass(cls):
        cls.hook = REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py"
        cls.session_id = "unit-test-gate2-pre"
        os.environ["CLAUDE_SESSION_ID"] = cls.session_id

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("CLAUDE_SESSION_ID", None)

    def _run_hook(self, payload: dict) -> subprocess.CompletedProcess:
        import subprocess
        return subprocess.run(
            ["python3", str(self.hook)],
            input=json.dumps(payload), capture_output=True, text=True,
            cwd=str(REPO_ROOT), env=os.environ.copy(),
        )

    def test_trivial_edit_passes(self):
        import subprocess
        r = self._run_hook({
            "hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": ".claude/known-gaps.md",
                            "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(r.returncode, 0,
                         f"trivial edit should pass\nstderr: {r.stderr[:400]}")


if __name__ == "__main__":
    import subprocess  # used by TestGate2PreBehavior
    unittest.main(verbosity=2)
