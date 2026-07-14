---
name: ue-material
description: Create, edit, validate, and analyze Unreal Engine Material Editor node graphs through compact MGJSON and clipboard T3D conversion. Use for requests about UE materials, material nodes, Material Editor graphs, shader-node wiring, parameterization, explaining copied material nodes, or modifying a copied graph. Do not use for Blueprint graphs, Niagara graphs, texture/image creation, mesh authoring, or standalone HLSL that is not being placed in a Material graph.
---

# UE Material

Use MGJSON as the only conversational representation of a Material graph. Let the bundled Python tools
create and consume verbose T3D; do not hand-author GUIDs, Pin records, or T3D in chat.

## Non-negotiable rules

- Run `scripts/validate.py` before every build. Do not build when it reports an error.
- Use class and Pin names from `catalog/nodes.json` or `references/nodes-index.md`; do not guess.
- Preserve node object order when a stable layout matters.
- Never create or connect the Material Root node. After paste, tell the user which final output to connect
  manually to Base Color, Roughness, Normal, Emissive Color, or another Root input.
- A `MaterialFunctionCall` may call a packaged function, but this skill cannot author the function's
  internal graph. Use `catalog/functions.json` and only its exact asset paths and Pin names.
- Treat `warning: ... not Editor-verified` as provenance information, not an automatic failure. Report
  any plugin, deprecated, path-uncertain, or asset-existence warning that can affect the user's result.
- Never paste the full T3D into the conversation. When clipboard access is unavailable, exchange it as a
  `.txt`/`.t3d` file.

## Choose the workflow

### Generate a new graph

1. Read `references/mgjson.md` when the request needs syntax beyond the summary below. Search
   `references/nodes-index.md` for suitable classes and check their exact catalog entries.
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

6. Tell the user: “Material Editor の何もない所で Ctrl+V してください。” Then name the one or
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
`references/format.md` only when debugging or extending the parser/catalog.

## MGJSON quick syntax

The top level is `{"nodes": {...}, "links": [...], "pos": {...}}`. Only `nodes` is required.

```json
{
  "nodes": {
    "color": {"class": "Constant3Vector", "props": {"Constant": [0.8, 0.15, 0.05]}},
    "gain": {"class": "ScalarParameter", "props": {"ParameterName": "Gain", "DefaultValue": 1.0}},
    "mul": {"class": "Multiply"}
  },
  "links": ["color -> mul.A", "gain -> mul.B"]
}
```

- Node IDs match `^[A-Za-z_][A-Za-z0-9_-]*$` and are local labels, not Unreal object names.
- A node is `{"class":"ShortCatalogName","props":{...}}`; `raw_props` is a last-resort map of
  single-line T3D right-hand-side strings.
- A link is `source[.output] -> destination.input`. Omitting the source output means output index 0.
- One destination input accepts at most one link. Outputs may fan out.
- `pos` values are integer `[x,y]`; omitted positions use 300×180 automatic layout.
- A grouped comment is
  `{"class":"Comment","props":{"Text":"Label","nodes":["a","b"]}}`.
- Asset properties use object paths such as `/Game/Textures/T_Base.T_Base`; `null` means no asset.
- Read `references/mgjson.md` for typed values, comments, validation rules, and normalization.

## Frequent classes and effective Pin names

The first output shown may be omitted in link syntax. Property input Pins are included after ordinary inputs.

| class | inputs | outputs |
|---|---|---|
| `Constant` | Value | Output |
| `Constant2Vector` | X, Y | RG, R, G |
| `Constant3Vector` | Constant | RGB, R, G, B |
| `ScalarParameter` | DefaultValue | Output |
| `VectorParameter` | DefaultValue | RGB, R, G, B, A, RGBA |
| `TextureCoordinate` | CoordinateIndex, UTiling, VTiling, UnMirrorU, UnMirrorV | Output |
| `TextureSample` | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA |
| `TextureSampleParameter2D` | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA |
| `Multiply` | A, B | Output |
| `Add` | A, B | Output |
| `Subtract` | A, B | Output |
| `Divide` | A, B | Output |
| `LinearInterpolate` | A, B, Alpha | Output |
| `OneMinus` | Input | Output |
| `Clamp` | Input, Min, Max, ClampMode | Output |
| `Fresnel` | ExponentIn, BaseReflectFractionIn, Normal | Output |
| `DotProduct` | A, B | Output |
| `Normalize` | VectorInput | Output |
| `ComponentMask` | Input, R, G, B, A | Output |
| `AppendVector` | A, B | Output |

Always prefer the live catalog over this table when they differ. For a Material Function call, read
`references/mf-call.md` before building because its input/output arrays are dynamic.

## Boundaries and recovery

- Root output connections must be completed manually after paste.
- Named Reroute, Composite, Substrate, plugin nodes, and version-specific dynamic Pins may require an
  Editor sample even when cataloged.
- Asset path syntax can be checked locally; asset existence requires the user's Unreal project.
- If paste loses Pins or links, keep the MGJSON, ask for a copy-back sample, run `parse.py`, and compare
  the compact result. Do not repeatedly paste speculative T3D.
- Use `references/format.md` for T3D importer details and `references/mf-call.md` for function calls; keep
  ordinary work in MGJSON.
