# 並列発注台帳(再開手順つき)

開始: 2026-07-14
ワーカー: Claude Haiku サブエージェント(1タスク=1エージェント)

## 再開手順(セッションが途中で切れた場合)

進捗の真実は **ファイル状態** にある。以下で未完了を特定して再発注すればよい:

1. `catalog/generated/<ID>.json` が存在し `python -m json.tool` が通る → そのタスクは完了扱い
2. 存在しない/壊れている → `tasks/catalog/<ID>.md`(M系は `tasks/<ID>-*.md`)を
   下記の発注文テンプレで再発注(status行がTODOのままでも 1. を優先して判断)
3. 全C系完了後: T06(catalog_merge)でマニフェスト突き合わせ → 欠落クラスがあれば
   該当バッチだけ再発注

## 発注文テンプレ(C系)

```
作業ディレクトリ: C:\work\script\ue_material_skill
参照ソース: C:\work\unreal\UnrealEngine-release(読み取り専用)
tasks/catalog/<ID>.md があなたのタスク。
必ず最初に tasks/INSTRUCTIONS-catalog.md を読み、手順・スキーマ・完了条件に従うこと。
対象クラスとヘッダパスはタスク内の表で確定。表以外のクラスを追加しない。
出力は catalog/generated/<ID>.json のみ(ディレクトリが無ければ作る)。
完了したら tasks/catalog/<ID>.md の status: TODO を status: DONE に書き換える。
他のファイルは変更しない。
```

## 発注文テンプレ(M系)

```
作業ディレクトリ: C:\work\script\ue_material_skill
tasks/<ID>.md があなたのタスク。
必ず最初に tasks/INSTRUCTIONS-mf.md を読むこと。
確信のないMaterial Functionは書かない(嘘より欠落がまし)。全エントリ verified: false。
出力は catalog/generated/<ID>-mf.json のみ。
完了したら tasks/<ID>.md の status: TODO を status: DONE に書き換える。
他のファイルは変更しない。
```

## 発注状況

| Wave | タスク | 発注 | 完了確認 |
|---|---|---|---|
| 1 | C01 C02 C03 C04 C05 C06 C07 C08 | 発注済 | **完了・検品済**(138クラス、カバレッジ欠落0) |
| 1 | M02 M03 M04 | 発注済 | **完了**(計82関数、全てverified:false) |
| 2+3 | C09〜C22(14タスク一括) | 発注済 2026-07-14 | |

Wave 1 QA記録: `tools/qa_outputs.py`(cppコンストラクタとの出力ピン照合)で14件検出
→ 実修正10件(VertexColor/DynamicParameter/SceneColor/SceneTexture/EyeAdaptation/
ChannelMaskParameter/PixelDepth/SceneDepth/Composite/PinBase)をカタログに反映済み。
Wave 2+3 の回収後も同スクリプトで検算すること。

## 高性能AI向けタスクの引き渡し

T01〜T08 / M01 は自己完結化済み。`tasks/HANDOFF.md` の発注文で外部AI
(Codex・別セッション等)にmdパスを伝えるだけで実行できる。
推奨: 第1陣 T01+T02+M01+T06 → 第2陣 T03+T04+T05 → T07。

Wave 2/3 は Wave 1 の完了を見て順次発注(一度に大量発注しないための分割。
依存関係はないので、再開時にまとめて発注してもよい)。
