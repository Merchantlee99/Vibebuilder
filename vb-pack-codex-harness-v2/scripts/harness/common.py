"""Shared helpers for Codex Harness v2 scripts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "harness" / "runtime.json"
TIER_ORDER = {"trivial": 0, "normal": 1, "high-risk": 2}


def utc_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True) + "\n")


def tier_at_least(tier: str, minimum: str) -> bool:
    return TIER_ORDER[tier] >= TIER_ORDER[minimum]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def nonempty_section(text: str, heading: str) -> bool:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return False
    body = match.group(1).strip()
    if not body:
        return False
    placeholders = {"tbd", "todo", "n/a", "none", "-", "pending"}
    return body.lower() not in placeholders


def parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


def parse_key_value_lines(text: str, fields: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in fields:
        match = re.search(rf"^{re.escape(field)}:\s*(.*)$", text, re.MULTILINE)
        values[field] = match.group(1).strip() if match else ""
    return values


def path_list_overlap(left: list[str], right: list[str]) -> bool:
    for a in left:
        for b in right:
            a_norm = a.strip().rstrip("/")
            b_norm = b.strip().rstrip("/")
            if not a_norm or not b_norm:
                continue
            if a_norm == b_norm or a_norm.startswith(b_norm + "/") or b_norm.startswith(a_norm + "/"):
                return True
    return False

