#!/usr/bin/env python3
"""Static frontend inventory for CSS, Tailwind, token drift, and layout-risk hints."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from common import ROOT, write_json
from event_log import record_event


FRONTEND_SUFFIXES = {".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte", ".html"}
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB_RE = re.compile(r"\brgba?\([^)]+\)")
ARBITRARY_TAILWIND_RE = re.compile(r"\b[a-zA-Z0-9_:-]+-\[[^\]]+\]")
CLASS_RE = re.compile(r"class(?:Name)?=[\"']([^\"']+)[\"']")
TOKEN_CLASSES = {
    "spacing": re.compile(r"^(?:p|m|gap|space|inset|top|right|bottom|left|w|h|min-w|max-w|min-h|max-h)-"),
    "radius": re.compile(r"^rounded"),
    "text": re.compile(r"^text-"),
    "color": re.compile(r"^(?:bg|text|border|ring|fill|stroke)-"),
}


def target_files(paths: list[str]) -> list[Path]:
    if paths:
        candidates = [ROOT / path for path in paths]
    else:
        candidates = [path for path in ROOT.rglob("*") if path.is_file()]
    files = []
    for path in candidates:
        if path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file() and item.suffix in FRONTEND_SUFFIXES)
        elif path.is_file() and path.suffix in FRONTEND_SUFFIXES:
            files.append(path)
    return sorted(set(files))


def audit_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    classes: list[str] = []
    for match in CLASS_RE.finditer(text):
        classes.extend(part for part in match.group(1).split() if part)
    token_counts = {
        name: Counter(cls for cls in classes if pattern.search(cls))
        for name, pattern in TOKEN_CLASSES.items()
    }
    return {
        "path": str(path.relative_to(ROOT)),
        "hex_values": sorted(set(HEX_RE.findall(text))),
        "rgb_values": sorted(set(RGB_RE.findall(text))),
        "arbitrary_tailwind": sorted(set(ARBITRARY_TAILWIND_RE.findall(text))),
        "class_count": len(classes),
        "token_samples": {name: counter.most_common(12) for name, counter in token_counts.items()},
    }


def summarize(items: list[dict]) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    hex_total = sum(len(item["hex_values"]) for item in items)
    rgb_total = sum(len(item["rgb_values"]) for item in items)
    arbitrary_total = sum(len(item["arbitrary_tailwind"]) for item in items)
    if hex_total or rgb_total:
        warnings.append("raw color values found; prefer project tokens when available")
    if arbitrary_total:
        warnings.append("arbitrary Tailwind values found; verify they are intentional")
    return {
        "files_scanned": len(items),
        "raw_hex_count": hex_total,
        "raw_rgb_count": rgb_total,
        "arbitrary_tailwind_count": arbitrary_total,
        "items": items,
    }, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    files = target_files(args.paths)
    items = [audit_file(path) for path in files]
    payload, warnings = summarize(items)
    if args.output:
        write_json(ROOT / args.output, payload)
    record_event("frontend_static.audit", actor="harness", status="warning" if warnings else "ok", warnings=warnings, files=len(files))
    if args.json:
        print(json.dumps({"ok": True, "warnings": warnings, **payload}, indent=2, ensure_ascii=False))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        print(f"scanned {len(files)} frontend files")
        if args.output:
            print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
