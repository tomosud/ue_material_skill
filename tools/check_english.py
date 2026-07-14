#!/usr/bin/env python3
"""Enforce the reviewed CJK-debt baseline for active skill content.

Unreal identifiers are not translated. Fixtures and the inactive legacy prose
quarantine are outside the active skill scope. A reviewed English conversion
must run this tool with --update-baseline so the allowed debt only decreases.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "skill"
DEFAULT_BASELINE = PROJECT_ROOT / "catalog" / "language-baseline.json"
TEXT_SUFFIXES = {".json", ".md", ".py", ".yaml", ".yml"}
CJK_RE = re.compile(
    "["
    "\u3040-\u30ff"  # Hiragana and Katakana
    "\u3400-\u4dbf"  # CJK Extension A
    "\u4e00-\u9fff"  # CJK Unified Ideographs
    "\uf900-\ufaff"  # CJK Compatibility Ideographs
    "]"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--update-baseline", action="store_true")
    return parser.parse_args()


def active_files() -> list[Path]:
    return sorted(
        path for path in SKILL_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
    )


def scan() -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for path in active_files():
        text = path.read_text(encoding="utf-8-sig")
        matching_lines = sum(bool(CJK_RE.search(line)) for line in text.splitlines())
        matching_chars = len(CJK_RE.findall(text))
        if matching_chars:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            result[relative] = {"cjk_lines": matching_lines, "cjk_chars": matching_chars}
    return result


def load_baseline(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or not isinstance(value.get("files"), dict):
        raise ValueError(f"{path} must contain a top-level files object")
    return value


def main() -> int:
    args = parse_args()
    current = scan()
    if args.update_baseline:
        document = {
            "schema_version": 1,
            "policy": (
                "CJK text is forbidden in active skill content. Counts record temporary refactoring "
                "debt and must only decrease through reviewed English conversions."
            ),
            "scope": "skill/**/*.{json,md,py,yaml,yml}",
            "exemptions": ["examples/**", "tests/fixtures/**", "catalog/quarantine/**"],
            "files": current,
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"updated {args.baseline}: {len(current)} files, "
            f"{sum(item['cjk_chars'] for item in current.values())} CJK characters"
        )
        return 0


    baseline = load_baseline(args.baseline)
    expected = baseline["files"]
    if current != expected:
        keys = sorted(set(current) | set(expected))
        for key in keys:
            if current.get(key) != expected.get(key):
                print(f"mismatch: {key}: baseline={expected.get(key)} current={current.get(key)}")
        print("language baseline mismatch; review the change, then run with --update-baseline")
        return 1

    print(
        f"English lint baseline matches: {len(current)} debt files, "
        f"{sum(item['cjk_chars'] for item in current.values())} CJK characters"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}")
        raise SystemExit(1)
