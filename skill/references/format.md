# Material Editor クリップボード T3D 仕様

この文書は、Unreal Engine の Material Editor がノードのコピー/ペーストに使う
T3D テキストについて、`build.py`（生成）と `parse.py`（解析）を実装するための
基準を定める。ローカルの UE 5.8.0 ソースで確認した。ここでいう「必須」は、
単なる構文上の必須条件ではなく、安全な生成物に必要な意味上の条件も含む。

## 目次

- [処理経路と根拠](#処理経路と根拠)
- [字句と全体構造](#字句と全体構造)
- [通常の MaterialGraphNode](#通常の-materialgraphnode)
- [MaterialExpression](#materialexpression)
- [コメントノード](#コメントノード)
- [CustomProperties Pin](#customproperties-pin)
- [接続と LinkedTo](#接続と-linkedto)
- [ペースト時の再構築](#ペースト時の再構築)
- [生成規約](#生成規約)
- [解析規約](#解析規約)
- [短い構造例](#短い構造例)
- [制限事項](#制限事項)

## 処理経路と根拠

コピー時は選択ノードごとに `PrepareForCopying` を呼び、式を一時的に GraphNode の
子へ `Rename` してから T3D exporter に渡す。このため、式は GraphNode の内側に
ネストして出力される。エクスポート後は所有者を Material / MaterialFunction に戻す。

ペースト時は T3D から全オブジェクトを先に生成し、次に全プロパティを適用する。
その後、Pin 参照の解決、`PostPasteNode`、`ReconstructNode`、MaterialExpression の
所有者・GUID・特殊ノードの補正、Pin から式入力への接続反映が行われる。

PLAN.md §2 にある検証用ソース位置を以下に維持する。

| 項目 | UE ソース位置 |
|---|---|
| Material Editor のコピー入口 | `FMaterialEditor::CopySelectedNodes` — `MaterialEditor.cpp:6409` |
| 選択ノードの T3D 出力 | `FEdGraphUtilities::ExportNodesToText` — `EdGraphUtilities.cpp:458` |
| 式をノードの子へ移す処理 | `UMaterialGraphNode::PrepareForCopying` — `MaterialGraphNode.cpp:362` |
| Material Editor のペースト入口 | `FMaterialEditor::PasteNodesHereFromBuffer` — `MaterialEditor.cpp:6572` |
| T3D の GraphNode import | `FEdGraphUtilities::ImportNodesFromText` — `EdGraphUtilities.cpp:484` |
| オブジェクトの二段階生成・プロパティ適用 | `FCustomizableTextObjectFactory::ProcessBuffer` — `EditorFactories.cpp:5343` |
| Pin の出力 / 入力 | `UEdGraphPin::ExportTextItem / ImportTextItem` — `EdGraphPin.cpp:1077 / 1265` |
| SourceIndex 採番 / Pin 再構築 | `UMaterialGraphNode_Base::PostPasteNode / ReconstructNode` — `MaterialGraphNode_Base.cpp:227 / 255` |
| プロパティ入力 Pin の追加 | `UMaterialGraphNode::CreateInputPins` — `MaterialGraphNode.cpp:722` |
| Pin から式入力への反映 | `UMaterialGraph::LinkMaterialExpressionsFromGraph` — `MaterialGraph.cpp:496` |
| 特殊な式のペースト後処理 | `FMaterialEditor::PostPasteMaterialExpression` — `MaterialEditor.cpp:6478` |
| Pin 参照文字列 | `UEdGraphPin::ExportText_PinReference` — `EdGraphPin.cpp:2298` |

## 字句と全体構造

### 行指向の基本形

T3D は行指向で、1 個の選択 GraphNode が 1 個の最上位 Object ブロックになる。
複数ノードは区切り記号なしで連続する。

```ebnf
document       = { graph-node-block } ;
object-block   = begin-line, { property-line | custom-line | object-block }, end-line ;
begin-line     = ws, "Begin Object", header-fields, newline ;
end-line       = ws, "End Object", newline ;
property-line  = ws, property-name, "=", raw-value, newline ;
custom-line    = ws, "CustomProperties Pin ", pin-struct, newline ;
header-fields  = { ws, header-name, "=", header-value } ;
pin-struct     = "(", pin-field, { ",", pin-field }, [","], ")" ;
```

- exporter の標準インデントはネストごとに 3 空白だが、構造判定は
  `Begin Object` / `End Object` のスタックで行い、空白数に依存しない。
- Object 名は `Name="..."`。生成側は必ず引用符で囲む。
- class path は `/Script/<Module>.<Class>`。Material GraphNode は UnrealEd、
  MaterialExpression は Engine モジュールに属する。
- `ExportPath=` と `Archetype=` は exporter が付けることがあるが、clipboard import
  と本ツールの生成には不要である。解析側は既知の header field として読み飛ばす。
- 通常の property は 1 行に 1 個出る。値は文字列、数値、enum、object reference、
  または入れ子の struct / array であり得る。値中の `,`、`=`、括弧、引用符を考慮せず
  単純 split してはならない。
- UObject exporter は Class Default Object との差分だけを出す。従ってプロパティが
  ないことは「未定義」ではなく、多くの場合「クラス既定値」を意味する。

### 二段書きとネスト

通常ノードでは、子 MaterialExpression が次の 2 ブロックとして現れる。

1. `Class=` と `Name=` を持つ**宣言ブロック**。オブジェクトを生成する。
2. 同じ `Name=` だけを持つ**定義ブロック**。差分プロパティを適用する。

```text
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_0"
   Begin Object Class=/Script/Engine.MaterialExpressionMultiply Name="MaterialExpressionMultiply_0"
   End Object
   Begin Object Name="MaterialExpressionMultiply_0"
      ...expression properties...
   End Object
   ...graph node properties and pins...
End Object
```

これは 2 個の式ではない。同一の親スコープと Name をキーに、宣言と定義を同じ
子オブジェクトへ結合する。UE exporter は inner object を宣言してから定義する
（`UnrealExporter.cpp:602-640`）。importer は一段形式も受理し得るが、`build.py` は
エディタ出力と同じ二段形式を必ず生成する。

最上位ブロックの `Class=` と `Name=` は必須。子の宣言ブロックも `Class=` と
`Name=` が必須で、定義ブロックは `Name=` が必須である。`End Object` は各
`Begin Object` と対応しなければならない。

## 通常の MaterialGraphNode

class は原則として `/Script/UnrealEd.MaterialGraphNode`。特殊な GraphNode subclass
はカタログまたは実サンプルに class が明記されている場合だけ置換する。

### プロパティ要件

| 要素 / プロパティ | 要件 | 用途と省略時の扱い |
|---|---|---|
| header `Class` | 必須 | import 対象 class の選択。通常値は `/Script/UnrealEd.MaterialGraphNode`。 |
| header `Name` | 必須 | `LinkedTo` のノード参照キー。document 内で一意にする。 |
| 子 Expression の宣言・定義 | 必須 | ノードが表す式そのもの。詳細は次節。 |
| `MaterialExpression=<object-ref>` | 必須 | GraphNode と子 Expression を結ぶ。欠落すると Material Editor のペースト後処理が式を参照できない。 |
| `CustomProperties Pin` | 条件付き必須 | 接続を保持する Pin、および正しい出力 `SourceIndex` を得るための全出力 Pin。安全な生成規約では全 Pin を常に出す。 |
| `NodePosX`, `NodePosY` | 省略可 | 既定は 0。相対レイアウトを保持・生成する場合は両方出す。ペースト地点を中心に全ノードが平行移動される。 |
| `NodeGuid` | 省略可 | 有効な一時 GUID を出してよいが、ペースト時に再発行される。 |
| `NodeComment` | 省略可 | ノード注釈。既定は空。後で Expression の `Desc` と同期される。 |
| `AdvancedPinDisplay` ほか UEdGraphNode 差分 | 省略可 | 既定値でよければ出さない。未知値は parser が raw property として保持する。 |
| `ExportPath`, `Archetype` | 省略可 | header の exporter 情報。本ツールは生成しない。 |

実機サンプル `example/sample.txt` では、`MaterialExpression` の object reference は
値全体を二重引用符で囲む次の形だった。`build.py` はこれを canonical form とする。

```text
MaterialExpression="/Script/Engine.MaterialExpressionMultiply'MaterialExpressionMultiply_0'"
```

内部式への参照には親 GraphNode 名を含む相対 path が現れる場合がある。PLAN §2.2 の
草案例にある class quote の内側で object path だけを引用する表記も parser は許容し、
引用符を正規化して同じ宣言済み子を解決する。

## MaterialExpression

式 class は `/Script/Engine.MaterialExpression<ClassSuffix>`。子 object 名は class の
末尾名に連番を付け、親 GraphNode 内で一意にする。

### プロパティ要件

| 要素 / プロパティ | 要件 | 用途と省略時の扱い |
|---|---|---|
| 宣言 header `Class` | 必須 | 生成する具体的 MaterialExpression class。抽象基底 class は不可。 |
| 宣言 header `Name` | 必須 | 親の `MaterialExpression=` と式入力参照の解決キー。 |
| 定義 header `Name` | 必須 | 宣言済みの子にプロパティを適用する。 |
| ノード固有 UPROPERTY | 意図する値が既定値と異なる場合に必須 | 例: `R=0.5`, `Constant=(R=...,G=...)`, `ParameterName="Roughness"`, `Texture=...`。カタログの props または `raw_props` をそのまま T3D 値へ変換する。 |
| `MaterialExpressionEditorX/Y` | 省略可 | GraphNode の `NodePosX/Y` から再同期される。エディタ出力との同形性のため重複出力してもよい。 |
| `MaterialExpressionGuid` | 省略可 | ペースト後に強制再発行される。一時 GUIDを出してもよい。 |
| `Material`, `Function` | 省略可、生成禁止 | ペースト先の Material / MaterialFunction で上書きされる。環境依存なので出さない。 |
| `SubgraphExpression` | 通常は省略 | ペースト先 graph の値で上書きされる。Composite 等は特殊処理に従う。 |
| `GraphNode` | 省略必須 | transient。`PostEditImport` が back pointer を設定する。T3D に生成しない。 |
| `Desc` | 省略可 | GraphNode の `NodeComment` から再同期される。 |
| 式入力（例: `A=(Expression=...)`） | 省略可 | Pin の `LinkedTo` から再構築される冗長表現。安全側の生成では併記する。 |

`FExpressionInput` の代表的な生値は次の形である。

```text
A=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_0.MaterialExpressionConstant_0'")
A=(Expression="/Script/Engine.MaterialExpressionTextureSample'MaterialGraphNode_1.MaterialExpressionTextureSample_0'",OutputIndex=2)
```

`OutputIndex` は source の出力配列 index で、0 は省略可能。`Mask`, `MaskR/G/B/A`,
`InputName` が付く場合もあるが、ペースト後の接続では source output の情報から更新される。
接続の正本には使わない。

asset object reference も同じく値全体を二重引用符で囲む。PLAN §2.3 の asset path を
実機サンプルで確認した object reference の quoting に合わせると次の形になる。

```text
Texture="/Script/Engine.Texture2D'/Game/T_x.T_x'"
```

存在しない asset path は `None` に解決されるだけで、GraphNode 自体の import は継続する。

## コメントノード

コメントは通常式ノードとは別 class であり、Pin を持たない。

```text
GraphNode class: /Script/UnrealEd.MaterialGraphNode_Comment
child class:     /Script/Engine.MaterialExpressionComment
pointer property: MaterialExpressionComment=<object-ref>
```

### プロパティ要件

| 対象 | 要素 / プロパティ | 要件 | 用途と省略時の扱い |
|---|---|---|---|
| GraphNode | header `Class`, `Name` | 必須 | comment node の生成と識別。 |
| GraphNode | 子 comment expression の宣言・定義 | 必須 | 通常式と同じ二段書き。 |
| GraphNode | `MaterialExpressionComment` | 必須 | 子 comment expression との対応。 |
| GraphNode | `NodePosX`, `NodePosY` | 省略可 | 左上位置。生成側はレイアウトのため出す。 |
| GraphNode | `NodeWidth`, `NodeHeight` | 意図する枠サイズに必須 | 省略時は class 既定値。包含ノードの bounds + margin から生成する。 |
| GraphNode | `NodeComment` | コメント文字列に必須 | 表示文字列。空なら省略可。 |
| GraphNode | `CommentColor`, `FontSize` | 非既定値の場合に必須 | 色は `(R=...,G=...,B=...,A=...)`。FontSize の既定は class に従う。 |
| GraphNode | `bCommentBubbleVisible_InDetailsPanel`, `bColorCommentBubble`, `MoveMode` | 非既定値の場合に必須 | bubble 表示、bubble 色、group movement。 |
| GraphNode | `NodeGuid` | 省略可 | 通常ノード同様に再発行される。 |
| GraphNode | `CustomProperties Pin` | 不要 | comment node に Pin はない。 |
| Expression | `SizeX`, `SizeY`, `Text` | 省略可だが併記推奨 | ペースト後は GraphNode の width / height / comment から同期される。 |
| Expression | `CommentColor`, `FontSize`, `bCommentBubbleVisible_InDetailsPanel`, `bColorCommentBubble`, `bGroupMode` | 省略可だが併記推奨 | GraphNode 側がペースト後の正本。生成側はエディタ出力との同形性のため両側に出してよい。 |
| Expression | `Material`, `Function`, `GraphNode` | 生成禁止 | 通常式と同様に所有者と back pointer が再設定される。 |

`LinkMaterialExpressionsFromGraph` は GraphNode の位置、文字列、サイズ、色、bubble 設定、
MoveMode を comment expression にコピーする（`MaterialGraph.cpp:597-624`）。従って desired
state は必ず GraphNode 側に書く。

## CustomProperties Pin

### 1 行の構造

各 Pin は GraphNode のプロパティ領域に 1 行で記述する。

```text
CustomProperties Pin (PinId=00112233445566778899AABBCCDDEEFF,PinName="A",LinkedTo=(MaterialGraphNode_0 11112222333344445555666677778888,),)
```

`UEdGraphNode::ImportCustomProperties` は `Pin` token の後を `UEdGraphPin::ImportTextItem`
へ渡す。外側の `(...)`、field の `name=value`、field 間の comma が必要で、末尾 comma
は exporter と同様に許可される。未知 field や未知 `PinType.*` member は parse error に
なるため、生成側はこの節の既知 field だけを出す。

### field 仕様

| field | 型 / 形式 | 構文上 | 安全な生成プロファイル |
|---|---|---|---|
| `PinId` | 32 桁 hex GUID | 必須 | document 内で一意。全 `LinkedTo` と一致させる。 |
| `PinName` | quoted FName | 省略可 | 全 Pin で必ず出す。入力は再構築時の名前照合に必須。 |
| `Direction` | quoted enum | 省略時 `EGPD_Input` | 出力だけ `Direction="EGPD_Output"` を必ず出す。 |
| `PinType.PinCategory` | quoted FName | 省略可 | UE 5.8実機で全data Pinから省略しても入力・出力・接続が再構築された。build.pyは出さない。 |
| その他 `PinType.*` | struct member の T3D 値 | 省略可 | 原則出さない。reconstruct で式 class から再生成される。 |
| `LinkedTo` | Pin reference array | 未接続なら省略 | 接続 Pin では必須。書式は次節。 |
| `DefaultValue` | quoted string | 省略可 | property input 等で既定値を保持する必要がある場合だけ出す。 |
| `AutogeneratedDefaultValue` | quoted string | 省略可 | 通常生成しない。 |
| `DefaultObject` | object path string | 省略可 | 通常生成しない。 |
| `DefaultTextValue` | FText | 省略可 | 通常生成しない。 |
| `PinFriendlyName`, `PinToolTip` | FText / string | 省略可 | 表示情報。通常生成しない。 |
| `SubPins`, `ParentPin`, `ReferencePassThroughConnection` | Pin reference array / reference | 省略可 | split pin 等の実サンプルを保持するときだけ出す。 |
| `PersistentGuid` | GUID | 省略可 | 通常生成しない。 |
| `bHidden`, `bNotConnectable`, `bDefaultValueIsReadOnly`, `bDefaultValueIsIgnored`, `bAdvancedView`, `bOrphanedPin`, `bHasSnappedChild`, `bHasSnappedParent` | `True` / `False` | 省略可 | catalog または raw sample が要求する場合だけ出す。 |

Pin import の真の構文最小セットは有効な `PinId` だけである
（`EdGraphPin.cpp:1543-1549`）。ただし Material node を正しく再構築するための実用最小は
次のとおり。

- 入力 Pin: `PinId`, `PinName`。接続時は `LinkedTo` も必要。
- 出力 Pin: `PinId`, `PinName`, `Direction="EGPD_Output"`。接続時は `LinkedTo` も必要。
- 全入力を catalog の `inputs` 順、その後に `prop_pins` 順で出す。
- 全出力を catalog の `outputs` 順で、未接続でも省略せず出す。
- UE 5.8.0-55116800実機では `PinType.*` を全7 Pinから省略した
  Constant×2 → Multiplyの値とA/B接続が完全に復元された。この実用最小を生成規約とする。

## 接続と LinkedTo

Pin reference 1 個の書式は、空白 1 個で区切った次の 2 要素である。

```text
<相手GraphNodeのName> <相手PinId>
```

配列は外側を括弧で囲み、各要素の後ろに comma を置く。

```text
LinkedTo=(MaterialGraphNode_1 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,)
LinkedTo=(MaterialGraphNode_1 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,MaterialGraphNode_2 BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB,)
```

これは `UEdGraphPin::ExportText_PinReference` の
`OwningNode->GetName() + " " + PinId.ToString()` そのものである
（`EdGraphPin.cpp:2298-2304`）。参照先 Pin が後で出現しても deferred resolution される。
document 外を指す unresolved reference は import 終了時に除去される。

Material の通常 data input は実質 1 接続なので、generator は 1 input に複数 source を
作らない。接続は source output と destination input の**両方**の `LinkedTo` に同じ関係を
記載する。UE は片側だけでも reciprocal link を補正できるが、build / validate の規約では
両方向一致を必須とする。parser は両側記載を 1 本に deduplicate し、Direction に基づいて
`output -> input` に正規化する。

Pin の配列順は意味を持つ。`PostPasteNode` は既存 Pin を登場順に走査し、data input、
data output、exec input、exec output ごとに 0 始まりの `SourceIndex` を採番する
（`MaterialGraphNode_Base.cpp:227-247`）。続く `ReconstructNode` は data input を
`PinName` 優先、見つからなければ `SourceIndex` で照合し、data output は
`SourceIndex` だけで照合する（同 `:255-317`）。従って TextureSample の
RGB / R / G / B / A のような複数出力は、未接続出力を含めて class 本来の順に全列挙する。

## ペースト時の再構築

PLAN.md §2.3 の 10 項目を実装規則として以下に保持する。

1. **接続の正本は Pin の `LinkedTo`**。`LinkMaterialExpressionsFromGraph` が Pin link
   から `FExpressionInput`（`A=(Expression=...)` 等）を再構築する。Expression 側の
   入力プロパティは冗長で、併記してもよい。
2. **`LinkedTo` は `<相手ノード名> <相手PinId>`**。PinId は generator が採番し、
   参照元・参照先と両方向 link を整合させる（`EdGraphPin.cpp:2298`）。
3. **Pin の記載順が `SourceIndex` を決める**。入力は `PinName` 優先、出力は
   `SourceIndex` のみで再照合される。入力名を正しくし、全出力を正順で列挙する。
4. **PinType はペースト中に捨てられ、式 class から再生成される**。出力 Pin の
   `Direction="EGPD_Output"` だけは旧 Pin の方向判定に必要なので省略しない。
5. **`NodeGuid`, `MaterialExpressionGuid` 等は再発行される**。入力 T3D 内では
   任意の一意な有効 GUID でよく、省略可能な GUID は省略してよい。
6. **`ShowAsInputPin` 付き UPROPERTY も入力 Pin**。通常の `FExpressionInput` 群の後に
   並び、同じ data input の `SourceIndex` に数えられる（`MaterialGraphNode.cpp:722`）。
7. **asset 参照は path 文字列**。存在しない path は `None` になるだけで、ペースト
   自体は成功する。
8. **Material の最終出力 Root はペースト不可**。Root は `CanDuplicateNode=false` である。
   複数選択のコピー文面には `MaterialGraphNode_Root` と Root への `LinkedTo` が現れる
   ことが実機サンプルで確認できたが、import factory は Root を生成しない。generator は
   Root と最後の 1 本を出さず、parser は Root と Root にだけ接続する link を除外し、
   BaseColor 等への最後の接続はユーザーへ手動接続を案内する。
9. **Expression の `Material=` / `Function=` はペースト先で上書き**されるため、
   generator は省略し、parser は環境依存 property として捨てる。
10. **MaterialFunctionCall / NamedReroute / Composite には特殊処理**がある
    （`MaterialEditor.cpp:6478`）。FunctionCall は `UpdateFromFunctionResource` で
    function asset から input/output を更新するため、function asset path と正しい
    Pin 名・順序を保持する。NamedReroute は全式追加後に declaration/usage を補正し、
    Composite は子 graph を deep copy して再構築する。これらは catalog または実機
    sample なしに一般ノードへ単純化しない。

処理順を実装観点でまとめると、(a) 全 Object と property を import、(b) PinId で参照を
解決し document 外 link を削除、(c) `PostPasteNode` で SourceIndex 採番、
(d) `ReconstructNode` で class 本来の Pin を作り旧 Pin の link 等を移動、
(e) 所有者・back pointer・GUID・特殊式を補正、(f) `LinkedTo` から Expression input を
確定、となる。生成側は (c)(d) で照合に必要な `PinName`、方向、順序を失わせてはならない。

## 生成規約

`build.py` は最低限、次の順で T3D を組み立てる。

1. node id ごとに一意な GraphNode name、Expression name、PinId を割り当てる。
2. catalog の `inputs + prop_pins`、`outputs` から全 Pin を順番どおり作る。
3. link を PinId に展開し、両端の `LinkedTo` を対称にする。
4. Expression 入力 property も安全のため併記する。source output index が 0 以外なら
   `OutputIndex` を出す。ただし `LinkedTo` と矛盾させない。
5. 各通常ノードを「最上位 GraphNode → Expression 宣言 → Expression 定義 →
   `MaterialExpression` pointer → node properties → Pin 行」の順で出す。
6. comment は comment expression を二段書きし、desired state を GraphNode 側へ必ず
   書く。必要なら expression 側にも mirror property を書く。
7. property は default と異なるものだけでよい。`raw_props` は property name と
   T3D 生値を変更せず Expression 定義へ出す。
8. `Material`, `Function`, `GraphNode`, destination Root node は出さない。

名前は document 内で一意なら任意だが、空白を避け、次を推奨する。

```text
MaterialGraphNode_0
MaterialExpressionMultiply_0
MaterialGraphNode_Comment_0
MaterialExpressionComment_0
```

## 解析規約

`parse.py` は次の情報を損失なく抽出する。

1. `Begin Object` で stack push、`End Object` で pop する。EOF 時に stack が空でない、
   または余分な `End Object` があれば構文エラーにする。
2. 最上位の MaterialGraphNode / MaterialGraphNode_Comment ごとに 1 node を作る。
3. 同じ親内の同名 Expression 宣言ブロックと定義ブロックを結合する。
4. GraphNode の `MaterialExpression` / `MaterialExpressionComment` 参照で主たる子を確定する。
5. `CustomProperties Pin` の outer `(...)` を、引用符と括弧 depth を追跡して field に分解する。
6. 全 Pin を読み終えてから `(node name, PinId)` table を作り、`LinkedTo` を解決する。
   実clipboardでは異なるノード間で同じPinIdが再利用される場合があるため、PinId単独を
   document全体のkeyにしてはならない。
   選択外ノードを指す参照は実 clipboard に現れ得るため、未解決外部 link は警告可能な
   破棄対象とし、構文エラーにしない。
7. link は output/input の direction と Pin の登場 index から正規化し、両側記載を重複除去する。
   `MaterialGraphNode_Root` と、それにだけ接続する link は MGJSON node/link に含めない。
8. Expression input property は接続抽出に使わない。`LinkedTo` が正本である。
9. `MaterialExpressionEditorX/Y`, GUID 類、`Material`, `Function`, `GraphNode` は props から除外する。
   `--keep-pos` の場合だけ GraphNode の `NodePosX/Y` を位置として保持する。
10. catalog で型が分かる property は値を MGJSON に変換し、未知 property は raw T3D 値を
    `raw_props` に保持する。未知 header field も解析失敗の理由にはしない。

class 名、object reference、enum、bool は大文字小文字を保持する。GUID の比較だけは
hyphen や case を正規化してよい。PinName は FName だが、外部形式へ出す際は表示された
文字列を保持する。

## 短い構造例

次はユーザー提供の実機 clipboard `example/sample.txt` から、Constant ノード 1 個を
そのまま抜粋した例である。`ExportPath`、環境依存の `Material`、完全な PinType と UI field
は実出力には現れるが、前節までに示した理由で generator の必須 field ではない。
`Value` は `ShowAsInputPin` 由来の property input で、式の通常入力がないため最初の input、
`Output` がその次に並ぶ。また出力の `LinkedTo` にはこの抜粋外（選択外）のノード参照もある。

```text
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_2" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.MM_Sub_Basic:MaterialGraph_0.MaterialGraphNode_2'"
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_1" ExportPath="/Script/Engine.MaterialExpressionConstant'/Engine/Transient.MM_Sub_Basic:MaterialGraph_0.MaterialGraphNode_2.MaterialExpressionConstant_1'"
   End Object
   Begin Object Name="MaterialExpressionConstant_1" ExportPath="/Script/Engine.MaterialExpressionConstant'/Engine/Transient.MM_Sub_Basic:MaterialGraph_0.MaterialGraphNode_2.MaterialExpressionConstant_1'"
      MaterialExpressionEditorX=-736
      MaterialExpressionEditorY=-224
      MaterialExpressionGuid=2D60CF0F4F2C03B1AB259CBFC713F735
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.MM_Sub_Basic'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionConstant'MaterialExpressionConstant_1'"
   NodePosX=-736
   NodePosY=-224
   NodeGuid=E296D8264FA7B197968117BAEE49BF7E
   CustomProperties Pin (PinId=6331F1D448FC7D94672C11A78C8F44E2,PinName="Value",PinType.PinCategory="optional",PinType.PinSubCategory="red",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0.0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=True,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=8864390F4AC4B66D088E2DA7FBAC5E2F,PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=(MaterialGraphNode_0 14E4D0074826EA2DE394409A34162EEF,MaterialGraphNode_1 132181FA42DF31D22C288CAE1ACBC9C9,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

## 制限事項

- `example/sample.txt` で通常ノード、Root、property input、両方向 link、完全な Pin field、
  object reference の引用符を確認した。ただしサンプルに UE Editor の正確なバージョン記録と
  Comment / Texture / MaterialFunctionCall / NamedReroute / Composite はない。これら class 固有形式は
  E01/T08 の追加サンプルで実機確認する。
- Engine/Content がないため、エンジン組み込み MaterialFunction asset の実体は確認できない。
  FunctionCall は catalog と実機 sample を優先する。
- T3D は UE の一般 UObject text format であり全機能は広い。本仕様の対象は Material Editor
  clipboard の GraphNode、MaterialExpression、Comment、Pin に限定する。
