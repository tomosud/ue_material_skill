"""Create or refresh source evidence records for Material Expression nodes.

The generator proves only class declarations automatically. It preserves manual
audit states and references from an existing output file. Schema, description,
and restriction states remain pending until a human or dedicated extractor has
inspected the relevant implementation paths.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "dev" / "catalog" / "manifest.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "skills" / "ue-material" / "catalog" / "node-evidence.json"
DEFAULT_AUDITS = REPOSITORY_ROOT / "dev" / "catalog" / "audits"
AUDIT_STATES = {"pending", "verified", "partial", "not_applicable"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ue-root",
        type=Path,
        default=Path(os.environ.get("UE_SOURCE_ROOT", DEFAULT_UE_ROOT)),
        help="Unreal Engine checkout root",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audits-dir", type=Path, default=DEFAULT_AUDITS)
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def source_version(ue_root: Path) -> dict[str, Any]:
    version_path = ue_root / "Engine" / "Build" / "Build.version"
    value = load_object(version_path)
    return {
        "major": value.get("MajorVersion"),
        "minor": value.get("MinorVersion"),
        "patch": value.get("PatchVersion"),
        "branch": value.get("BranchName"),
        "changelist": value.get("Changelist"),
    }


def declaration_is_present(path: Path, symbol: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(rf"\bclass\s+(?:[A-Z0-9_]+_API\s+)?{re.escape(symbol)}\b", text))


def reference_symbol_is_present(path: Path, symbol: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    for part in (item.strip() for item in symbol.split(" / ")):
        leaf = part.rsplit("::", 1)[-1]
        if leaf not in text:
            return False
    return True


def load_audits(directory: Path, ue_root: Path) -> dict[str, Any]:
    audits: dict[str, Any] = {}
    if not directory.exists():
        return audits
    for path in sorted(directory.glob("*.json")):
        document = load_object(path)
        for class_name, record in document.items():
            if class_name in audits:
                raise ValueError(f"duplicate audit for {class_name} in {path}")
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{class_name} must be an object")
            audit = record.get("audit")
            references = record.get("references")
            if not isinstance(audit, dict) or not isinstance(references, list):
                raise ValueError(f"{path}:{class_name} requires audit and references")
            for claim in ("declaration", "schema", "description", "restrictions"):
                if audit.get(claim) not in AUDIT_STATES:
                    raise ValueError(f"{path}:{class_name}.audit.{claim} has an invalid state")
            for index, reference in enumerate(references):
                if not isinstance(reference, dict):
                    raise ValueError(f"{path}:{class_name}.references[{index}] must be an object")
                relative_path = reference.get("path")
                symbol = reference.get("symbol")
                if not isinstance(relative_path, str) or not isinstance(symbol, str):
                    raise ValueError(f"{path}:{class_name}.references[{index}] needs path and symbol")
                source_path = ue_root / Path(relative_path)
                if not reference_symbol_is_present(source_path, symbol):
                    raise ValueError(
                        f"{path}:{class_name}: symbol {symbol!r} was not found in {source_path}"
                    )
            audits[class_name] = record
    return audits


def preserved_audit(existing: Any) -> dict[str, str]:
    default = {
        "declaration": "verified",
        "schema": "pending",
        "description": "pending",
        "restrictions": "pending",
    }
    if not isinstance(existing, dict):
        return default
    audit = existing.get("audit")
    if not isinstance(audit, dict):
        return default
    for key in default:
        value = audit.get(key)
        if value in AUDIT_STATES:
            default[key] = value
    default["declaration"] = "verified"
    return default


def preserved_references(existing: Any) -> list[dict[str, Any]]:
    if not isinstance(existing, dict) or not isinstance(existing.get("references"), list):
        return []
    return [item for item in existing["references"] if isinstance(item, dict)]


def build_records(
    ue_root: Path,
    manifest: dict[str, Any],
    existing_nodes: dict[str, Any],
    audit_overrides: dict[str, Any],
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for short_name in sorted(name for name in manifest if name != "(root)"):
        entry = manifest[short_name]
        if not isinstance(entry, dict):
            raise ValueError(f"manifest entry {short_name!r} must be an object")
        header = entry.get("header")
        symbol = entry.get("class")
        if not isinstance(header, str) or not isinstance(symbol, str):
            raise ValueError(f"manifest entry {short_name!r} lacks header/class")
        source_path = ue_root / Path(header)
        if not declaration_is_present(source_path, symbol):
            raise ValueError(f"declaration {symbol} was not found in {source_path}")

        old = audit_overrides.get(short_name, existing_nodes.get(short_name))
        references = preserved_references(old)
        canonical_header = header.replace("\\", "/")
        declaration_reference = next(
            (
                item for item in references
                if item.get("path") == canonical_header and item.get("symbol") == symbol
            ),
            None,
        )
        if declaration_reference is None:
            declaration_reference = {
                "path": canonical_header,
                "symbol": symbol,
                "claims": ["declaration"],
            }
        else:
            claims = declaration_reference.get("claims")
            claims = list(claims) if isinstance(claims, list) else []
            if "declaration" not in claims:
                claims.insert(0, "declaration")
            declaration_reference["claims"] = claims
        references = [item for item in references if item is not declaration_reference]
        references.insert(0, declaration_reference)
        records[short_name] = {
            "audit": preserved_audit(old),
            "references": references,
        }
    return records


def main() -> int:
    args = parse_args()
    ue_root = args.ue_root.expanduser().resolve()
    manifest = load_object(args.manifest)
    existing = load_object(args.output)
    existing_nodes = existing.get("nodes", {}) if isinstance(existing.get("nodes"), dict) else {}
    audit_overrides = load_audits(args.audits_dir, ue_root)
    unknown_audits = sorted(set(audit_overrides) - (set(manifest) - {"(root)"}))
    if unknown_audits:
        raise ValueError(f"audit fragments contain unknown classes: {unknown_audits}")
    records = build_records(ue_root, manifest, existing_nodes, audit_overrides)
    document = {
        "schema_version": 1,
        "source": {
            "root_env": "UE_SOURCE_ROOT",
            "paths": "source_relative",
            "read_only": True,
            "version": source_version(ue_root),
        },
        "audit_states": sorted(AUDIT_STATES),
        "nodes": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {args.output} with {len(records)} node evidence records "
        f"from {len(audit_overrides)} maintained audits"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
