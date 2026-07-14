#!/usr/bin/env python3
"""Parse Unreal Material Editor clipboard T3D into compact MGJSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import validate as mgvalidate
except ImportError:  # pragma: no cover - useful when imported as a package-like file
    mgvalidate = None


BEGIN_RE = re.compile(r"^\s*Begin Object(?:\s+(.*?))?\s*$")
END_RE = re.compile(r"^\s*End Object\s*$")
HEADER_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\"(?:\\.|[^\"])*\"|\S+)")
ALIASES = {
    "Constant": "const", "Constant2Vector": "const", "Constant3Vector": "const", "Constant4Vector": "const",
    "ScalarParameter": "scalar", "VectorParameter": "vector", "TextureCoordinate": "uv",
    "TextureSample": "tex", "TextureSampleParameter2D": "tex", "Multiply": "mul", "Add": "add",
    "LinearInterpolate": "lerp", "MaterialFunctionCall": "mf", "Comment": "comment",
}
IGNORED_EXPRESSION_PROPS = {
    "MaterialExpressionEditorX", "MaterialExpressionEditorY", "NodeGuid", "MaterialExpressionGuid",
    "ExpressionGUID", "Material", "Function", "GraphNode", "ExportPath", "SubgraphExpression",
}


class ParseError(RuntimeError):
    pass


@dataclass
class ObjectBlock:
    headers: dict[str, str]
    line: int
    properties: list[tuple[str, str]] = field(default_factory=list)
    pins: list[dict[str, Any]] = field(default_factory=list)
    children: list["ObjectBlock"] = field(default_factory=list)


@dataclass
class PinRecord:
    owner: str
    pin_id: str
    output: bool
    name: str
    index: int
    linked: list[tuple[str, str]]


@dataclass
class ParsedNode:
    graph_name: str
    class_name: str
    node_id: str
    graph: ObjectBlock
    expression: ObjectBlock | None
    mg_node: dict[str, Any]
    known: bool
    position: tuple[int, int] | None


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        body = value[1:-1]
        return (
            body.replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    return value


def split_top_level(value: str, delimiter: str = ",") -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    quote_char: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in {'"', "'"}:
            quote_char = char
        elif char in "([{" :
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == delimiter and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return [item for item in result if item]


def split_assignment(value: str) -> tuple[str, str] | None:
    depth = 0
    quote_char: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in {'"', "'"}:
            quote_char = char
        elif char in "([{" :
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == "=" and depth == 0:
            return value[:index].strip(), value[index + 1 :].strip()
    return None


def parse_headers(text: str) -> dict[str, str]:
    return {match.group(1): unquote(match.group(2)) for match in HEADER_RE.finditer(text)}


def parse_pin(text: str, line: int) -> dict[str, Any]:
    value = text.strip()
    if not value.startswith("(") or not value.endswith(")"):
        raise ParseError(f"line {line}: malformed CustomProperties Pin")
    fields: dict[str, str] = {}
    for part in split_top_level(value[1:-1]):
        assignment = split_assignment(part)
        if assignment:
            fields[assignment[0]] = assignment[1]
    pin_id = fields.get("PinId")
    if not pin_id:
        raise ParseError(f"line {line}: PinId is missing")
    linked: list[tuple[str, str]] = []
    linked_text = fields.get("LinkedTo")
    if linked_text and linked_text.startswith("(") and linked_text.endswith(")"):
        for reference in split_top_level(linked_text[1:-1]):
            pieces = reference.rsplit(None, 1)
            if len(pieces) == 2:
                linked.append((pieces[0], pieces[1]))
    return {
        "id": pin_id,
        "name": unquote(fields.get("PinName", '""')),
        "output": unquote(fields.get("Direction", '"EGPD_Input"')) == "EGPD_Output",
        "linked": linked,
    }


def parse_t3d(text: str) -> list[ObjectBlock]:
    roots: list[ObjectBlock] = []
    stack: list[ObjectBlock] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        begin = BEGIN_RE.match(raw_line)
        if begin:
            block = ObjectBlock(parse_headers(begin.group(1) or ""), line_number)
            if stack:
                stack[-1].children.append(block)
            else:
                roots.append(block)
            stack.append(block)
            continue
        if END_RE.match(raw_line):
            if not stack:
                raise ParseError(f"line {line_number}: unmatched End Object")
            stack.pop()
            continue
        if not stack or not raw_line.strip():
            continue
        stripped = raw_line.strip()
        prefix = "CustomProperties Pin "
        if stripped.startswith(prefix):
            stack[-1].pins.append(parse_pin(stripped[len(prefix) :], line_number))
            continue
        assignment = split_assignment(stripped)
        if assignment:
            stack[-1].properties.append(assignment)
    if stack:
        raise ParseError(f"line {stack[-1].line}: Begin Object has no matching End Object")
    return roots


def property_map(block: ObjectBlock | None) -> dict[str, str]:
    return dict(block.properties) if block else {}


def class_suffix(class_path: str) -> str:
    name = class_path.rsplit(".", 1)[-1]
    if name.startswith("U") and len(name) > 1 and name[1].isupper():
        name = name[1:]
    return name.removeprefix("MaterialExpression")


def expression_parts(graph: ObjectBlock) -> tuple[str | None, ObjectBlock | None]:
    declaration: ObjectBlock | None = None
    definition: ObjectBlock | None = None
    for child in graph.children:
        class_path = child.headers.get("Class", "")
        if "MaterialExpression" in class_path:
            declaration = child
            break
    if declaration:
        name = declaration.headers.get("Name")
        for child in graph.children:
            if child is not declaration and child.headers.get("Name") == name:
                definition = child
                break
        return declaration.headers.get("Class"), definition or declaration
    return None, None


def parse_generic(raw: str) -> Any:
    text = raw.strip()
    if text == "None":
        return None
    if text in {"True", "False"}:
        return text == "True"
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return unquote(text)
    if re.fullmatch(r"[-+]?\d+", text):
        try:
            return int(text)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", text):
        try:
            return float(text)
        except ValueError:
            pass
    if text.startswith("(") and text.endswith(")"):
        parts = split_top_level(text[1:-1])
        assignments = [split_assignment(part) for part in parts]
        if parts and all(item is not None for item in assignments):
            return {item[0]: parse_generic(item[1]) for item in assignments if item}
        return [parse_generic(part) for part in parts]
    return text


def parse_asset(raw: str) -> str | None:
    text = unquote(raw)
    if text == "None":
        return None
    match = re.search(r"'\"?([^']+?)\"?'$", text)
    return match.group(1) if match else text


def parse_typed(raw: str, spec: dict[str, Any]) -> Any:
    type_name = str(spec.get("type", "raw"))
    lower = type_name.lower()
    if lower.startswith("asset:"):
        return parse_asset(raw)
    if lower.startswith("enum:") or type_name.startswith("E"):
        return unquote(raw)
    value = parse_generic(raw)
    if type_name in {"FLinearColor", "FColor"} and isinstance(value, dict):
        return [value[key] for key in ("R", "G", "B", "A") if key in value]
    vector_keys = {
        "FVector2D": ("X", "Y"), "FIntPoint": ("X", "Y"),
        "FVector": ("X", "Y", "Z"), "FVector3f": ("X", "Y", "Z"),
        "FVector4": ("X", "Y", "Z", "W"), "FVector4f": ("X", "Y", "Z", "W"),
        "FVector4d": ("X", "Y", "Z", "W"),
    }
    if type_name in vector_keys and isinstance(value, dict):
        return [value[key] for key in vector_keys[type_name] if key in value]
    return value


def _is_default(value: Any, spec: dict[str, Any]) -> bool:
    return "default" in spec and value == spec["default"]


def extract_expression_props(
    class_name: str,
    expression: ObjectBlock | None,
    catalog: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    props: dict[str, Any] = {}
    raw_props: dict[str, str] = {}
    if not expression:
        return props, raw_props
    entry = catalog.get(class_name) if catalog else None
    prop_specs = entry.get("props", {}) if isinstance(entry, dict) else {}
    input_props = {
        pin.get("prop")
        for pin in (entry.get("inputs", []) if isinstance(entry, dict) else [])
        if isinstance(pin, dict)
    }
    for name, raw in expression.properties:
        base_name = name.split("(", 1)[0]
        if name in IGNORED_EXPRESSION_PROPS or base_name in {"FunctionInputs", "FunctionOutputs", "Outputs"}:
            continue
        # Connections are reconstructed exclusively from Pin.LinkedTo, even without a catalog.
        if re.match(r"^\(\s*Expression\s*=", raw):
            continue
        if name in input_props:
            continue
        spec = prop_specs.get(name) if isinstance(prop_specs, dict) else None
        if isinstance(spec, dict):
            value = parse_typed(raw, spec)
            if not _is_default(value, spec):
                props[name] = value
        else:
            raw_props[name] = raw
    return props, raw_props


def _integer_property(properties: dict[str, str], name: str) -> int | None:
    raw = properties.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _make_node_id(class_name: str, counts: dict[str, int]) -> str:
    base = ALIASES.get(class_name, class_name.lower())
    base = re.sub(r"[^A-Za-z0-9_-]", "", base) or "node"
    if not (base[0].isalpha() or base[0] == "_"):
        base = "node" + base
    counts[base] += 1
    return f"{base}{counts[base]}"


def _comment_props(graph: ObjectBlock, expression: ObjectBlock | None) -> dict[str, Any]:
    graph_props = property_map(graph)
    expression_props = property_map(expression)
    props: dict[str, Any] = {}
    text = graph_props.get("NodeComment", expression_props.get("Text"))
    if text is not None and unquote(text):
        props["Text"] = unquote(text)
    color = graph_props.get("CommentColor", expression_props.get("CommentColor"))
    if color is not None:
        value = parse_generic(color)
        if isinstance(value, dict):
            props["CommentColor"] = [value[key] for key in ("R", "G", "B", "A") if key in value]
    font = graph_props.get("FontSize", expression_props.get("FontSize"))
    if font is not None:
        try:
            props["FontSize"] = int(font)
        except ValueError:
            pass
    for name in ("bCommentBubbleVisible_InDetailsPanel", "bColorCommentBubble"):
        raw = graph_props.get(name, expression_props.get(name))
        if raw in {"True", "False"}:
            props[name] = raw == "True"
    move = graph_props.get("MoveMode")
    if move in {"GroupMovement", "NoGroupMovement"}:
        props["MoveMode"] = move
    width = _integer_property(graph_props, "NodeWidth") or _integer_property(expression_props, "SizeX")
    height = _integer_property(graph_props, "NodeHeight") or _integer_property(expression_props, "SizeY")
    if width:
        props["SizeX"] = width
    if height:
        props["SizeY"] = height
    return props


def _infer_comment_members(
    parsed_nodes: list[ParsedNode], positions: dict[str, tuple[int, int]],
) -> None:
    normal = [node for node in parsed_nodes if node.class_name != "Comment" and node.position]
    for comment in (node for node in parsed_nodes if node.class_name == "Comment" and node.position):
        props = comment.mg_node.setdefault("props", {})
        width = props.get("SizeX")
        height = props.get("SizeY")
        if not isinstance(width, int) or not isinstance(height, int):
            continue
        left, top = comment.position
        candidates = [
            node for node in normal
            if node.position
            and node.position[0] >= left and node.position[1] >= top
            and node.position[0] + 240 <= left + width
            and node.position[1] + 120 <= top + height
        ]
        if not candidates:
            continue
        bound_left = min(node.position[0] for node in candidates) - 80
        bound_top = min(node.position[1] for node in candidates) - 80
        bound_right = max(node.position[0] + 240 for node in candidates) + 80
        bound_bottom = max(node.position[1] + 120 for node in candidates) + 80
        if (left, top, left + width, top + height) == (bound_left, bound_top, bound_right, bound_bottom):
            props["nodes"] = [node.node_id for node in candidates]
            props.pop("SizeX", None)
            props.pop("SizeY", None)
            positions.pop(comment.node_id, None)


def convert_t3d(
    text: str,
    catalog: dict[str, Any] | None = None,
    keep_pos: bool = False,
) -> tuple[dict[str, Any], dict[str, int]]:
    roots = parse_t3d(text)
    graph_blocks = [block for block in roots if "MaterialGraphNode" in block.headers.get("Class", "")]
    counts: dict[str, int] = defaultdict(int)
    parsed_nodes: list[ParsedNode] = []
    graph_to_node: dict[str, ParsedNode] = {}
    positions: dict[str, tuple[int, int]] = {}
    unknown_count = 0
    raw_count = 0
    for graph in graph_blocks:
        graph_name = graph.headers.get("Name")
        graph_class = graph.headers.get("Class", "")
        if not graph_name or graph_class.endswith("MaterialGraphNode_Root"):
            continue
        expression_class, expression = expression_parts(graph)
        if graph_class.endswith("MaterialGraphNode_Comment"):
            class_name = "Comment"
        elif expression_class:
            class_name = class_suffix(expression_class)
        else:
            continue
        node_id = _make_node_id(class_name, counts)
        known = class_name == "Comment" or (catalog is not None and class_name in catalog)
        mg_node: dict[str, Any] = {"class": class_name}
        if class_name == "Comment":
            comment_props = _comment_props(graph, expression)
            if comment_props:
                mg_node["props"] = comment_props
        else:
            props, raw_props = extract_expression_props(class_name, expression, catalog)
            if props:
                mg_node["props"] = props
            if raw_props:
                mg_node["raw_props"] = raw_props
                raw_count += len(raw_props)
            if not known:
                unknown_count += 1
        graph_props = property_map(graph)
        x = _integer_property(graph_props, "NodePosX")
        y = _integer_property(graph_props, "NodePosY")
        position = (x, y) if x is not None and y is not None else None
        parsed = ParsedNode(graph_name, class_name, node_id, graph, expression, mg_node, known, position)
        parsed_nodes.append(parsed)
        graph_to_node[graph_name] = parsed
        if position:
            positions[node_id] = position

    pin_by_id: dict[str, PinRecord] = {}
    pins_by_owner: dict[str, list[PinRecord]] = defaultdict(list)
    for graph in graph_blocks:
        owner = graph.headers.get("Name")
        if not owner:
            continue
        direction_counts = {False: 0, True: 0}
        for raw_pin in graph.pins:
            output = bool(raw_pin["output"])
            record = PinRecord(
                owner, raw_pin["id"], output, raw_pin["name"], direction_counts[output], raw_pin["linked"]
            )
            direction_counts[output] += 1
            pin_by_id[record.pin_id] = record
            pins_by_owner[owner].append(record)

    def pin_name(pin: PinRecord) -> str:
        parsed = graph_to_node.get(pin.owner)
        fallback = f"{'out' if pin.output else 'in'}{pin.index}"
        if not parsed or not parsed.known or catalog is None:
            return fallback
        if parsed.class_name == "MaterialFunctionCall":
            return pin.name or fallback
        entry = catalog.get(parsed.class_name)
        if not isinstance(entry, dict):
            return fallback
        schema = list(entry.get("outputs", [])) if pin.output else list(entry.get("inputs", [])) + list(entry.get("prop_pins", []))
        if pin.index >= len(schema):
            return fallback
        return mgvalidate.effective_pin_name(schema[pin.index], pin.index, pin.output)

    links: list[str] = []
    seen_connections: set[tuple[str, str]] = set()
    for pin in pin_by_id.values():
        for linked_owner, linked_id in pin.linked:
            other = pin_by_id.get(linked_id)
            if not other or other.owner != linked_owner or pin.output == other.output:
                continue
            output_pin, input_pin = (pin, other) if pin.output else (other, pin)
            if output_pin.owner not in graph_to_node or input_pin.owner not in graph_to_node:
                continue
            key = tuple(sorted((output_pin.pin_id, input_pin.pin_id)))
            if key in seen_connections:
                continue
            seen_connections.add(key)
            source = graph_to_node[output_pin.owner]
            destination = graph_to_node[input_pin.owner]
            source_suffix = "" if output_pin.index == 0 else "." + pin_name(output_pin)
            links.append(f"{source.node_id}{source_suffix} -> {destination.node_id}.{pin_name(input_pin)}")

    _infer_comment_members(parsed_nodes, positions)
    document: dict[str, Any] = {"nodes": {node.node_id: node.mg_node for node in parsed_nodes}}
    if links:
        document["links"] = links
    if keep_pos and positions:
        document["pos"] = {node.node_id: list(positions[node.node_id]) for node in parsed_nodes if node.node_id in positions}
    stats = {
        "nodes": sum(node.class_name != "Comment" for node in parsed_nodes),
        "comments": sum(node.class_name == "Comment" for node in parsed_nodes),
        "links": len(links),
        "unknown_classes": unknown_count,
        "raw_props": raw_count,
    }
    return document, stats


def get_clipboard() -> str:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        fallback = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if fallback.exists():
            shell = str(fallback)
    if not shell:
        raise ParseError("neither pwsh nor powershell was found; pass a file or --stdin")
    command = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Get-Clipboard -Raw"
    completed = subprocess.run(
        [shell, "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise ParseError(completed.stderr.strip() or "Get-Clipboard failed")
    return completed.stdout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="T3D file; defaults to clipboard")
    parser.add_argument("--from-clipboard", action="store_true")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--no-catalog", action="store_true")
    parser.add_argument("--keep-pos", action="store_true")
    parser.add_argument("--stats", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if sum(bool(item) for item in (args.input, args.from_clipboard, args.stdin)) > 1:
        print("error: choose only one of file, --from-clipboard, or --stdin", file=sys.stderr)
        return 2
    try:
        if args.input:
            text = Path(args.input).read_text(encoding="utf-8-sig")
        elif args.stdin:
            text = sys.stdin.read()
        else:
            text = get_clipboard()
        if args.no_catalog:
            catalog = None
        else:
            if mgvalidate is None:
                raise ParseError("validate.py could not be imported; use --no-catalog")
            catalog = mgvalidate.load_catalog(args.catalog)
        document, stats = convert_t3d(text, catalog, args.keep_pos)
        if args.stats:
            print(" ".join(f"{key}={value}" for key, value in stats.items()))
        else:
            print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (OSError, ValueError, ParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
