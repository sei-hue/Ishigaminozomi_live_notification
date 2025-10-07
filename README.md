# YouTube Live Notifier (annouce_ishigami)

石神のぞみ などの複数 YouTube チャンネルのライブ開始を検知して、Windows の通知を出す軽量スクリプトです。

主な特徴

- 複数チャンネルを `config.json` の `CHANNEL_IDS` に指定して監視可能
- サムネイルを通知アイコンに利用（Pillow がインストールされている場合）
- `winotify` があれば通知のアイコン表示やクリックで URL を開く動作が使える
- Task Scheduler（タスクスケジューラ）で定期実行することを想定

## ファイル構成

プロジェクト例:

```
annouce_ishigami/
├─ annouce_ishigami.py   # メインスクリプト
├─ config.json            # 設定 (API_KEY, CHANNEL_IDS, CHECK_INTERVAL)
├─ run_once.py            # ワンショット実行用ラッパー（1回だけ実行）
├─ run_wrapper.bat        # タスクスケジューラ用のバッチ（作業ディレクトリを合わせるため）
└─ README.md
```

## 必要なライブラリ

推奨 (通知とサムネイル表示をフルに使うため):

```
pip install requests pillow win10toast winotify
```

- `requests` : YouTube Data API 呼び出し
- `pillow` : サムネイルを .ico に変換する場合に使用（任意）
- `win10toast` / `winotify` : Windows 通知。`winotify` があるとアイコンやクリック動作がより確実に使えます。

簡単にまとめた `requirements.txt` を作る場合:

```
requests
pillow
win10toast
winotify
```

## 設定 (`config.json`)

例:

```json
{
  "API_KEY": "YOUR_YOUTUBE_API_KEY",
  "CHANNEL_IDS": ["UCtLfA_qUqCJtjXJM2ZR_keg", "UCxxxxxx..."],
  "CHECK_INTERVAL": 300
}
```

- `API_KEY` : YouTube Data API v3 の API キー
- `CHANNEL_IDS` : 監視したいチャンネル ID の配列
- `CHECK_INTERVAL` : スクリプト内での待機秒数（run-once で使う場合は不要。タスクスケジューラで呼ぶ場合は短めに設定しない方が良い）

※ スクリプトは相対パスで `config.json` を読みます。スケジューラで実行する場合は作業ディレクトリをプロジェクト直下に合わせるか、ラッパー `.bat` を使ってください。

## 実行方法

- 単発で動作確認する場合:

```powershell
C:\Path\To\Python\python.exe run_once.py
```

- 常駐ではなく定期的に実行する（推奨）: `run_wrapper.bat` を作成してタスクスケジューラで呼び出す。

`run_wrapper.bat` の例（プロジェクト直下に配置）:

```bat
@echo off
cd /d C:\Users\progr\dev\enviroment-setting\annouce_ishigami
"C:\Users\progr\AppData\Local\Programs\Python\Python313\python.exe" run_once.py
```

## タスクスケジューラで 5 分ごとに実行する（例）

PowerShell またはコマンドプロンプトで実行:

```powershell
schtasks /Create /SC MINUTE /MO 5 /TN "YouTubeNotifierCheck" /TR '"C:\Users\progr\dev\enviroment-setting\annouce_ishigami\run_wrapper.bat"' /F
schtasks /Run /TN "YouTubeNotifierCheck"
```

または PowerShell の ScheduledTask API を使う方法（作業ディレクトリを明示する）:

```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Windows\System32\cmd.exe' -Argument '/c "cd /d C:\Users\progr\dev\enviroment-setting\annouce_ishigami && C:\Users\progr\AppData\Local\Programs\Python\Python313\python.exe run_once.py"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "YouTubeNotifierCheck" -Action $action -Trigger $trigger -Description "Check YouTube live every 5 minutes" -User $env:USERNAME
Start-ScheduledTask -TaskName "YouTubeNotifierCheck"
```

注意: 通知を表示させたい場合はタスクの登録時に「現在ログオンしているユーザーで実行」設定にするか、GUI で `Run only when user is logged on` を選択してください。SYSTEM や別ユーザーで実行するとデスクトップ通知が表示されない場合があります。

## よくあるトラブルと対処

- 通知に画像が出ない／クリックで Chrome ではなく Edge が開く

  - OS の既定ブラウザ設定に依存します。スクリプト側で強制的に Chrome を開く方法は限定的で、一般的には既定ブラウザを Chrome にするのが確実です。

- Pillow が無いとサムネイルは通知アイコンになりません（代わりにサムネ URL を通知本文に含めます）。

- `winotify` がインストールされていると通知のアイコン表示やアクションがより確実に動作します。インストール方法:

```powershell
pip install winotify
```

- タスクを作ったのに通知が出ない
  - タスクの実行ユーザーがログオンしているか、タスクの履歴（History）や Last Run Result を確認してください。

## 拡張案（今後できること）

- 通知済み動画 ID の永続化（ファイル／SQLite）
- ログのローテーション（logging モジュール）
- 通知クリックで特定のブラウザプロファイルや既存タブを使う改善（要追加実装）

---

必要ならこの README にサンプル `requirements.txt` を追加したり、実際にタスクを作成するコマンドを代行で実行することもできます。どこを補足しましょうか？
