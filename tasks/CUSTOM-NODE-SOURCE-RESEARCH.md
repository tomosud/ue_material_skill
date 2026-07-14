# UE 5.8 Customノード ソース調査

調査日: 2026-07-14  
対象: Unreal Engine 5.8.0-55116800 / `UE5/Release-5.8`  
参照source root: `C:\work\unreal\UnrealEngine-release`

## 目次

1. [結論](#結論)
2. [Customコードが置かれる場所](#customコードが置かれる場所)
3. [利用できる関数の実用分類](#利用できる関数の実用分類)
4. [入力と自動生成引数](#入力と自動生成引数)
5. [SceneTexture専用構文](#scenetexture専用構文)
6. [Additional Outputs、Defines、Includes](#additional-outputsdefinesincludes)
7. [旧translatorと新MIR経路の差](#旧translatorと新mir経路の差)
8. [失敗しやすい点](#失敗しやすい点)
9. [MGJSON・validatorへの実装要求](#mgjsonvalidatorへの実装要求)
10. [確認用fixture案](#確認用fixture案)
11. [参照したsource](#参照したsource)

## 結論

Customノード内で使えるものは、固定された一つの「UE Custom関数一覧」ではない。実際の可視範囲は次の合成になる。

1. 対象shader modelで使えるHLSL組み込み関数。
2. `MaterialTemplate.ush`のCustom関数挿入位置より前に宣言された型、関数、macro。
3. Custom入力から自動生成される値、texture、sampler。
4. `Include File Paths`から読み込んだプロジェクト固有`.ush`の宣言。

したがって、skillやcatalogでEngine private shaderの全関数を「対応済みAPI」と列挙してはいけない。技術的に見えても、material domain、shader stage、platform、feature define、宣言順、UE versionで使用可否が変わる。

実用上は次の三段階で扱うのが安全である。

| レベル | 対象 | 扱い |
|---|---|---|
| A: 推奨 | 標準HLSL、明示的な数値入力、texture入力と自動sampler、自己管理する`/Project/*.ush` | 通常生成に使用してよい |
| B: 条件付き | SceneTexture専用構文、pixel derivative、stage依存処理 | domain/stage/platformを検査して使う |
| C: Engine内部 | `Parameters`の直接field、`View`、`GetPrimitiveData`などEngine private helper | UE version固定・実機compile確認がある場合だけ |

Custom Expressionは`UMaterialExpressionCustomOutput`派生ノードとは別物である。この文書の対象は`UMaterialExpressionCustom`だけである。

## Customコードが置かれる場所

Customの`Code`は、shader sourceへそのまま式置換されるのではない。UEが生成する関数の本文になる。

旧translatorの概形:

```hlsl
MaterialFloat3 CustomExpression0(
    FMaterialPixelParameters Parameters,
    MaterialFloat3 A,
    Texture2D Tex,
    SamplerState TexSampler)
{
    // Custom.Code
}
```

新Material IR経路の概形:

```hlsl
float3 C5_MyCustom(
    FMaterialPixelParameters Parameters,
    float3 A,
    Texture2D Tex,
    SamplerState TexSampler)
{
    // Custom.Code
}
```

新経路は使用stageごとにvertex版またはpixel版を生成する。computeはpixel parameter型を使う。旧経路もvertex shader frequencyでは`FMaterialVertexParameters`、それ以外では`FMaterialPixelParameters`を渡す。

生成関数は`MaterialTemplate.ush`の`%{uniform_material_expressions}`または`%{custom_functions}`へ入り、挿入位置は同ファイルの約3632～3636行である。従って、その位置より後で初めて定義される関数は、forward declarationがなければCustomから呼べるとは限らない。

`Code`は関数本文なので、通常のfree functionを本文中に定義することはできない。複数Customで再利用するhelperは`.ush`へ置き、`Include File Paths`からincludeする。

## 利用できる関数の実用分類

### A1. 標準HLSL組み込み

次は最も移植しやすい。引数の型と対象shader modelが許す範囲で使用する。

| 分類 | 代表関数 |
|---|---|
| scalar/vector算術 | `abs`, `min`, `max`, `clamp`, `saturate`, `sign` |
| 補間・閾値 | `lerp`, `step`, `smoothstep` |
| 端数・丸め | `frac`, `fmod`, `floor`, `ceil`, `round`, `trunc` |
| vector | `dot`, `cross`, `length`, `distance`, `normalize`, `reflect`, `refract` |
| 指数・対数 | `sqrt`, `rsqrt`, `pow`, `exp`, `exp2`, `log`, `log2` |
| 三角関数 | `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2` |
| 変換・行列 | `mul`, `transpose` |
| pixel derivative | `ddx`, `ddy`, `fwidth` |

`ddx`、`ddy`、`fwidth`はpixel-capableな経路だけを前提とし、vertexで使わない。Nanite/compute等ではUE側の派生値処理もあるため、全platform共通とはみなさない。

安全な例:

```hlsl
float3 N = normalize(InputNormal);
float Facing = saturate(dot(N, normalize(ViewDir)));
return lerp(ColorA, ColorB, Facing);
```

### A2. texture入力用helper

`MaterialTemplate.ush`は`SceneTexturesCommon.ush`を通して`Common.ush`を読み込む。`Common.ush`には次のsampling wrapperが定義され、Customのtexture入力と組み合わせられる。

| texture型 | 通常 | 明示LOD | bias | gradient |
|---|---|---|---|---|
| `Texture2D` | `Texture2DSample` | `Texture2DSampleLevel` | `Texture2DSampleBias` | `Texture2DSampleGrad` |
| `Texture3D` | `Texture3DSample` | `Texture3DSampleLevel` | `Texture3DSampleBias` | `Texture3DSampleGrad` |
| `TextureCube` | `TextureCubeSample` | `TextureCubeSampleLevel` | `TextureCubeSampleBias` | `TextureCubeSampleGrad` |
| `Texture2DArray` | `Texture2DArraySample` | `Texture2DArraySampleLevel` | `Texture2DArraySampleBias` | `Texture2DArraySampleGrad` |
| `TextureCubeArray` | `TextureCubeArraySample` | `TextureCubeArraySampleLevel` | `TextureCubeArraySampleBias` | `TextureCubeArraySampleGrad` |
| `TextureExternal` | `TextureExternalSample` | `TextureExternalSampleLevel` | ― | `TextureExternalSampleGrad` |

入力名が`Tex`なら、UEは`Tex`に加えて`TexSampler`を自動生成する。

```hlsl
return Texture2DSample(Tex, TexSampler, UV);
```

`Tex.Sample(TexSampler, UV)`を直接書くより、UEのwrapperを使う方がplatform差とmaterial precision aliasに追従しやすい。

### A3. 自己管理するinclude関数

再利用関数の第一選択。プロジェクトの`<PROJECT>/Shaders`が存在すると、Engine起動時に`/Project`へvirtual shader directory mappingされる。

Custom設定:

```text
IncludeFilePaths[0] = /Project/Material/MyMaterialLib.ush
```

`.ush`側:

```hlsl
#ifndef MYPROJECT_MATERIAL_LIB
#define MYPROJECT_MATERIAL_LIB

float3 MyProject_AdjustColor(float3 C, float Strength)
{
    return lerp(C, saturate(C * C), Strength);
}

#endif
```

Custom側:

```hlsl
return MyProject_AdjustColor(Color, Strength);
```

filesystem絶対pathではなくvirtual shader pathを使う。plugin shaderの場合は、plugin/module側が`AddShaderSourceDirectoryMapping`で登録したvirtual pathを使う。include guardとプロジェクト固有prefixを付ける。

### B1. SceneTexture helper

source上、Customから直接使うための主要な入口は次である。

```hlsl
GetDefaultSceneTextureUV(Parameters, SceneTextureId)
SceneTextureFetchFunc(Parameters, SceneTextureId, PixelOffset)
SceneTextureFetch(SceneTextureId, PixelOffset)
SceneTextureLookup(Parameters, UV, SceneTextureId, bFiltered)
```

ただしSceneTextureの有効性はmaterial domain、mobile/deferred、translucency、post process等で分岐する。特に「関数名が見える」ことと「そのmaterialで有効な値が返る」ことは同義ではない。

### C1. `Parameters`とEngine private helper

挿入位置より前に、次のoverloadがsource上存在する。

```hlsl
GetPrimitiveData(Parameters)
GetLocalToWorld3x3(Parameters)
GetWorldPosition(Parameters)
GetTranslatedWorldPosition(Parameters)
GetScreenPosition(Parameters)
GetSceneTextureUV(Parameters)
GetViewportUV(Parameters)
GetObjectWorldPosition(Parameters)
```

`FMaterialPixelParameters`には`VertexColor`、`WorldNormal`、`WorldTangent`、`CameraVector`、`SvPosition`、`ScreenPosition`、`ViewBufferUV`、`TwoSidedSign`、`TangentToWorld`、world position群、`PerInstanceRandom`、`PrimitiveId`等がある。vertex版にもworld/local position、tangent basis、pre-skinned値、vertex color、TexCoords等がある。

調査した5.8 sourceでCustom挿入位置より前に見える代表的な内部helperは次の通り。これは利用可能性の調査結果であり、推奨allowlistではない。

| source | 代表symbol | 条件・注意 |
|---|---|---|
| `MaterialTemplate.ush` | `GetPrimitiveData`, `GetLocalToWorld3x3` | primitive/instance dataとvertex factory条件に依存 |
| `MaterialTemplate.ush` | `GetWorldPosition`, `GetTranslatedWorldPosition`, `GetObjectWorldPosition` | LWC型とcamera-relative座標を区別する |
| `MaterialTemplate.ush` | `GetScreenPosition`, `GetSceneTextureUV`, `GetViewportUV` | vertex/pixel overloadで意味と利用可能値が異なる |
| `Random.ush` | `PseudoRandom`, `RandFast`, `RandBBSfloat` | Engine private。実装・品質・seed規約を固定APIとみなさない |
| `SobolRandom.ush` | `SobolPixel`, `SobolIndex`, `SobolIndexToUniformUnitSquare` | sampling用途の内部helper |
| `MonteCarlo.ush` | `Hammersley`, `Hammersley16` | sampling用途の内部helper |
| `ColorSpace.ush` | `LinearRGB_2_XYZ`, `XYZ_2_LinearRGB`, `LinearRGB_2_HSV`, `HSV_2_LinearRGB`, `LinearRGB_2_YCoCg`, `YCoCg_2_LinearRGB` | UE working color spaceや命名の意味を確認する |
| `BlueNoiseCommon.ush` | `GetBlueNoiseScalar`, `GetBlueNoiseVec2`, `GetBlueNoiseDitheredCoverage` | 対応texture、dimension、screen coordinate、frame indexが必要 |

しかし、多くのfieldはcompile defineで条件付きであり、5.8 source内にも互換用・将来削除予定の注記がある。AIが通常生成するコードでは、必要値を対応Material Expressionから明示入力する。`Parameters`直読みは、UE 5.8固定の高度なescape hatchとして扱う。

同様に、`MaterialTemplate.ush`がincludeする`/Engine/Private/*.ush`の関数群、`View` uniform、内部macroは公開互換APIではない。catalogの「利用可能関数」に自動収録して安全扱いしない。

## 入力と自動生成引数

旧translatorが明示的に受け付けるCustom入力型は次である。

| 接続型 | Custom内の引数 |
|---|---|
| float1～4 | `MaterialFloat`～`MaterialFloat4` |
| LWC scalar/vector2～4 | demote済み`float[N] Name`とrawの`FWS* LWCName` |
| Texture2D | `Texture2D Name`, `SamplerState NameSampler` |
| TextureCube | `TextureCube Name`, `SamplerState NameSampler` |
| Texture2DArray | `Texture2DArray Name`, `SamplerState NameSampler` |
| TextureCubeArray | `TextureCubeArray Name`, `SamplerState NameSampler` |
| TextureExternal | `TextureExternal Name`, `SamplerState NameSampler` |
| VolumeTexture | `Texture3D Name`, `SamplerState NameSampler` |
| TextureCollection | `FResourceCollection Name` |

その他の型は旧経路で`Bad type ... for ... input`になる。新MIR経路は接続値の`MIR::FType`からparameterを作るが、旧経路との共通互換範囲を基準にする。

名前付き入力は接続必須である。未接続なら`Custom material ... missing input ...`になる。名前なし入力は引数から除外される。

LWC入力では`Name`は通常floatへdemoteした互換値、`LWCName`はraw world-space型である。単純なCustomは`Name`を使えるが、大規模world座標の精度を保持する処理はLWC helperと`LWCName`を理解して書く必要がある。

## SceneTexture専用構文

Custom入力が`SceneTexture`または`UserSceneTexture`のoutput 0へ直結している場合、UEはHLSL tokenを解析して次を置換する。

```hlsl
SceneInput.ID
```

は接続先の`PPI_*`または`PPIUser_*`へ置換される。

```hlsl
SceneInput.Fetch(1, -1)
```

は概ね次へ置換される。

```hlsl
SceneTextureFetchFunc(Parameters, PPI_..., 1, -1)
```

例:

```hlsl
float4 Center = SceneInput.Fetch(0, 0);
float4 Right  = SceneInput.Fetch(1, 0);
return abs(Right.rgb - Center.rgb);
```

またはIDを明示利用できる。

```hlsl
float2 UV = GetDefaultSceneTextureUV(Parameters, SceneInput.ID);
return SceneTextureLookup(Parameters, UV, SceneInput.ID, true);
```

置換はpreprocessor macro展開より前である。従って、入力名をmacro引数として渡した後に`.Fetch`を付ける書き方は変換されない。`SceneInput.ID`をmacroへ渡すか、macro本文に固定の入力名を書く。

`SceneInput`を`.ID`/`.Fetch`以外で直接参照すれば、接続ノードの通常sample値を意味する。専用構文だけを使う場合、UEは不要な通常sampleをdead stripできる。

## Additional Outputs、Defines、Includes

### Primary output

`OutputType`はFloat1、Float2、Float3、Float4、Material Attributes。Additional Outputがなければprimary pinは無名で、存在する場合はprimary pin名が`return`になる。

### Additional Outputs

各additional outputもFloat1～4またはMaterial Attributes。コード中でoutput名へ代入する。

```hlsl
Luma = dot(Color.rgb, float3(0.2126, 0.7152, 0.0722));
Filtered = saturate(Color.rgb * Strength);
return Filtered;
```

旧translatorはadditional outputの一時値を0初期化し、parameterを`inout`にする。新MIR経路は`out`にする。両方で安全にするため、追加出力は「必要な場合だけ」ではなく全制御経路で必ず代入する。

### Additional Defines

関数の前へ次の形で出る。

```hlsl
#ifndef MYPROJECT_MODE
#define MYPROJECT_MODE 1
#endif
```

空の名前・値は新MIR経路で明示error。複数Custom間の名前衝突を避けるため固有prefixを使う。

### Include File Paths

各値は関数の前へ`#include "..."`として出る。`/Engine`、`/Project`、または明示登録されたvirtual mappingを使う。`<PROJECT>/Shaders` mappingはディレクトリがEngine起動時に存在するときだけ追加されるため、作成後はEditor再起動とshader再compileを前提にする。

## 旧translatorと新MIR経路の差

UE 5.8 sourceには両方の生成実装がある。互換性fixtureは一方だけを見て合格にしない。

| 項目 | 旧`FHLSLMaterialTranslator` | 新Material IR |
|---|---|---|
| 関数名 | `CustomExpressionN` | `C<UniqueId>_<sanitized Description>` |
| stage | 現在のshader frequency | 使用stageごとのoverload。computeはpixel型 |
| input型 | `EMaterialValueType`のswitchで制限 | 接続値の`MIR::FType` |
| additional output | 0初期化した`inout` | `out` |
| parameter上限 | この関数内に明示上限なし | input + additional output合計32 |
| define空値検査 | ここではなし | 名前・値の空をerror |
| include空値検査 | ここではなし | 空をerror |
| `return`補完 | `Code.Contains("return")`で判定 | 同じ単純substring判定 |
| SceneTexture fixup | あり | あり |
| clip/discard flag | `HasPixelDiscard()`をCompilationOutputへ反映 | `Build`周辺では同じ反映を確認できず、別途実機確認要 |

新MIRはCustomの`Description`を関数名へ使用し、英数字以外を`_`へ変換し、先頭数字なら`_`を足す。ただし入力・追加出力名は同じsanitizeを通らない。生成側validatorでHLSL identifierを保証する。

32個上限はsamplerやLWCの追加HLSL引数ではなく、MIR上のinput/output parameter数に対して判定される。互換ルールとして`named Inputs + named AdditionalOutputs <= 32`を採用する。

## 失敗しやすい点

### `return`の自動補完は構文解析ではない

両経路とも`Code.Contains("return")`というcase-sensitive substringだけを見る。例えばコメントに`return`があるだけでも補完されない。

```hlsl
// return the adjusted color
Color * Strength
```

これは自動で`return`を付けてもらえずcompile errorになりうる。生成コードは常に明示的な`return ...;`を入れる。

### input/output名

Editorの`PostEditChangeProperty`がInputNameから除去するのは半角spaceだけで、完全なHLSL identifier検証ではない。additional output名も同じsanitizeを受けない。推奨規則:

```regex
^[A-Za-z_][A-Za-z0-9_]*$
```

予約語、`Parameters`、同一Custom内の重複、texture入力に対する`<Name>Sampler`との衝突も拒否する。

### helperの定義場所

Custom本文はすでに関数内なので、通常のglobal helper関数を本文に定義しない。他Customの`CustomExpressionN`や`C5_Name`を呼ばない。番号、順序、deduplicationは内部実装である。

### `clip` / `discard`

`Contains Clip Instruction`の`Search`は、case-sensitiveに`clip(`または`discard`を文字列検索するだけで保守的である。helper includeやmacro経由でdiscardする場合は自動検出を信用せず`Yes`を指定する。誤検出を避けたい場合のみ根拠付きで`No`にする。

### Engine private symbol

`Random.ush`、`MonteCarlo.ush`、`BlueNoiseCommon.ush`等はMaterialTemplateからincludeされるが、そこにある全関数を安定APIとはしない。feature define、引数型、include順が変化する。必要なら自分の`.ush`で薄いadapterを作り、UE version別にcompile testする。

## MGJSON・validatorへの実装要求

メインAIはCustomを`raw_props`だけで保持せず、次を構造化して往復させる。

```json
{
  "Code": "return A + B;",
  "OutputType": "CMOT_Float3",
  "Description": "AddVectors",
  "Inputs": [
    {"InputName": "A", "link": "..."},
    {"InputName": "B", "link": "..."}
  ],
  "AdditionalOutputs": [
    {"OutputName": "Luma", "OutputType": "CMOT_Float1"}
  ],
  "AdditionalDefines": [
    {"DefineName": "MYPROJECT_MODE", "DefineValue": "1"}
  ],
  "IncludeFilePaths": ["/Project/Material/MyMaterialLib.ush"],
  "ContainsClipInstruction": "CMCI_Search",
  "ShowCode": true
}
```

最低限のvalidator規則:

- `OutputType`とadditional output typeを既知enumへ限定する。
- named inputは接続必須。無名placeholderはT3D互換用に保持できる。
- named input + named additional outputを32以下にする。
- input/output名をidentifier規則、予約語、重複、sampler衝突で検査する。
- `AdditionalDefines`の名前と値を空にしない。define名もidentifierにする。
- includeを空にせず、absolute virtual shader path形式にする。filesystem pathや`..`を拒否する。
- `Code`へ明示`return`を推奨し、primary output型と明白に不整合ならwarningする。
- additional outputが全制御経路で代入されるか静的に断定できなければwarningし、Editor compileを必須にする。
- `clip`/`discard`をinclude/macroで使う可能性がある場合、`ContainsClipInstruction`の明示設定を促す。
- Engine private helper、`Parameters.`、`View.`を検出したら`unsafe_internal_api` warningとUE version固定要求を出す。
- SceneTexture `.ID`/`.Fetch`は該当入力がSceneTexture/UserSceneTexture output 0へ直結するときだけ許可する。

関数catalogは「全Engine shader関数のallowlist」ではなく、次のような保守的metadataにする。

```json
{
  "name": "Texture2DSample",
  "stability": "recommended",
  "stages": ["pixel", "vertex_if_supported"],
  "requires": ["Texture2D input", "generated sampler"]
}
```

Engine private helperは`stability: internal_version_locked`、SceneTextureは`stability: domain_conditional`とする。

## 確認用fixture案

最低でも次を別fixtureにしてEditor paste、compile、copy-backを確認する。

1. `float3`入力2個、明示`return`。
2. TextureObject入力 + UV入力 + `Texture2DSample(Tex, TexSampler, UV)`。
3. primary + Float1/Float3 additional outputs。全outputを必ず代入。
4. Additional Defineを分岐に使用。
5. `/Project/TestCustom.ush`をincludeして関数呼出し。
6. Post Process materialでSceneTextureの`.ID`と`.Fetch`。
7. pixel derivative fixtureと、vertex経路では拒否されるfixture。
8. LWC入力で`Name`と`LWCName`の生成確認。
9. 32 parameter成功、33 parameter失敗。
10. コメントに`return`を含むが明示returnがない負例。
11. include/macro経由の`clip`で`CMCI_Yes`。
12. 旧translatorと新MIRを切り替え可能なら、additional outputの同一結果確認。

成功判定はpasteできたことではなく、material compile error 0、期待pin名・型・順序、copy-back後のCode/配列/enum一致まで含める。

## 参照したsource

UE source rootからの相対pathと主要symbol:

- `Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionCustom.h`
  - `ECustomMaterialOutputType`, `FCustomInput`, `FCustomOutput`, `FCustomDefine`, `UMaterialExpressionCustom`
- `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp`
  - constructor, `Compile`, `PostEditChangeProperty`, `RebuildOutputs`, `HasPixelDiscard`
- `Engine/Source/Runtime/Engine/Private/Materials/HLSLMaterialTranslator.cpp`
  - `FHLSLMaterialTranslator::CustomExpression`
- `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressionsToMIR.cpp`
  - `DescriptionToIdentifier`, `UMaterialExpressionCustom::Build`
- `Engine/Source/Runtime/Engine/Public/Materials/MaterialIR.h`
  - `MaxNumFunctionParameters = 32`
- `Engine/Source/Runtime/Engine/Private/Materials/MaterialIRToHLSLTranslator.cpp`
  - `GenerateCustomFunctionsHLSL`
- `Engine/Source/Runtime/Engine/Private/Materials/MaterialShared.cpp`
  - `CustomExpressionSceneTextureInputFixup`
- `Engine/Shaders/Private/MaterialTemplate.ush`
  - parameter structs、scene texture helpers、Custom挿入slot
- `Engine/Shaders/Private/SceneTexturesCommon.ush`
  - `Common.ush` include
- `Engine/Shaders/Private/Common.ush`
  - texture sampling wrappers
- `Engine/Source/Runtime/RenderCore/Public/ShaderCore.h`
  - `AddShaderSourceDirectoryMapping`
- `Engine/Source/Runtime/Launch/Private/LaunchEngineLoop.cpp`
  - `/Engine`、`/Project` shader directory mapping

この調査はsource上の可視性と生成規則を確認したもの。全material domain・全RHIでのshader compile成功を保証するものではないため、上記fixtureのEditor実機検証を最終根拠にする。
