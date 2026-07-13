# T05: validate.py — MGJSON検証ツール [基盤 / 優先度A]

status: TODO
output: `skill/scripts/validate.py`
依存: T02(仕様)、カタログ

## 内容

Claudeが書いたMGJSONをbuild前に検証し、間違いを**具体的な修正案付き**で指摘する。

チェック項目:
- JSON構文、必須キー、ID重複
- クラス名がカタログに存在するか(近い名前をサジェスト: 例 `Lerp` → `LinearInterpolate`)
- linkの参照先ノードID・ピン名の存在(ピン名もサジェスト)
- 1入力ピンに複数リンク(禁止)、出力→出力 / 入力→入力の誤接続
- propsのキーがカタログにあるか、enum値が正しいか
- 循環接続の検出(警告)
- abstract/deprecatedクラスの使用(エラー/警告)
- 孤立ノードの警告

出力: 人間可読のエラーリスト(行番号相当の位置情報付き)+ exit code

## 完了条件
- [ ] 意図的に壊したMGJSON 10パターンで全て適切なメッセージが出る
- [ ] build.pyから関数として呼べる構造(モジュール分離)
