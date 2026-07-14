# 外部AIへの作業引き渡しガイド

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
