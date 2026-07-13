# ノードカタログ抽出 — 共通手順(C系タスク用)

C01〜C系の全タスクはこの手順に従う。タスクファイル側には対象クラスと出力先だけ書いてある。

## 目的

UEソースから各 MaterialExpression クラスの「ピン構成・プロパティ・機能」を機械可読JSONにする。
このJSONは T3D 生成ツール(build.py)が **ピンの順序と名前** を決めるための正データになる。
特に inputs の順序と outputs の順序・名前は間違えると誤配線に直結するので最重要。

## 調査場所

- ヘッダ: `C:\work\unreal\UnrealEngine-release\Engine\Source\Runtime\Engine\Public\Materials\MaterialExpression<名前>.h`
  (無い場合は `Engine\Source\Runtime\Engine` 以下を `MaterialExpression<名前>.h` で検索)
- 実装: `C:\work\unreal\UnrealEngine-release\Engine\Source\Runtime\Engine\Private\Materials\MaterialExpressions.cpp`
  (大半のクラスはこの巨大ファイル内。個別cppの場合もある。`UMaterialExpression<名前>::` で grep)
- 確認すべき実装箇所:
  - コンストラクタ: `Outputs` 配列を操作しているか(していなければ出力は既定1本)
  - `GetInputName` オーバーライド: ピン表示名の変更
  - `GetInputs` / `GetInput` オーバーライド: 入力列挙の変更(宣言順と異なる場合)
  - `IsInputConnectionRequired` オーバーライド

## 出力

`catalog/generated/<タスクID>.json` に1ファイル(例: C01なら `catalog/generated/C01.json`)。
トップレベルは `{ "<クラス短名>": { ... }, ... }`。クラス短名 = `MaterialExpression` を除いた名前。

## スキーマ(例2つで全フィールドを示す)

```json
{
  "Add": {
    "class": "/Script/Engine.MaterialExpressionAdd",
    "header": "Materials/MaterialExpressionAdd.h",
    "desc": "A + B。float/vector対応、次元は大きい方に合わせられる",
    "inputs": [
      {"name": "A", "prop": "A", "required": false, "default_prop": "ConstA"},
      {"name": "B", "prop": "B", "required": false, "default_prop": "ConstB"}
    ],
    "prop_pins": [],
    "outputs": [{"name": ""}],
    "props": {
      "ConstA": {"type": "float", "default": 0.0},
      "ConstB": {"type": "float", "default": 1.0}
    },
    "notes": "",
    "verified": false
  },
  "TextureSample": {
    "class": "/Script/Engine.MaterialExpressionTextureSample",
    "header": "Materials/MaterialExpressionTextureSample.h",
    "desc": "テクスチャをサンプリング",
    "inputs": [
      {"name": "Coordinates", "prop": "Coordinates", "required": false, "default_prop": null,
       "note": "未接続時はTexCoord[ConstCoordinate]"},
      {"name": "Tex", "prop": "TextureObject", "required": false},
      {"name": "ApplyViewMipBias", "prop": "AutomaticViewMipBiasValue", "required": false}
    ],
    "prop_pins": [],
    "outputs": [
      {"name": "RGB", "mask": "RGB"},
      {"name": "R", "mask": "R"},
      {"name": "G", "mask": "G"},
      {"name": "B", "mask": "B"},
      {"name": "A", "mask": "A"}
    ],
    "props": {
      "Texture": {"type": "asset:Texture", "default": null},
      "SamplerType": {"type": "enum:EMaterialSamplerType", "default": "SAMPLERTYPE_Color"},
      "ConstCoordinate": {"type": "uint32", "default": 0},
      "MipValueMode": {"type": "enum:ETextureMipValueMode", "default": "TMVM_None"}
    },
    "notes": "MipValueModeによって入力ピンが増減する(TMVM_MipLevel等でMipValueピン追加)",
    "verified": false
  }
}
```

## 抽出ルール

1. **inputs**: `FExpressionInput` 型のUPROPERTYを **ヘッダの宣言順** に列挙。
   親クラスの入力(継承)が先(例: TextureSampleParameter2D は TextureSample の入力を継承)。
   - `name`: `GetInputName` オーバーライドがあればその戻り値、なければプロパティ名
   - `prop`: UPROPERTY名(T3Dでの接続プロパティ名)
   - `required`: UPROPERTY meta に `RequiredInput="false"` があれば false。無指定は true
   - `default_prop`: metaの `OverridingInputProperty` や ToolTip の "Defaults to 'ConstX'"
     から対応する定数プロパティ名。なければ省略か null
2. **prop_pins**: meta に `ShowAsInputPin="Primary"` または `"Advanced"` が付くUPROPERTY。
   `[{"name": "...", "prop": "...", "kind": "Primary|Advanced", "type": "float"}]`。
   これらは inputs の**後**に入力ピンとして並ぶ
3. **outputs**: cppコンストラクタで `Outputs` を操作していなければ `[{"name": ""}]`。
   `Outputs.Add(FExpressionOutput(...))` があればその **順序どおり** に name と
   mask指定(R/G/B/A/RGB/RGBA)を記録
4. **props**: エディタで編集する主要UPROPERTY(EditAnywhere / EditDefaultsOnly)を
   型とデフォルト値付きで。ピン化されるものも含む。Transient・内部用は除外。
   型表記: `float` / `int32` / `uint32` / `bool` / `FName` / `FString` / `FLinearColor` /
   `FVector2D` 等はそのまま、enumは `enum:E型名`、アセット参照は `asset:型名`
5. **desc**: そのノードが何をするか日本語で1行。ヘッダのコメント・ToolTipを参考に
6. **抽象クラス**(`UCLASS(abstract, ...)`)は `{"abstract": true, "class": "...", "desc": "..."}` のみ
7. **非推奨**(クラス名やUCLASSに Deprecated)は `"deprecated": true` を付けて他は簡略でよい
8. パラメータ系(`ParameterName` を持つ)は `"is_parameter": true` を付ける
9. 確信が持てない点は **推測で断定せず** `notes` に疑問として書く
10. `verified` は必ず `false`(実機検証タスクT08で昇格する)

## 完了条件(全タスク共通)

- [ ] タスク記載の全クラスがJSONに含まれる(abstract/deprecatedもフラグ付きで)
- [ ] inputs がヘッダ宣言順(継承分が先)
- [ ] 各クラスについて cpp のコンストラクタを確認し Outputs 上書き有無を反映した
- [ ] GetInputName オーバーライドの有無を確認した
- [ ] `python -m json.tool` でパースが通る
