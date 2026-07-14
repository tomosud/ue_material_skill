#!/usr/bin/env python3
"""Validate Material Expression semantics against catalog and source evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from extract_expression_facts import extract_document
from semantics_schema import SemanticsError, render_description, validate_semantics
from source_symbols import source_file_has_symbol


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
DEFAULT_CATALOG = REPOSITORY_ROOT / "skills" / "ue-material" / "catalog" / "nodes.json"
DEFAULT_EVIDENCE = (
    REPOSITORY_ROOT / "skills" / "ue-material" / "catalog" / "node-evidence.json"
)
DEFAULT_MANIFEST = REPOSITORY_ROOT / "dev" / "catalog" / "manifest.json"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def normalized_source_hash(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _input_map(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inputs = entry.get("inputs")
    if not isinstance(inputs, list):
        return {}
    return {
        pin["name"]: pin
        for pin in inputs
        if isinstance(pin, dict) and isinstance(pin.get("name"), str)
    }


def _restriction_references(
    restrictions: list[Any], input_names: set[str], property_names: set[str]
) -> list[str]:
    errors: list[str] = []
    for index, restriction in enumerate(restrictions):
        if not isinstance(restriction, dict):
            continue
        for field, raw_value in restriction.items():
            if field == "material_property":
                continue
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            if field in {"input", "pin", "inputs", "pins"} or field.endswith(
                ("_input", "_pin", "_inputs", "_pins")
            ):
                for value in values:
                    if isinstance(value, str) and value not in input_names:
                        errors.append(
                            f"restrictions[{index}].{field} references unknown input {value!r}"
                        )
            if field in {"property", "properties"} or field.endswith(
                ("_property", "_properties")
            ):
                for value in values:
                    if isinstance(value, str) and value not in property_names:
                        errors.append(
                            f"restrictions[{index}].{field} references unknown property {value!r}"
                        )
    return errors


def validate_node_semantics(name: str, entry: Any) -> list[str]:
    prefix = f"{name}: "
    if not isinstance(entry, dict):
        return [prefix + "catalog entry must be an object"]
    semantics = entry.get("semantics")
    try:
        validate_semantics(semantics)
    except SemanticsError as error:
        return [prefix + str(error)]

    errors: list[str] = []
    inputs = _input_map(entry)
    props = entry.get("props")
    property_names = set(props) if isinstance(props, dict) else set()
    defaults = semantics["unconnected_defaults"]
    required_inputs = {
        restriction.get("input")
        for restriction in semantics["restrictions"]
        if isinstance(restriction, dict) and restriction.get("kind") == "required_input"
    }
    for input_name, default in defaults.items():
        if input_name not in inputs:
            errors.append(prefix + f"default references unknown input {input_name!r}")
        if not default.startswith("$") and default not in property_names:
            errors.append(prefix + f"default references unknown property {default!r}")
    for input_name, pin in inputs.items():
        default_prop = pin.get("default_prop")
        if isinstance(default_prop, str) and default_prop:
            if input_name in required_inputs:
                continue
            if defaults.get(input_name) != default_prop:
                errors.append(
                    prefix
                    + f"input {input_name!r} default_prop is {default_prop!r}, "
                    + "but semantics does not match"
                )
        elif input_name in defaults and not defaults[input_name].startswith("$"):
            errors.append(
                prefix + f"input {input_name!r} has a semantic property default but no default_prop"
            )
    errors.extend(
        prefix + error
        for error in _restriction_references(
            semantics["restrictions"], set(inputs), property_names
        )
    )
    expected_description = render_description(semantics, inputs)
    if entry.get("desc") != expected_description:
        errors.append(prefix + "desc is not the deterministic semantics rendering")
    return errors


def _safe_source_path(ue_root: Path, relative: str) -> Path | None:
    if Path(relative).is_absolute():
        return None
    root = ue_root.resolve()
    candidate = (root / Path(relative)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _symbol_present(path: Path, symbol: str) -> bool:
    return source_file_has_symbol(path, symbol)


def validate_references(
    name: str, ue_root: Path, evidence_record: Any
) -> list[str]:
    prefix = f"{name}: "
    if not isinstance(evidence_record, dict):
        return [prefix + "source evidence record is missing"]
    references = evidence_record.get("references")
    if not isinstance(references, list) or not references:
        return [prefix + "source evidence references must be a non-empty array"]
    errors: list[str] = []
    for index, reference in enumerate(references):
        location = prefix + f"references[{index}]"
        if not isinstance(reference, dict):
            errors.append(location + " must be an object")
            continue
        relative = reference.get("path")
        symbol = reference.get("symbol")
        source_hash = reference.get("source_hash")
        if not isinstance(relative, str) or not relative:
            errors.append(location + ".path must be a non-empty relative path")
            continue
        path = _safe_source_path(ue_root, relative)
        if path is None:
            errors.append(location + ".path escapes --ue-root")
            continue
        if not path.is_file():
            errors.append(location + f" source does not exist: {relative}")
            continue
        if not isinstance(symbol, str) or not symbol or not _symbol_present(path, symbol):
            errors.append(location + f" symbol was not found: {symbol!r}")
        if not isinstance(source_hash, str) or _HASH_RE.fullmatch(source_hash) is None:
            errors.append(location + ".source_hash must be lowercase SHA-256")
        elif source_hash != normalized_source_hash(path):
            errors.append(location + ".source_hash does not match source")
    return errors


def _literal(value: str) -> Any:
    stripped = value.strip()
    color_match = re.fullmatch(
        r"FLinearColor\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\)]+)\s*\)",
        stripped,
    )
    if color_match is not None:
        channels = [_literal(item) for item in color_match.groups()]
        if all(isinstance(item, (int, float)) for item in channels):
            return dict(zip(("r", "g", "b", "a"), channels))
    text_match = re.fullmatch(r'TEXT\("(?P<value>(?:\\.|[^"\\])*)"\)', stripped, re.DOTALL)
    if text_match is not None:
        return bytes(text_match.group("value"), "utf-8").decode("unicode_escape")
    if stripped in {"true", "false"}:
        return stripped == "true"
    if stripped in {"nullptr", "NULL"}:
        return None
    if stripped == "INDEX_NONE":
        return -1
    if "::" in stripped and re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)+", stripped
    ):
        return stripped.rsplit("::", 1)[-1]
    number = stripped.rstrip("fF")
    try:
        return float(number) if "." in number else int(number)
    except ValueError:
        return stripped


def validate_draft(name: str, entry: dict[str, Any], draft: Any) -> list[str]:
    prefix = f"{name}: draft "
    if not isinstance(draft, dict) or draft.get("draft") is not True:
        return [prefix + "record is missing or is not marked draft"]
    semantic_draft = draft.get("semantic_draft")
    if semantic_draft != {"operation": None, "formula": None}:
        return [prefix + "must leave operation and formula null"]
    facts = draft.get("facts")
    if not isinstance(facts, dict):
        return [prefix + "facts must be an object"]
    errors: list[str] = []
    for field in ("inputs", "properties", "constructor_assignments", "output_definitions"):
        if not isinstance(facts.get(field), list):
            errors.append(prefix + f"facts.{field} must be an array")
    if errors:
        return errors
    extracted_inputs = {
        fact.get("name")
        for fact in facts.get("inputs", [])
        if isinstance(fact, dict) and isinstance(fact.get("name"), str)
    }
    catalog_inputs = {
        pin.get("prop")
        for pin in entry.get("inputs", [])
        if isinstance(pin, dict) and isinstance(pin.get("prop"), str)
    }
    if extracted_inputs != catalog_inputs:
        errors.append(
            prefix
            + f"input declarations differ: catalog={sorted(catalog_inputs)}, "
            + f"source={sorted(extracted_inputs)}"
        )
    catalog_inputs_by_prop = {
        pin.get("prop"): pin
        for pin in entry.get("inputs", [])
        if isinstance(pin, dict) and isinstance(pin.get("prop"), str)
    }
    for fact in facts.get("inputs", []):
        if not isinstance(fact, dict) or not isinstance(
            fact.get("required_input"), bool
        ):
            continue
        property_name = fact.get("name")
        pin = catalog_inputs_by_prop.get(property_name)
        if pin is None:
            continue
        if pin.get("required") is not fact["required_input"]:
            errors.append(
                prefix
                + f"RequiredInput for {property_name!r} differs: "
                + f"catalog={pin.get('required')!r}, "
                + f"source={fact['required_input']!r}"
            )
    target_class = draft.get("class")
    extracted_properties = {
        fact.get("name")
        for fact in facts.get("properties", [])
        if isinstance(fact, dict)
        and isinstance(fact.get("name"), str)
        and not str(fact.get("type", "")).endswith("ExpressionInput")
        and isinstance(fact.get("reference"), dict)
        and isinstance(fact["reference"].get("symbol"), str)
        and fact["reference"]["symbol"].startswith(f"{target_class}::")
    }
    catalog_props = set(entry.get("props", {})) if isinstance(entry.get("props"), dict) else set()
    # Base-class and macro-expanded properties are not necessarily declared in
    # the selected header. Reject extracted target-class properties that the
    # catalog omitted, but do not treat inherited catalog properties as absent.
    unexpected_properties = extracted_properties - extracted_inputs - catalog_props
    if unexpected_properties:
        errors.append(
            prefix
            + f"source properties absent from catalog: {sorted(unexpected_properties)}"
        )
    initializers = {
        fact.get("name"): _literal(fact["initializer"])
        for fact in facts.get("properties", [])
        if isinstance(fact, dict)
        and isinstance(fact.get("name"), str)
        and isinstance(fact.get("initializer"), str)
    }
    assignments = {
        fact.get("property"): _literal(fact["value"])
        for fact in facts.get("constructor_assignments", [])
        if isinstance(fact, dict)
        and isinstance(fact.get("property"), str)
        and isinstance(fact.get("value"), str)
    }
    initializers.update(assignments)
    props = entry.get("props") if isinstance(entry.get("props"), dict) else {}
    for property_name, property_schema in props.items():
        if property_name not in initializers or not isinstance(property_schema, dict):
            continue
        expected = property_schema.get("default")
        # ``null`` is the catalog's explicit sentinel for a runtime-, asset-,
        # or project-derived default which cannot be represented as a stable
        # JSON literal.  Presence/type are still checked above.
        if expected is None:
            continue
        actual = initializers[property_name]
        if isinstance(actual, str) and any(character in actual for character in ".()"):
            continue
        if actual != expected:
            errors.append(
                prefix
                + f"constructor default for {property_name!r} differs: "
                + f"catalog={expected!r}, source={actual!r}"
            )
    extracted_output_names = [
        fact["name"]
        for fact in facts.get("output_definitions", [])
        if isinstance(fact, dict) and isinstance(fact.get("name"), str)
    ]
    semantics = entry.get("semantics")
    dynamic_outputs = (
        isinstance(semantics, dict) and semantics.get("operation") == "custom_code"
    )
    if extracted_output_names and not dynamic_outputs:
        if all(name == "" for name in extracted_output_names):
            extracted_output_names = [
                "Output" if index == 0 else f"Output{index + 1}"
                for index in range(len(extracted_output_names))
            ]
        catalog_output_names = [
            output.get("name")
            for output in entry.get("outputs", [])
            if isinstance(output, dict) and isinstance(output.get("name"), str)
        ]
        if catalog_output_names and all(name == "" for name in catalog_output_names):
            catalog_output_names = [
                "Output" if index == 0 else f"Output{index + 1}"
                for index in range(len(catalog_output_names))
            ]
        if catalog_output_names != extracted_output_names:
            errors.append(
                prefix
                + f"output names differ: catalog={catalog_output_names!r}, "
                + f"source={extracted_output_names!r}"
            )
    return errors


def _selected_names(
    catalog: dict[str, Any], requested: Iterable[str] | None
) -> list[str]:
    if requested:
        result: set[str] = set()
        for name in requested:
            if name in catalog:
                result.add(name)
                continue
            matches = [
                short_name
                for short_name, entry in catalog.items()
                if isinstance(entry, dict)
                and isinstance(entry.get("class"), str)
                and _catalog_class_symbol(entry["class"]) == name
            ]
            if len(matches) != 1:
                raise ValueError(f"class is not present in catalog: {name}")
            result.add(matches[0])
        return sorted(result)
    return sorted(
        name
        for name, entry in catalog.items()
        if isinstance(entry, dict) and "semantics" in entry
    )


def _catalog_class_symbol(value: str) -> str:
    leaf = value.rsplit(".", 1)[-1]
    return leaf if leaf.startswith("U") else "U" + leaf


def validate_all(
    ue_root: Path,
    catalog: dict[str, Any],
    evidence_document: dict[str, Any],
    manifest: dict[str, Any],
    requested: Iterable[str] | None = None,
    draft_document: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    evidence = evidence_document.get("nodes", evidence_document)
    if not isinstance(evidence, dict):
        return ["evidence document requires a nodes object"]
    draft_nodes: Any = None
    if draft_document is not None:
        if draft_document.get("kind") != "material_expression_fact_draft":
            errors.append("draft document has the wrong kind")
        draft_nodes = draft_document.get("nodes")
        if not isinstance(draft_nodes, dict):
            errors.append("draft document requires a nodes object")
            draft_nodes = {}
    for name in _selected_names(catalog, requested):
        entry = catalog[name]
        errors.extend(validate_node_semantics(name, entry))
        if not isinstance(entry, dict):
            continue
        errors.extend(validate_references(name, ue_root, evidence.get(name)))
        manifest_entry = manifest.get(name)
        if not isinstance(manifest_entry, dict):
            errors.append(f"{name}: manifest entry is missing")
        else:
            catalog_symbol = entry.get("class")
            if isinstance(catalog_symbol, str):
                catalog_symbol = _catalog_class_symbol(catalog_symbol)
            if catalog_symbol != manifest_entry.get("class"):
                errors.append(f"{name}: catalog and manifest class symbols differ")
            if entry.get("header") != manifest_entry.get("header"):
                errors.append(f"{name}: catalog and manifest header paths differ")
        if draft_nodes is not None:
            errors.extend(validate_draft(name, entry, draft_nodes.get(name)))
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ue-root",
        type=Path,
        default=Path(os.environ.get("UE_SOURCE_ROOT", DEFAULT_UE_ROOT)),
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--extract-draft", type=Path)
    parser.add_argument(
        "--extract-current",
        action="store_true",
        help="Mechanically extract current source facts and run Pin/default QA",
    )
    parser.add_argument("--class", dest="classes", action="append")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.extract_draft and args.extract_current:
        raise ValueError("--extract-draft and --extract-current are mutually exclusive")
    ue_root = args.ue_root.expanduser().resolve()
    manifest = load_object(args.manifest)
    catalog = load_object(args.catalog)
    if args.extract_draft:
        draft = load_object(args.extract_draft)
    elif args.extract_current:
        selected = _selected_names(catalog, args.classes)
        draft = extract_document(ue_root, manifest, selected)
    else:
        draft = None
    errors = validate_all(
        ue_root,
        catalog,
        load_object(args.evidence),
        manifest,
        args.classes,
        draft,
    )
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    if not args.quiet:
        print("semantic QA passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
