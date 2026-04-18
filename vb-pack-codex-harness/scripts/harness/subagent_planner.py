#!/usr/bin/env python3
"""Generate structured dispatch specs for Codex subagents."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import event_log
    import mode_recommender
    import ownership_guard
    from manifest_loader import load as load_manifest
else:  # pragma: no cover - package import path
    from . import event_log, mode_recommender, ownership_guard
    from .manifest_loader import load as load_manifest


STATE_PATH = Path(".codex/context/subagent-tasks.json")
SHARED_READ_SCOPE = [
    "Prompt.md",
    "PRD.md",
    "Plan.md",
    "Implement.md",
    "Documentation.md",
    "Subagent-Manifest.md",
]
PROTECTED_DEFAULTS = [
    "AGENTS.md",
    "ETHOS.md",
    ".codex/runtime.json",
    ".codex/manifests/**",
    ".codex/hooks/**",
    ".codex/telemetry/**",
    ".codex/context/activity-state.json",
    ".codex/context/session.json",
    ".codex/context/ownership.json",
    ".codex/context/subagent-tasks.json",
    ".codex/context/automation-intents.json",
]


def repo_root() -> Path:
    return event_log.repo_root()


def subagent_policy(root: Path) -> dict[str, Any]:
    path = root / ".codex" / "manifests" / "subagents.yaml"
    if not path.exists():
        return {}
    return load_manifest(path)


def state_path(root: Path) -> Path:
    return root / STATE_PATH


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        return {"tasks": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": {}}
    tasks = payload.get("tasks", {})
    if not isinstance(tasks, dict):
        tasks = {}
    return {"tasks": tasks}


def save_state(root: Path, payload: dict[str, Any]) -> Path:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def normalize_paths(root: Path, paths: list[str]) -> list[str]:
    cleaned = [ownership_guard.normalize(root, path) for path in paths if str(path).strip()]
    deduped = sorted(dict.fromkeys(cleaned))
    return [path for path in deduped if path]


def role_purpose(policy: dict[str, Any], role: str) -> str:
    roles = policy.get("roles", {})
    if isinstance(roles, dict):
        payload = roles.get(role, {})
        if isinstance(payload, dict):
            purpose = str(payload.get("purpose", "")).strip()
            if purpose:
                return purpose
    defaults = {
        "explorer": "Answer a bounded codebase question without editing production files.",
        "worker": "Implement a bounded slice inside an explicit write scope.",
        "reviewer": "Inspect for bugs, regressions, and missing validation without patching the same production scope.",
    }
    return defaults.get(role, "Support the orchestrator with a bounded task.")


def role_handoff(policy: dict[str, Any], role: str) -> list[str]:
    handoff = policy.get("handoff", {})
    if isinstance(handoff, dict):
        payload = handoff.get(role, [])
        if isinstance(payload, list):
            return [str(item) for item in payload if str(item).strip()]
    defaults = {
        "explorer": ["answer", "file_references", "open_questions"],
        "worker": ["changed_files", "validations_run", "remaining_risks"],
        "reviewer": ["findings", "validations_checked", "rollback_risk"],
    }
    return defaults.get(role, [])


def forbidden_paths(policy: dict[str, Any], role: str, extra: list[str]) -> list[str]:
    defaults = policy.get("defaults", {})
    configured = []
    if isinstance(defaults, dict):
        configured = defaults.get("protected_paths", [])
    base = [str(item) for item in configured] if isinstance(configured, list) else list(PROTECTED_DEFAULTS)
    merged = list(base or PROTECTED_DEFAULTS)
    if role != "reviewer":
        merged.append(".codex/reviews/**")
    return sorted(dict.fromkeys(item for item in merged + extra if str(item).strip()))


def render_dispatch_prompt(spec: dict[str, Any]) -> str:
    lines = [
        f"Role: {spec['role']}",
        f"Owner: {spec['owner']}",
        f"Goal: {spec['goal']}",
        f"Purpose: {spec['purpose']}",
        "",
        "Operating Contract",
        f"- Mode: {spec['mode']}",
        f"- Tier: {spec['tier']}",
        f"- Complexity: {spec['complexity']}",
        f"- Read scope: {', '.join(spec['read_scope']) if spec['read_scope'] else 'none'}",
        f"- Write scope: {', '.join(spec['write_scope']) if spec['write_scope'] else 'none'}",
        f"- Forbidden paths: {', '.join(spec['forbidden_paths']) if spec['forbidden_paths'] else 'none'}",
        f"- Stop condition: {spec['stop_condition']}",
        f"- Validation: {spec['validation']}",
        "",
        "Rules",
        "- You are not alone in the codebase. Do not revert unrelated edits.",
        "- Stay inside the declared ownership boundary.",
        "- Report exact changed files and residual risks in the handoff.",
    ]
    if spec["role"] == "explorer":
        lines.append("- Do not edit production files.")
    if spec["role"] == "reviewer":
        lines.append("- Do not patch the same production scope you are reviewing.")
    lines.extend(["", "Required Handoff"])
    lines.extend(f"- {item}" for item in spec["handoff"] or ["summary"])
    if spec["conflicts"]:
        lines.extend(["", "Ownership Conflicts"])
        lines.extend(f"- {item}" for item in spec["conflicts"])
    return "\n".join(lines)


def build_spec(
    root: Path,
    *,
    role: str,
    owner: str,
    goal: str,
    read_scope: list[str],
    write_scope: list[str],
    stop_condition: str,
    validation: str,
    mode: str,
    clean_room: bool,
    forbidden: list[str],
    claim: bool,
) -> dict[str, Any]:
    policy = subagent_policy(root)
    normalized_read = normalize_paths(root, read_scope) or list(SHARED_READ_SCOPE)
    normalized_write = normalize_paths(root, write_scope)
    if role == "explorer":
        normalized_write = []
    if role == "reviewer" and not normalized_write:
        normalized_write = [".codex/reviews/**"]

    classifier_role = "orchestrator"
    if role == "worker":
        classifier_role = "worker"
    elif role == "reviewer":
        classifier_role = "reviewer"
    recommended = mode_recommender.classify(normalized_write or normalized_read, classifier_role, clean_room)
    chosen_mode = recommended["mode"] if mode == "auto" else mode

    conflicts = ownership_guard.conflict_messages(root, owner, normalized_write) if normalized_write else []
    runtime_mode = ownership_guard.runtime_mode(root)
    dispatch_status = "blocked" if conflicts and runtime_mode == "enforced" else ("advisory" if conflicts else "ready")

    claim_result = 0
    claimed = False
    if claim and normalized_write and not conflicts:
        with contextlib.redirect_stdout(io.StringIO()):
            claim_result = ownership_guard.claim_paths(root, owner, normalized_write, chosen_mode)
        claimed = claim_result == 0
    elif claim and conflicts:
        claim_result = 2 if runtime_mode == "enforced" else 1

    spec: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "owner": owner,
        "role": role,
        "goal": goal,
        "purpose": role_purpose(policy, role),
        "mode": chosen_mode,
        "recommended_mode": recommended["mode"],
        "tier": recommended["tier"],
        "complexity": recommended["complexity"],
        "read_scope": normalized_read,
        "write_scope": normalized_write,
        "forbidden_paths": forbidden_paths(policy, role, forbidden),
        "stop_condition": stop_condition,
        "validation": validation,
        "handoff": role_handoff(policy, role),
        "conflicts": conflicts,
        "dispatch_status": dispatch_status,
        "ownership_claimed": claimed,
        "ownership_claim_result": claim_result,
    }
    spec["dispatch_prompt"] = render_dispatch_prompt(spec)
    return spec


def save_spec(root: Path, spec: dict[str, Any]) -> Path:
    payload = load_state(root)
    payload["tasks"][spec["owner"]] = spec
    return save_state(root, payload)


def release_spec(root: Path, owner: str) -> int:
    payload = load_state(root)
    payload.get("tasks", {}).pop(owner, None)
    save_state(root, payload)
    with contextlib.redirect_stdout(io.StringIO()):
        ownership_guard.release_owner(root, owner)
    event_log.append_event(
        kind="subagent-plan-cleared",
        actor="orchestrator",
        summary=f"released subagent ownership for {owner}",
        stage="execution",
        root=root,
    )
    print("ok")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    root = repo_root()
    spec = build_spec(
        root,
        role=args.role,
        owner=args.owner,
        goal=args.goal.strip(),
        read_scope=args.read_scope,
        write_scope=args.write_scope,
        stop_condition=args.stop_condition.strip(),
        validation=args.validation.strip(),
        mode=args.mode,
        clean_room=args.clean_room,
        forbidden=args.forbid,
        claim=args.claim,
    )
    save_spec(root, spec)
    event_log.append_event(
        kind="subagent-plan",
        actor="orchestrator",
        summary=f"prepared {args.role} dispatch for {args.owner}",
        files=spec["write_scope"] or spec["read_scope"],
        stage="execution",
        detail={
            "role": args.role,
            "mode": spec["mode"],
            "tier": spec["tier"],
            "dispatch_status": spec["dispatch_status"],
            "ownership_claimed": spec["ownership_claimed"],
            "conflict_count": len(spec["conflicts"]),
        },
        root=root,
    )
    print(json.dumps(spec, indent=2, ensure_ascii=False))
    return 2 if spec["dispatch_status"] == "blocked" else 0


def command_status() -> int:
    root = repo_root()
    print(json.dumps(load_state(root), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--role", choices=["explorer", "worker", "reviewer"], required=True)
    plan.add_argument("--owner", required=True)
    plan.add_argument("--goal", required=True)
    plan.add_argument("--mode", choices=["auto", "local", "worktree", "cloud"], default="auto")
    plan.add_argument("--clean-room", action="store_true")
    plan.add_argument("--read-scope", action="append", default=[])
    plan.add_argument("--write-scope", action="append", default=[])
    plan.add_argument("--forbid", action="append", default=[])
    plan.add_argument("--stop-condition", default="return when the bounded task is complete")
    plan.add_argument("--validation", default="report what was verified and what remains unverified")
    plan.add_argument("--claim", action="store_true")

    sub.add_parser("status")

    release = sub.add_parser("release")
    release.add_argument("--owner", required=True)

    args = parser.parse_args()
    if args.cmd == "plan":
        return command_plan(args)
    if args.cmd == "status":
        return command_status()
    return release_spec(repo_root(), args.owner)


if __name__ == "__main__":
    raise SystemExit(main())
