# Material Function Call Reference

This file documents the local MGJSON/T3D handling for `UMaterialExpressionMaterialFunctionCall` in the UE 5.8
baseline. It deliberately separates source structure, catalog assumptions, and Unreal Editor evidence.

## Evidence status

- The reference checkout contains Engine source but not `Engine/Content`, so built-in Material Function asset
  contents cannot be inspected there.
- `BlendAngleCorrectedNormals` has an Unreal Editor copy sample that records its object path and observed Pins.
- No packaged function currently has a generated paste/copy-back round-trip record.
- The other function catalog entries are parsing hypotheses. Their legacy descriptions and usage guidance are
  quarantined and must not be restored by translation alone.

Do not recommend a function as known-valid unless its exact asset path and ordered Pin schema have asset content
or recorded Editor evidence. Even then, report whether generated paste/copy-back was actually tested.

## Checked source structure

| Concern | Source-relative path and symbol |
|---|---|
| Function input/output records | `Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionMaterialFunctionCall.h` — `FFunctionExpressionInput`, `FFunctionExpressionOutput` |
| Empty constructor state and function update | `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp` — `UMaterialExpressionMaterialFunctionCall`, `UpdateFromFunctionResource` |
| Asset input/output collection and sorting | same file — `UMaterialFunction::GetInputsAndOutputs` |
| Graph post-paste and reconstruction | `Engine/Source/Editor/UnrealEd/Private/EdGraphUtilities.cpp` and `MaterialGraphNode_Base.cpp` |
| Function-specific paste handling | `Engine/Source/Editor/MaterialEditor/Private/MaterialEditor.cpp` — `FMaterialEditor::PostPasteMaterialExpression` |

The saved structures contain transient pointers plus persistent IDs and value records:

```cpp
FFunctionExpressionInput {
    transient ExpressionInput;
    FGuid ExpressionInputId;
    FExpressionInput Input;
}

FFunctionExpressionOutput {
    transient ExpressionOutput;
    FGuid ExpressionOutputId;
    FExpressionOutput Output;
}
```

Transient `ExpressionInput` and `ExpressionOutput` object pointers are not serialized by the local builder.
`UpdateFromFunctionResource` repopulates them from the resolved asset.

## Local builder profile

`build.py` emits the following catalog-derived data:

1. the `MaterialFunction` object reference;
2. ordered `FunctionInputs(n)` records;
3. ordered `FunctionOutputs(n)` records;
4. ordered base `Outputs(n)` records;
5. every graph input and output Pin in the same order.

Temporary `ExpressionInputId` and `ExpressionOutputId` values are deterministic valid GUIDs. They are not claims
about IDs stored in the asset. Expression links inside `FunctionInputs(n)` are omitted because graph `LinkedTo`
records are the local connection authority.

This profile is a source-derived implementation strategy with offline round-trip coverage. It is not yet proven
as a minimal or universally successful Editor paste profile.

## Order and Pin names

`UMaterialFunction::GetInputsAndOutputs` sorts function input and output expressions by `SortPriority`. The local
function catalog must preserve the observed asset order; the builder does not reorder it.

- MGJSON uses raw catalog Pin names without a display type suffix.
- Function input display names may be updated by Unreal after asset resolution.
- Output names come from the ordered function output records.
- `required` is catalog metadata for initial Pin construction; the resolved asset remains authoritative.

Supported catalog type tokens are `S`, `V2`, `V3`, `V4`, `T2d`, `TCube`, `T2dArr`, `TVol`, `SB`, `MA`,
`TExt`, `B`, and `Stra`. These are exact tokens, not localized labels.

## MGJSON

```json
{
  "nodes": {
    "mf": {
      "class": "MaterialFunctionCall",
      "props": {
        "MaterialFunction": "/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals.BlendAngleCorrectedNormals"
      }
    }
  }
}
```

`validate.py` and `build.py` resolve the object path against `skill/catalog/functions.json`. Function Pins come
from that matched entry rather than the static node entry.

Current validation behavior:

- a missing or unmatched catalog path is an error because no dynamic Pin schema is available;
- `path_uncertain` and missing asset/Editor evidence are warnings;
- missing generated paste/copy-back evidence is a separate warning;
- local validation cannot prove target-project asset existence.

If Unreal cannot resolve the asset, source handling can clear the function arrays and produce a Pin-less
unspecified function node. Treat Pin or link survival as unproven until an Editor copy-back confirms it.

## Function catalog shape

Each entry contains:

| Field | Requirement |
|---|---|
| `path` | required object path used by MGJSON |
| `inputs` | required ordered `{name,type,required?,id?}` array |
| `outputs` | required ordered `{name,type,id?}` array |
| `path_uncertain` | required or normalized boolean uncertainty flag |
| `desc`, `usage` | optional active prose; currently empty unless evidence supports new English guidance |

`name` is the raw Pin name. Optional `id` is a 32-hex GUID and may be recorded only from asset content or a
specific Editor sample. When absent, the builder generates a temporary ID.

The active catalog intentionally retains unaudited paths and Pins for parsing and investigation. That presence
does not make a function safe to recommend or generate.

## Canonical T3D shape

The following abbreviated shape illustrates builder fields. It is not a claim that the asset exists in every
target project.

```text
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_0"
   Begin Object Class=/Script/Engine.MaterialExpressionMaterialFunctionCall Name="MaterialExpressionMaterialFunctionCall_0"
   End Object
   Begin Object Name="MaterialExpressionMaterialFunctionCall_0"
      MaterialFunction="/Script/Engine.MaterialFunction'/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals.BlendAngleCorrectedNormals'"
      FunctionInputs(0)=(ExpressionInputId=11111111111111111111111111111111,Input=(OutputIndex=-1,InputName="BaseNormal"))
      FunctionOutputs(0)=(ExpressionOutputId=22222222222222222222222222222222,Output=(OutputName="Result"))
      Outputs(0)=(OutputName="Result")
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionMaterialFunctionCall'MaterialExpressionMaterialFunctionCall_0'"
   CustomProperties Pin (PinId=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,PinName="BaseNormal",)
   CustomProperties Pin (PinId=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB,PinName="Result",Direction="EGPD_Output",)
End Object
```

Connected Pins add reciprocal `LinkedTo` fields as described in `format.md`.

## Remaining work

- Export or inspect version-matched asset content to establish exact paths, order, defaults, and persistent IDs.
- Perform generated paste/copy-back tests for each function promoted to supported status.
- Compare the returned MGJSON and compile result; asset resolution alone does not prove semantic correctness.
- Keep uncertain entries parsing-only until those checks are complete.
