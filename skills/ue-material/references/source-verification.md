# Source Verification

Use this reference before making factual claims about any Material Expression, changing a catalog entry,
or using a node in a generated graph.

## Contents

- [Reference baseline](#reference-baseline)
- [Resolving the source root](#resolving-the-source-root)
- [Canonical terminology](#canonical-terminology)
- [Evidence dimensions](#evidence-dimensions)
- [Required audit workflow](#required-audit-workflow)
- [Description rules](#description-rules)
- [Dynamic and inherited nodes](#dynamic-and-inherited-nodes)
- [Material Function assets](#material-function-assets)
- [Current coverage](#current-coverage)
- [Known gaps](#known-gaps)

## Reference baseline

- Source root: a read-only Unreal Engine checkout resolved as described in
  [Resolving the source root](#resolving-the-source-root)
- Engine version: 5.8.0
- Source branch recorded by `Engine/Build/Build.version`: `UE5`
- Repository baseline: `307eb76854c40b13bbad0ce293b9e5eae8996805`
- Source access: read-only

Treat this baseline as version-specific. Do not broaden a source finding into a compatibility claim for
another Unreal Engine revision.

## Resolving the source root

The bundled Python tools never read Unreal source; they operate only on the packaged catalog. The source
root is required only for manual source verification. Resolve it in this order and stop at the first match:

1. **Skill-local setting file.** Read `.ue-material/settings.json` at the working-project root and use its
   `ueSourceRoot`.
2. **Environment variable.** Use `UE_SOURCE_ROOT`.
3. **User-directed limited scan.** Ask the user for the folder that holds their Unreal installation and scan
   only under it. Rank candidates by engine version and branch, let the user choose, then save the choice to
   the setting file.

Never scan whole drives by default. A recursive whole-drive walk is slow, can trigger access-denied on
protected paths, and may be flagged by endpoint security. Broaden the scope only with explicit user opt-in.

Run the limited scan depth-bounded and tolerant of permission errors, using the user-provided start folder:

```powershell
param([string]$Root = "E:\UE")   # user-provided start folder
Get-ChildItem -Path $Root -Recurse -Filter "Build.version" -Depth 6 -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match 'Engine\\Build\\Build\.version' }
```

Persist only the resolved selection, not the candidate list. Write it to `.ue-material/settings.json` at the
working-project root and keep that file out of version control; it is environment-specific and non-shared:

```jsonc
{
  "$comment": "ue-material skill local setting (environment-specific, gitignored)",
  "ueSourceRoot": "E:/UE/UE_5.8",
  "resolvedAt": "2026-07-15",
  "baseline": { "version": "5.8.0", "branch": "UE5" },
  "verified": { "materialsHeaders": true, "privateCpp": true, "gitCommitMatch": false }
}
```

Add the setting path to the working project's `.gitignore`:

```gitignore
# ue-material skill local setting (environment-specific, non-shared)
.ue-material/
```

Before using a resolved root, confirm it matches the baseline version and branch. A promoted or launcher
build has no `.git`, so exact baseline-commit matching may be unavailable; a version and branch match read
from `Engine/Build/Build.version` is an acceptable substitute for development testing. Plugin-owned nodes
(Substrate, MaterialX, and similar) live under `Engine/Plugins/.../Source/...` in the same checkout.

Confirm this mechanically instead of by eye. `catalog/node-evidence.json` records the baseline as a
`source.fingerprint` (`version|branch`) plus `source.git_commit`. Run the bundled check after resolving a
root:

```powershell
python scripts/source_fingerprint.py            # uses .ue-material/settings.json or UE_SOURCE_ROOT
python scripts/source_fingerprint.py --ue-root E:\UE\UE_5.8
```

`COMPATIBLE` (exit 0) means the resolved root is the same engine line as the catalog. A `WARNING` (exit 2)
means the version or branch differs, so catalog facts must be re-audited against that source before use.
Changelist and commit legitimately differ between a GitHub source release and a launcher promoted build of the
same version; they are reported for audit but do not gate the result.

The catalog is the durable, reviewed store of source-verified facts. When source inspection establishes a new
fact, contribute it back to the maintained catalog evidence rather than keeping it only in a local file, so it
stays fingerprinted, reviewed, and shared. Do not treat a local, per-machine note as an authority.

## Canonical terminology

Use exact source identifiers in this order:

1. C++ class symbol, for example `UMaterialExpressionTextureSample`.
2. Catalog short class, for example `TextureSample`.
3. Serialized `UPROPERTY` name.
4. Effective Pin name returned or constructed by the node implementation.
5. Exact enum token.
6. Exact object path.

Do not translate, title-case, expand, or otherwise normalize identifiers. Localized Editor labels are not
canonical. Store a UI label separately only when source or Editor evidence proves that label.

## Evidence dimensions

Keep these dimensions independent:

| Dimension | Meaning |
|---|---|
| `source` | The declaration or implementation was inspected in the reference source tree. |
| `offline` | Parser, validator, and builder behavior was checked without Unreal Editor. |
| `editor_copy` | An Editor-created node was copied and parsed. |
| `editor_paste` | Generated clipboard text was accepted by Unreal Editor. |
| `editor_roundtrip` | A generated graph was pasted, copied back, parsed, and compared semantically. |
| `asset_resolution` | Unreal Editor resolved the referenced asset path and expected asset type. |
| `shader_compile` | The material compiled in the stated domain, stage, platform, and feature configuration. |

Never use a single `verified` boolean to imply all of these. Existing `verified` fields predate this rule
and are not sufficient evidence by themselves. Consult `catalog/editor-evidence.json` for recorded
Editor observations.

## Required audit workflow

For each Material Expression:

1. Resolve its exact source-relative declaration path, module, base class, plugin ownership, abstract state,
   and deprecation state.
2. Inspect `UCLASS`, inheritance, `UPROPERTY` declarations, metadata, and in-class defaults.
3. Inspect its constructor and version migration code for effective defaults.
4. Resolve ordinary inputs through declarations plus `GetInputsView`, `GetInput`, `GetInputName`, and
   `IsInputConnectionRequired` overrides.
5. Resolve property Pins through metadata and graph-node construction order.
6. Resolve outputs through inherited defaults, constructor mutations, output-name overrides, and dynamic
   rebuild functions.
7. Inspect both `Compile` and `Build` when legacy translation and Material IR may differ.
8. Inspect material-domain, shader-stage, platform, plugin, and feature restrictions.
9. Inspect graph-node, import, paste, and reconstruction paths before making clipboard claims.
10. Record source-relative paths and symbols. Use line numbers only as optional navigation hints.

If a fact cannot be established from source, leave it unresolved or request an Editor sample. Never fill
the field from class-name interpretation, model knowledge, or another unsourced catalog.

## Description rules

Accept an English description only when:

- the operation is visible in `Compile`, `Build`, an authoritative ToolTip/comment, or another identified
  implementation;
- every mentioned input, output, default, range, unit, domain, and restriction has evidence;
- inherited behavior names both the derived declaration and the implementation provider;
- the wording is no broader than the inspected paths;
- state-dependent behavior is described as state-dependent.

A class name alone is never description evidence. If source proves only that a class exists, omit `desc`
instead of inventing a summary.

## Dynamic and inherited nodes

A static Pin list is insufficient when Pins depend on properties, assets, arrays, or reconstruction state.
Record the state transition or rebuild function that produces each schema. Common evidence sources include:

- `GetInputsView`, `GetInput`, and `GetInputName`;
- constructor changes to `Outputs`;
- `RebuildOutputs` or equivalent dynamic reconstruction;
- Material Function asset input/output discovery;
- Named Reroute declaration/usage recovery;
- special `MaterialGraphNode` subclasses;
- paste-time `PostPasteMaterialExpression` behavior.

For inherited behavior, verify that the derived class does not override the relevant path before citing the
base implementation.

## Material Function assets

The supplied checkout has no `Engine/Content`. C++ source can prove the `MaterialFunctionCall` mechanism,
but it cannot prove the path or Pin schema of an individual packaged Material Function asset.

Require one of the following for an individual function entry:

- available asset content;
- an Asset Registry export from the target Editor installation; or
- a versioned Editor copy sample containing the resolved path and Pins.

Do not recommend a function whose path or Pin schema is based only on model knowledge. Keep uncertain
function entries quarantined from default selection.

## Current coverage

At the baseline revision:

- the merged node catalog contains 359 entries;
- all 359 entries have a non-empty, source-resolved header field;
- 6 entries currently have recorded source verification for schema and description;
- the remaining entries stay in the same searchable catalog with their current provenance state;
- the function catalog contains 82 entries;
- 20 function paths are marked uncertain;
- legacy descriptions and notes for 337 nodes remain searchable, but most still need source-backed English
  replacement.

Recorded Editor evidence is narrower than the legacy flag suggests:

- `Constant`, `OneMinus`, `Comment`, and `Custom` have generated paste/copy-back evidence.
- `NamedRerouteDeclaration` and `NamedRerouteUsage` have Editor-copy evidence, not generated round-trip
  evidence.
- `BlendAngleCorrectedNormals` has an Editor-copy sample with a corrected asset path, not a generated
  round-trip result.

## Known gaps

- Catalog descriptions and notes still require source audit and English migration.
- Generated catalog fragments contain normalization debt that the merged catalog currently hides.
- Named Reroute generation and collision behavior still require Editor round-trip fixtures.
- Custom `IncludeFilePaths` lacks Editor copy-back evidence.
- Custom shader compilation across legacy translation, Material IR, domains, stages, and platforms remains
  unverified.
- The local offline `uv` CPython runtime is available; the current 25-test suite passes without Unreal Editor.
