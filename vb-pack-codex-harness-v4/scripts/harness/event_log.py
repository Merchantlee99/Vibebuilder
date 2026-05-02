#!/usr/bin/env python3
"""Append-only event and learning logs for Codex Harness v4."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import unicodedata

from common import ROOT, append_jsonl, event_id, load_json, utc_slug, write_json


EVENTS_PATH = ROOT / "harness" / "telemetry" / "events.jsonl"
LEARNINGS_PATH = ROOT / "harness" / "telemetry" / "learnings.jsonl"
LOCK_PATH = ROOT / "harness" / "telemetry" / "events.lock"
MANIFEST_PATH = ROOT / "harness" / "telemetry" / "events.manifest.json"
SEGMENTS_DIR = ROOT / "harness" / "telemetry" / "segments"
ACTIVE_REL = "harness/telemetry/events.jsonl"


@contextmanager
def event_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+", encoding="utf-8") as lock:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except ImportError:
            fcntl = None
        try:
            yield
        finally:
            if "fcntl" in locals() and fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def record_event(kind: str, actor: str = "harness", status: str = "ok", **data) -> dict:
    with event_lock():
        manifest = load_manifest()
        prev_hash = latest_chain_hash(manifest)
        event = {
            "id": event_id(kind),
            "ts": utc_slug(),
            "kind": kind,
            "actor": actor,
            "status": status,
            "data": data,
            "prev_hash": prev_hash,
        }
        event["hash"] = event_hash(event)
        append_jsonl(EVENTS_PATH, event)
        update_active_manifest(manifest)
        return event


def record_learning(summary: str, source_event: str = "", severity: str = "info", **data) -> dict:
    with event_lock():
        learning = {
            "id": event_id("learning"),
            "ts": utc_slug(),
            "summary": summary,
            "source_event": source_event,
            "severity": severity,
            "data": data,
        }
        append_jsonl(LEARNINGS_PATH, learning)
        return learning


def tail(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    items = []
    for line in lines:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"invalid": line})
    return items


def event_sources() -> list[Path]:
    manifest = load_manifest()
    sources = []
    for segment in manifest.get("segments", []):
        rel_path = segment.get("path", "")
        if rel_path:
            sources.append(ROOT / rel_path)
    sources.append(EVENTS_PATH)
    return sources


def iter_events() -> list[dict]:
    events = []
    for path in event_sources():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def canonical_event(event: dict) -> str:
    body = {key: value for key, value in event.items() if key != "hash"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return unicodedata.normalize("NFC", canonical)


def event_hash(event: dict) -> str:
    return hashlib.sha256(canonical_event(event).encode("utf-8")).hexdigest()


def latest_hash(path: Path) -> str:
    if not path.exists():
        return ""
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            return json.loads(line).get("hash", "")
        except json.JSONDecodeError:
            return ""
    return ""


def latest_chain_hash(manifest: dict | None = None) -> str:
    active_hash = latest_hash(EVENTS_PATH)
    if active_hash:
        return active_hash
    manifest = manifest if manifest is not None else load_manifest()
    active = manifest.get("active", {})
    if active.get("last_hash"):
        return active["last_hash"]
    segments = manifest.get("segments", [])
    if segments:
        return segments[-1].get("last_hash", "")
    return ""


def load_manifest() -> dict:
    manifest = load_json(MANIFEST_PATH, {})
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.setdefault("schema_version", 1)
    manifest.setdefault("segments", [])
    manifest.setdefault("active", {
        "path": ACTIVE_REL,
        "event_count": 0,
        "first_hash": "",
        "last_hash": "",
        "updated_at": "",
    })
    return manifest


def event_file_stats(path: Path, expected_prev: str = "") -> tuple[dict, list[str], str]:
    errors: list[str] = []
    prev = expected_prev
    first_hash = ""
    last_hash = expected_prev
    count = 0
    if not path.exists():
        return {
            "event_count": 0,
            "first_hash": "",
            "last_hash": expected_prev,
            "size_bytes": 0,
        }, errors, expected_prev

    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)} line {idx}: invalid json: {exc}")
            continue
        if event.get("prev_hash", "") != prev:
            errors.append(f"{path.relative_to(ROOT)} line {idx}: prev_hash mismatch")
        expected = event_hash(event)
        if event.get("hash") != expected:
            errors.append(f"{path.relative_to(ROOT)} line {idx}: hash mismatch")
        current_hash = event.get("hash", "")
        if not first_hash:
            first_hash = current_hash
        last_hash = current_hash
        prev = current_hash
        count += 1

    return {
        "event_count": count,
        "first_hash": first_hash,
        "last_hash": last_hash if count else expected_prev,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }, errors, prev


def update_active_manifest(manifest: dict | None = None) -> None:
    manifest = manifest if manifest is not None else load_manifest()
    base_prev = manifest.get("segments", [])[-1].get("last_hash", "") if manifest.get("segments") else ""
    stats, _, _ = event_file_stats(EVENTS_PATH, expected_prev=base_prev)
    active = {
        "path": ACTIVE_REL,
        "event_count": stats["event_count"],
        "first_hash": stats["first_hash"],
        "last_hash": "" if stats["event_count"] == 0 else stats["last_hash"],
        "base_prev_hash": base_prev,
        "size_bytes": stats["size_bytes"],
        "updated_at": utc_slug(),
    }
    manifest["active"] = active
    write_json(MANIFEST_PATH, manifest)


def verify_manifest_segments(manifest: dict) -> tuple[list[str], str]:
    errors: list[str] = []
    prev = ""
    for idx, segment in enumerate(manifest.get("segments", []), start=1):
        rel_path = segment.get("path", "")
        path = ROOT / rel_path
        if not rel_path or not path.exists():
            errors.append(f"segment {idx}: missing file {rel_path or '<empty>'}")
            continue
        stats, file_errors, prev = event_file_stats(path, expected_prev=prev)
        errors.extend(file_errors)
        for key in ["event_count", "first_hash", "last_hash", "size_bytes"]:
            if segment.get(key) != stats.get(key):
                errors.append(f"segment {idx}: {key} mismatch")
    return errors, prev


def verify_events() -> tuple[bool, list[str]]:
    errors = []
    manifest = load_manifest()
    segment_errors, prev = verify_manifest_segments(manifest)
    errors.extend(segment_errors)

    active_stats, active_errors, active_last = event_file_stats(EVENTS_PATH, expected_prev=prev)
    errors.extend(active_errors)
    active = manifest.get("active", {})
    if MANIFEST_PATH.exists():
        expected_active = {
            "event_count": active_stats["event_count"],
            "first_hash": active_stats["first_hash"],
            "last_hash": "" if active_stats["event_count"] == 0 else active_stats["last_hash"],
            "size_bytes": active_stats["size_bytes"],
        }
        for key, value in expected_active.items():
            if active.get(key) != value:
                errors.append(f"active: {key} mismatch")
        if active.get("base_prev_hash", "") != prev:
            errors.append("active: base_prev_hash mismatch")
    _ = active_last
    return not errors, errors


def rotate_events(args: argparse.Namespace) -> int:
    with event_lock():
        if not EVENTS_PATH.exists() or not EVENTS_PATH.read_text(encoding="utf-8").strip():
            print("no events to rotate")
            return 0
        if args.max_bytes and EVENTS_PATH.stat().st_size < args.max_bytes and not args.force:
            print("rotation skipped")
            return 0

        ok, errors = verify_events()
        if not ok:
            for error in errors:
                print(f"ERROR: {error}")
            return 1

        manifest = load_manifest()
        base_prev = manifest.get("segments", [])[-1].get("last_hash", "") if manifest.get("segments") else ""
        stats, _, _ = event_file_stats(EVENTS_PATH, expected_prev=base_prev)
        SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        suffix = stats["last_hash"][:12] if stats["last_hash"] else "empty"
        segment = SEGMENTS_DIR / f"events-{utc_slug()}-{suffix}.jsonl"
        os.replace(EVENTS_PATH, segment)
        EVENTS_PATH.write_text("", encoding="utf-8")

        segment_meta = {
            "path": str(segment.relative_to(ROOT)),
            "rotated_at": utc_slug(),
            **stats,
        }
        manifest.setdefault("segments", []).append(segment_meta)
        manifest["active"] = {
            "path": ACTIVE_REL,
            "event_count": 0,
            "first_hash": "",
            "last_hash": "",
            "base_prev_hash": stats["last_hash"],
            "size_bytes": 0,
            "updated_at": utc_slug(),
        }
        write_json(MANIFEST_PATH, manifest)
        print(str(segment.relative_to(ROOT)))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    event = sub.add_parser("event")
    event.add_argument("--kind", required=True)
    event.add_argument("--actor", default="harness")
    event.add_argument("--status", default="ok")
    event.add_argument("--data-json", default="{}")

    learning = sub.add_parser("learning")
    learning.add_argument("--summary", required=True)
    learning.add_argument("--source-event", default="")
    learning.add_argument("--severity", choices=["info", "warning", "error"], default="info")
    learning.add_argument("--data-json", default="{}")

    show = sub.add_parser("tail")
    show.add_argument("--log", choices=["events", "learnings"], default="events")
    show.add_argument("--limit", type=int, default=20)

    sub.add_parser("verify")

    rotate = sub.add_parser("rotate")
    rotate.add_argument("--max-bytes", type=int, default=0)
    rotate.add_argument("--force", action="store_true")

    args = parser.parse_args()
    if args.command == "event":
        data = json.loads(args.data_json)
        print(json.dumps(record_event(args.kind, args.actor, args.status, **data), indent=2))
        return 0
    if args.command == "learning":
        data = json.loads(args.data_json)
        print(json.dumps(record_learning(args.summary, args.source_event, args.severity, **data), indent=2))
        return 0
    if args.command == "tail":
        path = EVENTS_PATH if args.log == "events" else LEARNINGS_PATH
        print(json.dumps(tail(path, args.limit), indent=2))
        return 0
    if args.command == "verify":
        ok, errors = verify_events()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
        print("event log ok" if ok else "event log corrupted")
        return 0 if ok else 1
    if args.command == "rotate":
        return rotate_events(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
