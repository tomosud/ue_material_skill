# UE Material 操作 Claude Skill — 調査結果と実装計画

作成日: 2026-07-13
調査対象: `C:\work\unreal\UnrealEngine-release` (UE 5.8, branch UE5)

## 1. ゴール

Claude Skill「ue-material」を作る。できること:

1. **自然言語 → マテリアルノードテキスト生成**
   「Fresnelでリムライトを作って」→ Material Editor にそのまま Ctrl+V できるテキストを返す
2. **エディタからのコピペ解析**
   ユーザーが Material Editor でノードをコピー(Ctrl+C)して貼ったテキストを解析し、
   構造の説明・修正・ノード追加などを行い、ペースト可能なテキストで返す
3. **往復編集**: 既存グラフの一部改変(パラメータ化、ノード差し替え、接続変更)

外部ツール・プラグイン・UE起動は不要。純粋にテキスト生成/解析で完結する
(クリップボード形式が公開のT3Dテキストであるため)。

## 2. 調査結果: クリップボード形式の仕組み

### 2.1 コピー/ペーストのコードパス

| 処理 | 場所 |
|---|---|
| コピー | `FMaterialEditor::CopySelectedNodes` — MaterialEditor.cpp:6409 |
| エクスポート | `FEdGraphUtilities::ExportNodesToText` — EdGraphUtilities.cpp:458 (`UExporter::ExportToOutputDevice`、T3D形式) |
| ペースト | `FMaterialEditor::PasteNodesHereFromBuffer` — MaterialEditor.cpp:6572 |
| インポート | `FEdGraphUtilities::ImportNodesFromText` — EdGraphUtilities.cpp:484 → `FGraphObjectTextFactory` (FCustomizableTextObjectFactory::ProcessBuffer — EditorFactories.cpp:5343) |
| Pin書式 | `UEdGraphPin::ExportTextItem / ImportTextItem` — EdGraphPin.cpp:1077 / 1265 |
| ペースト後処理 | `UMaterialGraphNode_Base::PostPasteNode / ReconstructNode` — MaterialGraphNode_Base.cpp:227 / 255 |
| 接続の確定 | `UMaterialGraph::LinkMaterialExpressionsFromGraph` — MaterialGraph.cpp:496 |

コピー時は `UMaterialGraphNode::PrepareForCopying` (MaterialGraphNode.cpp:362) が
MaterialExpression を一時的にノードの子に Rename するため、
クリップボードには **GraphNode の中に Expression がネストされた形** で出る。

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
   CustomProperties Pin (PinId=<GUID32hex>,PinName="A",PinType.PinCategory="optional",LinkedTo=(MaterialGraphNode_1 <相手PinId>,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=<GUID>,PinName="B",...)
   CustomProperties Pin (PinId=<GUID>,PinName="Output",Direction="EGPD_Output",...)
End Object
```

構文ルール(ProcessBuffer / ImportObjectProperties の実装から):
- 先頭ブロックは `Class=` と `Name=` が必須。`ExportPath=` は省略可
- サブオブジェクトは「`Class=`付きブロックで宣言 → `Name=`のみのブロックでプロパティ設定」の
  2段書きがエディタ出力の形式(1段にまとめても import 側は受理する)
- プロパティは **デフォルト値との差分のみ** 記載する形式(全部書いても害はない)
- コメントノードは `Class=/Script/UnrealEd.MaterialGraphNode_Comment` +
  ネストされた `MaterialExpressionComment`

### 2.3 実装から確定した重要な事実(Skillの生成ルールに直結)

1. **接続は Pin の `LinkedTo` が正**。
   ペースト後 `UpdateMaterialAfterGraphChange` → `LinkMaterialExpressionsFromGraph` が
   Pin のリンクから Expression の入力 (`A=(Expression=...)`) を**再構築**する。
   Expression 側の入力プロパティはペースト時には冗長(入れても無害、エディタ出力には含まれる)。
2. **`LinkedTo` の書式は `<相手ノード名> <相手PinのPinId>`**
   (`UEdGraphPin::ExportText_PinReference` — EdGraphPin.cpp:2298)。
   生成時は両ノードの PinId を自分で採番して整合させる。GUIDは32桁hexで任意の値でよい。
3. **Pin の記載順が SourceIndex を決める**(`PostPasteNode` が登場順に連番を振る)。
   その後 `ReconstructNode` が Expression から Pin を再生成し、
   旧Pinを **入力は PinName → だめなら SourceIndex、出力は SourceIndex のみ** で照合して
   リンクを引き継ぐ。
   → **入力Pinは正しい PinName を付ける。出力Pinは全出力を正しい順序で列挙する**
   (TextureSample のように出力が RGB/R/G/B/A と複数あるノードで順序を間違うと誤配線になる)。
4. **PinType の中身はペースト時に捨てられ再生成される**ため最小限でよい。
   Direction はデフォルトが入力なので、出力Pinのみ `Direction="EGPD_Output"` が必要。
5. **NodeGuid / MaterialExpressionGuid / ParameterGuid はペースト時に再発行される**
   (`CreateNewGuid`, `UpdateMaterialExpressionGuid`)。ユニークでありさえすればよい。
6. **プロパティ入力ピン**: `ShowAsInputPin` メタデータ付き UPROPERTY(Constant の Value 等)も
   入力ピンとして FExpressionInput の後に並び、SourceIndex に数えられる
   (MaterialGraphNode.cpp:722)。カタログにはこれも含める必要がある。
7. **アセット参照はパス文字列**:
   `Texture=/Script/Engine.Texture2D'"/Engine/EngineResources/DefaultTexture.DefaultTexture"'`。
   存在しないパスは None になるだけでペースト自体は成功する。
8. ペーストできるのは選択ノード相当のみ。**最終出力ノード(Root)は貼れない**ので、
   BaseColor 等への接続は「ユーザーが手で1本つなぐ」案内をする
   (Root入力の接続はテキストで表現できない)。
9. `Material=` / `Function=` プロパティはペースト側で上書きされるため省略してよい。
10. マテリアル関数(MaterialFunctionCall)、Named Reroute、Composite(折りたたみ)にも
    ペースト後の特殊処理があり動作する (MaterialEditor.cpp:6478 `PostPasteMaterialExpression`)。

### 2.4 ノードの種類

- `MaterialExpression*.h` は **275クラス** (`Engine/Source/Runtime/Engine/Public/Materials/`)
- 入力ピン: 各クラスの `FExpressionInput` 型 UPROPERTY(宣言順)+ ShowAsInputPin プロパティ
- 出力ピン: 既定は1本 (`Output`)。コンストラクタで `Outputs` を上書きするクラスあり
  (TextureSample: RGB,R,G,B,A / Panner等)
- 入力名: 既定はプロパティ名。`GetInputName` オーバーライドで変わるクラスあり

→ ヘッダの機械抽出でカタログの大半を作れるが、
   **正解はエディタからの実コピペサンプル**なので、主要ノードは実サンプルで検証する。

## 3. Skill 設計

```
ue-material/
├── SKILL.md                 # 本体: トリガー条件、ワークフロー、生成ルールの要約
├── references/
│   ├── format.md            # T3D形式の完全仕様(2.2/2.3の内容+実サンプル)
│   ├── nodes-core.md        # 主要ノード詳細カタログ(実機検証済み: ピン名/順序/プロパティ/実例)
│   ├── nodes-all.md         # 275クラスの自動生成インデックス(クラス名/入出力/主プロパティ)
│   └── examples/            # 実エディタからコピーした完全サンプル(パターン別)
│       ├── basic-math.txt
│       ├── texture-uv.txt
│       ├── parameters.txt
│       └── comment-reroute.txt
└── scripts/
    ├── validate.py          # 生成テキストの検証(下記)
    └── parse.py             # コピペテキスト → 構造JSON(ノード/接続/プロパティの要約)
```

### SKILL.md のワークフロー

1. **生成**(自然言語→テキスト):
   references のカタログからノードを選定 → 接続グラフを設計 →
   NodePosX/Y を左→右のデータフローで自動レイアウト(列間 ~300px、行間 ~150-200px)→
   テキスト生成 → `validate.py` で自己検証 → コードブロックで出力し
   「全選択→コピー→Material Editor 上で Ctrl+V」の手順と Root への手動接続を案内
2. **解析**(コピペ→理解): `parse.py` で構造化 → 日本語で構造を説明
3. **改変**: 解析結果に対して編集 → 再生成(既存の PinId/名前をなるべく保持)
4. **未知ノード対応**: カタログにないノードは、ユーザーに
   「そのノードを1個エディタでコピーして貼ってください」と依頼して形式を学習(往復プロトコル)

### validate.py のチェック項目

- Begin/End の対応、Class=/Name= 必須項目
- ノード名・Expression名の一意性
- `MaterialExpression=` 参照がネスト内オブジェクトと一致
- PinId の一意性、`LinkedTo` の相互参照整合(相手ノード名+PinIdが実在、双方向)
- 出力Pinの `Direction="EGPD_Output"` 有無
- カタログ照合: ピン名/順序が既知ノード定義と一致するか
- GUID形式(32桁hex)

## 4. 実装フェーズ

### Phase 1 — MVP(まずここまで)
1. `format.md` 作成(本調査結果を仕様化)
2. コアノード ~30種の手動カタログ + 生成テンプレート
   - Constant / Constant2Vector / Constant3Vector / Constant4Vector
   - ScalarParameter / VectorParameter / StaticSwitchParameter
   - Add / Subtract / Multiply / Divide / LinearInterpolate / Clamp / Power / OneMinus
   - TextureSample / TextureSampleParameter2D / TextureCoordinate / Panner / Rotator
   - Fresnel / DotProduct / CrossProduct / Normalize / ComponentMask / AppendVector
   - Time / VertexColor / WorldPosition / PixelNormalWS / Desaturation / Saturate
   - Comment / NamedRerouteDeclaration / NamedRerouteUsage
3. `validate.py` / `parse.py` 実装
4. SKILL.md 作成
5. **実機検証**: 生成テキストを実際の Material Editor に貼って動作確認
   (単ノード → 複数ノード接続 → パラメータ → テクスチャ → コメント、の順)

### Phase 2 — カタログ自動生成
- UEソースのヘッダ275本をパースするスクリプト
  (`FExpressionInput` 宣言順、`GetInputName`/`Outputs` オーバーライド、
  ShowAsInputPin メタデータ、UPROPERTY既定値を抽出)→ `nodes-all.md` 生成
- 出力ピン定義はヘッダだけでは不明なクラスがあるため cpp のコンストラクタも参照

### Phase 3 — 応用
- Material Function 呼び出し(FunctionCall)対応
- 既存グラフの大規模リファクタ(パラメータ一括化など)
- レイアウト品質向上(重なり回避、コメント枠での グルーピング)
- UEバージョン差の吸収(5.x系はこの形式でほぼ安定。必要ならバージョン指定オプション)

## 5. リスク・未確定事項(Phase 1 実機検証で潰す)

| 項目 | 内容 | 対策 |
|---|---|---|
| ピン順序の例外 | GetInputs をオーバーライドするクラスで宣言順と一致しない可能性 | コアノードは実コピペで検証 |
| プロパティピンの扱い | ShowAsInputPin ピンの省略可否・順序 | 実機で省略時挙動を確認 |
| 最小テキストの受理範囲 | Pin行の必須フィールド最小セット | 実機で削り込みテスト |
| バージョン差 | 5.0〜5.8 での ExportPath / プロパティ差 | まず手元バージョンで固定、examples をバージョン別に |
| Substrate | Substrate 有効環境ではノード構成が異なる | Phase 3 以降 |

## 6. 次のアクション

1. この計画の承認
2. Phase 1 開始。最初の成果物は「Constant3Vector 1個」を貼れるテキスト → 実機確認
3. ユーザー側でエディタからのコピペサンプル提供(数パターン)があると
   examples/ の整備が早い
