#!/usr/bin/env python3
"""Validate compact Unreal Material Graph JSON (MGJSON).

The module is standard-library only and is intentionally importable by build.py.
Errors prevent generation; warnings describe suspicious but representable input.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


NODE_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
RAW_PROP_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\([0-9]+\))?$")
GUID_RE = re.compile(r"^[0-9A-Fa-f]{32}$")
INT_TYPE_RE = re.compile(r"^(?:u?int(?:8|16|32|64)?|byte)$", re.IGNORECASE)
LINK_RE = re.compile(r"^\s*(.*?)\s*->\s*(.*?)\s*$")
CLASS_ALIASES = {"Lerp": "LinearInterpolate"}


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    path: str
    message: str
    suggestion: str | None = None

    def __str__(self) -> str:
        result = f"{self.severity}: {self.path}: {self.message}"
        if self.suggestion:
            result += f"; suggestion: {self.suggestion}"
        return result


@dataclass
class ValidationResult:
    diagnostics: list[Diagnostic]

    @property
    def errors(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class Link:
    source_id: str
    source_pin: str | None
    destination_id: str
    destination_pin: str
    index: int
    raw: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_catalog(path: Path | str | None = None) -> dict[str, Any]:
    target = Path(path) if path else repository_root() / "skill" / "catalog" / "nodes.json"
    with target.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError(f"catalog {target} must contain an object")
    return value


def load_functions(path: Path | str | None = None) -> dict[str, Any]:
    target = Path(path) if path else repository_root() / "skill" / "catalog" / "functions.json"
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError(f"function catalog {target} must contain an object")
    return value


def load_document(text: str) -> tuple[Any | None, list[Diagnostic]]:
    try:
        return json.loads(text, object_pairs_hook=_unique_object), []
    except json.JSONDecodeError as exc:
        return None, [
            Diagnostic(
                "error",
                f"$ (line {exc.lineno}, column {exc.colno})",
                f"invalid JSON: {exc.msg}",
            )
        ]
    except DuplicateKeyError as exc:
        return None, [Diagnostic("error", "$", str(exc), "rename or remove one occurrence")]


def _suggest(value: str, choices: Iterable[str], aliases: dict[str, str] | None = None) -> str | None:
    choices_list = list(choices)
    result: list[str] = []
    if aliases and value in aliases and aliases[value] in choices_list:
        result.append(aliases[value])
    for item in difflib.get_close_matches(value, choices_list, n=3, cutoff=0.42):
        if item not in result:
            result.append(item)
    if not result:
        return None
    return "did you mean " + ", ".join(repr(item) for item in result[:3]) + "?"


def effective_pin_name(pin: dict[str, Any], index: int, output: bool) -> str:
    name = pin.get("name")
    if isinstance(name, str) and name:
        return name
    if output:
        mask = pin.get("mask")
        if isinstance(mask, str) and mask:
            return mask
        return "Output" if index == 0 else f"out{index}"
    prop = pin.get("prop")
    return str(prop) if prop else f"in{index}"


def _function_for_node(node: dict[str, Any], functions: dict[str, Any]) -> dict[str, Any] | None:
    props = node.get("props")
    path = props.get("MaterialFunction") if isinstance(props, dict) else None
    if not isinstance(path, str):
        return None
    return next(
        (item for item in functions.values() if isinstance(item, dict) and item.get("path") == path),
        None,
    )


def pin_schema(
    node: dict[str, Any], entry: dict[str, Any], functions: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if node.get("class") == "MaterialFunctionCall":
        function = _function_for_node(node, functions)
        if function:
            inputs = [
                {"name": pin.get("name", ""), "prop": pin.get("name", ""), "required": pin.get("required", False)}
                for pin in function.get("inputs", [])
                if isinstance(pin, dict)
            ]
            outputs = [
                {"name": pin.get("name", "")}
                for pin in function.get("outputs", [])
                if isinstance(pin, dict)
            ]
            return inputs, outputs
    inputs = list(entry.get("inputs", [])) + list(entry.get("prop_pins", []))
    return inputs, list(entry.get("outputs", []))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _array_of(value: Any, lengths: set[int], integers: bool = False) -> bool:
    if not isinstance(value, list) or len(value) not in lengths:
        return False
    if integers:
        return all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return all(_is_number(item) for item in value)


def _validate_typed_value(value: Any, spec: dict[str, Any]) -> tuple[bool, str | None]:
    type_name = str(spec.get("type", "raw"))
    lower = type_name.lower()
    if lower in {"float", "double"}:
        return _is_number(value), "use a finite JSON number"
    if INT_TYPE_RE.fullmatch(type_name):
        return isinstance(value, int) and not isinstance(value, bool), "use a JSON integer"
    if lower == "bool":
        return isinstance(value, bool), "use true or false"
    if type_name in {"FName", "FString", "FText"}:
        return isinstance(value, str), "use a JSON string"
    if lower.startswith("enum:") or type_name.startswith("E"):
        return isinstance(value, str) and bool(value), "use the enum value name as a non-empty string"
    if lower.startswith("asset:"):
        ok = value is None or (
            isinstance(value, str) and bool(value) and value.startswith("/") and "\n" not in value
        )
        return ok, "use null or an Unreal object path such as /Game/Folder/Asset.Asset"
    if type_name in {"FLinearColor", "FColor"}:
        return _array_of(value, {3, 4}, integers=type_name == "FColor"), "use an array with 3 or 4 numeric elements"
    if type_name == "FIntPoint":
        return _array_of(value, {2}, integers=True), "use a 2-element integer array"
    dimensions = {
        "FVector2D": 2,
        "FVector": 3,
        "FVector3f": 3,
        "FVector4": 4,
        "FVector4f": 4,
        "FVector4d": 4,
    }
    if type_name in dimensions:
        count = dimensions[type_name]
        return _array_of(value, {count}), f"use a {count}-element numeric array"
    if type_name == "FGuid":
        return isinstance(value, str) and bool(GUID_RE.fullmatch(value)), "use exactly 32 hexadecimal digits"
    if lower.startswith(("array:", "tarray<")):
        return isinstance(value, list), "use a JSON array"
    if lower.startswith("struct:") or type_name.startswith("F"):
        return isinstance(value, (dict, list)), "use a JSON object or catalog-defined array"
    return True, None


def parse_link(value: Any, index: int) -> tuple[Link | None, Diagnostic | None]:
    path = f"$.links[{index}]"
    if not isinstance(value, str):
        return None, Diagnostic("error", path, "link must be a string")
    match = LINK_RE.fullmatch(value)
    if not match or value.count("->") != 1:
        return None, Diagnostic(
            "error", path, "invalid link syntax", "use 'source[.output] -> destination.input'"
        )
    source_text, destination_text = (part.strip() for part in match.groups())
    if not source_text or not destination_text:
        return None, Diagnostic("error", path, "link endpoint is empty")
    if "." in source_text:
        source_id, source_pin = (part.strip() for part in source_text.split(".", 1))
        if not source_pin:
            return None, Diagnostic("error", path, "source output name is empty")
    else:
        source_id, source_pin = source_text, None
    if "." not in destination_text:
        return None, Diagnostic(
            "error", path, "destination input name is required", "append '.InputName'"
        )
    destination_id, destination_pin = (
        part.strip() for part in destination_text.split(".", 1)
    )
    if not destination_pin:
        return None, Diagnostic("error", path, "destination input name is empty")
    if not source_id or not destination_id:
        return None, Diagnostic("error", path, "node id is empty")
    return Link(source_id, source_pin, destination_id, destination_pin, index, value), None


def _comment_validation(
    node_id: str,
    node: dict[str, Any],
    nodes: dict[str, Any],
    pos: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    path = f"$.nodes.{node_id}.props"
    props = node.get("props", {})
    if not isinstance(props, dict):
        diagnostics.append(Diagnostic("error", path, "Comment props must be an object"))
        return
    allowed = {
        "Text", "nodes", "CommentColor", "FontSize",
        "bCommentBubbleVisible_InDetailsPanel", "bColorCommentBubble", "MoveMode",
        "SizeX", "SizeY",
    }
    for key in props.keys() - allowed:
        diagnostics.append(Diagnostic("error", f"{path}.{key}", "unknown Comment property", _suggest(key, allowed)))
    if "Text" in props and not isinstance(props["Text"], str):
        diagnostics.append(Diagnostic("error", f"{path}.Text", "must be a string"))
    contained = props.get("nodes")
    if contained is not None:
        if not isinstance(contained, list) or not contained:
            diagnostics.append(Diagnostic("error", f"{path}.nodes", "must be a non-empty array of node ids"))
        else:
            seen: set[str] = set()
            for index, target in enumerate(contained):
                target_path = f"{path}.nodes[{index}]"
                if not isinstance(target, str):
                    diagnostics.append(Diagnostic("error", target_path, "must be a node id string"))
                elif target in seen:
                    diagnostics.append(Diagnostic("error", target_path, f"duplicate contained node {target!r}"))
                elif target == node_id:
                    diagnostics.append(Diagnostic("error", target_path, "Comment cannot contain itself"))
                elif target not in nodes:
                    diagnostics.append(Diagnostic("error", target_path, f"unknown contained node {target!r}", _suggest(target, nodes)))
                elif isinstance(nodes[target], dict) and nodes[target].get("class") == "Comment":
                    diagnostics.append(Diagnostic("error", target_path, "Comment cannot contain another Comment"))
                seen.add(target)
        if node_id in pos or "SizeX" in props or "SizeY" in props:
            diagnostics.append(Diagnostic("error", path, "contained Comment cannot also specify pos, SizeX, or SizeY"))
    if "CommentColor" in props and not _array_of(props["CommentColor"], {3, 4}):
        diagnostics.append(Diagnostic("error", f"{path}.CommentColor", "must have 3 or 4 finite numbers"))
    if "FontSize" in props and (
        not isinstance(props["FontSize"], int) or isinstance(props["FontSize"], bool) or not 1 <= props["FontSize"] <= 1000
    ):
        diagnostics.append(Diagnostic("error", f"{path}.FontSize", "must be an integer from 1 to 1000"))
    for key in ("bCommentBubbleVisible_InDetailsPanel", "bColorCommentBubble"):
        if key in props and not isinstance(props[key], bool):
            diagnostics.append(Diagnostic("error", f"{path}.{key}", "must be boolean"))
    if "MoveMode" in props and props["MoveMode"] not in {"GroupMovement", "NoGroupMovement"}:
        diagnostics.append(Diagnostic("error", f"{path}.MoveMode", "must be GroupMovement or NoGroupMovement"))
    for key in ("SizeX", "SizeY"):
        if key in props and (
            not isinstance(props[key], int) or isinstance(props[key], bool) or props[key] <= 0
        ):
            diagnostics.append(Diagnostic("error", f"{path}.{key}", "must be a positive integer"))


def validate_document(
    document: Any,
    catalog: dict[str, Any] | None = None,
    functions: dict[str, Any] | None = None,
) -> ValidationResult:
    catalog = catalog if catalog is not None else load_catalog()
    functions = functions if functions is not None else load_functions()
    diagnostics: list[Diagnostic] = []
    if not isinstance(document, dict):
        return ValidationResult([Diagnostic("error", "$", "top-level value must be an object")])
    allowed_top = {"nodes", "links", "pos"}
    for key in document.keys() - allowed_top:
        diagnostics.append(Diagnostic("error", f"$.{key}", "unknown top-level key", _suggest(key, allowed_top)))
    nodes = document.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return ValidationResult(diagnostics + [Diagnostic("error", "$.nodes", "required non-empty object")])
    links_value = document.get("links", [])
    if not isinstance(links_value, list):
        diagnostics.append(Diagnostic("error", "$.links", "must be an array of strings"))
        links_value = []
    pos = document.get("pos", {})
    if not isinstance(pos, dict):
        diagnostics.append(Diagnostic("error", "$.pos", "must be an object"))
        pos = {}
    for node_id, coords in pos.items():
        path = f"$.pos.{node_id}"
        if node_id not in nodes:
            diagnostics.append(Diagnostic("error", path, f"unknown node id {node_id!r}", _suggest(node_id, nodes)))
        if not _array_of(coords, {2}, integers=True):
            diagnostics.append(Diagnostic("error", path, "position must be [integer, integer]"))

    normal_nodes: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for node_id, node in nodes.items():
        node_path = f"$.nodes.{node_id}"
        if not NODE_ID_RE.fullmatch(node_id):
            diagnostics.append(Diagnostic("error", node_path, "invalid node id", "use letters, digits, '_' or '-', starting with a letter or '_'"))
        if not isinstance(node, dict):
            diagnostics.append(Diagnostic("error", node_path, "node must be an object"))
            continue
        for key in node.keys() - {"class", "props", "raw_props"}:
            diagnostics.append(Diagnostic("error", f"{node_path}.{key}", "unknown node key", _suggest(key, {"class", "props", "raw_props"})))
        class_name = node.get("class")
        if not isinstance(class_name, str) or not class_name:
            diagnostics.append(Diagnostic("error", f"{node_path}.class", "required non-empty string"))
            continue
        if class_name == "Comment":
            if "raw_props" in node:
                diagnostics.append(Diagnostic("error", f"{node_path}.raw_props", "Comment does not accept raw_props"))
            _comment_validation(node_id, node, nodes, pos, diagnostics)
            continue
        entry = catalog.get(class_name)
        if not isinstance(entry, dict):
            diagnostics.append(Diagnostic("error", f"{node_path}.class", f"unknown class {class_name!r}", _suggest(class_name, catalog, CLASS_ALIASES)))
            continue
        normal_nodes[node_id] = (node, entry)
        if entry.get("abstract"):
            diagnostics.append(Diagnostic("error", f"{node_path}.class", f"class {class_name!r} is abstract and cannot be built"))
        if entry.get("deprecated"):
            diagnostics.append(Diagnostic("warning", f"{node_path}.class", f"class {class_name!r} is deprecated"))
        if not entry.get("verified", False):
            diagnostics.append(Diagnostic("warning", f"{node_path}.class", f"class {class_name!r} is not Editor-verified"))
        props = node.get("props", {})
        raw_props = node.get("raw_props", {})
        if not isinstance(props, dict):
            diagnostics.append(Diagnostic("error", f"{node_path}.props", "must be an object"))
            props = {}
        if not isinstance(raw_props, dict):
            diagnostics.append(Diagnostic("error", f"{node_path}.raw_props", "must be an object of strings"))
            raw_props = {}
        overlap = props.keys() & raw_props.keys()
        for prop_name in overlap:
            diagnostics.append(Diagnostic("error", f"{node_path}.raw_props.{prop_name}", "property also exists in props; choose one representation"))
        prop_catalog = entry.get("props", {}) if isinstance(entry.get("props"), dict) else {}
        for prop_name, value in props.items():
            prop_path = f"{node_path}.props.{prop_name}"
            spec = prop_catalog.get(prop_name)
            if not isinstance(spec, dict):
                diagnostics.append(Diagnostic("error", prop_path, f"unknown typed property {prop_name!r}", _suggest(prop_name, prop_catalog)))
                continue
            ok, suggestion = _validate_typed_value(value, spec)
            if not ok:
                diagnostics.append(Diagnostic("error", prop_path, f"invalid value for catalog type {spec.get('type')!r}", suggestion))
            type_name = str(spec.get("type", ""))
            if (type_name.startswith("enum:") or type_name.startswith("E")) and isinstance(value, str):
                choices = spec.get("choices", spec.get("values", spec.get("enum_values")))
                if isinstance(choices, list):
                    if value not in choices:
                        diagnostics.append(Diagnostic("error", prop_path, f"unknown enum value {value!r}", _suggest(value, choices)))
                else:
                    diagnostics.append(Diagnostic("warning", prop_path, f"catalog has no choices for {type_name}; enum name was type-checked only"))
            if type_name.lower().startswith("asset:") and isinstance(value, str):
                diagnostics.append(Diagnostic("warning", prop_path, "asset path syntax is valid but existence was not checked"))
        for prop_name, value in raw_props.items():
            prop_path = f"{node_path}.raw_props.{prop_name}"
            if not isinstance(prop_name, str) or not RAW_PROP_RE.fullmatch(prop_name):
                diagnostics.append(Diagnostic("error", prop_path, "invalid raw property name"))
            if not isinstance(value, str) or "\n" in value or "\r" in value:
                diagnostics.append(Diagnostic("error", prop_path, "raw property value must be a single-line string"))
            else:
                diagnostics.append(Diagnostic("warning", prop_path, "raw property bypasses typed catalog validation"))
        if class_name == "MaterialFunctionCall":
            function_path = props.get("MaterialFunction")
            if not isinstance(function_path, str) or not function_path:
                diagnostics.append(Diagnostic("error", f"{node_path}.props.MaterialFunction", "MaterialFunctionCall requires a function object path"))
            elif _function_for_node(node, functions) is None:
                diagnostics.append(Diagnostic("error", f"{node_path}.props.MaterialFunction", "function path is not in the packaged function catalog", "add its input/output schema or paste a sample from the Editor"))

    parsed_links: list[Link] = []
    occupied_inputs: dict[tuple[str, str], int] = {}
    seen_links: dict[tuple[str, str | None, str, str], int] = {}
    connected: set[str] = set()
    graph: dict[str, set[str]] = {node_id: set() for node_id in normal_nodes}
    for index, raw_link in enumerate(links_value):
        link, parse_error = parse_link(raw_link, index)
        if parse_error:
            diagnostics.append(parse_error)
            continue
        assert link is not None
        path = f"$.links[{index}]"
        parsed_links.append(link)
        duplicate_key = (link.source_id, link.source_pin, link.destination_id, link.destination_pin)
        if duplicate_key in seen_links:
            diagnostics.append(Diagnostic("error", path, f"duplicate link; first occurrence is $.links[{seen_links[duplicate_key]}]"))
        else:
            seen_links[duplicate_key] = index
        endpoints_valid = True
        for endpoint_id, role in ((link.source_id, "source"), (link.destination_id, "destination")):
            if endpoint_id not in nodes:
                diagnostics.append(Diagnostic("error", path, f"unknown {role} node {endpoint_id!r}", _suggest(endpoint_id, nodes)))
                endpoints_valid = False
            elif endpoint_id not in normal_nodes:
                diagnostics.append(Diagnostic("error", path, f"Comment {endpoint_id!r} cannot be a link endpoint"))
                endpoints_valid = False
        if not endpoints_valid:
            continue
        source_node, source_entry = normal_nodes[link.source_id]
        destination_node, destination_entry = normal_nodes[link.destination_id]
        source_inputs, source_outputs = pin_schema(source_node, source_entry, functions)
        destination_inputs, destination_outputs = pin_schema(destination_node, destination_entry, functions)
        source_input_names = [effective_pin_name(pin, i, False) for i, pin in enumerate(source_inputs)]
        source_output_names = [effective_pin_name(pin, i, True) for i, pin in enumerate(source_outputs)]
        destination_input_names = [effective_pin_name(pin, i, False) for i, pin in enumerate(destination_inputs)]
        destination_output_names = [effective_pin_name(pin, i, True) for i, pin in enumerate(destination_outputs)]
        source_pin = link.source_pin or (source_output_names[0] if source_output_names else None)
        if source_pin is None:
            diagnostics.append(Diagnostic("error", path, f"class {source_node.get('class')!r} has no output pins"))
        elif source_pin not in source_output_names:
            if source_pin in source_input_names:
                diagnostics.append(Diagnostic("error", path, f"source pin {source_pin!r} is an input, not an output"))
            else:
                diagnostics.append(Diagnostic("error", path, f"unknown source output {source_pin!r}", _suggest(source_pin, source_output_names)))
        if link.destination_pin not in destination_input_names:
            if link.destination_pin in destination_output_names:
                diagnostics.append(Diagnostic("error", path, f"destination pin {link.destination_pin!r} is an output, not an input"))
            else:
                diagnostics.append(Diagnostic("error", path, f"unknown destination input {link.destination_pin!r}", _suggest(link.destination_pin, destination_input_names)))
        input_key = (link.destination_id, link.destination_pin)
        if input_key in occupied_inputs:
            diagnostics.append(Diagnostic("error", path, f"destination input already linked by $.links[{occupied_inputs[input_key]}]"))
        else:
            occupied_inputs[input_key] = index
        if source_pin in source_output_names and link.destination_pin in destination_input_names:
            connected.update((link.source_id, link.destination_id))
            graph[link.source_id].add(link.destination_id)

    if len(normal_nodes) > 1:
        for node_id in normal_nodes:
            if node_id not in connected:
                diagnostics.append(Diagnostic("warning", f"$.nodes.{node_id}", "isolated node has no valid links"))

    state: dict[str, int] = {node_id: 0 for node_id in graph}
    stack: list[str] = []
    reported_cycles: set[frozenset[str]] = set()

    def visit(node_id: str) -> None:
        state[node_id] = 1
        stack.append(node_id)
        for target in graph[node_id]:
            if state[target] == 0:
                visit(target)
            elif state[target] == 1:
                start = stack.index(target)
                cycle = stack[start:] + [target]
                key = frozenset(cycle)
                if key not in reported_cycles:
                    reported_cycles.add(key)
                    diagnostics.append(Diagnostic("warning", "$.links", "data cycle detected: " + " -> ".join(cycle)))
        stack.pop()
        state[node_id] = 2

    for node_id in graph:
        if state[node_id] == 0:
            visit(node_id)
    return ValidationResult(diagnostics)


def validate_text(
    text: str,
    catalog: dict[str, Any] | None = None,
    functions: dict[str, Any] | None = None,
) -> tuple[Any | None, ValidationResult]:
    document, load_diagnostics = load_document(text)
    if load_diagnostics:
        return None, ValidationResult(load_diagnostics)
    return document, validate_document(document, catalog, functions)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="MGJSON file, or - for stdin")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--functions", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
        catalog = load_catalog(args.catalog)
        functions = load_functions(args.functions)
        _, result = validate_text(text, catalog, functions)
    except (OSError, ValueError) as exc:
        print(f"error: $: {exc}", file=sys.stderr)
        return 1
    for item in result.diagnostics:
        print(item, file=sys.stderr if item.severity == "error" else sys.stdout)
    if result.ok:
        print(f"valid MGJSON ({len(result.warnings)} warning(s))")
        return 0
    print(f"invalid MGJSON ({len(result.errors)} error(s), {len(result.warnings)} warning(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
