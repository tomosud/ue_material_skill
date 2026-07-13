# タスク索引 — UE Material Skill

全体計画は [../PLAN.md](../PLAN.md)。1ファイル=1タスク。各タスクは自己完結しており、
安価なAIワーカーに個別発注できる(C系・M02〜M04が特に向く)。

完了したら該当ファイルの `status:` を `DONE` に書き換え、この表も更新すること。

## 依存関係

```
E01(実機サンプル) ──┬─→ T01(T3D仕様) ──┬─→ T03(build.py) ─→ T08(実機検証) ─→ verified昇格
                    │   T02(MGJSON仕様) ┴─→ T04(parse.py)
                    │                      └→ T05(validate.py)
C01..C17(カタログ) ─┴─→ T06(マージ) ──────→ T03が参照
M01(MF形式調査) ────→ M02..M04(MFナレッジ) → T06
T01..T05 ───────────→ T07(SKILL.md)
```

- **今すぐ並列発注可**: C01〜C17、M02〜M04(共通手順書が確定済みのため)、E01、T01、T02、M01
- **MVPクリティカルパス**: E01 → T01/T02 → T03/T04/T05 → T08

## 基盤タスク(T系)— 本体側/能力の高いAIで

| ID | 内容 | 優先 | status |
|---|---|---|---|
| [T01](T01-format-spec.md) | T3D形式仕様書 | A | TODO |
| [T02](T02-mgjson-spec.md) | 中間フォーマットMGJSON仕様書 | A | TODO |
| [T03](T03-build-tool.md) | build.py(MGJSON→T3D、クリップボード書込) | A | TODO |
| [T04](T04-parse-tool.md) | parse.py(T3D→MGJSON、クリップボード読取) | A | TODO |
| [T05](T05-validate-tool.md) | validate.py(MGJSON検証) | A | TODO |
| [T06](T06-catalog-merge.md) | カタログ結合・lint | B | TODO |
| [T07](T07-skill-md.md) | SKILL.md執筆 | A | TODO |
| [T08](T08-editor-verification.md) | 実機検証(ユーザー協働) | A | TODO |

## サンプル収集(ユーザー協働)

| ID | 内容 | 優先 | status |
|---|---|---|---|
| [E01](E01-collect-examples.md) | エディタから実サンプル9点をコピー保存 | A(最初に) | TODO |

## ノードカタログ(C系)— 安価なAIに並列発注

共通手順: [INSTRUCTIONS-catalog.md](INSTRUCTIONS-catalog.md)(スキーマ・抽出ルール)

**対象クラスの確定リスト**: [../catalog/manifest.json](../catalog/manifest.json) —
`Engine/Source` と `Engine/Plugins` の全ヘッダを機械走査した **359クラス**
(クラス名→ヘッダパス→abstract/deprecated/plugin フラグ)。各タスクの対象表は
ここから生成しており、**全クラスがいずれか1つのバッチに漏れなく割当済み**。
再生成は `python tools/gen_manifest_tasks.py`(走査コマンドはスクリプト冒頭に記載)。

| ID | カテゴリ | クラス数 | 優先 | status |
|---|---|---|---|---|
| [C01](catalog/C01.md) | 定数・パラメータ | 15 | A | TODO |
| [C02](catalog/C02.md) | 基本演算 | 20 | A | TODO |
| [C03](catalog/C03.md) | 補間・条件・三角・指数 | 21 | A | TODO |
| [C04](catalog/C04.md) | ベクトル演算・法線 | 14 | A | TODO |
| [C05](catalog/C05.md) | テクスチャ・UV | 13 | A | TODO |
| [C06](catalog/C06.md) | 座標・ジオメトリデータ | 20 | A | TODO |
| [C07](catalog/C07.md) | 時間・ユーティリティ | 18 | A | TODO |
| [C08](catalog/C08.md) | 構造ノード・MaterialAttributes | 17 | A | TODO |
| [C09](catalog/C09.md) | その他(Engine) Absorption〜Convert | 16 | B | TODO |
| [C10](catalog/C10.md) | その他(Engine) CurveAtlas〜EvalPhysicsInteger | 16 | B | TODO |
| [C11](catalog/C11.md) | その他(Engine) EvalPhysicsScalar〜IsFirstPerson | 16 | B | TODO |
| [C12](catalog/C12.md) | その他(Engine) IsOrthographic〜MapARPassthrough | 16 | B | TODO |
| [C13](catalog/C13.md) | その他(Engine) MaterialAttributeLayers〜ParticleMacroUV | 16 | B | TODO |
| [C14](catalog/C14.md) | その他(Engine) ParticleMotionBlurFade〜PreSkinnedLocalBounds | 16 | B | TODO |
| [C15](catalog/C15.md) | その他(Engine) PreSkinnedNormal〜SamplePhysicsScalar | 16 | B | TODO |
| [C16](catalog/C16.md) | その他(Engine) SamplePhysicsVector〜SkyLightEnvMapSample | 16 | B | TODO |
| [C17](catalog/C17.md) | その他(Engine) Sobol〜TextureObjectFromCollection | 16 | B | TODO |
| [C18](catalog/C18.md) | その他(Engine) TextureSampleParameter2DArray〜VolumetricCloud | 15 | B | TODO |
| [C19](catalog/C19.md) | Substrate系(25クラス) | 25 | B | TODO |
| [C20](catalog/C20.md) | プラグイン系 (Experimental) | 6 | B | TODO |
| [C21](catalog/C21.md) | プラグイン系 (Interchange/MaterialX) | 29 | B | TODO |
| [C22](catalog/C22.md) | プラグイン系 (Paper2D 等) | 2 | B | TODO |

その他(Engine)には Landscape 系ノード(LandscapeLayerBlend 等)も含まれる。
除外は内部ヘルパのみ(Utils / sToMIRCommon。ExternalCodeBase はabstractとして収載)。

## Material Function(M系)

共通手順(M02〜M04): [INSTRUCTIONS-mf.md](INSTRUCTIONS-mf.md)

| ID | 内容 | 優先 | status |
|---|---|---|---|
| [M01](M01-mf-call-format.md) | MaterialFunctionCallのT3D形式調査(ソース読解) | A | TODO |
| [M02](M02-mf-texturing-uv.md) | MFナレッジ: Texturing/UV/Procedural | B | TODO |
| [M03](M03-mf-blend-color.md) | MFナレッジ: Blend/Color/Gradient | B | TODO |
| [M04](M04-mf-math-util.md) | MFナレッジ: Math/Opacity/Utility | B | TODO |

## ワーカーへの発注テンプレ

```
リポジトリ: C:\work\script\ue_material_skill
タスク: tasks/catalog/C01.md を読んで実行してください。
共通手順 tasks/INSTRUCTIONS-catalog.md に必ず従うこと。
UEソース: C:\work\unreal\UnrealEngine-release(読み取りのみ)
出力先以外のファイルは変更しないこと。
```
