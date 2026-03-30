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
BATCH_SIZE = 3 # أقصى عدد للفيديوهات الجديدة في كل تشغيل
# ==============================

def load_last_id():
    """تحميل آخر معرف فيديو تم معالجته بنجاح"""
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return json.load(f).get("last_id", None)
        except: return None
    return None

def save_last_id(video_id):
    """حفظ المعرف الجديد ليكون المرجع في التشغيل القادم"""
    with open(LAST_ID_FILE, 'w') as f:
        json.dump({"last_id": video_id}, f)

def fetch_youtube_shorts():
    """جلب المقاطع من الخلاصة مع التأكد أنها Shorts"""
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
    """التحميل باستخدام yt-dlp بالمجلد المحدد"""
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

    new_to_download = []
    
    # بما أن الأحدث في الأعلى، نبحث حتى نصل للـ ID القديم
    for item in all_shorts:
        if item['id'] == last_saved_id:
            break # توقف هنا، كل ما هو أسفل تم معالجته سابقاً
        new_to_download.append(item)
    
    if not new_to_download:
        print("✨ لا توجد فيديوهات أحدث من آخر فيديو معالج.")
        return

    # معالجة أحدث 3 فيديوهات فقط من القائمة الجديدة
    to_process = new_to_download[:BATCH_SIZE]
    print(f"🚀 تم العثور على {len(to_process)} مقطع جديد.")

    successfully_downloaded_ids = []
    
    # التحميل (نبدأ من الأقدم في القائمة الجديدة للأحدث ليكون الـ ID الأخير هو الأحدث فعلياً)
    for item in reversed(to_process):
        if download_video(item['link'], item['title']):
            successfully_downloaded_ids.append(item['id'])

    # حفظ آخر ID تم تحميله بنجاح ليكون المرجع القادم
    if successfully_downloaded_ids:
        # آخر عنصر في القائمة (بسبب reversed) هو الأحدث زمنياً
        save_last_id(successfully_downloaded_ids[-1])
        print(f"✅ تم تحديث المرجع إلى آخر فيديو محمل: {successfully_downloaded_ids[-1]}")

if __name__ == "__main__":
    main()
