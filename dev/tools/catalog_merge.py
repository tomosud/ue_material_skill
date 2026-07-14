#!/usr/bin/env python3
"""Merge and lint generated UE MaterialExpression catalogs.

Standard-library only. The script deliberately normalizes worker naming mistakes
through manifest data, but reports every normalization on stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from extract_node_aliases import AliasError, extract_alias_map, load_legacy
from semantics_schema import (
    SemanticsError,
    render_description,
    validate_formula_references,
    validate_semantics,
)


AUDIT_STATES = {"pending", "verified", "stale", "not_applicable"}
SKILL_VERSION = "1.0.0"
UE_VERSION = "5.8.0"
UE_BRANCH = "UE5"
GENERATED_AT = "2026-07-15T00:00:00Z"


class CatalogError(Exception):
    pass


def duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle, object_pairs_hook=duplicate_guard)
    except (OSError, json.JSONDecodeError, CatalogError) as exc:
        raise CatalogError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"{path}: top-level value must be an object")
    return value


def load_audits(directory: Path) -> dict[str, Any]:
    """Load maintained audit fragments, rejecting duplicate class ownership."""

    if not directory.is_dir():
        raise CatalogError(f"audit directory does not exist: {directory}")
    audits: dict[str, Any] = {}
    for path in sorted(directory.glob("*.json")):
        for class_name, record in load_json(path).items():
            if class_name in audits:
                raise CatalogError(f"duplicate audit for {class_name} in {path}")
            audits[class_name] = record
    return audits


def _reference_identities(record: Any) -> list[tuple[str, str, tuple[str, ...]]]:
    if not isinstance(record, dict) or not isinstance(record.get("references"), list):
        return []
    identities = []
    for reference in record["references"]:
        if not isinstance(reference, dict):
            continue
        claims = reference.get("claims")
        identities.append(
            (
                str(reference.get("path", "")),
                str(reference.get("symbol", "")),
                tuple(sorted(str(claim) for claim in claims))
                if isinstance(claims, list)
                else (),
            )
        )
    return identities


def validate_audit_sync(audits: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    """Ensure maintained audits and the packaged evidence cannot silently drift."""

    errors: list[str] = []
    for class_name, audit_record in sorted(audits.items()):
        evidence_record = evidence.get(class_name)
        if not isinstance(audit_record, dict):
            errors.append(f"audit:{class_name}: expected object")
            continue
        if not isinstance(evidence_record, dict):
            errors.append(f"audit:{class_name}: missing from node evidence")
            continue
        for field in ("audit", "semantics"):
            if audit_record.get(field) != evidence_record.get(field):
                errors.append(f"audit:{class_name}.{field}: differs from node evidence")
        audit_identities = _reference_identities(audit_record)
        evidence_identities = [
            identity
            for identity in _reference_identities(evidence_record)
            if identity[2] != ("declaration",)
        ]
        if audit_identities != evidence_identities:
            errors.append(
                f"audit:{class_name}.references: identity differs from node evidence"
            )
    return errors


def strip_cpp_prefix(name: str) -> str:
    if len(name) > 1 and name[0] in "UAIF" and name[1].isupper():
        return name[1:]
    return name


def short_from_class_name(name: str) -> str:
    name = strip_cpp_prefix(name.rsplit(".", 1)[-1])
    return name.removeprefix("MaterialExpression")


def canonical_class_path(manifest_entry: dict[str, Any]) -> str:
    module = manifest_entry.get("module")
    cpp_class = manifest_entry.get("class")
    if not isinstance(module, str) or not module:
        raise CatalogError(f"manifest entry has invalid module: {manifest_entry!r}")
    if not isinstance(cpp_class, str) or not cpp_class:
        raise CatalogError(f"manifest entry has invalid class: {manifest_entry!r}")
    return f"/Script/{module}.{strip_cpp_prefix(cpp_class)}"


def resolve_manifest_key(
    raw_key: str, entry: dict[str, Any], manifest: dict[str, Any]
) -> str | None:
    candidates = [raw_key, short_from_class_name(raw_key)]
    class_path = entry.get("class")
    if isinstance(class_path, str):
        candidates.append(short_from_class_name(class_path))
    for candidate in candidates:
        if candidate in manifest and candidate != "(root)":
            return candidate
    return None


def require_type(
    errors: list[str], path: str, value: Any, expected: type | tuple[type, ...]
) -> None:
    if not isinstance(value, expected):
        if isinstance(expected, tuple):
            expected_name = " or ".join(item.__name__ for item in expected)
        else:
            expected_name = expected.__name__
        errors.append(f"{path}: expected {expected_name}, got {type(value).__name__}")


def validate_pin_array(errors: list[str], path: str, value: Any, kind: str) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: expected array")
        return
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path}: expected object")
            continue
        if "name" not in item or not isinstance(item.get("name"), str):
            errors.append(f"{item_path}.name: required string")
        if kind in {"inputs", "prop_pins"}:
            if "prop" in item and (
                not isinstance(item.get("prop"), str) or not item.get("prop")
            ):
                errors.append(f"{item_path}.prop: expected non-empty string")
        if kind == "inputs" and "required" in item and not isinstance(item["required"], bool):
            errors.append(f"{item_path}.required: expected bool")
        if kind == "prop_pins":
            if "kind" in item and item.get("kind") not in {"Primary", "Advanced"}:
                errors.append(f"{item_path}.kind: expected Primary or Advanced")
            if "type" in item and (
                not isinstance(item.get("type"), str) or not item.get("type")
            ):
                errors.append(f"{item_path}.type: expected non-empty string")


def validate_node_entry(key: str, entry: Any, source: Path) -> list[str]:
    errors: list[str] = []
    base = f"{source}:{key}"
    if not isinstance(entry, dict):
        return [f"{base}: expected object"]
    if not isinstance(entry.get("class"), str) or not entry.get("class"):
        errors.append(f"{base}.class: required non-empty string")
    if "desc" in entry and not isinstance(entry.get("desc"), str):
        errors.append(f"{base}.desc: expected string")
    if "header" in entry and not isinstance(entry["header"], str):
        errors.append(f"{base}.header: expected string")
    for flag in ("abstract", "deprecated", "is_parameter"):
        if flag in entry and not isinstance(entry[flag], bool):
            errors.append(f"{base}.{flag}: expected bool")
    if entry.get("abstract") or entry.get("deprecated"):
        return errors
    for field in ("inputs", "prop_pins", "outputs"):
        if field in entry:
            validate_pin_array(errors, f"{base}.{field}", entry[field], field)
    props = entry.get("props")
    if props is not None and not isinstance(props, dict):
        errors.append(f"{base}.props: expected object")
    elif isinstance(props, dict):
        for prop_name, spec in props.items():
            prop_path = f"{base}.props.{prop_name}"
            if not isinstance(spec, dict):
                errors.append(f"{prop_path}: expected object")
            elif not isinstance(spec.get("type"), str) or not spec.get("type"):
                errors.append(f"{prop_path}.type: required non-empty string")
    if "notes" in entry and not isinstance(entry.get("notes"), str):
        errors.append(f"{base}.notes: expected string")
    aliases = entry.get("aliases")
    if aliases is not None and (
        not isinstance(aliases, list)
        or any(not isinstance(alias, str) or not alias for alias in aliases)
    ):
        errors.append(f"{base}.aliases: expected an array of non-empty strings")
    return errors


def normalize_node_entry(
    key: str, raw_entry: dict[str, Any], source: Path, warnings: list[str]
) -> dict[str, Any]:
    """Fill legacy worker omissions without concealing invalid field types."""

    entry = dict(raw_entry)

    def default(field: str, value: Any) -> None:
        if field not in entry or entry[field] is None or (
            field == "desc" and entry[field] == ""
        ):
            entry[field] = value
            warnings.append(f"{source.name}:{key}: defaulted missing {field}")

    # Never infer a description from the class name. Descriptions require
    # explicit source evidence in node-evidence.json.
    default("desc", "")
    default("inputs", [])
    default("prop_pins", [])
    default("outputs", [])
    default("props", {})
    default("notes", "")
    default("aliases", [])
    props = entry.get("props") if isinstance(entry.get("props"), dict) else {}
    if entry.get("is_parameter") and isinstance(props, dict):
        inherited_parameter_props = {
            "ParameterName": {"type": "FName", "default": "Param"},
            "ExpressionGUID": {"type": "FGuid", "default": None},
            "Group": {"type": "FName", "default": ""},
            "SortPriority": {"type": "int32", "default": 32},
        }
        for prop_name, prop_spec in inherited_parameter_props.items():
            if prop_name not in props:
                props[prop_name] = prop_spec
                warnings.append(
                    f"{source.name}:{key}: inherited parameter prop {prop_name}"
                )
        parameter_name = props.get("ParameterName")
        if isinstance(parameter_name, dict) and parameter_name.get("default") == "":
            parameter_name["default"] = "Param"
        entry["props"] = props
    for field in ("inputs", "prop_pins"):
        pins = entry.get(field)
        if not isinstance(pins, list):
            continue
        normalized_pins: list[Any] = []
        for index, raw_pin in enumerate(pins):
            if not isinstance(raw_pin, dict):
                normalized_pins.append(raw_pin)
                continue
            pin = dict(raw_pin)
            if not pin.get("prop"):
                pin["prop"] = pin.get("name") or f"Input{index}"
                warnings.append(
                    f"{source.name}:{key}.{field}[{index}]: inferred prop={pin['prop']!r}"
                )
            if field == "inputs":
                pin.setdefault("required", False)
            else:
                pin.setdefault("kind", "Primary")
                prop_spec = props.get(pin["prop"], {})
                inferred_type = (
                    prop_spec.get("type", "raw")
                    if isinstance(prop_spec, dict)
                    else "raw"
                )
                if not pin.get("type"):
                    pin["type"] = inferred_type
                    warnings.append(
                        f"{source.name}:{key}.{field}[{index}]: "
                        f"inferred type={inferred_type!r}"
                    )
            normalized_pins.append(pin)
        entry[field] = normalized_pins
    return entry


MF_TYPES = {"S", "V2", "V3", "V4", "T2d", "TCube", "T2dArr", "TVol", "SB", "MA", "TExt", "B", "Stra"}


def validate_function_entry(key: str, entry: Any, source: Path) -> list[str]:
    errors: list[str] = []
    base = f"{source}:{key}"
    if not isinstance(entry, dict):
        return [f"{base}: expected object"]
    if not isinstance(entry.get("path"), str) or not entry.get("path"):
        errors.append(f"{base}.path: required non-empty string")
    for field in ("desc", "usage"):
        if field in entry and not isinstance(entry.get(field), str):
            errors.append(f"{base}.{field}: expected string")
    for flag in ("path_uncertain",):
        if flag in entry and not isinstance(entry.get(flag), bool):
            errors.append(f"{base}.{flag}: expected bool")
    for direction in ("inputs", "outputs"):
        pins = entry.get(direction)
        if not isinstance(pins, list):
            errors.append(f"{base}.{direction}: required array")
            continue
        for index, pin in enumerate(pins):
            pin_path = f"{base}.{direction}[{index}]"
            if not isinstance(pin, dict):
                errors.append(f"{pin_path}: expected object")
                continue
            if not isinstance(pin.get("name"), str) or not pin.get("name"):
                errors.append(f"{pin_path}.name: required non-empty string")
            if pin.get("type") not in MF_TYPES:
                errors.append(f"{pin_path}.type: expected one of {sorted(MF_TYPES)}")
            if direction == "inputs" and "required" in pin and not isinstance(pin["required"], bool):
                errors.append(f"{pin_path}.required: expected bool")
            if "id" in pin and not re.fullmatch(r"[0-9A-Fa-f]{32}", str(pin["id"])):
                errors.append(f"{pin_path}.id: expected 32 hex digits")
    return errors


def merge_nodes(
    files: list[Path],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    aliases: dict[str, list[str]] | None = None,
) -> tuple[OrderedDict[str, Any], list[str], list[str]]:
    merged: dict[str, Any] = {}
    warnings: list[str] = []
    errors: list[str] = []
    for source in files:
        document = load_json(source)
        for raw_key, raw_entry in document.items():
            errors.extend(validate_node_entry(raw_key, raw_entry, source))
            if not isinstance(raw_entry, dict):
                continue
            key = resolve_manifest_key(raw_key, raw_entry, manifest)
            if key is None:
                errors.append(f"{source}:{raw_key}: class is not present in manifest")
                continue
            if key in merged:
                errors.append(f"{source}:{raw_key}: duplicate class after normalization: {key}")
                continue
            entry = normalize_node_entry(key, raw_entry, source, warnings)
            canonical = canonical_class_path(manifest[key])
            if raw_key != key:
                warnings.append(f"{source.name}: normalized key {raw_key!r} -> {key!r}")
            if entry.get("class") != canonical:
                warnings.append(
                    f"{source.name}:{key}: normalized class {entry.get('class')!r} -> {canonical!r}"
                )
            entry["class"] = canonical
            entry["header"] = str(manifest[key].get("header", ""))
            entry["abstract"] = bool(manifest[key].get("abstract", entry.get("abstract", False)))
            entry["deprecated"] = bool(manifest[key].get("deprecated", entry.get("deprecated", False)))
            entry["plugin"] = manifest[key].get("origin") == "plugin"
            entry["aliases"] = list((aliases or {}).get(key, []))
            evidence_record = evidence.get(key)
            semantics = (
                evidence_record.get("semantics")
                if isinstance(evidence_record, dict)
                else None
            )
            if semantics is not None:
                try:
                    validate_semantics(semantics)
                    input_pins = [
                        pin
                        for pin in entry.get("inputs", [])
                        if isinstance(pin, dict)
                    ]
                    input_order = [
                        pin["name"]
                        for pin in input_pins
                        if isinstance(pin.get("name"), str)
                    ]
                    formula_input_names = input_order + [
                        pin["prop"]
                        for pin in input_pins
                        if isinstance(pin.get("prop"), str)
                    ]
                    property_names = (
                        entry.get("props", {}).keys()
                        if isinstance(entry.get("props"), dict)
                        else ()
                    )
                    validate_formula_references(
                        semantics["formula"], formula_input_names, property_names
                    )
                    entry["semantics"] = semantics
                    entry["desc"] = render_description(semantics, input_order)
                except SemanticsError as exc:
                    errors.append(f"node evidence:{key}.semantics: {exc}")
            entry.pop("verified", None)
            merged[key] = entry
    expected = set(manifest) - {"(root)"}
    actual = set(merged)
    for key in sorted(expected - actual):
        errors.append(f"coverage: missing manifest class {key}")
    for key in sorted(actual - expected):
        errors.append(f"coverage: unexpected class {key}")
    return OrderedDict((key, merged[key]) for key in sorted(merged)), warnings, errors


def merge_functions(
    files: list[Path], warnings: list[str]
) -> tuple[OrderedDict[str, Any], list[str]]:
    merged: dict[str, Any] = {}
    errors: list[str] = []
    paths: dict[str, str] = {}
    for source in files:
        document = load_json(source)
        for key, entry in document.items():
            errors.extend(validate_function_entry(key, entry, source))
            if key in merged:
                errors.append(f"{source}:{key}: duplicate function name")
                continue
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                path = entry["path"]
                if path in paths:
                    errors.append(f"{source}:{key}: duplicate function path also used by {paths[path]}")
                paths[path] = key
            if isinstance(entry, dict):
                entry = dict(entry)
                entry.setdefault("desc", "")
                entry.setdefault("usage", "")
                if "path_uncertain" not in entry:
                    entry["path_uncertain"] = False
                    warnings.append(
                        f"{source.name}:{key}: defaulted missing path_uncertain=false"
                    )
                entry.pop("verified", None)
            merged[key] = entry
    return OrderedDict((key, merged[key]) for key in sorted(merged)), errors


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    """Hash canonical LF bytes so Git checkout policy cannot change release identity."""
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def build_metadata(catalog_root: Path, meta_path: Path) -> OrderedDict[str, Any]:
    hashes = OrderedDict(
        (path.relative_to(catalog_root).as_posix(), sha256_file(path))
        for path in sorted(
            catalog_root.rglob("*.json"),
            key=lambda item: item.relative_to(catalog_root).as_posix(),
        )
        if path.resolve() != meta_path.resolve()
    )
    return OrderedDict(
        (
            ("skill_version", SKILL_VERSION),
            ("ue_version", UE_VERSION),
            ("ue_branch", UE_BRANCH),
            ("generated_at", GENERATED_AT),
            ("catalog_hashes", hashes),
        )
    )


def validate_evidence(
    evidence: dict[str, Any], manifest: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    records = evidence.get("nodes")
    if not isinstance(records, dict):
        return {}, ["node evidence: top-level 'nodes' must be an object"]
    expected = set(manifest) - {"(root)"}
    actual = set(records)
    for key in sorted(expected - actual):
        errors.append(f"node evidence: missing class {key}")
    for key in sorted(actual - expected):
        errors.append(f"node evidence: unexpected class {key}")
    for key in sorted(expected & actual):
        record = records[key]
        if not isinstance(record, dict):
            errors.append(f"node evidence:{key}: expected object")
            continue
        audit = record.get("audit")
        references = record.get("references")
        if not isinstance(audit, dict):
            errors.append(f"node evidence:{key}.audit: expected object")
            continue
        for claim in ("declaration", "schema", "description", "restrictions"):
            if audit.get(claim) not in AUDIT_STATES:
                errors.append(
                    f"node evidence:{key}.audit.{claim}: expected one of {sorted(AUDIT_STATES)}"
                )
        if audit.get("declaration") != "verified":
            errors.append(f"node evidence:{key}: declaration must be verified")
        semantics = record.get("semantics")
        if semantics is not None:
            try:
                validate_semantics(semantics)
            except SemanticsError as exc:
                errors.append(f"node evidence:{key}.semantics: {exc}")
        elif audit.get("description") == "verified":
            errors.append(
                f"node evidence:{key}: verified description requires semantics"
            )
        if not isinstance(references, list) or not references:
            errors.append(f"node evidence:{key}.references: required non-empty array")
            continue
        covered_claims: set[str] = set()
        for index, reference in enumerate(references):
            path = f"node evidence:{key}.references[{index}]"
            if not isinstance(reference, dict):
                errors.append(f"{path}: expected object")
                continue
            if not isinstance(reference.get("path"), str) or not reference.get("path"):
                errors.append(f"{path}.path: required non-empty string")
            if not isinstance(reference.get("symbol"), str) or not reference.get("symbol"):
                errors.append(f"{path}.symbol: required non-empty string")
            claims = reference.get("claims")
            if not isinstance(claims, list) or not claims:
                errors.append(f"{path}.claims: required non-empty array")
            else:
                covered_claims.update(str(claim) for claim in claims)
        for claim, state in audit.items():
            if state == "verified" and claim not in covered_claims:
                errors.append(
                    f"node evidence:{key}: verified {claim!r} has no reference claiming it"
                )
    return records, errors


def write_index(path: Path, nodes: OrderedDict[str, Any]) -> None:
    lines = [
        "# Material Expression Index",
        "",
        "This entry point covers `catalog/nodes.json`; `search_catalog.py` joins source references and legacy wording.",
        "This file is generated by repository maintenance tooling; do not edit it manually.",
        f"Coverage: all {len(nodes)} declared classes in one searchable catalog; nodes are not split by audit status.",
        "",
        "Use `python scripts/search_catalog.py <terms>` for descriptions, source symbols, Pins, properties,",
        "plugins, and legacy Japanese or English wording. Use `--class`, `--pin`, `--property`, or `--evidence`",
        "for exact filtering. Results return node information together with field-level `provenance`.",
        "Before explaining or using a node, inspect its references in the configured Unreal Engine source root.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    dev_root = root / "dev"
    skill_root = root / "skills" / "ue-material"
    parser.add_argument("--generated-dir", type=Path, default=dev_root / "catalog" / "generated")
    parser.add_argument("--manifest", type=Path, default=dev_root / "catalog" / "manifest.json")
    parser.add_argument("--output", type=Path, default=skill_root / "catalog" / "nodes.json")
    parser.add_argument("--functions-output", type=Path, default=skill_root / "catalog" / "functions.json")
    parser.add_argument("--meta-output", type=Path, default=skill_root / "catalog" / "meta.json")
    parser.add_argument("--index", type=Path, default=skill_root / "references" / "nodes-index.md")
    parser.add_argument("--evidence", type=Path, default=skill_root / "catalog" / "node-evidence.json")
    parser.add_argument(
        "--audits-dir",
        type=Path,
        default=dev_root / "catalog" / "audits",
        help="Maintained audit fragments which must match packaged node evidence",
    )
    parser.add_argument(
        "--legacy-prose",
        type=Path,
        default=skill_root / "catalog" / "legacy-node-prose.json",
        help="Inactive legacy prose used only to derive deterministic search aliases",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = load_json(args.manifest)
        aliases = extract_alias_map(load_legacy(args.legacy_prose))
        evidence_document = load_json(args.evidence)
        evidence, evidence_errors = validate_evidence(evidence_document, manifest)
        audits = load_audits(args.audits_dir)
        audit_sync_errors = validate_audit_sync(audits, evidence)
        node_files = sorted(args.generated_dir.glob("C[0-9][0-9].json"))
        function_files = sorted(args.generated_dir.glob("M[0-9][0-9]-mf.json"))
        if not node_files:
            raise CatalogError(f"no CXX.json files found in {args.generated_dir}")
        nodes, warnings, node_errors = merge_nodes(
            node_files, manifest, evidence, aliases
        )
        functions, function_errors = merge_functions(function_files, warnings)
        errors = node_errors + function_errors + evidence_errors + audit_sync_errors
        if not args.quiet:
            for warning in warnings:
                print(f"warning: {warning}", file=sys.stderr)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            print(f"catalog merge failed with {len(errors)} error(s)", file=sys.stderr)
            return 1
        write_json(args.output, nodes)
        write_json(args.functions_output, functions)
        write_index(args.index, nodes)
        write_json(args.meta_output, build_metadata(args.meta_output.parent, args.meta_output))
        if not args.quiet:
            total = len(nodes)
            expected = len(manifest) - (1 if "(root)" in manifest else 0)
            abstract = sum(bool(item.get("abstract")) for item in nodes.values())
            deprecated = sum(bool(item.get("deprecated")) for item in nodes.values())
            source_schema = sum(
                record.get("audit", {}).get("schema") == "verified"
                for record in evidence.values() if isinstance(record, dict)
            )
            source_descriptions = sum(
                record.get("audit", {}).get("description") == "verified"
                for record in evidence.values() if isinstance(record, dict)
            )
            plugins = sum(bool(item.get("plugin")) for item in nodes.values())
            coverage = 100.0 * total / expected if expected else 100.0
            print(
                f"nodes={total} manifest={expected} coverage={coverage:.1f}% "
                f"abstract={abstract} deprecated={deprecated} plugin={plugins} "
                f"source_schema={source_schema} source_descriptions={source_descriptions}"
            )
            print(f"functions={len(functions)}")
            print(f"normalizations={len(warnings)}")
            print(f"wrote {args.output}")
            print(f"wrote {args.functions_output}")
            print(f"wrote {args.index}")
            print(f"wrote {args.meta_output}")
        return 0
    except (CatalogError, AliasError, SemanticsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
