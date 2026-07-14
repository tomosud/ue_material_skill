# T01: T3D形式仕様書の作成 [基盤 / 優先度A]

status: TODO
output: `skill/references/format.md`
依存: なし(E01のサンプルがあれば精度向上)

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: PLAN.md の§2(調査結果)全体、examples/*.txt(あれば)
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

PLAN.md §2(調査結果)を、ツール実装者と「未知ノード対応」時のClaudeが参照できる
完全な仕様書に清書する。

含めるもの:
- T3D全体構造(Begin/End Object、2段書き、ネスト)
- MaterialGraphNode / MaterialExpression / Comment それぞれの必須・省略可プロパティ一覧
- CustomProperties Pin 行のフィールド仕様と最小セット、LinkedTo書式
- ペースト時に何が再構築されるか(PLAN §2.3の10項目)
- E01のサンプルがあれば実例を1つ添付(短いもの)

## 完了条件
- [ ] このmdだけを読んでbuild.py/parse.pyのT3D部分が実装できる情報量
- [ ] PLAN.mdのソース行番号参照を維持(検証可能性のため)
