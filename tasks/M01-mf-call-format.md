# M01: MaterialFunctionCall のT3D形式調査 [MF / 優先度A]

status: DONE
output: `skill/references/mf-call.md`
依存: なし(E01の 07-function-call.txt があれば精度向上)

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: PLAN.md §2、tasks/INSTRUCTIONS-mf.md(スキーマ改訂先)
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

MaterialFunction呼び出しノードをテキスト生成するための調査。UEソースを読む:

- `Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp` の
  `UMaterialExpressionMaterialFunctionCall`(UpdateFromFunctionResource、
  FunctionInputs/FunctionOutputs の構造)
- `Engine/Source/Editor/MaterialEditor/Private/MaterialEditor.cpp:6519`
  (ペースト時のFunctionCall特殊処理 — 既知: `UpdateFromFunctionResource` が
  MFアセットから入出力を再構築する)

明らかにすること:
1. T3Dに最低限必要なプロパティ(`MaterialFunction=` のアセットパスだけで足りるか、
   FunctionInputs/FunctionOutputsの記載は必要か)
2. Pin行のPinName(MF側の入出力名)と順序の決まり方
3. 存在しないMFパスを指定した場合の挙動
4. build.py がMF呼び出しを生成するのに必要なカタログ情報の最小セット
   (→ M02〜M04のMFナレッジのスキーマを確定させる)

## 完了条件
- [x] mf-call.md に上記4点の回答とT3Dテンプレート
- [x] M02〜M04用のMFエントリJSONスキーマを定義して INSTRUCTIONS-mf.md に追記

## 実施メモ

- 成果物: `skill/references/mf-call.md`
- asset path だけでは初回 ReconstructNode に Pin schema がなく不足するため、build.py は
  FunctionInputs / FunctionOutputs / base Outputs と全 Graph Pin を仮生成する方針とした。
- MF Pin は function 内 SortPriority 順。MGJSON / catalog は生名と type を分離し、UE が
  paste 後に input 名へ `(V3)` 等の type suffix と required/optional を復元する。
- `tasks/INSTRUCTIONS-mf.md` に required / id optional field と対応 type を追記した。
- 未解決点: Engine/Content と function-call 実 sample がないため、asset path、永続 ID、
  preview-default、最小 field 削減は T08 で確認が必要。
