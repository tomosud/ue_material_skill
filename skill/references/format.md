# Material Editor Clipboard T3D

This reference defines the UE 5.8 Material Editor clipboard subset consumed by `parse.py` and emitted by
`build.py`. Ordinary work should remain in MGJSON; read this file only when debugging or extending clipboard
conversion.

## Evidence boundary

The object and Pin reconstruction rules below were checked against the configured UE 5.8 source root. A source
path proves implementation structure, not a successful Editor paste. Actual copy, paste, and round-trip results
are recorded separately in `skill/catalog/editor-evidence.json`.

| Concern | Source-relative path and symbol |
|---|---|
| Material Editor copy entry | `Engine/Source/Editor/MaterialEditor/Private/MaterialEditor.cpp` — `FMaterialEditor::CopySelectedNodes` |
| Material Editor paste entry | same file — `FMaterialEditor::PasteNodesHereFromBuffer` |
| Graph export/import | `Engine/Source/Editor/UnrealEd/Private/EdGraphUtilities.cpp` — `FEdGraphUtilities::ExportNodesToText`, `ImportNodesFromText` |
| Expression reparenting for copy | `Engine/Source/Editor/UnrealEd/Private/MaterialGraphNode.cpp` — `UMaterialGraphNode::PrepareForCopying` |
| Two-pass object import | `Engine/Source/Editor/UnrealEd/Private/EditorFactories.cpp` — `FCustomizableTextObjectFactory::ProcessBuffer` |
| Pin text import/export | `Engine/Source/Runtime/Engine/Private/EdGraph/EdGraphPin.cpp` — `UEdGraphPin::ImportTextItem`, `ExportTextItem` |
| Pin reference text | same file — `UEdGraphPin::ExportText_PinReference` |
| Post-paste Pin indexing and reconstruction | `Engine/Source/Editor/UnrealEd/Private/MaterialGraphNode_Base.cpp` — `PostPasteNode`, `ReconstructNode` |
| Material input and output Pin creation | `Engine/Source/Editor/UnrealEd/Private/MaterialGraphNode.cpp` — `CreateInputPins`, `CreateOutputPins` |
| Graph links applied to expressions | `Engine/Source/Editor/UnrealEd/Private/MaterialGraph.cpp` — `LinkMaterialExpressionsFromGraph` |
| Class-specific paste handling | `Engine/Source/Editor/MaterialEditor/Private/MaterialEditor.cpp` — `PostPasteMaterialExpression` |

## Object structure

T3D is line-oriented, but nesting must be parsed with a `Begin Object` / `End Object` stack rather than by
indentation.

```ebnf
document       = { graph-node-block } ;
object-block   = begin-line, { property-line | custom-line | object-block }, end-line ;
begin-line     = ws, "Begin Object", header-fields, newline ;
end-line       = ws, "End Object", newline ;
property-line  = ws, property-name, "=", raw-value, newline ;
custom-line    = ws, "CustomProperties Pin ", pin-struct, newline ;
```

Values may contain nested parentheses, commas, equals signs, quotes, and object references. A parser cannot
split them with an unqualified comma or equals operation. UObject export commonly omits values equal to the
Class Default Object; absence usually means a class default, not an unknown value.

An ordinary Material graph node contains two blocks for the same child expression: a declaration with `Class`
and `Name`, followed by a definition with the same `Name` and its property differences.

```text
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_0"
   Begin Object Class=/Script/Engine.MaterialExpressionMultiply Name="MaterialExpressionMultiply_0"
   End Object
   Begin Object Name="MaterialExpressionMultiply_0"
      ...expression properties...
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionMultiply'MaterialExpressionMultiply_0'"
   ...graph properties and Pins...
End Object
```

Those child blocks describe one object. The parser joins them by parent scope and `Name`. The builder always
emits this two-block form.

## Ordinary graph nodes and expressions

The default graph class is `/Script/UnrealEd.MaterialGraphNode`. Use a subclass only when a source-audited
catalog entry or an Editor sample requires it.

Required builder structure:

1. a top-level graph node with unique `Class` and `Name`;
2. the child Material Expression declaration and definition;
3. `MaterialExpression=<object-reference>` linking the graph node to that child;
4. every input and output Pin in source order;
5. `NodePosX` and `NodePosY` when relative layout matters.

The expression class is `/Script/<Module>.MaterialExpression<ClassSuffix>` as recorded in the source-derived
manifest. Emit typed catalog properties or approved `raw_props` in the expression definition. Do not emit
environment-owned `Material`, `Function`, `GraphNode`, or destination Root pointers.

`MaterialExpressionEditorX/Y`, graph positions, and temporary GUIDs may be emitted for shape compatibility,
but the Editor reassigns or resynchronizes them after paste. The builder uses deterministic temporary GUIDs;
they are not asset identity.

An `FExpressionInput` may also be serialized on the expression:

```text
A=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_0.MaterialExpressionConstant_0'")
A=(Expression="/Script/Engine.MaterialExpressionConstant3Vector'MaterialGraphNode_1.MaterialExpressionConstant3Vector_0'",OutputIndex=1)
```

The builder emits this redundant form, but Pin `LinkedTo` records are the connection authority. `OutputIndex=0`
may be omitted.

Asset object references quote the complete value:

```text
Texture="/Script/Engine.Texture2D'/Game/T_x.T_x'"
```

Syntax validation cannot prove that the object exists in the target project.

## Comment nodes

The local Comment representation maps to:

```text
graph class: /Script/UnrealEd.MaterialGraphNode_Comment
child class: /Script/Engine.MaterialExpressionComment
pointer:    MaterialExpressionComment=<object-reference>
```

The graph node holds the paste-authoritative frame position, dimensions, text, color, bubble settings, and move
mode. The child expression may mirror those values. `LinkMaterialExpressionsFromGraph` copies graph Comment
state back to the expression. Comments have no Pins.

## Pin serialization

Each Pin is a `CustomProperties Pin` line:

```text
CustomProperties Pin (PinId=00112233445566778899AABBCCDDEEFF,PinName="A",LinkedTo=(MaterialGraphNode_0 11112222333344445555666677778888,),)
```

The safe builder profile is intentionally smaller than a full Editor export:

- every Pin has a unique 32-hex `PinId` and an exact `PinName`;
- output Pins include `Direction="EGPD_Output"`;
- connected Pins include `LinkedTo`;
- input Pins are emitted as ordinary expression inputs followed by property inputs;
- all outputs are emitted in source order, including unconnected outputs;
- `PinType.*`, UI text, persistent GUIDs, and state flags are omitted unless a class-specific sample proves
  they are needed.

UE 5.8 Editor evidence records a successful generated paste for a Constant → Multiply graph with the reduced
Pin profile, but that result does not generalize automatically to every special node.

An individual Pin reference is:

```text
<other GraphNode Name> <other PinId>
```

References are wrapped in a comma-terminated array. The builder writes reciprocal `LinkedTo` records at both
ends of each link. The parser deduplicates them into one MGJSON link. Resolve a Pin reference by the pair
`(owning node name, PinId)`, not by PinId alone; actual clipboard selections can reuse a PinId under different
owners.

`PostPasteNode` derives `SourceIndex` from Pin order. `ReconstructNode` matches data inputs by name when possible
and then by index, while data outputs depend on source index. This is why generated output order must match the
source-audited class schema exactly. Semantic channel masks are not substitutes for clipboard Pin names.

## Paste reconstruction sequence

The checked source path performs these relevant stages:

1. create all imported objects and apply their properties;
2. resolve Pin references and remove unresolved external links;
3. assign source indices in `PostPasteNode`;
4. reconstruct class Pins and transfer old Pin links;
5. repair owners, back-pointers, GUIDs, and special expressions;
6. apply graph Pin links to Material Expression inputs.

Consequences for the builder:

- Pin `LinkedTo` records are authoritative.
- output direction, input names, and complete Pin ordering cannot be guessed;
- property Pins created from `ShowAsInputPin` metadata follow ordinary expression inputs;
- the destination Material Root is not generated; the user makes final Root connections manually;
- special nodes such as Material Function Call, Named Reroute, and Composite require their own source review
  and Editor evidence.

## Builder contract

`build.py`:

1. allocates deterministic graph names, expression names, and Pin IDs;
2. expands source-audited catalog schemas into ordered Pins;
3. writes reciprocal links and redundant expression inputs consistently;
4. emits the graph node, expression declaration, expression definition, pointer, graph properties, and Pins;
5. mirrors Comment state where required;
6. omits environment owners and the Material Root.

The builder must run validation first and emit nothing after an error.

## Parser contract

`parse.py`:

1. validates balanced object nesting;
2. joins expression declarations and definitions within the same parent;
3. selects the child through `MaterialExpression` or `MaterialExpressionComment`;
4. parses Pin structs while tracking quotes and nesting depth;
5. resolves links only after every Pin has been read;
6. normalizes reciprocal output-to-input links and drops Root-only links;
7. converts source-audited properties to typed MGJSON and retains unknown properties as raw T3D values;
8. removes environment-owned fields and preserves positions only with `--keep-pos`.

Unknown header fields do not by themselves invalidate a parse. Case and original Pin spelling are preserved;
only GUID comparison may normalize case or separators.

## Scope limits

- This reference covers Material graph nodes, Material Expressions, Comments, and Pins, not the complete UObject
  text format.
- Engine Material Function assets are absent from the reference checkout. Their existence and internal schema
  require asset content or Editor evidence.
- Clipboard parse/build round-trip tests do not prove shader compilation or target-project asset resolution.
