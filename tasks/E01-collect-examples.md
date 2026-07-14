# E01: 実機サンプル収集 [ユーザー協働 / 優先度A / 最初にやる]

status: DONE（01〜09全件収集済み）
output: `examples/*.txt`(生T3D)
依存: なし。**他タスクの精度を上げるので最優先**

## 内容

ユーザーがUnreal EditorのMaterial Editorでノードをコピーし、テキストファイルに保存する。
(クリップボードから `Get-Clipboard -Raw > examples/xxx.txt` でも可)

### 依頼するサンプル(各1ファイル)

| ファイル | エディタで選択してコピーするもの |
|---|---|
| `01-single-constant.txt` | Constant3Vector 1個(色を変えておく) |
| `02-math-chain.txt` | Constant×2 → Multiply → Add あたりの接続済み4ノード |
| `03-texture.txt` | TexCoord → TextureSample(テクスチャ割当済み)の2ノード |
| `04-texture-mask.txt` | TextureSampleのGピンから何かに接続したもの(出力ピン順の確認用) |
| `05-parameters.txt` | ScalarParameter + VectorParameter(名前/Group/デフォルト値設定済み) |
| `06-comment.txt` | コメント枠+中に2ノード |
| `07-function-call.txt` | 適当なMaterialFunction呼び出しノード1個(例: BlendAngleCorrectedNormals) |
| `08-named-reroute.txt` | NamedReroute宣言+使用のペア |
| `09-custom.txt` | Customノード(入力2個定義したもの) |

あわせて **UEエディタの正確なバージョン**(Help > About)をREADMEかファイル名に記録。

## 完了条件
- [x] 01〜09の全9サンプル収集
- [x] UEバージョン記録

## 実施メモ

- ユーザー提供 `example/sample.txt` を受領。Root + SubstrateSimpleClearCoatBSDF + Constant +
  ScalarParameter 2個を含む実T3Dで、T01/T04の仕様・解析検証に使用した。
- Editorバージョンはユーザー画像から
  `5.8.0-55116800+++UE5+Release-5.8`（Windows 11 25H2 build 26200.8655）と確認した。
- 指定の01〜09別sampleではないため、引き続き完了扱いにはしない。
- 2026-07-14、`01-single-constant.txt` 収集開始。最初のクリップボードは
  `MaterialExpressionConstant`（Scalar Constant、R=0.0）だったが、指定は
  `Constant3Vector` のため保存せず、ユーザーへ再コピーを依頼中。
- 再コピーで `MaterialExpressionConstant3Vector` を確認し、実T3Dを
  `examples/01-single-constant.txt` に保存した。最低要件01〜05のうち1件完了、次は02待ち。
- 初回保存分は既定色（0,0,0）だったため、ユーザー指摘を受けて色変更済みの再コピー
  （RGB=`1.0,0.644811,0.532869`）へ差し替えた。01の「色を変えておく」を満たす。
- `examples/02-math-chain.txt` を保存。Constant 2個（0、5）→ Multiply A/B → Add Aの
  4ノード・3接続を実T3Dで確認した。最低要件01〜05のうち2件完了、次は03待ち。
- 03の最初のコピーは TexCoord → `TextureSampleParameter2D`（テクスチャ割当・UV接続済み）
  だった。指定の通常 `TextureSample` ではなく、05のParameter例とも重複するため未保存。
  通常Texture Sampleでの再コピー待ち。
- 03再コピーで通常の `MaterialExpressionTextureSample`、割り当てTexture2D、
  TexCoord→UVs接続を確認し、`examples/03-texture.txt` に保存した。
  最低要件01〜05のうち3件完了、次は04待ち。
- `examples/04-texture-mask.txt` を保存。TextureSampleのG出力からMultiply Aへの接続を
  ピンIDと `OutputIndex=2,Mask=1,MaskG=1` の双方で確認した。
  最低要件01〜05のうち4件完了、次は05待ち。
- `examples/05-parameters.txt` を保存。ScalarParameterは
  `Strength` / Group `Controls` / Default `0.75`、VectorParameterは
  `TintColor` / Group `Controls` / 非黒色Defaultを確認した。最低要件01〜05を完了。
- 任意追加06〜09の収集を開始。06は検証済みMGJSONから Constant→OneMinus と青い
  `Comment Sample` 枠を生成してクリップボードへ配置済み。UE貼り付け後の実機コピー返却待ち。
- 06の実機コピーを `parse.py --keep-pos --stats` で確認し、2 nodes / 1 Comment / 1 link、
  unknown 0、raw props 0。`examples/06-comment.txt` に生T3Dを保存した。次は07。
- 07はカタログ収載済み `BlendAngleCorrectedNormals` のMaterialFunctionCallを生成。
  validateは既定の未実機検証・asset existence未確認warning 2件のみで成功し、正確なasset pathと
  BaseNormal / AdditionalNormal / Result Pinを含む1ノードをクリップボードへ配置。実機返却待ち。
- 07の貼り付け結果はUE側でfunction assetを解決できず `Unspecified Function` になった。
  返却clipboardも生T3Dではなく同名のプレーンテキストだったため未保存。生成物の反復貼り付けは
  中止し、ユーザーが利用可能な任意Material Functionを手で配置・コピーする方式へ切り替えた。
- 手動配置された `BlendAngleCorrectedNormals` を受領。parse結果は1 node、unknown/raw 0で、
  実pathはカタログ想定と異なる`Engine_MaterialFunctions02/Utility`だった。生T3Dを
  `examples/07-function-call.txt` に保存し、カタログ元・仕様例を実測値へ修正した。次は08。
- 08はUE 5.8ソースの`Convert to Named Reroute`処理を確認し、通常Rerouteを宣言＋使用へ
  変換する手動作成手順をユーザーへ案内。宣言・使用ペアのコピー返却待ち。
- 08実機コピーを受領。NamedRerouteDeclaration `test` とUsageの共有GUID一致を確認し、
  `examples/08-named-reroute.txt` に保存。宣言側の未収載`VariableGuid`をC08へ追加し、
  宣言・使用の両classを実機検証済みへ更新した。次は09。
- 09実機コピーを受領。Custom 1 node、`Code="return A + B;"`、入力A/B、Output Pinを確認し、
  `examples/09-custom.txt` に生T3Dを保存。`ShowCode: bool`をC08へ追加した。索引付きの
  `Inputs(0)` / `Inputs(1)`は現MGJSON仕様のescape hatchである`raw_props`へ可逆保持される。
  これで任意追加分を含む01〜09を全件収集した。
