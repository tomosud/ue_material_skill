"""Generate the Material Expression class manifest from an Unreal Engine checkout.

Usage:
    python tools/gen_manifest.py
    python tools/gen_manifest.py --ue-root C:/path/to/UnrealEngine
    python tools/gen_manifest.py --scan precomputed-rg-output.txt

The source root defaults to UE_SOURCE_ROOT, then to the repository's documented
UE 5.8 checkout. The tool writes catalog/manifest.json only; it does not create
task or documentation files.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "catalog" / "manifest.json"

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


def scan_declarations(engine_root: Path) -> list[str]:
    result = subprocess.run(
        [
            resolve_rg(),
            "-n",
            "--no-heading",
            "-g",
            "*.h",
            RG_PATTERN,
            "Source",
            "Plugins",
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


def build_manifest(engine_root: Path, scan_lines: list[str]) -> dict[str, dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}
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
        entries[short_name] = {
            "abstract": abstract,
            "base": base,
            "class": class_name,
            "deprecated": deprecated_flag or class_name.endswith("_DEPRECATED"),
            "header": "Engine/" + header,
            "module": module,
            "origin": origin,
        }
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

    manifest = build_manifest(engine_root, scan_lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
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
