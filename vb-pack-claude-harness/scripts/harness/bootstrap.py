#!/usr/bin/env python3
"""
bootstrap.py — Generate .claude/settings.local.json and initialize runtime
state for a new project.

Usage:
    python3 scripts/harness/bootstrap.py                # idempotent install
    python3 scripts/harness/bootstrap.py --force        # overwrite settings
    python3 scripts/harness/bootstrap.py --reset-logs   # wipe events/learnings
    python3 scripts/harness/bootstrap.py --promote advisory   # mode transition
    python3 scripts/harness/bootstrap.py --promote enforced

What it does (all idempotent unless --force):
  1. Copy templates/settings.template.json → .claude/settings.local.json
     (strips the _comment key, preserves JSON formatting)
  2. chmod +x on .claude/hooks/*.py and scripts/harness/*.py
  3. Create .claude/{audits,reviews,direction-checks,spikes,test-runs,ephemeral}
  4. Initialize runtime.json from templates/runtime.initial.json if missing
     (fresh hook_health, no stale timestamps)
  5. Initialize empty events.jsonl / learnings.jsonl (0-byte) if missing
  6. Run self_test.py and report pass/fail

--reset-logs: truncates events.jsonl + learnings.jsonl to 0 bytes. Used when
  cloning the template to wipe any committed history.

--promote <mode>: transitions runtime.mode (bootstrap → advisory → enforced).
  Checks gating conditions before allowing promotion to enforced.

Exit 0 = ready. Exit 1 = one or more problems.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    ".claude/audits",
    ".claude/reviews",
    ".claude/direction-checks",
    ".claude/spikes",
    ".claude/test-runs",
    ".claude/ephemeral",
    ".claude/agents",
    ".claude/sealed-prompts",
    ".claude/skills/_manual",
    ".claude/skills/_evolving",
]


def copy_settings(force: bool) -> tuple[bool, str]:
    src = REPO_ROOT / "templates" / "settings.template.json"
    dst = REPO_ROOT / ".claude" / "settings.local.json"
    if not src.exists():
        return False, f"missing template: {src}"
    if dst.exists() and not force:
        return True, "already present (use --force to overwrite)"
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"template JSON invalid: {exc}"
    data.pop("_comment", None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return True, f"wrote {dst.relative_to(REPO_ROOT)}"


def chmod_executable() -> tuple[bool, str]:
    targets = list((REPO_ROOT / ".claude" / "hooks").glob("*.py"))
    targets += list((REPO_ROOT / "scripts" / "harness").glob("*.py"))
    count = 0
    for p in targets:
        mode = p.stat().st_mode
        p.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        count += 1
    return True, f"{count} file(s) made executable"


def ensure_dirs() -> tuple[bool, str]:
    created = 0
    for rel in REQUIRED_DIRS:
        p = REPO_ROOT / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created += 1
    return True, f"{created} directory(ies) created (of {len(REQUIRED_DIRS)})"


FRESH_RUNTIME = {
    "framework_version": "unified-4-axis-1.0",
    "deployment_profile": "template",
    "mode": "bootstrap",
    "schema_version": 2,
    "agent_defaults": {
        "worker_isolation": "worktree",
        "explorer_isolation": "none",
        "reviewer_isolation": "none"
    },
    "tier": "normal",
    "complexity": "simple",
    "plan": {"id": "", "path": "Plan.md", "status": "pending", "hash": ""},
    "orchestrator": {
        "writable_globs": ["*.md", "**/*.md", "plans/**", "docs/**",
                            "templates/*.md", "templates/**/*.md"]
    },
    "limits": {
        "diff_max_files": 12, "diff_max_added_removed": 500,
        "retry_budget": 3, "trivial_loc": 20, "normal_loc": 100,
        "high_risk_loc_threshold": 150,
    },
    "gates": {
        "scope_locked": False, "plan_reviewed": False,
        "failing_tests_committed": False, "implementation_verified": False,
        "deterministic_verified": False, "ship_approved": False,
    },
    "bootstrap": {
        "allow_dirty_worktree": True,
        "enforcement_phase": "advisory",
        "baseline_manifest": ".claude/baseline/current.json",
        "advisory_rules": ["scope_creep", "test_skip"],
        "full_mode_requirements": [
            "dirty worktree baseline must be refreshed or removed",
            "deterministic gate commands must be green for changed surfaces",
            "commit/push gate should move from advisory to blocking",
        ],
    },
    "self_evolving": {
        "memory_pre_hook_enabled": True, "memory_post_hook_enabled": True,
        "skill_auto_gen_enabled": True, "taxonomy_learner_enabled": True,
        "insights_interval_days": 7, "auto_apply_proposals": False,
        "pending_proposals": [],
    },
    "hook_health": {},
}


def init_runtime(force: bool) -> tuple[bool, str]:
    dst = REPO_ROOT / ".claude" / "runtime.json"
    if dst.exists() and not force:
        return True, "already present"
    # Always start fresh — NEVER copy a committed runtime.json which may
    # contain stale hook_health timestamps from template author's sessions.
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(FRESH_RUNTIME, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return True, "wrote fresh runtime.json (no stale state)"


def init_logs(reset: bool) -> tuple[bool, str]:
    """Create empty events.jsonl / learnings.jsonl.

    - reset=False: create only if missing (do not touch existing user data)
    - reset=True : truncate to 0 bytes even if present
    """
    claude = REPO_ROOT / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    targets = [claude / "events.jsonl", claude / "learnings.jsonl"]
    actions = []
    for p in targets:
        if reset or not p.exists():
            p.write_text("", encoding="utf-8")
            actions.append(p.name)
    if not actions:
        return True, "already present (no reset)"
    verb = "reset" if reset else "created empty"
    return True, f"{verb}: {', '.join(actions)}"


PROMOTE_ORDER = ("bootstrap", "advisory", "enforced")


def promote_mode(target: str) -> tuple[bool, str]:
    dst = REPO_ROOT / ".claude" / "runtime.json"
    if not dst.exists():
        return False, "runtime.json missing — run bootstrap first"
    data = json.loads(dst.read_text(encoding="utf-8"))
    current = data.get("mode", "bootstrap")
    profile = data.get("deployment_profile", "template")
    if target not in PROMOTE_ORDER:
        return False, f"unknown mode: {target} (expected one of {PROMOTE_ORDER})"
    if PROMOTE_ORDER.index(target) <= PROMOTE_ORDER.index(current):
        return False, f"cannot promote from {current} → {target} (no-op or demote)"
    # Template profile cannot promote to enforced — prevents accidental
    # enforcement on a template distribution repo.
    if target == "enforced" and profile == "template":
        return False, ("enforced mode blocked on template profile. "
                        "Run `bootstrap.py --adopt-project` first to transition "
                        "this clone into a project repo.")
    # Pre-flight for enforced
    if target == "enforced":
        blockers = _enforced_preflight()
        if blockers:
            return False, "enforced pre-flight failed:\n    - " + "\n    - ".join(blockers)
    data["mode"] = target
    if target == "enforced":
        data.setdefault("bootstrap", {})["enforcement_phase"] = "enforced"
        data["bootstrap"]["allow_dirty_worktree"] = False
    elif target == "advisory":
        data.setdefault("bootstrap", {})["enforcement_phase"] = "advisory"
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return True, f"promoted: {current} → {target}"


SCRUB_PATHS = [
    ".claude/events.jsonl", ".claude/learnings.jsonl",
    ".claude/context-snapshot.md",
]
SCRUB_DIRS = [
    ".claude/reviews", ".claude/direction-checks", ".claude/spikes",
    ".claude/audits", ".claude/test-runs", ".claude/ephemeral",
]


def scrub_preview() -> tuple[bool, str]:
    """Report what adopt_project --scrub would remove, without touching it."""
    report: list[str] = []
    for rel in SCRUB_PATHS:
        p = REPO_ROOT / rel
        if p.exists():
            try:
                size = p.stat().st_size
            except OSError:
                size = -1
            report.append(f"  would truncate:  {rel}  ({size}B)")
    for rel in SCRUB_DIRS:
        p = REPO_ROOT / rel
        if p.exists():
            try:
                children = list(p.iterdir())
            except OSError:
                children = []
            if children:
                report.append(f"  would clean:     {rel}/  ({len(children)} item(s))")
    # Tracked files
    try:
        r = subprocess.run(
            ["git", "ls-files"] + SCRUB_PATHS +
            [d + "/" for d in SCRUB_DIRS],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=10,
        )
        tracked = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if tracked:
            report.append(f"  git-tracked ({len(tracked)}):")
            for t in tracked[:15]:
                report.append(f"    - {t}")
            if len(tracked) > 15:
                report.append(f"    ... +{len(tracked) - 15} more")
    except Exception:
        pass

    if not report:
        return True, "already clean — nothing to scrub"
    return True, "preview:\n" + "\n".join(report)


def adopt_project() -> tuple[bool, str]:
    """Transition a template clone into an active project.

    Steps:
      1. Scrub generated artifacts (events.jsonl, reviews/, etc.)
      2. Flip deployment_profile: template → project in runtime.json
      3. git init if no .git; create initial empty commit if no HEAD

    After this, `--promote enforced` becomes allowed.
    """
    import shutil
    actions: list[str] = []

    # 1. scrub
    for rel in SCRUB_PATHS:
        p = REPO_ROOT / rel
        if p.exists():
            p.write_text("", encoding="utf-8")
            actions.append(f"truncated {rel}")
    for rel in SCRUB_DIRS:
        p = REPO_ROOT / rel
        if p.exists() and any(p.iterdir()):
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True, exist_ok=True)
            actions.append(f"cleaned {rel}/")

    # 2. profile flip
    rt = REPO_ROOT / ".claude" / "runtime.json"
    if rt.exists():
        data = json.loads(rt.read_text(encoding="utf-8"))
        prev = data.get("deployment_profile", "template")
        data["deployment_profile"] = "project"
        # Reset hook_health to avoid stale timestamps
        data["hook_health"] = {}
        rt.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
        actions.append(f"deployment_profile: {prev} → project")

    # 3. git init if missing
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        r = subprocess.run(["git", "init", "-q"], cwd=str(REPO_ROOT),
                            capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            actions.append("git init")

    # 4. seed empty commit if no HEAD
    r = subprocess.run(["git", "rev-parse", "--verify", "HEAD"],
                        capture_output=True, text=True,
                        cwd=str(REPO_ROOT), timeout=5)
    if r.returncode != 0:
        subprocess.run(["git", "commit", "--allow-empty", "-m",
                         "chore: seed commit for harness adoption"],
                        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10)
        actions.append("seeded empty commit")

    return True, "adopted:\n    " + "\n    ".join(actions)


def _enforced_preflight() -> list[str]:
    """Return list of blocker messages; empty list = clear to promote."""
    blockers: list[str] = []
    # 1. Clean git worktree
    try:
        r = subprocess.run(["git", "status", "--porcelain"],
                            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            blockers.append("dirty git worktree — commit or stash first")
    except Exception:
        pass
    # 2. self_test passes
    st = REPO_ROOT / "scripts" / "harness" / "self_test.py"
    if st.exists():
        r = subprocess.run(["python3", str(st)], capture_output=True, text=True,
                           cwd=str(REPO_ROOT), timeout=60)
        if r.returncode != 0:
            blockers.append("self_test not green")
    # 3. Unit tests pass
    r = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
                        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=120)
    if r.returncode != 0:
        blockers.append("unit tests not green")
    return blockers


def run_self_test() -> tuple[bool, str]:
    test_script = REPO_ROOT / "scripts" / "harness" / "self_test.py"
    if not test_script.exists():
        return False, "self_test.py missing"
    try:
        result = subprocess.run(
            ["python3", str(test_script)],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "self_test.py timed out"
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-5:]
        return False, "self_test failed:\n    " + "\n    ".join(tail)
    return True, "self_test passed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing settings.local.json and runtime.json")
    ap.add_argument("--reset-logs", action="store_true",
                    help="truncate events.jsonl + learnings.jsonl to 0 bytes")
    ap.add_argument("--promote", metavar="MODE", default=None,
                    help="promote runtime.mode (bootstrap→advisory→enforced)")
    ap.add_argument("--adopt-project", action="store_true",
                    help="transition template → project profile (scrub + git init)")
    ap.add_argument("--scrub-preview", action="store_true",
                    help="preview what adopt-project would scrub (no changes)")
    args = ap.parse_args()

    if args.scrub_preview:
        ok, msg = scrub_preview()
        print(msg)
        return 0 if ok else 1

    if args.adopt_project:
        ok, msg = adopt_project()
        mark = "ok " if ok else "FAIL"
        print(f"  [{mark}] adopt-project         {msg}")
        return 0 if ok else 1

    if args.promote:
        ok, msg = promote_mode(args.promote)
        mark = "ok " if ok else "FAIL"
        print(f"  [{mark}] promote               {msg}")
        return 0 if ok else 1

    steps = [
        ("settings.local.json", lambda: copy_settings(args.force)),
        ("hook executability", chmod_executable),
        ("required directories", ensure_dirs),
        ("runtime.json",         lambda: init_runtime(args.force)),
        ("events/learnings logs", lambda: init_logs(args.reset_logs)),
        ("self_test",            run_self_test),
    ]
    failed: list[str] = []
    for label, fn in steps:
        ok, msg = fn()
        mark = "ok " if ok else "FAIL"
        print(f"  [{mark}] {label:<22} {msg}")
        if not ok:
            failed.append(label)
    print()
    if failed:
        print(f"bootstrap FAILED ({len(failed)}): {', '.join(failed)}")
        return 1
    print("bootstrap OK — harness is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
