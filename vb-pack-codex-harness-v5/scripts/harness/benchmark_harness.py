#!/usr/bin/env python3
"""Run quick v5 harness benchmarks and optional v4 comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, utc_slug, write_json


TASKS = [
    ("trivial_gate", ["scripts/harness/gate.py", "all", "--tier", "trivial", "--json"]),
    ("normal_template_gate", ["scripts/harness/gate.py", "all", "--tier", "normal", "--template", "--json"]),
    ("quality_template", ["scripts/harness/quality_gate.py", "--tier", "normal", "--template", "--json"]),
    ("implementation_template", ["scripts/harness/implementation_gate.py", "--template", "--json"]),
    ("ui_template", ["scripts/harness/ui_evidence_gate.py", "--template", "--json"]),
    ("memory_audit", ["scripts/harness/memory_guard.py", "audit", "--json"]),
]


def run_command(root: Path, command: list[str]) -> dict:
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, *command], cwd=root, text=True, capture_output=True, check=False)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
    }


def compatible_task_for_root(root: Path, task: tuple[str, list[str]]) -> tuple[str, list[str]] | None:
    name, command = task
    if (root / command[0]).exists():
        return name, command
    return None


def run_suite(root: Path, tasks: list[tuple[str, list[str]]]) -> dict:
    results = []
    for task in tasks:
        compatible = compatible_task_for_root(root, task)
        if not compatible:
            continue
        name, command = compatible
        result = run_command(root, command)
        result["name"] = name
        results.append(result)
    return {
        "root": str(root),
        "results": results,
        "total_elapsed_ms": round(sum(item["elapsed_ms"] for item in results), 2),
        "failed": [item["name"] for item in results if item["exit_code"] != 0],
    }


def compare(v5: dict, baseline: dict | None) -> dict:
    if baseline is None:
        return {"baseline_available": False, "warnings": ["no baseline root supplied"]}
    warnings: list[str] = []
    base_by_name = {item["name"]: item for item in baseline["results"]}
    comparisons = []
    for item in v5["results"]:
        base = base_by_name.get(item["name"])
        if not base:
            continue
        delta = item["elapsed_ms"] - base["elapsed_ms"]
        comparisons.append({
            "name": item["name"],
            "baseline_ms": base["elapsed_ms"],
            "v5_ms": item["elapsed_ms"],
            "delta_ms": round(delta, 2),
        })
        if item["name"] in {"trivial_gate", "normal_template_gate", "quality_template"} and delta > 750:
            warnings.append(f"{item['name']} is materially slower than baseline by {round(delta, 2)}ms")
    return {"baseline_available": True, "comparisons": comparisons, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    v5 = run_suite(ROOT, TASKS)
    baseline = run_suite(Path(args.baseline_root).resolve(), TASKS) if args.baseline_root else None
    result = {
        "schema_version": 1,
        "run_id": f"bench-{utc_slug()}",
        "v5": v5,
        "baseline": baseline,
        "comparison": compare(v5, baseline),
    }
    output = args.output or f"harness/evals/runs/{result['run_id']}.json"
    write_json(ROOT / output, result)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"v5 total: {v5['total_elapsed_ms']}ms")
        if baseline:
            print(f"baseline total: {baseline['total_elapsed_ms']}ms")
        for warning in result["comparison"].get("warnings", []):
            print(f"WARN: {warning}")
        print(output)
    has_failures = bool(v5["failed"] or result["comparison"].get("warnings"))
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
