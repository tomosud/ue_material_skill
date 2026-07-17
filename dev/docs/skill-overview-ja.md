# ue-material スキル 現状実装まとめとアップデート耐性リファクタリング方針

作成日: 2026-07-17
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

基本コンセプトは「**カタログ = (UE バージョン, ソースハッシュ) に対する再現可能なビルド成果物**」
にすることである。improvement-plan.md の Phase A / F と整合する。

### 6-1. バージョンをデータに刻む(Phase A 相当・一部実装済み)

- fingerprint(`5.8.0|UE5`)刻印と実行時照合は**実装済み**(`gen_node_evidence.py` +
  `source_fingerprint.py`)。
- 未実装: `meta.json`(skill_version / ue_version / 各カタログの SHA-256)、
  manifest への**クラス別ソースファイルハッシュ**記録、`catalog_diff.py`(新旧 manifest の
  差分を added / removed / hash_changed / unchanged に分類)。
- ハッシュがあれば、UE 更新時の再監査対象を「変わったクラスだけ」に機械的に絞れる。
  変わっていないクラスの `verified` は持ち越し、変わったものだけ `stale` に自動降格する。

### 6-2. 複数バージョンの持ち方(提案)

- **1 バージョン = 1 カタログセット**を基本とする。単一カタログ内に per-node のバージョン
  レンジを持たせる案は、監査状態 4 軸との掛け算で複雑化するため採らない。
- レイアウト案: `skills/ue-material/catalog/` を現行バージョン(既定)とし、追加バージョンは
  `catalog/versions/<fingerprint>/` に同一スキーマで併置。`source_fingerprint.py` の照合結果で
  スクリプト群が読むカタログを切り替える。
- 生成側は「同じパイプラインに別の `UE_SOURCE_ROOT` を与えると別バージョンのカタログが出る」
  形を保つ。バージョン間の差分は `catalog_diff.py` の出力そのものがリリースノートになる。
- 配布サイズが問題になるまでは全バージョン同梱でよい。問題になったら既定 + 差分形式を検討する。

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
| 説明・制約・Compile 挙動 | `GetCaption()` / `Compile()` / コメント | **半自動**: Caption は取れるが、説明文の合成と制約は監査対象のまま(improvement-plan.md Phase C の構造化スキーマで扱う) |

### 7-2. 提案ツール: `gen_node_schema.py`(dev/tools/ 新設)

- 入力: `UE_SOURCE_ROOT` + `manifest.json`。出力: `dev/catalog/generated/auto/<class>.json`
  (現行フラグメントと同一スキーマ + 抽出メタデータ)。
- 各クラスについて header と対応 .cpp(`Private/Materials/MaterialExpressions.cpp` 集約分と
  クラス別 cpp の両方)を対象に、上表の「可」項目を抽出する。
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

### 7-4. 実施順(improvement-plan.md への組み込み)

improvement-plan.md の推奨順 **A → B → C → D → E → F** に対し、本方針は:

- §6-1(ハッシュ・diff)= Phase A そのもの。**最初に着手**。
- §7-2 `gen_node_schema.py` は Phase D(量産監査)の**前**に挟む。353 クラスの pending を
  人手で潰す前に機械抽出で下敷きを作る方が、監査コストが桁で下がる。
  位置づけとしては「Phase C.5」または Phase D の前提ツールとして発注する。
- §6-2(複数バージョン)は Phase F(自動アップデート)と同時期でよい。単一バージョンで
  パイプラインが機械化されていれば、複数化は主にレイアウトと切り替えの問題になる。

## 8. 変わらない原則(リファクタリング後も維持)

- 配布物は英語のみ・Python 標準ライブラリのみ・`dev/` 非依存・オフライン動作。
- UE チェックアウトは読み取り専用。ソースで証明できない事実は書かない。
- 機械抽出であっても「根拠(path + symbol + hash)を持たないデータを verified にしない」。
  機械化されるのは**抽出と差分検出**であり、監査状態の語彙と昇格規則は変えない。
- オフラインゲート(unittest / check_english / check_distribution / catalog_merge の決定論性)を
  全変更で通す。
