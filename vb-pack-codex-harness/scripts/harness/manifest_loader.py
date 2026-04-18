#!/usr/bin/env python3
"""Minimal YAML loader and schema helpers for the harness manifests.

This parser intentionally supports only the subset used in this repository:
  - nested mappings
  - lists of scalar values
  - scalar values: strings, ints, booleans
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class Line:
    indent: int
    content: str
    number: int


class ManifestError(ValueError):
    """Raised when a manifest cannot be parsed or validated."""


def _tokenize(text: str) -> list[Line]:
    lines: list[Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2 != 0:
            raise ManifestError(f"line {number}: indentation must use 2-space steps")
        lines.append(Line(indent=indent, content=raw.strip(), number=number))
    return lines


def _parse_scalar(raw: str):
    value = raw.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _split_key_value(content: str, number: int) -> tuple[str, str]:
    if ":" not in content:
        raise ManifestError(f"line {number}: expected key:value entry")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise ManifestError(f"line {number}: empty key")
    return key, value.strip()


def _parse_block(lines: list[Line], index: int, indent: int):
    if index >= len(lines):
        return {}, index
    if lines[index].indent != indent:
        raise ManifestError(
            f"line {lines[index].number}: expected indent {indent}, got {lines[index].indent}"
        )

    if lines[index].content.startswith("- "):
        items: list[object] = []
        while index < len(lines) and lines[index].indent == indent and lines[index].content.startswith("- "):
            raw = lines[index].content[2:].strip()
            if not raw:
                raise ManifestError(f"line {lines[index].number}: nested lists are not supported")
            if ":" in raw:
                raise ManifestError(f"line {lines[index].number}: lists of mappings are not supported")
            items.append(_parse_scalar(raw))
            index += 1
        return items, index

    mapping: dict[str, object] = {}
    while index < len(lines) and lines[index].indent == indent and not lines[index].content.startswith("- "):
        key, raw_value = _split_key_value(lines[index].content, lines[index].number)
        if raw_value == "":
            next_index = index + 1
            if next_index < len(lines) and lines[next_index].indent > indent:
                child, index = _parse_block(lines, next_index, indent + 2)
                mapping[key] = child
            else:
                mapping[key] = ""
                index = next_index
        else:
            mapping[key] = _parse_scalar(raw_value)
            index += 1
    return mapping, index


def loads(text: str):
    lines = _tokenize(text)
    if not lines:
        return {}
    data, index = _parse_block(lines, 0, lines[0].indent)
    if index != len(lines):
        raise ManifestError(f"unparsed trailing content starting at line {lines[index].number}")
    return data


def load(path: Path):
    return loads(path.read_text(encoding="utf-8"))


def expect_type(value, expected_type, label: str) -> None:
    if not isinstance(value, expected_type):
        raise ManifestError(f"{label}: expected {expected_type.__name__}, got {type(value).__name__}")

