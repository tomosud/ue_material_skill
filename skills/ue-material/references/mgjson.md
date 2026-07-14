# MGJSON Reference

MGJSON is the compact, conversational representation used by this skill for Unreal Material graphs.
`validate.py`, `build.py`, and `parse.py` are the implementation authority for this format. MGJSON omits
clipboard-only GUIDs, object names, owner references, and most Pin serialization fields.

This document specifies the local format. It does not make a node behavior claim. Consult
`source-verification.md` and the node evidence catalog before using a class or Pin schema for generation.

## Document shape

```ebnf
document      = object containing "nodes" [and "links"] [and "pos"] ;
nodes         = object { node-id : node } ;
links         = array of link-string ;
pos           = object { node-id : [x, y] } ;
normal-node   = { "class": class-name,
                  ["props": object], ["raw_props": object] } ;
comment-node  = { "class": "Comment", ["props": comment-props] } ;
```

- The document is a UTF-8 JSON object.
- `nodes` is required and must be a non-empty object.
- `links` is optional and defaults to an empty array.
- `pos` is optional; omitted positions use the builder's automatic layout.
- Unknown keys and duplicate JSON object keys are errors.

Node IDs are local labels and must match:

```regex
^[A-Za-z_][A-Za-z0-9_-]*$
```

They are case-sensitive and are unrelated to Unreal object names or GUIDs. Periods, spaces, and `->` are
excluded to keep link parsing unambiguous.

## Nodes

```json
{
  "class": "Multiply",
  "props": {"ConstB": 0.5},
  "raw_props": {"FutureProperty": "(X=1.0,Y=2.0)"}
}
```

- `class` is the catalog short name, without the `MaterialExpression` prefix.
- `props` contains typed values whose names and types are declared by the catalog.
- `raw_props` contains single-line T3D right-hand-side strings for properties that are not typed in the
  catalog.
- The same property cannot occur in both `props` and `raw_props`.
- `parse.py` may omit values that deep-equal a catalog default.

An unknown class can be preserved by `parse.py` for investigation, but `validate.py` and `build.py` reject it
because no safe Pin schema is available. `raw_props` is an escape hatch for properties, not for unknown Pins.
Abstract classes are errors. Deprecated classes produce warnings.

## Typed property values

| Catalog type | MGJSON value |
|---|---|
| `float`, `double` | finite JSON number |
| signed or unsigned integer | JSON integer |
| `bool` | JSON boolean |
| `FName`, `FString`, `FText` | JSON string |
| `enum:EType` | enum value-name string |
| `asset:Type` | Unreal object path string or `null` |
| `FLinearColor`, `FColor` | three- or four-number array |
| `FVector2D`, `FIntPoint` | two-number array |
| `FVector`, `FVector3f` | three-number array |
| `FVector4`, `FVector4f` | four-number array |
| `FGuid` | 32 hexadecimal characters |

Three-component colors use the catalog alpha default when available, otherwise `1.0`. Color values are not
clamped to 0–1. Every numeric component must be finite.

Asset values normally use a complete object path such as `/Game/Textures/T_Base.T_Base`. `/Game`, `/Engine`,
and plugin mount paths are syntactically accepted. `null` means no asset. Validation checks syntax and catalog
type, not asset existence; existence requires the target project's Asset Registry or Unreal Editor.

Enum values use their exact Unreal token, not an integer or localized label. A catalog choice list is enforced
when present. Without a choice list, validation can check only that the value is a non-empty string and emits a
warning.

`raw_props` names must match:

```regex
^[A-Za-z_][A-Za-z0-9_]*(?:\([0-9]+\))?$
```

Values cannot contain a newline. The builder emits them without interpreting or requoting the right-hand side.
Environment-owned properties such as `Material`, `Function`, `GraphNode`, editor coordinates, and generated
GUIDs must not be carried through `raw_props`.

## Links

Canonical syntax is:

```text
source[.output] -> destination.input
```

- Omitting the source output selects output index 0.
- The destination input is required.
- Extra whitespace around the arrow is accepted and normalized.
- One destination input accepts at most one link; outputs may fan out.
- Duplicate links are errors. Data cycles are warnings.
- A Comment cannot be a link endpoint.
- The Material Root is not represented. The user connects final outputs to Root inputs after paste.

Effective input names are resolved in this order: non-empty `name`, `prop`, then `in<index>`. Effective output
names are resolved as non-empty `name`, `mask`, `Output` for index 0, then `out<index>`. A source-audited catalog
entry may use internal clipboard names such as `Output2`; do not replace those names with a semantic channel
label.

Input order is `inputs` followed by `prop_pins`. Output order is the catalog `outputs` order. These orders are
part of the clipboard reconstruction contract and cannot be rearranged for presentation.

## Positions and comments

`pos` maps a node ID to an integer `[x, y]`. Unknown IDs and non-integer coordinates are errors. Explicit
positions are preserved. Missing positions are assigned by `build.py` using graph depth and document order.
`parse.py` discards positions unless `--keep-pos` is used.

Comment is a reserved local class. Its supported properties are:

| Property | Type |
|---|---|
| `Text` | string |
| `nodes` | unique, non-empty array of normal-node IDs |
| `CommentColor` | three- or four-number color |
| `FontSize` | positive integer |
| `bCommentBubbleVisible_InDetailsPanel` | boolean |
| `bColorCommentBubble` | boolean |
| `MoveMode` | `GroupMovement` or `NoGroupMovement` |
| `SizeX`, `SizeY` | positive integers for an ungrouped frame |

For a grouped Comment, the builder computes the frame from contained node positions. An explicit Comment
position or size conflicts with computed grouping and is rejected. An ungrouped Comment may use `pos` and size.
A Comment cannot contain itself, another Comment, or a missing node.

## Dynamic Pins

`Custom` derives its Pins from node properties rather than static catalog arrays. Read
`custom-expressions.md` before creating one. Its source-checked rules, 32-parameter Material IR limit, shader
include mappings, Scene Texture fixup, and private-API warnings are maintained there rather than duplicated
here.

`MaterialFunctionCall` derives Pins from the function catalog. Read `mf-call.md`. Function catalog entries are
parsing support unless their exact path and Pin schema have separate asset or Editor evidence.

## Validation behavior

Errors prevent generation and return exit code 1. Warnings preserve representable input but identify risk or
missing evidence. Major error classes are:

1. invalid JSON, duplicate keys, unknown keys, or an invalid document shape;
2. invalid node IDs, unknown or abstract classes, and invalid typed or raw properties;
3. invalid positions or Comment containment;
4. malformed links, unknown endpoints or Pins, reversed Pin direction, duplicate links, or multiple links to
   one input;
5. class-specific validation failures, including source-checked Custom rules.

Warnings include deprecation, isolated nodes, cycles, unchecked enum values, raw properties, unresolved asset
existence, incomplete source audits, and incomplete Unreal Editor evidence. Source and Editor evidence are
reported independently.

`build.py` calls validation and emits no T3D when any error is present.

## Parse normalization

`parse.py` performs these normalizations:

1. discard the Material Root and links that terminate only at the Root;
2. derive the short class from the Material Expression class;
3. assign deterministic local node IDs from class aliases and T3D order;
4. reconstruct internal links from Pin `LinkedTo` records and deduplicate reciprocal records;
5. use audited catalog Pin names when a schema matches, otherwise use `in<index>` and `out<index>`;
6. convert known property text to typed MGJSON and preserve unknown properties in `raw_props`;
7. omit environment-owned coordinates, GUIDs, owner pointers, and reproducible derived fields;
8. retain positions only with `--keep-pos`.

`--stats` reports counts rather than MGJSON. Unknown external Pin references are discarded because copied
selections can legitimately contain links to nodes outside the selection.

## Source-audited example

The classes and Pins in this example have source references in `catalog/node-evidence.json`.

```json
{
  "nodes": {
    "a": {"class": "Constant", "props": {"R": 0.25}},
    "b": {"class": "Constant", "props": {"R": 2.0}},
    "multiply": {"class": "Multiply"},
    "bias": {"class": "Add", "props": {"ConstB": 0.1}}
  },
  "links": [
    "a -> multiply.A",
    "b -> multiply.B",
    "multiply -> bias.A"
  ]
}
```
