#!/usr/bin/env python3
"""Evaluate classify_task.py against route fixtures."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "fixtures" / "route_fixtures.jsonl"
CLASSIFIER = ROOT / "scripts" / "classify_task.py"


def load_classifier():
    spec = importlib.util.spec_from_file_location("classify_task", CLASSIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load classifier: {CLASSIFIER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            fixture = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: invalid json: {exc}") from exc
        fixture["_lineno"] = lineno
        fixtures.append(fixture)
    return fixtures


def has_constraint(result: dict[str, Any], name: str, expected: Any) -> bool:
    constraints = result.get("constraints", {})
    if not isinstance(constraints, dict):
        return False
    return constraints.get(name) == expected


def check_fixture(classifier: Any, fixture: dict[str, Any]) -> list[str]:
    result = classifier.classify(fixture["text"])
    errors: list[str] = []

    expected_route = fixture.get("expected_route")
    if expected_route and result.get("route") != expected_route:
        errors.append(f"route expected {expected_route!r}, got {result.get('route')!r}")

    for name, expected in fixture.get("expect_constraints", {}).items():
        if not has_constraint(result, name, expected):
            got = result.get("constraints", {}).get(name) if isinstance(result.get("constraints"), dict) else None
            errors.append(f"constraint {name!r} expected {expected!r}, got {got!r}")

    skills = result.get("suggested_skills", [])
    if not isinstance(skills, list):
        errors.append("suggested_skills is not a list")
        skills = []
    for skill in fixture.get("expect_skills", []):
        if skill not in skills:
            errors.append(f"missing skill {skill!r}")
    for skill in fixture.get("forbid_skills", []):
        if skill in skills:
            errors.append(f"forbidden skill {skill!r} present")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--suite", choices=["train", "heldout", "all"], default="all")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    classifier = load_classifier()
    fixtures = load_fixtures(args.fixtures)
    if args.suite != "all":
        fixtures = [fixture for fixture in fixtures if fixture.get("suite") == args.suite]

    failures: list[dict[str, Any]] = []
    for fixture in fixtures:
        errors = check_fixture(classifier, fixture)
        if errors:
            failures.append(
                {
                    "id": fixture.get("id"),
                    "line": fixture.get("_lineno"),
                    "text": fixture.get("text"),
                    "errors": errors,
                    "result": classifier.classify(fixture["text"]),
                }
            )

    report = {
        "fixtures": len(fixtures),
        "passed": len(fixtures) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"route_eval: {report['passed']}/{report['fixtures']} passed")
        for failure in failures:
            print(f"- {failure['id']} line {failure['line']}:")
            for error in failure["errors"]:
                print(f"  - {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
