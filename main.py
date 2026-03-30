import os
import json
import subprocess
import requests
import base64
from pathlib import Path
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree as ET

# ========== CONFIGURATION ==========
REPO = os.environ.get('GITHUB_REPO', 'uploadtiktok/DowShorts')
BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
YT_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCLSEQ0cuNz_vJ_H3uXB1R7w"

VIDEO_FOLDER = "shorts"
LAST_ID_FILE = "last_processed_id.json"
BATCH_SIZE = 3 
MAX_ITEMS = 3 # عدد العناصر التي ستبقى في ملف rss.xml الخاص بك
# ====================================

# ========== RSS HELPER FUNCTIONS ==========
def get_local_rss_items():
    """قراءة العناصر الحالية من ملف rss.xml المحلي إذا وجد"""
    path = Path("rss.xml")
    if not path.exists():
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
                filename = link.split('/')[-1]
                items.append({
                    'title': title,
                    'filename': filename,
                    'link': link,
                    'pub_date': pub_date
                })
    except Exception as e:
        print(f"⚠️ Error parsing local RSS: {e}")
    return items

def update_rss_file(new_videos_data):
    """تحديث ملف rss.xml بنفس هيكل الكود الذي أرفقته"""
    print("📡 Updating RSS feed...")
    current_items = get_local_rss_items()
    
    new_items = []
    for filename, title in new_videos_data:
        # رابط الملف الخام على جيت هاب
        video_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{VIDEO_FOLDER}/{filename}"
        pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        new_items.append({
            'title': title,
            'filename': filename,
            'link': video_url,
            'pub_date': pub_date
        })
    
    # الجديدة في الأعلى + القديمة
    all_items = new_items + current_items
    all_items = all_items[:MAX_ITEMS] # الاحتفاظ بالعدد المحدد فقط
    
    # بناء هيكل RSS
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'My YouTube Shorts Feed'
    ET.SubElement(channel, 'link').text = f"https://github.com/{REPO}"
    ET.SubElement(channel, 'description').text = 'Latest downloaded shorts'
    
    for item in all_items:
        node = ET.SubElement(channel, 'item')
        ET.SubElement(node, 'title').text = item['title']
        ET.SubElement(node, 'link').text = item['link']
        ET.SubElement(node, 'pubDate').text = item['pub_date']
        ET.SubElement(node, 'enclosure', url=item['link'], type='video/mp4')
        ET.SubElement(node, 'guid', isPermaLink='false').text = item['link']
    
    # تنسيق XML ليكون جميلاً (Pretty Print)
    xml_str = ET.tostring(rss, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    clean_xml = "\n".join(line for line in pretty_xml.split('\n') if line.strip())
    
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(clean_xml)
    print(f"✅ RSS updated with {len(new_items)} new videos.")

# ========== DOWNLOAD & SYNC LOGIC ==========
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
        print(f"❌ RSS Fetch Error: {e}")
        return []

def download_video(url, title):
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
    
    # تنظيف العنوان ليكون اسم ملف صالح
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_title}.mp4"
    file_path = os.path.join(VIDEO_FOLDER, filename)

    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--js-runtime", "node",
        "--remote-components", "ejs:github",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", file_path,
        url
    ]

    try:
        subprocess.run(command, check=True)
        return filename
    except:
        return None

def main():
    last_id = load_last_id()
    all_shorts = fetch_youtube_shorts()
    
    new_candidates = []
    for item in all_shorts:
        if item['id'] == last_id:
            break
        new_candidates.append(item)
    
    if not new_candidates:
        print("✨ No new videos.")
        return

    new_candidates.reverse() # من الأقدم للأحدث لمعالجة الدفعة بالترتيب
    to_process = new_candidates[:BATCH_SIZE]
    
    downloaded_info = []
    final_id = last_id

    for item in to_process:
        fname = download_video(item['link'], item['title'])
        if fname:
            downloaded_info.append((fname, item['title']))
            final_id = item['id']
        else:
            break

    if downloaded_info:
        update_rss_file(downloaded_info)
        save_last_id(final_id)

if __name__ == "__main__":
    main()
