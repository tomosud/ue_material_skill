#!/usr/bin/env python3
"""Mechanically extract source facts for Material Expression audit drafts.

The output is intentionally not a semantics record.  In particular, operation
and formula remain null: this tool never infers behavior from class names or
compiler calls.  A reviewer must reconcile the draft with source before it can
become maintained catalog data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UE_ROOT = Path(r"C:\work\unreal\UnrealEngine-release")
DEFAULT_MANIFEST = REPOSITORY_ROOT / "dev" / "catalog" / "manifest.json"

_DECLARATION_RE = re.compile(
    r"^\s*(?P<type>(?:[A-Za-z_][A-Za-z0-9_:<>]*\s*[*&]?))\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?:\{(?P<braced_initializer>[^;]*)\}|=\s*(?P<initializer>[^;]+))?;"
)
_INPUT_TYPE_RE = re.compile(r"(?:ExpressionInput|MaterialAttributesInput)$")
_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:this->)?(?P<property>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"(?P<value>[^;]+);\s*(?://.*)?$"
)
_OUTPUT_RE = re.compile(r"(?:FExpressionOutput\s*\(|Outputs?\.Add\s*\()")
_STATIC_OUTPUT_NAME_RE = re.compile(
    r'FExpressionOutput\s*\(\s*TEXT\s*\(\s*"(?P<name>(?:\\.|[^"\\])*)"\s*\)'
)
_REQUIRED_INPUT_RE = re.compile(
    r'\bRequiredInput\s*=\s*(?:"(?P<quoted>true|false)"|(?P<bare>true|false))',
    re.IGNORECASE,
)


def normalized_source_hash(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ue-root",
        type=Path,
        default=Path(os.environ.get("UE_SOURCE_ROOT", DEFAULT_UE_ROOT)),
        help="Unreal Engine checkout root",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--class",
        dest="classes",
        action="append",
        required=True,
        help="short catalog name or full UMaterialExpression class; repeatable",
    )
    return parser.parse_args(argv)


def _relative_source_path(ue_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(ue_root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"source path escapes --ue-root: {path}") from error


def _reference(
    ue_root: Path, path: Path, symbol: str, line: int, source_hash: str
) -> dict[str, Any]:
    return {
        "path": _relative_source_path(ue_root, path),
        "symbol": symbol,
        "line": line,
        "source_hash": source_hash,
    }


def _statement(lines: list[str], start: int) -> tuple[str, int]:
    """Return one declaration statement and its final zero-based line index."""

    pieces: list[str] = []
    index = start
    while index < len(lines):
        pieces.append(lines[index].strip())
        if ";" in lines[index]:
            break
        index += 1
    return " ".join(piece for piece in pieces if piece), index


def _braced_range(lines: list[str], start: int) -> tuple[int, int] | None:
    brace_line = start
    while brace_line < len(lines) and "{" not in lines[brace_line]:
        # A declaration/call which ends first is not a braced definition.
        if ";" in lines[brace_line]:
            return None
        brace_line += 1
    if brace_line == len(lines):
        return None
    depth = 0
    for index in range(brace_line, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        if depth == 0:
            return brace_line, index
    return None


def _class_range(lines: list[str], class_symbol: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"\bclass\b[^;]*\b{re.escape(class_symbol)}\b")
    for index, line in enumerate(lines):
        if pattern.search(line):
            class_range = _braced_range(lines, index)
            if class_range is not None:
                return class_range
    return None


def extract_header_facts(
    ue_root: Path, path: Path, class_symbol: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    source_hash = normalized_source_hash(path)
    class_range = _class_range(lines, class_symbol)
    if class_range is None:
        raise ValueError(f"class declaration {class_symbol} was not found in {path}")
    inputs: list[dict[str, Any]] = []
    properties: list[dict[str, Any]] = []
    property_macro: tuple[str, int] | None = None
    index = class_range[0] + 1
    while index < class_range[1]:
        stripped = lines[index].strip()
        if stripped.startswith("UPROPERTY"):
            macro = stripped
            macro_end = index
            depth = stripped.count("(") - stripped.count(")")
            while depth > 0 and macro_end + 1 < len(lines):
                macro_end += 1
                piece = lines[macro_end].strip()
                macro += " " + piece
                depth += piece.count("(") - piece.count(")")
            property_macro = (macro, index + 1)
            index = macro_end + 1
            continue
        statement, end = _statement(lines, index)
        match = _DECLARATION_RE.match(statement)
        if match:
            type_name = " ".join(match.group("type").split())
            name = match.group("name")
            fact = {
                "name": name,
                "type": type_name,
                "reference": _reference(
                    ue_root, path, f"{class_symbol}::{name}", index + 1, source_hash
                ),
            }
            initializer = match.group("initializer") or match.group("braced_initializer")
            if initializer is not None:
                fact["initializer"] = initializer.strip()
            if _INPUT_TYPE_RE.search(type_name.rstrip(" *&")):
                if property_macro is not None:
                    required_match = _REQUIRED_INPUT_RE.search(property_macro[0])
                    if required_match is not None:
                        raw_required = (
                            required_match.group("quoted")
                            or required_match.group("bare")
                        )
                        fact["required_input"] = raw_required.lower() == "true"
                inputs.append(fact)
            if property_macro is not None:
                fact = dict(fact)
                fact["uproperty"] = property_macro[0]
                fact["uproperty_line"] = property_macro[1]
                properties.append(fact)
            property_macro = None
            index = end + 1
            continue
        # Comments and metadata may occur between UPROPERTY and its declaration.
        if stripped and not stripped.startswith(("//", "/*", "*", "#")):
            property_macro = None
        index += 1
    return inputs, properties


def _constructor_range(lines: list[str], class_symbol: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"\b{re.escape(class_symbol)}::{re.escape(class_symbol)}\s*\(")
    start = next((index for index, line in enumerate(lines) if pattern.search(line)), None)
    if start is None:
        return None
    return _braced_range(lines, start)


def _method_ranges(
    lines: list[str], class_symbol: str
) -> list[tuple[str, int, int]]:
    pattern = re.compile(
        rf"^(?P<prefix>.*?)\b{re.escape(class_symbol)}::"
        rf"(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    )
    result: list[tuple[str, int, int]] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match is None:
            continue
        # A non-constructor definition has a return type (or declaration macro)
        # before the qualified name. Requiring that prefix prevents a qualified
        # call inside another class method from being treated as a definition.
        prefix = match.group("prefix").strip()
        if not prefix or any(token in prefix for token in "();={}"):
            continue
        source_range = _braced_range(lines, index)
        if source_range is not None:
            result.append((match.group("method"), source_range[0], source_range[1]))
    return result


def _output_fact(
    ue_root: Path,
    path: Path,
    class_symbol: str,
    method: str,
    line: str,
    line_number: int,
    source_hash: str,
) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "expression": line.strip(),
        "reference": _reference(
            ue_root, path, f"{class_symbol}::{method}", line_number, source_hash
        ),
    }
    match = _STATIC_OUTPUT_NAME_RE.search(line)
    if match is not None:
        fact["name"] = match.group("name")
    return fact


def extract_cpp_facts(
    ue_root: Path, path: Path, class_symbol: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    source_hash = normalized_source_hash(path)
    assignments: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    constructor = _constructor_range(lines, class_symbol)
    if constructor is not None:
        for index in range(constructor[0] + 1, constructor[1]):
            match = _ASSIGNMENT_RE.match(lines[index])
            if match:
                assignments.append(
                    {
                        "property": match.group("property"),
                        "value": match.group("value").strip(),
                        "reference": _reference(
                            ue_root,
                            path,
                            f"{class_symbol}::{class_symbol}",
                            index + 1,
                            source_hash,
                        ),
                    }
                )
            if re.search(r"\bCachedInputs\.Empty\s*\(\s*\)", lines[index]):
                assignments.append(
                    {
                        "property": "CachedInputs",
                        "value": "empty",
                        "reference": _reference(
                            ue_root,
                            path,
                            f"{class_symbol}::{class_symbol}",
                            index + 1,
                            source_hash,
                        ),
                    }
                )
            if re.search(r"\bCachedInputs\.(?:Push|Add)\s*\(", lines[index]):
                assignments.append(
                    {
                        "property": "CachedInputs",
                        "value": "populated",
                        "reference": _reference(
                            ue_root,
                            path,
                            f"{class_symbol}::{class_symbol}",
                            index + 1,
                            source_hash,
                        ),
                    }
                )
            if _OUTPUT_RE.search(lines[index]):
                outputs.append(
                    _output_fact(
                        ue_root,
                        path,
                        class_symbol,
                        class_symbol,
                        lines[index],
                        index + 1,
                        source_hash,
                    )
                )
    for method, first, last in _method_ranges(lines, class_symbol):
        if method == class_symbol:
            continue
        for index in range(first, last + 1):
            if _OUTPUT_RE.search(lines[index]):
                outputs.append(
                    _output_fact(
                        ue_root,
                        path,
                        class_symbol,
                        method,
                        lines[index],
                        index + 1,
                        source_hash,
                    )
                )
    return assignments, outputs


def _resolve_classes(
    manifest: dict[str, Any], requested: Iterable[str]
) -> list[tuple[str, dict[str, Any]]]:
    by_symbol = {
        entry.get("class"): (name, entry)
        for name, entry in manifest.items()
        if isinstance(entry, dict) and isinstance(entry.get("class"), str)
    }
    resolved: dict[str, dict[str, Any]] = {}
    for requested_name in requested:
        candidate = manifest.get(requested_name)
        if isinstance(candidate, dict):
            resolved[requested_name] = candidate
            continue
        match = by_symbol.get(requested_name)
        if match is None:
            raise ValueError(f"class is not present in manifest: {requested_name}")
        resolved[match[0]] = match[1]
    return sorted(resolved.items())


def _source_files(ue_root: Path, entry: dict[str, Any]) -> list[Path]:
    relative_paths: list[str] = []
    for field in ("header", "impl"):
        value = entry.get(field)
        if isinstance(value, str):
            relative_paths.append(value)
    relative_paths.extend(
        [
            "Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp",
            "Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressionsToMIR.cpp",
        ]
    )
    result: list[Path] = []
    for relative in relative_paths:
        path = ue_root / Path(relative)
        if path.is_file() and path not in result:
            result.append(path)
    return result


def _lineage_entries(
    manifest: dict[str, Any], entry: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return target then manifest-known bases, stopping before unknown roots."""

    by_class = {
        value.get("class"): value
        for value in manifest.values()
        if isinstance(value, dict) and isinstance(value.get("class"), str)
    }
    result = [entry]
    seen = {entry.get("class")}
    current = entry
    while isinstance(current.get("base"), str):
        if current["base"] in {"UMaterialExpression", "UObject"}:
            break
        parent = by_class.get(current["base"])
        if not isinstance(parent, dict) or parent.get("class") in seen:
            break
        result.append(parent)
        seen.add(parent.get("class"))
        current = parent
    return result


def _merge_named_facts(groups: Iterable[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for group in groups:
        for fact in group:
            name = fact.get("name")
            if isinstance(name, str):
                result[name] = fact
    return list(result.values())


def extract_document(
    ue_root: Path, manifest: dict[str, Any], requested: Iterable[str]
) -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    for short_name, entry in _resolve_classes(manifest, requested):
        class_symbol = entry.get("class")
        header = entry.get("header")
        if not isinstance(class_symbol, str) or not isinstance(header, str):
            raise ValueError(f"manifest entry {short_name} lacks class/header")
        header_path = ue_root / Path(header)
        if not header_path.is_file():
            raise ValueError(f"header does not exist: {header_path}")
        lineage = _lineage_entries(manifest, entry)
        header_groups: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
        for lineage_entry in reversed(lineage):
            lineage_header = lineage_entry.get("header")
            lineage_class = lineage_entry.get("class")
            if not isinstance(lineage_header, str) or not isinstance(lineage_class, str):
                continue
            lineage_path = ue_root / Path(lineage_header)
            if lineage_path.is_file():
                header_groups.append(
                    extract_header_facts(ue_root, lineage_path, lineage_class)
                )
        inputs = _merge_named_facts(group[0] for group in header_groups)
        properties = _merge_named_facts(group[1] for group in header_groups)
        assignments: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        source_paths: list[Path] = []
        for lineage_entry in reversed(lineage):
            lineage_class = lineage_entry.get("class")
            if not isinstance(lineage_class, str):
                continue
            for source_path in _source_files(ue_root, lineage_entry):
                if source_path not in source_paths:
                    source_paths.append(source_path)
                if source_path.suffix.lower() != ".cpp":
                    continue
                source_assignments, source_outputs = extract_cpp_facts(
                    ue_root, source_path, lineage_class
                )
                assignments.extend(source_assignments)
                if lineage_entry is entry:
                    outputs.extend(source_outputs)
        if any(
            fact.get("property") == "bShowTextureInputPin"
            and fact.get("value", "").strip() == "false"
            for fact in assignments
        ):
            inputs = [fact for fact in inputs if fact.get("name") != "TextureObject"]
        cached_input_actions = [
            fact.get("value")
            for fact in assignments
            if fact.get("property") == "CachedInputs"
        ]
        if cached_input_actions and cached_input_actions[-1] == "empty":
            inputs = []
        nodes[short_name] = {
            "class": class_symbol,
            "draft": True,
            "semantic_draft": {"operation": None, "formula": None},
            "facts": {
                "inputs": inputs,
                "properties": properties,
                "constructor_assignments": assignments,
                "output_definitions": outputs,
            },
            "sources": [
                {
                    "path": _relative_source_path(ue_root, path),
                    "source_hash": normalized_source_hash(path),
                }
                for path in source_paths
            ],
        }
    return {
        "schema_version": 1,
        "kind": "material_expression_fact_draft",
        "nodes": nodes,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ue_root = args.ue_root.expanduser().resolve()
    if not ue_root.is_dir():
        raise ValueError(f"--ue-root does not exist: {ue_root}")
    document = extract_document(ue_root, load_object(args.manifest), args.classes)
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
