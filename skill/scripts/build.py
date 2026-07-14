#!/usr/bin/env python3
"""Build Unreal Material Editor clipboard T3D from MGJSON."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import validate as mgvalidate


GUID_NAMESPACE = uuid.UUID("4c10a3bc-2267-47e2-a1b3-1198aaf9dc73")
NODE_WIDTH = 240
NODE_HEIGHT = 120
COMMENT_MARGIN = 80
# Expressions whose Editor graph node is a specialized subclass (matches real clipboard).
GRAPH_NODE_CLASSES = {"Custom": "/Script/UnrealEd.MaterialGraphNode_Custom"}


class BuildError(RuntimeError):
    pass


@dataclass
class NodeInfo:
    node_id: str
    document: dict[str, Any]
    catalog: dict[str, Any] | None
    graph_name: str
    expression_name: str
    expression_class: str
    position: tuple[int, int]
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    input_ids: list[str]
    output_ids: list[str]


@dataclass(frozen=True)
class ResolvedLink:
    source_id: str
    source_index: int
    destination_id: str
    destination_index: int


def deterministic_guid(label: str) -> str:
    return uuid.uuid5(GUID_NAMESPACE, label).hex.upper()


def quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def number_text(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if value == 0:
        return "0.0"
    result = format(value, ".15g")
    return result if any(char in result for char in ".eE") else result + ".0"


def struct_text(keys: list[str], values: list[Any]) -> str:
    return "(" + ",".join(f"{key}={number_text(value)}" for key, value in zip(keys, values)) + ")"


def asset_class_path(type_name: str) -> str:
    raw = type_name.split(":", 1)[1] if ":" in type_name else type_name
    raw = raw.removeprefix("TSoftObjectPtr<").removesuffix(">")
    if raw.startswith("U") and len(raw) > 1 and raw[1].isupper():
        raw = raw[1:]
    aliases = {
        "MaterialFunctionInterface": "MaterialFunction",
        "Texture": "Texture",
        "Object": "Object",
    }
    class_name = aliases.get(raw, raw)
    module = "CoreUObject" if class_name == "Object" else "Engine"
    return f"/Script/{module}.{class_name}"


def serialize_generic(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return number_text(value)
    if isinstance(value, str):
        return quote(value)
    if isinstance(value, list):
        return "(" + ",".join(serialize_generic(item) for item in value) + ")"
    if isinstance(value, dict):
        return "(" + ",".join(f"{key}={serialize_generic(item)}" for key, item in value.items()) + ")"
    raise BuildError(f"cannot serialize property value of type {type(value).__name__}")


def serialize_property(value: Any, spec: dict[str, Any]) -> str:
    type_name = str(spec.get("type", "raw"))
    lower = type_name.lower()
    if value is None:
        return "None"
    if lower in {"float", "double"} or lower.startswith(("int", "uint")):
        return number_text(value)
    if lower == "bool":
        return "True" if value else "False"
    if type_name in {"FName", "FString", "FText"}:
        return quote(value)
    if lower.startswith("enum:") or type_name.startswith("E"):
        return value
    if lower.startswith("asset:"):
        reference = "{0}'{1}'".format(asset_class_path(type_name), value)
        return quote(reference)
    if type_name in {"FLinearColor", "FColor"}:
        values = list(value)
        if len(values) == 3:
            default = spec.get("default")
            alpha = default[3] if isinstance(default, list) and len(default) == 4 else 1.0
            values.append(alpha)
        return struct_text(["R", "G", "B", "A"], values)
    keys = {
        "FVector2D": ["X", "Y"],
        "FIntPoint": ["X", "Y"],
        "FVector": ["X", "Y", "Z"],
        "FVector3f": ["X", "Y", "Z"],
        "FVector4": ["X", "Y", "Z", "W"],
        "FVector4f": ["X", "Y", "Z", "W"],
        "FVector4d": ["X", "Y", "Z", "W"],
    }
    if type_name in keys:
        return struct_text(keys[type_name], list(value))
    if type_name == "FGuid":
        return value.upper()
    return serialize_generic(value)


def indexed_array_lines(name: str, value: list[Any], spec: dict[str, Any]) -> list[str]:
    """Emit a TArray property the way UE clipboard T3D does: one Name(index)=... line
    per element. Struct elements use the catalog 'struct' field schema; fields that
    are not in the schema round-trip through serialize_generic unchanged."""
    if not value:
        return [f"      {name}=()"]
    struct_spec = spec.get("struct") if isinstance(spec.get("struct"), dict) else None
    lines: list[str] = []
    for index, item in enumerate(value):
        if struct_spec is None or not isinstance(item, dict):
            lines.append(f"      {name}({index})={serialize_generic(item)}")
            continue
        ordered = [key for key in struct_spec if key in item]
        ordered += [key for key in item if key not in struct_spec]
        fields = []
        for key in ordered:
            field_spec = struct_spec.get(key)
            if isinstance(field_spec, dict):
                fields.append(f"{key}={serialize_property(item[key], field_spec)}")
            else:
                fields.append(f"{key}={serialize_generic(item[key])}")
        lines.append(f"      {name}({index})=({','.join(fields)})")
    return lines


def compute_positions(document: dict[str, Any], links: list[mgvalidate.Link]) -> dict[str, tuple[int, int]]:
    nodes = document["nodes"]
    normal_ids = [node_id for node_id, node in nodes.items() if node.get("class") != "Comment"]
    order = {node_id: index for index, node_id in enumerate(normal_ids)}
    successors: dict[str, set[str]] = {node_id: set() for node_id in normal_ids}
    predecessors: dict[str, set[str]] = {node_id: set() for node_id in normal_ids}
    for link in links:
        if link.source_id in successors and link.destination_id in successors:
            successors[link.source_id].add(link.destination_id)
            predecessors[link.destination_id].add(link.source_id)
    indegree = {node_id: len(predecessors[node_id]) for node_id in normal_ids}
    queue = deque(node_id for node_id in normal_ids if indegree[node_id] == 0)
    depth = {node_id: 0 for node_id in normal_ids}
    processed: set[str] = set()
    while queue:
        node_id = queue.popleft()
        processed.add(node_id)
        for target in sorted(successors[node_id], key=order.get):
            depth[target] = max(depth[target], depth[node_id] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    for node_id in normal_ids:
        if node_id not in processed:
            external = [depth[item] for item in predecessors[node_id] if item in processed]
            depth[node_id] = max(external, default=-1) + 1
    rows: dict[int, int] = defaultdict(int)
    result: dict[str, tuple[int, int]] = {}
    explicit = document.get("pos", {})
    for node_id in normal_ids:
        if node_id in explicit:
            result[node_id] = tuple(explicit[node_id])
        else:
            column = depth[node_id]
            result[node_id] = (column * 300, rows[column] * 180)
            rows[column] += 1
    for node_id, node in nodes.items():
        if node.get("class") != "Comment":
            continue
        props = node.get("props", {})
        contained = props.get("nodes")
        if contained:
            left = min(result[item][0] for item in contained)
            top = min(result[item][1] for item in contained)
            result[node_id] = (left - COMMENT_MARGIN, top - COMMENT_MARGIN)
        elif node_id in explicit:
            result[node_id] = tuple(explicit[node_id])
        else:
            result[node_id] = (0, rows[0] * 180)
            rows[0] += 1
    return result


def _comment_size(node: dict[str, Any], positions: dict[str, tuple[int, int]]) -> tuple[int, int]:
    props = node.get("props", {})
    contained = props.get("nodes")
    if contained:
        left = min(positions[item][0] for item in contained)
        top = min(positions[item][1] for item in contained)
        right = max(positions[item][0] + NODE_WIDTH for item in contained)
        bottom = max(positions[item][1] + NODE_HEIGHT for item in contained)
        return right - left + COMMENT_MARGIN * 2, bottom - top + COMMENT_MARGIN * 2
    return int(props.get("SizeX", 400)), int(props.get("SizeY", 200))


def _resolve_links(
    document: dict[str, Any], infos: dict[str, NodeInfo]
) -> tuple[list[ResolvedLink], list[mgvalidate.Link]]:
    raw_links: list[mgvalidate.Link] = []
    resolved: list[ResolvedLink] = []
    for index, value in enumerate(document.get("links", [])):
        link, error = mgvalidate.parse_link(value, index)
        if error or link is None:
            raise BuildError(str(error))
        raw_links.append(link)
        source = infos[link.source_id]
        destination = infos[link.destination_id]
        output_names = [mgvalidate.effective_pin_name(pin, i, True) for i, pin in enumerate(source.outputs)]
        input_names = [mgvalidate.effective_pin_name(pin, i, False) for i, pin in enumerate(destination.inputs)]
        source_index = 0 if link.source_pin is None else output_names.index(link.source_pin)
        destination_index = input_names.index(link.destination_pin)
        resolved.append(ResolvedLink(link.source_id, source_index, link.destination_id, destination_index))
    return resolved, raw_links


def _make_infos(
    document: dict[str, Any],
    catalog: dict[str, Any],
    functions: dict[str, Any],
) -> tuple[dict[str, NodeInfo], list[mgvalidate.Link]]:
    parsed: list[mgvalidate.Link] = []
    for index, raw in enumerate(document.get("links", [])):
        link, _ = mgvalidate.parse_link(raw, index)
        if link:
            parsed.append(link)
    positions = compute_positions(document, parsed)
    infos: dict[str, NodeInfo] = {}
    for index, (node_id, node) in enumerate(document["nodes"].items()):
        class_name = node["class"]
        is_comment = class_name == "Comment"
        entry = None if is_comment else catalog[class_name]
        graph_name = f"MaterialGraphNode_{index}"
        if is_comment:
            expression_class = "/Script/Engine.MaterialExpressionComment"
            expression_name = f"MaterialExpressionComment_{index}"
            inputs: list[dict[str, Any]] = []
            outputs: list[dict[str, Any]] = []
        else:
            assert entry is not None
            expression_class = entry["class"]
            expression_name = f"{expression_class.rsplit('.', 1)[-1]}_{index}"
            inputs, outputs = mgvalidate.pin_schema(node, entry, functions)
        infos[node_id] = NodeInfo(
            node_id=node_id,
            document=node,
            catalog=entry,
            graph_name=graph_name,
            expression_name=expression_name,
            expression_class=expression_class,
            position=positions[node_id],
            inputs=inputs,
            outputs=outputs,
            input_ids=[deterministic_guid(f"pin:{node_id}:input:{i}") for i in range(len(inputs))],
            output_ids=[deterministic_guid(f"pin:{node_id}:output:{i}") for i in range(len(outputs))],
        )
    return infos, parsed


def _linked_references(
    infos: dict[str, NodeInfo], links: list[ResolvedLink]
) -> dict[tuple[str, str, int], list[str]]:
    result: dict[tuple[str, str, int], list[str]] = defaultdict(list)
    for link in links:
        source = infos[link.source_id]
        destination = infos[link.destination_id]
        result[(link.source_id, "output", link.source_index)].append(
            f"{destination.graph_name} {destination.input_ids[link.destination_index]}"
        )
        result[(link.destination_id, "input", link.destination_index)].append(
            f"{source.graph_name} {source.output_ids[link.source_index]}"
        )
    return result


def _pin_line(
    pin_id: str,
    name: str,
    output: bool,
    linked: list[str],
) -> str:
    fields = [f"PinId={pin_id}", f"PinName={quote(name)}"]
    if output:
        fields.append('Direction="EGPD_Output"')
    if linked:
        fields.append("LinkedTo=(" + "".join(item + "," for item in linked) + ")")
    return "   CustomProperties Pin (" + ",".join(fields) + ",)"


def _object_reference(info: NodeInfo, nested_path: bool = False) -> str:
    path = f"{info.graph_name}.{info.expression_name}" if nested_path else info.expression_name
    return quote(f"{info.expression_class}'{path}'")


def _function_lines(info: NodeInfo, functions: dict[str, Any]) -> list[str]:
    function = mgvalidate._function_for_node(info.document, functions)
    if not function:
        return []
    result: list[str] = []
    for index, pin in enumerate(function.get("inputs", [])):
        guid = str(pin.get("id") or deterministic_guid(f"mf:{info.node_id}:input:{index}"))
        result.append(
            f"      FunctionInputs({index})=(ExpressionInputId={guid.upper()},"
            f"Input=(OutputIndex=-1,InputName={quote(pin['name'])}))"
        )
    for index, pin in enumerate(function.get("outputs", [])):
        guid = str(pin.get("id") or deterministic_guid(f"mf:{info.node_id}:output:{index}"))
        result.append(
            f"      FunctionOutputs({index})=(ExpressionOutputId={guid.upper()},"
            f"Output=(OutputName={quote(pin['name'])}))"
        )
        result.append(f"      Outputs({index})=(OutputName={quote(pin['name'])})")
    return result


def _expression_lines(
    info: NodeInfo,
    links: list[ResolvedLink],
    infos: dict[str, NodeInfo],
    functions: dict[str, Any],
) -> list[str]:
    node = info.document
    entry = info.catalog or {}
    lines: list[str] = []
    props = node.get("props", {})
    prop_catalog = entry.get("props", {})
    for name, value in props.items():
        spec = prop_catalog[name]
        if str(spec.get("type", "")).lower().startswith("tarray<") and isinstance(value, list):
            lines.extend(indexed_array_lines(name, value, spec))
        else:
            lines.append(f"      {name}={serialize_property(value, spec)}")
    for name, value in node.get("raw_props", {}).items():
        lines.append(f"      {name}={value}")
    if node.get("class") == "MaterialFunctionCall":
        lines.extend(_function_lines(info, functions))
    else:
        ordinary_count = len(entry.get("inputs", []))
        for link in links:
            if link.destination_id != info.node_id or link.destination_index >= ordinary_count:
                continue
            input_pin = info.inputs[link.destination_index]
            prop = input_pin.get("prop")
            if not prop:
                continue
            source = infos[link.source_id]
            fields = [f"Expression={_object_reference(source, nested_path=True)}"]
            if link.source_index:
                fields.append(f"OutputIndex={link.source_index}")
            lines.append(f"      {prop}=({','.join(fields)})")
    x, y = info.position
    lines.extend(
        [
            f"      MaterialExpressionEditorX={x}",
            f"      MaterialExpressionEditorY={y}",
            f"      MaterialExpressionGuid={deterministic_guid('expression:' + info.node_id)}",
        ]
    )
    return lines


def _normal_block(
    info: NodeInfo,
    links: list[ResolvedLink],
    linked: dict[tuple[str, str, int], list[str]],
    infos: dict[str, NodeInfo],
    functions: dict[str, Any],
) -> list[str]:
    graph_class = GRAPH_NODE_CLASSES.get(str(info.document.get("class")), "/Script/UnrealEd.MaterialGraphNode")
    lines = [
        f'Begin Object Class={graph_class} Name={quote(info.graph_name)}',
        f"   Begin Object Class={info.expression_class} Name={quote(info.expression_name)}",
        "   End Object",
        f"   Begin Object Name={quote(info.expression_name)}",
    ]
    lines.extend(_expression_lines(info, links, infos, functions))
    lines.extend(
        [
            "   End Object",
            f"   MaterialExpression={_object_reference(info)}",
            f"   NodePosX={info.position[0]}",
            f"   NodePosY={info.position[1]}",
            f"   NodeGuid={deterministic_guid('node:' + info.node_id)}",
        ]
    )
    for index, pin in enumerate(info.inputs):
        name = mgvalidate.effective_pin_name(pin, index, False)
        lines.append(
            _pin_line(
                info.input_ids[index], name, False,
                linked[(info.node_id, "input", index)],
            )
        )
    for index, pin in enumerate(info.outputs):
        name = mgvalidate.effective_pin_name(pin, index, True)
        lines.append(
            _pin_line(
                info.output_ids[index], name, True,
                linked[(info.node_id, "output", index)],
            )
        )
    lines.append("End Object")
    return lines


def _comment_block(info: NodeInfo, positions: dict[str, tuple[int, int]]) -> list[str]:
    props = info.document.get("props", {})
    width, height = _comment_size(info.document, positions)
    text = props.get("Text", "")
    color = props.get("CommentColor")
    if color and len(color) == 3:
        color = list(color) + [1.0]
    font_size = props.get("FontSize")
    bubble = props.get("bCommentBubbleVisible_InDetailsPanel")
    color_bubble = props.get("bColorCommentBubble")
    move_mode = props.get("MoveMode")
    lines = [
        f'Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Comment Name={quote(info.graph_name)}',
        f"   Begin Object Class={info.expression_class} Name={quote(info.expression_name)}",
        "   End Object",
        f"   Begin Object Name={quote(info.expression_name)}",
        f"      SizeX={width}",
        f"      SizeY={height}",
    ]
    if text:
        lines.append(f"      Text={quote(text)}")
    if color:
        lines.append(f"      CommentColor={struct_text(['R', 'G', 'B', 'A'], color)}")
    if font_size is not None:
        lines.append(f"      FontSize={font_size}")
    if bubble is not None:
        lines.append(f"      bCommentBubbleVisible_InDetailsPanel={'True' if bubble else 'False'}")
    if color_bubble is not None:
        lines.append(f"      bColorCommentBubble={'True' if color_bubble else 'False'}")
    if move_mode is not None:
        lines.append(f"      bGroupMode={'True' if move_mode == 'GroupMovement' else 'False'}")
    lines.extend(
        [
            "   End Object",
            f"   MaterialExpressionComment={_object_reference(info)}",
            f"   NodePosX={info.position[0]}",
            f"   NodePosY={info.position[1]}",
            f"   NodeWidth={width}",
            f"   NodeHeight={height}",
        ]
    )
    if text:
        lines.append(f"   NodeComment={quote(text)}")
    if color:
        lines.append(f"   CommentColor={struct_text(['R', 'G', 'B', 'A'], color)}")
    if font_size is not None:
        lines.append(f"   FontSize={font_size}")
    if bubble is not None:
        lines.append(f"   bCommentBubbleVisible_InDetailsPanel={'True' if bubble else 'False'}")
    if color_bubble is not None:
        lines.append(f"   bColorCommentBubble={'True' if color_bubble else 'False'}")
    if move_mode is not None:
        lines.append(f"   MoveMode={move_mode}")
    lines.extend([f"   NodeGuid={deterministic_guid('node:' + info.node_id)}", "End Object"])
    return lines


def build_t3d(
    document: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    functions: dict[str, Any] | None = None,
) -> str:
    catalog = catalog if catalog is not None else mgvalidate.load_catalog()
    functions = functions if functions is not None else mgvalidate.load_functions()
    validation = mgvalidate.validate_document(document, catalog, functions)
    if not validation.ok:
        raise BuildError("MGJSON validation failed:\n" + "\n".join(str(item) for item in validation.errors))
    infos, _ = _make_infos(document, catalog, functions)
    resolved, _ = _resolve_links(document, infos)
    linked = _linked_references(infos, resolved)
    positions = {node_id: info.position for node_id, info in infos.items()}
    lines: list[str] = []
    for info in infos.values():
        if info.document.get("class") == "Comment":
            lines.extend(_comment_block(info, positions))
        else:
            lines.extend(_normal_block(info, resolved, linked, infos, functions))
    return "\n".join(lines) + "\n"


def set_clipboard(text: str) -> str:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        fallback = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if fallback.exists():
            shell = str(fallback)
    if not shell:
        raise BuildError("neither pwsh nor powershell was found; use --stdout or -o FILE")
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".t3d", delete=False) as handle:
            handle.write(text)
            temp_path = handle.name
        command = "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:UE_MATERIAL_T3D_FILE | Set-Clipboard"
        environment = os.environ.copy()
        environment["UE_MATERIAL_T3D_FILE"] = temp_path
        completed = subprocess.run(
            [shell, "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise BuildError(f"clipboard command failed ({Path(shell).name}): {detail}")
        return Path(shell).name
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="MGJSON file, or - for stdin")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--functions", type=Path)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("-o", "--output", type=Path)
    output.add_argument("--stdout", action="store_true")
    output.add_argument("--to-clipboard", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
        catalog = mgvalidate.load_catalog(args.catalog)
        functions = mgvalidate.load_functions(args.functions)
        document, result = mgvalidate.validate_text(source, catalog, functions)
        for warning in result.warnings:
            print(warning, file=sys.stderr)
        if not result.ok or document is None:
            for error in result.errors:
                print(error, file=sys.stderr)
            print("build aborted; no T3D was emitted", file=sys.stderr)
            return 1
        text = build_t3d(document, catalog, functions)
        if args.output:
            args.output.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {args.output}", file=sys.stderr)
        elif args.stdout:
            sys.stdout.write(text)
        else:
            shell = set_clipboard(text)
            print(f"copied {len(document['nodes'])} node(s) to clipboard using {shell}")
        return 0
    except (OSError, ValueError, BuildError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
