from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def test_runtime_json_is_valid(self) -> None:
        data = json.loads((REPO_ROOT / ".codex" / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(data["response_language"], "ko")
        self.assertIn(data["deployment_profile"], {"template", "project"})
        self.assertIsInstance(data["hook_adapter"]["enabled"], bool)
        if data["deployment_profile"] == "template":
            self.assertEqual(data["mode"], "advisory")
            self.assertFalse(data["hook_adapter"]["enabled"])
        self.assertIn("defaults", data)
        self.assertIn("feedback_loop", data)

    def test_scripts_parse(self) -> None:
        for path in (REPO_ROOT / "scripts" / "harness").glob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"))

    def test_bootstrap_skip_self_test(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/harness/bootstrap.py", "--skip-self-test"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_manifest_validation(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/harness/validate_manifests.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_mode_recommender_worker_prefers_worktree(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "scripts/harness/mode_recommender.py",
                "--role",
                "worker",
                "src/auth/service.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["mode"], "worktree")
        self.assertEqual(payload["tier"], "high-risk")

    def test_protect_paths_advisory(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/harness/protect_paths.py", "AGENTS.md"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ADVISORY", proc.stdout)

    def test_event_and_learning_log_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "telemetry").mkdir(parents=True)

            from scripts.harness import event_log, learning_log

            event_log.append_event(
                kind="test",
                actor="unit",
                summary="event",
                root=root,
            )
            learning_log.append_learning(
                pattern="unit-pattern",
                mistake="unit mistake",
                fix="unit fix",
                root=root,
            )
            self.assertTrue((root / ".codex" / "telemetry" / "events.jsonl").exists())
            self.assertTrue((root / ".codex" / "telemetry" / "learnings.jsonl").exists())
            self.assertEqual(len(list(event_log.iter_events(root))), 1)
            self.assertEqual(len(learning_log.load_recent(root=root)), 1)

    def test_session_state_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "context").mkdir(parents=True)
            from scripts.harness import session_state

            first = session_state.resolve_session_id(root)
            second = session_state.resolve_session_id(root)
            self.assertEqual(first, second)
            payload = json.loads((root / ".codex" / "context" / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["session_id"], first)

    def test_activity_bridge_sync_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            (root / "Plan.md").write_text("# Plan\n", encoding="utf-8")
            from scripts.harness import activity_bridge, event_log

            self.assertEqual(activity_bridge.sync(root), [])
            self.assertEqual(len(list(event_log.iter_events(root))), 0)

            (root / "Plan.md").write_text("# Plan\n\nupdated\n", encoding="utf-8")
            changed = activity_bridge.sync(root)
            self.assertEqual(changed, ["Plan.md"])
            self.assertEqual(len(list(event_log.iter_events(root))), 1)

            self.assertEqual(activity_bridge.sync(root), [])
            self.assertEqual(len(list(event_log.iter_events(root))), 1)

    def test_append_only_guard_detects_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex").mkdir(parents=True)
            (root / ".codex" / "runtime.json").write_text('{"mode":"enforced"}\n', encoding="utf-8")
            existing = root / "old.txt"
            candidate = root / "new.txt"
            existing.write_text("a\nb\n", encoding="utf-8")
            candidate.write_text("x\na\nb\n", encoding="utf-8")
            from scripts.harness.append_only_guard import check_append_only

            violations = check_append_only(existing, candidate)
            self.assertTrue(violations)

    def test_ownership_guard_conflict_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex").mkdir(exist_ok=True)
            (root / ".codex" / "runtime.json").write_text('{"mode":"enforced"}\n', encoding="utf-8")
            from scripts.harness.ownership_guard import claim_paths, conflict_messages

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(claim_paths(root, "worker-a", ["src/api"], "worktree"), 0)
            conflicts = conflict_messages(root, "worker-b", ["src/api/auth"])
            self.assertTrue(conflicts)

    def test_runtime_gate_enforced_blocks_missing_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex").mkdir(exist_ok=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "mode-policy.yaml", root / ".codex" / "manifests" / "mode-policy.yaml")
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "review-matrix.yaml", root / ".codex" / "manifests" / "review-matrix.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "enforced", "deployment_profile": "project"}) + "\n",
                encoding="utf-8",
            )
            for rel in ("Prompt.md", "PRD.md", "Plan.md", "Implement.md", "Documentation.md", "Subagent-Manifest.md"):
                (root / rel).write_text("# seeded\n## Validation\n- ok\n## Rollback\n- ok\n", encoding="utf-8")
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "seed"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "Unit Test",
                    "GIT_AUTHOR_EMAIL": "unit@test.local",
                    "GIT_COMMITTER_NAME": "Unit Test",
                    "GIT_COMMITTER_EMAIL": "unit@test.local",
                },
            )
            from scripts.harness.runtime_gate import command_check_complete

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command_check_complete(root, "normal", None), 2)

    def test_runtime_gate_blocks_enforced_mode_for_template_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "mode-policy.yaml", root / ".codex" / "manifests" / "mode-policy.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "advisory", "deployment_profile": "template"}) + "\n",
                encoding="utf-8",
            )
            from scripts.harness.runtime_gate import command_set_mode

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command_set_mode(root, "enforced"), 2)

    def test_runtime_gate_allows_enforced_for_project_with_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "mode-policy.yaml", root / ".codex" / "manifests" / "mode-policy.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "advisory", "deployment_profile": "project"}) + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            commit = subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "seed"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "Unit Test",
                    "GIT_AUTHOR_EMAIL": "unit@test.local",
                    "GIT_COMMITTER_NAME": "Unit Test",
                    "GIT_COMMITTER_EMAIL": "unit@test.local",
                },
            )
            self.assertEqual(commit.returncode, 0, commit.stdout + commit.stderr)
            from scripts.harness.runtime_gate import command_set_mode, load_runtime

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command_set_mode(root, "enforced"), 0)
            self.assertEqual(load_runtime(root)["mode"], "enforced")

    def test_runtime_gate_blocks_non_independent_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex" / "reviews").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "mode-policy.yaml", root / ".codex" / "manifests" / "mode-policy.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "enforced", "deployment_profile": "project"}) + "\n",
                encoding="utf-8",
            )
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "review-matrix.yaml", root / ".codex" / "manifests" / "review-matrix.yaml")
            for rel in ("Prompt.md", "PRD.md", "Plan.md", "Implement.md", "Documentation.md", "Subagent-Manifest.md"):
                (root / rel).write_text("# seeded\n## Validation\n- ok\n## Rollback\n- ok\n", encoding="utf-8")
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "seed"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "Unit Test",
                    "GIT_AUTHOR_EMAIL": "unit@test.local",
                    "GIT_COMMITTER_NAME": "Unit Test",
                    "GIT_COMMITTER_EMAIL": "unit@test.local",
                },
            )
            review = root / ".codex" / "reviews" / "review.md"
            review.write_text(
                "\n".join(
                    [
                        "Reviewer: main-codex",
                        "Producer: main-codex",
                        "Reviewer-Session: session-123",
                        "Producer-Session: session-123",
                        "",
                        "Verdict: accept",
                        "",
                        "Files:",
                        "- Prompt.md",
                        "",
                        "Findings:",
                        "- none",
                        "",
                        "Validation:",
                        "- pytest -q (pass)",
                        "",
                        "Risks:",
                        "- none",
                        "",
                        "Rollback:",
                        "- revert commit",
                        "",
                        "Notes: " + ("x" * 260),
                    ]
                ),
                encoding="utf-8",
            )
            from scripts.harness.runtime_gate import command_check_complete

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command_check_complete(root, "normal", ".codex/reviews/review.md"), 2)

    def test_review_gate_prepare_seeds_review_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "review-matrix.yaml", root / ".codex" / "manifests" / "review-matrix.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "advisory", "deployment_profile": "project"}) + "\n",
                encoding="utf-8",
            )
            (root / "Prompt.md").write_text("seeded prompt\n", encoding="utf-8")
            (root / "PRD.md").write_text("seeded prd\n", encoding="utf-8")
            (root / "Plan.md").write_text("# Plan\n\n## Rollback\n- revert safely\n", encoding="utf-8")
            (root / "Implement.md").write_text("# Implement\n\n## Validation\n- pytest -q passed\n", encoding="utf-8")
            (root / "Documentation.md").write_text("seeded docs\n", encoding="utf-8")
            (root / "Subagent-Manifest.md").write_text("seeded manifest\n", encoding="utf-8")
            from scripts.harness.review_gate import prepare_review

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    prepare_review(
                        root,
                        tier="normal",
                        producer="main-codex",
                        review_file=None,
                        base="HEAD",
                        files=["src/api.py"],
                        validations=[],
                        rollback_items=[],
                        force=False,
                    ),
                    0,
                )
            reviews = sorted((root / ".codex" / "reviews").glob("*.md"))
            self.assertEqual(len(reviews), 1)
            content = reviews[0].read_text(encoding="utf-8")
            self.assertIn("Producer: main-codex", content)
            self.assertIn("- src/api.py", content)
            self.assertIn("producer context: pytest -q passed", content)

    def test_review_gate_finalize_blocks_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex" / "reviews").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "review-matrix.yaml", root / ".codex" / "manifests" / "review-matrix.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"mode": "advisory", "deployment_profile": "project"}) + "\n",
                encoding="utf-8",
            )
            for rel in ("Prompt.md", "PRD.md", "Plan.md", "Implement.md", "Documentation.md", "Subagent-Manifest.md"):
                (root / rel).write_text("# seeded\n## Validation\n- ok\n## Rollback\n- ok\n", encoding="utf-8")
            review = root / ".codex" / "reviews" / "review.md"
            review.write_text(
                "\n".join(
                    [
                        "Reviewer: <required-reviewer>",
                        "Producer: main-codex",
                        "Reviewer-Session: <required-reviewer-session>",
                        "Producer-Session: session-123",
                        "",
                        "Verdict: pending",
                        "",
                        "Files:",
                        "- src/api.py",
                        "",
                        "Findings:",
                        "- <reviewer: add findings or replace with none>",
                        "",
                        "Validation:",
                        "- producer context: pytest -q passed",
                        "- <reviewer-run command and result>",
                        "",
                        "Risks:",
                        "- <reviewer: remaining risk or none>",
                    ]
                ),
                encoding="utf-8",
            )
            from scripts.harness.review_gate import finalize_review

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(finalize_review(root, tier="normal", review_file="latest", actor="main-codex"), 2)

    def test_hook_adapter_session_start_emits_context_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            runtime = {
                "deployment_profile": "project",
                "mode": "advisory",
                "stage": "project-bootstrap",
                "hook_adapter": {"enabled": True},
            }
            (root / ".codex" / "runtime.json").write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            from scripts.harness.hook_adapter import session_start_output

            result = session_start_output(root, {"source": "startup"})
            self.assertIsNotNone(result)
            text = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Codex harness active.", text)
            self.assertIn("review_gate.py prepare/finalize", text)

    def test_hook_adapter_user_prompt_prefetches_relevant_learning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            (root / ".codex").mkdir(exist_ok=True)
            runtime = {
                "deployment_profile": "project",
                "mode": "advisory",
                "hook_adapter": {"enabled": True, "prefetch_on_prompt": True, "prefetch_top_k": 2},
            }
            (root / ".codex" / "runtime.json").write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            from scripts.harness.learning_log import append_learning
            from scripts.harness.hook_adapter import user_prompt_submit_output

            append_learning(
                pattern="ownership-conflict",
                mistake="parallel ownership conflict on auth paths",
                fix="split write scopes before parallel auth edits",
                root=root,
            )
            result = user_prompt_submit_output(root, {"prompt": "parallel auth edit plan"})
            self.assertIsNotNone(result)
            text = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Relevant harness learnings", text)
            self.assertIn("ownership-conflict", text)

    def test_hook_adapter_stop_blocks_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex" / "reviews").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "review-matrix.yaml", root / ".codex" / "manifests" / "review-matrix.yaml")
            runtime = {
                "deployment_profile": "project",
                "mode": "advisory",
                "hook_adapter": {"enabled": True, "stop_on_pending_review": True},
            }
            (root / ".codex" / "runtime.json").write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            (root / "Prompt.md").write_text("seeded prompt\n", encoding="utf-8")
            (root / "PRD.md").write_text("seeded prd\n", encoding="utf-8")
            (root / "Plan.md").write_text("# Plan\n\n## Rollback\n- revert\n\n## Tier\n- tier: normal\n", encoding="utf-8")
            (root / "Implement.md").write_text("# Implement\n\n## Validation\n- pytest -q passed\n", encoding="utf-8")
            (root / "Documentation.md").write_text("seeded docs\n", encoding="utf-8")
            (root / "Subagent-Manifest.md").write_text("seeded manifest\n", encoding="utf-8")
            review = root / ".codex" / "reviews" / "review.md"
            review.write_text(
                "\n".join(
                    [
                        "Reviewer: <required-reviewer>",
                        "Producer: main-codex",
                        "Reviewer-Session: <required-reviewer-session>",
                        "Producer-Session: session-123",
                        "",
                        "Verdict: pending",
                        "",
                        "Files:",
                        "- src/api.py",
                        "",
                        "Findings:",
                        "- <reviewer: add findings or replace with none>",
                        "",
                        "Validation:",
                        "- producer context: pytest -q passed",
                        "- <reviewer-run command and result>",
                        "",
                        "Risks:",
                        "- <reviewer: remaining risk or none>",
                    ]
                ),
                encoding="utf-8",
            )
            from scripts.harness.hook_adapter import stop_output

            result = stop_output(root, {"stop_hook_active": False})
            self.assertIsNotNone(result)
            self.assertEqual(result["decision"], "block")
            self.assertIn("review_gate.py finalize", result["reason"])

    def test_repo_local_hook_script_smoke(self) -> None:
        runtime = json.loads((REPO_ROOT / ".codex" / "runtime.json").read_text(encoding="utf-8"))
        proc = subprocess.run(
            [
                "python3",
                ".codex/hooks/session_start.py",
            ],
            cwd=str(REPO_ROOT),
            input=json.dumps({"source": "startup"}),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        if runtime["hook_adapter"]["enabled"]:
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("Codex harness active.", payload["hookSpecificOutput"]["additionalContext"])
        else:
            self.assertEqual(proc.stdout.strip(), "")

    def test_worktree_init_repo_creates_head_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("seed\n", encoding="utf-8")
            from scripts.harness.worktree_manager import init_repo

            self.assertEqual(init_repo(root, "main", True), 0)
            verify = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    def test_subagent_planner_builds_worker_spec_and_claims_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "context").mkdir(parents=True)
            (root / ".codex" / "manifests").mkdir(parents=True)
            (root / ".codex").mkdir(exist_ok=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "subagents.yaml", root / ".codex" / "manifests" / "subagents.yaml")
            (root / ".codex" / "runtime.json").write_text(json.dumps({"mode": "advisory"}) + "\n", encoding="utf-8")
            from scripts.harness.subagent_planner import build_spec, load_state, save_spec

            spec = build_spec(
                root,
                role="worker",
                owner="worker-auth",
                goal="implement auth slice",
                read_scope=["Plan.md"],
                write_scope=["src/auth", "tests/auth"],
                stop_condition="auth tests pass",
                validation="pytest tests/auth -q",
                mode="auto",
                clean_room=False,
                forbidden=[],
                claim=True,
            )
            self.assertEqual(spec["mode"], "worktree")
            self.assertEqual(spec["dispatch_status"], "ready")
            self.assertTrue(spec["ownership_claimed"])
            self.assertIn("Do not revert unrelated edits.", spec["dispatch_prompt"])
            save_spec(root, spec)
            state = load_state(root)
            self.assertIn("worker-auth", state["tasks"])
            ownership = json.loads((root / ".codex" / "context" / "ownership.json").read_text(encoding="utf-8"))
            self.assertIn("worker-auth", ownership["claims"])

    def test_automation_planner_scan_generates_followup_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for rel in (
                ".codex/context",
                ".codex/manifests",
                ".codex/reviews",
                ".codex/telemetry",
                ".codex/audits",
                ".codex/skills/_proposed",
            ):
                (root / rel).mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "automation-policy.yaml", root / ".codex" / "manifests" / "automation-policy.yaml")
            (root / ".codex" / "runtime.json").write_text(
                json.dumps({"feedback_loop": {"insights_interval_days": 7}}) + "\n",
                encoding="utf-8",
            )
            (root / "Plan.md").write_text("# Plan\n\n- tier: high-risk\n", encoding="utf-8")
            (root / ".codex" / "reviews" / "review-20260418T000000Z.md").write_text(
                "\n".join(
                    [
                        "Reviewer: <required-reviewer>",
                        "Producer: main-codex",
                        "Reviewer-Session: <required-reviewer-session>",
                        "Producer-Session: session-main",
                        "Review-Tier: high-risk",
                        "Requested-At: 20260418T000000Z",
                        "",
                        "Verdict: pending",
                        "",
                        "Files:",
                        "- src/auth/service.py",
                        "",
                        "Findings:",
                        "- <reviewer: add findings or replace with none>",
                        "",
                        "Validation:",
                        "- <reviewer-run command and result>",
                        "",
                        "Risks:",
                        "- <reviewer: remaining risk or none>",
                        "",
                        "Rollback:",
                        "- <reviewer: confirm rollback path and trigger>",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (root / ".codex" / "skills" / "_proposed" / "ownership-conflict.md").write_text("# skill\n", encoding="utf-8")
            from scripts.harness.automation_planner import scan

            payload = scan(root)
            names = {item["name"] for item in payload["suggestions"]}
            self.assertIn("Pending Review Follow-up", names)
            self.assertIn("Harness Evolution Sweep", names)
            self.assertIn("Proposed Skill Triage", names)
            state = json.loads((root / ".codex" / "context" / "automation-intents.json").read_text(encoding="utf-8"))
            self.assertEqual(len(state["suggestions"]), 3)

    def test_skill_auto_gen_creates_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            (root / ".codex" / "skills" / "_proposed").mkdir(parents=True)
            (root / ".codex" / "manifests").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".codex" / "manifests" / "evolution-policy.yaml", root / ".codex" / "manifests" / "evolution-policy.yaml")
            from scripts.harness.learning_log import append_learning
            from scripts.harness.skill_auto_gen import generate

            for idx in range(3):
                append_learning(
                    pattern="ownership-conflict",
                    mistake=f"overlap {idx}",
                    fix="split write scopes",
                    root=root,
                )
            created = generate(3, root)
            self.assertEqual(len(created), 1)
            self.assertTrue(created[0].exists())

    def test_insights_report_excludes_proposed_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".codex" / "telemetry").mkdir(parents=True)
            (root / ".codex" / "context").mkdir(parents=True)
            proposed = root / ".codex" / "skills" / "_proposed"
            proposed.mkdir(parents=True)
            (proposed / "README.md").write_text("index\n", encoding="utf-8")
            (proposed / "ownership-conflict.md").write_text("# skill\n", encoding="utf-8")
            from scripts.harness.insights_report import generate

            report = generate(root)
            content = report.read_text(encoding="utf-8")
            self.assertIn("ownership-conflict.md", content)
            self.assertNotIn("README.md", content)

    def test_bootstrap_adopt_project_updates_runtime(self) -> None:
        runtime_path = REPO_ROOT / ".codex" / "runtime.json"
        original = runtime_path.read_text(encoding="utf-8")
        try:
            proc = subprocess.run(
                ["python3", "scripts/harness/bootstrap.py", "--skip-self-test", "--adopt-project", "--project-focus", "first project loop"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["deployment_profile"], "project")
            self.assertEqual(payload["mode"], "advisory")
            self.assertEqual(payload["current_focus"], "first project loop")
            self.assertTrue(payload["hook_adapter"]["enabled"])
        finally:
            runtime_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
