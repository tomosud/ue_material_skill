# -*- coding: utf-8 -*-
"""UEソースを走査して MaterialExpression クラスの確定マニフェストを作り、
カタログタスク(tasks/catalog/C*.md)を再生成する。

usage: python tools/gen_manifest_tasks.py   (ripgrep `rg` が必要)

Output: catalog/manifest.json   (クラス名 -> ヘッダ/モジュール/abstract等フラグ)
        tasks/catalog/C*.md     (対象クラス表つきタスクファイル。既存C*.mdは削除される)
        stdout                  (tasks/README.md 用の索引表)

UEバージョンを更新したら再実行し、README.mdの表とタスクstatusを手で照合すること。
"""
import json
import os
import re
import subprocess
import sys
import io
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UE = r"C:\work\unreal\UnrealEngine-release\Engine"
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# クラス宣言の走査(前方宣言 `class X;` は行末`;`で除外。2行宣言は base 無しで拾い後段で解決)
PATTERN = r"^\s*class\s+([A-Z0-9_]+_API\s+)?UMaterialExpression\w*\s*(:\s*public[^;]*)?$"

def resolve_rg():
    import shutil
    for cand in [os.environ.get("RG_PATH"), shutil.which("rg"),
                 os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\rg.exe")]:
        if cand and os.path.isfile(cand):
            return cand
    return None

if len(sys.argv) > 2 and sys.argv[1] == "--scan":
    SCAN = sys.argv[2]  # 事前走査済みファイルを使う
else:
    rg = resolve_rg()
    if not rg:
        sys.exit("ripgrep(rg)が見つからない。RG_PATH を設定するか、以下を手動実行して\n"
                 "  cd %s && rg -n --no-heading -g *.h \"%s\" Source Plugins > scan.txt\n"
                 "  python tools/gen_manifest_tasks.py --scan scan.txt" % (UE, PATTERN))
    SCAN = os.path.join(tempfile.gettempdir(), "matexpr_scan.txt")
    with open(SCAN, "w", encoding="utf-8") as scan_out:
        subprocess.run([rg, "-n", "--no-heading", "-g", "*.h", PATTERN, "Source", "Plugins"],
                       cwd=UE, stdout=scan_out, check=True)
TASK_DIR = os.path.join(PROJ, "tasks", "catalog")
CATALOG_DIR = os.path.join(PROJ, "catalog")

DECL_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):\s*class\s+(?:[A-Z0-9_]+_API\s+)?"
    r"(?P<cls>UMaterialExpression[A-Za-z0-9_]*)\s*(?::\s*public\s+(?P<base>[A-Za-z0-9_:]+))?\s*$")

def find_base(path_abs, line_no):
    """Declaration continues on following lines; find ': public X'."""
    try:
        with open(path_abs, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None
    for l in lines[line_no:line_no + 3]:
        mb = re.search(r":\s*public\s+([A-Za-z0-9_:]+)", l)
        if mb:
            return mb.group(1)
    return None

entries = {}
with open(SCAN, "r", encoding="utf-8", errors="replace") as f:
    for raw in f:
        m = DECL_RE.match(raw.strip())
        if not m:
            continue
        cls = m.group("cls")
        path = m.group("path").replace("\\", "/")
        line = int(m.group("line"))
        base = m.group("base") or find_base(os.path.join(UE, path), line)
        if base is None:
            continue  # not a real declaration
        # skip generated/intermediate dirs
        if "/Intermediate/" in path:
            continue
        short = cls[len("UMaterialExpression"):] or "(root)"
        if cls in entries:  # duplicate decl (shouldn't happen for UCLASS)
            entries[cls]["dup"] = entries[cls].get("dup", []) + [path]
            continue
        entries[cls] = {"short": short, "header": path, "line": line, "base": base}

# read UCLASS line above each decl to detect abstract/deprecated
file_cache = {}
for cls, e in entries.items():
    p = os.path.join(UE, e["header"])
    if p not in file_cache:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                file_cache[p] = f.readlines()
        except OSError:
            file_cache[p] = []
    lines = file_cache[p]
    idx = e["line"] - 1
    flags = ""
    # look back up to 12 lines for UCLASS(...) possibly multi-line
    back = "".join(lines[max(0, idx - 12):idx])
    mu = re.search(r"UCLASS\s*\(([^)]*)\)", back, re.S)
    if mu:
        flags = re.sub(r"\s+", " ", mu.group(1)).strip()
    e["abstract"] = bool(re.search(r"\babstract\b", flags, re.I))
    e["deprecated"] = ("Deprecated" in flags) or cls.endswith("_DEPRECATED")
    # module: Source/<Tree>/<Module>/... or Plugins/<...>/Source/<Module>/...
    parts = e["header"].split("/")
    if parts[0] == "Source":
        e["module"] = parts[2] if len(parts) > 2 else "?"
        e["origin"] = "engine"
    else:  # Plugins
        e["module"] = parts[1] if len(parts) > 1 else "Plugins"
        e["origin"] = "plugin"

# drop the root base class from batching but keep in manifest
manifest = {e["short"]: {
    "class": cls,
    "header": "Engine/" + e["header"],
    "base": e["base"],
    "module": e["module"],
    "origin": e["origin"],
    "abstract": e["abstract"],
    "deprecated": e["deprecated"],
} for cls, e in entries.items()}

os.makedirs(CATALOG_DIR, exist_ok=True)
with open(os.path.join(CATALOG_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)

shorts = {s for s in manifest if s != "(root)"}
print("total classes: %d  (abstract=%d, deprecated=%d, plugin=%d)" % (
    len(shorts),
    sum(1 for s in shorts if manifest[s]["abstract"]),
    sum(1 for s in shorts if manifest[s]["deprecated"]),
    sum(1 for s in shorts if manifest[s]["origin"] == "plugin")))

# ---------------- batches ----------------
BATCHES_A = [
    ("C01", "定数・パラメータ", ["Constant", "Constant2Vector", "Constant3Vector", "Constant4Vector",
        "ConstantBiasScale", "ScalarParameter", "VectorParameter",
        "DoubleVectorParameter", "StaticBool", "StaticBoolParameter", "StaticSwitch",
        "StaticSwitchParameter", "StaticComponentMaskParameter", "ChannelMaskParameter",
        "Parameter"]),
    ("C02", "基本演算", ["Add", "Subtract", "Multiply", "Divide", "Modulo", "Fmod", "Power",
        "SquareRoot", "Abs", "Sign", "Floor", "Ceil", "Round", "Truncate", "Frac",
        "OneMinus", "Min", "Max", "Clamp", "Saturate"]),
    ("C03", "補間・条件・三角・指数", ["LinearInterpolate", "InverseLinearInterpolate", "SmoothStep",
        "Step", "If", "Sine", "Cosine", "Tangent", "Arcsine", "ArcsineFast",
        "Arccosine", "ArccosineFast", "Arctangent", "ArctangentFast", "Arctangent2",
        "Arctangent2Fast", "Exponential", "Exponential2", "Logarithm", "Logarithm2", "Logarithm10"]),
    ("C04", "ベクトル演算・法線", ["DotProduct", "CrossProduct", "Normalize", "ComponentMask",
        "AppendVector", "Distance", "Length", "Desaturation", "Fresnel", "SphereMask",
        "RotateAboutAxis", "DeriveNormalZ", "Transform", "TransformPosition"]),
    ("C05", "テクスチャ・UV", ["TextureSample", "TextureSampleParameter2D", "TextureObject",
        "TextureObjectParameter", "TextureCoordinate", "Panner", "Rotator", "BumpOffset",
        "TextureProperty", "TextureSampleParameterCube", "AntialiasedTextureMask",
        "TextureBase", "TextureSampleParameter"]),
    ("C06", "座標・ジオメトリデータ", ["WorldPosition", "ActorPositionWS", "ObjectPositionWS",
        "CameraPositionWS", "CameraVectorWS", "PixelNormalWS", "VertexNormalWS",
        "VertexTangentWS", "ReflectionVectorWS", "LocalPosition", "ScreenPosition",
        "ViewSize", "SceneTexelSize", "ObjectBounds", "ObjectLocalBounds", "ObjectRadius",
        "ObjectOrientation", "TwoSidedSign", "PixelDepth", "SceneDepth"]),
    ("C07", "時間・ユーティリティ", ["Time", "DeltaTime", "VertexColor", "Noise", "VectorNoise",
        "BlackBody", "HsvToRgb", "RgbToHsv", "DepthFade", "DistanceCullFade",
        "DynamicParameter", "PerInstanceRandom", "PerInstanceFadeAmount", "PerInstanceCustomData",
        "EyeAdaptation", "SceneColor", "SceneTexture", "SRGBColorToWorkingColorSpace"]),
    ("C08", "構造ノード・MaterialAttributes", ["Comment", "Reroute", "RerouteBase",
        "NamedRerouteBase", "NamedRerouteDeclaration", "NamedRerouteUsage",
        "Composite", "PinBase", "MaterialFunctionCall", "FunctionInput", "FunctionOutput",
        "Custom", "GetMaterialAttributes", "SetMaterialAttributes", "MakeMaterialAttributes",
        "BreakMaterialAttributes", "BlendMaterialAttributes"]),
]

SPECIAL_NOTES = {
    "C01": "Parameter は抽象基底(継承関係の記録が目的)。",
    "C05": "TextureBase / TextureSampleParameter は抽象基底。TextureSample の MipValueMode による動的ピンは notes に必ず記載。",
    "C08": "Custom は Inputs/AdditionalOutputs 配列で動的ピンになる特殊ノード — 配列構造を props に詳しく記録。",
}

used = set()
batches = []
warn = []
for tid, title, classes in BATCHES_A:
    ok = [c for c in classes if c in shorts]
    missing = [c for c in classes if c not in shorts]
    if missing:
        warn.append("%s: not in manifest: %s" % (tid, ", ".join(missing)))
    used |= set(ok)
    batches.append((tid, title, "A", ok, SPECIAL_NOTES.get(tid, "")))

# rest: engine substrate gets own batch; plugins get own batches by module
rest = sorted(shorts - used)
sub = [s for s in rest if manifest[s]["header"].endswith("MaterialExpressionSubstrate.h")]
plugin_rest = [s for s in rest if manifest[s]["origin"] == "plugin" and s not in sub]
engine_rest = [s for s in rest if manifest[s]["origin"] == "engine" and s not in sub]

CHUNK = 16
n = 9
for i in range(0, len(engine_rest), CHUNK):
    chunk = engine_rest[i:i + CHUNK]
    batches.append(("C%02d" % n, "その他(Engine) %s〜%s" % (chunk[0], chunk[-1]), "B", chunk, ""))
    n += 1
if sub:
    batches.append(("C%02d" % n, "Substrate系", "B", sub,
                    "Substrate無効環境では使えない旨を各エントリの notes に記載。"))
    n += 1
# plugin batches grouped by module
from collections import OrderedDict
bymod = OrderedDict()
for s in plugin_rest:
    bymod.setdefault(manifest[s]["module"], []).append(s)
plugin_group = []
for mod, cls_list in bymod.items():
    plugin_group.append((mod, cls_list))
# chunk plugin groups into batches of <=CHUNK classes, keeping modules together where possible
cur, cur_n = [], 0
def flush_plugin(cur):
    global n
    if not cur:
        return
    mods = sorted({manifest[s]['module'] for s in cur})
    batches.append(("C%02d" % n, "プラグイン系 (%s)" % ", ".join(mods), "B", sorted(cur),
                    "プラグイン由来のノード。該当プラグイン有効時のみペースト可能な旨を notes に記載。"))
    n += 1
for mod, cls_list in plugin_group:
    if cur_n + len(cls_list) > CHUNK and cur:
        flush_plugin(cur)
        cur, cur_n = [], 0
    cur.extend(cls_list)
    cur_n += len(cls_list)
flush_plugin(cur)

# ---------------- write task files ----------------
if os.path.isdir(TASK_DIR):
    for fn in os.listdir(TASK_DIR):
        if re.match(r"C\d+\.md$", fn):
            os.remove(os.path.join(TASK_DIR, fn))
os.makedirs(TASK_DIR, exist_ok=True)

TEMPLATE = """# {tid}: ノードカタログ — {title} [優先度{prio} / 並列可]

status: TODO
output: `catalog/generated/{tid}.json`

**必ず先に `tasks/INSTRUCTIONS-catalog.md` を読むこと。**
手順・出力スキーマ・抽出ルール・完了条件は全てそこに書いてある。

対象クラスは下表で**確定**(catalog/manifest.json から機械生成。検索・推測は不要)。
表のクラス以外を追加しない。全クラスを1つ残らずJSONに含めること
(abstract/deprecated はフラグのみでよい)。

## 対象クラス

| クラス | ヘッダ(C:\\work\\unreal\\UnrealEngine-release\\ 以下) | 備考 |
|---|---|---|
{rows}
{notes}"""

index = []
for tid, title, prio, classes, note in batches:
    rows = []
    for s in classes:
        m = manifest[s]
        remark = []
        if m["abstract"]:
            remark.append("abstract")
        if m["deprecated"]:
            remark.append("deprecated")
        if m["origin"] == "plugin":
            remark.append("plugin:" + m["module"])
        rows.append("| %s | %s | %s |" % (m["class"], m["header"].replace("/", "\\"), " ".join(remark)))
    notes = ("\n## このバッチの注意\n\n" + note + "\n") if note else ""
    body = TEMPLATE.format(tid=tid, title=title, prio=prio, rows="\n".join(rows), notes=notes)
    with open(os.path.join(TASK_DIR, tid + ".md"), "w", encoding="utf-8") as f:
        f.write(body)
    index.append((tid, title, prio, len(classes)))

print()
for w in warn:
    print("WARN " + w)
print()
covered = used | set(sub) | set(plugin_rest) | set(engine_rest)
print("coverage: %d / %d classes in batches" % (len(covered), len(shorts)))
print()
for tid, title, prio, k in index:
    print("| [%s](catalog/%s.md) | %s | %d | %s | TODO |" % (tid, tid, title, k, prio))
