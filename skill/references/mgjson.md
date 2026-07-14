# MGJSON 仕様

MGJSON は、Unreal Engine Material Graph と AI の間で使うコンパクトな JSON 形式である。
T3D 固有の GUID、object name、全 Pin field、所有者参照を隠し、意味のあるノード、
プロパティ、接続だけを表す。`validate.py`、`build.py`、`parse.py` は本仕様を正本とする。

## 目次

- [文書構造](#文書構造)
- [ノード](#ノード)
- [プロパティ値](#プロパティ値)
- [接続](#接続)
- [位置と自動レイアウト](#位置と自動レイアウト)
- [コメント](#コメント)
- [カタログとの対応](#カタログとの対応)
- [検証規則](#検証規則)
- [parse.py の正規化規則](#parsepy-の正規化規則)
- [例](#例)

## 文書構造

### 形式

```ebnf
document      = object containing "nodes" [and "links"] [and "pos"] ;
nodes         = object { node-id : node } ;
links         = array of link-string ;
pos           = object { node-id : [x, y] } ;
node          = normal-node | comment-node ;
normal-node   = { "class": class-name,
                  ["props": object], ["raw_props": object] } ;
comment-node  = { "class": "Comment", ["props": comment-props] } ;
```

JSON は UTF-8。top-level は object でなければならない。

| key | 必須 | 型 | 意味 |
|---|---:|---|---|
| `nodes` | yes | object | node id から node 定義への map。空は禁止。 |
| `links` | no | array[string] | 接続。省略時は空配列。 |
| `pos` | no | object | 明示位置。省略 node は自動配置。 |

未知の top-level key は typo を隠すため error とする。JSON object の key 重複は通常の
parser では後勝ちになるが、本ツールは `object_pairs_hook` 等で検出して error とする。

### node id

node id は document 内の短い識別子で、次を満たす。

```regex
^[A-Za-z_][A-Za-z0-9_-]*$
```

- 大文字小文字を区別する。
- `.`、空白、`->` は link parser との曖昧さを避けるため禁止する。
- object の key なので一意でなければならない。
- Unreal の object name や GUID とは無関係で、T3D 生成時に別途割り当てる。

## ノード

### 通常ノード

```json
{
  "class": "Multiply",
  "props": {"ConstB": 0.5},
  "raw_props": {"FutureProperty": "(X=1.0,Y=2.0)"}
}
```

| key | 必須 | 型 | 規則 |
|---|---:|---|---|
| `class` | yes | string | `MaterialExpression` を除いたカタログ短名。完全 class path は不可。 |
| `props` | no | object | カタログ `props` の property 名と typed JSON 値。省略時は空。 |
| `raw_props` | no | object[string] | カタログ未収載 property の T3D 右辺生値。省略時は空。 |

node 内の未知 key は error。`props` と `raw_props` に同じ property 名を置くことは禁止する。
class 既定値と同じ `props` は入力として許可するが、`parse.py` は省略する。

### 未知 class

`parse.py` はカタログにない MaterialExpression も捨てず、class suffix と `raw_props` を
出力する。この MGJSON は解析・引き継ぎには有効だが、Pin 構成を生成できないため
`validate.py` / `build.py` は unknown class を error にする。再生成するには、そのノード
1 個の clipboard sample から class、input、property input、全 output の順序をカタログへ
追加する。`raw_props` は「未知 property」の escape hatch であり、未知 Pin schema の代替ではない。

### abstract / deprecated

- catalog の `abstract: true` class は生成不能なので error。
- `deprecated: true` class は warning。class が現行 UE で生成可能なら build は続行できる。
- `verified: false` は通常状態で error にしない。必要に応じて warning summary に含める。

## プロパティ値

`props` の key は catalog entry の `props` key をそのまま使う。値の JSON 表現は
catalog の `type` に従う。

| catalog type | MGJSON 値 | 例 |
|---|---|---|
| `float`, `double` | finite number | `0.5` |
| `int8`〜`int64`, `uint8`〜`uint64` | integer | `2` |
| `bool` | boolean | `true` |
| `FName`, `FString`, `FText` | string | `"Roughness"` |
| `enum:EType` | enum value name string | `"SAMPLERTYPE_Color"` |
| `asset:Type` | Unreal asset path string または `null` | `"/Game/Textures/T_Base.T_Base"` |
| `FLinearColor`, `FColor` | number array 3 または 4 要素 | `[1.0, 0.2, 0.0]` |
| `FVector2D`, `FIntPoint` | number / integer array 2 要素 | `[2.0, 2.0]` |
| `FVector`, `FVector3f` | number array 3 要素 | `[0.0, 0.0, 1.0]` |
| `FVector4`, `FVector4f` | number array 4 要素 | `[1.0, 0.0, 0.0, 1.0]` |
| `FGuid` | 32 hex string | `"00112233445566778899AABBCCDDEEFF"` |
| その他の既知 struct | JSON object または catalog が定める array | `{"x": 1, "y": 2}` |

### 色

- `[r,g,b]` は alpha を class 既定値、既定値が得られなければ `1.0` とする。
- `[r,g,b,a]` は alpha を明示する。
- 値域は HDR color を許すため 0〜1 に制限しない。全要素は finite number とする。
- parse は T3D `(R=...,G=...,B=...,A=...)` を array に変換する。

### asset path

- `/Game/...`、`/Engine/...`、plugin mount path `/PluginName/...` を許可する。
- object path は原則 `Package.Asset` まで含める。
- 空 string は禁止し、参照なしは `null` を使う。
- build は catalog の具体的 asset type を使って T3D object reference に変換する。
- path の存在確認は Editor asset registry が必要なため validate の対象外。

### enum

enum は整数でなく C++ / T3D の value name を使う。catalog が enum choices を持つ場合は
厳密照合し、持たない場合は non-empty string の型検査だけを行い warning を出せる。

### raw_props

`raw_props` の value は T3D property line の `=` より右側だけを表す string である。

```json
"raw_props": {
  "CustomStruct": "(Mode=Foo,Weights=(1.0,2.0))"
}
```

- property 名は `^[A-Za-z_][A-Za-z0-9_]*(?:\([0-9]+\))?$` を満たす。
- value に改行を含めてはならない。
- build は解釈・再引用せず `PropertyName=<raw value>` として Expression 定義へ出す。
- `Material`, `Function`, `GraphNode`, editor position、GUID property は環境依存なので
  raw_props にも出さない。

## 接続

### canonical syntax

```text
src[.output] -> dst.input
```

```ebnf
link       = source-endpoint, " -> ", destination-endpoint ;
source-endpoint = node-id, [ ".", output-name ] ;
destination-endpoint = node-id, ".", input-name ;
```

- canonical separator は両側 1 空白の ` -> `。parser / validator は arrow 周辺の追加空白を
  許容して trim するが、serializer は canonical form で出す。
- source の output 名省略は、その class の output index 0 を意味する。
- destination input 名は必須。
- endpoint は最初の `.` で node id と Pin 名に分ける。Pin 名は前後を trim し、空は禁止。
- Pin 名には空白、日本語、括弧を許すが `->` は禁止する。

### Pin 名の正規化

カタログ field から MGJSON で使う effective name を次で決める。

入力 (`inputs` の後に `prop_pins`):

1. `name` が non-empty なら `name`。
2. 空なら `prop`。
3. それもなければ `in<index>`。

出力 (`outputs` 順):

1. `name` が non-empty なら `name`。
2. 空で `mask` が non-empty なら `mask`（例: `RGB`, `R`, `G`, `B`, `A`）。
3. index 0 なら `Output`。
4. それ以外は `out<index>`。

source output を省略した場合は常に index 0 であり、その effective name が `RGB` でも
`Output` でも同じ Pin を指す。serializer は compactness のため index 0 を省略する。

### 接続制約

- source は output、destination は input / prop_pin でなければならない。
- 1 input に入る link は最大 1 本。複数なら error。
- 同一 link の重複は error。
- self-loop を含む data cycle は warning。UE の一部特殊 graph を除き通常は意図しない。
- output は複数 input に fan-out できる。
- Comment は endpoint にできない。
- Root node は MGJSON に存在しない。BaseColor 等への最終接続は表現せず、build 後に
  Material Editor で手動接続する。

## 位置と自動レイアウト

`pos` は node id から `[x,y]` への map。

```json
"pos": {"uv": [-600, 0], "tex": [-300, 0]}
```

- x, y は finite integer。float 入力は error とする。
- `nodes` にない id は error。
- position がない通常 node は build が接続 DAG の深さで左から右へ配置する。
- column 間隔 300 px、row 間隔 180 px。同じ depth は node 定義順に上から下へ並べる。
- cycle の node は、cycle 外 predecessor から得られる最大 depth、なければ depth 0 に置く。
- 明示 pos は変更しない。明示 node も自動配置 node の depth 計算には参加する。
- parse は既定で position を捨て、`--keep-pos` のときだけ GraphNode の `NodePosX/Y` を出す。

JSON object の insertion order を layout と ID 採番の安定化に使う。実装は入力順を保持する。

## コメント

Comment は予約 class `Comment` で表す。

```json
{
  "class": "Comment",
  "props": {
    "Text": "Base color",
    "nodes": ["uv", "tex"],
    "CommentColor": [0.1, 0.25, 0.5, 1.0],
    "FontSize": 18
  }
}
```

comment props:

| key | 型 | 規則 |
|---|---|---|
| `Text` | string | 表示文字列。省略時は空。 |
| `nodes` | array[string] | 包含する通常 node id。一意、1個以上。省略可。 |
| `CommentColor` | 3/4 number array | 省略時は UE 既定色。 |
| `FontSize` | positive integer | 1〜1000。 |
| `bCommentBubbleVisible_InDetailsPanel` | bool | optional。 |
| `bColorCommentBubble` | bool | optional。 |
| `MoveMode` | string | `GroupMovement` または `NoGroupMovement`。 |
| `SizeX`, `SizeY` | positive integer | `nodes` がない手動枠だけで使用。 |

`nodes` がある場合、build は対象通常 node の position を先に確定し、各 node を
240×120 px とみなした bounding box に上下左右 80 px の margin を加える。Comment の
`NodePosX/Y`, `NodeWidth/Height` と Expression mirror property をこの bounds から生成する。
この場合 Comment 自身の `pos` と `SizeX/SizeY` は競合するため error。

`nodes` がない場合は自由 comment とし、`pos` を使う。size 省略時は 400×200 px。
Comment の `nodes` に別 Comment、自分自身、存在しない id を指定してはならない。

## カタログとの対応

`skill/catalog/nodes.json` の各短名 entry を使う。

| MGJSON | catalog |
|---|---|
| `node.class` | top-level key |
| `node.props` key/type | `entry.props` key/type/default |
| destination input | `entry.inputs` + `entry.prop_pins` の effective name |
| source output | `entry.outputs` の effective name / index |
| T3D class path | `entry.class` |

property input は通常 input の後に並ぶ。この順序は T3D `SourceIndex` の生成に必須。
全 output も接続有無にかかわらず catalog 順で T3D に出す。

## 検証規則

`validate.py` は diagnostic を `error` と `warning` に分ける。error が 1 件以上なら exit 1、
error なしなら warning があっても exit 0。成功時は exit 0。JSON / I/O 自体の失敗も exit 1。

### error

1. JSON syntax error、duplicate key、top-level / node shape 不正、未知 key。
2. node id 不正、空 nodes、未知 class、abstract class。
3. props / raw_props の型不正、未知 typed prop、同名衝突、raw value の改行。
4. pos の未知 id、非整数座標、Comment bounds 指定との競合。
5. link syntax 不正、未知 node / Pin、source input、destination output。
6. destination input への複数 link、duplicate link。
7. Comment endpoint / 不正な包含 id、Comment の再帰包含。

class / property / Pin の未知名には `difflib.get_close_matches` 等で最も近い候補を最大3件示す。
diagnostic path は `$`, `$.nodes.mul.class`, `$.links[2]` のような JSONPath 風表記にする。

### warning

1. deprecated / unverified class。
2. 孤立した通常 node（link なし）。node が1個だけの document では警告しない。
3. data cycle / self-loop。
4. catalog に enum choices がなく値を厳密検査できない場合。
5. `raw_props` 使用、asset path の存在未確認。

build は validate を関数として呼び、error があれば T3D を一切出力しない。

## parse.py の正規化規則

1. T3D の MaterialGraphNode_Root と Root だけへの link を捨てる。
2. GraphNode class から `MaterialExpression` suffix を除いて `class` を得る。
3. node id は次の alias + 1始まり連番を使用する。alias 未登録なら class 名を lower camel
   ではなく ASCII lowercase にして用いる。

| class | alias |
|---|---|
| `Constant`, `Constant2Vector`, `Constant3Vector`, `Constant4Vector` | `const` |
| `ScalarParameter` | `scalar` |
| `VectorParameter` | `vector` |
| `TextureCoordinate` | `uv` |
| `TextureSample`, `TextureSampleParameter2D` | `tex` |
| `Multiply` | `mul` |
| `Add` | `add` |
| `LinearInterpolate` | `lerp` |
| `MaterialFunctionCall` | `mf` |
| `Comment` | `comment` |

例: 最初の Multiply は `mul1`、2個目は `mul2`。T3D の出現順に採番する。

4. 接続は `LinkedTo` だけから復元し、両方向記載を1本に deduplicate する。
5. catalog がある場合は effective Pin name を使い、source index 0 は省略する。
6. catalog がない / Pin が一致しない場合は入力 `in<index>`、出力 `out<index>` を使う。
7. known prop は T3D から typed MGJSON へ変換し、catalog default と deep-equal なら省略する。
8. 未知 property は `raw_props` に右辺をそのまま保存する。
9. `MaterialExpressionEditorX/Y`, `NodeGuid`, `MaterialExpressionGuid`, `ExpressionGUID`,
   `Material`, `Function`, `GraphNode`, `ExportPath` は出力しない。ただし parameter 固有の
   `ExpressionGUID` は意味上必要な場合もペーストで再発行されるため省略する。
10. `--keep-pos` のときだけ通常 node と自由 Comment の pos を出す。包含 Comment の geometry
    は可能なら内包関係へ戻し、確定できなければ自由 Comment として size / pos を保持する。

JSON 出力は `ensure_ascii=false`、compact separator を使用してよい。`--stats` は MGJSON の代わりに
node 数、Comment 数、内部 link 数、unknown class / raw prop 数だけを出す。

## 例

### 1. 単純な演算

```json
{
  "nodes": {
    "a": {"class": "Constant", "props": {"R": 0.25}},
    "b": {"class": "Constant", "props": {"R": 2.0}},
    "mul": {"class": "Multiply"}
  },
  "links": ["a -> mul.A", "b -> mul.B"]
}
```

### 2. テクスチャとパラメータ

```json
{
  "nodes": {
    "uv": {"class": "TextureCoordinate", "props": {"UTiling": 2.0, "VTiling": 2.0}},
    "tex": {
      "class": "TextureSampleParameter2D",
      "props": {
        "ParameterName": "BaseTex",
        "Texture": "/Game/Textures/T_Base.T_Base"
      }
    },
    "strength": {"class": "ScalarParameter", "props": {"ParameterName": "Strength", "DefaultValue": 1.0}},
    "mul": {"class": "Multiply"}
  },
  "links": [
    "uv -> tex.Coordinates",
    "tex.RGB -> mul.A",
    "strength -> mul.B"
  ],
  "pos": {"uv": [-600, 0]}
}
```

### 3. コメント付き

```json
{
  "nodes": {
    "color": {"class": "Constant3Vector", "props": {"Constant": [0.8, 0.15, 0.05]}},
    "gain": {"class": "ScalarParameter", "props": {"ParameterName": "Gain", "DefaultValue": 1.0}},
    "mul": {"class": "Multiply"},
    "group": {
      "class": "Comment",
      "props": {
        "Text": "Tint controls",
        "nodes": ["color", "gain", "mul"],
        "CommentColor": [0.12, 0.22, 0.42, 1.0]
      }
    }
  },
  "links": ["color -> mul.A", "gain -> mul.B"]
}
```
