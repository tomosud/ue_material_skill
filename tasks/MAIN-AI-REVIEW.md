# メインAI向け完成後精査レポート

精査日: 2026-07-14  
対象: `ue-material` skill / UE 5.8.0-55116800  
精査基準commit: `ac9bf91` (`Add UE samples and fix pin parsing`)  
目的: 完了済みタスクの再判定ではなく、広く安全に使える完成度へ上げる次段階を定義する。

## 結論

現在の成果は、UE 5.8の主要な通常Materialノードについて、MGJSON生成・検証・T3D化・
clipboard往復を行う実用的な基盤として成立している。一方、359 node class全体を
「生成まで完全対応」とはまだ表現できない。特に動的Pin、内部object参照、asset依存ノードは、
解析できることと安全に再生成できることを分けて扱う必要がある。

次の開発単位は、以下の順を推奨する。

1. P0: Customの動的Pin往復と既定値を正す。**DONE (2026-07-14)**
2. P0: `verified`を証拠レベルへ分解する。
3. P0: 01〜09実sampleを自動回帰テストへ固定する。
4. P1: Editor自動往復ハーネスを作り、利用頻度上位classを昇格する。
5. P1: catalog生成元、version、実行環境の再現性を整える。

## 現在保証できる範囲

- `validate.py` / `build.py` / `parse.py` の通常ノード、Comment、既知MaterialFunctionCallの
  基本経路は実装済み。
- T08のEditor steps 1〜9はUE 5.8.0実機で成功。
- E01の01〜09は全て実Editor clipboard T3Dとして保存済み。
- 02の異なるnode間でPinIdが重複する実例を検出し、parserは
  `(owner node name, PinId)`で正しく3接続を復元する。
- merged catalogは359 node / 82 functionを収載し、JSONとmanifest coverageは成立している。
- Editor実証済みフラグはnode 6/359（1.7%）、function 1/82（1.2%）。nodeは
  `Comment`、`Constant`、`OneMinus`、`NamedRerouteDeclaration`、`NamedRerouteUsage`、`Custom`、
  functionは`BlendAngleCorrectedNormals`。

ここで注意すべきなのは、前3 nodeはbuild→paste→copy-backを含む一方、Named Rerouteは
手動作成物のcopy解析までであること。同じ`verified: true`でも保証内容が異なる。

## P0: リリース品質の前に実施する項目

### 1. Customをraw保持から意味的な往復へ昇格する — DONE

2026-07-14に実装とUE 5.8実機検証を完了した。正本は`tasks/P01-custom-roundtrip.md`。
LumaSplitのbuild→paste→copy-backでCode、A入力、return+Luma出力、define、2接続を確認し、
実T3Dを`tests/fixtures/p01-custom-lumasplit-copyback.txt`へ固定した。以下の「現状」は実装前の記録。

CustomノードのHLSL生成経路、利用可能関数、texture sampler、SceneTexture専用構文、include mapping、
旧translatorと新Material IRの差は
[`tasks/CUSTOM-NODE-SOURCE-RESEARCH.md`](CUSTOM-NODE-SOURCE-RESEARCH.md)にsource根拠付きで分離した。
実装前に同文書の「結論」「旧translatorと新MIR経路の差」「MGJSON・validatorへの実装要求」を読むこと。

特に、UE 5.8の新MIR経路はnamed input + named additional outputを合計32個に制限し、
additional outputを旧経路の`inout`ではなく`out`として生成する。互換性のため、32個上限を検証し、
追加出力は全制御経路で必ず代入する規約にする。

実装前の現状:

- sample 09は`Code`と`ShowCode`をtyped props、`Inputs(0)` / `Inputs(1)`を`raw_props`へ保持する。
- catalogの`Custom.inputs` / `outputs`は空なので、build側`pin_schema()`はA/B/Output Pinを作れない。
- `validate.py`は`TArray<FCustomInput>`のJSON arrayを型として許すが、buildは通常propertyとして
  一括serializeし、UE実clipboardと同じ索引付き`Inputs(n)`および動的Pin schemaを生成しない。

UE 5.8ソースとの追加照合で、catalogの既定値差異も確認した。

| property | catalogの現在値 | UE 5.8 constructor |
|---|---|---|
| `Code` | `""` | 説明コメント＋`float3(1, 1, 1)` |
| `Description` | `""` | `"Custom"` |
| `OutputType` | `CMOT_Float1` | `CMOT_Float3` |
| `Inputs` | `null` | 空名inputを1件追加 |
| `ShowCode` | `false` | `false`（一致） |

根拠: `MaterialExpressionCustom.h`と`MaterialExpressions.cpp`の
`UMaterialExpressionCustom::UMaterialExpressionCustom`。

推奨設計:

- MGJSONでは`props.Inputs`を`[{"InputName":"A"},{"InputName":"B"}]`のような構造化arrayにする。
- parseは`Inputs(n)`をbase propertyごとに集約する。
- buildは`Inputs(n)=...`、`AdditionalOutputs(n)=...`を索引付きで出す。
- `pin_schema()`はInputsからinput Pin、OutputTypeとAdditionalOutputsから全output Pinを作る。
- AdditionalDefines / IncludeFilePathsも同じindexed-array codecを共有する。
- 不明なstruct fieldだけを局所的raw値として保持し、配列全体をraw escape hatchにしない。

受入条件:

- sample 09をparse→validate→build→UE paste→copy-backし、A/B、Output、Code、OutputTypeが一致。
- A/Bへ接続した3node fixtureで2 linkを保持。
- AdditionalOutputs 2件、AdditionalDefines、IncludeFilePathsのfixtureを追加。
- Customを`roundtrip_verified`へ昇格できる。

### 2. `verified`を証拠レベルへ分解する

単一boolでは、ソース読解、実機copy観測、paste成功、意味的round-tripが区別できない。
誤った安心を避けるため、次のような段階を推奨する。

```json
"verification": {
  "source": true,
  "editor_copy": true,
  "editor_paste": false,
  "roundtrip": false,
  "ue_version": "5.8.0-55116800",
  "sample": "examples/08-named-reroute.txt"
}
```

- 後方互換が必要なら`verified`は`roundtrip`からのみ導出する。
- Named Rerouteは現時点では`editor_copy=true`、`roundtrip=false`が妥当。
- MaterialFunctionCallはasset pathと全Pinを含むpaste/copy-backが成功したentryだけroundtrip扱いにする。
- validator warningには「未検証」だけでなく、到達済みの最高レベルとUE versionを出す。

受入条件:

- catalog全entryが同一のverification schemaを持つ。
- `catalog_merge.py`が不正な昇格やversion欠落を検出する。
- `verification-log.md`と機械可読fieldが矛盾しない。

### 3. 実sampleベースの自動回帰テストを追加する

現状は独立したtest suiteがなく、`catalog/generated/test.json`だけがtest名を持つ。
02の重複PinId問題は最終全件監査まで発見できなかったため、手動QAだけでは再発を防げない。

最低限必要なtest:

- `parse.py`: 01〜09のnode/comment/link/raw count、class、主要propsをassert。
- 02: 異なるownerで同じPinIdでも3 linkになること。
- 03/04: TextureSampleの出力index・maskがGへ戻ること。
- 06: Comment containment normalization。
- 07: MF pathとPin順。
- 08: declaration/usage GUID一致と内部参照のpaste/copy-back。
- 09: P0-1完了後の動的Pin往復。
- validate/build: 既存の破損17パターン、canonical build→parse→build。
- CLI: stdin/file/clipboard失敗時のexit codeと文字コード。

fixtureは`examples/`の生T3Dを正本とし、期待MGJSONを小さなgolden fileにする。
テストがEditor不要の層とEditor必須の層を明確に分ける。

## P1: 信頼範囲を広げる項目

### 4. Named Rerouteの生成往復を実証する

UEソース上、Usageの`PostCopyNode`は`DeclarationGuid`からcopied expressions内のDeclarationを
再探索するため、古い`Declaration` object pathがimport時に解決できなくても回復できる可能性が高い。
ただし現在は手動copy sampleしかなく、buildが生成したpairのpaste/copy-backは未実施。

次のfixtureを実機確認する。

- Declaration + Usageのみ。
- Constant→Declaration、Usage→Multiplyを含む4node/2link。
- 貼付先に同じVariableGuidを持つ既存Declarationがある衝突ケース。
- Usage単独copy/paste時に無関係なDeclarationへ誤接続しないこと。

`Declaration`は一般asset propertyではなく、MGJSONのnode ID参照として表現し、build時に新しい
GraphNode/Expression名へ解決する専用型にすると安全性が上がる。

### 5. Editor自動往復ハーネスを作る

359 classを人手だけで検証するのは現実的でない。Editor Utility、Automation Test、または
小さなEditor pluginを用い、次を機械化する。

1. MGJSON fixtureをT3Dへbuild。
2. test Material graphへimport。
3. ReconstructNode / PostPaste処理後に再export。
4. parseしてcanonical MGJSON比較。
5. node caption、Pin名/方向/順、link、主要property、compile errorを記録。

最初は利用頻度の高い30〜50 classを対象にする。Multiply/Add/Lerp、parameters、texture系、
UV、Fresnel、Clamp、ComponentMask、AppendVector、Transform系、static switch、Substrate主要nodeを
優先する。単に359件を貼るより、頻出classの深い検証を先に行う。

### 6. catalogの生成元を正規化する

確認事項:

- merged `nodes.json`のclass pathは全て正規化済み。
- しかし`catalog/generated/C*.json`にはC++ prefix付き
  `/Script/... .UMaterialExpression...`が123件残る。
- merge時のdefault/inference warningは500件超。

merged fileだけを利用する限り直ちに壊れないが、source artifactを直接読むAIや将来の再生成時に
混乱する。全generated sourceをcanonical schemaへ一度migrationし、mergeの補完警告を0へ近づける。

受入条件:

- generatedにもU prefix付きruntime class pathが0件。
- inferred `prop` / `type` / missing fieldをsource側へ書き戻す。
- merge二重実行でdiff 0、warning 0または承認済みallowlistのみ。

### 7. UE versionとasset provenanceを機械可読にする

catalog rootまたは各entryへ次を持たせる。

- UE semantic versionとfull changelist。
- source commit/hashまたはbranch。
- header/source根拠。
- Editor sample取得version。
- plugin/module、必要feature flag。

5.7/5.8/次versionの差分更新時は、class追加削除、Pin順、default、enum、asset pathを比較する
`catalog_diff.py`を用意する。MFはEngine Content / Asset RegistryからpathとPin schemaをexportする
Editor側補助toolを作り、モデル知識依存を減らす。

### 8. CLIとclipboardの可搬性を上げる

現SKILLは`python`コマンドを前提とするが、このsessionでは`py.exe`と`uv.exe`のみが解決された。
Python launcherを`python`→`py -3`→設定値の順で解決するwrapperまたは明確なsetup診断を用意する。

clipboard処理は`pwsh`がPATHにあれば最優先するが、その実行に失敗してもWindows PowerShellへ
retryしない。候補を順に実行し、成功したものを採用する。`--clipboard-shell` overrideと
`doctor.py`を加えると、Python/catalog/PowerShell/clipboard/encodingを一度に診断できる。

### 9. repo固有toolを可搬化・整理する

- `tools/qa_outputs.py`と`extract_c04_v2.py`は
  `C:\work\unreal\UnrealEngine-release`をhard-codeしている。
- `extract_c04_v2.py`は出力先もこのrepoの絶対pathをhard-codeしている。
- `catalog/generated/test.json`はmerge対象外の一時artifactに見える。

UE source rootをCLI引数または環境変数にし、一時artifactは削除または正式fixtureへ移す。
rootのone-off extractorは`tools/`へ整理し、入力・出力・dry-runを明示する。

## P2: 機能拡張案

### 10. Root接続・material asset作成を別モードにする

clipboard skillではRootを含めず、最終接続を人手にする設計は安全で妥当。ただし完全自動material
作成を求める場合は、T3D clipboardの範囲を広げず、Editor Python/plugin経由の別workflowにする。
既存skillの安全境界を崩さない。

### 11. project-local asset discovery

Editor側でAsset Registryを照会し、Texture、MaterialFunction、ParameterCollectionの存在と型を
JSON exportする補助toolを追加する。validatorへ任意のproject catalogを重ねれば、存在しないasset
pathやproject固有MFのPin違いをbuild前に検出できる。

### 12. layout fidelity

現layoutは通常graphに十分だが、Comment boundsはheuristicで、自由枠とgroup枠が曖昧になる。
`layout_mode: auto|preserve`や明示sizeを導入し、往復比較では意味一致と座標一致を別判定にする。

## 文書上の小さな不整合

- `format.md`のPin表は「PinIdはdocument内で一意」とする一方、解析規約は実sampleに基づき
  `(node name, PinId)`をidentityとする。生成側はglobal uniqueを推奨、解析側はowner付きで
  tolerant、と明記して矛盾を解消する。
- `HANDOFF.md`の「現在実行中」見出しは全task完了後も残っている。内容は完了項目なので
  「実施済み」に変えると再開者が迷わない。
- `verification-log.md`のstep番号とE01 sample番号が並存し、01〜09の意味が二種類ある。
  「T08 Editor step」と「E01 collected sample」を見出しで分離する。

## 推奨マイルストーン

### Milestone A: core hardening

- Custom動的Pin対応。
- verification evidence schema。
- offline regression suite。
- PinId文書整合。
- CLI doctor / shell retry。

完了条件: CIでoffline testが全成功し、CustomとNamed Rerouteを含むEditor round-tripが成功。

### Milestone B: trusted common catalog

- Editor自動往復ハーネス。
- 頻出30〜50 nodeのroundtrip昇格。
- generated補完warningとU prefixを解消。
- version/provenance metadata。

完了条件: 対象classごとにUE version、fixture、Pin schema、roundtrip結果を機械的に追跡可能。

### Milestone C: project integration

- Asset Registry exporter。
- project-local MF/texture validation。
- 必要ならEditor pluginによるmaterial asset作成。

## メインAIへの具体的な次の発注

最初の1タスクは次を推奨する。

> `tasks/MAIN-AI-REVIEW.md`のP0-1を実行する。Customのindexed TArrayをMGJSONへ構造化し、
> parse/validate/buildの動的Pin schemaを実装する。UE 5.8ソースのconstructor既定値へcatalogを
> 修正し、`examples/09-custom.txt`を使ったoffline testを追加する。Editor確認が必要な段階で
> buildしたfixtureをclipboardへ置き、ユーザーへpaste/copy-backを1回だけ依頼する。

この発注では先に`tasks/CUSTOM-NODE-SOURCE-RESEARCH.md`も読むこと。特にMIR互換の32 parameter上限、
additional outputの全経路代入、identifier/sampler衝突検査、virtual include path、SceneTexture直結条件を
受入条件へ追加する。Engine private HLSL symbolを一般向けallowlistにしない。

その後、P0-2とP0-3を同じ変更系列で実施する。広いcatalog昇格はこの基盤が固まってから行う。

## 変更時の注意

- 現在の全task `DONE`は既存scopeの完了を表す。追加改善を始める場合は新taskを作り、既存の
  完了履歴を上書きしない。
- ユーザー所有の未追跡`.claude/settings.local.json`には触れない。
- 作業開始時に`git status`を確認し、以後の変更を意図した単位でcommitする。
- Editor未確認の結果をroundtrip済みとして昇格しない。
