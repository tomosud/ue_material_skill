# T02: 中間フォーマット MGJSON 仕様書 [基盤 / 優先度A]

status: TODO
output: `skill/references/mgjson.md`
依存: なし

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: PLAN.md の§3(アーキテクチャ)、catalog/generated/C01.json(propsの型表記の実例として)
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


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
