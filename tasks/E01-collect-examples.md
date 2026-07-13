# E01: 実機サンプル収集 [ユーザー協働 / 優先度A / 最初にやる]

status: TODO
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
- [ ] 上記9ファイル(最低でも01〜05)
- [ ] UEバージョン記録
