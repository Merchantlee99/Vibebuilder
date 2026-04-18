#!/usr/bin/env python3
"""mcp_audit.py — List MCP servers, their permission scope, and recent use.

Reads:
  .claude/mcp.json             (optional project-local MCP config)
  .claude/settings.local.json  (permissions.allow / .deny)
  .claude/events.jsonl         (frequency from Gate ⑨ hits + tool calls)

Output:
  table: server | configured | allowed-tools | denied-tools | recent-calls |
         gate-9-hits

Usage:
  python3 scripts/harness/mcp_audit.py                # human table
  python3 scripts/harness/mcp_audit.py --json         # JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _parse_tool_pattern(pat: str) -> tuple[str, str] | None:
    """Extract (server, tool) from 'mcp__server__tool' or 'mcp__server__*'."""
    m = re.match(r"mcp__([^_]+(?:_[^_]+)*)__(.+)", pat)
    if not m:
        return None
    return m.group(1), m.group(2)


def collect() -> dict:
    mcp_cfg = _load_json(REPO_ROOT / ".claude" / "mcp.json")
    settings = _load_json(REPO_ROOT / ".claude" / "settings.local.json")

    configured_servers = set()
    if isinstance(mcp_cfg.get("mcpServers"), dict):
        configured_servers = {k for k in mcp_cfg["mcpServers"] if not k.startswith("_")}

    allow = (settings.get("permissions", {}) or {}).get("allow", []) or []
    deny = (settings.get("permissions", {}) or {}).get("deny", []) or []

    allow_by_server: dict[str, list[str]] = defaultdict(list)
    deny_by_server: dict[str, list[str]] = defaultdict(list)
    for entry in allow:
        p = _parse_tool_pattern(entry)
        if p:
            allow_by_server[p[0]].append(p[1])
    for entry in deny:
        p = _parse_tool_pattern(entry)
        if p:
            deny_by_server[p[0]].append(p[1])

    calls_by_server: dict[str, int] = defaultdict(int)
    gate9_by_server: dict[str, int] = defaultdict(int)
    events_log = REPO_ROOT / ".claude" / "events.jsonl"
    if events_log.exists():
        try:
            for line in events_log.read_text(encoding="utf-8").splitlines()[-5000:]:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                f = e.get("file", "") or ""
                tool = (e.get("detail") or {}).get("tool", "") or f
                if tool.startswith("mcp__"):
                    parts = tool.split("__", 2)
                    server = parts[1] if len(parts) >= 2 else "?"
                    calls_by_server[server] += 1
                    if e.get("gate") == "09":
                        gate9_by_server[server] += 1
        except OSError:
            pass

    all_servers = sorted(
        configured_servers
        | set(allow_by_server)
        | set(deny_by_server)
        | set(calls_by_server)
    )

    rows = []
    for s in all_servers:
        rows.append({
            "server": s,
            "configured": s in configured_servers,
            "allow": sorted(set(allow_by_server.get(s, []))),
            "deny": sorted(set(deny_by_server.get(s, []))),
            "recent_calls": calls_by_server.get(s, 0),
            "gate9_hits": gate9_by_server.get(s, 0),
        })
    return {"rows": rows,
            "mcp_json_exists": (REPO_ROOT / ".claude" / "mcp.json").exists()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    data = collect()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if not data["mcp_json_exists"]:
        print("  note: .claude/mcp.json not present "
              "(copy from templates/mcp.template.json to enable)\n")
    if not data["rows"]:
        print("  (no MCP servers configured or used)")
        return 0

    header = f"  {'server':<24} {'cfg':<4} {'allow':<6} {'deny':<6} {'calls':<7} {'g9':<4}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in data["rows"]:
        allow_n = len(r["allow"])
        deny_n = len(r["deny"])
        cfg = "yes" if r["configured"] else "no"
        print(f"  {r['server']:<24} {cfg:<4} {allow_n:<6} {deny_n:<6} "
              f"{r['recent_calls']:<7} {r['gate9_hits']:<4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
