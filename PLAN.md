# UE Material 操作 Claude Skill — 調査結果と実装計画 (v2)

作成: 2026-07-13 / v2改訂: 2026-07-14
調査対象: `C:\work\unreal\UnrealEngine-release` (UE 5.8, branch UE5)

v2の変更点: **AIはT3Dを直接読み書きしない**。コンパクトな中間フォーマット(MGJSON)で
入出力し、T3Dへの組み立て/分解はPythonツールが行う。クリップボード連携により
T3Dテキストは会話に一切登場しない。作業は `tasks/` 配下の小タスクに分割済み。

## 1. ゴール

Claude Skill「ue-material」を作る。できること:

1. **自然言語 → マテリアルノード生成**: 「Fresnelでリムライト」→ ツールがT3Dを
   クリップボードへ書き込み → ユーザーは Material Editor で Ctrl+V するだけ
2. **エディタからのコピー解析**: ユーザーがエディタでノードをコピー →
   ツールがクリップボードから読んで中間JSONに要約 → Claudeが構造を理解・説明・改変
3. **往復編集**: 既存グラフの部分改変(パラメータ化、ノード差し替え、接続変更)

## 2. 調査結果: クリップボード形式の仕組み(確定事項)

### 2.1 コピー/ペーストのコードパス

| 処理 | 場所 |
|---|---|
| コピー | `FMaterialEditor::CopySelectedNodes` — MaterialEditor.cpp:6409 |
| エクスポート | `FEdGraphUtilities::ExportNodesToText` — EdGraphUtilities.cpp:458 (`UExporter::ExportToOutputDevice`、T3D形式) |
| ペースト | `FMaterialEditor::PasteNodesHereFromBuffer` — MaterialEditor.cpp:6572 |
| インポート | `FEdGraphUtilities::ImportNodesFromText` — EdGraphUtilities.cpp:484 → `FCustomizableTextObjectFactory::ProcessBuffer` — EditorFactories.cpp:5343 |
| Pin書式 | `UEdGraphPin::ExportTextItem / ImportTextItem` — EdGraphPin.cpp:1077 / 1265 |
| ペースト後処理 | `UMaterialGraphNode_Base::PostPasteNode / ReconstructNode` — MaterialGraphNode_Base.cpp:227 / 255 |
| 接続の確定 | `UMaterialGraph::LinkMaterialExpressionsFromGraph` — MaterialGraph.cpp:496 |

コピー時は `UMaterialGraphNode::PrepareForCopying` (MaterialGraphNode.cpp:362) が
MaterialExpression をノードの子に Rename するため、クリップボードには
**GraphNode の中に Expression がネストされた形** で出る。

### 2.2 テキスト形式(T3D)

1ノード = 1つの `Begin Object Class=/Script/UnrealEd.MaterialGraphNode` ブロック。

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_0"
   Begin Object Class=/Script/Engine.MaterialExpressionMultiply Name="MaterialExpressionMultiply_0"
   End Object
   Begin Object Name="MaterialExpressionMultiply_0"
      A=(Expression=/Script/Engine.MaterialExpressionConstant'"MaterialGraphNode_1.MaterialExpressionConstant_0"')
      MaterialExpressionEditorX=-200
      MaterialExpressionEditorY=64
      MaterialExpressionGuid=A1B2C3D4E5F60718293A4B5C6D7E8F90
   End Object
   MaterialExpression=/Script/Engine.MaterialExpressionMultiply'"MaterialExpressionMultiply_0"'
   NodePosX=-200
   NodePosY=64
   NodeGuid=00112233445566778899AABBCCDDEEFF
   CustomProperties Pin (PinId=<GUID32hex>,PinName="A",PinType.PinCategory="optional",LinkedTo=(MaterialGraphNode_1 <相手PinId>,),...)
   CustomProperties Pin (PinId=<GUID>,PinName="B",...)
   CustomProperties Pin (PinId=<GUID>,PinName="Output",Direction="EGPD_Output",...)
End Object
```

構文ルール:
- 先頭ブロックは `Class=` と `Name=` が必須。`ExportPath=` は省略可
- サブオブジェクトは「`Class=`付き宣言ブロック → `Name=`のみのプロパティブロック」の2段書き
  (エディタ出力形式。1段でもimport側は受理)
- プロパティは **デフォルト値との差分のみ** 記載
- コメントは `Class=/Script/UnrealEd.MaterialGraphNode_Comment` + `MaterialExpressionComment`

### 2.3 実装から確定した重要な事実

1. **接続は Pin の `LinkedTo` が正**。ペースト後 `LinkMaterialExpressionsFromGraph` が
   PinリンクからExpression入力(`A=(Expression=...)`)を**再構築**する。
   Expression側の入力プロパティはペースト時は冗長(入れても無害)。
2. **`LinkedTo` 書式は `<相手ノード名> <相手PinId>`** (EdGraphPin.cpp:2298)。
   PinId(32桁hex GUID)は自分で採番して両側を整合させればよい。
3. **Pinの記載順が SourceIndex を決める**(PostPasteNodeが登場順に連番)。
   ReconstructNode の照合は **入力=PinName優先、出力=SourceIndexのみ**。
   → 入力Pinは正しい名前を付ける。**出力Pinは全出力を正順で列挙必須**
   (TextureSampleのRGB/R/G/B/Aなどで誤配線防止)。
4. **PinTypeの中身はペースト時に捨てられ再生成**されるため最小限でよい。
   出力Pinのみ `Direction="EGPD_Output"` が必要。
5. **NodeGuid / MaterialExpressionGuid 等はペースト時に再発行** → 任意のユニーク値でよい。
6. **プロパティ入力ピン**(`ShowAsInputPin` メタ付きUPROPERTY)も入力ピンとして
   FExpressionInput の後に並び SourceIndex に数えられる (MaterialGraphNode.cpp:722)。
7. **アセット参照はパス文字列**: `Texture=/Script/Engine.Texture2D'"/Game/T_x.T_x"'`。
   存在しないパスは None になるだけでペーストは成功する。
8. **最終出力ノード(Root)はペースト不可** → BaseColor等への最後の1本は手動接続を案内。
9. `Material=` / `Function=` プロパティはペースト側で上書きされるため省略可。
10. MaterialFunctionCall / NamedReroute / Composite はペースト後の特殊処理あり
    (MaterialEditor.cpp:6478 `PostPasteMaterialExpression`)。FunctionCallは
    `UpdateFromFunctionResource` でMFアセットから再構築される → MFパスとピン名だけ正しければよい。

### 2.4 ノードの規模

- `MaterialExpression*.h` は **275ヘッダ** (`Engine/Source/Runtime/Engine/Public/Materials/`)。
  実装の大半は `Private/Materials/MaterialExpressions.cpp`(巨大)か個別cpp。
- 入力ピン: `FExpressionInput` 型UPROPERTYの宣言順 + ShowAsInputPinプロパティ
- 出力ピン: 既定1本。コンストラクタで `Outputs` 上書きのクラスあり(TextureSample等)
- 入力名: 既定はプロパティ名。`GetInputName` オーバーライドあり

### 2.5 環境の確認事項

- PowerShell `Get-Clipboard` / `Set-Clipboard` が動作 → **ツールがクリップボードを直接読み書きできる**
- このチェックアウトに `Engine/Content` なし → エンジン組み込みMFのuassetは参照不可。
  MFナレッジはモデル知識+実機検証フラグで管理する

## 3. アーキテクチャ v2: 中間フォーマット + 変換ツール

### 3.1 判断の根拠

| | T3Dを直接AIが読み書き | 中間フォーマット+ツール(採用) |
|---|---|---|
| トークン | 1ノード約300〜700tok(Pin行のGUIDが支配的) | 1ノード約15〜40tok。**90%以上削減** |
| 正確性 | GUID採番・Pin順序・整合をAIが毎回間違えずに書く必要 | 機械的な部分は全てツールが保証 |
| クリップボード | ユーザーが長文を貼る/コピーする | `Get-Clipboard`/`Set-Clipboard`で**T3Dは会話に登場しない** |
| レイアウト | NodePosX/Yを全ノードでAIが決める | ツールが自動レイアウト(posは省略可) |

結論: AIの入出力は中間フォーマット(MGJSON)に限定し、T3D変換は決定的なPythonツールに任せる。
これは正確性の面でも優れる(GUID・ピン順序のヒューマンエラー相当が消える)。

### 3.2 中間フォーマット MGJSON(仕様詳細はタスクT02)

```json
{
  "nodes": {
    "uv":  {"class": "TextureCoordinate", "props": {"UTiling": 2.0, "VTiling": 2.0}},
    "tex": {"class": "TextureSampleParameter2D",
            "props": {"ParameterName": "BaseTex", "Texture": "/Game/Textures/T_Base.T_Base"}},
    "mul": {"class": "Multiply"}
  },
  "links": [
    "uv -> tex.UVs",
    "tex.RGB -> mul.A",
    "tex.A -> mul.B"
  ],
  "pos": {"uv": [-600, 0]}
}
```

- ノードIDは短い任意名。`class` は `MaterialExpression` を除いた短名
- `links` は `"src[.出力名] -> dst.入力名"`。出力名省略=第1出力
- `props` はデフォルトと違うものだけ。`pos` は省略可(ツールが左→右に自動レイアウト)
- コメント枠: `{"class": "Comment", "props": {"Text": "...", "nodes": ["uv","tex"]}}` で包含指定

### 3.3 ツール(scripts/)

| ツール | 役割 |
|---|---|
| `build.py` | MGJSON → T3D。ピン構成はカタログ参照、GUID採番、自動レイアウト。`--to-clipboard` / stdout |
| `parse.py` | T3D → MGJSON。`--from-clipboard` / ファイル。位置・GUID等のノイズを捨てて要約 |
| `validate.py` | MGJSON検証(カタログ照合: クラス名/ピン名/props、リンク整合、循環検出) |
| `catalog_merge.py` | `catalog/generated/*.json` を結合・lint して `catalog/nodes.json` を生成 |

ワークフロー:
- **生成**: Claude が MGJSON を書く → `validate.py` → `build.py --to-clipboard` →
  「エディタで Ctrl+V してください。BaseColorへの接続だけ手動で」
- **解析**: ユーザー「エディタでコピーした」→ `parse.py --from-clipboard` →
  MGJSONだけがコンテキストに入る → 説明・改変 → `build.py --to-clipboard` で返す
- フォールバック(リモート環境等): ファイル渡し(ユーザーがtxtに貼る/受け取る)

### 3.4 カタログ(catalog/)

ツールがピン順序・ピン名・プロパティを知るための正データ。
`catalog/generated/<タスクID>.json`(各AIワーカーの成果物)→ merge → `catalog/nodes.json`。
スキーマと抽出ルールは `tasks/INSTRUCTIONS-catalog.md` に固定済み(全ワーカー共通)。

### 3.5 最終的なSkill構成

```
ue-material/
├── SKILL.md                 # トリガー、ワークフロー、MGJSONの書き方要約
├── references/
│   ├── format.md            # T3D仕様(デバッグ・未知ノード対応用)
│   ├── mgjson.md            # 中間フォーマット仕様
│   ├── nodes-index.md       # ノード逆引き(やりたいこと→クラス名)
│   └── mf/*.md              # Material Functionナレッジ
├── scripts/                 # build.py / parse.py / validate.py
└── catalog/nodes.json       # マージ済みカタログ(scripts が参照)
```

## 4. 作業分割

タスクは `tasks/` 配下に1ファイル1タスクで配置。索引と依存関係は `tasks/README.md`。

対象ノードは推測ではなく、`Engine/Source` + `Engine/Plugins` の全ヘッダを機械走査した
確定マニフェスト `catalog/manifest.json`(**359クラス**。Landscape系・Substrate系・
プラグイン系を含む。abstract/deprecated/pluginフラグ付き)に基づく。
各カタログタスクには対象クラスとヘッダパスの確定表が埋め込み済みで、全クラスが
いずれか1バッチに漏れなく割当てられている(再生成: `python tools/gen_manifest_tasks.py`)。

- **T01〜T08**: 基盤(仕様書、ツール実装、SKILL.md、実機検証)。T03/T04が本体
- **C01〜C08**: ノードカタログ優先度A(主要8カテゴリ138クラス)— **安価なAIに並列発注可**
- **C09〜C22**: 残り全クラスの優先度Bバッチ(Engine残り・Substrate・プラグイン)— 同上
- **M01〜M04**: MaterialFunction(呼び出し形式の調査+MFナレッジ3分割)
- **E01**: 実機サンプル収集(ユーザー協働)

並列性: C系・M02〜M04は `INSTRUCTIONS-catalog.md` 確定済みのため**今すぐ全部並列可**。
T03(build)はC01+C02のカタログがあれば着手可。MVPパスは
E01 → T01/T02 → T03/T04/T05 → T08(実機検証)。

## 5. リスク・未確定事項(T08実機検証で潰す)

| 項目 | 内容 | 対策 |
|---|---|---|
| ピン順序の例外 | GetInputsオーバーライドで宣言順と不一致の可能性 | カタログにnotes、実機round-trip検証 |
| プロパティピン | ShowAsInputPinピンの省略可否・順序 | 実機で確認 |
| 最小テキスト受理範囲 | Pin行の必須フィールド最小セット | 実機で削り込みテスト |
| バージョン差 | 5.0〜5.8のプロパティ差 | 手元バージョン優先、examplesをバージョン別管理 |
| MFナレッジの確度 | Contentが無くモデル知識ベース | unverifiedフラグ、実機検証で昇格 |
| Substrate | 有効環境ではノード構成が異なる | 別バッチ(低優先) |

## 6. 次のアクション

1. E01: ユーザーがエディタからサンプル数点をコピーしてファイル保存(形式の実物確認)
2. C01〜C08 / M02〜M04 を安価なAIへ並列発注
3. 本体側で T01/T02 → T03/T04/T05 を実装
4. T08 実機検証(ユーザー協働)→ カタログの verified 昇格
