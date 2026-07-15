# Setup Guide

This guide explains how to consume the `ue-material` skill from one or more AI coding tools while keeping a
single skill source of truth. It also covers how the skill resolves its Unreal Engine source root.

The skill itself is self-contained under `skills/ue-material/` and depends only on the Python standard library
(Windows clipboard operations additionally require PowerShell). Nothing in the skill reads Unreal source at
runtime; the source root is only for manual source verification.

## 1. Choose an installation style

### A. Standard install

Copy `skills/ue-material/` into the `ue-material` directory under your Codex skills directory. The installed
directory must contain `SKILL.md` at its root:

```text
$CODEX_HOME/skills/ue-material/SKILL.md
```

Then invoke it as `$ue-material` or ask the tool to create, inspect, or modify Unreal Material Editor nodes.

### B. Shared junction setup (test / multi-tool)

When you want several AI tools to use the *same* skill source (so improvements land in one place), link each
tool's skills directory to the skill source with a Windows **directory junction**. Junctions need no admin
rights and are treated as ordinary folders by most tools.

Run from your consuming/test project root, pointing at the skill source checkout:

```powershell
$Skill = "E:\Work\ue_material_skill\skills\ue-material"

New-Item -ItemType Directory -Force -Path ".agents\skills" | Out-Null
New-Item -ItemType Directory -Force -Path ".claude\skills" | Out-Null

cmd /c mklink /J ".agents\skills\ue-material" "$Skill"
cmd /c mklink /J ".claude\skills\ue-material" "$Skill"
```

| Link path | Kind | Target |
| --- | --- | --- |
| `.agents/skills/ue-material` | Junction | `E:\Work\ue_material_skill\skills\ue-material` |
| `.claude/skills/ue-material` | Junction | `E:\Work\ue_material_skill\skills\ue-material` |

Keep the junction targets out of the consuming project's version control so the separate skill source is not
tracked twice:

```gitignore
# skill source linked from a separate repository (do not track junction contents)
.agents/skills/ue-material/
.claude/skills/ue-material/
```

Always make skill improvements in the skill source (`E:\Work\ue_material_skill`); the linked environment is
for consumption and verification only.

## 2. Resolve the Unreal Engine source root

The source root is required only for manual source verification, not for running the tools. Resolve it in this
order and stop at the first match:

1. `.ue-material/settings.json` at the working-project root (`ueSourceRoot`).
2. Environment variable `UE_SOURCE_ROOT`.
3. A user-directed limited scan of a folder you provide.

Do not scan whole drives by default. Give a start folder and scan only under it:

```powershell
param([string]$Root = "E:\UE")   # your start folder
Get-ChildItem -Path $Root -Recurse -Filter "Build.version" -Depth 6 -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match 'Engine\\Build\\Build\.version' }
```

Save only the chosen result to `.ue-material/settings.json` and gitignore it:

```jsonc
{
  "$comment": "ue-material skill local setting (environment-specific, gitignored)",
  "ueSourceRoot": "E:/UE/UE_5.8",
  "resolvedAt": "2026-07-15",
  "baseline": { "version": "5.8.0", "branch": "UE5" },
  "verified": { "materialsHeaders": true, "privateCpp": true, "gitCommitMatch": false }
}
```

```gitignore
# ue-material skill local setting (environment-specific, non-shared)
.ue-material/
```

The skill baseline is Unreal Engine 5.8.0, branch `UE5`. Confirm a resolved root matches this version and
branch (read from `Engine/Build/Build.version`). A promoted or launcher build has no `.git`, so exact
baseline-commit matching may be unavailable; a version and branch match is acceptable for development testing.
Verify it mechanically with the bundled check:

```powershell
python scripts/source_fingerprint.py --ue-root E:\UE\UE_5.8
```

`COMPATIBLE` means the root is the same engine line as the catalog; a `WARNING` means the version or branch
differs and catalog facts must be re-audited. See `skills/ue-material/references/source-verification.md` for
the full policy.

## 3. Verify the setup

Run from the installed or linked `ue-material` skill directory (Python 3.12+):

```powershell
python scripts/search_catalog.py Multiply
python scripts/validate.py --help
python scripts/source_fingerprint.py --ue-root E:\UE\UE_5.8
```

The catalog search should return provenance-annotated matches, the validator should print its usage with
exit code 0, and the fingerprint check should report `COMPATIBLE` for a baseline-matching engine. Once these
respond, the skill is usable from the configured tools.
