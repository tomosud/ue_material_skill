---
name: ue-material
description: Create, edit, validate, and analyze Unreal Engine Material Editor node graphs through compact MGJSON and clipboard T3D conversion. Use for requests about UE materials, material nodes, Material Editor graphs, shader-node wiring, parameterization, explaining copied material nodes, or modifying a copied graph. Do not use for Blueprint graphs, Niagara graphs, texture/image creation, mesh authoring, or standalone HLSL that is not being placed in a Material graph.
---

# UE Material

Use MGJSON as the only conversational representation of a Material graph. Let the bundled Python tools
create and consume verbose T3D; do not hand-author GUIDs, Pin records, or T3D in chat.

## Non-negotiable rules

- Run `scripts/validate.py` before every build. Do not build when it reports an error.
- Run `scripts/search_catalog.py` for broad discovery across every declared class, schema, source symbol, and
  legacy phrase. It returns each node as one record with field-level provenance; audit status is not a catalog
  partition or an exclusion rule.
- Read `references/source-verification.md` and inspect the configured UE source root before every factual node
  explanation or graph-generation decision. Never infer behavior from a class name or catalog prose alone.
- Preserve node object order when a stable layout matters.
- Never create or connect the Material Root node. After paste, tell the user which final output to connect
  manually to Base Color, Roughness, Normal, Emissive Color, or another Root input.
- A `MaterialFunctionCall` may call a packaged function, but this skill cannot author the function's
  internal graph. Do not recommend a function whose exact path and Pin schema lack recorded asset or Editor
  evidence.
- Treat source-audit and Editor-evidence warnings as separate provenance information, not automatic failures.
  Report any plugin, deprecated, path-uncertain, or asset-existence warning that can affect the result.
- Never paste the full T3D into the conversation. When clipboard access is unavailable, exchange it as a
  `.txt`/`.t3d` file.

## Choose the workflow

### Generate a new graph

1. Read `references/mgjson.md` when the request needs syntax beyond the summary below. Run
   `python scripts/search_catalog.py <terms>`, then inspect the returned source references in the configured UE
   source root. Do not fill gaps from memory, regardless of the recorded provenance state.
2. Write MGJSON to a temporary or user-requested `.json` file.
3. Validate it:

   ```powershell
   python scripts/validate.py graph.json
   ```

4. Resolve every error. Keep warnings visible when they describe an actual compatibility risk.
5. Build directly to the local clipboard:

   ```powershell
   python scripts/build.py graph.json --to-clipboard
   ```

6. Tell the user: "Paste with Ctrl+V in an empty area of Material Editor." Then name the one or
   more final outputs they must connect manually to the Root inputs. Mention that paste uses the current
   cursor location and preserves relative layout.

If clipboard access is unavailable, use `python scripts/build.py graph.json -o material-nodes.t3d` and
give the file to the user without expanding it into chat.

### Analyze copied nodes

When the user says they copied Material nodes, immediately parse the clipboard instead of asking them to
paste its text:

```powershell
python scripts/parse.py --from-clipboard
```

Use `--keep-pos` only when layout is relevant. Use `--stats` for a size/coverage check. Explain the compact
MGJSON result and connections; do not retrieve or quote the clipboard T3D separately.

For a remote/file workflow, ask for the exported `.txt`/`.t3d` file and run:

```powershell
python scripts/parse.py copied-nodes.txt
```

### Modify an existing graph

1. Parse the copied selection to MGJSON.
2. Edit nodes, typed properties, links, comments, and optional positions in MGJSON only.
3. Validate, then build to clipboard.
4. Give the same empty-area Ctrl+V and manual Root-connection instructions.

Do not silently retain links to nodes outside the copied selection: Unreal removes unresolved external Pin
references, and `parse.py` intentionally reports only internal links.

### Handle an unknown node

Do not approximate an unknown class or its Pin order. Ask the user to place only that node in Material
Editor, set any important non-default properties, copy it, and say when ready. Then run:

```powershell
python scripts/parse.py --from-clipboard --no-catalog --keep-pos
```

Use the resulting class and `raw_props` as evidence. Unknown Pins appear as `inN`/`outN`; request a second
sample with representative connections if direction/order matters. Until a reviewed catalog entry exists,
explain that the graph can be analyzed but `validate.py`/`build.py` will reject that class. Consult
`references/source-verification.md` before adding facts, and consult `references/format.md` only when
debugging or extending the parser/catalog.

### Work with a Custom expression

Read `references/custom-expressions.md` before generating or modifying `UMaterialExpressionCustom` code.
Use only source-backed input/output rules, keep private Engine shader APIs version-locked, and require an
Editor material compile for claims that source inspection or clipboard round-trip cannot prove.

## MGJSON quick syntax

The top level is `{"nodes": {...}, "links": [...], "pos": {...}}`. Only `nodes` is required.

```json
{
  "nodes": {
    "custom": {"class": "Custom", "props": {"Code": "return 0.0;"}}
  }
}
```

- Node IDs match `^[A-Za-z_][A-Za-z0-9_-]*$` and are local labels, not Unreal object names.
- A node is `{"class":"ShortCatalogName","props":{...}}`; `raw_props` is a last-resort map of
  single-line T3D right-hand-side strings.
- A link is `source[.output] -> destination.input`. Omitting the source output means output index 0.
- One destination input accepts at most one link. Outputs may fan out.
- `pos` values are integer `[x,y]`; omitted positions use the tool's automatic layout.
- Asset properties use object paths such as `/Game/Textures/T_Base.T_Base`; `null` means no asset.
- Read `references/mgjson.md` for typed values, comments, validation rules, and normalization.

## Node and function discovery

Use `scripts/search_catalog.py` to search source symbols, exact Pins, properties, plugins, and evidence states
without loading the complete catalog. Search includes structural data and legacy wording by default and returns
them in one node record. Use field-level `provenance` to choose which claims need closer inspection, but inspect
source before every node explanation or use. `references/nodes-index.md` is the compact entry point to the full
catalog. For a Material Function call, read `references/mf-call.md` and require separate asset or Editor evidence
before building.

## Boundaries and recovery

- Root output connections must be completed manually after paste.
- Named Reroute, Composite, Substrate, plugin nodes, and version-specific dynamic Pins may require an
  Editor sample even when cataloged.
- Asset path syntax can be checked locally; asset existence requires the user's Unreal project.
- If paste loses Pins or links, keep the MGJSON, ask for a copy-back sample, run `parse.py`, and compare
  the compact result. Do not repeatedly paste speculative T3D.
- Use `references/format.md` for T3D importer details and `references/mf-call.md` for function calls; keep
  ordinary work in MGJSON.
