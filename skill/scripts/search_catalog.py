#!/usr/bin/env python3
"""Search Material Expression catalog facts and their independent evidence states."""

from __future__ import annotations

import argparse
import json
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
        "--evidence", choices=("pending", "partial", "verified", "not_applicable"),
        help="Require this state in at least one audit dimension",
    )
    parser.add_argument("--generation-ready", action="store_true")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    return parser.parse_args(argv)


def generation_ready(entry: dict[str, Any], audit: dict[str, Any]) -> bool:
    return bool(
        audit.get("declaration") == "verified"
        and audit.get("schema") == "verified"
        and audit.get("description") == "verified"
        and audit.get("restrictions") in {"verified", "not_applicable"}
        and not entry.get("abstract")
        and not entry.get("deprecated")
    )


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


def searchable_text(
    class_name: str, entry: dict[str, Any], record: dict[str, Any]
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
    return " ".join(parts).casefold()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.plugin and args.engine:
        raise ValueError("--plugin and --engine are mutually exclusive")
    if args.limit <= 0:
        raise ValueError("--limit must be positive")

    catalog = mgvalidate.load_catalog()
    evidence = mgvalidate.load_node_evidence()
    editor = mgvalidate.load_editor_evidence()
    editor_classes = editor.get("classes", {}) if isinstance(editor.get("classes"), dict) else {}
    terms = [term.casefold() for term in args.terms]
    results: list[dict[str, Any]] = []

    for class_name, entry in catalog.items():
        if not isinstance(entry, dict):
            continue
        record = evidence.get(class_name, {})
        record = record if isinstance(record, dict) else {}
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
        ready = generation_ready(entry, audit)
        if args.generation_ready and not ready:
            continue
        haystack = searchable_text(class_name, entry, record)
        if any(term not in haystack for term in terms):
            continue
        editor_record = editor_classes.get(class_name, {})
        editor_record = editor_record if isinstance(editor_record, dict) else {}
        results.append({
            "class": class_name,
            "description": entry.get("desc", "") if audit.get("description") == "verified" else "",
            "inputs": inputs if audit.get("schema") == "verified" else [],
            "outputs": outputs if audit.get("schema") == "verified" else [],
            "properties": sorted(props) if audit.get("schema") == "verified" else [],
            "source_audit": audit,
            "editor": {
                "copy": bool(editor_record.get("editor_copy")),
                "paste": bool(editor_record.get("editor_paste")),
                "roundtrip": bool(editor_record.get("editor_roundtrip")),
            },
            "generation_ready": ready,
            "plugin": bool(entry.get("plugin")),
        })

    results = results[: args.limit]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            audit = item["source_audit"]
            print(
                f"{item['class']} ready={str(item['generation_ready']).lower()} "
                f"source(schema={audit.get('schema')},description={audit.get('description')},"
                f"restrictions={audit.get('restrictions')}) "
                f"editor(roundtrip={str(item['editor']['roundtrip']).lower()})"
            )
            if item["description"]:
                print(f"  {item['description']}")
            if item["inputs"] or item["outputs"]:
                print(f"  inputs={item['inputs']} outputs={item['outputs']}")
        print(f"matches={len(results)} limit={args.limit}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}")
        raise SystemExit(1)
