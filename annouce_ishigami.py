import requests
import json
from win10toast import ToastNotifier
import time
import threading
import tempfile
import os
import io
try:
    from winotify import Notification, audio
    WINOTIFY_AVAILABLE = True
except Exception:
    WINOTIFY_AVAILABLE = False

# Pillow は任意依存: インストールされていればサムネイルを .ico に変換して通知アイコンに利用する
try:
    from PIL import Image
except Exception:
    Image = None

# ======================
# 設定
# ======================
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

API_KEY = config.get("API_KEY")
CHANNEL_IDS = config.get("CHANNEL_IDS", [])
CHECK_INTERVAL = config.get("CHECK_INTERVAL", 300)

# 通知オブジェクト
toaster = ToastNotifier()

# 通知済みの動画IDを保持して二重通知を防ぐ
notified_videos = set()
# チャンネルID -> チャンネル名 をキャッシュ
channel_titles = {}
channel_titles_lock = threading.Lock()

def get_channel_title(channel_id):
    """チャンネル名を取得してキャッシュする。失敗時は channel_id を返す。"""
    with channel_titles_lock:
        if channel_id in channel_titles:
            return channel_titles[channel_id]

    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet",
        "id": channel_id,
        "key": API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        d = r.json()
        if "items" in d and len(d["items"]) > 0:
            title = d["items"][0]["snippet"].get("title")
            if title:
                with channel_titles_lock:
                    channel_titles[channel_id] = title
                return title
    except Exception as e:
        print(f"⚠️ チャンネル名取得に失敗しました ({channel_id}): {e}")

    return channel_id


def _remove_file_later(path, delay=30):
    """通知に使った一時アイコンを delay 秒後に削除する（削除失敗は無視）。"""
    def _worker():
        try:
            time.sleep(delay)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    # 削除に失敗しても無視
                    pass
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def check_channel_live(channel_id):
    """指定チャンネルのライブ配信をチェックし、見つかれば通知する"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "eventType": "live",
        "type": "video",
        "key": API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            item = data["items"][0]
            live_title = item["snippet"].get("title")
            video_id = item["id"].get("videoId")
            channel_title = item["snippet"].get("channelTitle")
            # サムネイルは動画サムネイルを利用
            thumbnails = item["snippet"].get("thumbnails", {})
            # 可能な限り高解像度のサムネイルを選ぶ
            thumb_url = None
            for key in ("maxres", "high", "medium", "default"):
                if key in thumbnails and thumbnails[key].get("url"):
                    thumb_url = thumbnails[key]["url"]
                    break

            live_url = f"https://www.youtube.com/watch?v={video_id}"

            if video_id and video_id not in notified_videos:
                notified_videos.add(video_id)
                print(f"🔴 [{channel_id}] {channel_title} - ライブ配信中: {live_title} ({live_url})")

                # 通知テキストにチャンネル名とサムネイル URL を含める
                notification_text = f"{channel_title}\n{live_title}\n{live_url}"

                icon_path = None
                # Pillow があればサムネイルを取得して .ico に変換して通知アイコンとして使用する
                if Image and thumb_url:
                    try:
                        r = requests.get(thumb_url, timeout=10)
                        r.raise_for_status()
                        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                        # アイコンサイズにリサイズ
                        icon_size = (64, 64)
                        img = img.resize(icon_size, Image.LANCZOS)
                        tmp_dir = tempfile.gettempdir()
                        icon_path = os.path.join(tmp_dir, f"yt_{video_id}.ico")
                        img.save(icon_path, format="ICO")
                    except Exception as e:
                        # サムネ取得/変換に失敗したらログに出すが通知自体は続行
                        print(f"⚠️ サムネ取得/変換に失敗しました: {e}")
                        icon_path = None

                # アイコンがある場合は指定、なければテキストにサムネURLを追加
                if not icon_path and thumb_url:
                    notification_text += f"\nサムネ: {thumb_url}"

                # 通知を出す（winotify があればそちらを優先してアイコン表示を試みる）
                try:
                    if WINOTIFY_AVAILABLE:
                        # winotify は icon をアプリロゴとして表示できる
                        n = Notification(app_id="YouTubeNotifier",
                                         title=f"{channel_title}",
                                         msg=f"{live_title}\n{live_url}",
                                         icon=icon_path if icon_path else None)
                        # クリックでブラウザを開くアクションを追加（可能なら Chrome ランチャーを使う）
                        try:
                            n.add_actions(label="開く", launch=live_url)
                        except Exception:
                            pass
                        try:
                            n.set_audio(audio.Default, loop=False)
                        except Exception:
                            pass
                        n.show()
                        if icon_path:
                            _remove_file_later(icon_path)
                    else:
                        if icon_path:
                            toaster.show_toast("YouTube Live通知", notification_text, icon_path=icon_path, duration=10)
                            # 通知で使った一時ファイルを後で削除
                            _remove_file_later(icon_path)
                        else:
                            toaster.show_toast("YouTube Live通知", notification_text, duration=10)
                except Exception as e:
                    print(f"⚠️ 通知表示に失敗しました: {e}")
            else:
                # すでに通知済みの動画
                print(f"（通知済）[{channel_id}] {live_title}")
        else:
            # 配信が見つからない場合でもチャンネル名を表示
            ch_title = get_channel_title(channel_id)
            print(f"🟢 [{ch_title}] 現在ライブは行われていません。")

    except Exception as e:
        print(f"⚠️ [{channel_id}] エラーが発生しました: {e}")

def check_all_channels():
    """すべてのチャンネルを順番にチェックする"""
    threads = []
    for ch in CHANNEL_IDS:
        t = threading.Thread(target=check_channel_live, args=(ch,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    print("🎬 YouTubeライブ通知システム起動中...")
    if not API_KEY or not CHANNEL_IDS:
        print("設定が不十分です。config.json に API_KEY と CHANNEL_IDS を設定してください。")
        raise SystemExit(1)

    while True:
        check_all_channels()
        time.sleep(CHECK_INTERVAL)