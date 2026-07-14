# 外部AIへの作業引き渡しガイド

## 現在地（継続更新）

最終更新: 2026-07-14 / 引き継ぎ実行者: Codex

この欄を再開時の正本とする。個別タスクの完了判定は各 task md の `status:` と成果物を
優先し、古い一覧表の status は参考にしない。

完成後の追加精査、残存risk、優先順位付き改善案は
[`tasks/MAIN-AI-REVIEW.md`](MAIN-AI-REVIEW.md)を参照。次段階を始めるメインAIは、まず同文書の
P0と「メインAIへの具体的な次の発注」を読むこと。

Customノードの利用可能関数とUE 5.8 source調査は
[`tasks/CUSTOM-NODE-SOURCE-RESEARCH.md`](CUSTOM-NODE-SOURCE-RESEARCH.md)に記録した。
旧translator/MIR差、32引数上限、texture sampler、SceneTexture、`/Project` include、
Engine private APIの危険度を含む。Custom対応に着手するAIは必読。

### 完了済み

- T01: `skill/references/format.md`。ユーザー提供 `example/sample.txt` の実 T3D を反映済み。
- C01〜C22: `catalog/generated/C01.json`〜`C22.json`。全 task md が `DONE`。
- M02〜M04: `catalog/generated/M02-mf.json`〜`M04-mf.json`。全 task md が `DONE`。
- ここまでの成果は commit `8faac81` (`Add node catalogs and T3D format spec`) に含まれる。

### 現在実行中

- 追加精査としてCustomノードのUE 5.8 source調査を完了し、
  `tasks/CUSTOM-NODE-SOURCE-RESEARCH.md`へ記録した。これは調査・設計報告であり、
  CustomのMGJSON構造化実装自体は未着手。次の実装AIはMAIN-AI-REVIEW P0-1と同時に扱う。
- T02 完了: `skill/references/mgjson.md` と `tasks/T02-mgjson-spec.md` を更新済み。
- M01 完了: `skill/references/mf-call.md`、task md、`INSTRUCTIONS-mf.md` を更新済み。
- T06 完了: 359/359ノードと82 MFを `skill/catalog/` に統合し、逆引き索引を生成済み。
- T05 完了: `skill/scripts/validate.py`。破損17パターン、正常graph、CLI exit codeを検証済み。
- T03/T04 完了: `build.py` / `parse.py`。通常・Comment・MF、typed/raw props、layout、
  file/stdin/stdout/clipboard、catalog無しparse、実sample、canonical round-tripを確認済み。
- T07 完了: `skill/SKILL.md`（159行）と `skill/agents/openai.yaml`。skill-creatorの
  `quick_validate.py` は `Skill is valid!`。
- T08 完了: offline QAとEditor steps 1〜9が全てOK。実copy→parse→build→再paste同型、
  PinType全省略も成功。結果は`tasks/verification-log.md`。Editorは
  `5.8.0-55116800+++UE5+Release-5.8`（Windows 11 build 26200.8655）。
- E01 完了: `examples/01-single-constant.txt` に実機コピーの色変更済み Constant3Vector
  （RGB=`1.0,0.644811,0.532869`）を保存。02はConstant×2 → Multiply → Addの4ノード・
  3接続、03は通常Texture SampleとTexCoord・割り当てTexture2D・UV接続、04はTextureSample
  G出力→Multiply A、05は設定済みScalarParameter + VectorParameterを保存。06はComment枠＋
  2ノードを生成・実機往復し、2 nodes / 1 Comment / 1 link、unknown/raw 0を確認。
  07は`BlendAngleCorrectedNormals` MaterialFunctionCallの生成時に旧pathで`Unspecified Function`
  となったため、手動配置された実機コピーを再受領し、
  `examples/07-function-call.txt` に保存済み。
  正しいpathが`Engine_MaterialFunctions02/Utility`と判明したため、M02元カタログとMF仕様例を
  修正し、BaseNormal / AdditionalNormal / Resultを実機確認済み。08は通常Rerouteを
  `Convert to Named Reroute`で宣言＋使用へ変換した実機コピーを受領し、
  `examples/08-named-reroute.txt` に保存済み。共有GUID一致を確認し、未収載VariableGuidを
  C08へ追加、両classをverifiedへ更新。09は入力A/Bと`return A + B;`を持つCustomを受領し、
  `examples/09-custom.txt`へ保存。未収載の`ShowCode: bool`をC08へ追加した。索引付きInputsは
  MGJSONの`raw_props`へ可逆保持される。これで01〜09の実機sampleを全件収集済み。

### 監査結果と注意

- 基盤T01〜T08、C01〜C22、M01〜M04、追加sample収集E01はすべて完了。
  E01は最低要件01〜05に加え、任意追加06〜09も実機収集済み。
- `catalog/generated/*.json` は 26 ファイルすべて JSON syntax OK。
- `tools/qa_outputs.py` の候補20 classを照合し、明確な差分だった ViewProperty を
  `Property` / `InvProperty` の2出力へ修正した。他は無名出力、機能フラグ条件、または
  CustomOutput の `GetNumOutputs()` によるため候補表示のままで妥当。
- 一部 generated catalog の `class` に C++ prefix `U` が混入している
  （例: C08 の `/Script/Engine.UMaterialExpressionMaterialFunctionCall`）。T06 は manifest の
  module / class 名から runtime class path を正規化し、merged catalog に誤 prefix を残さない。
- T06 は既存章の省略フィールドを500件超警告したうえで補完する。型違反・重複・manifest
  不一致はエラー。実round-trip済み3 classだけverified true。詳細はT06/T08実施メモ参照。
- validate.py は未検証classごとに warning を出す設計。MaterialFunctionCall は packaged
  function catalog の path が必須で、任意の未収載functionは Pin schema 不明のため error。
- T03試験中に parameter基底の継承props欠落を発見し、T06 mergeで `ParameterName` / `Group` /
  `SortPriority` を `is_parameter` classへ補完するよう修正・再生成した。
- step 8実copy-backでComment geometryが完全一致しないことを確認し、`parse.py` の包含推定を
  各辺0〜200pxのtight-enclosure判定へ修正。修正版の実round-tripは同型を確認済み。
- clipboard試験はWindows PowerShell経路で成功。step 9でPinType field全省略も実機確認済み。
- E01全件監査で02の異なるConstant出力が同じPinIdを持つことを確認。`parse.py`のPin解決を
  PinId単独から`(owner node name, PinId)`へ修正し、3接続すべての復元を確認済み。
- 最終QA: 01〜09は全T3DのBegin/End均衡、parse成功、unknown class 0。09だけは索引付きInputs
  2件を設計どおり`raw_props`保持。Python compile、catalog merge、generated + merged JSON
  28ファイル、`git diff --check`、全task `status: DONE`を確認済み。
- 実行環境では `python` が PATH から見えず、`py` に登録 interpreter もなかった。
  検証用 Python 3.12.11を `.uv-python/` へ一時配置してEditor検証と最終QAに使用し、
  最終QA後に`.uv-python/` / `.uv-cache/` / `__pycache__`を削除済み。
- ユーザー所有の未追跡 `.claude/settings.local.json` には触れない。

### 中断時の再開手順

1. この「現在地」と `git status --short` を読む。
2. `rg -n "^status:" tasks -g "*.md"` で task の実態を再確認する。
3. `status: DONE` でない最上流 task から依存順に再開する。
4. 各 task の成果物、task md の `status` / `実施メモ`、この欄を同じ作業単位で更新する。
5. Python 実装後は unit test と build→parse round-trip を必ず再実行する。

このリポジトリのタスクは全て **タスクmdのパスを伝えるだけ** で、会話コンテキストなしに
任意のAI(Codex CLI、別のClaude Codeセッション、その他エージェント)へ発注できる。

## 発注文(これだけ伝えればよい)

```
C:\work\script\ue_material_skill の tasks/T03-build-tool.md を実行して。
md内の「単独実行の前提」と「完了条件」に従うこと。
```

各タスクmdに以下が揃っている:
- 作業ディレクトリ / UEソースの場所(読み取り専用)
- 必読ファイル一覧(そのタスクに必要な文脈は全てリポジトリ内のファイルにある)
- 出力先と完了条件
- 完了時の作法(status: DONE 更新 + 「## 実施メモ」追記)

## 高性能AI向けタスク(設計・実装・ソース読解)

| タスク | 内容 | 着手可能条件 |
|---|---|---|
| tasks/T01-format-spec.md | T3D仕様書の清書 | 今すぐ可 |
| tasks/T02-mgjson-spec.md | 中間フォーマット仕様 | 今すぐ可 |
| tasks/M01-mf-call-format.md | MaterialFunctionCall形式のソース調査 | 今すぐ可 |
| tasks/T03-build-tool.md | build.py 実装 | T01+T02完了後 |
| tasks/T04-parse-tool.md | parse.py 実装 | T01+T02完了後 |
| tasks/T05-validate-tool.md | validate.py 実装 | T02完了後 |
| tasks/T06-catalog-merge.md | カタログ結合・lint | 今すぐ可(C系一部完了済) |
| tasks/T07-skill-md.md | SKILL.md 執筆 | T01〜T05完了後 |

推奨並列: 第1陣 = T01 + T02 + M01 + T06(相互依存なし)。
第2陣 = T03 + T04 + T05(T01/T02の成果物ができてから)。

## 安価なAI向けタスク(機械的抽出・知識書き出し)

- tasks/catalog/C01.md〜C22.md(ノードカタログ。C01〜C08とM02〜M04は完了済み)
- 発注文テンプレは tasks/DISPATCH.md 参照

## 競合の回避

- 各タスクの出力ファイルは重複しない設計。同じタスクを二重発注しない限り衝突しない
- 着手前に対象タスクmdの `status:` を確認(DONE なら作業不要、
  進行中マークが必要なら `status: WIP <担当名>` に書き換えてから始めてよい)
- 全体進捗の確認: `catalog/generated/*.json の存在` と各mdの `status:` 行が真実

## 品質チェック(発注元がやること)

- C系回収後: `python tools/qa_outputs.py`(出力ピンとcppコンストラクタの矛盾検出)
- 全回収後: T06 の catalog_merge.py で manifest.json とのカバレッジ検査
