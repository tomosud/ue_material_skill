# Unreal Editor verification log

最終更新: 2026-07-14

## 現在の判定

- オフライン検証: **OK**
- Unreal Editor貼り付け検証: **OK（steps 1〜9）**
- 対象ソース: UE 5.8 checkout
- 実際に使うEditor: **Unreal Editor 5.8.0-55116800+++UE5+Release-5.8**
- OS表示: Windows 11 (25H2) [10.0.26200.8655] (x86_64)
- catalog `verified`: `Constant` / `OneMinus` / `Comment`を実round-tripで昇格し、
  `NamedRerouteDeclaration` / `NamedRerouteUsage`を実機copyで昇格。

`example/sample.txt`に加え、E01の01〜09をすべて実Editor T3Dとして収集済み。
07の実測でMaterialFunction pathを修正し、08でNamedRerouteの`VariableGuid`、09でCustomの
`ShowCode`をカタログへ補完した。

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
- E01 `02-math-chain.txt`: 異なるConstant間の重複PinIdをowner名との複合keyで解決し、
  Constant×2 → Multiply → Addの3接続を復元。

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
| 1 | **OK (2026-07-14)** | Constant3Vectorが1個貼られ、色が (0.2, 0.5, 0.9) |
| 2 | **OK (2026-07-14)** | Constant 2個からMultiply A/Bへの2接続 |
| 3 | **OK (2026-07-14)** | TextureSampleのG（3番目の出力）がMultiply.Aへ接続 |
| 4 | **OK (2026-07-14)** | ScalarParameter name=Strength、default=0.75、Group=Controls |
| 5 | **OK (2026-07-14)** | TextureSampleParameter2DとDefaultTexture参照 |
| 6 | **OK (2026-07-14)** | ConstantのValue property Pinが再構築され、接続も保持 |
| 7 | **OK (2026-07-14)** | Comment枠が2ノードを80px marginで包含 |
| 8 | **OK (2026-07-14)** | 実copy→parse→build→再pasteで同じgraph |
| 9 | **OK (2026-07-14)** | `PinType.*`全省略で値・A/B接続が完全復元。format/buildへ反映 |

### 手動結果 01

- 結果: **OK**
- 確認画像: Constant3Vector 1個がMaterial Editorへ貼り付けられた。
- 値: X/R=0.2、Y/G=0.5、Z/B=0.9。プレビュー色も一致。
- Root未接続: step 1の想定どおり（Root接続は生成対象外）。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 02

- 結果: **OK**
- Constant 0.25の出力がMultiply.Aへ接続された。
- Constant 2.0の出力がMultiply.Bへ接続された。
- 2本ともPin接続と値がfixtureに一致。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 03

- 結果: **OK**
- TextureSampleの緑色G出力（output index 2）がMultiply.Aへ接続された。
- RGB/R/G/B/A/RGBAの全出力順と選択出力がfixtureに一致。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 04

- 結果: **OK**
- Parameter Name=`Strength`、Default Value=`0.75`、Group=`Controls`をDetailsで確認。
- Sort Priorityはcatalog補完既定値どおり`32`。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 05

- 結果: **OK**
- TextureSampleParameter2DのParameter Name=`BaseTexture`を確認。
- `/Engine/EngineResources/DefaultTexture.DefaultTexture` が`None`にならず解決され、
  Detailsのasset欄とnode previewへDefaultTextureが表示された。
- catalogの`asset:UTexture`から生成した`/Script/Engine.Texture` object referenceはUE 5.8で有効。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 06

- 結果: **OK**
- source Constant R=`0.8`の出力からtarget Constantの`Value` property Pinへ接続された。
- paste後もValue Pinが存在し、リンクは削除されなかった。
- ShowAsInputPin系を通常inputsの後へ出すbuild規約がUE 5.8で機能することを確認。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 07

- 結果: **OK**
- 青系Comment枠、Text=`Invert`、Constant 0.4、OneMinus、内部linkを画像で確認。
- 2ノードは枠内に収まり、生成規約の80px margin相当の余白が保持された。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### Step 08 進行メモ

- 最初の実copy-backは2 nodes / 1 Comment / 1 link、typed props、raw props 0で解析成功。
- EditorがComment geometryを微調整し、従来の80px完全一致判定では包含`nodes`へ戻らず
  `SizeX=700` / `SizeY=280`の自由枠になった。
- `parse.py` を修正し、各辺0〜200pxのtight enclosing frameを包含Commentと判定するようにした。
  生成fixtureのparseで`nodes=[const1,oneminus1]`へ戻ることを再確認済み。
- 修正版で実clipboardを再取得し、次のcanonical MGJSONへ正常変換した（error 0 / raw props 0）。
  `Constant(R=0.4)`、`OneMinus`、包含Comment `Invert`、内部link 1本。
- Commentは`nodes=[const1,oneminus1]`へ復元され、SizeX/SizeY自由枠は除去された。
- 再buildしたT3Dをclipboardへ格納済み。ユーザーの再paste結果待ち。

### 手動結果 08

- 結果: **OK**
- 元graphと再paste graphを同一画面で比較し、Comment text/color/bounds、Constant 0.4、
  OneMinus、内部linkが一致した。
- 実copy-backで発見したComment geometry差は修正版parserで包含`nodes`へ正規化された。
- `Constant`、`OneMinus`、`Comment`は実round-trip確認済み。catalog verified昇格対象。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

### 手動結果 09

- 結果: **OK**
- Constant×2 → Multiplyの全7 Pinから`PinType.*`を完全に除いたT3Dをpasteした。
- Constant値0.25 / 2.0、Multiply.A / Bへの2接続が完全に復元された。
- build.pyはdata Pinの`PinType.PinCategory`を出さない最小形式へ変更した。
- format.mdにUE 5.8.0-55116800実機結果を追記した。
- 再QA: py_compile、catalog merge、PinType field 0、通常/Comment round-trip、
  verified class一覧を確認して`FINAL_QA_OK`。
- UEバージョン: 5.8.0-55116800+++UE5+Release-5.8。

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
