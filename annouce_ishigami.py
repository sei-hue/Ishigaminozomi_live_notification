import requests
import json
from win10toast import ToastNotifier
import time

# ======================
# 設定
# ======================
with open('config.json', 'r') as f:
    config = json.load(f)

API_KEY = config["API_KEY"]
CHANNEL_ID = config["CHANNEL_ID"]
CHECK_INTERVAL = config["CHECK_INTERVAL"]

# 通知オブジェクト
toaster = ToastNotifier()

def check_live_status():
    """YouTube Data APIを使ってライブ配信をチェック"""
    url = f"https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": CHANNEL_ID,
        "eventType": "live",
        "type": "video",
        "key": API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # ライブ配信が見つかった場合
        if "items" in data and len(data["items"]) > 0:
            live_title = data["items"][0]["snippet"]["title"]
            video_id = data["items"][0]["id"]["videoId"]
            live_url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"🔴 ライブ配信中: {live_title}")
            toaster.show_toast(
                "YouTube Live通知",
                f"ライブが始まりました！\n{live_title}",
                duration=10
            )
            # 自動でブラウザを開く
            #webbrowser.open(live_url)
        else:
            print("🟢 現在ライブは行われていません。")

    except Exception as e:
        print(f"⚠️ エラーが発生しました: {e}")

if __name__ == "__main__":
    print("🎬 YouTubeライブ通知システム起動中...")
    while True:
        check_live_status()
        time.sleep(CHECK_INTERVAL)