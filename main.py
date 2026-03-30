import os
import json
import subprocess
import requests
from pathlib import Path
from xml.etree import ElementTree as ET

# ========== الإعدادات ==========
YT_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCLSEQ0cuNz_vJ_H3uXB1R7w"
VIDEO_FOLDER = "shorts"
LAST_ID_FILE = "last_processed_id.json"
BATCH_SIZE = 3 # سيعالج 3 فقط في كل مرة
# ==============================

def load_last_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return json.load(f).get("last_id", None)
        except: return None
    return None

def save_last_id(video_id):
    with open(LAST_ID_FILE, 'w') as f:
        json.dump({"last_id": video_id}, f)

def fetch_youtube_shorts():
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
            
            if "/shorts/" in link:
                entries.append({'id': v_id, 'title': title, 'link': link})
        return entries
    except Exception as e:
        print(f"❌ خطأ في جلب الخلاصة: {e}")
        return []

def download_video(url, title):
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)

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
    except:
        return False

def main():
    last_saved_id = load_last_id()
    all_shorts = fetch_youtube_shorts()
    
    if not all_shorts:
        print("📭 الخلاصة فارغة.")
        return

    # استخراج كافة المقاطع الجديدة (التي لم تعالج بعد)
    new_candidates = []
    for item in all_shorts:
        if item['id'] == last_saved_id:
            break
        new_candidates.append(item)
    
    if not new_candidates:
        print("✨ لا توجد فيديوهات جديدة.")
        return

    # بما أن القائمة مرتبة من الأحدث للأقدم، سنعكسها لنبدأ من الأقدم (الأقرب للـ ID القديم)
    # ونأخذ أول 3 فقط (Batch)
    new_candidates.reverse() 
    to_process = new_candidates[:BATCH_SIZE]
    
    print(f"🚀 تم العثور على {len(new_candidates)} مقطع جديد إجمالاً.")
    print(f"📦 سيتم معالجة {len(to_process)} مقاطع في هذه الدفعة.")

    last_successful_id = None
    for item in to_process:
        if download_video(item['link'], item['title']):
            last_successful_id = item['id']
        else:
            # إذا فشل مقطع، نتوقف عند آخر مقطع نجح لنحاول مرة أخرى لاحقاً
            break

    # تحديث المرجع بآخر مقطع تم تحميله فعلياً في هذه الدفعة
    if last_successful_id:
        save_last_id(last_successful_id)
        print(f"✅ تم تحديث المرجع إلى: {last_successful_id}")

if __name__ == "__main__":
    main()
