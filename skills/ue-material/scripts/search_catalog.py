#!/usr/bin/env python3
"""Search Material Expression catalog facts and their independent evidence states."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import validate as mgvalidate


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="*", help="Case-insensitive terms matched across catalog and source evidence")
    parser.add_argument("--class", dest="class_name", help="Exact short class name")
    parser.add_argument("--pin", help="Exact effective input or output Pin name")
    parser.add_argument("--property", help="Exact property name")
    parser.add_argument("--plugin", action="store_true", help="Return plugin nodes only")
    parser.add_argument("--engine", action="store_true", help="Return Engine nodes only")
    parser.add_argument(
        "--evidence",
        choices=("pending", "verified", "stale", "not_applicable"),
        help="Require this state in at least one audit dimension",
    )
    parser.add_argument("--limit", type=int, help="Maximum results to return (default: 8)")
    parser.add_argument("--all", action="store_true", help="Return every matching result")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print packaged skill and Unreal Engine catalog metadata, then exit",
    )
    return parser.parse_args(argv)


def pin_names(entry: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_inputs = list(entry.get("inputs", [])) + list(entry.get("prop_pins", []))
    raw_outputs = list(entry.get("outputs", []))
    inputs = [
        mgvalidate.effective_pin_name(pin, index, False)
        for index, pin in enumerate(raw_inputs) if isinstance(pin, dict)
    ]
    outputs = [
        mgvalidate.effective_pin_name(pin, index, True)
        for index, pin in enumerate(raw_outputs) if isinstance(pin, dict)
    ]
    return inputs, outputs


def load_legacy_prose() -> dict[str, Any]:
    target = mgvalidate.skill_root() / "catalog" / "legacy-node-prose.json"
    with target.open("r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or document.get("status") != "inactive_review_only":
        raise ValueError(f"legacy prose {target} must be marked inactive_review_only")
    nodes = document.get("nodes") if isinstance(document, dict) else None
    if not isinstance(nodes, dict):
        raise ValueError(f"legacy prose {target} must contain a 'nodes' object")
    return nodes


def load_metadata() -> dict[str, Any]:
    target = mgvalidate.skill_root() / "catalog" / "meta.json"
    with target.open("r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"catalog metadata {target} must be an object")
    return document


def searchable_text(
    class_name: str,
    entry: dict[str, Any],
    record: dict[str, Any],
    legacy_record: dict[str, Any] | None = None,
) -> str:
    references = record.get("references", [])
    reference_text = " ".join(
        f"{item.get('path', '')} {item.get('symbol', '')}"
        for item in references if isinstance(item, dict)
    )
    inputs, outputs = pin_names(entry)
    parts = [
        class_name,
        str(entry.get("class", "")),
        str(entry.get("header", "")),
        str(entry.get("desc", "")),
        str(entry.get("category", "")),
        " ".join(inputs + outputs),
        " ".join(entry.get("props", {}).keys()) if isinstance(entry.get("props"), dict) else "",
        reference_text,
    ]
    if legacy_record is not None:
        parts.append(json.dumps(legacy_record, ensure_ascii=False, sort_keys=True))
    return " ".join(parts).casefold()


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
ALL_TERMS_BONUS = 5


def query_terms(values: list[str]) -> list[str]:
    return [term.casefold() for value in values for term in value.split() if term]


def text_tokens(*values: str) -> set[str]:
    return {
        token.casefold()
        for value in values
        for token in TOKEN_RE.findall(value)
    }


def flattened_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for key in sorted(value) for item in flattened_strings(value[key])]
    if isinstance(value, list):
        return [item for value_item in value for item in flattened_strings(value_item)]
    return []


def relevance_score(
    terms: list[str],
    class_name: str,
    entry: dict[str, Any],
    record: dict[str, Any],
    legacy_record: dict[str, Any] | None,
) -> int | None:
    """Return a deterministic field-weighted score, or None for an AND miss."""

    class_folded = class_name.casefold()
    aliases = [
        alias.casefold() for alias in entry.get("aliases", []) if isinstance(alias, str)
    ]
    references = record.get("references", [])
    reference_values = [str(entry.get("class", "")), str(entry.get("header", ""))]
    for reference in references if isinstance(references, list) else []:
        if isinstance(reference, dict):
            reference_values.extend(
                (str(reference.get("path", "")), str(reference.get("symbol", "")))
            )
    reference_folded = [value.casefold() for value in reference_values]
    inputs, outputs = pin_names(entry)
    props = entry.get("props", {}) if isinstance(entry.get("props"), dict) else {}
    names = {name.casefold() for name in inputs + outputs + list(props)}
    active_tokens = text_tokens(
        str(entry.get("desc", "")),
        str(entry.get("notes", "")),
        str(entry.get("category", "")),
    )
    legacy_tokens = text_tokens(*flattened_strings(legacy_record or {}))

    total = 0
    for term in terms:
        scores: list[int] = []
        if term == class_folded:
            scores.append(100)
        elif class_folded.startswith(term):
            scores.append(70)
        elif term in class_folded:
            scores.append(50)
        if term in aliases:
            scores.append(60)
        if any(term in value for value in reference_folded):
            scores.append(45)
        if term in names:
            scores.append(35)
        if term in active_tokens:
            scores.append(15)
        if term in legacy_tokens:
            scores.append(8)
        if not scores:
            return None
        total += max(scores)
    if len(terms) > 1:
        total += ALL_TERMS_BONUS * len(terms)
        if " ".join(terms) in aliases:
            total += 60
    return total


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    if args.version:
        print(json.dumps(load_metadata(), ensure_ascii=False, indent=2))
        return 0
    if args.plugin and args.engine:
        raise ValueError("--plugin and --engine are mutually exclusive")
    if args.all and args.limit is not None:
        raise ValueError("--all and --limit are mutually exclusive")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be positive")

    catalog = mgvalidate.load_catalog()
    evidence = mgvalidate.load_node_evidence()
    editor = mgvalidate.load_editor_evidence()
    legacy = load_legacy_prose()
    editor_classes = editor.get("classes", {}) if isinstance(editor.get("classes"), dict) else {}
    terms = query_terms(args.terms)
    ranked_results: list[tuple[int, str, dict[str, Any]]] = []

    for class_name, entry in catalog.items():
        if not isinstance(entry, dict):
            continue
        record = evidence.get(class_name, {})
        record = record if isinstance(record, dict) else {}
        legacy_record = legacy.get(class_name)
        legacy_record = legacy_record if isinstance(legacy_record, dict) else None
        audit = record.get("audit", {})
        audit = audit if isinstance(audit, dict) else {}
        inputs, outputs = pin_names(entry)
        if args.class_name and class_name != args.class_name:
            continue
        if args.pin and args.pin not in inputs + outputs:
            continue
        props = entry.get("props", {}) if isinstance(entry.get("props"), dict) else {}
        if args.property and args.property not in props:
            continue
        if args.plugin and not entry.get("plugin"):
            continue
        if args.engine and entry.get("plugin"):
            continue
        if args.evidence and args.evidence not in audit.values():
            continue
        score = relevance_score(terms, class_name, entry, record, legacy_record)
        if score is None:
            continue
        editor_record = editor_classes.get(class_name, {})
        editor_record = editor_record if isinstance(editor_record, dict) else {}
        active_description = str(entry.get("desc", ""))
        legacy_description = (
            str(legacy_record.get("desc", "")) if legacy_record is not None else ""
        )
        active_notes = str(entry.get("notes", ""))
        legacy_notes = (
            str(legacy_record.get("notes", "")) if legacy_record is not None else ""
        )
        legacy_field_notes = (
            legacy_record.get("field_notes", {}) if legacy_record is not None else {}
        )
        if active_description:
            description_provenance = audit.get("description", "missing")
        elif legacy_description:
            description_provenance = "legacy_unverified"
        else:
            description_provenance = audit.get("description", "missing")
        if active_notes:
            restrictions_provenance = audit.get("restrictions", "missing")
        elif legacy_notes:
            restrictions_provenance = "legacy_unverified"
        else:
            restrictions_provenance = audit.get("restrictions", "missing")
        result: dict[str, Any] = {
            "class": class_name,
            "description": active_description or legacy_description,
            "notes": active_notes or legacy_notes,
            "field_notes": legacy_field_notes,
            "inputs": inputs,
            "outputs": outputs,
            "properties": sorted(props),
            "provenance": {
                "declaration": audit.get("declaration", "missing"),
                "schema": audit.get("schema", "missing"),
                "description": description_provenance,
                "restrictions": restrictions_provenance,
            },
            "source_references": record.get("references", []),
            "editor": {
                "copy": bool(editor_record.get("editor_copy")),
                "paste": bool(editor_record.get("editor_paste")),
                "roundtrip": bool(editor_record.get("editor_roundtrip")),
            },
            "plugin": bool(entry.get("plugin")),
            "aliases": list(entry.get("aliases", [])),
        }
        semantics = entry.get("semantics")
        if isinstance(semantics, dict):
            result["semantics"] = {
                "restrictions": semantics.get("restrictions", []),
                "unresolved": semantics.get("unresolved", []),
            }
        ranked_results.append((score, class_name.casefold(), result))

    ranked_results.sort(key=lambda item: (-item[0], item[1], item[2]["class"]))
    total_matches = len(ranked_results)
    limit = total_matches if args.all else (args.limit if args.limit is not None else 8)
    results = [item[2] for item in ranked_results[:limit]]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            provenance = item["provenance"]
            print(
                f"{item['class']} "
                f"source(schema={provenance.get('schema')},"
                f"description={provenance.get('description')},"
                f"restrictions={provenance.get('restrictions')}) "
                f"editor(roundtrip={str(item['editor']['roundtrip']).lower()})"
            )
            if item["description"]:
                print(f"  {item['description']}")
            semantics = item.get("semantics")
            if isinstance(semantics, dict):
                if semantics["restrictions"]:
                    print(
                        "  restrictions="
                        + json.dumps(
                            semantics["restrictions"], ensure_ascii=False, sort_keys=True
                        )
                    )
                if semantics["unresolved"]:
                    print(f"  unresolved={semantics['unresolved']}")
            print(
                f"  inputs={item['inputs']} outputs={item['outputs']} "
                f"properties={item['properties']}"
            )
            if (
                provenance.get("schema") != "verified"
                or provenance.get("description") != "verified"
                or (
                    isinstance(semantics, dict)
                    and bool(semantics.get("unresolved"))
                )
            ):
                print("  verify node facts against the configured Unreal Engine source before use")
        print(f"matches={total_matches} shown={len(results)} limit={'all' if args.all else limit}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}")
        raise SystemExit(1)
