# T08: 実機検証プロトコル [基盤 / 優先度A / ユーザー協働]

status: WAITING USER（offline QA完了、Unreal Editor steps 1〜9待ち）
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
- [ ] ステップ1〜8がOK、9の結果がformat.mdに反映済み
- [ ] 発見した相違点が全てツール/カタログ/仕様書に反映済み

## 実施メモ（進行中）

- `tasks/verification-log.md` を作成し、自動化可能なvalidate/build/parse/round-trip、
  実sample、catalog無し、MF、clipboard、JSON、skill validatorを全て実行した。
- 手動step 1〜7のMGJSON fixtureと期待値、copy-back手順、verified昇格規則をlogへ固定した。
- build生成T3DのUnreal Editor Ctrl+Vはこの実行環境から操作できないため未判定。
  完了条件を満たしていないので `DONE` / `verified: true` にはしていない。
