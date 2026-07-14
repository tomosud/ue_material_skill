# MaterialFunctionCall T3D 仕様

`UMaterialExpressionMaterialFunctionCall` を MGJSON / T3D から生成するための仕様。
UE 5.8.0 ソースで確認した。`BlendAngleCorrectedNormals` は実機clipboard sampleで
asset path、FunctionInputs / FunctionOutputs、型suffix付きPin表示を確認済み。

## 結論

`MaterialFunction=<asset reference>` だけでは、安全な clipboard T3D としては不足する。
ペースト処理では GraphNode の `ReconstructNode` が
`FMaterialEditor::PostPasteMaterialExpression` より先に実行される。function call の
constructor は input / output / base `Outputs` を空にするため、asset path しかないと
初回 reconstruct で Pin が作られず、後段は `bRecreateAndLinkNode=false` で function 情報だけを
更新するので Pin が戻らない可能性がある。

build.py は次を出す。

1. `MaterialFunction` asset reference。
2. MF catalog 順の `FunctionInputs(n)`。`Input.InputName` と個数が初回 input Pin を作る。
3. MF catalog 順の `FunctionOutputs(n)`。実 asset 更新用の仮 ID / output 情報を持たせる。
4. MF catalog 順の基底 `Outputs(n)`。初回 output Pin を作る正データ。
5. 全 Graph Pin。input は MF 名、output は MF 名、順序は catalog 順。

`ExpressionInputId` / `ExpressionOutputId` は asset 内の実 ID と一致しなくてもよい。build は
有効な一意 GUID を仮採番する。ペースト後 `UpdateFromFunctionResource(false)` が asset から
配列と transient pointer を再取得し、Graph link は後続の
`LinkMaterialExpressionsFromGraph` が Pin `SourceIndex` から式入力へ反映する。

## 根拠となる処理順

| 処理 | ソース |
|---|---|
| function call は初期状態で input/output が空 | `MaterialExpressions.cpp:15663-15674` |
| `FunctionInputs` / `FunctionOutputs` の保存構造 | `MaterialExpressionMaterialFunctionCall.h:21-94` |
| MF asset の input/output 収集と SortPriority 順 sort | `MaterialExpressions.cpp:14114-14159` |
| Graph paste 後に `PostPasteNode` → `ReconstructNode` | `EdGraphUtilities.cpp:232-247` |
| paste 特殊処理は `UpdateFromFunctionResource(false)` | `MaterialEditor.cpp:6519-6526` |
| 特殊処理後に input Pin の required/optional と型付き名を復元 | `MaterialEditor.cpp:6528-6549` |
| asset から配列を更新し、ID 一致なら旧 input 接続を継承 | `MaterialExpressions.cpp:16102-16138` |
| `bRecreateAndLinkNode=false` では GraphNode を再生成しない | `MaterialExpressions.cpp:16164-16192` |

## 保存構造

```cpp
FFunctionExpressionInput {
    transient ExpressionInput;
    FGuid ExpressionInputId;
    FExpressionInput Input;
}

FFunctionExpressionOutput {
    transient ExpressionOutput;
    FGuid ExpressionOutputId;
    FExpressionOutput Output;
}
```

transient な `ExpressionInput` / `ExpressionOutput` object pointer は T3D に書かない。
`UpdateFromFunctionResource` が function asset 内の `FunctionInput` / `FunctionOutput` expression
から再生成する。

### 入出力順

`UMaterialFunction::GetInputsAndOutputs` は function 内 expression を走査し、input / output を
それぞれ `SortPriority` の昇順で sort する（`MaterialExpressions.cpp:14114-14159`）。
MF catalog の `inputs` / `outputs` はこの表示順を記録し、build はその順を変えない。

### Pin 名

- 初回 reconstruct 用 input Pin: catalog の生の `inputs[].name`。
- asset 解決後の input Pin: UE が `<name> (<type>)` に更新する。例 `BaseNormal (V3)`。
  type suffix は `S`, `V2`, `V3`, `V4`, `T2d`, `TCube`, `T2dArr`, `TVol`, `SB`,
  `MA`, `TExt`, `B`, `Stra`（`MaterialExpressions.cpp:15863-15904`）。
- MGJSON の link では suffix を付けず MF catalog の生名を使う。build が T3D の初期名を作り、
  UE が型付き表示へ更新する。
- output Pin は `outputs[].name`。type suffix は付けない。
- required は `FunctionInput.bUsePreviewValueAsDefault` の反転。catalog に情報がなければ
  `required: true` として初期 Pin を作り、paste 後に UE が補正する。

## T3D テンプレート

`BlendAngleCorrectedNormals` を例にした canonical template。GUID と node position は仮値。
class path と object reference の引用規則は `format.md` に従う。

```text
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_0"
   Begin Object Class=/Script/Engine.MaterialExpressionMaterialFunctionCall Name="MaterialExpressionMaterialFunctionCall_0"
   End Object
   Begin Object Name="MaterialExpressionMaterialFunctionCall_0"
      MaterialFunction="/Script/Engine.MaterialFunction'/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals.BlendAngleCorrectedNormals'"
      FunctionInputs(0)=(ExpressionInputId=11111111111111111111111111111111,Input=(OutputIndex=-1,InputName="BaseNormal"))
      FunctionInputs(1)=(ExpressionInputId=22222222222222222222222222222222,Input=(OutputIndex=-1,InputName="AdditionalNormal"))
      FunctionOutputs(0)=(ExpressionOutputId=33333333333333333333333333333333,Output=(OutputName="Result"))
      Outputs(0)=(OutputName="Result")
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionMaterialFunctionCall'MaterialExpressionMaterialFunctionCall_0'"
   NodePosX=-300
   NodePosY=0
   CustomProperties Pin (PinId=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,PinName="BaseNormal",PinType.PinCategory="required",)
   CustomProperties Pin (PinId=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB,PinName="AdditionalNormal",PinType.PinCategory="required",)
   CustomProperties Pin (PinId=CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC,PinName="Result",Direction="EGPD_Output",)
End Object
```

接続 Pin には通常ノードと同じく両方向 `LinkedTo` を加える。Expression 側の
`FunctionInputs(n).Input.Expression` は冗長なので build は出さず、後続の Graph link 反映へ
任せる。

## asset が解決できない場合

存在しない path / 未ロード class は `MaterialFunction == nullptr` になる。paste 特殊処理は
function arrays を空に更新し、`MaterialFunction == nullptr` かつ input/output が空なら
Graph Pin を空にする（`MaterialEditor.cpp:6552-6558`）。結果は pinless な
`Unspecified Function` node で、paste 全体は継続する。

従って validate/build は以下を行う。

- path のローカル実在確認はできないため、MF catalog に一致することを確認する。
- `path_uncertain: true` または `verified: false` は warning。
- MF catalog に path がない / 一致しない場合は dynamic Pin schema を作れないため error。
- Unreal Editor 側で asset が解決できなければ Pin と接続が失われる旨を warning 文に含める。

## MGJSON 表現

```json
{
  "nodes": {
    "mf": {
      "class": "MaterialFunctionCall",
      "props": {
        "MaterialFunction": "/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals.BlendAngleCorrectedNormals"
      }
    }
  }
}
```

`validate.py` / `build.py` は `MaterialFunction` path を M02〜M04 の結合済み MF catalog で
逆引きし、通常の node catalog にある空の dynamic Pin 配列ではなく MF entry の Pin を使う。

## MF catalog の最小スキーマ

top-level key は人間が指定する function 名。各 entry:

| key | 必須 | 型 | 用途 |
|---|---:|---|---|
| `path` | yes | string | `/Engine/.../Name.Name` 形式。MGJSON `MaterialFunction` と一致。 |
| `desc` | yes | string | 機能説明。 |
| `inputs` | yes | array | 表示順の `{name,type,required?,id?}`。 |
| `outputs` | yes | array | 表示順の `{name,type,id?}`。 |
| `usage` | yes | string | 適用場面。 |
| `verified` | yes | bool | 実機検証前は false。 |
| `path_uncertain` | yes | bool | path に確証がなければ true。 |

input / output item:

- `name`: non-empty string。T3D の生 Pin 名。
- `type`: `S|V2|V3|V4|T2d|TCube|T2dArr|TVol|SB|MA|TExt|B|Stra`。
- input `required`: optional bool。省略時 true。
- `id`: optional 32 hex GUID。uasset / 実 sample で確認できたときだけ記録する。
  未記録時は build が仮 GUID を生成する。

build に必要な本質的最小セットは `path` と、順序付きの input/output `name` / `type`。
`required` は初期 UI、`id` は旧接続継承の精度を上げるが、paste 後の Pin link 再反映には
必須ではない。

## 未解決点

- 実 asset の正確な `SortPriority`、input の preview-default 必須性、永続 GUID は
  Engine/Content または function-call clipboard sample がないと確認できない。
- template の最小 field 削減（`FunctionOutputs` を省略できるか等）は T08 で検証する。
- M02〜M04 は原則モデル知識ベース。実機確認済みentryだけ`verified: true`へ昇格し、
  確証のない path は `path_uncertain: true` のまま扱う。
