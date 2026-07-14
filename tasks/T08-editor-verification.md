# T08: 実機検証プロトコル [基盤 / 優先度A / ユーザー協働]

status: DONE
output: `tasks/verification-log.md`(検証結果の記録)、カタログの verified 昇格
依存: T03, T04

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: PLAN.md §5(リスク)、skill/scripts/build.py・parse.py
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

生成したT3Dを実際のUnreal Editorに貼って検証する。ユーザーの操作が必要なので、
1回のセッションでまとめて検証できるようチェックリスト化する。

### 検証ステップ(段階的に)

1. **最小**: Constant3Vector 1個 → 貼れるか
2. **接続**: Constant × 2 → Multiply → 接続が復元されるか
3. **複数出力**: TextureSample の G だけを Multiply.A へ → 誤配線しないか(重要)
4. **パラメータ**: ScalarParameter(名前・デフォルト値・グループ)
5. **アセット参照**: TextureSampleParameter2D + エンジン標準テクスチャパス
6. **プロパティピン**: Constant の Value ピン等、ShowAsInputPin の挙動
7. **コメント**: Comment枠+包含ノード
8. **往復**: エディタでコピー → parse → build → 貼り直し → 同じグラフになるか
9. **最小化テスト**: Pin行のフィールドをどこまで削れるか(PinType省略等)

### 記録フォーマット

各項目: UEバージョン / 結果(OK/NG) / NG時の症状とT3D差分 / カタログ・ツールへの反映内容

### 検証済みクラスの昇格

round-tripが通ったクラスは catalog の `verified: true` に更新(スクリプトで一括)。

## 完了条件
- [x] ステップ1〜8がOK、9の結果がformat.mdに反映済み
- [x] 発見した相違点が全てツール/カタログ/仕様書に反映済み

## 実施メモ（進行中）

- `tasks/verification-log.md` を作成し、自動化可能なvalidate/build/parse/round-trip、
  実sample、catalog無し、MF、clipboard、JSON、skill validatorを全て実行した。
- 手動step 1〜7のMGJSON fixtureと期待値、copy-back手順、verified昇格規則をlogへ固定した。
- build生成T3DのUnreal Editor Ctrl+Vはこの実行環境から操作できないため未判定。
  完了条件を満たしていないので `DONE` / `verified: true` にはしていない。
- 2026-07-14: ユーザー提供画像でstep 1を確認。Constant3Vectorが貼られ、
  X/R=0.2、Y/G=0.5、Z/B=0.9とプレビュー色がfixtureに一致したためOK。
- 2026-07-14: ユーザー提供画像でstep 2を確認。Constant 0.25 / 2.0から
  Multiply A / Bへの2接続がfixtureどおり復元されたためOK。
- 2026-07-14: ユーザー提供画像でstep 3を確認。TextureSampleのG（output index 2）から
  Multiply.Aへ接続され、複数出力の順序が正しく復元されたためOK。
- 2026-07-14: ユーザー提供画像でstep 4を確認。ScalarParameterのName=`Strength`、
  Default=`0.75`、Group=`Controls`（Sort Priority=`32`）が一致したためOK。
- 2026-07-14: ユーザー提供画像でstep 5を確認。TextureSampleParameter2Dの
  Name=`BaseTexture`とDefaultTexture asset参照・previewが正しく復元されたためOK。
- 2026-07-14: ユーザー提供画像でstep 6を確認。Constant出力から別Constantの
  `Value` property Pinへ接続され、paste後もPin/linkが保持されたためOK。
- 2026-07-14: ユーザー提供画像でstep 7を確認。青系`Invert` Comment枠が
  Constant 0.4とOneMinusおよび内部linkを適切なmarginで包含したためOK。
- 2026-07-14: step 8の最初のcopy-backでEditorによるComment geometry微調整を検出。
  `parse.py` の完全一致判定をtight-enclosure（各辺0〜200px）へ修正し、再copy待ち。
- 2026-07-14: 修正版で実copy-backを再解析。2 nodes / 1 Comment / 1 link、raw props 0、
  Comment包含nodes復元を確認し、再build T3Dをclipboardへ格納。再paste画像待ち。
- 2026-07-14: 再paste画像で元graphとの同型を確認しstep 8 OK。Constant / OneMinus /
  Commentはcatalog verified昇格対象。残りはPinType省略のstep 9。
- 2026-07-14: step 9で全7 Pinの`PinType.*`を省略してもConstant値とMultiply A/B接続が
  完全復元。build.py/format.mdへ反映し、Constant/OneMinus/Commentをverified昇格。
- 最終QAはcatalog 359/359、verified 3、PinType field 0、通常/Comment round-trip、
  py_compile、`git diff --check`を通過した。
