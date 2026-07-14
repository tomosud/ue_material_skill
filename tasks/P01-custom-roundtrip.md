# P01: Customノードのraw保持→意味的round-trip昇格 [MAIN-AI-REVIEW P0-1]

status: DONE (Codex, 2026-07-14)
output: `skill/scripts/{validate,build,parse}.py` 拡張、catalog Custom entry 修正、
`tests/` offline回帰テスト、`skill/references/mgjson.md` Custom節

必読: tasks/MAIN-AI-REVIEW.md P0-1、tasks/CUSTOM-NODE-SOURCE-RESEARCH.md

## 受入条件(発注文より)

- [x] Inputs / AdditionalOutputs / AdditionalDefines / IncludeFilePaths をMGJSONで構造化
- [x] parse / validate / build で indexed TArray と動的Pinを往復
- [x] UE 5.8 constructor既定値へcatalog修正
      (Description="Custom", OutputType=CMOT_Float3, Code=ctor既定, Inputs=[{InputName:""}])
- [x] named input + named additional output 合計32以下を検証
- [x] additional output の全経路代入(静的に断定できなければwarning)
- [x] input/output名: identifier規則、予約語、重複、<TextureName>Sampler衝突を検査
- [x] virtual shader include path 検査(絶対virtual path、`..`拒否)
- [x] SceneTexture の .ID/.Fetch は該当入力がSceneTexture/UserSceneTexture出力0へ直結時のみ許可
- [x] Engine private HLSL関数を一般allowlist化しない(unsafe_internal_api warningのみ)
- [x] examples/09-custom.txt を使うoffline回帰テスト追加
- [x] 旧translatorと新Material IRの差を壊さない(named input接続必須、明示return推奨)
- [x] Editor実機: sample09 round-trip + AdditionalOutputs fixture(ユーザー1操作ずつ)

## UEソース確定事項(実装根拠)

- ctor: `MaterialExpressions.cpp` UMaterialExpressionCustom::UMaterialExpressionCustom
- RebuildOutputs: AdditionalOutputs空→無名出力1本 / あり→"return" + 各named output
  (無名additional outputはPinにならない)
- GraphNodeクラスは `/Script/UnrealEd.MaterialGraphNode_Custom`(sample09と一致)
- FCustomInput{InputName:FName, Input:FExpressionInput(接続はPinが正)} /
  FCustomOutput{OutputName:FName, OutputType:enum} / FCustomDefine{DefineName,DefineValue:FString}

## 実施メモ

- 2026-07-14 実装完了(Editor実機検証を除く)。変更ファイル:
  - `skill/scripts/validate.py`: `custom_pin_schema`(動的Pin)、`_validate_struct_array`、
    `_custom_checks`(identifier/予約語/重複/Sampler衝突/32上限/define/include/return/
    未代入output/unsafe_internal_api)、`_custom_link_checks`(named input接続warning、
    SceneTexture `.ID`/`.Fetch` 直結検査)。link_records収集を追加。
  - `skill/scripts/build.py`: `indexed_array_lines`(TArrayの索引付き行出力、空は`Name=()`)、
    `GRAPH_NODE_CLASSES`(Custom→MaterialGraphNode_Custom)、Python 3.11互換fix
    (asset参照のf-string backslash)。
  - `skill/scripts/parse.py`: `Inputs(n)`等の索引付きprop集約(FCustomInput.Inputは
    Pin LinkedToが正のため破棄)、`dynamic_pins` classのPin名をnode propsから解決。
  - catalog: `catalog/generated/C08.json` + `skill/catalog/nodes.json` のCustomを
    UE5.8 ctor既定値(Description="Custom"/OutputType=CMOT_Float3/Code=ctor既定/
    Inputs=[無名1件])+struct schema+dynamic_pins+choices へ修正。catalog_merge再実行で
    保持されることを確認(normalizations=560で従来同等)。
  - `tests/test_custom_roundtrip.py`: offline回帰14件(sample09含む)全green。
    既存sample 01〜09のparse健全性・02の3link・04のG出力・02のcanonical安定も固定。
  - `skill/references/mgjson.md`: 「動的ピン: Customノード」節を追加。
- `return`検査はUEのsubstring判定より厳しく「comment外の`\breturn\b`」で判定
  (comment内returnがUEの自動wrapを抑止する危険ケースを検出できる)。
- 2026-07-14 Editor実機検証完了。UE 5.8でLumaSplit fixtureをpaste→copy-backし、
  `Code`、`Inputs=[A]`、`AdditionalOutputs=[Luma]`、
  `AdditionalDefines=[MYPROJ_MODE=1]`、`Constant→A`、`Luma→Multiply.A`を確認した。
  実copy-backは`tests/fixtures/p01-custom-lumasplit-copyback.txt`へ保存。
- copy-backで判明した派生field `bShowOutputNameOnPin=True`は`RebuildOutputs()`が
  AdditionalOutputsから再構築するため、`raw_props`へ保持せずparse時に除外するよう修正した。
- 実copy-backのparse→validate→build→parseはraw props 0でcanonical一致。
  offline回帰は16件全green、py_compile成功、catalog merge成功、skill quick validationは
  `Skill is valid!`。Customをgenerated/merged catalogで`verified: true`へ昇格した。

## 残存リスク（P0-1完了を妨げない後続検証）

- `IncludeFilePaths`はoffline canonical往復済みだが、実Editor copy-backは未確認。
- 今回の実機確認はgraphのpaste/copy-back。旧translator・新MIR双方でのmaterial shader compile、
  platform/domain別挙動、include先関数のcompileは別の統合試験が必要。
