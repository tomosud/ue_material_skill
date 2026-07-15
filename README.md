# UE Material Skill Repository

This repository develops and packages the `ue-material` Codex skill. The skill converts between compact
MGJSON and Unreal Engine Material Editor clipboard T3D, validates graph structure, searches Material Expression
metadata, and preserves source and Editor provenance.

## Repository layout

- `skills/ue-material/` is the self-contained distributable skill.
- `dev/catalog/` contains manifests, generated fragments, maintained audits, and inactive function prose.
- `dev/fixtures/` contains Unreal Editor captures and semantic round-trip inputs.
- `dev/tests/` contains offline regression tests.
- `dev/tools/` contains catalog generators, linters, and distribution checks.
- `dev/docs/` contains development plans and the current source-refresh procedure.
- `dist/` is reserved for generated release archives and is not tracked.

Development has a one-way dependency on the packaged skill. Files under `skills/ue-material/` must not depend
on `dev/`, repository-local fixtures, or local absolute paths.

## Install the skill

Copy `skills/ue-material/` to the `ue-material` directory under your Codex skills directory. The installed
directory must contain `SKILL.md` at its root. For a standard personal installation, the resulting path is:

```text
$CODEX_HOME/skills/ue-material/SKILL.md
```

Then invoke it as `$ue-material` or ask Codex to create, inspect, or modify Unreal Material Editor nodes.

For a shared junction-based setup across multiple AI tools and for resolving the Unreal Engine source root,
see `SETUP.md`.

## Basic usage

Run commands from the installed `ue-material` skill directory. The scripts use only the Python standard
library; Windows clipboard operations additionally require PowerShell.

Search every declared Material Expression, including legacy Japanese or English wording:

```powershell
python scripts/search_catalog.py texture sample
python scripts/search_catalog.py --class TextureSample
```

Validate MGJSON before building:

```powershell
python scripts/validate.py graph.json
```

Build to Unreal clipboard T3D or a file:

```powershell
python scripts/build.py graph.json --to-clipboard
python scripts/build.py graph.json -o material-nodes.t3d
```

Parse copied or exported Material nodes:

```powershell
python scripts/parse.py --from-clipboard
python scripts/parse.py material-nodes.t3d
```

## Specification summary

- MGJSON is the conversational graph format; T3D is an import/export detail handled by the scripts.
- Node IDs are local stable labels. Links use `source[.output] -> destination.input`.
- The Material Root node is never generated or connected. Connect final outputs manually after paste.
- Material Function calls require a packaged function path and recorded Pin schema; this skill does not author
  a function's internal graph.
- Custom expressions have version-specific input, output, include, define, and shader-compilation constraints.
- Catalog prose and provenance help discovery, but every factual node explanation and generation decision must
  be checked against the resolved Unreal Engine source checkout.
- Resolve the source root in order: `.ue-material/settings.json` (`ueSourceRoot`), then `UE_SOURCE_ROOT`, then
  a user-directed limited scan of a user-provided folder. Do not scan whole drives by default. Catalog source
  paths are relative to that root. See `skills/ue-material/references/source-verification.md`.

Detailed specifications live in the distributable skill:

- `skills/ue-material/references/mgjson.md`
- `skills/ue-material/references/format.md`
- `skills/ue-material/references/custom-expressions.md`
- `skills/ue-material/references/mf-call.md`
- `skills/ue-material/references/source-verification.md`

## Development checks

The repository currently uses an offline `uv` Python runtime:

```powershell
uv run --offline --no-project python -B -m unittest discover -s dev/tests -v
uv run --offline --no-project python -B dev/tools/check_english.py
uv run --offline --no-project python -B dev/tools/check_distribution.py
uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
```

The Unreal Engine source baseline and the existing data-refresh commands are documented in
`dev/docs/source-update.md`. The refactoring history and remaining audit work are recorded in
`dev/docs/refactoring-plan.md`.
