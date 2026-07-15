#!/usr/bin/env python3
"""Compare a resolved Unreal Engine source root against the catalog baseline fingerprint.

The bundled catalog was source-verified against one engine baseline. This tool reads
Engine/Build/Build.version from the resolved source root, derives a version|branch
fingerprint, and compares it with the baseline recorded in catalog/node-evidence.json.

The check is advisory. A version or branch mismatch means the resolved root is a
different engine line, so catalog facts must be re-audited against that source before
they are trusted. Changelist and git commit differ legitimately between a GitHub source
release and a launcher promoted build of the same version, so they are reported for
audit but do not gate the result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def normalize_branch(name: Any) -> Any:
    """Reduce a Build.version BranchName to its engine stream (e.g. ++UE5+Release-5.8 -> UE5)."""
    if not isinstance(name, str) or not name:
        return name
    text = name.strip()
    if text.startswith("++"):
        text = text[2:]
    return text.split("+", 1)[0]


def read_build_version(ue_root: Path) -> dict[str, Any]:
    value = load_object(ue_root / "Engine" / "Build" / "Build.version")
    return {
        "major": value.get("MajorVersion"),
        "minor": value.get("MinorVersion"),
        "patch": value.get("PatchVersion"),
        "branch": normalize_branch(value.get("BranchName")),
        "changelist": value.get("Changelist"),
    }


def fingerprint(version: dict[str, Any]) -> str | None:
    """Mechanical version|branch key used to detect a different engine line."""
    major, minor, patch = version.get("major"), version.get("minor"), version.get("patch")
    branch = version.get("branch")
    if None in (major, minor, patch) or not branch:
        return None
    return f"{major}.{minor}.{patch}|{branch}"


def resolve_root(args_root: Path | None) -> Path | None:
    if args_root:
        return args_root.expanduser()
    setting = Path.cwd() / ".ue-material" / "settings.json"
    if setting.is_file():
        try:
            root = load_object(setting).get("ueSourceRoot")
        except (OSError, ValueError, json.JSONDecodeError):
            root = None
        if isinstance(root, str) and root:
            return Path(root).expanduser()
    env = os.environ.get("UE_SOURCE_ROOT")
    return Path(env).expanduser() if env else None


def baseline_source() -> dict[str, Any]:
    document = load_object(skill_root() / "catalog" / "node-evidence.json")
    source = document.get("source")
    if not isinstance(source, dict):
        raise ValueError("node-evidence.json is missing a source block")
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ue-root", type=Path, help="Unreal Engine checkout root to check")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    args = parser.parse_args(argv)

    source = baseline_source()
    base_fingerprint = source.get("fingerprint")

    root = resolve_root(args.ue_root)
    if root is None:
        print(
            "error: no source root resolved (pass --ue-root, set .ue-material/settings.json, "
            "or UE_SOURCE_ROOT)",
            file=sys.stderr,
        )
        return 1
    root = root.resolve()
    if not (root / "Engine" / "Build" / "Build.version").is_file():
        print(f"error: {root} is not an Unreal Engine checkout (no Engine/Build/Build.version)", file=sys.stderr)
        return 1

    version = read_build_version(root)
    resolved_fingerprint = fingerprint(version)
    compatible = (
        resolved_fingerprint is not None
        and base_fingerprint is not None
        and resolved_fingerprint == base_fingerprint
    )

    report = {
        "root": str(root),
        "baseline_fingerprint": base_fingerprint,
        "baseline_git_commit": source.get("git_commit"),
        "resolved_fingerprint": resolved_fingerprint,
        "resolved_changelist": version.get("changelist"),
        "compatible": compatible,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"root      {report['root']}")
        print(f"baseline  {base_fingerprint}  (commit {source.get('git_commit')})")
        print(f"resolved  {resolved_fingerprint}  (CL {version.get('changelist')})")
        if compatible:
            print("result    COMPATIBLE: engine line matches the catalog baseline")
        else:
            print(
                "result    WARNING: engine line differs from the catalog baseline; "
                "re-audit source before trusting catalog facts"
            )
    return 0 if compatible else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
