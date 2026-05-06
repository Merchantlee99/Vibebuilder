#!/usr/bin/env python3
"""Append and verify v5 evidence records."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from common import ROOT, append_jsonl, event_id, utc_slug
from event_log import record_event


EVIDENCE_PATH = ROOT / "harness" / "evidence" / "evidence.jsonl"
VALID_KINDS = {
    "command",
    "runtime",
    "visual",
    "accessibility",
    "layout",
    "review",
    "risk",
    "learning",
    "static-frontend",
}
VALID_STATUS = {"pass", "fail", "warning", "not-applicable"}
VALID_TIERS = {"trivial", "normal", "high-risk"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_from_arg(raw: str) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if ":" in raw:
        artifact_type, path_value = raw.split(":", 1)
    else:
        artifact_type, path_value = "artifact", raw
    path = Path(path_value)
    if path.is_absolute():
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            errors.append(f"artifact path must be inside harness root: {path}")
            rel_path = str(path)
        else:
            rel_path = str(rel)
    else:
        rel_path = str(path)
        path = ROOT / path
    artifact = {
        "type": artifact_type.strip() or "artifact",
        "path": rel_path,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else "",
    }
    if not path.exists():
        errors.append(f"artifact does not exist: {rel_path}")
    return artifact, errors


def parse_changed_files(values: list[str]) -> list[str]:
    files: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                files.append(item)
    return files


def load_records(path: Path = EVIDENCE_PATH) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    if not path.exists():
        return records, errors
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}:{line_no}: invalid json: {exc}")
            continue
        records.append(record)
    return records, errors


def validate_record(record: dict, line_label: str = "record") -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "id", "task_id", "kind", "tier", "status", "actor", "summary"]
    for key in required:
        if key not in record or record.get(key) in {"", None}:
            errors.append(f"{line_label}: missing {key}")
    if record.get("kind") not in VALID_KINDS:
        errors.append(f"{line_label}: invalid kind {record.get('kind')}")
    if record.get("status") not in VALID_STATUS:
        errors.append(f"{line_label}: invalid status {record.get('status')}")
    if record.get("tier") not in VALID_TIERS:
        errors.append(f"{line_label}: invalid tier {record.get('tier')}")
    if record.get("status") == "not-applicable" and not record.get("not_applicable_reason"):
        errors.append(f"{line_label}: not-applicable requires not_applicable_reason")
    if record.get("kind") == "visual" and not record.get("artifacts") and not record.get("no_screenshot_reason"):
        errors.append(f"{line_label}: visual evidence without artifacts requires no_screenshot_reason")

    artifacts = record.get("artifacts", [])
    if artifacts is None:
        artifacts = []
    if not isinstance(artifacts, list):
        errors.append(f"{line_label}: artifacts must be a list")
        return errors
    for idx, artifact in enumerate(artifacts, start=1):
        prefix = f"{line_label}: artifact {idx}"
        rel = artifact.get("path", "") if isinstance(artifact, dict) else ""
        if not rel:
            errors.append(f"{prefix}: missing path")
            continue
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{prefix}: missing file {rel}")
            continue
        expected = artifact.get("sha256", "")
        if expected and path.is_file() and sha256_file(path) != expected:
            errors.append(f"{prefix}: sha256 mismatch")
    return errors


def records_for_task(task_id: str, path: Path = EVIDENCE_PATH) -> tuple[list[dict], list[str]]:
    records, errors = load_records(path)
    if task_id:
        records = [record for record in records if record.get("task_id") == task_id]
    return records, errors


def append_record(args: argparse.Namespace) -> int:
    artifacts: list[dict] = []
    errors: list[str] = []
    for raw in args.artifact:
        artifact, artifact_errors = artifact_from_arg(raw)
        artifacts.append(artifact)
        errors.extend(artifact_errors)

    record = {
        "schema_version": 1,
        "id": args.id or event_id("ev"),
        "ts": utc_slug(),
        "task_id": args.task_id,
        "kind": args.kind,
        "tier": args.tier,
        "status": args.status,
        "actor": args.actor,
        "cwd": str(ROOT),
        "changed_files": parse_changed_files(args.changed_file),
        "command": args.evidence_command_text,
        "exit_code": args.exit_code,
        "route": args.route,
        "viewport": args.viewport,
        "state": args.state,
        "artifacts": artifacts,
        "redacted": args.redacted,
        "no_screenshot_reason": args.no_screenshot_reason,
        "summary": args.summary,
        "not_applicable_reason": args.not_applicable_reason,
        "residual_risk": args.residual_risk,
    }
    errors.extend(validate_record(record, "new record"))
    if errors and not args.allow_invalid:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    append_jsonl(EVIDENCE_PATH, record)
    record_event("evidence.append", actor=args.actor, status=args.status, task_id=args.task_id, evidence_kind=args.kind)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def verify(args: argparse.Namespace) -> int:
    records, errors = load_records(ROOT / args.path if args.path else EVIDENCE_PATH)
    for idx, record in enumerate(records, start=1):
        errors.extend(validate_record(record, f"line {idx}"))
    if args.task_id and not any(record.get("task_id") == args.task_id for record in records):
        errors.append(f"no evidence for task_id: {args.task_id}")
    payload = {"ok": not errors, "records": len(records), "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("PASS" if payload["ok"] else "FAIL")
    return 0 if payload["ok"] else 1


def show(args: argparse.Namespace) -> int:
    records, errors = records_for_task(args.task_id)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.kind:
        records = [record for record in records if record.get("kind") == args.kind]
    if args.limit:
        records = records[-args.limit :]
    print(json.dumps(records, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("append")
    add.add_argument("--id", default="")
    add.add_argument("--task-id", required=True)
    add.add_argument("--kind", choices=sorted(VALID_KINDS), required=True)
    add.add_argument("--tier", choices=sorted(VALID_TIERS), default="normal")
    add.add_argument("--status", choices=sorted(VALID_STATUS), default="pass")
    add.add_argument("--actor", default="main-codex")
    add.add_argument("--changed-file", action="append", default=[])
    add.add_argument("--command", dest="evidence_command_text", default="")
    add.add_argument("--exit-code", type=int)
    add.add_argument("--route", default="")
    add.add_argument("--viewport", default="")
    add.add_argument("--state", default="")
    add.add_argument("--artifact", action="append", default=[])
    add.add_argument("--redacted", action="store_true")
    add.add_argument("--no-screenshot-reason", default="")
    add.add_argument("--summary", required=True)
    add.add_argument("--not-applicable-reason", default="")
    add.add_argument("--residual-risk", default="")
    add.add_argument("--allow-invalid", action="store_true")

    check = sub.add_parser("verify")
    check.add_argument("--task-id", default="")
    check.add_argument("--path", default="")
    check.add_argument("--json", action="store_true")

    ls = sub.add_parser("list")
    ls.add_argument("--task-id", default="")
    ls.add_argument("--kind", choices=sorted(VALID_KINDS))
    ls.add_argument("--limit", type=int, default=0)

    args = parser.parse_args()
    if args.command == "append":
        return append_record(args)
    if args.command == "verify":
        return verify(args)
    if args.command == "list":
        return show(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
