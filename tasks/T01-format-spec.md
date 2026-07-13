# T01: T3D形式仕様書の作成 [基盤 / 優先度A]

status: TODO
output: `skill/references/format.md`
依存: なし(E01のサンプルがあれば精度向上)

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
