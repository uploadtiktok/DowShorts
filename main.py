import os
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree as ET

# ========== CONFIGURATION ==========
REPO = "uploadtiktok/DowShorts"
BRANCH = "main"
YT_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCLSEQ0cuNz_vJ_H3uXB1R7w"

VIDEO_FOLDER = "shorts"
LAST_ID_FILE = "last_processed_id.json"
BATCH_SIZE = 3 
MAX_ITEMS = 3 

# Telegram Settings
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# ====================================

def send_telegram_msg(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def get_local_rss_items():
    path = Path("rss.xml")
    if not path.exists() or path.stat().st_size == 0:
        return []
    items = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            if link:
                items.append({'title': title, 'link': link, 'pub_date': pub_date})
    except: return []
    return items

def cleanup_shorts_folder(keep_filenames):
    folder = Path(VIDEO_FOLDER)
    if not folder.exists(): return
    for file_path in folder.glob("*.mp4"):
        if file_path.name not in keep_filenames:
            try:
                file_path.unlink()
            except: pass

def update_rss_file(new_videos_data):
    current_items = get_local_rss_items()
    new_items = []
    for filename, title in new_videos_data:
        video_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{VIDEO_FOLDER}/{filename}"
        pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        new_items.append({'title': title, 'link': video_url, 'pub_date': pub_date})
    
    all_items = (new_items + current_items)[:MAX_ITEMS]
    keep_filenames = [item['link'].split('/')[-1] for item in all_items]
    cleanup_shorts_folder(keep_filenames)
    
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'My YouTube Shorts Feed'
    ET.SubElement(channel, 'link').text = f"https://github.com/{REPO}"
    
    for item in all_items:
        node = ET.SubElement(channel, 'item')
        ET.SubElement(node, 'title').text = item['title']
        ET.SubElement(node, 'link').text = item['link']
        ET.SubElement(node, 'pubDate').text = item['pub_date']
        ET.SubElement(node, 'enclosure', url=item['link'], type='video/mp4')
        ET.SubElement(node, 'guid', isPermaLink='false').text = item['link']
    
    xml_str = ET.tostring(rss, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
    clean_xml = "\n".join(line for line in pretty_xml.split('\n') if line.strip())
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(clean_xml)

def download_video(url, title):
    Path(VIDEO_FOLDER).mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_title}.mp4"
    file_path = os.path.join(VIDEO_FOLDER, filename)
    command = [
        "yt-dlp", "--cookies", "cookies.txt", "--js-runtime", "node",
        "--remote-components", "ejs:github", "-f", 
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4", "-o", file_path, url
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return filename
        else:
            error_msg = result.stderr
            if "Sign in to confirm your age" in error_msg or "cookie" in error_msg.lower():
                send_telegram_msg(f"⚠️ <b>تنبيه من DowShorts:</b>\nيبدو أن الكوكيز قد انتهت صلاحيته! يرجى تجديده فوراً.")
            return None
    except: return None

def main():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, 'r') as f:
            last_id = json.load(f).get("last_id")
    else: last_id = None

    try:
        response = requests.get(YT_RSS_URL, timeout=10)
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        all_shorts = []
        for entry in root.findall('atom:entry', ns):
            v_id = entry.find('yt:videoId', ns).text
            title = entry.find('atom:title', ns).text
            link = entry.find('atom:link', ns).attrib['href']
            if "/shorts/" in link:
                all_shorts.append({'id': v_id, 'title': title, 'link': link})
    except: return

    new_candidates = []
    for item in all_shorts:
        if item['id'] == last_id: break
        new_candidates.append(item)
    
    if not new_candidates: return

    new_candidates.reverse()
    to_process = new_candidates[:BATCH_SIZE]
    downloaded_info = []
    final_id = last_id

    for item in to_process:
        fname = download_video(item['link'], item['title'])
        if fname:
            downloaded_info.append((fname, item['title']))
            final_id = item['id']
        else: break

    if downloaded_info:
        update_rss_file(downloaded_info)
        with open(LAST_ID_FILE, 'w') as f:
            json.dump({"last_id": final_id}, f)
        # إرسال تقرير نجاح (اختياري)
        send_telegram_msg(f"✅ <b>تم تحميل مقاطع جديدة:</b>\nتمت معالجة {len(downloaded_info)} فيديو بنجاح.")

if __name__ == "__main__":
    main()
