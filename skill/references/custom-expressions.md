# Custom Expressions

Use this reference only for `UMaterialExpressionCustom`. It does not describe classes derived from
`UMaterialExpressionCustomOutput`.

## Contents

- [Safety boundary](#safety-boundary)
- [Generated function model](#generated-function-model)
- [Inputs and generated samplers](#inputs-and-generated-samplers)
- [Outputs](#outputs)
- [Defines and includes](#defines-and-includes)
- [Scene Texture shorthand](#scene-texture-shorthand)
- [Legacy and Material IR differences](#legacy-and-material-ir-differences)
- [Validation rules](#validation-rules)
- [Recorded evidence](#recorded-evidence)
- [Unresolved integration tests](#unresolved-integration-tests)
- [Source map](#source-map)

## Safety boundary

Custom code executes inside a generated material function. Its visible symbols depend on the shader model,
material domain, shader stage, platform, feature defines, include order, and Unreal Engine version.

Prefer:

- standard HLSL supported by the target shader model;
- explicit numeric and texture inputs;
- generated texture samplers;
- project-owned `.ush` files exposed through a registered virtual shader path.

Treat `Parameters`, `View`, private `/Engine/Private` helpers, and implementation-specific functions as
version-locked internal APIs. Do not maintain a general allowlist of private Engine shader functions.
Require a material compile test for every use of an internal symbol.

## Generated function model

`Code` becomes the body of a generated function; it is not pasted into global shader scope. Do not define a
normal free function inside `Code`. Put reusable helpers in a project or plugin `.ush` file.

The constructor sets these UE 5.8 defaults:

| Property | Default |
|---|---|
| `Description` | `Custom` |
| `Code` | The built-in explanatory comment followed by `float3(1, 1, 1)` |
| `ShowCode` | `false` |
| `OutputType` | `CMOT_Float3` |
| `Inputs` | One input whose `InputName` is empty |

Source: `UMaterialExpressionCustom::UMaterialExpressionCustom` in
`Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp`.

The legacy translator emits a `CustomExpressionN` function. Material IR emits a function named from a
unique ID and a sanitized `Description`, with one overload per used vertex or pixel stage. Compute uses the
pixel parameter type in the inspected UE 5.8 implementation.

## Inputs and generated samplers

Named inputs must be connected. `UMaterialExpressionCustom::Compile` reports a missing-input error for an
unconnected named input. Empty input names are skipped.

The legacy translator explicitly supports these input families:

- float scalar and float vectors;
- LWC scalar and vectors, with a demoted float argument and an additional `LWC<Name>` argument;
- `Texture2D`, `TextureCube`, `Texture2DArray`, `TextureCubeArray`, `TextureExternal`, and volume texture;
- texture collections.

Texture inputs receive a sampler argument named `<InputName>Sampler`. For an input named `Tex`, use the
generated `TexSampler`, for example:

```hlsl
return Texture2DSample(Tex, TexSampler, UV);
```

`Engine/Shaders/Private/Common.ush` defines the inspected `Texture2DSample`,
`Texture2DSampleLevel`, `Texture2DSampleBias`, and `Texture2DSampleGrad` wrappers. Prefer these wrappers over
assuming platform-specific direct sampling behavior.

## Outputs

`OutputType` supports `CMOT_Float1`, `CMOT_Float2`, `CMOT_Float3`, `CMOT_Float4`, and
`CMOT_MaterialAttributes` in the inspected implementation.

`UMaterialExpressionCustom::RebuildOutputs` creates:

- one unnamed primary output when `AdditionalOutputs` is empty; or
- a primary output named `return`, followed by each named additional output.

Unnamed additional outputs do not become Pins.

The legacy translator declares additional outputs as `inout` values that default to zero. Material IR emits
them as output-only parameters. Assign every additional output on every control-flow path for behavior that
is safe across both implementations.

## Defines and includes

Material IR rejects an empty `DefineName`, empty `DefineValue`, or empty include path. Use unique project
prefixes for defines to avoid collisions.

Use virtual shader paths, not filesystem paths. UE 5.8 registers `/Engine` and conditionally registers
`/Project` when the project shader directory exists during Engine startup. A project include therefore uses
a path such as:

```text
/Project/Material/MyMaterialLib.ush
```

If the project shader directory is created after startup, restart the Editor before relying on the mapping.
Plugin paths require the plugin or module to register its own mapping.

## Scene Texture shorthand

`CustomExpressionSceneTextureInputFixup` applies only when a Custom input is connected directly to output 0
of `UMaterialExpressionSceneTexture` or `UMaterialExpressionUserSceneTexture`.

For an input named `SceneInput`, the parser can replace:

```hlsl
SceneInput.ID
SceneInput.Fetch(1, -1)
```

with the connected scene texture identifier and a `SceneTextureFetchFunc` call. The fixup scans HLSL tokens;
do not assume macro expansion will create a later `.ID` or `.Fetch` pattern. Using `SceneInput` without the
shorthand refers to the ordinary connected input value.

Scene texture availability remains material-domain, platform, and rendering-path dependent. The presence of
the shorthand in source is not proof that a particular material configuration can use it.

## Legacy and Material IR differences

| Behavior | Legacy translator | Material IR |
|---|---|---|
| Function naming | `CustomExpressionN` | Unique ID plus sanitized `Description` |
| Input typing | Explicit material-value-type switch | `MIR::FType` from connected values |
| Additional output parameter | `inout` | output-only |
| Parameter limit | No local limit found in the inspected function | 32 named input/output parameters |
| Empty define/include validation | Not established in the inspected path | Explicit error |
| Generated overloads | Current shader frequency | Used vertex/pixel stages |
| Scene Texture fixup | Yes | Yes |
| Automatic `return` decision | Case-sensitive substring search | Case-sensitive substring search |

The Material IR limit is `MIR::MaxNumFunctionParameters = 32`. Enforce
`named Inputs + named AdditionalOutputs <= 32` for common compatibility.

The automatic `return` check is not a parser. A comment containing lowercase `return` can suppress automatic
insertion. Always write an explicit `return ...;` for the primary output.

## Validation rules

Apply these rules before building:

- Require `^[A-Za-z_][A-Za-z0-9_]*$` for named inputs, additional outputs, and define names.
- Reject HLSL reserved words, `Parameters`, duplicate names, and collisions with generated
  `<TextureName>Sampler` parameters.
- Require every named input to be connected.
- Enforce the 32 named input/output limit.
- Reject empty defines and includes.
- Require an absolute virtual include path and reject filesystem paths and `..` traversal.
- Warn when explicit primary `return` is missing.
- Warn when every additional output cannot be shown to receive a value on every control-flow path.
- Warn on `Parameters.`, `View.`, and known private Engine helpers; require version-locked compile evidence.
- Allow `.ID` and `.Fetch` only when the matching input is directly connected to Scene Texture output 0.
- Treat `ContainsClipInstruction=CMCI_Search` as a case-sensitive text search for `clip(` or `discard`, not
  as proof that macro/include-based discard was detected.

See `mgjson.md` for the structured `Inputs`, `AdditionalOutputs`, `AdditionalDefines`, and
`IncludeFilePaths` representation.

## Recorded evidence

The UE 5.8 `LumaSplit` fixture has generated paste/copy-back evidence:

- input `A`;
- primary output `return`;
- additional output `Luma`;
- define `MYPROJ_MODE=1`;
- `Constant3Vector -> Custom.A`;
- `Custom.Luma -> Multiply.A`;
- canonical parse/build/parse with no raw properties.

Artifacts:

- `tests/fixtures/p01-custom-lumasplit.mgjson`
- `tests/fixtures/p01-custom-lumasplit-copyback.txt`

The copy-back also showed that `bShowOutputNameOnPin=True` is derived from `RebuildOutputs`; the parser does
not preserve it as a raw property.

## Unresolved integration tests

The following are not proven by the recorded round-trip:

- Editor copy-back of `IncludeFilePaths`;
- material shader compilation through both legacy translation and Material IR;
- behavior across material domains, shader stages, platforms, and RHIs;
- project include resolution and included helper compilation;
- Scene Texture shorthand compilation in a valid domain;
- 32-parameter success and 33-parameter failure in Editor;
- LWC input behavior;
- include/macro-based discard with an explicit `ContainsClipInstruction` setting.

Do not describe these as supported until the corresponding Editor compile fixture succeeds.

## Source map

All paths are relative to the reference source root.

| Path | Relevant symbols or evidence |
|---|---|
| `Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionCustom.h` | `ECustomMaterialOutputType`, `FCustomInput`, `FCustomOutput`, `FCustomDefine`, `UMaterialExpressionCustom` |
| `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp` | Constructor, `Compile`, input accessors, `PostEditChangeProperty`, `RebuildOutputs`, `HasPixelDiscard` |
| `Engine/Source/Runtime/Engine/Private/Materials/HLSLMaterialTranslator.cpp` | `FHLSLMaterialTranslator::CustomExpression` |
| `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressionsToMIR.cpp` | `DescriptionToIdentifier`, `UMaterialExpressionCustom::Build` |
| `Engine/Source/Runtime/Engine/Public/Materials/MaterialIR.h` | `MaxNumFunctionParameters` |
| `Engine/Source/Runtime/Engine/Private/Materials/MaterialIRToHLSLTranslator.cpp` | `GenerateCustomFunctionsHLSL` |
| `Engine/Source/Runtime/Engine/Private/Materials/MaterialShared.cpp` | `CustomExpressionSceneTextureInputFixup` |
| `Engine/Shaders/Private/Common.ush` | Texture sampling wrappers |
| `Engine/Source/Runtime/RenderCore/Public/ShaderCore.h` | `AddShaderSourceDirectoryMapping` contract |
| `Engine/Source/Runtime/Launch/Private/LaunchEngineLoop.cpp` | `/Engine` and `/Project` mapping setup |

