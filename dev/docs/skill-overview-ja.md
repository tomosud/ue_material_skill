# ue-material スキル 現状実装まとめとアップデート耐性リファクタリング方針

作成日: 2026-07-17(同日更新: 設計議論の結論を §6〜§8 に反映)
対象コミット: `65c3891`(ブランチ `refact_01`)
現行ベースライン: Unreal Engine 5.8.0 / branch `UE5` / fingerprint `5.8.0|UE5`
関連文書: `dev/docs/improvement-plan.md`(Phase A–G 実行計画)、`dev/docs/source-update.md`(現行の更新手順)、
`dev/docs/refactoring-plan.md`(完了済み Phase 0–8 の記録)

この文書は、スキルを引き継ぐ人・ワーカー AI に「このスキルが何を・どうやって行うか」を最短で
理解してもらうための概観と、今後のリファクタリング方針(複数 UE バージョン対応・ノード情報の
機械的抽出)をまとめたものである。詳細な実行手順は関連文書側にある。

---

## 1. このスキルは何をするものか

**Unreal Engine の Material Editor のノードグラフを、AI との会話で作成・解析・改変できるようにする
スキル**である。仕組みの核は次の 1 行に集約される:

> AI は **MGJSON**(コンパクトな独自 JSON 形式)だけを読み書きし、Unreal との受け渡しは
> 同梱 Python スクリプトが **クリップボード T3D**(Unreal のコピー&ペースト形式)との相互変換で行う。

ユーザーから見た代表的な使い方は 3 つ:

1. **生成**: 「金属マテリアルのノードを組んで」→ AI が MGJSON を書き、`validate.py` で検証後
   `build.py --to-clipboard` で T3D をクリップボードへ。ユーザーは Material Editor に Ctrl+V で貼るだけ。
2. **解析**: ユーザーが Editor でノードをコピー →`parse.py --from-clipboard` が T3D を MGJSON に
   変換 → AI が構成と接続を説明する。
3. **改変**: 解析で得た MGJSON を編集 → 検証 → ビルドして貼り戻す。

意図的に「やらないこと」も仕様である:

- **Material Root ノードは生成も接続もしない**(ペースト後にユーザーが手動接続する)。
- T3D・GUID・Pin レコードを AI が手書きしない。会話に T3D 全文を貼らない。
- Material Function の内部グラフは作らない(呼び出しノードのみ、実証済みの Pin スキーマが条件)。
- ソースで裏を取れない事実を推測で埋めない(後述の provenance 管理)。

## 2. 配布物の構成(skills/ue-material/)

配布物は自己完結しており、`dev/` にも絶対パスにも依存しない。Python は標準ライブラリのみ
(クリップボード操作のみ PowerShell を利用)。

```
skills/ue-material/
├── SKILL.md                     # AI 向けワークフロー規則(絶対規則・手順・境界)
├── scripts/
│   ├── parse.py                 # T3D → MGJSON(クリップボード/ファイル入力)
│   ├── validate.py              # MGJSON のスキーマ・リンク・Custom ノード検証
│   ├── build.py                 # MGJSON → T3D(クリップボード/ファイル出力)
│   ├── search_catalog.py        # カタログ横断検索(クラス・Pin・プロパティ・legacy 語句)
│   └── source_fingerprint.py    # 解決した UE ソースとカタログ基準線の一致確認
├── catalog/
│   ├── nodes.json               # ノードカタログ 359 クラス(スキーマ本体)
│   ├── functions.json           # Material Function カタログ 82 件
│   ├── node-evidence.json       # ソース根拠と監査状態(provenance)+ 基準 fingerprint
│   ├── editor-evidence.json     # Editor 実証の記録
│   └── legacy-node-prose.json   # 旧和文プロース(検索用資産。説明文としては退役予定)
└── references/                  # AI が必要時に読む詳細仕様
    ├── mgjson.md                # MGJSON 形式仕様
    ├── format.md                # T3D インポータ詳細(パーサ/カタログ拡張時のみ)
    ├── custom-expressions.md    # Custom ノード(HLSL)の制約
    ├── mf-call.md               # Material Function 呼び出しの条件
    ├── nodes-index.md           # 全カタログへのコンパクトな索引
    └── source-verification.md   # UE ソースルート解決と検証の手順
```

### 実行時のワークフロー(SKILL.md が AI に課す手順)

```
[Preflight] source_fingerprint.py で UE ソースルートを確認
    │  COMPATIBLE → 続行 / 不一致・未解決 → 作業前にユーザーへ確認(ゲート)
    ▼
[発見]  search_catalog.py <語句> でノード候補と provenance を取得
    │  必要ならソース参照(path + symbol)を解決済みルートで実地確認
    ▼
[記述]  MGJSON を .json ファイルに書く(会話上の表現は MGJSON のみ)
    ▼
[検証]  validate.py graph.json   ← エラーが残る限りビルド禁止
    ▼
[出力]  build.py graph.json --to-clipboard(または -o file.t3d)
    ▼
[案内]  「空きエリアに Ctrl+V」+ Root へ手動接続すべき最終出力を明示
```

ソースルートの解決順は `.ue-material/settings.json`(`ueSourceRoot`)→ 環境変数
`UE_SOURCE_ROOT` → ユーザー指定フォルダの限定スキャン。ドライブ全体の走査はしない。

### MGJSON の最小知識

```json
{
  "nodes": {
    "tex":  {"class": "TextureSample", "props": {"Texture": "/Game/T_Base.T_Base"}},
    "mul":  {"class": "Multiply"}
  },
  "links": ["tex.RGB -> mul.A"],
  "pos":   {"tex": [0, 0], "mul": [300, 0]}
}
```

- ノード ID はローカルなラベル(Unreal のオブジェクト名ではない)。
- リンクは `source[.output] -> destination.input`。出力省略時は index 0。入力は 1 本まで、出力はファンアウト可。
- `props` は型付きプロパティ、`raw_props` は T3D 右辺文字列をそのまま持つ最終手段。

## 3. データの三層構造と provenance

このスキルの信頼性の根幹は「**事実には必ずソース根拠を付け、根拠の状態(provenance)を
データとして持ち歩く**」ことにある。データは三層に分かれる。

| 層 | 場所 | 内容 | 生成方法 |
|---|---|---|---|
| ①宣言マニフェスト | `dev/catalog/manifest.json` | UE ソースを ripgrep 走査して得た全 `UMaterialExpression*` クラスの宣言(header パス・基底クラス) | **機械的**(`gen_manifest.py`) |
| ②生成フラグメント + 監査 | `dev/catalog/generated/C01–C22.json`, `M02–M04-mf.json` / `dev/catalog/audits/` | 各クラスの inputs / outputs / props / 説明などのスキーマ断片と、人手・AI によるソース監査の上書き | **半手動**(ワーカー AI バッチがソースを読んで抽出、その後 C++ コンストラクタと突合修正) |
| ③配布カタログ | `skills/ue-material/catalog/*.json` | ①②を `catalog_merge.py` がマージ・リントした成果物 | **機械的**(マージのみ) |

`node-evidence.json` は各クラスに 4 軸の監査状態
(`declaration` / `schema` / `description` / `restrictions`、値は `verified` / `pending` /
`partial` / `not_applicable`)と、`{path, symbol, claims}` 形式のソース参照リストを持つ。
現状は **359 クラス中、declaration はほぼ全件 verified、schema/description は大半が pending**
(監査済みは少数)。つまり「宣言の存在」は機械的に証明済みだが、「Pin 構成と説明」の多くは
ワーカー AI 抽出のままで、ソース監査による昇格待ちである。

さらに `node-evidence.json` の `source` ブロックに基準線
(`version: 5.8.0`, `branch: UE5`, `git_commit`, `fingerprint: "5.8.0|UE5"`)が刻まれており、
実行時に `source_fingerprint.py` がユーザー環境のチェックアウトの
`Engine/Build/Build.version` と照合する。branch 名は `++UE5+Release-5.8` → `UE5` のように
正規化するため、GitHub ソース版とランチャー版の同一リリースを同一視できる。

## 4. 現行の更新パイプライン(source-update.md の要約)

UE ソースが更新されたときの手順は既に文書化・部分自動化されている:

```
1. gen_manifest.py        … チェックアウトを走査して manifest.json を再生成(機械的)
2. gen_node_evidence.py   … 宣言証拠を更新 + Build.version から基準 fingerprint を刻印(機械的)
                            ※ schema/description は昇格しない。宣言の存在証明のみ
3. catalog_merge.py       … フラグメントを配布カタログへマージ、nodes-index.md 再生成(機械的)
4. 差分レビュー           … 変更クラスごとに宣言・コンストラクタ・Pin・Compile を実地確認(手動)
5. オフラインゲート       … unittest(32件)+ check_english.py + check_distribution.py(機械的)
```

新しく判明した事実は、ローカルメモではなく `dev/catalog/audits/`(bounded override)と
`dev/catalog/generated/`(スキーマ断片)に記録して再生成する。これにより検証済み事実が
fingerprint 付きで配布物に乗る。

## 5. 現状の課題(リファクタリングの動機)

1. **スキーマ抽出が半手動**: ②層(inputs/outputs/props)の初期抽出はワーカー AI が
   ヘッダと .cpp コンストラクタを読んで書いたもの。実際に出力 Pin の取り違えが発生し、
   コンストラクタ突合で 10 クラスをパッチした経緯がある。UE 更新のたびに同じ人海戦術は
   再現性・コスト両面で持たない。
2. **単一バージョン前提**: カタログは `5.8.0|UE5` の 1 基準線のみ。fingerprint 不一致は
   検出できるが、「では 5.7 / 5.9 ではどうか」に答えるデータを持てない。
3. **差分の分類手段がない**: manifest にソースファイルのハッシュが無く、UE 更新時に
   「どのクラスの何が変わったから、どこだけ再監査すればよいか」を機械的に絞れない
   (improvement-plan.md Phase A-2/A-3 が未着手)。
4. **監査バックログ**: schema/description が pending のまま多数残っており、実行時の
   「毎回ソースを読め」規則で補っている。抽出の機械化はこのバックログ解消の前提でもある。

## 6. 方針 1: 複数 UE バージョン対応・アップデート耐性

### 6-0. 設計思想: 一次情報はソース、DB は効率化のための導出キャッシュ

検証の結果、時間とトークンを惜しまなければカタログ DB なしでも大半の問いはソース直読で
答えられることが確認できた(参照範囲は Materials 系に閉じており約 3MB。「なぜ」の問いも
翻訳層 + 数ファイルの狙い読みで解決する)。したがって DB の存在理由は**効率化**に一本化する:

- **一次情報(真実)は UE ソース**。カタログはそこから**機械的に導出されたキャッシュ**であり、
  手保守のデータベースではない。
- 導出キャッシュである以上、「(UE バージョン, ソースハッシュ)に対する再現可能なビルド成果物」
  でなければならない。同じソースからは同じカタログが出る(決定論)。
- **例外 = ソースから導出できない一次情報**は次の 3 つだけで、これらは現行機構をそのまま残す:
  1. 監査結果(`dev/catalog/audits/` の bounded override)
  2. Editor 実証(`editor-evidence.json`、クリップボード実測・コンパイル実証)
  3. 検索 alias(和文クエリ対応など、ソースに存在しない索引情報)

improvement-plan.md の Phase A / F と整合する。

### 6-1. バージョンをデータに刻む(Phase A 相当・一部実装済み)

- fingerprint(`5.8.0|UE5`)刻印と実行時照合は**実装済み**(`gen_node_evidence.py` +
  `source_fingerprint.py`)。
- 未実装: `meta.json`(skill_version / ue_version / 各カタログの SHA-256)、
  manifest への**クラス別ソースファイルハッシュ**記録、`catalog_diff.py`(新旧 manifest の
  差分を added / removed / hash_changed / unchanged に分類)。
- ハッシュがあれば、UE 更新時の再監査対象を「変わったクラスだけ」に機械的に絞れる。
  変わっていないクラスの `verified` は持ち越し、変わったものだけ `stale` に自動降格する。

### 6-2. 複数バージョンの持ち方: 抽出ツール同梱 + その場再生成(採用方針)

バージョン別カタログの併置配布ではなく、**構造抽出ツールをスキル本体に同梱し、
カタログを「出荷時に焼いたキャッシュ + 実行時に再導出できるもの」にする**:

- 抽出ツール(§7-2)を `skills/ue-material/scripts/` に置き、開発側のカタログビルドと
  実行時の再生成を**単一実装**にする(二重メンテを避ける)。
- **平常時**: 同梱カタログ(= fingerprint 一致のビルド済みキャッシュ)を使う。速く、
  オフラインで、開発時ゲート済み。
- **fingerprint 不一致時**: 現行の「止まってユーザーに確認」に代えて、抽出ツールを
  ユーザーのソースにその場で走らせ、構造カタログをローカル再生成できる。構造(Pin・props・
  使用条件)は即座に新バージョンへ追従し、AI 抽出の意味情報・監査状態だけ `stale` 表示にする。
- これによりバージョン別カタログを配布しなくても、ユーザーの手元にあるどのバージョンにも
  構造レベルで追従できる。1 バージョン = 1 カタログセットの原則は維持(per-node バージョン
  レンジ案は監査 4 軸との掛け算で複雑化するため採らない)。
- バージョン間の差分は `catalog_diff.py` の出力そのものがリリースノートになる。
- 留意点: ライブ再生成はパーサの破綻がユーザーの会話中に顕在化しうる。再生成結果には
  抽出信頼度(§7-2)を必ず付け、`manual_required` が出たクラスは Editor サンプル採取
  (既存の unknown-node フロー)へ誘導する。

### 6-3. 更新フローの目標形

```
UE 新バージョン取得
  → gen_manifest.py(新 fingerprint で走査、クラス別ハッシュ付き)
  → catalog_diff.py(旧 manifest と比較 → 再監査ワークリスト JSON)
  → 機械抽出パス(§7)で hash_changed / added クラスのスキーマを再抽出
  → 抽出信頼度の低いクラスだけを人手/AI 監査(ワークリスト駆動)
  → catalog_merge.py → オフラインゲート → 新バージョンのカタログセットとして配布
```

## 7. 方針 2: ノード index・input/output 情報の機械的抽出

現状ワーカー AI が読んでいる情報は、大部分が UE ソース上に**機械的にパース可能な形**で存在する。
どこまで機械で取れるか・どこから先が取れないかを仕分けるのが設計の要点である。

### 7-1. 情報源と抽出可能性の仕分け

| 情報 | ソース上の在り処 | 機械抽出 |
|---|---|---|
| クラス宣言・基底・header パス | `class ENGINE_API UMaterialExpressionX : public ...`(header) | **済**(gen_manifest.py) |
| 入力 Pin と順序(= input index) | header の `UPROPERTY()` 付き `FExpressionInput` フィールド。**宣言順が Pin index** | **可**: UPROPERTY ブロックの正規表現/簡易パーサで宣言順に列挙 |
| 入力名の上書き | .cpp の `GetInputName(int32 Index)` オーバーライド | **概ね可**: switch/if の定型が多い。非定型は要フラグ |
| 出力 Pin と順序 | .cpp コンストラクタの `Outputs.Reset()` + `Outputs.Add(FExpressionOutput(TEXT("R"), 1,1,0,0,0))` の呼び出し順 | **可**: 定型呼び出しの列挙。過去の出力 Pin 取り違えはまさにここの人手読み違いで、機械化の効果が最も大きい |
| デフォルト出力(Outputs 無宣言) | 基底 `UMaterialExpression` の既定(単一無名出力) | **可**: Outputs 操作が無いクラスに既定を適用 |
| プロパティ(props)と既定値 | header の UPROPERTY フィールド + コンストラクタ初期化 | **可**(型と既定値の対応表が必要) |
| プロパティ駆動 Pin(prop_pins)・動的 Pin | `RebuildOutputs()` / Custom ノードの `Inputs` 配列など実行時決定 | **不可 → 検出のみ**: `RebuildOutputs` 等の存在を検出して `dynamic_pins` フラグを立て、Editor サンプル(parse.py --no-catalog)で補完 |
| Root 入力の使用条件(ドメイン/ブレンド/シェーディングモデル別の有効・無効) | `Material.cpp` の `IsPropertyActive_Internal()`(単一の純関数、UE 5.8 では 7768 行目〜) | **可**: 純関数なのでバージョンごとに決定表(domain × blendmode × shadingmodel → 有効 Root 入力)として導出できる |
| ノード単位の使用条件(例: SceneTexture は PostProcess 系のみ、SkyLightEnvMapSample は Surface のみ) | `HLSLMaterialTranslator.cpp` の `Errorf` 群 + 各ノード `Compile()` 内のドメイン分岐 | **半自動**: `Errorf` 文字列と `GetMaterialDomain()` 比較の grep で候補を機械列挙し、条件の意味づけは AI 抽出(根拠付き)で `restrictions` フィールドに落とす |
| 表示名・検索語 | `GetCaption()` / `GetKeywords()` | **可**: 定型オーバーライドの列挙 |
| 説明・Compile 挙動 | `Compile()` / コメント | **半自動**: 説明文の合成と制約は §7-5 の構造化スキーマで扱う |

### 7-2. 提案ツール: `extract_schema.py`(`skills/ue-material/scripts/` 新設)

- **配置はスキル本体**。開発側のカタログビルド(dev/tools からの呼び出し)と、実行時の
  fingerprint 不一致時のローカル再生成(§6-2)を同一実装で担う。標準ライブラリのみ。
- 入力: 解決済みソースルート + `manifest.json`。出力: `dev/catalog/generated/auto/<class>.json`
  (現行フラグメントと同一スキーマ + 抽出メタデータ)。実行時再生成ではローカルの
  `.ue-material/` 配下に同形式で出力する。
- 各クラスについて header と対応 .cpp(`Private/Materials/MaterialExpressions.cpp` 集約分と
  クラス別 cpp の両方)を対象に、上表の「可」項目を抽出する。使用条件の抽出対象として
  `Material.cpp` と `HLSLMaterialTranslator.cpp` を参照範囲に加える(参照全集合は
  約 2.7MB → 約 3MB に増える程度)。
- **各抽出値に `extraction: {method, confidence, source_hash}` を付ける**。定型パターンに
  完全一致したら `high`、ヒューリスティックを要したら `low`、パース不能・動的 Pin 検出時は
  `manual_required`。`low`/`manual_required` だけが人手監査キューに乗る。
- 既存の手動監査(`dev/catalog/audits/`)は常に機械抽出より優先(現行 catalog_merge.py の
  override 機構をそのまま使う)。機械抽出はあくまで「pending の初期値の品質を上げ、
  再抽出を無償にする」層である。
- 検証: 既存カタログ(人手+突合済みの 359 クラス)に対して機械抽出を走らせ、一致率を測る。
  不一致はどちらかのバグなので、これ自体が両方向のバリデーションになる。
  `dev/fixtures/roundtrip/` と `dev/fixtures/editor/` の実測データも回帰材料に使う。

### 7-3. 補完チャネル(機械抽出で届かない部分)

1. **Editor リフレクションダンプ(任意・強力)**: UE Editor の Python API(`unreal` モジュール)で
   `MaterialExpression` 派生クラスを列挙し、実行時の入出力 Pin をダンプするスクリプトを
   `dev/tools/` に用意する。動的 Pin も実行時値で取れるため、ソースパースの答え合わせと
   `dynamic_pins` クラスの実測に使える。Editor が必要なので**開発時専用**(配布物には含めない)。
2. **クリップボード実測**: 既存の「未知ノードは Editor で 1 個置いてコピー →
   `parse.py --from-clipboard --no-catalog`」フローを、そのまま監査証拠
   (`editor-evidence.json`)への記録に接続する。

### 7-4. 要約(意味情報)の作り方: 2 階建て + AI は「抽出者」であって「作文者」ではない

効率化のためには各ノードの役割要約が必要だが、AI の自由英作文は揺らぎ・監査不能・
再現不能の三重苦になる(現行の和文プロースが実例)。次の 2 階建てとする:

- **1 階(機械・コストゼロで再生成可)**:
  - `GetCaption()` / `GetKeywords()` から表示名・検索語を機械抽出する。
  - 構造データから骨格文を決定論的に合成する(例: inputs/outputs/props の列挙文)。
- **2 階(AI・差分駆動)**:
  - 「何をするか」「条件付き挙動」「使用条件の理由」は、AI が `Compile()` 等を読み、
    **スキーマで定義された構造化フィールドにのみ**記録する。各事実に根拠
    `{path, symbol, source_hash}` を必ず付ける。自由記述の逃げ場は `notes` 1 箇所に限定し、
    常に unverified 扱いとする。
  - 配布用の英文 desc は構造化フィールドから**テンプレートで機械合成**する。
    同じ事実からは同じ文が出る(決定論)。事実が変わったときだけ文が変わるので、
    バージョン間 diff がそのままレビュー対象になる。
  - UE 更新時はソースハッシュが変わったクラスだけ AI 再抽出する。**AI コストは差分に比例**し、
    全件再作文は発生しない。ハッシュが変わった事実は `stale` に自動降格する。

イメージ(TextureSample):

```json
"semantics": {
  "op": "Samples a texture at UV coordinates",
  "conditional": [
    {"when": "MipValueMode == TMVM_Derivative",
     "effect": "CoordinatesDX/CoordinatesDY inputs become required",
     "evidence": {"path": ".../MaterialExpressions.cpp", "symbol": "GetInputName", "source_hash": "..."}}
  ]
}
```

→ 合成結果: "Samples a texture at UV coordinates. When MipValueMode is TMVM_Derivative,
CoordinatesDX/DY become required."

AI 抽出結果はフィールド単位で機械抽出(§7-2)や Editor 実測と突合できるため、読み違いは
検出可能になる(過去の出力 Pin 取り違えはまさにこの種の突合で発見された)。

### 7-5. 変えないもの: 監査と Editor 実証

監査結果(`dev/catalog/audits/`)と Editor 実証(`editor-evidence.json`)は**ソースから
導出できない一次情報**であり、現行機構をそのまま残す。機械抽出・AI 抽出の結果は常に
これらのオーバーレイの**下**に置かれ、監査 override が最優先である点も変えない
(現行 `catalog_merge.py` の優先順位をそのまま使う)。

### 7-6. 実施順(improvement-plan.md への組み込み)

improvement-plan.md の推奨順 **A → B → C → D → E → F** に対し、本方針は:

- §6-1(ハッシュ・diff)= Phase A そのもの。**最初に着手**。
- §7-2 `extract_schema.py` は Phase D(量産監査)の**前**に挟む。353 クラスの pending を
  人手で潰す前に機械抽出で下敷きを作る方が、監査コストが桁で下がる。
  位置づけとしては「Phase C.5」または Phase D の前提ツールとして発注する。
  §7-4 の構造化 semantics スキーマは Phase C(構造化スキーマ設計)の具体化であり、
  AI 抽出バッチ(2 階)は Phase D の作業内容そのものになる。
- §6-2(複数バージョン)は Phase F(自動アップデート)と同時期でよい。単一バージョンで
  パイプラインが機械化されていれば、複数化は主にレイアウトと切り替えの問題になる。

## 8. 変わらない原則(リファクタリング後も維持)

- **一次情報は UE ソース。カタログは機械導出されたバージョン刻印付きキャッシュ**であり、
  ソースと矛盾したらソースが勝つ。ソースから導出できない一次情報は
  監査(`audits/`)・Editor 実証(`editor-evidence.json`)・検索 alias の 3 つだけで、
  これらの永続化機構は現行のまま残す。
- 配布物は英語のみ・Python 標準ライブラリのみ・`dev/` 非依存・オフライン動作。
- UE チェックアウトは読み取り専用。ソースで証明できない事実は書かない。
- 機械抽出・AI 抽出であっても「根拠(path + symbol + hash)を持たないデータを verified に
  しない」。機械化されるのは**抽出と差分検出と英文合成**であり、監査状態の語彙と昇格規則は
  変えない。AI は構造化フィールドへの抽出者であり、自由作文はしない。
- オフラインゲート(unittest / check_english / check_distribution / catalog_merge の決定論性)を
  全変更で通す。
