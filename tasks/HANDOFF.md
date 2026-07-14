# 外部AIへの作業引き渡しガイド

## 現在地（継続更新）

最終更新: 2026-07-14 / 引き継ぎ実行者: Codex

この欄を再開時の正本とする。個別タスクの完了判定は各 task md の `status:` と成果物を
優先し、古い一覧表の status は参考にしない。

### 完了済み

- T01: `skill/references/format.md`。ユーザー提供 `example/sample.txt` の実 T3D を反映済み。
- C01〜C22: `catalog/generated/C01.json`〜`C22.json`。全 task md が `DONE`。
- M02〜M04: `catalog/generated/M02-mf.json`〜`M04-mf.json`。全 task md が `DONE`。
- ここまでの成果は commit `8faac81` (`Add node catalogs and T3D format spec`) に含まれる。

### 現在実行中

- T02 完了: `skill/references/mgjson.md` と `tasks/T02-mgjson-spec.md` を更新済み。
- M01 完了: `skill/references/mf-call.md`、task md、`INSTRUCTIONS-mf.md` を更新済み。
- T06 完了: 359/359ノードと82 MFを `skill/catalog/` に統合し、逆引き索引を生成済み。
- T05 完了: `skill/scripts/validate.py`。破損17パターン、正常graph、CLI exit codeを検証済み。
- T03/T04 完了: `build.py` / `parse.py`。通常・Comment・MF、typed/raw props、layout、
  file/stdin/stdout/clipboard、catalog無しparse、実sample、canonical round-tripを確認済み。
- T07 完了: `skill/SKILL.md`（159行）と `skill/agents/openai.yaml`。skill-creatorの
  `quick_validate.py` は `Skill is valid!`。
- T08 offline QA 完了: 7 fixture、実sample、MF、catalog無し、全JSON、skill validatorがOK。
  `tasks/verification-log.md` に全結果と手動fixtureを記録済み。残作業はEditor steps 1〜9のみ。

### 監査結果と注意

- 未完了: E01、T08。E01/T08 の Unreal Editor 操作だけはユーザー協働。
- `catalog/generated/*.json` は 26 ファイルすべて JSON syntax OK。
- `tools/qa_outputs.py` の候補20 classを照合し、明確な差分だった ViewProperty を
  `Property` / `InvProperty` の2出力へ修正した。他は無名出力、機能フラグ条件、または
  CustomOutput の `GetNumOutputs()` によるため候補表示のままで妥当。
- 一部 generated catalog の `class` に C++ prefix `U` が混入している
  （例: C08 の `/Script/Engine.UMaterialExpressionMaterialFunctionCall`）。T06 は manifest の
  module / class 名から runtime class path を正規化し、merged catalog に誤 prefix を残さない。
- T06 は既存章の省略フィールドを500件超警告したうえで補完する。型違反・重複・manifest
  不一致はエラー。全 `verified` は Editor確認前なので false。詳細は T06 実施メモ参照。
- validate.py は未検証classごとに warning を出す設計。MaterialFunctionCall は packaged
  function catalog の path が必須で、任意の未収載functionは Pin schema 不明のため error。
- T03試験中に parameter基底の継承props欠落を発見し、T06 mergeで `ParameterName` / `Group` /
  `SortPriority` を `is_parameter` classへ補完するよう修正・再生成した。
- clipboard試験は Windows PowerShell 経路で成功。現在のclipboardにはT08 step 1の
  Constant3Vector T3Dが入り、Material Editorの空白でCtrl+Vすれば最初の手動試験を開始できる。
- 実行環境では `python` が PATH から見えず、`py` に登録 interpreter もなかった。
  検証用 Python 3.12.11 を一時配置して全QAを行い、`.uv-python/` / `.uv-cache/` /
  `__pycache__` は最終QA後に削除済み。再開時はユーザー環境の `python` を使う。
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
