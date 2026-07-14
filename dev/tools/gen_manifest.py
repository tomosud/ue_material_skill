"""Generate the Material Expression class manifest from an Unreal Engine checkout.

Usage:
    python dev/tools/gen_manifest.py
    python dev/tools/gen_manifest.py --ue-root C:/path/to/UnrealEngine
    python dev/tools/gen_manifest.py --scan precomputed-rg-output.txt

The source root defaults to UE_SOURCE_ROOT, then to the repository's documented
UE 5.8 checkout. The tool writes dev/catalog/manifest.json only; it does not create
task or documentation files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dev" / "catalog" / "manifest.json"

# Exclude forward declarations ending in a semicolon. Multi-line declarations
# are resolved by inspecting the following source lines.
RG_PATTERN = (
    r"^\s*class\s+([A-Z0-9_]+_API\s+)?"
    r"UMaterialExpression\w*\s*(:\s*public[^;]*)?$"
)
DECLARATION_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):\s*class\s+"
    r"(?:[A-Z0-9_]+_API\s+)?"
    r"(?P<class_name>UMaterialExpression[A-Za-z0-9_]*)\s*"
    r"(?::\s*public\s+(?P<base>[A-Za-z0-9_:]+))?\s*$"
)
IMPLEMENTATION_RG_PATTERN = r"\bUMaterialExpression[A-Za-z0-9_]+::[A-Za-z0-9_~]+"
IMPLEMENTATION_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):.*?\b"
    r"(?P<class_name>UMaterialExpression[A-Za-z0-9_]*)::[A-Za-z0-9_~]+"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ue-root",
        type=Path,
        default=Path(os.environ.get("UE_SOURCE_ROOT", DEFAULT_UE_ROOT)),
        help="Unreal Engine checkout root, or its Engine directory",
    )
    parser.add_argument(
        "--scan",
        type=Path,
        help="Read precomputed ripgrep output instead of scanning the checkout",
    )
    parser.add_argument(
        "--impl-scan",
        type=Path,
        help="Read precomputed ripgrep implementation output instead of scanning the checkout",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Manifest output path",
    )
    return parser.parse_args()


def engine_root_from(value: Path) -> Path:
    value = value.expanduser().resolve()
    return value if value.name.lower() == "engine" else value / "Engine"


def resolve_rg() -> str:
    candidates = (
        os.environ.get("RG_PATH"),
        shutil.which("rg"),
        os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\rg.exe"),
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("ripgrep was not found; set RG_PATH or pass --scan")


def scan_source(
    engine_root: Path,
    glob: str,
    pattern: str,
    roots: list[str] | None = None,
) -> list[str]:
    result = subprocess.run(
        [
            resolve_rg(),
            "-n",
            "--no-heading",
            "-g",
            glob,
            pattern,
            *(roots or ["Source", "Plugins"]),
        ],
        cwd=engine_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.splitlines()


def scan_declarations(engine_root: Path) -> list[str]:
    return scan_source(engine_root, "*.h", RG_PATTERN)


def declaration_module_roots(scan_lines: list[str]) -> list[str]:
    """Return source-module roots that own the scanned declarations."""

    roots: set[str] = set()
    for raw_line in scan_lines:
        match = DECLARATION_RE.match(raw_line.strip())
        if not match:
            continue
        parts = match.group("path").replace("\\", "/").split("/")
        try:
            source_index = parts.index("Source")
            roots.add("/".join(parts[: source_index + 2]))
        except (ValueError, IndexError):
            continue
    return sorted(roots)


def scan_implementations(engine_root: Path, declarations: list[str]) -> list[str]:
    # Scanning only modules that declare Material Expressions avoids traversing
    # every unrelated Engine plugin while still proving each class/path match.
    roots = declaration_module_roots(declarations)
    return scan_source(engine_root, "*.cpp", IMPLEMENTATION_RG_PATTERN, roots)


def normalized_source_hash(path: Path) -> str:
    """Hash source bytes after normalizing CRLF and bare CR to LF."""

    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def implementation_paths(scan_lines: list[str]) -> dict[str, str]:
    """Return only class-to-cpp mappings that are unambiguous in the scan."""

    candidates: dict[str, set[str]] = {}
    for raw_line in scan_lines:
        match = IMPLEMENTATION_RE.match(raw_line.strip())
        if not match:
            continue
        path = match.group("path").replace("\\", "/")
        if "/Intermediate/" in path:
            continue
        candidates.setdefault(match.group("class_name"), set()).add(path)
    return {
        class_name: next(iter(paths))
        for class_name, paths in candidates.items()
        if len(paths) == 1
    }


def find_base(path: Path, declaration_line: int) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines[declaration_line : declaration_line + 3]:
        match = re.search(r":\s*public\s+([A-Za-z0-9_:]+)", line)
        if match:
            return match.group(1)
    return None


def class_flags(path: Path, declaration_line: int) -> tuple[bool, bool]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    except OSError:
        return False, False
    index = declaration_line - 1
    context = "".join(lines[max(0, index - 12) : index])
    match = re.search(r"UCLASS\s*\(([^)]*)\)", context, re.DOTALL)
    flags = re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
    return bool(re.search(r"\babstract\b", flags, re.IGNORECASE)), "Deprecated" in flags


def module_and_origin(relative_header: str) -> tuple[str, str]:
    parts = relative_header.split("/")
    if parts[0] == "Source":
        return (parts[2] if len(parts) > 2 else "?", "engine")
    try:
        source_index = parts.index("Source")
        module = parts[source_index + 1]
    except (ValueError, IndexError):
        module = parts[1] if len(parts) > 1 else "Plugins"
    return module, "plugin"


def build_manifest(
    engine_root: Path,
    scan_lines: list[str],
    impl_scan_lines: list[str] | None = None,
) -> dict[str, dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}
    implementations = implementation_paths(impl_scan_lines or [])
    for raw_line in scan_lines:
        match = DECLARATION_RE.match(raw_line.strip())
        if not match:
            continue
        class_name = match.group("class_name")
        header = match.group("path").replace("\\", "/")
        declaration_line = int(match.group("line"))
        if "/Intermediate/" in header:
            continue
        base = match.group("base") or find_base(engine_root / header, declaration_line)
        if base is None:
            continue
        if class_name in entries:
            raise RuntimeError(f"duplicate Material Expression declaration: {class_name}")
        abstract, deprecated_flag = class_flags(engine_root / header, declaration_line)
        module, origin = module_and_origin(header)
        short_name = class_name.removeprefix("UMaterialExpression") or "(root)"
        entry: dict[str, object] = {
            "abstract": abstract,
            "base": base,
            "class": class_name,
            "deprecated": deprecated_flag or class_name.endswith("_DEPRECATED"),
            "header": "Engine/" + header,
            "header_hash": normalized_source_hash(engine_root / header),
            "module": module,
            "origin": origin,
        }
        implementation = implementations.get(class_name)
        if implementation is not None:
            entry["impl"] = "Engine/" + implementation
            entry["impl_hash"] = normalized_source_hash(engine_root / implementation)
        entries[short_name] = entry
    return dict(sorted(entries.items()))


def main() -> int:
    args = parse_args()
    engine_root = engine_root_from(args.ue_root)
    if not engine_root.is_dir():
        raise RuntimeError(f"Engine directory does not exist: {engine_root}")

    if args.scan:
        scan_lines = args.scan.read_text(encoding="utf-8", errors="replace").splitlines()
    else:
        scan_lines = scan_declarations(engine_root)
    if args.impl_scan:
        impl_scan_lines = args.impl_scan.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    elif args.scan:
        # A declaration fixture is commonly used without a corresponding cpp
        # fixture. Do not inspect an unrelated checkout in that mode.
        impl_scan_lines = []
    else:
        impl_scan_lines = scan_implementations(engine_root, scan_lines)

    manifest = build_manifest(engine_root, scan_lines, impl_scan_lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    classes = [entry for name, entry in manifest.items() if name != "(root)"]
    print(f"wrote {args.output}")
    print(
        "classes={classes} abstract={abstract} deprecated={deprecated} plugin={plugin}".format(
            classes=len(classes),
            abstract=sum(bool(entry["abstract"]) for entry in classes),
            deprecated=sum(bool(entry["deprecated"]) for entry in classes),
            plugin=sum(entry["origin"] == "plugin" for entry in classes),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
