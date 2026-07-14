# UE Material Skill Refactoring Plan

Status: in progress; Phases 0–3, 5, and 6 completed; Phase 4 continues; Phase 7 automated gates pass  
Plan language: English  
Reference source root: `C:\work\unreal\UnrealEngine-release`  
Source baseline: Unreal Engine 5.8.0, branch `UE5`, from `Engine/Build/Build.version`

## 1. Purpose

Refactor the `ue-material` skill so that it is searchable, evidence-based, and efficient to load.
The active skill content will use English consistently. Unreal Engine identifiers will retain their
exact source spelling. Node descriptions and behavior claims will be accepted only when they can be
traced to the reference source root or to explicit Unreal Editor evidence.

This plan deliberately separates cleanup, source audit, translation, catalog correction, and Editor
verification. Bulk translation must not preserve an unsupported claim merely by rewriting it in
English.

The plan was initially created without code changes. The user subsequently authorized phased implementation;
each script, schema, catalog, and test change remains separately reviewable.

## 2. Goals

1. Make all active skill instructions and maintained reference prose English.
2. Use stable Unreal Engine source identifiers as canonical terminology.
3. Eliminate guessed node descriptions, Pin layouts, defaults, restrictions, and compatibility claims.
4. Separate source evidence, offline conversion evidence, and Unreal Editor evidence.
5. Remove completed implementation-task Markdown after preserving durable facts in their proper homes.
6. Keep `SKILL.md` concise and load detailed references only when a task needs them.
7. Make large catalogs searchable through generated indexes or query tooling rather than duplicated prose.
8. Record Unreal Engine version and source provenance in a machine-checkable form.

## 3. Non-goals

- Do not translate Unreal class names, property names, Pin names, enum tokens, asset paths, or API symbols.
- Do not treat a source review as proof that clipboard paste, Editor round-trip, asset resolution, or shader
  compilation succeeds.
- Do not treat an offline parse/build round-trip as Unreal Editor verification.
- Do not claim individual Material Function assets are valid when their `.uasset` content or an Editor sample
  is unavailable.
- Do not preserve development history as active skill documentation. Git history already provides history.
- Do not introduce a deep reference hierarchy that requires loading one index to discover another index.

## 4. Current-state findings

The initial read-only audit found the following:

- `skill/catalog/nodes.json` contains 359 node entries.
- Only 6 of 359 entries currently have `verified: true`; the boolean does not express what was verified.
- 334 node entries have a non-empty `header`; 25 Substrate entries do not.
- Header paths use inconsistent roots and separators.
- 284 node descriptions and 175 node notes contain Japanese text.
- The catalog does not store field-level source evidence for descriptions, Pins, defaults, or restrictions.
- `skill/catalog/functions.json` contains 82 Material Functions. Only 1 is marked verified, and 20 have
  `path_uncertain: true`.
- The reference checkout does not contain `Engine/Content`, so most individual Material Function entries
  cannot be validated from the supplied source tree.
- `skill/SKILL.md` is mostly English but still contains Japanese operational text.
- `skill/agents/openai.yaml` contains a Japanese `short_description`.
- The four current reference documents are primarily Japanese. `nodes-index.md` duplicates catalog data in
  a large human-readable table.
- All task files report `status: DONE`, while `tasks/README.md` still reports every task as `TODO`.
- Several completed-task documents contain stale progress headings or superseded next actions.
- Durable Custom node research and Editor verification facts currently live under `tasks/`, mixed with
  dispatch instructions and implementation history.
- Some repository tools hard-code the source root, but changing them is outside the documentation-only
  scope of this plan creation.

## 5. Language and terminology policy

### 5.1 Active language

- Write all maintained skill prose in English.
- Write all maintained catalog descriptions, notes, warnings, CLI-facing documentation, and skill metadata
  in English.
- Do not mix a Japanese translation into an English sentence as a parenthetical alias.
- Store files as UTF-8 and preserve exact identifier spelling.
- Permit non-English text only when it is user data, an asset name, a graph comment, a test fixture value,
  or a short source quotation required as evidence.

Add an automated language check during implementation. It should inspect active Markdown, YAML metadata,
and human-readable catalog fields while excluding fixtures and explicit user content.

### 5.2 Canonical Unreal terminology

Use this precedence order:

1. Exact C++ symbol, such as `UMaterialExpressionTextureSampleParameter2D`.
2. Exact catalog short class, such as `TextureSampleParameter2D`.
3. Exact `UPROPERTY` name for serialized properties.
4. Exact effective Pin name produced by `GetInputName`, `GetOutputName`, output construction, or Editor
   reconstruction logic.
5. Exact enum token and exact asset object path.
6. English UI label only when the source or a recorded Editor sample proves it.

Do not derive a description from a class name. Do not normalize capitalization, spacing, abbreviations,
or legacy spelling in identifiers. A friendly search alias may exist only in a dedicated alias field and
must never replace the canonical identifier.

### 5.3 Localized and unstable UI labels

Localized Unreal Editor labels are not canonical. When a UI-facing label is needed, store it separately
from the source identifier and record how it was obtained. Prefer source symbols for search and graph
generation. Treat label changes across Unreal versions as versioned evidence, not as synonyms to merge
silently.

## 6. Source-first evidence policy

### 6.1 Required rule

Every factual node description must have source evidence. A node entry must not contain a behavioral
description based on model knowledge, common usage, class-name interpretation, or another unsourced catalog.

If the supplied source cannot prove a statement:

- omit the statement;
- mark the field as unresolved; or
- request an Editor sample when the fact is observable only at runtime or in the UI.

Never fill an unresolved field with a plausible explanation.

### 6.2 Evidence precedence

Review the following evidence as applicable:

1. Class declaration, inheritance, `UCLASS`, and `UPROPERTY` metadata.
2. In-class defaults and constructor assignments.
3. `GetInputs`, `GetInput`, `GetInputName`, `IsInputConnectionRequired`, output construction, and dynamic
   Pin rebuild logic.
4. Both `Compile` and `Build` paths when legacy translation and MIR can differ.
5. `GetCaption`, `GetCreationName`, `GetKeywords`, ToolTips, and source comments for display intent.
6. `IsAllowedIn`, validation, compile errors, shader-stage checks, material-domain checks, plugin gates,
   deprecation metadata, and version guards for restrictions.
7. Material graph and paste/reconstruction code for clipboard behavior.
8. Unreal Editor fixtures for UI labels, asset resolution, paste behavior, copy-back behavior, and shader
   compilation that source inspection alone cannot prove.

### 6.3 Provenance format

Replace the ambiguous `verified` boolean with explicit evidence dimensions. The exact schema will be
designed before catalog migration, but it must express at least:

- Unreal Engine version and branch;
- source-relative declaration path and class symbol;
- source-relative implementation paths and symbols used for behavior claims;
- whether class schema, inputs, outputs, properties, defaults, description, and restrictions were audited;
- offline fixture identity and result;
- Editor copy, paste, round-trip, asset-resolution, and shader-compile results independently;
- unresolved items and version-specific caveats.

Use source-relative paths plus symbols as the stable reference. Line numbers may be generated as navigation
hints, but they must not be the sole evidence because they drift between revisions.

### 6.4 Description acceptance rule

An English `desc` is accepted only when all of the following are true:

1. The described operation is visible in source behavior or an authoritative source comment/ToolTip.
2. The cited symbol belongs to the cataloged class or to a clearly identified inherited implementation.
3. Inputs, outputs, defaults, units, ranges, shader stages, and material-domain restrictions mentioned by
   the description have their own evidence.
4. The wording does not imply broader support than the evidence proves.
5. The entry identifies unresolved dynamic behavior instead of hiding it in a generic sentence.

## 7. Node audit checklist

Audit every node against `C:\work\unreal\UnrealEngine-release` in this order:

1. Resolve the exact module, class path, header, base class, plugin ownership, abstract state, and deprecation.
2. Resolve ordinary inputs from declarations and all relevant overrides.
3. Resolve property Pins from metadata and their effective order.
4. Resolve outputs from constructors, inherited defaults, dynamic rebuild functions, and output-name logic.
5. Resolve serialized properties, types, enum domains, default values, and version migrations.
6. Resolve behavior through `Compile`, `Build`, or the class-specific implementation.
7. Resolve Editor restrictions and special graph-node behavior.
8. Write a minimal English description using only proven facts.
9. Record source paths and symbols for each audited category.
10. Run schema validation and any available fixture checks before marking the entry source-audited.

For dynamic nodes, audit the state machine that changes Pins. A single static Pin list is not sufficient.
For inherited nodes, record both the derived declaration and the inherited implementation that supplies
the behavior.

## 8. Material Function policy

Keep the source-verified `MaterialFunctionCall` mechanism separate from claims about individual Material
Function assets.

The supplied source checkout lacks `Engine/Content`. Therefore:

- do not source-verify the existing 82 function assets from C++ source;
- do not translate model-knowledge descriptions and present them as audited facts;
- quarantine unverified function entries from default recommendations;
- retain an entry only when an Editor copy sample, Asset Registry export, or available `.uasset` evidence
  proves the asset path and Pin schema;
- track asset path, Pin order, Pin types, engine version, and sample identity independently;
- keep uncertain paths explicitly unavailable rather than merely warning after selection.

## 9. Markdown cleanup and disposition

No implementation-history Markdown should be deleted until its durable facts have been moved to the correct
active reference, fixture, or evidence record. After extraction, Git history is sufficient for the original
task narrative.

| Current document | Disposition | Required extraction before removal |
|---|---|---|
| `PLAN.md` | Remove after this refactoring plan becomes the active plan | Any still-valid architecture constraints not already in `SKILL.md` or references |
| `tasks/README.md` | Remove | None after completed-task links are no longer active |
| `tasks/DISPATCH.md` | Remove | None; it is completed worker-dispatch history |
| `tasks/HANDOFF.md` | Remove | Unresolved risks and current guarantees only |
| `tasks/INSTRUCTIONS-catalog.md` | Remove | Source-audit rules, rewritten in English and strengthened by this plan |
| `tasks/INSTRUCTIONS-mf.md` | Remove | Material Function evidence rules only |
| `tasks/T01` through `tasks/T08` | Remove | Accepted specifications and verified outcomes only |
| `tasks/catalog/C01` through `C22` | Remove | None after catalog provenance and coverage are machine-checkable |
| `tasks/M01` through `M04` | Remove | Source-verified call mechanics and asset evidence only |
| `tasks/E01-collect-examples.md` | Remove | Fixture metadata and Editor version |
| `tasks/P01-custom-roundtrip.md` | Remove | Custom fixture evidence and unresolved compile risks |
| `tasks/verification-log.md` | Replace with structured evidence, then remove | Fixture IDs, engine version, operation tested, expected result, and actual result |
| `tasks/CUSTOM-NODE-SOURCE-RESEARCH.md` | Migrate, then remove | Durable Custom expression rules with source-relative paths and symbols |
| `tasks/MAIN-AI-REVIEW.md` | Remove after open items are represented here or in tracked work | Evidence split, regression gaps, portability, and unresolved dynamic-node work |

Do not add a README, quick-reference document, changelog, or handoff document inside the skill. The skill
must contain only instructions and resources needed by an agent performing material-graph work.

## 10. Target documentation structure

The intended active structure is:

```text
skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── mgjson.md
│   ├── t3d-format.md
│   ├── source-verification.md
│   ├── custom-expressions.md
│   └── material-function-calls.md
├── catalog/
│   ├── nodes.json
│   ├── node-evidence.json
│   └── functions.json
└── scripts/
```

The final evidence filename and schema may change during design, but evidence must remain machine-readable.

Keep every reference directly linked from `SKILL.md`. Avoid nested reference indexes. If one reference grows
beyond a practical loading size, split it by task domain into sibling files and link each sibling directly
from `SKILL.md` with an explicit read condition.

`nodes-index.md` should not remain a manually maintained duplicate of `nodes.json`. Replace it with one of:

1. a generated, deterministic English index split into directly linked domains; or
2. a catalog query command that returns a small set of source-audited entries.

Prefer the query approach if it reduces context use without harming discoverability.

## 11. Progressive-disclosure rules

- Keep `SKILL.md` focused on workflow selection, safety rules, validation order, and reference routing.
- Remove the duplicated frequent-node table when reliable catalog querying exists.
- Keep MGJSON syntax and short examples in `SKILL.md`; keep the complete schema in `references/mgjson.md`.
- Keep ordinary use out of the T3D format reference.
- Load Custom expression rules only for Custom nodes.
- Load Material Function rules only for function calls.
- Put detailed node facts in the catalog and evidence data, not in prose tables.
- Add a table of contents to any reference longer than 100 lines.
- Split a reference before it approaches 500 lines or becomes expensive to search in context.

## 12. Phased execution plan

### Phase 0: Freeze the baseline

Deliverables:

- Record the current commit, Unreal version, catalog counts, fixture list, and existing test results.
- Confirm the source root is readable and treat it as read-only.
- Preserve the user-owned untracked `.claude/` directory without modification.
- Define the allowed file scope for each later phase.

Exit gate:

- The baseline can be reproduced without relying on stale task status tables.

### Phase 1: Consolidate and remove obsolete Markdown

Deliverables:

- Create a fact-migration checklist for every document in the disposition table.
- Move durable Custom, T3D, MGJSON, function-call, and verification facts to their target homes in English.
- Convert narrative verification results into structured fixture/evidence records.
- Remove completed dispatch, handoff, task, and obsolete planning Markdown only after the migration check passes.
- Repair all links from active skill documents.

Exit gate:

- No unique operational rule or verified fact exists only in a deleted document.
- The active documentation set has no stale `TODO`, `in progress`, or superseded next-action text.

### Phase 2: Establish language and evidence schemas

Deliverables:

- Finalize the English-only lint scope and exemptions.
- Finalize canonical terminology and alias rules.
- Replace the single `verified` concept with explicit source, offline, and Editor evidence dimensions.
- Normalize source-relative path format and separators.
- Record engine version and branch in generated artifacts.
- Define a validation error for any description without acceptable evidence.

Exit gate:

- New or changed catalog facts cannot be accepted without a source path and symbol.
- Source verification cannot be confused with Editor verification.

### Phase 3: Audit and gate the current catalog

Deliverables:

- Mark every existing description and note as audited, unresolved, or quarantined.
- Resolve the 25 missing Substrate header paths from the source manifest or remove unsupported entries.
- Identify inconsistent, incomplete, inherited, and dynamic Pin schemas.
- Prevent unaudited entries from being recommended as safe generation targets.
- Keep parsing support distinct from safe generation support.

Exit gate:

- No unaudited description is presented as factual.
- Every available generation entry has a resolvable declaration path and minimum schema evidence.

### Phase 4: Source-audit nodes in bounded batches

Run small batches so review remains practical:

1. Existing Editor fixtures and the most common arithmetic, constants, parameters, texture, coordinate,
   vector, and utility nodes.
2. Remaining ordinary Engine nodes.
3. Dynamic and special graph nodes, including Named Reroute, Custom, Function Call, Composite, and nodes
   with state-dependent Pins.
4. Substrate and experimental nodes.
5. Plugin nodes, only when the matching plugin source is present.

For every batch:

- inspect the reference source root directly;
- record paths and symbols;
- correct schema before translating descriptions;
- write concise English descriptions from accepted evidence;
- run deterministic catalog generation and validation;
- add focused fixtures for risky behavior;
- report unresolved facts instead of guessing.

Exit gate per batch:

- All changed descriptions and schema fields have evidence.
- No unrelated node entry changes.
- Generated and merged catalogs remain deterministic.

### Phase 5: Refactor active skill documentation

Deliverables:

- Rewrite `SKILL.md` and `openai.yaml` in English.
- Translate and correct MGJSON, T3D, Custom, and function-call references section by section.
- Remove duplicated node tables after catalog discovery is reliable.
- Add direct conditional links from `SKILL.md` to every reference.
- Keep examples minimal and source-audited.

Exit gate:

- Active skill prose passes the language lint.
- `SKILL.md` remains under 500 lines and contains no detailed catalog duplication.
- All reference routing is direct and task-specific.

### Phase 6: Rebuild search and indexing

Deliverables:

- Provide deterministic catalog search by canonical class, source symbol, Pin, property, category, plugin,
  evidence state, and English description terms.
- Generate any human-readable index from audited catalog data only.
- Split generated indexes by domain only when query-based discovery is insufficient.
- Ensure search results show evidence state and unresolved caveats.

Exit gate:

- An agent can find a suitable audited node without loading the entire catalog or a 359-row Markdown table.

### Phase 7: Validate and forward-test

Deliverables:

- Run skill structure validation.
- Run Markdown link, English-language, JSON schema, provenance coverage, and source-path resolution checks.
- Run existing unit and offline round-trip tests.
- Re-run Unreal Editor smoke tests for changed high-risk nodes.
- Forward-test realistic generation, analysis, modification, unknown-node, Custom, and Material Function tasks
  with clean context.

Exit gate:

- The skill never recommends an unaudited node as source-proven.
- Evidence shown to the agent matches the actual verification performed.
- The skill remains usable without loading implementation history.

## 13. Validation matrix

| Claim | Minimum evidence | Stronger evidence when applicable |
|---|---|---|
| Class exists | Source declaration | Manifest coverage check |
| Input or property exists | Declaration or effective input override | Editor copy fixture |
| Pin display name and order | Name/order implementation | Editor copy and paste round-trip |
| Output name and order | Constructor or dynamic output implementation | Editor copy and paste round-trip |
| Default value | In-class initializer or constructor | Editor Details-panel fixture |
| Mathematical behavior | `Compile` and/or `Build` implementation | Shader compile fixture |
| Domain or stage restriction | Validation/compile/source guard | Failing and passing Editor compile fixtures |
| Clipboard generation works | Material graph/paste source path | Editor paste and copy-back fixture |
| Asset path exists | Asset Registry or asset content | Editor resolution fixture |
| Material Function Pin schema | Asset content or Editor sample | Versioned round-trip fixture |

## 14. Completion criteria

The refactor is complete when:

1. Active skill documentation and human-readable catalog content are English, subject only to documented
   fixture/user-data exemptions.
2. Every retained node description is backed by source-relative path and symbol evidence.
3. Unreal identifiers are exact and are not replaced by localized labels.
4. Source, offline, and Editor verification are represented independently.
5. Unverified Material Function assets are not recommended as known-valid functions.
6. Completed implementation-task Markdown has been removed after durable fact migration.
7. `SKILL.md` and its direct references follow progressive disclosure without duplicated catalog tables.
8. Catalog search does not require loading the full node catalog into context.
9. All automated validation and selected Unreal Editor regression checks pass.
10. Remaining unknowns are explicit, versioned, and never filled by inference.

## 15. Working protocol

- Execute one phase or one bounded node batch per reviewable change.
- Inspect `git status` before each phase and preserve unrelated user changes.
- Read the reference source root directly whenever a technical fact is unclear.
- Keep the source root read-only.
- Report source gaps and request Editor evidence when source inspection cannot settle a claim.
- Do not broaden a source-audited claim into a compatibility claim for other Unreal versions.
- Re-run the relevant validation gate after every batch.

## 16. Deferred implementation work preserved from the completed review

Keep these items visible after the old task and handoff documents are removed:

- Expand regression coverage for all `examples/01` through `09`, including duplicate Pin IDs across owners,
  Texture Sample output masks, Comment containment, Material Function path/Pin order, Named Reroute
  references, and Custom dynamic Pins.
- Add generated Named Reroute paste/copy-back tests, including GUID collisions and usage-only copies.
- Add an Editor automation harness that imports generated T3D, reconstructs nodes, exports them, parses the
  result, compares canonical MGJSON, and records compile errors.
- Normalize generated catalog fragments so runtime class paths never retain a C++ `U` prefix and merge-time
  inferred/defaulted fields approach zero.
- Add versioned catalog provenance and a future catalog-diff workflow for class, Pin, default, enum, and
  asset-path changes.
- Remove hard-coded source/repository paths from maintenance tools and use an explicit source-root argument
  or environment variable.
- Improve Python and clipboard-shell discovery, including a diagnostic command and Windows PowerShell
  fallback when `pwsh` is unavailable.
- Remove or formalize one-off artifacts such as `catalog/generated/test.json` and the root extractor.
- Keep full Material asset creation outside the clipboard workflow; use a separate Editor integration if
  that capability is added.
- Add optional Asset Registry export for project-local textures, functions, and parameter collections.
- Treat semantic layout and exact coordinate fidelity separately; Comment bounds remain heuristic.

## 17. Execution record

### Phase 0 completed on 2026-07-14

- Fixed the repository baseline at `307eb76854c40b13bbad0ce293b9e5eae8996805`.
- Confirmed the read-only UE 5.8.0 source checkout and `UE5` branch marker.
- Preserved the user-owned untracked `.claude/` directory.
- Recorded that the previous 16-test baseline passed under Python 3.12.11. No directly installed Python
  interpreter was available; an offline `uv` managed runtime was identified during Phase 2.

### Phase 1 completed on 2026-07-14

- Migrated source-audit rules to `skill/references/source-verification.md`.
- Migrated source-checked Custom rules to `skill/references/custom-expressions.md`.
- Migrated narrative Editor results to `skill/catalog/editor-evidence.json`.
- Removed the completed root implementation plan and all completed `tasks/**/*.md` files.
- Replaced `tools/gen_manifest_tasks.py` with `tools/gen_manifest.py`, which generates only the manifest and
  accepts `--ue-root` or `UE_SOURCE_ROOT`.
- Verified the new generator CLI and scanned the reference source successfully: 359 classes, 11 abstract
  classes, and 37 plugin classes.
- Confirmed that active files no longer reference the removed task or handoff documents.

### Phase 2 completed on 2026-07-14

- Added `skill/catalog/node-evidence.json` with independent declaration, schema, description, and restriction
  audit states for every manifest class.
- Verified all 359 class declarations against the configured UE 5.8 source root without treating declaration
  coverage as behavioral verification.
- Source-audited the `Custom` expression across its declaration, compile paths, dynamic outputs, MIR path,
  HLSL generation, Scene Texture fixup, and include-path mappings.
- Added `tools/gen_node_evidence.py` and made `catalog_merge.py` require complete, valid evidence coverage.
- Changed the generated node index to expose descriptions and Pin names only after the corresponding source
  audit is verified.
- Changed MGJSON validation to report source-audit and Unreal Editor evidence separately instead of relying
  on the legacy `verified` boolean.
- Added provenance regression tests. All 18 unit tests pass with the offline `uv` Python runtime.

### Phase 3 completed on 2026-07-14

- Moved unaudited legacy descriptions, notes, and nested field notes for 337 nodes to
  `catalog/quarantine/legacy-node-prose.json`. The quarantine is inactive review data and cannot be restored
  by translation alone.
- Added an active-prose merge gate: a description, note, or field note now fails catalog generation unless
  its corresponding source evidence dimension is verified.
- Removed the legacy per-node `verified` boolean from generated and merged node catalogs.
- Rebuilt the manifest from the source checkout, corrected 38 plugin runtime module names, and resolved all
  25 previously missing Substrate header paths. The merged catalog now has zero missing headers.
- Made source-pending catalog schema parsing-only in `SKILL.md`; the generated index no longer presents it as
  safe generation guidance.
- Removed the unsupported frequent-node Pin table from `SKILL.md` and replaced its example with the audited
  `Custom` node.
- Removed the obsolete one-off output QA script and malformed `catalog/generated/test.json` artifact.

### Phase 4 batch 1 completed on 2026-07-14

- Added maintained, bounded audit fragments under `skill/catalog/audits/`; generated evidence now validates
  every referenced path and symbol against the configured source root.
- Source-audited `Constant`, `Constant2Vector`, `Constant3Vector`, `Add`, and `Multiply`, in addition to the
  existing `Custom` audit.
- Corrected `Constant2Vector` and `Constant3Vector` clipboard Pin names from semantic mask labels to the
  source-generated `Output`, `Output2`, `Output3`, and `Output4` names while retaining mask metadata.
- Verified declared properties, explicit binary-input defaults, output construction, compile behavior, MIR
  behavior, and generated graph Pin naming through the relevant headers, `MaterialExpressions.cpp`,
  `MaterialExpressionsToMIR.cpp`, `MaterialGraphNode.cpp`, and `EdGraphNode.h`.
- Added focused source-schema regression coverage. All 20 offline unit tests pass.

### Phase 5 completed on 2026-07-14

- Rewrote `SKILL.md`, `openai.yaml`, `mgjson.md`, `format.md`, and `mf-call.md` in English and removed the
  duplicated unsupported frequent-node table.
- Reduced the three large reference documents to direct, task-specific contracts that distinguish local tool
  behavior, UE source facts, offline round-trip evidence, and Unreal Editor evidence.
- Quarantined unsupported prose for all 82 Material Function entries because the reference checkout does not
  contain `Engine/Content`; active function paths and Pins remain parsing-only unless separate evidence exists.
- Added `tools/check_english.py` and a reviewed zero-debt baseline. Active `skill/**` content now contains zero
  CJK characters; fixtures and inactive quarantine data are explicitly exempt.
- Kept `SKILL.md` at 109 lines and each maintained prose reference under 160 lines.

### Phase 6 completed on 2026-07-14

- Added `skill/scripts/search_catalog.py` for deterministic search by class, free text, source path/symbol, Pin,
  property, plugin origin, evidence state, and generation readiness.
- Search results expose source audit and Editor round-trip states separately and hide unaudited descriptions,
  Pins, and properties.
- Replaced the 359-row Markdown node table with a 6-row generation-ready index and explicit coverage summary.
- Verified manifest, evidence, merged nodes, merged functions, and the compact index regenerate byte-for-byte.

### Phase 7 automated gate run on 2026-07-14

- Python syntax checks pass for every maintenance and bundled skill script.
- The active-skill English lint passes with zero CJK debt.
- Catalog merge outputs are deterministic and `git diff --check` passes.
- All 20 offline unit and semantic round-trip tests pass.
- The standard skill `quick_validate.py` could not import its external `PyYAML` dependency in the offline
  runtime; its complete frontmatter checks were inspected and run equivalently with the available shell.
- Unreal Editor smoke tests remain required for the corrected `Constant2Vector`/`Constant3Vector` component
  output Pin generation and for any future Material Function promotion.
