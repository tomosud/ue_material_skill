# Material Expression 逆引き索引

`skill/catalog/nodes.json` から自動生成。説明文を検索して class と Pin を確認する。
手編集せず `catalog_merge.py` を再実行する。

| class | 説明 | 入力 | 出力 | flags |
|---|---|---|---|---|
| `Abs` | abs(Input)。絶対値 | Input | Output | - |
| `AbsorptionMediumMaterialOutput` | パストレーサー用固体屈折性ガラスの吸収特性を設定する出力。透光距離100単位時の透光色を入力 | TransmittanceColor | - | - |
| `ActorPositionWS` | アクタのワールド座標 | Origin | Output | - |
| `Add` | A + B。float/vector対応、次元は大きい方に合わせられる | A, B | Output | - |
| `Aggregate` | マテリアル属性またはユーザー定義アグリゲートの複数入力をまとめて1つの出力に | PrototypeInput | Output | - |
| `AntialiasedTextureMask` | アンチエイリアスされたテクスチャマスク。単一チャンネルの高精度マスク出力 | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `AppendVector` | 2つのベクトル・スカラーを結合して高次元ベクトルを作成 | A, B | Output | - |
| `Arccosine` | Arccosine | Input | Output | - |
| `ArccosineFast` | ArccosineFast | Input | Output | - |
| `Arcsine` | Arcsine | Input | Output | - |
| `ArcsineFast` | ArcsineFast | Input | Output | - |
| `Arctangent` | Arctangent | Input | Output | - |
| `Arctangent2` | Arctangent2 | Y, X | Output | - |
| `Arctangent2Fast` | Arctangent2Fast | Y, X | Output | - |
| `ArctangentFast` | ArctangentFast | Input | Output | - |
| `AtmosphericFogColor` | 大気フォグの色を計算（非推奨：Atmosphereプラグイン推奨） | WorldPosition | Output | - |
| `AtmosphericLightColor` | 大気中の太陽光の地表照度を計算（DisplayName: Atmosphere Sun Light Illuminance On Ground） | - | Output | - |
| `AtmosphericLightVector` | 大気中の太陽光ベクトルを計算（DisplayName: Atmosphere Sun Light Vector） | - | Output | - |
| `BentNormalCustomOutput` | ベント法線のカスタム出力。パストレーサー用の湾曲法線情報を設定 | Input | - | - |
| `BindlessSwitch` | バインドレス対応とデフォルト実装を条件分岐。バインドレス対応時はBindless入力、非対応時はDefault入力を選択 | Default, Bindless | Output | - |
| `BlackBody` | 温度から黒体放射の色を計算。物理的に正確な色温度表現 | Temp | Output | - |
| `Blend` | マテリアル属性（ピクセル/頂点）を2つの入力間でAlphaにより線形補間 | A, B, Alpha | Output | - |
| `BlendMaterialAttributes` | 2つの MaterialAttributes を指定比率で混合 | A, B, Alpha | Output | - |
| `Bounds` | メッシュのバウンディングボックス情報（ローカル座標）を出力。タイプにより出力が異なる | Type | Half Extents, Extents, Min, Max | - |
| `BreakMaterialAttributes` | MaterialAttributes 構造体を個別の属性に分解 | MaterialAttributes | - | - |
| `BumpOffset` | バンプオフセット。高さマップに基づいて座標をシフト（視差マッピング効果） | Coordinate, Height, HeightRatioInput | Output | - |
| `CameraPositionWS` | カメラのワールド座標 | - | Output | - |
| `CameraVectorWS` | カメラから現在のピクセルへの方向ベクトル | - | Output | - |
| `Ceil` | ceil(Input)。天井関数(切り上げ) | Input | Output | - |
| `ChannelMaskParameter` | チャネルマスクパラメータ（R/G/B/A チャネルを選択して出力） | Input | R | - |
| `Clamp` | clamp(Input, Min, Max)。値を範囲内に制限 | Input, Min, Max, ClampMode | Output | - |
| `ClearCoatNormalCustomOutput` | クリアコート底面法線のカスタム出力 | Input | - | - |
| `CloudSampleAttribute` | クラウドレイヤーのサンプル属性を取得（高度、レイヤー内位置、正規化高度、シャドウ距離） | - | Altitude, AltitudeInLayer, NormAltitudeInLayer, ShadowSampleDistance | - |
| `CollectionParameter` | マテリアルパラメータコレクションの単一パラメータを参照 | - | Output | - |
| `CollectionTransform` | マテリアルパラメータコレクション内の連続5ベクトル要素を変換行列として使用 | Input | Output | - |
| `ColorRamp` | 入力値に基づいて曲線からリニアカラーをサンプリング | Input | Output | - |
| `Comment` | コメント用ノード。マテリアルグラフの整理に使用 | - | Output | - |
| `ComponentMask` | ベクトルの特定のコンポーネント(R/G/B/A)を選択出力 | Input, R, G, B, A | Output | - |
| `Composite` | サブグラフを組み込むノード。入出力はピンベースで管理される | - | - | - |
| `Constant` | 定数値（float）を出力する | Value | Output | - |
| `Constant2Vector` | 2要素ベクトル定数（X, Y）を出力 | X, Y | RG, R, G | - |
| `Constant3Vector` | 3要素ベクトル定数（RGB）を出力 | Constant | RGB, R, G, B | - |
| `Constant4Vector` | 4要素ベクトル定数（RGBA）を出力 | Constant | RGBA, R, G, B, A, RGB | - |
| `ConstantBiasScale` | 入力に Bias と Scale を適用: (Bias + Input) * Scale | Input, Bias, Scale | Output | - |
| `ConstantDouble` | 倍精度浮動小数点定数値を出力 | Value | Output | - |
| `Convert` | 動的入出力型コンバージョンノード。複数の型変換と成分マッピングに対応 | - | - | - |
| `Cosine` | Cosine | Input, Period | Output | - |
| `CrossProduct` | 2つのベクトルの外積を計算 | A, B | Output | - |
| `CurveAtlasRowParameter` | スカラーパラメータを曲線アトラスの行位置として使用し、時間入力で値をサンプリングする | CurveTime | RGB, R, G, B, A | - |
| `Custom` | HLSL コードを埋め込むノード。入出力は動的に定義される | - | - | - |
| `CustomOutput` | カスタム出力の基底クラス(抽象) | - | - | abstract |
| `DBufferTexture` | DBuffer テクスチャから値を取得する。A/B/C のいずれかを選択してサンプリング | Coordinates | RGBA, RGB, A | - |
| `DDX` | 入力値の水平方向の偏微分(ddx)を計算する | Value | Output | - |
| `DDY` | 入力値の垂直方向の偏微分(ddy)を計算する | Value | Output | - |
| `DataDrivenShaderPlatformInfoSwitch` | シェーダプラットフォーム情報に基づいて条件分岐し、2つの入力から選択する | InputTrue, InputFalse | Output | - |
| `DecalColor` | デカール受信サーフェスのベースカラーを取得する | - | RGB, R, G, B, A, RGBA | - |
| `DecalDerivative` | デカール受信サーフェスの偏微分(DDX, DDY)を取得する | - | DDX, DDY | - |
| `DecalLifetimeOpacity` | デカールのライフタイムに基づいた不透明度を取得する | - | Opacity | - |
| `DecalMipmapLevel` | テクスチャサイズからミップマップレベルを計算する | TextureSize | Output | - |
| `DeltaTime` | 前フレームからの経過時間を出力 | - | Output | - |
| `DepthFade` | シーン深度に基づいて半透明のフェードを適用。オブジェクトが別のオブジェクトに接近時に透明化 | Opacity, FadeDistance | Output | - |
| `DepthOfFieldFunction` | 深度から被写界深度関連の値を計算する(ピント、近景、遠景、円盤の混乱など) | Depth | Output | - |
| `DeriveNormalZ` | 法線XY成分からZ成分を復元(法線圧縮用) | InXY | Output | - |
| `Desaturation` | 色を彩度を下げて灰色化(グレースケール変換) | Input, Fraction, LuminanceFactors | Output | - |
| `Distance` | 2点間の距離を計算 | A, B | Output | - |
| `DistanceCullFade` | カメラからの距離に基づいてフェード。遠距離カリングに使用 | - | Output | - |
| `DistanceFieldApproxAO` | ディスタンスフィールドを用いた環境遮蔽(AO)を近似計算する | Position, Normal, BaseDistance, Radius, NumSteps, StepScaleDefault | Output | - |
| `DistanceFieldGradient` | ディスタンスフィールドの勾配(法線)を取得する | Position | Output | - |
| `DistanceFieldsRenderingSwitch` | ディスタンスフィールドレンダリングがサポートされているかで条件分岐する | No, Yes | Output | - |
| `DistanceToNearestSurface` | 最も近いサーフェスまでの距離を取得する | Position | Output | - |
| `Divide` | A / B。float/vector対応 | A, B | Output | - |
| `DotProduct` | 2つのベクトルの内積を計算 | A, B | Output | - |
| `DoubleVectorParameter` | ダブル精度ベクトルパラメータ（XYZ/XYZW） | DefaultValue | XYZ, X, Y, Z, W | - |
| `DynamicParameter` | パーティクルシステムからの動的パラメータを受け取る。4つまでのベクトルを出力可能 | DefaultValue, ParameterIndex | R, G, B, A, RGB, RGBA | - |
| `EvalPhysicsIntegerField` | グローバルフィジックスフィールドから整数値をサンプリングする | WorldPosition, FieldTarget | Output | - |
| `EvalPhysicsScalarField` | グローバルフィジクスフィールドからスカラー値をサンプリング | WorldPosition, Target Type, Target Type | Output | - |
| `EvalPhysicsVectorField` | グローバルフィジクスフィールドからベクトル値をサンプリング | WorldPosition, Target Type, Target Type | Output | - |
| `Exponential` | Exponential | Input | Output | - |
| `Exponential2` | Exponential2 | Input | Output | - |
| `ExternalCodeBase` | 外部HLSLコードを挿入するベースクラス | - | - | abstract |
| `EyeAdaptation` | 目の順応(露出補正)の現在値を参照 | - | EyeAdaptation | - |
| `EyeAdaptationInverse` | EyeAdaptation逆変換を適用 | LightValueInput, AlphaInput | EyeAdaptationInverse | - |
| `FeatureLevelSwitch` | フィーチャーレベルに応じて異なる入力を選択 | Default, SM5, SM4_REMOVED, ES3_1, ES3_1_REMOVED, MAX | Output | - |
| `FirstPersonOutput` | 一人称視点レンダリング用のカスタム出力 | FirstPersonInterpolationAlpha | Output | - |
| `FloatToUInt` | 浮動小数点数を符号なし整数に変換 | Input | Output | - |
| `Floor` | floor(Input)。床関数(切り下げ) | Input | Output | - |
| `Fmod` | A fmod B。浮動小数点数のモジュロ | A, B | Output | - |
| `FontSample` | フォントテクスチャをサンプリング | - | Output, out1, out2, out3, out4 | - |
| `FontSampleParameter` | パラメータ化されたフォントテクスチャサンプリング | - | Output, out1, out2, out3, out4 | - |
| `FontSignedDistance` | フォント署名距離フィールドのサンプリング | - | Signed Distance, Smooth Signed Distance, Pixel Distance Factor, Implicit Opacity | - |
| `Frac` | frac(Input)。小数部取得 | Input | Output | - |
| `Fresnel` | フレネル効果を計算、視点角度による鏡面反射率を算出 | ExponentIn, BaseReflectFractionIn, Normal | Output | - |
| `FunctionInput` | マテリアル関数の入力ピン定義 | Preview | Output | - |
| `FunctionOutput` | マテリアル関数の出力ピン定義 | A | Output | - |
| `GIReplace` | GI計算方式によって異なる入力を選択 | Default, StaticIndirect, DynamicIndirect | Output | - |
| `GenericConstant` | 汎用定数値ベースクラス | - | - | abstract |
| `GetMaterialAttributes` | MaterialAttributes 構造体から属性を抽出 | MaterialAttributes | - | - |
| `HairAttributes` | 髪属性へのアクセス | - | U, V, Length, Radius, Seed, Tangent, Root UV, BaseColor, Roughness, Depth, Coverage, AuxilaryData, AtlasUVs, Group Index, AO, Clump ID | - |
| `HairColor` | メラニン濃度から髪色を生成 | Melanin, Redness, DyeColor | Color | - |
| `HeightfieldMinMaxTexture` | UHeightfieldMinMaxTextureオブジェクトに含まれるテクスチャを出力。SamplerTypeはMinMaxTextureから自動選択される | - | Output | plugin |
| `HsvToRgb` | HSV色空間からRGB色空間に変換 | Input | Output | - |
| `If` | If | A, B, AGreaterThanB, AEqualsB, ALessThanB, EqualsThreshold | Output | - |
| `IfThenElse` | 条件によって異なる値を選択 | Condition, True, False | Output | - |
| `InverseLinearInterpolate` | InverseLinearInterpolate | A, B, Value | Output | - |
| `IsFirstPerson` | 一人称視点かどうかを判定 | - | Output | - |
| `IsOrthographic` | 現在のカメラが正投影かどうかを出力(1=正投影、0=透視投影) | - | Output | - |
| `LandscapeGrassOutput` | ランドスケープ上の草タイプごとの密度を出力 | - | - | - |
| `LandscapeLayerBlend` | 複数のランドスケープレイヤーをブレンド | - | Output | - |
| `LandscapeLayerCoords` | ランドスケープレイヤーのテクスチャ座標を取得 | - | Output | - |
| `LandscapeLayerSample` | 指定ランドスケープレイヤーのウェイト値をサンプリング | - | Output | - |
| `LandscapeLayerSwitch` | ランドスケープレイヤーが使用されているかで出力を切り替え | LayerUsed, LayerNotUsed | Output | - |
| `LandscapeLayerWeight` | ランドスケープレイヤーの重みに応じて Base から Layer にブレンド | Base, Layer | Output | - |
| `LandscapePhysicalMaterialOutput` | ランドスケープ上の各位置での物理マテリアルを出力 | - | - | - |
| `LandscapeVisibilityMask` | ランドスケープの可視性マスク（非表示レイヤーを検出） | - | Output | - |
| `LayerStack` | マテリアルレイヤー関数スタックを処理（実験的機能） | - | Output | - |
| `LegacyBlendMaterialAttributes` | マテリアル属性のレガシーブレンド（廃止予定） | A, B, Alpha, VertexAttribute_UseA, VertexAttribute_UseB, PixelAttribute_UseA, PixelAttribute_UseB | Output | - |
| `Length` | ベクトルの長さ・大きさを計算 | Input | Output | - |
| `LightVector` | ライト方向ベクトルを出力 | - | Output | - |
| `LightmapUVs` | ライトマップのUV座標を出力 | - | RG | - |
| `LightmassReplace` | ライトマスレンダリング時と実行時で異なる値を使用 | Realtime, Lightmass | Output | - |
| `LinearInterpolate` | LinearInterpolate | A, B, Alpha | Output | - |
| `LocalPosition` | ローカル座標系でのピクセル位置 | Shader Offsets, Local Origin | XYZ, XY, Z | - |
| `Logarithm` | Logarithm | Input | Output | - |
| `Logarithm10` | Logarithm10 | X | Output | - |
| `Logarithm2` | Logarithm2 | X | Output | - |
| `MainDirectionalLight` | メインの指向性ライトの情報を出力（照度と方向ベクトル） | - | Illuminance, Direction | - |
| `MakeMaterialAttributes` | 個別の属性入力から MaterialAttributes を構築 | BaseColor, Metallic, Specular, Roughness, Anisotropy, EmissiveColor, Opacity, OpacityMask, Normal, Tangent, WorldPositionOffset, SubsurfaceColor, ClearCoat, ClearCoatRoughness, AmbientOcclusion, Refraction, PixelDepthOffset, ShadingModel, Displacement | Output | - |
| `MapARPassthroughCameraUV` | ビューポートUVをAR透視カメラUVにマッピング（アスペクト比とデバイス回転を考慮） | Coordinates | Output | - |
| `MaterialAttributeLayers` | マテリアル属性レイヤーの構成と合成。複数のレイヤーとブレンド関数を使用して属性を結合 | Input | Output | - |
| `MaterialCache` | マテリアルキャッシュの読み書き。キャッシュタグと属性レイアウトの動的管理 | Primitive, UV | - | - |
| `MaterialFunctionCall` | マテリアル関数を呼び出すノード | - | - | - |
| `MaterialLayerOutput` | マテリアルレイヤー出力。レイヤーグラフの終端ノード | - | Material Attributes | - |
| `MaterialProxyReplace` | リアルタイム/マテリアルプロキシの切り替え。IsResultMaterialAttributes() == true | Realtime, MaterialProxy | Output | - |
| `MaterialSample` | 別のマテリアルの機能出力を参照。プロトタイプ段階（ENABLE_MATERIAL_SAMPLE_PROTOTYPE=0） | - | Output | - |
| `MaterialXAppend3Vector` | A material expression that allows combining 3 channels together to create a vector with more channel than the original | A, B, C | Output | plugin |
| `MaterialXAppend4Vector` | A material expression that allows combining 4 channels together to create a vector with more channel than the original | A, B, C, D | Output | plugin |
| `MaterialXBurn` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXContrast` | A material expression that increases or decreases contrast of a float/color value using a linear slope multiplier. | Input, Amount, Pivot | Output | plugin |
| `MaterialXDifference` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXDisjointOver` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXDodge` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXFractal` | Zero-centered 2D or 3D Fractal noise in 1, 2, 3 or 4 channels, created by summing several octaves of 2D or 3D Perlin noise, increasing the frequency and decreasing the amplitude at each octave. Defaul | Position, Amplitude, Octaves, Lacunarity, Diminish | Output | plugin |
| `MaterialXIn` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXLuminance` | A material expression that outputs a grayscale image containing the luminance of the incoming RGB color in all color channels; the alpha channel is left unchanged if present. | Input | Output | plugin |
| `MaterialXMask` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXMatte` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXMinus` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXMod` | The remaining fraction after dividing an incoming input by a value and subtracting the integer portion. Unlike UE FMod or Modulo expressions, Mod always returns a non-negative result, matching the int | A, B | Output | plugin |
| `MaterialXOut` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXOver` | Merge nodes take two 4-channel (color4) inputs and use the built-in alpha channel(s) to control the compositing of the A and B inputs. "A" and "B" refer to the non-alpha channels of the A and B inputs | A, B, Alpha | Output | plugin |
| `MaterialXOverlay` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXPlus` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXPremult` | Multiply the RGB channels of the input by the Alpha channel of the input. Input must be of type float4 | Input | Output | plugin |
| `MaterialXRamp4` | A material expression that computes a 4-corner bilinear value ramp.. | Coordinates, A, B, C, D | Output | plugin |
| `MaterialXRampLeftRight` | A material expression that computes a left-to-right bilinear value ramp. | Coordinates, A, B | Output | plugin |
| `MaterialXRampTopBottom` | A material expression that computes a top-to-bottom bilinear value ramp. | Coordinates, A, B | Output | plugin |
| `MaterialXRange` | A material expression that Remap a value from one range to another, optionally applying a gamma correction in the middle, and optionally clamping output values. | Input, InputLow, InputHigh, TargetLow, TargetHigh, Gamma, Clamp | Output | plugin |
| `MaterialXRemap` | A material expression that Remap a value from one range to another. | Input, InputLow, InputHigh, TargetLow, TargetHigh | Output | plugin |
| `MaterialXScreen` | Blend nodes take two 1-4 channel inputs and apply the same operator to all channels. Blend nodes support an optional float input mix , which can be used to mix the original B value with the result of  | A, B, Alpha | Output | plugin |
| `MaterialXSplitLeftRight` | A material expression that computes a left-right split matte, split at a specified u value. | Coordinates, A, B, Center | Output | plugin |
| `MaterialXSplitTopBottom` | A material expression that computes a top-bottom split matte, split at a specified v value. | Coordinates, A, B, Center | Output | plugin |
| `MaterialXTextureSampleParameterBlur` | The size of the blur kernel, relative to 0-1 UV space. | - | Output | plugin |
| `MaterialXUnpremult` | Divide the RGB channels of the input by the Alpha channel of the input. If the Alpha value is zero, the original color4 input value is passed through unchanged. Input must be of type float4 | Input | Output | plugin |
| `Max` | max(A, B)。最大値 | A, B | Output | - |
| `MeshPaintTextureCoordinateIndex` | メッシュペイント用テクスチャ座標インデックス。External Code Base のラッパー | - | Output | - |
| `MeshPaintTextureObject` | メッシュペイント用テクスチャオブジェクト。External Code Base のラッパー | - | Output | - |
| `MeshPaintTextureReplace` | メッシュペイントテクスチャの切り替え。デフォルト/メッシュペイント入力 | Default, MeshPaintTexture | Output | - |
| `MeshPartitionChannelSample` | MeshPartitionDefinitionで指定されたチャネルをテクスチャ座標から取得 | Channel Texture | Output | plugin |
| `MeshPartitionChannelSampleIndex` | インデックスで指定されたMeshPartitionチャネルをテクスチャ座標から取得 | Channel Texture, Channel Index | Output | plugin |
| `MeshPartitionInspector` | MeshPartitionチャネルの検査・可視化用。全チャネルをランダムカラーで表示 | Channel Texture | Output | plugin |
| `MeshPartitionResource` | MeshPartitionの共有テクスチャリソースパラメータ。他のMeshPartition表現式から参照される | - | Channel Texture | plugin |
| `MeshPartitionTexcoord` | MeshPartitionチャネルのテクスチャ座標を出力。uvとunit単位の2つの出力を提供 | - | uv, uv [unit] | plugin |
| `Min` | min(A, B)。最小値 | A, B | Output | - |
| `Modulo` | A mod B。整数演算のモジュロ | A, B | Output | - |
| `MotionVectorWorldOffsetOutput` | モーションベクトル世界オフセット出力。ピクセル単位のモーションベクトルオフセット | Input | - | - |
| `Multiply` | A * B。float/vector対応 | A, B | Output | - |
| `NamedRerouteBase` | 名前付き Reroute の基底クラス | - | Output | abstract |
| `NamedRerouteDeclaration` | 名前付き変数を宣言するノード | Input | Output | - |
| `NamedRerouteUsage` | 名前付き変数の使用側ノード | - | Output | - |
| `NaniteReplace` | ナナイトレンダリング時の置き換え。デフォルト/ナナイト入力で切り替え | Default, Nanite | Output | - |
| `NeuralNetworkInput` | ニューラルネットワーク入力ノード。ニューラルポストプロセスの入力 | Coordinates, Input0, Mask | - | - |
| `NeuralNetworkOutput` | ニューラルネットワーク出力ノード。ニューラルポストプロセスの出力 | Coordinates | RGBA | - |
| `Noise` | パーリンノイズやシンプレックスノイズなど複数の手法でノイズを生成。3次元位置から自動生成 | Position, FilterWidth, Function, Quality | Output | - |
| `Normalize` | ベクトルを正規化(単位ベクトル化) | VectorInput | Output | - |
| `ObjectBounds` | オブジェクトのバウンディングボックス情報 | - | Output | - |
| `ObjectLocalBounds` | オブジェクトのローカル座標系バウンディングボックス情報 | - | Half Extents, Extents, Min, Max | - |
| `ObjectOrientation` | オブジェクトの向きを示すベクトル | - | Output | - |
| `ObjectPositionWS` | オブジェクトのワールド座標 | Origin | Output | - |
| `ObjectRadius` | オブジェクトのバウンディングスフィアの半径 | - | Output | - |
| `OneMinus` | 1 - Input。補数 | Input | Output | - |
| `Operator` | 演算ノード。単項/二項/三項演算を動的にサポート | - | Output | - |
| `Panner` | UV座標をパン（移動）。時間に基づいて座標をシフト | Coordinate, Time, Speed, SpeedX, SpeedY | Output | - |
| `Parameter` | パラメータの基底クラス | - | - | - |
| `ParticleColor` | パーティクルカラー。RGB/R/G/B/A/RGBA 出力 | - | RGB, R, G, B, A, RGBA | - |
| `ParticleDirection` | パーティクル方向。パーティクルの移動方向ベクトル | - | Output | - |
| `ParticleMacroUV` | パーティクルマクロUV。パーティクルシステムの MacroUVPosition/Radius を使用した UV 座標生成 | - | Output | - |
| `ParticleMotionBlurFade` | パーティクルのモーションブラーフェード値を公開 | - | Output | - |
| `ParticlePositionWS` | パーティクルのワールド座標位置を取得 | Origin | Output | - |
| `ParticleRadius` | パーティクルの半径を取得 | - | Output | - |
| `ParticleRandom` | パーティクルのランダム値を取得 | - | Output | - |
| `ParticleRelativeTime` | パーティクルの相対時間を取得 | - | Output | - |
| `ParticleSize` | パーティクルのサイズを取得 | - | Output | - |
| `ParticleSpeed` | パーティクルの速度を取得 | - | Output | - |
| `ParticleSpriteRotation` | パーティクルのスプライト回転を取得 | - | Rad, Deg | - |
| `ParticleSubUV` | パーティクルのサブUVテクスチャをサンプリング | - | RGB, R, G, B, A, RGBA | - |
| `ParticleSubUVProperties` | パーティクルのSubUVプロパティへのダイレクトアクセス | - | TextureCoordinate0, TextureCoordinate1, Blend | - |
| `PathTracingBufferTexture` | パストレーシングバッファテクスチャをルックアップ | Coordinates | RGBA, RGB, A | - |
| `PathTracingQualitySwitch` | パストレーシング品質に応じて値を切り替え | Normal, PathTraced | Output | - |
| `PathTracingRayTypeSwitch` | パストレーシングのレイタイプに応じて値を切り替え | Main, Shadow, IndirectDiffuse, IndirectSpecular, IndirectVolume | Output | - |
| `PerInstanceCustomData` | インスタンスごとのカスタムデータを参照。float値を出力 | DefaultValue, DataIndex | Output | - |
| `PerInstanceCustomData3Vector` | インスタンスカスタムデータ(3Dベクトル)を取得 | DefaultValue, DataIndex | Output | - |
| `PerInstanceFadeAmount` | インスタンスごとのフェード量を出力 | - | Output | - |
| `PerInstanceRandom` | インスタンスごとのランダム値を出力 | - | Output | - |
| `PhysicalMaterialOutput` | 物理マテリアルの重みを出力するカスタム出力ノード。複数の物理マテリアルと入力値の配列で構成 | - | - | plugin |
| `PinBase` | ピン集約ノード。複数の Reroute ピンを管理 | - | - | - |
| `PixelDepth` | 現在のピクセルの深度値 | - | R | - |
| `PixelNormalWS` | 現在のピクセルの表面法線(ワールド座標) | - | Output | - |
| `PostVolumeUserFlagTest` | ポストボリュームユーザーフラグをテスト | BitIndex | Output | - |
| `Power` | Base ^ Exponent。べき乗 | Base, Exponent | Output | - |
| `PreSkinnedLocalBounds` | スキニング前のローカルバウンディングボックス情報を取得 | - | Half Extents, Extents, Min, Max | - |
| `PreSkinnedNormal` | スキニング前のローカル法線を返す。スケルタルメッシュの頂点シェーダでのみ使用可能 | - | Output | - |
| `PreSkinnedPosition` | スキニング前のローカル位置を返す（非推奨、'Local Position'にマージされた） | - | Output | - |
| `PrecomputedAOMask` | Lightmass World設定で生成された事前計算AOマスクにアクセス | - | Output | - |
| `PreviousFrameSwitch` | 現在フレームと前フレームのいずれかを選択するスイッチ | Current Frame, Previous Frame | Output | - |
| `QualitySwitch` | 品質レベルに基づいて異なる入力を選択するスイッチ | Default, Low, High, Epic, Cinematic | Output | - |
| `RayTracingQualitySwitch` | レイトレーシング対応かどうかに基づいて異なる入力を選択するスイッチ | Normal, RayTraced | Output | - |
| `RecordTextureStreamingInfo` | テクスチャのUVスケール情報を自動ストリーミングシステム用に記録 | TextureObject, Coordinates | Tex | - |
| `ReflectionCapturePassSwitch` | リフレクションキャプチャレンダリング時の特殊な挙動を定義するスイッチ | Default, Reflection | Output | - |
| `ReflectionVectorWS` | 反射ベクトル | Custom World Normal, Normalize custom world normal | Output | - |
| `RequiredSamplersSwitch` | プラットフォームのサンプラー数制限に基づいてロジックを切り替えるスイッチ | Within platform limit, Over platform limit | Output | - |
| `Reroute` | 入力をそのまま出力に通す。グラフの結線を整理するために使用 | Input | Output | - |
| `RerouteBase` | Reroute 系の基底クラス。複数の入力値を通す機能を提供 | - | Output | abstract |
| `RgbToHsv` | RGB色空間からHSV色空間に変換 | Input | Output | - |
| `RotateAboutAxis` | 任意の軸周りにベクトルを回転 | NormalizedRotationAxis, RotationAngle, PivotPoint, Position, Period | Output | - |
| `Rotator` | UV座標を回転。中心点を基準に時間に基づいて回転 | Coordinate, Time, CenterX, CenterY, Speed | Output | - |
| `Round` | round(Input)。四捨五入 | Input | Output | - |
| `RuntimeVirtualTextureCustomData` | ランタイム仮想テクスチャのカスタムデータにアクセス | - | Output | - |
| `RuntimeVirtualTextureOutput` | ランタイム仮想テクスチャへ複数のマテリアル属性を出力 | BaseColor, Specular, Roughness, Normal, WorldHeight, Opacity, Mask, Displacement, Mask4 | - | - |
| `RuntimeVirtualTextureReplace` | 仮想テクスチャレンダリングパス時のロジック切り替え | Default, VirtualTextureOutput | Output | - |
| `RuntimeVirtualTextureSample` | ランタイム仮想テクスチャからサンプリング。複数の出力ピンを持つ | Coordinates, WorldPosition, MipValue, DDX, DDY | BaseColor, Specular, Roughness, Normal, WorldHeight, Mask, Displacement, Mask4 | - |
| `RuntimeVirtualTextureSampleParameter` | ランタイム仮想テクスチャサンプリングのパラメータ版 | Coordinates, WorldPosition, MipValue, DDX, DDY | BaseColor, Specular, Roughness, Normal, WorldHeight, Mask, Displacement, Mask4 | - |
| `SRGBColorToWorkingColorSpace` | sRGB色空間からワーキング色空間に変換 | Input | Output | - |
| `SamplePhysicsIntegerField` | グローバルフィジックスフィールドの整数値をサンプリング | WorldPosition, Target Type | Output | - |
| `SamplePhysicsScalarField` | グローバルフィジックスフィールドのスカラー値をサンプリング | WorldPosition, Target Type | Output | - |
| `SamplePhysicsVectorField` | 物理フィールドベクトル値をサンプリング | WorldPosition, FieldTarget, WorldPositionOriginType | Output | - |
| `Saturate` | saturate(Input)。[0,1]に制限 | Input | Output | - |
| `ScalarBlueNoise` | スカラーブルーノイズをサンプリング | - | Output | - |
| `ScalarParameter` | スカラー値のパラメータ | DefaultValue | Output | - |
| `SceneColor` | 画面座標からシーンカラーをサンプリング | Input, InputMode | RGB, A | - |
| `SceneDepth` | シーンの深度値をサンプリング | Input, InputMode | R | - |
| `SceneDepthWithoutWater` | 水を除いたシーン深度値を取得 | Input, InputMode, FallbackDepth | Output | - |
| `SceneTexelSize` | シーンテクスチャのテクセルサイズ | - | Output | - |
| `SceneTexture` | 画面配置テクスチャ(深度、法線など)をサンプリング | Coordinates, SceneTextureId, Filtered | Color, Size, InvSize | - |
| `ScreenPosition` | スクリーン座標系でのピクセル位置 | - | ViewportUV, PixelPosition | - |
| `SetMaterialAttributes` | 複数の属性を MaterialAttributes 構造体に組み込む | - | Output | - |
| `ShaderStageSwitch` | ピクセル/頂点シェーダステージで異なる入力を選択 | PixelShader, VertexShader | Output | - |
| `ShadingModel` | シェーディングモデルを指定 | ShadingModel | Output | - |
| `ShadingPathSwitch` | シェーディングパスに応じて異なる入力を選択 | Default | Output | - |
| `ShadowReplace` | 影マップレンダリング時に別の入力を使用 | Default, Shadow | Output | - |
| `Sign` | sign(Input)。符号(-1/0/1) | Input | Output | - |
| `Sine` | Sine | Input, Period | Output | - |
| `SingleLayerWaterMaterialOutput` | 単層水マテリアル出力 | ScatteringCoefficients, AbsorptionCoefficients, PhaseG, ColorScaleBehindWater | Output, out1, out2, out3 | - |
| `SkyAtmosphereAerialPerspective` | 大気エアリアルパースペクティブをサンプリング | WorldPosition, WorldPositionOriginType | Output | - |
| `SkyAtmosphereDistantLightScatteredLuminance` | 大気遠距離光の散乱ルミナンス | - | Output | - |
| `SkyAtmosphereLightDirection` | 大気光の方向を取得 | LightIndex | Output | - |
| `SkyAtmosphereLightDiskLuminance` | 大気光ディスクのルミナンス | DiskAngularDiameterOverride, LightIndex | Output | - |
| `SkyAtmosphereLightIlluminance` | 大気光の照度 | WorldPosition, LightIndex, WorldPositionOriginType | Output | - |
| `SkyAtmosphereLightIlluminanceOnGround` | 地上の大気光照度 | LightIndex | Output | - |
| `SkyAtmosphereViewLuminance` | ビュー方向での大気ルミナンス | WorldDirection | Output | - |
| `SkyLightEnvMapSample` | スカイライトキューブマップをサンプリング | Direction, Roughness | Output | - |
| `SmoothStep` | SmoothStep | Min, Max, Value | Output | - |
| `Sobol` | Sobol準ランダム数列サンプラー。2D格子セルと点番号から準ランダム座標を生成 | Cell, Index, Seed | Output | - |
| `SparseVolumeTextureBase` | スパースボリュームテクスチャのベースクラス | - | - | abstract |
| `SparseVolumeTextureObject` | スパースボリュームテクスチャオブジェクトを出力 | - | Output | - |
| `SparseVolumeTextureObjectParameter` | スパースボリュームテクスチャオブジェクトパラメータ | - | Output | - |
| `SparseVolumeTextureSample` | スパースボリュームテクスチャをサンプリング。2つの属性出力を持つ | Coordinates, TextureObject, MipValue, DDX(UVs), DDY(UVs), MipValueMode, SamplerSource | Attributes A, Attributes B | - |
| `SparseVolumeTextureSampleParameter` | スパースボリュームテクスチャサンプリングパラメータ | Coordinates, TextureObject, MipValue, DDX(UVs), DDY(UVs), MipValueMode, SamplerSource | Attributes A, Attributes B | - |
| `SpeedTree` | SpeedTreeアセット用のジオメトリ・風・LOD制御 | GeometryInput, WindInput, LODInput, ExtraBendWS | Output | - |
| `SphereMask` | 球体との距離に基づいてマスク値を生成 | A, B, Radius, Hardness | Output | - |
| `SphericalParticleOpacity` | 球形パーティクルの不透明度を計算 | Density | Output | - |
| `SpriteTextureSampler` | 2D スプライト用のテクスチャサンプラー。SourceTexture またはペーパー2D スプライトの AdditionalSourceTextures をサンプリング | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, AutomaticViewMipBiasValue, MipValueMode, SamplerSource | Output | plugin |
| `SquareRoot` | sqrt(Input)。平方根 | Input | Output | - |
| `StaticBool` | 静的ブール定数（コンパイル時定数） | Value | Output | - |
| `StaticBoolParameter` | 静的ブールパラメータ（DynamicBranch で動的に変更可） | DefaultValue | Output | - |
| `StaticComponentMaskParameter` | 静的成分マスクパラメータ（R/G/B/A から選択） | Input, DefaultR, DefaultG, DefaultB, DefaultA | Output | - |
| `StaticSwitch` | 静的条件分岐（DefaultValue が True なら A、False なら B を出力） | True, False, Value, DefaultValue | Output | - |
| `StaticSwitchParameter` | 静的条件分岐パラメータ（DefaultValue で True/False 分岐） | True, False | Output | - |
| `Step` | Step | Y, X | Output | - |
| `SubstrateAdd` | SubstrateAdd | A, B | Output | - |
| `SubstrateBSDF` | SubstrateBSDF | - | Output | abstract |
| `SubstrateConvertMaterialAttributes` | SubstrateConvertMaterialAttributes | WaterScatteringCoefficients, WaterAbsorptionCoefficients, WaterPhaseG, ColorScaleBehindWater | Output | - |
| `SubstrateConvertToDecal` | SubstrateConvertToDecal | DecalMaterial, Coverage | Output | - |
| `SubstrateEyeBSDF` | SubstrateEyeBSDF | DiffuseColor, Roughness, CorneaNormal, IrisNormal, IrisPlaneNormal, IrisMask, IrisDistance, EmissiveColor | Output | - |
| `SubstrateHairBSDF` | SubstrateHairBSDF | BaseColor, Scatter, Specular, Roughness, Backlit, Tangent, EmissiveColor | Output | - |
| `SubstrateHazinessToSecondaryRoughness` | SubstrateHazinessToSecondaryRoughness | BaseRoughness, Haziness | Second Roughness, Second Roughness Weight | - |
| `SubstrateHorizontalMixing` | SubstrateHorizontalMixing | Background, Foreground, Mix | Output | - |
| `SubstrateLightFunction` | SubstrateLightFunction | Color | Output | - |
| `SubstrateMetalnessToDiffuseAlbedoF0` | SubstrateMetalnessToDiffuseAlbedoF0 | BaseColor, Metallic, Specular | DiffuseAlbedo, F0 | - |
| `SubstratePostProcess` | SubstratePostProcess | Color, Opacity | Output | - |
| `SubstrateSelect` | SubstrateSelect | A, B, SelectValue | Output | - |
| `SubstrateShadingModels` | SubstrateShadingModels | BaseColor, Metallic, Specular, Roughness, Anisotropy, EmissiveColor, Normal, Tangent, SubSurfaceColor, ClearCoat, ClearCoatRoughness, Opacity, TransmittanceColor, WaterScatteringCoefficients, WaterAbsorptionCoefficients, WaterPhaseG, ColorScaleBehindWater, ClearCoatNormal, CustomTangent, ThinTranslucentSurfaceCoverage | Output | - |
| `SubstrateSimpleClearCoatBSDF` | SubstrateSimpleClearCoatBSDF | DiffuseAlbedo, F0, Roughness, ClearCoatCoverage, ClearCoatRoughness, Normal, EmissiveColor, BottomNormal | Output | - |
| `SubstrateSingleLayerWaterBSDF` | SubstrateSingleLayerWaterBSDF | BaseColor, Metallic, Specular, Roughness, Normal, EmissiveColor, TopMaterialOpacity, WaterAlbedo, WaterExtinction, WaterPhaseG, ColorScaleBehindWater | Output | - |
| `SubstrateSlabBSDF` | SubstrateSlabBSDF | DiffuseAlbedo, F0, F90, Roughness, Anisotropy, Normal, Tangent, SSSMFP, SSSMFPScale, SSSPhaseAnisotropy, EmissiveColor, SecondRoughness, SecondRoughnessWeight, FuzzRoughness, FuzzAmount, FuzzColor, GlintValue, GlintUV | Output | - |
| `SubstrateThinFilm` | SubstrateThinFilm | Normal, F0, F90, Thickness, IOR | Specular Color, Edge Specular Color | - |
| `SubstrateToonBSDF` | SubstrateToonBSDF | BaseColor, Metallic, Specular, Roughness, Normal, EmissiveColor, PatternUVs, Anisotropy, Tangent | Output | - |
| `SubstrateTransmittanceToMFP` | SubstrateTransmittanceToMFP | TransmittanceColor, Thickness | MFP, Thickness | abstract |
| `SubstrateUI` | SubstrateUI | Color, Opacity | Output | - |
| `SubstrateUnlitBSDF` | SubstrateUnlitBSDF | EmissiveColor, TransmittanceColor, Normal | Output | - |
| `SubstrateUtilityBase` | SubstrateUtilityBase | - | Output | abstract |
| `SubstrateVerticalLayering` | SubstrateVerticalLayering | Top, Base, Thickness | Output | - |
| `SubstrateVolumetricFogCloudBSDF` | SubstrateVolumetricFogCloudBSDF | Albedo, Extinction, EmissiveColor, AmbientOcclusion | Output | - |
| `SubstrateWeight` | SubstrateWeight | A, Weight | Output | - |
| `SubsurfaceMediumMaterialOutput` | サブサーフェス媒質の平均自由光路と散乱分布を設定（パストレーサー専用） | MeanFreePath, ScatteringDistribution | - | - |
| `Subtract` | A - B。float/vector対応 | A, B | Output | - |
| `Switch` | 条件値に基づいて複数の入力から1つを選択 | SwitchValue, Default | Output | - |
| `Tangent` | Tangent | Input, Period | Output | - |
| `TangentOutput` | カスタムアイタンジェント出力 | Input | - | - |
| `TemporalResponsivenessOutput` | テンポラルアキュムレーションの応答性を制御（実験的） | Input | - | - |
| `TemporalSobol` | テンポラル対応Sobol準ランダム数列サンプラー | Index, Seed | Output | - |
| `TextureBase` | テクスチャサンプル・テクスチャオブジェクトの基底クラス | SamplerType | Output | abstract |
| `TextureCollection` | テクスチャコレクションを参照。テクスチャコレクションオブジェクトと数を出力 | - | TextureCollection, TextureCount | - |
| `TextureCollectionParameter` | テクスチャコレクションパラメータ | - | TextureCollection, TextureCount | - |
| `TextureCoordinate` | テクスチャ座標（UV）出力。タイリングやミラーリング設定対応 | CoordinateIndex, UTiling, VTiling, UnMirrorU, UnMirrorV | Output | - |
| `TextureObject` | テクスチャオブジェクト出力（サンプリングなし）。マテリアル関数用プレビュー値 | - | Output | - |
| `TextureObjectFromCollection` | テクスチャコレクションからテクスチャオブジェクトを取得 | TextureCollection, CollectionIndex | Output | - |
| `TextureObjectParameter` | テクスチャオブジェクトパラメータ（サンプリングなし） | - | Output | - |
| `TextureProperty` | テクスチャプロパティ出力（テクスチャサイズなど） | TextureObject, Property | Output | - |
| `TextureSample` | テクスチャをサンプリング。RGB/R/G/B/A/RGBA複数出力対応 | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameter` | テクスチャサンプルパラメータの基底クラス | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | abstract |
| `TextureSampleParameter2D` | テクスチャパラメータ(2D)。TextureSampleParameterの2D専用版 | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameter2DArray` | テクスチャ配列(2D配列)をサンプリング。パラメータ化可能 | Coordinates, Tex, MipValue, CoordinatesDX, CoordinatesDY, AutomaticViewMipBiasValue, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameterCube` | キューブマップテクスチャパラメータ（サンプリング） | Coordinates, TextureObject, MipValue, CoordinatesDX, CoordinatesDY, Apply View MipBias, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameterCubeArray` | キューブマップ配列をサンプリング。パラメータ化可能 | Coordinates, Tex, MipValue, CoordinatesDX, CoordinatesDY, AutomaticViewMipBiasValue, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameterSubUV` | SubUVアニメーション対応の2Dテクスチャをサンプリング。パラメータ化可能 | Coordinates, Tex, MipValue, CoordinatesDX, CoordinatesDY, AutomaticViewMipBiasValue, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `TextureSampleParameterVolume` | ボリュームテクスチャをサンプリング。パラメータ化可能 | Coordinates, Tex, MipValue, CoordinatesDX, CoordinatesDY, AutomaticViewMipBiasValue, MipValueMode, SamplerSource | RGB, R, G, B, A, RGBA | - |
| `ThinTranslucentMaterialOutput` | 薄型透光材料の透過率と表面被覆率を出力 | TransmittanceColor, SurfaceCoverage | Output, out1 | - |
| `Time` | 時間値を出力。Period で時刻をループさせることが可能。bIgnorePause で一時停止を無視可能 | - | Output | - |
| `Transform` | ベクトルをある座標系から別の座標系に変換 | Input, TransformSourceType, TransformType | Output | - |
| `TransformPosition` | 位置座標をある座標系から別の座標系に変換 | Input, PeriodicWorldTileSize, FirstPersonInterpolationAlpha, TransformSourceType, TransformType | Output | - |
| `Truncate` | trunc(Input)。小数部切り捨て | Input | Output | - |
| `TruncateLWC` | LWC(Large World Coordinate)値の整数部を抽出 | Input | Output | - |
| `TwoSidedSign` | 両面マテリアル時の表裏判定値 | - | Output | - |
| `UIntToFloat` | uint32値をfloatに変換 | Input | Output | - |
| `UserSceneTexture` | ユーザー指定のシーンテクスチャをサンプリング | Coordinates, UserSceneTexture, Filtered, Clamped | Color, Size, InvSize | - |
| `VectorNoise` | 3次元ベクトルとしてノイズを出力。セルノイズ、パーリンノイズ勾配など対応 | Position, Function, Quality, bTiling, TileSize | Output | - |
| `VectorParameter` | ベクトル値のパラメータ（RGB/RGBA） | DefaultValue | RGB, R, G, B, A, RGBA | - |
| `VertexColor` | メッシュの頂点カラーを出力 | - | RGB, R, G, B, A | - |
| `VertexInterpolator` | 頂点シェーダーの値をピクセルシェーダーに補間転送 | VS | PS | - |
| `VertexNormalWS` | 頂点の法線(ワールド座標) | - | Output | - |
| `VertexTangentWS` | 頂点の接線(ワールド座標) | - | Output | - |
| `ViewProperty` | ビュー関連のプロパティ(解像度、FOV、カメラ位置等)を取得 | ViewProperty | Property, InvProperty | - |
| `ViewSize` | ビューのサイズ(幅と高さ) | - | Output | - |
| `VirtualTextureFeatureSwitch` | 仮想テクスチャサポートの有無で分岐 | No, Yes | Output | - |
| `VolumetricAdvancedMaterialInput` | ボリューメトリッククラウド詳細材質入力 | - | ConservativeDensity as Float3, ConservativeDensity as Float4 | - |
| `VolumetricAdvancedMaterialOutput` | ボリューメトリッククラウド詳細材質出力。位相関数、散乱パラメータ等を設定 | PhaseG, PhaseG2, PhaseBlend, MultiScatteringContribution, MultiScatteringOcclusion, MultiScatteringEccentricity, ConservativeDensity | Output, out1, out2, out3, out4, out5, out6 | - |
| `VolumetricCloudEmptySpaceSkippingInput` | ボリューメトリッククラウド空白スキップ用の球体情報(中心、半径)を出力 | - | Sphere Center, Sphere Radius | - |
| `VolumetricCloudEmptySpaceSkippingOutput` | ボリューメトリッククラウド空白スキップ出力。物質が存在するか否かを示す | ContainsMatter | Output | - |
| `WorldPosition` | ワールド座標系での現在のピクセル位置を出力 | Shader Offsets | XYZ, XY, Z | - |
