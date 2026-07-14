# ue-material 改善計画: 検索順位・ソース非依存運用・自動アップデート

Status: 計画(未着手)
作成日: 2026-07-15
前提コミット: `2c0b9fd`
前提ベースライン: UE 5.8.0 / branch `UE5` / チェックアウト `C:\work\unreal\UnrealEngine-release`
先行文書: `dev/docs/refactoring-plan.md`(完了済み Phase 0–8)、`dev/docs/source-update.md`、
`dev/docs/skill-evaluation-2026-07-15.md`

この計画はワーカー AI に段階実行させることを前提とする。各 Phase は独立にレビュー可能な
変更単位であり、**Phase 末尾の Exit gate を全て通過するまで次へ進まない**。

---

## 0. 要求と過不足の整理

ユーザー要求:

1. 検索結果に関連度順位を付ける(言語ベクター等も検討)
2. 実行時の UE ソースアクセスを基本的に不要にする — `legacy_unverified` の和文プロースを、
   ソースから組み立てた構造化表記(揺らぎのない正確な**英文**)に**置き換える**。
   和文レガシープロースは説明文としては全廃し、最終的に配布物から退役させる
3. 効率的な自動アップデートを確立する
4. バージョン表記の追加と、ソース自体のハッシュによる更新検出
5. Editor 実証の全件先行は非現実的 — 回帰検証は後回し、使いながら改善

### 要求に対して追加した項目(不足の補完)

- **A-3 `catalog_diff.py`**: 要求 3・4 の前提。ハッシュを記録しても差分を分類する
  ツールが無ければ再監査対象を特定できず、自動アップデートが成立しない。
- **C(構造化スキーマの先行設計)**: 353 ノードを一斉監査する前に、説明文の
  「揺らぎのなさ」を保証する機構(構造化フィールド + 決定論的な英文合成)と
  パイロット検証を挟む。スキーマ未確定のまま量産すると全件やり直しになる。
- **E(SKILL.md 運用規則の書き換え)**: 要求 2 の受益部分。カタログを直しても
  「毎回ソースを読め」の規則が残れば効率は変わらない。provenance 連動の免除規則と
  `UE_SOURCE_ROOT` 不在時のフォールバックを明文化する。
- **stale 状態の導入**: ソースハッシュが変わった監査済みエントリを自動降格する
  状態。これが無いとエンジン更新後に古い監査結果が「verified」のまま残る。

### 意図的に除外した項目(過剰の排除)

- **実行時埋め込みベクター検索**: スキルは「Python 標準ライブラリのみ・オフライン」が
  配布制約。クエリ側のベクター化に外部モデルが必要な方式は採用しない。
  決定論的な字句ランキング + alias で解決し、ベクターは B-4 の条件付き代替に留める。
- **Editor 実証の先行全件実施**: ユーザー指示により後回し。Phase G として
  「使いながら蓄積する」仕組みの定義のみ行い、実装しない。
- **CI からの UE ソース参照**: CI 環境にエンジンソースは置けない。CI は
  オフラインゲートのみ、ソース依存工程はローカル実行と明確に分離する。

### 依存関係と実行順

```
A(バージョン/ハッシュ/diff) ──→ D(量産監査) ──→ E(規則書き換え)
        │                          ↑
        └──→ F(自動アップデート)   C(スキーマ+パイロット)
B(検索順位)は独立。いつでも実行可。
G(Editor 回帰)は E 以降、任意時期。
```

推奨順: **A → B → C → D(複数バッチ)→ E → F → G(保留)**。
B は A と並行発注可。F は A 完了後なら D と並行可。

---

## 共通規約(全 Phase・全ワーカー共通)

- 配布物 `skills/ue-material/**` は英語のみ・Python 標準ライブラリのみ・`dev/` 非依存。
- UE ソースチェックアウトは読み取り専用。事実は必ずソース根拠(path + symbol)を伴う。
  ソースで証明できない事実は書かない・埋めない・推測しない。
- 監査状態の語彙: `verified` / `pending` / `stale` / `legacy_unverified` / `not_applicable`。
- 各 Phase 完了時に以下の標準ゲートを全て実行し、結果を変更概要に記録する:

```powershell
uv run --offline --no-project python -B -m unittest discover -s dev/tests -v
uv run --offline --no-project python -B dev/tools/check_english.py
uv run --offline --no-project python -B dev/tools/check_distribution.py
uv run --offline --no-project python -B dev/tools/catalog_merge.py --quiet
git diff --check
```

- `catalog_merge.py` の再実行で差分が出ないこと(決定論性)を必ず確認する。
- 1 Phase(D はバッチ 1 つ)= 1 レビュー単位。無関係ファイルを変更しない。

---

## Phase A: バージョン・ソースハッシュ・差分分類(基盤)

目的: 要求 4 の充足と、要求 3(自動アップデート)・Phase D(再監査範囲特定)の基盤。

### A-1 バージョンメタデータ

- `skills/ue-material/catalog/meta.json` を新設:
  `skill_version`(semver)、`ue_version`、`ue_branch`、`generated_at`(UTC 日付)、
  各カタログファイルの SHA-256。
- `catalog_merge.py` が meta.json を生成し、`check_distribution.py` が
  ファイルハッシュ整合を検証する。
- `search_catalog.py` に `--version` を追加し meta.json を表示。
- README に「更新 = `skills/ue-material/` の丸ごと上書きコピー」と
  バージョン確認方法を追記。

### A-2 ソースファイルハッシュの記録

- `gen_manifest.py` を拡張し、各クラスの header(および判明している実装 cpp)の
  SHA-256 を `dev/catalog/manifest.json` に記録する。
- `gen_node_evidence.py` を拡張し、監査済みエントリの references 各項目に
  記録時点の `source_hash` を保存する。
- ハッシュ計算は改行コード差を吸収するため **LF 正規化後のバイト列**に対して行う。

### A-3 `dev/tools/catalog_diff.py`

- 新旧 2 つの manifest.json を比較し、以下を分類した機械可読レポート(JSON)と
  人間可読サマリを出力する:
  - `added` / `removed` / `renamed?`(header 移動)
  - `hash_changed`(宣言 header 変更 → schema 再監査候補)
  - `impl_hash_changed`(実装 cpp 変更 → description/restrictions 再監査候補)
  - `unchanged`
- 出力レポートはそのまま Phase D / F の再監査ワークリストとして使える形式にする。

### A-4 stale 降格

- `gen_node_evidence.py`: 監査済みエントリの `source_hash` が現在のソースと
  不一致の場合、該当 audit 次元を `verified` → `stale` に自動降格する
  (人手 override の削除はしない。降格のみ)。
- `validate.py` / `search_catalog.py` は `stale` を pending と同様に
  「ソース確認が必要」と表示する。

### Exit gate

- meta.json が決定論的に再生成され、ハッシュ検証が check_distribution.py で通る。
- 既知の 6 監査済みノードすべてに source_hash が付き、テストで検証される。
- manifest を 2 回生成して catalog_diff.py が「差分ゼロ」を報告する。
- header を一時コピーで改変した negative テストで stale 降格が発火する
  (テストはフィクスチャで行い、実チェックアウトは変更しない)。
- 標準ゲート全通過。

---

## Phase B: 検索の関連度順位(独立・早期実施可)

目的: 要求 1。`search_catalog.py` の出力を関連度順に並べ、既定件数を制限する。

### B-1 決定論的スコアリング

標準ライブラリのみで実装する字句ランキング。案(実装時に調整可、ただし決定論必須):

| 一致対象 | スコア |
|---|---|
| クラス名 完全一致(大文字小文字無視) | 100 |
| クラス名 前方一致 / 部分一致 | 70 / 50 |
| alias 完全一致 | 60 |
| ソースシンボル一致 | 45 |
| Pin / property 名一致 | 35 |
| desc / notes トークン一致 | 15 |
| legacy プローストークン一致 | 8 |

- 複数語クエリは AND 的に加点(全語ヒットにボーナス)。同点はクラス名の辞書順で
  安定ソート。
- 既定で上位 8 件 + 「他 N 件、--all で表示」のフッター。`--all` / `--limit N` を追加。
- `--class` 等の完全一致フィルタの挙動は変えない。

### B-2 alias フィールド

- nodes.json の各エントリに `aliases: []` を追加(既定は空)。
- 生成ツールで legacy-node-prose.json から**機械的に**日本語キーワードを抽出して
  aliases に投入する(例: 説明文の名詞句上位)。alias は検索補助専用であり、
  事実の主張ではないことをスキーマコメントで明示する。
- これにより日本語クエリ(例: 「テクスチャ サンプル」)でも順位付けが機能する。
- **この alias 抽出は Phase D での和文プロース退役の前提**。退役後の日本語検索は
  aliases のみで担保されるため、抽出の再現コマンドを dev/tools/ に残すこと。

### B-3 テスト

- `dev/tests/test_catalog_search.py` に追加:
  `texture sample` → 先頭が `TextureSample`、`lerp` → `LinearInterpolate` が上位、
  日本語クエリの上位一致、`--limit`/`--all` の件数、順位の決定論性(2 回実行同一)。

### B-4 ベクター検索(条件付き・原則実施しない)

字句ランキングで代表 20 クエリ中 17 以上が top-3 に入るなら実施しない。
不足する場合のみ、**事前計算の文字 n-gram ハッシュベクトル**(生成はビルド時、
クエリ側も同一ハッシュ関数で標準ライブラリのみ・決定論)を検討する。
外部埋め込みモデル・実行時ネットワークアクセスは採用しない。

### Exit gate

- 上記テスト全通過、代表クエリの top-3 品質基準を満たす。
- 出力は 1 クエリあたり既定で 50 行以内。標準ゲート全通過。

---

## Phase C: 構造化セマンティクスのスキーマ設計とパイロット

目的: 要求 2 の中核。「揺らぎのない構造化表記」を量産可能な形で確定する。

### C-1 スキーマ設計

nodes.json エントリに `semantics` を追加する。自由プロースを増やすのではなく、
**構造化フィールドから英文 desc を決定論的に合成する**:

```json
"semantics": {
  "operation": "componentwise_binary",
  "formula": "A + B",
  "unconnected_defaults": {"A": "ConstA", "B": "ConstB"},
  "value_domain": "float/vector, componentwise",
  "restrictions": [],
  "unresolved": []
}
```

- `operation` は列挙語彙(binary/unary/texture_sample/coordinate/parameter/
  constant/flow/custom/... 実装時に確定)。
- `desc` は catalog_merge.py が semantics からテンプレート合成する。
  人手・ワーカーの自由英作文を desc に直接置くことを禁止し、表記揺れを排除する。
- テンプレートで表現できない事実は `notes` に置くが、その場合も引用元
  symbol を references に追加しなければ merge が拒否する。
- 証明できない項目は `unresolved` に列挙する(空欄で埋めない)。
- 監査フラグメント(`dev/catalog/audits/*.json`)の既存形式
  (audit 状態 + references[path/symbol/claims])を保ち、`semantics` を追加。

### C-2 抽出支援ツール

- `dev/tools/extract_expression_facts.py` を新設: 指定クラスの header /
  MaterialExpressions.cpp / MaterialExpressionsToMIR.cpp から、コンストラクタの
  出力定義・入力宣言・UPROPERTY・既定値を機械抽出して**下書き JSON** を出力する。
  機械抽出は下書きであり、ワーカーによるソース照合を置き換えない。
- 既存の出力 Pin QA(コンストラクタ照合)の知見を移植し、
  `dev/tools/qa_semantics.py` として schema 検証 + Pin/コンストラクタ突合 +
  references 実在検証を一括実行できるようにする。

### C-3 パイロットバッチ

- 既監査 6 ノード + 頻出 14 ノード(Lerp, Clamp, Power, TextureSample,
  TextureCoordinate, ScalarParameter, VectorParameter, ComponentMask,
  AppendVector, Divide, Subtract, OneMinus, Fresnel, Time を目安)を
  semantics 形式で監査し、合成された desc の品質をレビューする。
- パイロットの結果でテンプレート語彙・operation 列挙を確定してから D に進む。

### Exit gate

- semantics スキーマ検証が catalog_merge.py に組み込まれ、違反があると
  マージが失敗する。
- パイロット 20 ノードの desc が全てテンプレート合成で生成され、references の
  path/symbol が gen_node_evidence.py で実在検証されている。
- 20 ノードの schema/description 監査状態が `verified`。標準ゲート全通過。

---

## Phase D: 量産ソース監査(バッチ発注・ワーカー並列)

目的: 残り約 339 ノードの schema/description を `pending`/`legacy_unverified` から
`verified` にし、実行時ソースアクセス不要の前提を作る。

### 発注設計

- 1 バッチ = 12〜18 クラス。優先順:
  1. 数学・定数・パラメータ・テクスチャ・座標・ベクトル系の頻出ノード
  2. その他の通常 Engine ノード
  3. 動的 Pin / 特殊グラフノード(NamedReroute, Composite, FunctionCall 系,
     状態依存 Pin)— **上級ワーカーまたはメイン AI が担当**
  4. Substrate ノード
  5. プラグインノード(該当プラグインソースがチェックアウトに存在する場合のみ)
- 発注文書 `dev/docs/audit-batch-instructions.md` を C 完了後に作成する。
  内容: 自己完結の前提(ソースルート、読み取り専用、推測禁止、unresolved 運用)、
  semantics スキーマ、監査手順(refactoring-plan §7 の 10 手順を継承)、
  出力先(`dev/catalog/audits/<batch>.json`)、実行すべき QA コマンド。
- ワーカー成果物は監査フラグメント JSON のみ。skills/ 直接編集は禁止し、
  反映は必ず catalog_merge.py 経由にする。

### 受け入れ(バッチごと・メイン AI が実施)

1. `qa_semantics.py` 通過(schema / Pin 突合 / references 実在)。
2. 抜き取りソース照合: バッチ内 3 ノード以上を無作為に選び、references の
   symbol を実ソースで確認する。虚偽引用が 1 件でもあればバッチ全体を差し戻す。
3. `unresolved` の妥当性確認(動的挙動を一般文で隠していないか)。
4. 標準ゲート + 決定論確認。
5. verified になったノードは合成英文 desc を唯一の説明として表示し、和文レガシー
   プロースは表示経路から退役させる。B-2 の alias 抽出が完了していることを確認の上、
   該当エントリを legacy-node-prose.json から削除する(原文は git 履歴に残る)。

### Exit gate(Phase 全体)

- 非プラグイン・非 Substrate の全クラスで schema/description が `verified` または
  明示的 `unresolved` 付き verified。
- **配布物の説明表示経路に和文レガシープロースが一切残っていない。** 全バッチ完了後、
  `catalog/legacy-node-prose.json` を配布物から撤去する(未監査残がある場合は
  その残ノード分のみ `dev/catalog/quarantine/` へ移し、配布物には含めない)。
  撤去後、check_english.py の同ファイル exemption を削除し、lint が
  exemption なしで通ることを確認する。
- 日本語クエリの検索テスト(B-3)が alias のみで引き続き通る。
- プラグイン/Substrate の未監査残があれば、その一覧が machine-readable に
  出力できる(`search_catalog.py --evidence pending`)。
- 標準ゲート全通過。

---

## Phase E: 実行時規則の書き換え(ソース非依存運用への切替)

目的: 要求 2 の受益。カバレッジ達成後に SKILL.md の運用規則を provenance 連動にする。

### E-1 規則変更(SKILL.md / source-verification.md)

- 「全ノードで使用前ソース inspect 必須」を廃し、次の 3 段に置き換える:
  1. `verified`(かつ stale でない)ノード: カタログの semantics/desc を
     そのまま事実として使用してよい。ソース再読不要。
  2. `pending` / `stale` / `legacy_unverified`: 従来通りソース inspect 必須。
     ソースが無い環境では Editor サンプル要求(既存の unknown-node 手順)に切替。
  3. `unresolved` 記載のある挙動: その項目に限りソースまたは Editor サンプルが必要。
- `UE_SOURCE_ROOT` 不在時の明示フォールバック節を追加:
  「verified ノードのみで作業する。pending ノードは Editor サンプル手順を使う。
  推測での補完は不変で禁止」。

### E-2 ツール側の整合

- `search_catalog.py` の各レコード先頭に `[verified]` / `[pending]` / `[stale]` を
  表示する。Phase D で和文レガシープロースは退役済みのため、`pending` ノードは
  説明なし(構造データ + ソース参照のみ)で表示し、説明の代用を出さない。
- `validate.py` の警告文言を新 3 段規則に合わせる。

### Exit gate

- SKILL.md が新規則で 200 行以内・英語 lint 通過。
- クリーンコンテキストでのフォワードテスト: (a) verified ノードのみの生成タスクが
  ソース参照なしで完了する、(b) pending ノードを含むタスクで正しくソース inspect
  または Editor サンプル要求に分岐する、の 2 本を実施し記録する。
- 標準ゲート全通過。

---

## Phase F: 自動アップデートパイプライン

目的: 要求 3。エンジン更新時の再監査を「変更があったものだけ」に絞り、
定型工程を 1 コマンド化する。

### F-1 オーケストレータ `dev/tools/update_from_source.py`

実行フロー(dry-run 既定、`--apply` で反映):

1. `gen_manifest.py` 相当を実行し、新 manifest を一時生成。
2. `catalog_diff.py` で旧 manifest と比較し、変更分類レポートを
   `dev/catalog/diff-<date>.json` に出力。
3. `gen_node_evidence.py` で declaration 検証と stale 降格を実施。
4. `catalog_merge.py` で再生成、meta.json の `ue_version` / ハッシュを更新。
5. 標準ゲートを実行し、結果を含むサマリを出力:
   「added N / removed N / 要再監査 N(クラス名列挙)/ ゲート結果」。
6. 再監査ワークリスト(Phase D と同じバッチ形式)を自動生成する。

自動化の範囲は**機械で証明できる工程まで**。schema/description の再 verify は
生成されたワークリストに基づく Phase D 型のバッチ監査で行い、自動昇格はしない。

### F-2 CI(オフラインゲートのみ)

- GitHub Actions(または同等)で push 時に標準ゲート + merge 再生成差分ゼロ確認を
  実行する。UE ソース依存工程(gen_manifest / gen_node_evidence)は CI 対象外と
  明記する。
- リポジトリに Python/uv の取得手順を含む CI 定義を追加する。

### Exit gate

- 同一ソースに対する `update_from_source.py` 実行が「変更ゼロ・ゲート全通過」を
  報告する(冪等性)。
- フィクスチャで header 改変を模擬した dry-run が、該当クラスのみを
  要再監査として列挙する。
- CI がグリーン。標準ゲート全通過。

---

## Phase G: Editor 回帰検証(保留 — 定義のみ、実装しない)

ユーザー方針により後回し。将来の実装のために方式だけ固定しておく:

- **使いながら蓄積**: 実利用で貼り付け成功/失敗が確認された際、コピーバック T3D を
  `dev/fixtures/editor/` に保存し、`editor-evidence.json` にノード・UE バージョン・
  結果を 1 コマンドで追記する小ツール(`dev/tools/record_editor_evidence.py`)を用意する。
- **将来の自動化**: UE Editor 自動化(T3D import → 再構築 → export → parse →
  canonical MGJSON 比較 → コンパイル結果記録)は refactoring-plan §16 の記載を継承。
- 実装トリガー: 貼り付け不具合が実際に発生した領域、または Phase F でのエンジン
  更新後の高リスクノード(動的 Pin 系)から着手する。

---

## 発注テンプレート(ワーカー AI 向け共通ヘッダ)

各 Phase をワーカーに渡す際は、以下を発注文の先頭に必ず含める:

1. リポジトリルートと変更許可スコープ(Phase ごとの対象ファイル列挙)。
2. UE ソースルート(`UE_SOURCE_ROOT`)と読み取り専用の明示。
3. 「ソースで証明できない事実は書かない。unresolved に記録する」規則。
4. 出力形式(該当スキーマの実例 1 件)。
5. 完了時に実行するゲートコマンド(本文書「共通規約」のブロックをコピー)。
6. 変更概要の報告様式: 変更ファイル一覧、ゲート結果、未解決事項。

メイン AI の受け入れ責務: 抜き取りソース照合、決定論確認、Phase Exit gate の判定。
