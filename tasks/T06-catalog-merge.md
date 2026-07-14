# T06: catalog_merge.py — カタログ結合・lint [基盤 / 優先度B]

status: DONE
output: `skill/scripts/catalog_merge.py` + `skill/catalog/nodes.json`
依存: C系タスクが1個以上完了していること

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: tasks/INSTRUCTIONS-catalog.md(スキーマ)、catalog/manifest.json、catalog/generated/ 配下
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

安価なAIワーカーが作った `catalog/generated/*.json` を1つの `catalog/nodes.json` に
結合し、品質チェックする。

- クラス名重複の検出(後勝ちではなくエラーにして手動解決)
- スキーマ準拠チェック(INSTRUCTIONS-catalog.md のスキーマ)
- **カバレッジ検査**: `catalog/manifest.json`(全359クラスの確定リスト)と突き合わせ、
  未収載クラス・マニフェストに無い謎クラスを列挙する
- 統計出力: 収載クラス数 / manifest比カバレッジ% / abstract / deprecated / verified数
- 逆引きインデックス `skill/references/nodes-index.md` の自動生成
  (desc から「やりたいこと→クラス名」の一覧表)

## 完了条件
- [x] generated/ にファイルを置いて実行すると nodes.json と nodes-index.md が更新される
- [x] スキーマ違反が具体的なメッセージで検出される

## 実施メモ

- 成果物: `skill/scripts/catalog_merge.py`、`skill/catalog/nodes.json`、
  `skill/catalog/functions.json`、`skill/references/nodes-index.md`
- manifest 359/359 クラスを収載。C19/C21 のキー表記差と C++ の `U` prefix を
  manifest に基づいて正規化した。MF は M02〜M04 の82件を統合した。
- 既存ワーカー成果物の省略可能フィールドは警告を残して安全な既定値で補完する。
  配列・bool・object 等の型違反、重複、manifest 不一致はエラーのまま扱う。
- 検証: 二重実行、JSON再読込、`py_compile`、359件カバレッジ、明示的な不正入力
  (`inputs: "not-array"`) が `expected array` になることを確認した。
- `tools/qa_outputs.py` の候補20件を確認し、明確な差分だった ViewProperty の
  2出力 (`Property` / `InvProperty`) を C18 と統合結果へ反映した。
- 全エントリはまだ Editor 未検証のため `verified: false` のまま。補完警告500件超は
  T08で優先的に確認する監査情報であり、`--quiet` では表示を抑止できる。
