# T04: parse.py — T3D → MGJSON 解析ツール [基盤 / 優先度A]

status: TODO
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
  - PinId→(ノード, ピン名/インデックス)の解決。カタログがあればピン名を復元、
    無くても `in0`/`out2` のようなインデックス表記で出力(カタログ非依存で動くこと)
  - props: Expressionブロックのプロパティのうち位置(MaterialExpressionEditorX/Y)、
    GUID類、Material=等の環境依存参照を除いたものを出力
  - `--keep-pos` で位置保持、`--stats` でノード数/接続数のみ
- 未知プロパティは `raw_props` に落とす(捨てない)

## 完了条件
- [ ] 実エディタのコピー(E01サンプル)を食わせてMGJSONが出る
- [ ] T3D 2,000トークン相当 → 100トークン以下のMGJSONになる(典型ケース)
- [ ] カタログ無しでも動作する(ピン名がインデックス表記になるだけ)
