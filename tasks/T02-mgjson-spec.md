# T02: 中間フォーマット MGJSON 仕様書 [基盤 / 優先度A]

status: TODO
output: `skill/references/mgjson.md`
依存: なし

## 内容

AI⇔ツール間の中間フォーマット仕様を確定する。PLAN.md §3.2 の草案をベースに:

- nodes / links / pos の正式仕様(BNF程度の厳密さ)
- link構文: `"src[.出力名] -> dst.入力名"`。出力名省略時は第1出力。
  入力名はカタログの inputs[].name または prop_pins[].name
- props: カタログの props キーをそのまま使う。色は `[r,g,b]` or `[r,g,b,a]`、
  アセットは `/Game/...` パス文字列、enumは値名文字列
- Comment の包含指定(`"nodes": [...]` → build.py が枠サイズを計算)
- 未知ノードのエスケープハッチ: `"raw_props": {"プロパティ名": "T3D生値文字列"}`
  (カタログ未収載プロパティをそのまま通す)
- parse.py 出力時の規約: 位置は捨てる(`--keep-pos`でのみ保持)、
  デフォルト値と同じpropsは出さない、ID命名は `class略名+連番`
- MGJSONのバリデーションルール一覧(validate.pyの仕様を兼ねる)

## 完了条件
- [ ] 例が3つ以上(単純、テクスチャ+パラメータ、コメント付き)
- [ ] このmdだけでT03/T04/T05の入出力仕様が確定する
