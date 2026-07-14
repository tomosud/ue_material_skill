# T04: parse.py — T3D → MGJSON 解析ツール [基盤 / 優先度A]

status: DONE
output: `skill/scripts/parse.py`
依存: T01, T02

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: skill/references/format.md、skill/references/mgjson.md、examples/*.txt(実T3Dサンプル)
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

エディタでコピーされたT3Dテキストを読み、コンパクトなMGJSONに要約する。
**T3Dを会話コンテキストに入れないための入口**なので、出力の小ささを最優先。

- 入力: `--from-clipboard`(PowerShell `Get-Clipboard -Raw`。既定)、ファイル、stdin
- 出力: MGJSON(stdout)
- 実装:
  - Begin/End Objectのネストパーサ(行指向で十分)
  - ノード名→短ID変換(`MaterialGraphNode_5` → `mul1` 等、クラス名から採番)
  - 接続の抽出: CustomProperties Pin の LinkedTo から(Expression入力プロパティは使わない)
  - (ノード名, PinId)→(ノード, ピン名/インデックス)の解決。カタログがあればピン名を復元、
    無くても `in0`/`out2` のようなインデックス表記で出力(カタログ非依存で動くこと)
  - props: Expressionブロックのプロパティのうち位置(MaterialExpressionEditorX/Y)、
    GUID類、Material=等の環境依存参照を除いたものを出力
  - `--keep-pos` で位置保持、`--stats` でノード数/接続数のみ
- 未知プロパティは `raw_props` に落とす(捨てない)

## 完了条件
- [x] 実エディタのコピー(E01サンプル)を食わせてMGJSONが出る
- [x] T3D 2,000トークン相当 → 100トークン以下のMGJSONになる(典型ケース)
- [x] カタログ無しでも動作する(ピン名がインデックス表記になるだけ)

## 実施メモ

- 成果物: `skill/scripts/parse.py`。clipboard（既定）/ file / stdinからT3Dを読み、compact
  MGJSONをstdoutへ出す。`--keep-pos`、`--stats`、`--no-catalog` を実装した。
- Begin/End Object stack、quoted/parenthesized value、CustomProperties Pin、LinkedToの両方向
  dedupe、Root除外、class alias採番、typed default省略、unknown raw_props保持を実装した。
- Commentは生成規約と一致するboundsなら `nodes` 包含へ戻し、自由枠だけsize/posを保持する。
- `example/sample.txt`（実Editor T3D）は4 node / 3 internal linkとして解析され、出力MGJSONを
  validate.pyへ渡してerror 0を確認した。clipboardからの同サイクルも確認済み。
- カタログ無しでは link Pinが `in0` / `outN` になり、unknown class/raw propsを捨てずに動作。
- compactness例: 3ノードT3D 3,070文字 → MGJSON 184文字（概算46 token）。5ノードComment
  付き7,254文字 → 585文字。canonical round-trip完全一致、MF round-tripも確認した。
- E01全件監査で、UEが異なるConstantノードへ同一PinIdを再利用した実sampleを確認した。
  PinId単独の表を`(owner node name, PinId)`複合キーへ修正し、02の3接続をすべて復元する
  回帰確認を追加した。これは当初のT01解析規約とも一致する。
