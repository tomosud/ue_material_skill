#!/usr/bin/env python3
"""Validate that the tracked UE Material skill is a self-contained distribution."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPOSITORY_ROOT / "skills" / "ue-material"
CATALOG_ROOT = SKILL_ROOT / "catalog"
REQUIRED_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "catalog/editor-evidence.json",
    "catalog/functions.json",
    "catalog/legacy-node-prose.json",
    "catalog/meta.json",
    "catalog/node-evidence.json",
    "catalog/nodes.json",
    "scripts/build.py",
    "scripts/parse.py",
    "scripts/search_catalog.py",
    "scripts/validate.py",
}
METADATA_FIELDS = {
    "skill_version",
    "ue_version",
    "ue_branch",
    "generated_at",
    "catalog_hashes",
}
SEMVER_PATTERN = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
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


def sha256_file(path: Path) -> str:
    """Hash canonical LF bytes so Git checkout policy cannot change release identity."""
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def validate_metadata(catalog_root: Path = CATALOG_ROOT) -> list[str]:
    errors: list[str] = []
    meta_path = catalog_root / "meta.json"
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid metadata catalog/meta.json: {exc}"]
    if not isinstance(metadata, dict):
        return ["catalog/meta.json: top-level value must be an object"]

    if set(metadata) != METADATA_FIELDS:
        missing = sorted(METADATA_FIELDS - set(metadata))
        extra = sorted(set(metadata) - METADATA_FIELDS)
        errors.append(f"catalog/meta.json: metadata fields differ: missing={missing} extra={extra}")
    skill_version = metadata.get("skill_version")
    if not isinstance(skill_version, str) or not SEMVER_PATTERN.fullmatch(skill_version):
        errors.append("catalog/meta.json: skill_version must be SemVer")
    ue_version = metadata.get("ue_version")
    if not isinstance(ue_version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", ue_version):
        errors.append("catalog/meta.json: ue_version must have major.minor.patch form")
    if not isinstance(metadata.get("ue_branch"), str) or not metadata["ue_branch"].strip():
        errors.append("catalog/meta.json: ue_branch must be a non-empty string")
    generated_at = metadata.get("generated_at")
    if not isinstance(generated_at, str):
        errors.append("catalog/meta.json: generated_at must be a UTC timestamp")
    else:
        try:
            datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("catalog/meta.json: generated_at must use YYYY-MM-DDTHH:MM:SSZ")

    hashes = metadata.get("catalog_hashes")
    if not isinstance(hashes, dict):
        errors.append("catalog/meta.json: catalog_hashes must be an object")
        return errors
    catalog_files = sorted(
        (
            path.relative_to(catalog_root).as_posix(),
            path,
        )
        for path in catalog_root.rglob("*.json")
        if path.resolve() != meta_path.resolve()
    )
    expected_names = [name for name, _ in catalog_files]
    if list(hashes) != expected_names:
        errors.append(
            "catalog/meta.json: catalog_hashes keys must exactly match sorted catalog JSON files: "
            f"expected={expected_names} actual={list(hashes)}"
        )
    for name, path in catalog_files:
        declared = hashes.get(name)
        if not isinstance(declared, str) or not SHA256_PATTERN.fullmatch(declared):
            errors.append(f"catalog/meta.json: invalid SHA-256 for {name}")
            continue
        actual = sha256_file(path)
        if declared != actual:
            errors.append(
                f"catalog/meta.json: SHA-256 mismatch for {name}: "
                f"expected={declared} actual={actual}"
            )
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
    errors.extend(validate_metadata())

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
