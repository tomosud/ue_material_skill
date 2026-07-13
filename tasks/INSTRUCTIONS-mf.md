# エンジン組み込みMaterialFunction ナレッジ化 — 共通手順(M02〜M04用)

## 背景と注意

- この環境のUEソースチェックアウトには `Engine/Content` が**無い**ため、MFのuasset実体は
  参照できない。**モデル知識(UEドキュメント・一般知識)ベース**で書き、全て `verified: false`
- **確信が持てないMFは書かない方がよい**(存在しない関数名・間違ったピン名は実害になる)。
  確度の高い有名どころだけでよい
- アセットパスは通常 `/Engine/Functions/Engine_MaterialFunctions01/<カテゴリ>/<名前>.<名前>`
  または `...Functions02/Functions03`。パスに自信が無ければ `"path_uncertain": true` を付ける

## 出力スキーマ

`catalog/generated/<タスクID>-mf.json`:

```json
{
  "BlendAngleCorrectedNormals": {
    "path": "/Engine/Functions/Engine_MaterialFunctions01/Texturing/BlendAngleCorrectedNormals.BlendAngleCorrectedNormals",
    "desc": "2つのノーマルマップを角度補正付きで合成する",
    "inputs": [
      {"name": "BaseNormal", "type": "V3"},
      {"name": "AdditionalNormal", "type": "V3"}
    ],
    "outputs": [{"name": "Result", "type": "V3"}],
    "usage": "ディテールノーマルの重ね合わせの定番",
    "verified": false,
    "path_uncertain": false
  }
}
```

type表記: S=Scalar, V2/V3/V4=Vector, T2d=Texture Object, B=Bool, MA=MaterialAttributes

## 各エントリに書くこと

- desc: 何をする関数か(日本語1行)
- inputs/outputs: ピン名と型(**エディタ表示名**。順序は分かる範囲で)
- usage: いつ使うか・定番の組み合わせ(1行)
- 自信の無いフィールドは省略してよい(嘘を書くより欠落がまし)

## 完了条件(共通)

- [ ] JSONパースが通る
- [ ] 全エントリ verified: false
- [ ] 確度の低い関数を無理に含めていない
