# Phase D ソース監査バッチ発注文書

この文書は、Unreal Engine の Material Expression を Phase D で量産監査するワーカー向けの
共通発注仕様である。発注者は冒頭のバッチ固有欄だけを埋め、本文を省略せずワーカーへ渡す。
ワーカーは追加の暗黙知、過去の会話、モデル知識を前提にしてはならない。

## 1. バッチ固有欄（発注者が必ず記入）

- リポジトリルート: `<REPOSITORY_ROOT>`
- バッチ ID: `<BATCH_ID>`（英数字とハイフン。例: `D01-common-math`）
- 対象クラス: `<12〜18 個の短いカタログ名を重複なく列挙>`
- UE ソースルート: 環境変数 `UE_SOURCE_ROOT`
- 編集を許可するファイル:
  `dev/catalog/audits/<BATCH_ID>.json` の新規作成または、そのバッチの差し戻し時に限る同ファイルの修正
- 参照基準: 発注時の `dev/catalog/manifest.json`、`dev/catalog/generated/C*.json`、
  `skills/ue-material/catalog/node-evidence.json`

バッチ ID、対象クラス、`UE_SOURCE_ROOT` のいずれかが未指定、対象が 12 未満または 18 超、
対象クラスが manifest に存在しない、または別の audit fragment と重複する場合は作業を開始せず、
発注者へ差し戻す。対象の追加・入れ替えをワーカー判断で行ってはならない。

## 2. 目的と成果物

目的は、指定された各クラスの宣言、実効 Pin/Property スキーマ、動作、制約を参照 UE ソースで
監査し、構造化 `semantics` とフィールド単位の根拠を記録することである。監査済み description は
自由英作文ではなく `semantics` から決定論的に生成される。

ワーカーが手編集して提出する成果物は、次の 1 ファイルだけである。

```text
dev/catalog/audits/<BATCH_ID>.json
```

次は禁止する。

- `skills/ue-material/**` の直接編集
- `dev/catalog/generated/**`、manifest、既存の別バッチ audit、テスト、ツール、文書の編集
- legacy prose の翻訳、復元、またはソース根拠としての利用
- UE ソースチェックアウト内の作成・編集・整形・削除・ビルド生成物の書き込み
- 対象外クラスの「ついで」の修正

配布カタログへの反映は発注者が `gen_node_evidence.py` と `catalog_merge.py` を通して行う。
ジェネレーター実行で `skills/ue-material/**` に生じる派生差分を、ワーカーの手編集成果物として
扱ってはならない。

## 3. ソース環境と不変の証拠規則

作業はリポジトリルートから行う。UE 5.8.0 / branch `UE5` の参照チェックアウトを想定するが、
実際の場所は固定パスではなく `UE_SOURCE_ROOT` から読む。

```powershell
if (-not $env:UE_SOURCE_ROOT) { throw 'UE_SOURCE_ROOT is required' }
if (-not (Test-Path -LiteralPath $env:UE_SOURCE_ROOT -PathType Container)) {
    throw "UE_SOURCE_ROOT does not exist: $env:UE_SOURCE_ROOT"
}
Get-Content -Raw -Encoding UTF8 (Join-Path $env:UE_SOURCE_ROOT 'Engine/Build/Build.version')
```

`UE_SOURCE_ROOT` は常に読み取り専用として扱う。参照、検索、ハッシュ計算以外を行わない。
ソースで証明できない事実は書かず、空欄や一般論で埋めず、推測しない。クラス名、慣例、既存の
和文説明、別バージョンの知識から動作を推定してはならない。未決着の論点は `unresolved` に
安定 ID として記録する。ソースで符号化済みの主張をすべて証明できる次元は `verified` とし、
証明が不足する次元は `pending` のまま差し戻す。根拠がない次元を `verified` に昇格してはならない。

ソース監査が証明するのは指定チェックアウトの事実だけであり、Editor 貼り付け成功、シェーダー
コンパイル成功、他の UE バージョンとの互換性まで意味しない。ソースだけで確定できない Editor
表示名、動的再構築、asset 内容などは `unresolved` と成果報告に残し、必要な Editor fixture を
明記する。

## 4. バッチの選定と難度

1 バッチは必ず 12〜18 クラスとし、レビュー可能な同系統の単位にまとめる。優先順は次の通り。

1. 数学、定数、パラメータ、テクスチャ、座標、ベクトルの頻出ノード
2. その他の通常 Engine ノード
3. 動的 Pin または特殊グラフノード（Named Reroute、Composite、Function Call、状態依存 Pin）
4. Substrate ノード
5. プラグインノード（対応するプラグインソースが `UE_SOURCE_ROOT` に存在する場合だけ）

3 は静的 Pin 表だけでは監査できないため、上級ワーカーまたはメイン AI にだけ発注する。状態、
プロパティ、接続、再構築イベントにより Pin が変わる場合は、その状態遷移と Pin 再生成処理を
監査する。4 と 5 は通常 Engine ノードと混在させない。プラグインソースが存在しなければ監査を
成立させようとせず、対象を `unresolved` として差し戻す。

## 5. audit fragment の JSON 契約

トップレベルは、短いカタログ名をキーとする JSON object である。キーは指定対象と完全一致させ、
全対象を辞書順に並べる。UTF-8、LF、末尾改行あり、JSON として決定論的に整形する。

各レコードは `audit`、`semantics`、`references` を持つ。実例:

```json
{
  "Divide": {
    "audit": {
      "declaration": "verified",
      "schema": "verified",
      "description": "verified",
      "restrictions": "not_applicable"
    },
    "semantics": {
      "operation": "componentwise_binary",
      "formula": "A / B",
      "unconnected_defaults": {
        "A": "ConstA",
        "B": "ConstB"
      },
      "value_domain": "numeric_scalar_or_vector",
      "restrictions": [],
      "unresolved": []
    },
    "references": [
      {
        "path": "Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionDivide.h",
        "symbol": "UMaterialExpressionDivide",
        "claims": ["declaration", "schema"],
        "source_hash": "eb19c4aadef79ebd5423e6261ce7ca4a6c159285f484729fda49203a2e1c05d3"
      },
      {
        "path": "Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp",
        "symbol": "UMaterialExpressionDivide::Compile",
        "claims": ["schema", "description"],
        "source_hash": "9930f4df181e6fec9dc720d2f2968cfaa377c93fc2d7045a950ae08cf7a59371"
      },
      {
        "path": "Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressionsToMIR.cpp",
        "symbol": "UMaterialExpressionDivide::Build / BuildBinaryOperatorWithDefaults",
        "claims": ["description"],
        "source_hash": "a40f549263684674f2b154ffdf2b4bf336527786ca7ed983cb4507987ba9d2e8"
      }
    ]
  }
}
```

これは形の例であり、ハッシュや facts を別クラスへ複製してはならない。実際の値は指定された
`UE_SOURCE_ROOT` を読んで作る。

### 5.1 `audit`

必須次元は `declaration`、`schema`、`description`、`restrictions`。現行ツールで許可される値は
`pending`、`verified`、`stale`、`not_applicable` である。

- `verified`: その次元の全主張を references が証明する。
- `pending`: 未監査。完成バッチでは原則残さず、残る場合は差し戻し理由を報告する。
- `stale`: 以前の根拠の `source_hash` が現在のソースと不一致。新規監査で意図的に設定しない。
- `not_applicable`: 制約など、その次元に該当する事実がないことを実装全体の確認で判断した場合。

`legacy_unverified` は旧プロースの provenance 状態であり、現行 audit fragment の許可値ではない。
`verified` の各次元には、同名 claim を持つ reference が最低 1 件必要である。未証明の次元を
`verified` に見せかけたり、`not_applicable` で未調査を隠したりしてはならない。`unresolved` は
audit 状態とは独立して警告されるため、既知の証明範囲を曖昧な中間状態で表現しない。

### 5.2 `semantics`

キーは次の 6 個で固定し、追加・欠落を禁止する。

| キー | 契約 |
|---|---|
| `operation` | 下記の閉じた列挙から 1 個 |
| `formula` | canonical ASCII 式。`custom_code` だけ `null` |
| `unconnected_defaults` | 入力表示名から Property 名または `$built_in_token` への object |
| `value_domain` | 下記の閉じた列挙から 1 個 |
| `restrictions` | 構造化 restriction object の配列 |
| `unresolved` | 一意な dotted snake_case ID の配列 |

許可される `operation`:

```text
constant, componentwise_binary, componentwise_unary, linear_interpolate,
clamp, power, texture_sample, texture_coordinate, parameter, component_mask,
append_vector, dot_product, cross_product, normalize, distance, desaturation,
static_bool, static_switch, texture_object, coordinate_panner, coordinate_rotator,
bump_offset, texture_property, fresnel, time,
vector_transform, position_transform, view_property, position_property,
axis_rotation, derive_normal_z, sphere_mask, conditional, smoothstep, length,
scene_value, custom_code
```

許可される `value_domain`:

```text
float1, float2, float3, float4, numeric_scalar_or_vector,
double3, boolean, texture_sample_value, texture_object, user_defined,
branch_promoted_value, position_float3_or_double3
```

現在の閉じた語彙で正確に表現できないノードに、新しい operation/domain を独断で追加しない。
その場合はスキーマ拡張候補と根拠を報告し、バッチを `unresolved` として発注者へ返す。

`formula` は ASCII 1 行で、識別子、非負数、関数呼び出し、丸括弧、`,`、`+ - * /` のみを使う。
`semantics_schema.canonical_formula()` が返す空白・括弧表記と完全一致させる。式は説明用の近似ではなく、
`Compile` / `Build` またはクラス固有実装が証明する動作だけを表す。

`unconnected_defaults` のキーは merged catalog の実効 input `name` と一致させる。値が `$` で
始まらない場合、同じ catalog record の `props` に存在し、input の `default_prop` と一致する
必要がある。未接続既定値が存在しない入力は object に入れない。

`restrictions` の各要素は `kind`（snake_case）を必須とする構造化 object である。他の値は JSON
scalar または空でない文字列の配列だけを許す。`description`、`details`、`message`、`note`、
`notes`、`prose`、`text` のような自由文フィールドは禁止する。`input` / `pin` / `property` および
それらで終わるフィールドは、実在する input/property 名を正確に参照する。

`unresolved` は `category.specific_issue` 形式の安定した dotted snake_case ID とする。例:

```json
"unresolved": ["legacy_mir.period_zero_behavior_equivalence"]
```

単なる `unknown`、文章、空文字、同一 ID の重複は禁止する。未解決の範囲は成果報告で各 ID ごとに
説明し、何を追加確認すれば解決できるかを示す。

description を audit JSON に書かない。`catalog_merge.py` が `semantics` と input 順から英文を
生成する。テンプレートで表現不能な事実を自由な notes に逃がさず、構造化 restriction、
`unresolved`、またはスキーマ拡張の差し戻しとして扱う。

### 5.3 `references` と `source_hash`

各 reference は次を満たす。

- `path`: `UE_SOURCE_ROOT` からの `/` 区切り相対パス。絶対パス、`..`、ローカル固有パスは禁止。
- `symbol`: 実ファイル内で確認した正確な型・関数・enum・helper 名。複数なら ` / ` で区切る。
- `claims`: `declaration`、`schema`、`description`、`restrictions` のうち、その symbol が実際に
  証明する次元だけ。
- `source_hash`: 参照ファイル全体を CRLF と CR から LF へ正規化した後の SHA-256。小文字 64 桁。

同じファイルに複数 symbol があれば 1 reference にまとめてもよいが、各 symbol の leaf 名が
ファイル内に存在し、各 claim との対応を人手で確認する。単なるファイル実在や文字列ヒットは
動作の証明ではない。派生クラスが基底実装を継承する場合は、派生宣言と、実効挙動を供給する基底の
宣言・実装を両方参照する。

`source_hash` は Windows の生バイトハッシュではなく正規化ハッシュである。既存ツールと同じ
定義を使う。対象クラスの下書き抽出では次のコマンドが source path と正規化ハッシュを出力する。

```powershell
uv run --offline --no-project python -B dev/tools/extract_expression_facts.py `
  --class <CLASS_1> --class <CLASS_2>
```

抽出結果は下書きにすぎない。`semantic_draft.operation` と `formula` が `null` であることが示す通り、
機械抽出を監査の代用にしない。追加の実装ファイルも直接読み、そのファイルの正規化ハッシュを
記録する。`qa_semantics.py` が最終的に現在のソースとの一致を検証する。

## 6. クラスごとの監査手順

各対象を次の順で監査する。途中の不一致を後工程の文章で覆い隠してはならない。

1. manifest から正確な module、runtime class path、header、基底クラス、plugin ownership、
   abstract 状態、deprecation を解決する。
2. header の宣言と、`GetInputs`、`GetInputName`、`GetInputType`、その他の override を追い、通常 input
   の実効表示名、順序、必須性を解決する。
3. metadata と Pin 生成処理を追い、Property Pin、型、表示名、実効順序を解決する。
4. constructor、継承既定、dynamic rebuild、output-name logic を追い、output の名前、順序、mask、
   状態依存性を解決する。
5. serialized property の型、enum domain、in-class initializer、constructor default、version migration
   を解決し、既存 generated schema と突き合わせる。
6. `Compile`、`Build`、MIR/HLSL helper、またはクラス固有実装を読み、数式、値域、未接続時挙動を
   解決する。legacy と MIR の差も確認する。
7. validation、compile guard、Editor restriction、material domain / shader stage 制約、特殊 graph-node
   挙動を解決する。
8. 証明済みの事実だけを閉じた `semantics` に符号化する。自由な英文 description は書かない。
9. 各 audit 次元を証明する source-relative path、正確な symbol、claims、`source_hash` を記録する。
10. schema、merged Pin/Property、reference、hash、生成 description を QA し、利用可能な fixture が
    あれば追加変更せず照合する。その後でのみ audit 状態を確定する。

既存 generated schema に誤りがある場合、誤ったまま `schema: verified` にしてはならない。しかし
この発注の許可スコープを越えて generated fragment を修正してもならない。差異、ソース根拠、必要な
修正を成果報告に列挙し、そのクラスを発注者へ差し戻す。発注者が schema 修正を別レビュー単位で
反映した後、同じ audit を再 QA する。

## 7. QA 手順

### 7.1 ワーカーの事前確認

```powershell
git status --short
uv run --offline --no-project python -B dev/tools/extract_expression_facts.py `
  --class <CLASS_1> --class <CLASS_2>
```

抽出コマンドにはバッチの全クラスを `--class` で列挙する。標準出力を一時下書きとして使ってよいが、
リポジトリに下書きファイルを追加しない。作業前の無関係な変更はユーザー所有として保持する。

### 7.2 isolated semantics QA

`qa_semantics.py` は merged catalog と evidence を検証するため、発注者は audit fragment を一時的な
evidence/catalog へ反映して QA する。これにより、ワーカー成果物を audit JSON だけに保てる。
以下の `<TEMP_DIR>` はリポジトリ外の一時ディレクトリに置く。

```powershell
uv run --offline --no-project python -B dev/tools/gen_node_evidence.py `
  --audits-dir dev/catalog/audits `
  --output <TEMP_DIR>/node-evidence.json

uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet `
  --evidence <TEMP_DIR>/node-evidence.json `
  --output <TEMP_DIR>/nodes.json `
  --functions-output <TEMP_DIR>/functions.json `
  --meta-output <TEMP_DIR>/meta.json `
  --index <TEMP_DIR>/nodes-index.md

uv run --offline --no-project python -B dev/tools/qa_semantics.py `
  --catalog <TEMP_DIR>/nodes.json `
  --evidence <TEMP_DIR>/node-evidence.json `
  --extract-current `
  --class <CLASS_1> --class <CLASS_2>
```

ここでも全クラスを列挙する。合格条件は `semantic QA passed` と exit code 0。QA は次を検証する。

- 閉じた semantics schema と canonical formula
- unconnected default と merged input/property/default_prop の一致
- 現行 UE ソースから機械抽出した input/property、明示的 RequiredInput、静的 output 名との一致
- restriction が参照する input/property の実在
- `semantics` から生成した description の完全一致
- source-relative path の root 内への封じ込め、ファイル実在、symbol leaf の実在
- LF 正規化 SHA-256 の一致
- catalog class/header と manifest の一致

QA の文字列検出だけを根拠にしてはならない。ワーカー自身が各 symbol の定義・呼び出し範囲を読んで
claim を確認し、発注者は受け入れ時にバッチ内から無作為に 3 クラス以上を抜き取って再照合する。
虚偽または無関係な引用が 1 件でもあればバッチ全体を差し戻す。

### 7.3 標準ゲートと決定論性（発注者の受け入れ）

発注者が audit を通常経路へ反映した後、次をすべて実行する。

```powershell
uv run --offline --no-project python -B dev/tools/gen_node_evidence.py
uv run --offline --no-project python -B dev/tools/qa_semantics.py `
  --extract-current `
  --class <CLASS_1> --class <CLASS_2>
uv run --offline --no-project python -B -m unittest discover -s dev/tests -v
uv run --offline --no-project python -B dev/tools/check_english.py
uv run --offline --no-project python -B dev/tools/check_distribution.py
uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
git diff --check
```

続けて `catalog_merge.py --quiet` をもう一度実行し、2 回目に差分が増えないことを `git diff` で
確認する。1 回目の生成差分は audit に対応する対象クラスだけでなければならない。無関係な class、
function、index 項目が変わった場合は受け入れない。

発注者はさらに次を確認する。

1. バッチ内 3 クラス以上の無作為抜き取り source/symbol 照合
2. `unresolved` が具体的で、動的挙動や backend 差を一般文で隠していないこと
3. `verified` の schema/description claim coverage
4. 合成英文 description だけが説明表示経路に入り、和文 legacy prose が復活していないこと
5. alias 抽出が済んだ対象だけを、別の管理変更で legacy prose の表示経路から退役させること

legacy prose の削除や quarantine 移動はこのワーカーバッチの許可スコープ外であり、発注者が別途行う。

## 8. 完了条件と差し戻し条件

バッチは次をすべて満たした場合だけ完了とする。

- 指定された 12〜18 クラスだけが audit fragment にあり、全クラスが欠落なく監査されている。
- 各クラスの declaration、実効 schema、description semantics、restrictions を手順どおり調査した。
- `verified` claim はすべて source path + symbol + current normalized `source_hash` で覆われる。
- 未決着事項は安定した `unresolved` ID で明示され、符号化した主張には推測がない。該当次元を
  `verified` にするのは、その符号化済み主張を references がすべて証明する場合だけである。
- isolated QA が通り、許可外ファイルを手編集していない。
- 発注者の抜き取り照合、標準ゲート、決定論確認が通る。

次のいずれかがあれば、完了扱いにせず差し戻す。

- 閉じた semantics 語彙では正確に表せず、スキーマ拡張が必要
- generated schema とソースが不一致で、許可スコープ内では修正不能
- dynamic/inherited behavior の実効経路を追えない
- plugin source、asset content、Editor evidence など必要な証拠がない
- legacy と MIR の差、domain/stage restriction、version migration が未確認
- source hash 不一致、symbol 不在、対象重複、対象外差分

## 9. 成果報告形式

ワーカーは JSON とともに、次の形式で簡潔に報告する。成功していないゲートを「通過」と書かない。

```text
バッチ: <BATCH_ID>
対象: <CLASS_1>, <CLASS_2>, ...（合計 N）

変更ファイル:
- dev/catalog/audits/<BATCH_ID>.json

監査結果:
- verified: <class と verified 次元の要約>
- unresolved: <class、該当次元、unresolved ID>
- not_applicable: <class と次元>
- 差し戻し: <class、理由、必要な次の証拠または schema 修正>

主要根拠:
- <class>: <source-relative path> :: <symbol> -> <claims>

QA:
- extract draft review: pass/fail/not run
- isolated gen_node_evidence: pass/fail/not run
- isolated catalog_merge: pass/fail/not run
- qa_semantics: pass/fail/not run
- git diff --check: pass/fail/not run

未解決事項:
- <unresolved ID>: <未確定の範囲と、解決に必要な source/Editor evidence>
- なし（空の場合）

許可外変更:
- なし
```

標準ゲート、無作為抜き取り、通常経路への生成反映は発注者の受け入れ報告に追記する。未実行項目は
必ず `not run` とし、推測で補完しない。
