# Unreal Engine Source Data Refresh

This document records the repository's current refresh procedure. It does not introduce a new audit workflow
or infer node behavior automatically. Inspect the requested Unreal Engine source directly whenever a fact is
unclear.

## Baseline

- Current reference version: Unreal Engine 5.8.0, branch `UE5`.
- Repository development checkout: `C:\work\unreal\UnrealEngine-release`.
- Distribution metadata stores source-relative paths and reads the checkout location from `UE_SOURCE_ROOT`.
- Treat the checkout as read-only.

Set the source root for the shell that runs the existing generators:

```powershell
$env:UE_SOURCE_ROOT = 'C:\work\unreal\UnrealEngine-release'
```

## Existing refresh commands

Run these commands from the repository root.

1. Rebuild the declaration manifest from the configured checkout:

   ```powershell
   uv run --offline --no-project python -B dev/tools/gen_manifest.py
   ```

2. Refresh declaration evidence while preserving maintained audit overrides:

   ```powershell
   uv run --offline --no-project python -B dev/tools/gen_node_evidence.py
   ```

   This step proves declarations only. It does not promote schema, description, restriction, compile, or
   Editor claims. Those require direct source inspection and, where applicable, an Editor fixture.

   This step also stamps the baseline into `node-evidence.json` from `Engine/Build/Build.version` and the
   checkout's `.git`: `source.version`, `source.git_commit`, and a `source.fingerprint` (`version|branch`).
   The `BranchName` is normalized to its engine stream (for example `++UE5+Release-5.8` becomes `UE5`) so the
   fingerprint matches both GitHub source and launcher promoted builds of the same release. Consumers compare
   this baseline with `skills/ue-material/scripts/source_fingerprint.py`.

3. Merge the existing generated catalog fragments into the distributable catalog and regenerate the compact
   node index:

   ```powershell
   uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
   ```

4. Review all generated differences. For each changed class, inspect its declaration, constructor, Pin
   overrides, outputs, `Compile`, `Build`, restrictions, plugin ownership, and deprecation state as applicable.
   Do not translate or restore legacy prose as a factual description without that inspection.

5. Run the current offline gates:

   ```powershell
   uv run --offline --no-project python -B -m unittest discover -s dev/tests -v
   uv run --offline --no-project python -B dev/tools/check_english.py
   uv run --offline --no-project python -B dev/tools/check_distribution.py
   ```

## Data locations

- `dev/catalog/manifest.json`: generated declaration manifest.
- `dev/catalog/generated/`: maintained node and Material Function input fragments.
- `dev/catalog/audits/`: bounded source-audit overrides.
- `skills/ue-material/catalog/node-evidence.json`: distributable source references and provenance.
- `skills/ue-material/catalog/nodes.json`: merged node catalog.
- `skills/ue-material/catalog/functions.json`: merged Material Function catalog.
- `skills/ue-material/catalog/legacy-node-prose.json`: searchable legacy wording, not source evidence.

The quarantine tools under `dev/tools/` are migration utilities, not normal source-refresh steps. Use them only
when intentionally moving unsupported prose out of generated fragments.

## Manual follow-up

Record unresolved facts instead of guessing. Dynamic Pins, inherited behavior, Material Function assets,
Named Reroutes, Composite graphs, Substrate nodes, plugins, clipboard reconstruction, and shader compilation
may need focused source review or a versioned Unreal Editor sample after a source update.

## Capturing new source-verified facts

When source inspection establishes a new fact, record it in the maintained catalog rather than in a local,
per-machine file. This keeps every verified fact fingerprinted, reviewed, and shared through the distribution.

1. Add or update a bounded override under `dev/catalog/audits/` for the class. Each entry needs an `audit`
   block (`declaration`/`schema`/`description`/`restrictions` set to a valid state) and a `references` list of
   `{ "path": <source-relative>, "symbol": <exact symbol>, "claims": [...] }`. `gen_node_evidence.py` verifies
   that every referenced symbol exists in the resolved source before writing.
2. For merged schema, Pins, defaults, or descriptions, update the corresponding fragment under
   `dev/catalog/generated/` so `catalog_merge.py` folds it into `nodes.json`.
3. Regenerate (`gen_node_evidence.py`, `catalog_merge.py`) and run the offline gates above. Review every
   generated difference against source before committing.
