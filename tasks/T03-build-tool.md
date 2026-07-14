# T03: build.py — MGJSON → T3D 生成ツール [基盤 / 優先度A]

status: TODO
output: `skill/scripts/build.py`
依存: T01, T02, カタログ最低限(C01+C02があれば着手可)

## 単独実行の前提(外部AI向け)

- このmdと下記「必読」だけで着手可能。会話コンテキストは不要
- 作業ディレクトリ: C:/work/script/ue_material_skill(リポジトリ)
- UEソース: C:/work/unreal/UnrealEngine-release(**読み取り専用**)
- 必読: skill/references/format.md(T01成果物)、skill/references/mgjson.md(T02成果物)、catalog/nodes.json(無ければ catalog/generated/*.json を直接参照)、PLAN.md §2.3
- 変更してよいのは output に書かれた成果物と本mdのみ。完了時は本mdの `status:` を DONE にし、
  成果物パス・未解決点・判断に迷った点を本md末尾に「## 実施メモ」として追記する


## 内容

Python(標準ライブラリのみ)で MGJSON から Material Editor にペースト可能な
T3Dテキストを組み立てる。

- 入力: MGJSONファイル or stdin
- 出力: `--to-clipboard`(PowerShell `Set-Clipboard` 呼び出し。既定)、`-o file`、stdout
- カタログ(`catalog/nodes.json`)からピン構成を引く:
  - 入力ピン: inputs順 + prop_pins順に **全ピン** を PinName 付きで出力
  - 出力ピン: outputs順に全列挙、`Direction="EGPD_Output"`
  - PinId: 決定的でよい(uuid4で採番し両側整合)
- LinkedTo の両方向整合、Expression側入力プロパティ(`A=(Expression=...)`)も出力
  (エディタ出力と同形にして安全側に倒す)
- 自動レイアウト: posが無いノードはトポロジカル順で列配置
  (列間300px、行間180px、リンクの深さで列決定)。pos指定は尊重
- Comment: 包含ノードのバウンディングボックス+マージンでSizeX/SizeYを計算
- エラー処理: カタログに無いクラス/ピン名は明確なエラーメッセージ
  (「エディタからそのノードをコピーして見せて」と促す文言)

## 完了条件
- [ ] PLAN §3.2 のサンプルMGJSONからT3Dが生成できる
- [ ] validate.py(T05)を内蔵チェックとして呼ぶ or 同等チェック
- [ ] クリップボード書き込みがWindowsで動く(pwsh/powershell両対応)
- [ ] 単体テスト: 生成→parse.py(T04)で往復して同型になる
