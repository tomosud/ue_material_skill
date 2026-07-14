# Unreal Editor verification log

最終更新: 2026-07-14

## 現在の判定

- オフライン検証: **OK**
- Unreal Editor貼り付け検証: **WAITING USER**
- 対象ソース: UE 5.8 checkout
- 実際に使うEditorの正確なバージョン: **未記録**（Help > Aboutで記録すること）
- catalog `verified`: 全件 `false` のまま。Editor round-tripが通ったclassだけ昇格する。

`example/sample.txt` はユーザー提供の実Editor T3Dとして解析済みだが、要求されていたE01の
9種類別sampleとEditorバージョンは未収集である。従ってparse実入力の根拠には使えるが、
build生成物のCtrl+V成功を示すものではない。

## 自動検証結果

実行日: 2026-07-14 / Python 3.12.11 / 標準ライブラリ（skill validatorのみPyYAML）

| fixture | 自動検証 | T3D文字数 | node/link |
|---|---|---:|---:|
| 01 Constant3Vector | validate→build→parse→build→parse 完全一致 | 1,265 | 1 / 0 |
| 02 Constant×2→Multiply | 同上、両方向LinkedTo | 3,070 | 3 / 2 |
| 03 TextureSample.G→Multiply.A | 同上、Expression `OutputIndex=2` | 3,508 | 2 / 1 |
| 04 ScalarParameter | name/default/group保持 | 934 | 1 / 0 |
| 05 TextureSampleParameter2D | asset object path保持 | 2,499 | 1 / 0 |
| 06 Constant Value property Pin | link保持（Editor挙動は未確認） | 1,774 | 2 / 1 |
| 07 Comment + 2 nodes | bounds→包含nodes復元 | 2,546 | 2+1 comment / 1 |
| 08 `example/sample.txt` | 4 nodes / 3 internal links、再build完全一致 | — | 4 / 3 |
| MF `3ColorBlend` | FunctionInputs(0..3)、FunctionOutputs(0)、Outputs(0)生成 | 3,382 | 2 / 1 |

追加結果:

- `catalog_merge.py`: manifest 359/359、MF 82、二重実行OK。
- `py_compile`: catalog_merge / validate / build / parse 全てOK。
- generated + merged JSON: 28ファイル再読込OK。
- `validate.py`: 破損17パターンと正常graphを確認済み（T05実施メモ）。
- catalog無しparse: `inN`/`outN` linkで4 nodes / 3 links、raw props保持。
- clipboard: Windows PowerShellのSet-Clipboard→Get-Clipboard再読込OK。
- skill-creator `quick_validate.py`: `Skill is valid!`。

## Editor手動検証の実行方法

各fixtureのMGJSONを一時 `.json` に保存し、リポジトリルートで次を実行する。

```powershell
python skill/scripts/validate.py fixture.json
python skill/scripts/build.py fixture.json --to-clipboard
```

Material Editorの何もない所でCtrl+Vする。各試験後、結果、UEバージョン、症状、copy-back
T3Dとの差分を下表へ追記する。失敗時もfixtureを変えず、貼られたノードを選択してCtrl+Cし、
`python skill/scripts/parse.py --from-clipboard --keep-pos` のMGJSONを記録する。

| step | 状態 | Editorで確認すること |
|---:|---|---|
| 1 | WAITING | Constant3Vectorが1個貼られ、色が (0.2, 0.5, 0.9) |
| 2 | WAITING | Constant 2個からMultiply A/Bへの2接続 |
| 3 | WAITING | TextureSampleのG（3番目の出力）がMultiply.Aへ接続 |
| 4 | WAITING | ScalarParameter name=Strength、default=0.75、Group=Controls |
| 5 | WAITING | TextureSampleParameter2DとDefaultTexture参照 |
| 6 | WAITING | ConstantのValue property Pinが再構築されるか。接続可否も記録 |
| 7 | WAITING | Comment枠が2ノードを80px marginで包含し、移動がgroup動作 |
| 8 | WAITING | 貼った選択をcopy→parse→build→再pasteして同じgraph |
| 9 | WAITING | 現build.pyの最小Pin fieldで受理されるか。必要fieldがあればformat.mdへ反映 |

### Fixture 01

```json
{"nodes":{"color":{"class":"Constant3Vector","props":{"Constant":[0.2,0.5,0.9]}}}}
```

### Fixture 02

```json
{"nodes":{"a":{"class":"Constant","props":{"R":0.25}},"b":{"class":"Constant","props":{"R":2.0}},"mul":{"class":"Multiply"}},"links":["a -> mul.A","b -> mul.B"]}
```

### Fixture 03

```json
{"nodes":{"tex":{"class":"TextureSample"},"mul":{"class":"Multiply"}},"links":["tex.G -> mul.A"]}
```

### Fixture 04

```json
{"nodes":{"strength":{"class":"ScalarParameter","props":{"ParameterName":"Strength","DefaultValue":0.75,"Group":"Controls"}}}}
```

### Fixture 05

```json
{"nodes":{"tex":{"class":"TextureSampleParameter2D","props":{"ParameterName":"BaseTexture","Texture":"/Engine/EngineResources/DefaultTexture.DefaultTexture"}}}}
```

### Fixture 06

```json
{"nodes":{"driver":{"class":"Constant","props":{"R":0.8}},"target":{"class":"Constant"}},"links":["driver -> target.Value"]}
```

### Fixture 07

```json
{"nodes":{"a":{"class":"Constant","props":{"R":0.4}},"b":{"class":"OneMinus"},"group":{"class":"Comment","props":{"Text":"Invert","nodes":["a","b"],"CommentColor":[0.1,0.2,0.5,1.0]}}},"links":["a -> b.Input"]}
```

## 昇格規則

1. stepごとにpaste後の選択をcopy-backし、parse結果とfixtureを比較する。
2. class、Pin順、接続、typed propertyが一致したclassだけ merged catalogで
   `verified: true` にする。generated source側にも同じ変更を反映し、merge再実行で保持する。
3. MFはasset path、input/output順、型suffixまで確認できたentryだけ昇格する。
4. 差分が出た場合は catalog/build/parse/format.md の順で原因を直し、同じfixtureを再試験する。
5. step 1〜8 OK、step 9の最小field結果をformat.mdへ反映した時点でT08をDONEにする。
