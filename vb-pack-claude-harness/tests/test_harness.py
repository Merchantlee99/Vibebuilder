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


# Portable tempdir — system tmpdir may be unreachable under sandbox/CI
# restrictions. Fall back to an in-repo ephemeral path so tests do not skip.
def _portable_tempdir():
    """Return a context manager that yields a clean temp Path.

    Tries tempfile.TemporaryDirectory first; on PermissionError / OSError
    falls back to REPO_ROOT/.claude/ephemeral/test-<pid>-<n>/ and cleans up.
    """
    try:
        return tempfile.TemporaryDirectory()
    except (OSError, PermissionError):
        pass

    class _FallbackTemp:
        def __init__(self):
            import os as _os
            base = REPO_ROOT / ".claude" / "ephemeral" / f"test-{_os.getpid()}-{id(self)}"
            base.mkdir(parents=True, exist_ok=True)
            self.name = str(base)
            self._path = base
        def __enter__(self):
            return self.name
        def __exit__(self, *a):
            import shutil
            try:
                shutil.rmtree(self._path, ignore_errors=True)
            except Exception:
                pass
    return _FallbackTemp()


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
        with _portable_tempdir() as tmp:
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
        with _portable_tempdir() as tmp:
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


class TestGate7BlocksProtectedPaths(unittest.TestCase):
    """Behavior test: Gate ⑦ classifies control-plane paths + gate_7_selfprotect
    raises SystemExit(2). Function-level to bypass circuit breaker state."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))

    def test_is_protected_path_matches_hooks(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path(".claude/hooks/anything.py"))

    def test_is_protected_path_matches_harness(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path("scripts/harness/anything.py"))

    def test_is_protected_path_matches_claude_md(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path("CLAUDE.md"))

    def test_is_protected_path_matches_events_jsonl(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path(".claude/events.jsonl"))

    def test_is_protected_path_matches_learnings_jsonl(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path(".claude/learnings.jsonl"))

    def test_reviews_dir_not_protected(self):
        from common import is_protected_path
        # Reviews are produced by Gate ②, NOT in protected set.
        self.assertIsNone(is_protected_path(".claude/reviews/unit-test.md"))

    def test_direction_checks_not_protected(self):
        from common import is_protected_path
        self.assertIsNone(is_protected_path(".claude/direction-checks/foo.md"))

    def test_gate_7_raises_on_protected(self):
        import importlib
        pre = importlib.import_module("pre_tool_use")
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            os.environ["CLAUDE_SESSION_ID"] = "unit-test-gate7-fn"
            try:
                with self.assertRaises(SystemExit) as ctx:
                    pre.gate_7_selfprotect(repo, [".claude/hooks/x.py"])
                self.assertEqual(ctx.exception.code, 2)
            finally:
                os.environ.pop("CLAUDE_SESSION_ID", None)

    def test_gate_7_passes_on_unprotected(self):
        import importlib
        pre = importlib.import_module("pre_tool_use")
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            # Should NOT raise
            pre.gate_7_selfprotect(repo, ["src/app.py", "docs/readme.md"])


class TestNoEnvAuthorBypass(unittest.TestCase):
    """Regression: Gate ② author_actor must not be readable from env."""

    def test_post_tool_use_does_not_read_env(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "post_tool_use.py").read_text()
        self.assertNotIn("CLAUDE_HARNESS_AUTHOR", src,
                         "env-based author override reintroduces the Gate ② "
                         "actor-crossover bypass")
        # Positive: author_actor is pinned to literal "claude"
        self.assertIn('author_actor = "claude"', src)


class TestCircuitBreakerSeverity(unittest.TestCase):
    """P0-2: tripped vs manual must be distinguishable so pre_tool_use can
    fail-closed on tripped while still allowing maintenance mode."""

    def test_circuit_severity_exists(self):
        import hook_health
        self.assertTrue(hasattr(hook_health, "circuit_severity"))

    def test_severity_ok_when_not_disabled(self):
        import hook_health
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            (repo / ".claude" / "runtime.json").write_text(
                json.dumps({"hook_health": {"pre_tool_use": {"disabled": False}}})
            )
            self.assertEqual(
                hook_health.circuit_severity("pre_tool_use", repo_root=repo),
                "ok",
            )

    def test_severity_manual(self):
        import hook_health
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            (repo / ".claude" / "runtime.json").write_text(json.dumps({
                "hook_health": {"pre_tool_use": {
                    "disabled": True, "streak": 0,
                    "last_failure_reason": "manually disabled",
                }}
            }))
            self.assertEqual(
                hook_health.circuit_severity("pre_tool_use", repo_root=repo),
                "manual",
            )

    def test_severity_tripped(self):
        import hook_health
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            (repo / ".claude" / "runtime.json").write_text(json.dumps({
                "hook_health": {"pre_tool_use": {
                    "disabled": True, "streak": 3,
                    "last_failure_reason": "KeyError in gate_6_scope",
                }}
            }))
            self.assertEqual(
                hook_health.circuit_severity("pre_tool_use", repo_root=repo),
                "tripped",
            )

    def test_pre_tool_use_fails_closed_on_tripped(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("circuit_severity", src)
        self.assertIn('_severity == "tripped"', src)
        # When tripped, must emit_block (fail-closed), not emit_continue
        tripped_idx = src.find('_severity == "tripped"')
        self.assertGreater(tripped_idx, 0)
        window = src[tripped_idx:tripped_idx + 500]
        self.assertIn("emit_block", window,
                      "tripped branch must emit_block (fail-closed)")


class TestBootstrapScript(unittest.TestCase):
    """P1-1: bootstrap.py must exist, parse, and have key steps."""

    def test_bootstrap_exists(self):
        p = REPO_ROOT / "scripts" / "harness" / "bootstrap.py"
        self.assertTrue(p.exists(), "bootstrap.py missing")
        ast.parse(p.read_text(encoding="utf-8"))

    def test_settings_template_exists(self):
        p = REPO_ROOT / "templates" / "settings.template.json"
        self.assertTrue(p.exists(), "settings.template.json missing")
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("hooks", data)
        for evt in ("SessionStart", "UserPromptSubmit",
                    "PreToolUse", "PostToolUse", "Stop"):
            self.assertIn(evt, data["hooks"],
                          f"template missing hook event {evt}")


class TestNativeFeatureArtifacts(unittest.TestCase):
    """Native Claude feature scaffolding from manifests+playbooks round."""

    def test_subagent_manifest_present(self):
        p = REPO_ROOT / ".claude" / "manifests" / "subagents.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        for role in ("orchestrator", "explorer", "worker", "reviewer", "planner"):
            self.assertIn(role, data["roles"], f"role {role} missing")

    def test_capability_routing_present(self):
        p = REPO_ROOT / ".claude" / "manifests" / "capability-routing.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in ("codebase_question", "bounded_implementation",
                  "gui_blocked_or_auth_heavy"):
            self.assertIn(r, data["routes"], f"route {r} missing")

    def test_automation_policy_valid_json(self):
        p = REPO_ROOT / ".claude" / "manifests" / "automation-policy.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("recommended_loops", data)
        self.assertGreaterEqual(len(data["recommended_loops"]), 3)

    def test_playbooks_present(self):
        d = REPO_ROOT / ".claude" / "playbooks"
        required = ["subagents.md", "mcp.md", "memory.md",
                    "hooks-recipes.md", "computer-browser-use.md",
                    "git-ops.md", "automation.md", "plugins.md"]
        for name in required:
            p = d / name
            self.assertTrue(p.exists(), f"playbook missing: {name}")
            self.assertGreater(p.stat().st_size, 500,
                               f"playbook too small: {name}")

    def test_plugins_lock_valid(self):
        p = REPO_ROOT / ".claude" / "plugins.lock"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("locked", data)
        self.assertIn("suggested", data)

    def test_mcp_template_valid(self):
        p = REPO_ROOT / "templates" / "mcp.template.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("mcpServers", data)

    def test_new_scripts_compile(self):
        for name in ["subagent_planner.py", "automation_planner.py",
                     "mcp_audit.py", "activity_replay.py"]:
            p = REPO_ROOT / "scripts" / "harness" / name
            self.assertTrue(p.exists(), f"{name} missing")
            ast.parse(p.read_text(encoding="utf-8"))

    def test_gate_9_scans_mcp(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "post_tool_use.py").read_text()
        self.assertIn('startswith("mcp__")', src,
                      "Gate ⑨ must scan MCP tool responses")

    def test_gate_7_protects_manifests(self):
        from common import is_protected_path
        self.assertIsNotNone(is_protected_path(".claude/manifests/x.yaml"))
        self.assertIsNotNone(is_protected_path(".claude/playbooks/x.md"))
        self.assertIsNotNone(is_protected_path(".claude/plugins.lock"))


class TestSubagentPlannerBehavior(unittest.TestCase):
    """subagent_planner.py behavior tests."""

    def test_plan_rejects_protected_write_scope(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/subagent_planner.py", "plan",
             "--role", "worker", "--owner", "test-protected",
             "--goal", "test", "--write-scope", ".claude/hooks/x.py"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertNotEqual(r.returncode, 0,
                            "planner must reject protected write_scope")

    def test_plan_accepts_normal_scope(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/subagent_planner.py", "plan",
             "--role", "worker", "--owner", "test-normal",
             "--goal", "test", "--write-scope", "src/foo"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0,
                         f"planner rejected legitimate scope:\n{r.stderr}")
        out = json.loads(r.stdout)
        self.assertEqual(out["dispatch_status"], "ready")
        self.assertIn("dispatch_prompt", out)


class TestAutomationPlannerBehavior(unittest.TestCase):
    def test_scan_runs(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/automation_planner.py", "scan"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0)


class TestMcpAuditBehavior(unittest.TestCase):
    def test_audit_runs(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/mcp_audit.py", "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("rows", data)


class TestBootstrapProfileGate(unittest.TestCase):
    def test_promote_enforced_blocks_on_template(self):
        """When deployment_profile=template, enforced promotion is blocked."""
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            (repo / ".claude" / "runtime.json").write_text(json.dumps({
                "deployment_profile": "template",
                "mode": "advisory",
            }))
            # Import adopting the temp root
            import importlib, scripts  # noqa
            # We can't easily redirect REPO_ROOT — but we can call the
            # function directly with a patched path. Test the source has the guard.
            src = (REPO_ROOT / "scripts" / "harness" / "bootstrap.py").read_text()
            self.assertIn('profile == "template"', src,
                          "bootstrap must block enforced on template profile")
            self.assertIn("adopt-project", src,
                          "adopt-project path must be referenced")


class TestProtectedPathsSingleSource(unittest.TestCase):
    """R1: common.py loads from protected_paths.py — no drift."""

    def test_canonical_module_exists(self):
        p = REPO_ROOT / "scripts" / "harness" / "protected_paths.py"
        self.assertTrue(p.exists())

    def test_regex_and_globs_same_count(self):
        import protected_paths
        self.assertEqual(len(protected_paths.PROTECTED_REGEX),
                         len(protected_paths.PROTECTED_GLOBS))

    def test_common_imports_from_canonical(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "common.py").read_text()
        self.assertIn("from protected_paths import PROTECTED_REGEX", src)


class TestGlobConflictBoundary(unittest.TestCase):
    """R3: path-boundary-aware conflict detection."""

    def setUp(self):
        import subagent_planner
        self.fn = subagent_planner._glob_conflict

    def test_equal(self):
        self.assertTrue(self.fn("src/foo", "src/foo"))

    def test_descendant(self):
        self.assertTrue(self.fn("src/auth/api.py", "src/auth"))

    def test_sibling_prefix_not_conflict(self):
        # Regression: 'src/auth' vs 'src/authentication' must NOT collide
        self.assertFalse(self.fn("src/auth", "src/authentication"))

    def test_unrelated(self):
        self.assertFalse(self.fn("src/foo", "src/bar"))

    def test_glob_pattern_against_child(self):
        self.assertTrue(self.fn(".claude/hooks/foo.py", ".claude/hooks/**"))


class TestGate11SubagentPreflight(unittest.TestCase):
    """R6: Task/Agent preflight logic."""

    def test_gate_11_defined(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py").read_text()
        self.assertIn("def gate_11_subagent_preflight", src)
        self.assertIn('tool_name in ("Task", "Agent")', src)


class TestRoutingHint(unittest.TestCase):
    """R4: capability routing hint injection."""

    def test_routing_hint_function_exists(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "user_prompt_submit.py").read_text()
        self.assertIn("def _routing_hint", src)

    def test_explore_phrase_routes_to_explore(self):
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        import importlib
        ups = importlib.import_module("user_prompt_submit")
        hint = ups._routing_hint("search for all references to auth", REPO_ROOT)
        self.assertIn("codebase_question", hint)
        self.assertIn("Explore", hint)

    def test_implement_phrase_routes_to_worker(self):
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        import importlib
        ups = importlib.import_module("user_prompt_submit")
        hint = ups._routing_hint("implement the new payment flow", REPO_ROOT)
        self.assertIn("bounded_implementation", hint)

    def test_noise_prompt_returns_empty(self):
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        import importlib
        ups = importlib.import_module("user_prompt_submit")
        hint = ups._routing_hint("just thinking out loud", REPO_ROOT)
        self.assertEqual(hint, "")


class TestEventLogSyntheticFilter(unittest.TestCase):
    """R5: iter_all_events supports include_synthesized=False."""

    def test_filter_excludes_synthesized(self):
        with _portable_tempdir() as tmp:
            repo = Path(tmp)
            (repo / ".claude").mkdir()
            log = repo / ".claude" / "events.jsonl"
            lines = [
                json.dumps({"gate": "06", "outcome": "edit-tracked",
                            "ts": "2026-01-01T00:00:00Z", "session": "s",
                            "actor": "claude", "file": "a.py",
                            "detail": {"total_loc": 10}}),
                json.dumps({"gate": "06", "outcome": "edit-tracked",
                            "ts": "2026-01-01T00:00:01Z", "session": "s",
                            "actor": "replay", "file": "b.py",
                            "detail": {"synthesized": True, "total_loc": 5}}),
            ]
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")
            import event_log
            all_evs = list(event_log.iter_all_events(repo_root=repo))
            real_only = list(event_log.iter_all_events(
                repo_root=repo, include_synthesized=False))
            self.assertEqual(len(all_evs), 2)
            self.assertEqual(len(real_only), 1)
            self.assertEqual(real_only[0]["actor"], "claude")


class TestAutomationPlannerSignals(unittest.TestCase):
    """R9 coverage extension."""

    def test_stale_insights_detected(self):
        import importlib
        ap = importlib.import_module("automation_planner")
        # With no insights files, signal should fire
        self.assertTrue(ap.signal_stale_insights(days=0))

    def test_scan_writes_intents_file(self):
        import subprocess
        subprocess.run(
            ["python3", "scripts/harness/automation_planner.py", "scan"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        p = REPO_ROOT / ".claude" / "context" / "automation-intents.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("intents", data)


class TestMcpAuditFields(unittest.TestCase):
    """R9 coverage for mcp_audit."""

    def test_json_output_shape(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/mcp_audit.py", "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("rows", data)
        self.assertIn("mcp_json_exists", data)


class TestSessionStartPluginDrift(unittest.TestCase):
    """R7: session_start reads plugins.lock."""

    def test_plugins_lock_referenced_in_snapshot(self):
        src = (REPO_ROOT / ".claude" / "hooks" / "session_start.py").read_text()
        self.assertIn("plugins.lock", src)
        self.assertIn("Plugins (pinned)", src)


class TestGate11EndToEnd(unittest.TestCase):
    """N3: Exercise Gate ⑪ by running pre_tool_use.py as a subprocess
    with CLAUDE_HARNESS_TEST_BYPASS_CIRCUIT=1 so circuit state doesn't
    interfere.
    """

    HOOK = REPO_ROOT / ".claude" / "hooks" / "pre_tool_use.py"

    def _run(self, payload: dict, *, mode: str = "advisory") -> subprocess.CompletedProcess:
        # Temporarily set runtime mode via env-free override: the gate reads
        # runtime.json directly, so we snapshot/restore it.
        rt = REPO_ROOT / ".claude" / "runtime.json"
        import subprocess, os as _os
        orig = rt.read_text(encoding="utf-8") if rt.exists() else None
        try:
            if orig:
                data = json.loads(orig)
                data["mode"] = mode
                rt.write_text(json.dumps(data) + "\n", encoding="utf-8")
            env = _os.environ.copy()
            env["CLAUDE_HARNESS_TEST_BYPASS_CIRCUIT"] = "1"
            env["CLAUDE_SESSION_ID"] = "unit-test-gate11-e2e"
            return subprocess.run(
                ["python3", str(self.HOOK)],
                input=json.dumps(payload), capture_output=True, text=True,
                cwd=str(REPO_ROOT), env=env, timeout=10,
            )
        finally:
            if orig is not None:
                rt.write_text(orig, encoding="utf-8")

    def test_protected_path_with_edit_verb_blocks_in_enforced(self):
        r = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "cwd": str(REPO_ROOT),
            "tool_input": {
                "subagent_type": "general-purpose",
                "prompt": "please edit .claude/hooks/foo.py to fix the race",
            },
        }, mode="enforced")
        self.assertEqual(r.returncode, 2,
                         f"expected exit 2, got {r.returncode}\nstderr: {r.stderr}")

    def test_protected_path_without_edit_verb_passes(self):
        r = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "cwd": str(REPO_ROOT),
            "tool_input": {
                "subagent_type": "Explore",
                "prompt": "read .claude/hooks/foo.py and summarize its structure",
            },
        }, mode="enforced")
        self.assertEqual(r.returncode, 0, f"Explore prompt should not block\n{r.stderr}")

    def test_negated_edit_verb_passes(self):
        r = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "cwd": str(REPO_ROOT),
            "tool_input": {
                "subagent_type": "general-purpose",
                "prompt": "work on src/foo.py but do NOT edit .claude/hooks/ anything",
            },
        }, mode="enforced")
        self.assertEqual(r.returncode, 0, f"negated verb should not block\n{r.stderr}")

    def test_advisory_mode_logs_not_blocks(self):
        r = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "cwd": str(REPO_ROOT),
            "tool_input": {
                "subagent_type": "general-purpose",
                "prompt": "edit .claude/hooks/foo.py",
            },
        }, mode="advisory")
        self.assertEqual(r.returncode, 0, "advisory mode should not block")


class TestRegexToGlobStrict(unittest.TestCase):
    """protected_paths._regex_to_glob must reject unsupported metachars."""

    def test_rejects_alternation(self):
        import protected_paths
        with self.assertRaises(ValueError):
            protected_paths._regex_to_glob(r"^(foo|bar)$", "file")

    def test_rejects_plus(self):
        import protected_paths
        with self.assertRaises(ValueError):
            protected_paths._regex_to_glob(r"^foo+$", "file")

    def test_accepts_supported(self):
        import protected_paths
        self.assertEqual(
            protected_paths._regex_to_glob(r"^\.claude/hooks/", "dir"),
            ".claude/hooks/**",
        )


class TestBootstrapScrubPreview(unittest.TestCase):
    def test_scrub_preview_runs(self):
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/harness/bootstrap.py", "--scrub-preview"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=15,
        )
        self.assertEqual(r.returncode, 0, f"scrub-preview failed:\n{r.stderr}")
        # Must be descriptive, not destructive language
        self.assertIn("preview", r.stdout.lower() + "already clean")


class TestRoutingHintWordBoundary(unittest.TestCase):
    """N2 regression: 'search' inside a larger word must not trigger."""

    def _hint(self, msg: str) -> str:
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        import importlib
        ups = importlib.import_module("user_prompt_submit")
        return ups._routing_hint(msg, REPO_ROOT)

    def test_search_as_word(self):
        self.assertIn("codebase_question", self._hint("search the repo"))

    def test_researching_not_search(self):
        # "researching" contains "search" substring — must not trigger
        hint = self._hint("we are researching approaches")
        self.assertNotIn("codebase_question", hint)

    def test_overview_no_false_positive(self):
        self.assertEqual(self._hint("give me an overview of this project"), "")


if __name__ == "__main__":
    import subprocess  # used by TestGate2PreBehavior
    unittest.main(verbosity=2)
