# T06: catalog_merge.py — カタログ結合・lint [基盤 / 優先度B]

status: TODO
output: `skill/scripts/catalog_merge.py` + `skill/catalog/nodes.json`
依存: C系タスクが1個以上完了していること

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
