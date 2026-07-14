# T07: SKILL.md 執筆 [基盤 / 優先度A]

status: TODO
output: `skill/SKILL.md`
依存: T01〜T05 完了後

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: PLAN.md 全体、skill/ 配下の全成果物、tasks/INSTRUCTIONS-*.md
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

Claude Skill 本体。frontmatter(name/description トリガー最適化)+ 本文:

- トリガー: UEマテリアル作成/編集/解析、「マテリアルノード」「Material Editor」等
- ワークフロー(厳守手順として記述):
  1. 生成: MGJSONを書く → `validate.py` → `build.py --to-clipboard` →
     ユーザーへ「Material Editorの何もない所で Ctrl+V」+ Root接続の案内
  2. 解析: 「コピーした」と言われたら `parse.py --from-clipboard` を実行(T3Dを読まない)
  3. 改変: parse → MGJSON編集 → build
  4. 未知ノード: ユーザーにエディタでそのノード1個のコピーを依頼 → parse → raw_propsから学習
- MGJSON記法の要約(詳細は references/mgjson.md へ誘導)
- よく使うノードの早見表(頻出20個: クラス名と入出力ピン名)
- 制約の明示: Rootノード不可、MFは呼び出しのみ(中身は作れない)、
  クリップボードはローカル実行時のみ(リモートはファイル渡しにフォールバック)

## 完了条件
- [ ] skill-creator の作法に準拠(500行以内、詳細はreferencesへ)
- [ ] descriptionだけで適切にトリガーする(していけない場合も明記)
