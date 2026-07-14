"""Create or refresh source evidence records for Material Expression nodes.

The generator proves only class declarations automatically. It preserves manual
audit states and references from an existing output file. Schema, description,
and restriction states remain pending until a human or dedicated extractor has
inspected the relevant implementation paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from semantics_schema import SemanticsError, validate_semantics
from source_symbols import source_file_has_symbol


DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "dev" / "catalog" / "manifest.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "skills" / "ue-material" / "catalog" / "node-evidence.json"
DEFAULT_AUDITS = REPOSITORY_ROOT / "dev" / "catalog" / "audits"
AUDIT_STATES = {"pending", "verified", "stale", "not_applicable"}
SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


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


def normalized_source_hash(path: Path) -> str:
    """Hash source bytes after normalizing CRLF and bare CR to LF."""

    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def reference_symbol_is_present(path: Path, symbol: str) -> bool:
    return source_file_has_symbol(path, symbol)


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
            semantics = record.get("semantics")
            if semantics is not None:
                try:
                    validate_semantics(semantics)
                except SemanticsError as exc:
                    raise ValueError(
                        f"{path}:{class_name}.semantics: {exc}"
                    ) from exc
            elif audit.get("description") == "verified":
                raise ValueError(
                    f"{path}:{class_name}: verified description requires semantics"
                )
            for index, reference in enumerate(references):
                if not isinstance(reference, dict):
                    raise ValueError(f"{path}:{class_name}.references[{index}] must be an object")
                relative_path = reference.get("path")
                symbol = reference.get("symbol")
                if not isinstance(relative_path, str) or not isinstance(symbol, str):
                    raise ValueError(f"{path}:{class_name}.references[{index}] needs path and symbol")
                recorded_hash = reference.get("source_hash")
                if recorded_hash is not None and (
                    not isinstance(recorded_hash, str)
                    or SOURCE_HASH_RE.fullmatch(recorded_hash) is None
                ):
                    raise ValueError(
                        f"{path}:{class_name}.references[{index}].source_hash must be SHA-256"
                    )
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


def has_maintained_claims(existing: Any) -> bool:
    """Return whether a record carries review state beyond generated declaration data."""

    audit = existing.get("audit") if isinstance(existing, dict) else None
    if not isinstance(audit, dict):
        return False
    return any(
        audit.get(claim) not in {None, "pending"}
        for claim in ("schema", "description", "restrictions")
    )


def preserved_references(existing: Any) -> list[dict[str, Any]]:
    if not isinstance(existing, dict) or not isinstance(existing.get("references"), list):
        return []
    return [dict(item) for item in existing["references"] if isinstance(item, dict)]


def preserved_semantics(existing: Any) -> dict[str, Any] | None:
    if not isinstance(existing, dict) or not isinstance(existing.get("semantics"), dict):
        return None
    semantics = dict(existing["semantics"])
    validate_semantics(semantics)
    return semantics


def reference_key(reference: dict[str, Any]) -> tuple[Any, Any]:
    return reference.get("path"), reference.get("symbol")


def attach_source_hashes(
    ue_root: Path,
    references: list[dict[str, Any]],
    existing: Any,
    maintained_audit: bool,
) -> set[str]:
    """Attach recorded hashes and return verified claims whose source is stale.

    Maintained audit hashes describe the source snapshot that was inspected. On
    mismatch that recorded hash is retained, so stale evidence cannot silently
    become verified merely by running the generator a second time.
    """

    existing_hashes = {
        reference_key(item): item.get("source_hash")
        for item in preserved_references(existing)
        if isinstance(item.get("source_hash"), str)
        and SOURCE_HASH_RE.fullmatch(item["source_hash"])
    }
    stale_claims: set[str] = set()
    for reference in references:
        relative_path = reference.get("path")
        if not isinstance(relative_path, str):
            raise ValueError("evidence reference lacks a source path")
        source_path = ue_root / Path(relative_path)
        if not source_path.is_file():
            raise ValueError(f"evidence source does not exist: {source_path}")
        current_hash = normalized_source_hash(source_path)
        recorded_hash = reference.get("source_hash")
        if not (
            isinstance(recorded_hash, str)
            and SOURCE_HASH_RE.fullmatch(recorded_hash)
        ):
            recorded_hash = existing_hashes.get(reference_key(reference))
        if not maintained_audit or not isinstance(recorded_hash, str):
            recorded_hash = current_hash
        reference["source_hash"] = recorded_hash
        if maintained_audit and recorded_hash != current_hash:
            claims = reference.get("claims")
            if isinstance(claims, list):
                # Declaration presence is freshly verified by this generator.
                stale_claims.update(str(claim) for claim in claims if claim != "declaration")
    return stale_claims


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

        existing_record = existing_nodes.get(short_name)
        maintained_audit = (
            short_name in audit_overrides or has_maintained_claims(existing_record)
        )
        old = audit_overrides.get(short_name, existing_record)
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
        stale_claims = attach_source_hashes(
            ue_root,
            references,
            existing_nodes.get(short_name),
            maintained_audit,
        )
        audit = preserved_audit(old)
        for claim in stale_claims:
            if audit.get(claim) == "verified":
                audit[claim] = "stale"
        record = {
            "audit": audit,
            "references": references,
        }
        semantics = preserved_semantics(old)
        if semantics is not None:
            record["semantics"] = semantics
        records[short_name] = record
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
        "schema_version": 2,
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
        newline="\n",
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
