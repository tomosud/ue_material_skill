# Improvement plan implementation: resume notes

Last updated: 2026-07-15 (Asia/Tokyo)

This document is the hand-off point for continuing
[`improvement-plan.md`](./improvement-plan.md). Preserve the current worktree and resume from
Phase D. Do not start Phase E until the Phase D integration and quality gates below pass.

## Current stage

| Phase | Status | Result |
| --- | --- | --- |
| A | Complete | Deterministic metadata, source hashes, catalog diff classification, and stale-evidence handling |
| B | Complete | Deterministic AND search, `limit`/`all`, ranking, and legacy-prose aliases |
| C | Complete | Closed semantics schema, source fact extraction, semantic QA, and 20 pilot audits |
| D | In progress | D01-D03 integrated; D04-D05 audited but not yet regenerated into the distributable catalog |
| E-G | Pending | Do not begin until Phase D passes its integration gate |

## Accepted audit batches

The following batches are present under `dev/catalog/audits/`:

- `C02-pilot-math.json` and `C03-pilot-texture.json`: 20 pilot nodes.
- `D01-common-math.json`, `D02-extended-math.json`, and
  `D03-parameters-texture.json`: 45 nodes integrated through the normal generation path.
- `D04-vector-coordinate.json`: 15 nodes audited and source-spot-checked.
- `D05-scene-coordinates.json`: 15 nodes audited and source-spot-checked.

The last fully generated distributable evidence/catalog contains 65 maintained audits: the 20
pilot nodes plus D01-D03. D04-D05 must still be regenerated into
`skills/ue-material/catalog/node-evidence.json` and `nodes.json`.

### D04 classes

`Abs`, `ActorPositionWS`, `DeriveNormalZ`, `Fmod`, `If`, `Length`, `LocalPosition`,
`Modulo`, `ObjectOrientation`, `RotateAboutAxis`, `SmoothStep`, `SphereMask`, `Transform`,
`TransformPosition`, `ViewSize`.

### D05 classes

`CameraPositionWS`, `CameraVectorWS`, `LightVector`, `ObjectLocalBounds`, `ObjectPositionWS`,
`ObjectRadius`, `PixelNormalWS`, `PreSkinnedNormal`, `PreSkinnedPosition`,
`ReflectionVectorWS`, `SceneTexelSize`, `ScreenPosition`, `VertexNormalWS`,
`VertexTangentWS`, `WorldPosition`.

## Work completed after the interrupted session

D06 source research found generated-data and closed-vocabulary gaps. The following foundation
changes are already applied, but `D06-scene-depth-lighting.json` has deliberately not been
created yet:

- Corrected `SceneDepth`, `SceneColor`, `SceneTexture`, `SceneDepthWithoutWater`,
  `AtmosphericFogColor`, and `SkyAtmosphereLightIlluminance` defaults or effective input names.
- Added D06 scene formula functions to `dev/tools/semantics_schema.py`.
- Added structured restrictions for minimum feature level, supported blend modes, and
  backend-specific shader stages.
- Added a regression test for the new D06 formula/restriction shapes in
  `dev/tests/test_semantics_tools.py`.

The intended D06 batch is:

`SceneTexture`, `SceneDepth`, `PixelDepth`, `DepthFade`, `DBufferTexture`, `SceneColor`,
`SceneDepthWithoutWater`, `EyeAdaptation`, `EyeAdaptationInverse`, `AtmosphericFogColor`,
`SkyAtmosphereLightDirection`, `SkyAtmosphereLightIlluminance`,
`SkyAtmosphereDistantLightScatteredLuminance`, `PrecomputedAOMask`, `LightmapUVs`.

Before accepting D06, resolve or explicitly record the legacy/MIR output-dimension difference
for `EyeAdaptationInverse`. More complex material-domain and shading-model conditions may also
need additional closed restriction shapes; do not encode them as free-form prose.

## Last known verification state

- The packaged 65-audit evidence/catalog passed semantic QA.
- The full suite last passed with 59 tests before the latest Phase D schema/generated-data
  refinements.
- The semantics-focused suite last passed with 14 tests before the final D06 foundation patch.
- D04 isolated QA passed.
- D05 isolated QA passed before its final minor refinements; rerun it before integration.
- After the interrupted session, all edited generated JSON and D04/D05 audit JSON files parsed
  successfully with PowerShell `ConvertFrom-Json`.
- `git diff --check` passed after the D06 foundation patch.
- The final Python/`uv` regeneration and test pass was not run because execution credits were
  unavailable. Do not treat the static checks as a substitute for the quality gate.

## Exact resume order

1. Inspect `git status --short`. Preserve all current changes. In particular, `.claude/` is
   user-owned and must not be modified or removed.
2. Confirm the offline `uv` runtime can execute again.
3. Integrate D04-D05 through the normal path:

   ```powershell
   uv run --offline --no-project python -B dev/tools/gen_node_evidence.py
   uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
   ```

4. Run semantic QA for all D04-D05 classes. PowerShell can build the repeated arguments without
   changing the class list:

   ```powershell
   $classes = @(
     'Abs','ActorPositionWS','DeriveNormalZ','Fmod','If','Length','LocalPosition','Modulo',
     'ObjectOrientation','RotateAboutAxis','SmoothStep','SphereMask','Transform',
     'TransformPosition','ViewSize','CameraPositionWS','CameraVectorWS','LightVector',
     'ObjectLocalBounds','ObjectPositionWS','ObjectRadius','PixelNormalWS','PreSkinnedNormal',
     'PreSkinnedPosition','ReflectionVectorWS','SceneTexelSize','ScreenPosition','VertexNormalWS',
     'VertexTangentWS','WorldPosition'
   )
   $classArgs = $classes | ForEach-Object { @('--class', $_) }
   uv run --offline --no-project python -B dev/tools/qa_semantics.py --extract-current @classArgs
   ```

5. Run the repository gates:

   ```powershell
   uv run --offline --no-project python -B -m unittest discover -s dev/tests -v
   uv run --offline --no-project python -B dev/tools/check_english.py
   uv run --offline --no-project python -B dev/tools/check_distribution.py
   uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
   git diff --check
   ```

6. Run `catalog_merge.py --quiet` once more and confirm the second run adds no diff. Confirm that
   the first integration changes only the expected D04-D05 catalog/evidence entries and metadata.
7. If any D04-D05 check fails, fix that batch and repeat steps 3-6 before starting D06 audit JSON.
8. Create and independently review `D06-scene-depth-lighting.json`, then repeat the isolated and
   standard gates documented in [`audit-batch-instructions.md`](./audit-batch-instructions.md).
9. Continue Phase D in small, disjoint batches. Only after every Phase D batch is integrated and
   green should Phase E retire legacy prose and synthesize descriptions exclusively from verified
   semantics.

## Source and worktree constraints

- Unreal Engine source baseline: `C:\work\unreal\UnrealEngine-release` (read-only for this task).
- Repository root: `C:\work\script\ue_material_skill`.
- Use `apply_patch` for manual edits and preserve unrelated worktree changes.
- Audit acceptance requires source-symbol review in addition to automated QA. Spot-check at least
  three classes per batch as described in `audit-batch-instructions.md`.
- Never bypass a failed stage gate by proceeding to the next phase.

