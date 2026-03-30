import os
import json
import base64
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET

# ========== الإعدادات ==========
TOKEN = os.environ.get('PAT_TOKEN', os.environ.get('GITHUB_TOKEN', ''))
REPO = os.environ.get('GITHUB_REPO', 'uploadtiktok/TikTok')
BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
# رابط خلاصة القناة (بجاد الأثري)
YT_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCLSEQ0cuNz_vJ_H3uXB1R7w"

BATCH_SIZE = 3 # تحميل احدث 3 فيديوهات جديدة فقط
VIDEO_FOLDER = "shorts" # المجلد الذي طلبت التحميل فيه
LAST_ID_FILE = "last_processed_ids.json"
# ==============================

def load_processed_ids():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return json.load(f).get("ids", [])
        except: return []
    return []

def save_processed_ids(ids_list):
    with open(LAST_ID_FILE, 'w') as f:
        json.dump({"ids": ids_list[-50:]}, f)

def fetch_youtube_shorts():
    print(f"📡 جاري فحص خلاصة اليوتيوب...")
    try:
        response = requests.get(YT_RSS_URL)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        
        entries = []
        for entry in root.findall('atom:entry', ns):
            v_id = entry.find('yt:videoId', ns).text
            title = entry.find('atom:title', ns).text
            link = entry.find('atom:link', ns).attrib['href']
            
            # التأكد أن المقطع من نوع Shorts
            if "/shorts/" in link:
                entries.append({'id': v_id, 'title': title, 'link': link})
        return entries
    except Exception as e:
        print(f"❌ خطأ في جلب الخلاصة: {e}")
        return []

def download_video(url, title):
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)

    # استخدام نفس الأوامر التي نجحت معك سابقاً
    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--js-runtime", "node",
        "--remote-components", "ejs:github",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", f"{VIDEO_FOLDER}/%(title)s.%(ext)s",
        "--no-playlist",
        url
    ]

    try:
        print(f"📥 جاري تحميل: {title}")
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"⚠️ فشل تحميل المقطع: {title}")
        return False

def main():
    processed_ids = load_processed_ids()
    all_shorts = fetch_youtube_shorts()
    
    # تصفية المقاطع الجديدة فقط (التي لم يسبق تحميلها)
    new_shorts = [s for s in all_shorts if s['id'] not in processed_ids]
    
    if not new_shorts:
        print("📭 لا توجد مقاطع Shorts جديدة.")
        return

    # أخذ أحدث 3 فيديوهات (تكون في أعلى الخلاصة عادةً)
    to_process = new_shorts[:BATCH_SIZE]
    print(f"🚀 تم العثور على {len(to_process)} مقاطع جديدة.")

    downloaded_ids = []
    for item in to_process:
        success = download_video(item['link'], item['title'])
        if success:
            downloaded_ids.append(item['id'])

    if downloaded_ids:
        save_processed_ids(processed_ids + downloaded_ids)
        print(f"✅ تم الانتهاء من معالجة {len(downloaded_ids)} فيديو بنجاح.")

if __name__ == "__main__":
    main()
