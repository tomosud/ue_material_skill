# T06: catalog_merge.py — カタログ結合・lint [基盤 / 優先度B]

status: TODO
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
- [ ] generated/ にファイルを置いて実行すると nodes.json と nodes-index.md が更新される
- [ ] スキーマ違反が具体的なメッセージで検出される
