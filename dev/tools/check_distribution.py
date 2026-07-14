#!/usr/bin/env python3
"""Validate that the tracked UE Material skill is a self-contained distribution."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPOSITORY_ROOT / "skills" / "ue-material"
REQUIRED_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "catalog/editor-evidence.json",
    "catalog/functions.json",
    "catalog/legacy-node-prose.json",
    "catalog/node-evidence.json",
    "catalog/nodes.json",
    "scripts/build.py",
    "scripts/parse.py",
    "scripts/search_catalog.py",
    "scripts/validate.py",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".json", ".md", ".py", ".yaml", ".yml"}
FORBIDDEN_TEXT = {
    "C:\\work\\script\\ue_material_skill": "local repository path",
    "C:/work/script/ue_material_skill": "local repository path",
    "dev/fixtures": "development fixture path",
    "dev/tests": "development test path",
    "examples/": "obsolete fixture path",
    "tests/fixtures/": "obsolete fixture path",
}


def relative(path: Path) -> str:
    return path.relative_to(SKILL_ROOT).as_posix()


def validate_frontmatter(text: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["SKILL.md must start with YAML frontmatter"]
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return ["SKILL.md frontmatter has no closing delimiter"]
    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.fullmatch(r"([a-z][a-z0-9_-]*):\s*(.*)", line)
        if not match:
            errors.append(f"SKILL.md has unsupported frontmatter syntax: {line!r}")
            continue
        fields[match.group(1)] = match.group(2).strip()
    if set(fields) != {"name", "description"}:
        errors.append("SKILL.md frontmatter must contain only name and description")
    if fields.get("name") != "ue-material":
        errors.append("SKILL.md frontmatter name must be ue-material")
    if not fields.get("description"):
        errors.append("SKILL.md frontmatter description must be non-empty")
    return errors


def main() -> int:
    errors: list[str] = []
    if not SKILL_ROOT.is_dir():
        print(f"error: missing skill directory: {SKILL_ROOT}")
        return 1

    files = sorted(path for path in SKILL_ROOT.rglob("*") if path.is_file())
    actual = {relative(path) for path in files}
    for required in sorted(REQUIRED_FILES - actual):
        errors.append(f"missing required distribution file: {required}")

    for path in files:
        path_name = relative(path)
        if path.is_symlink():
            errors.append(f"symlink is not allowed in the distribution: {path_name}")
        if "__pycache__" in path.parts or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"cache artifact is not allowed: {path_name}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {path_name}: {exc}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig")
        for token, label in FORBIDDEN_TEXT.items():
            if token in text:
                errors.append(f"{path_name}: contains {label}: {token}")
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
    errors.extend(validate_frontmatter(skill_text))

    if errors:
        for error in errors:
            print(f"error: {error}")
        print(f"distribution check failed with {len(errors)} error(s)")
        return 1
    print(f"distribution check passed: {len(files)} files under {SKILL_ROOT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
