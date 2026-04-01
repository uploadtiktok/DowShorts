import os
import subprocess
import asyncio
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

# ========== CONFIGURATION ==========
CURRENT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = CURRENT_DIR.parent

VIDEO_FOLDER = CURRENT_DIR / "shorts"
LAST_VIDEO_FILE = CURRENT_DIR / "last_video.json"
COOKIES_FILE = ROOT_DIR / "cookies.txt"

# YouTube API Settings
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = "UCLSEQ0cuNz_vJ_H3uXB1R7w"

# Telegram Settings
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

# Telegram Notifications (اختياري)
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# ====================================

def send_telegram_msg(message):
    """إرسال إشعار عبر تيليجرام (اختياري)"""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=15)
    except:
        pass

def parse_duration(duration):
    """تحويل مدة الفيديو من ISO 8601 إلى ثواني"""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def get_video_info(video_id):
    """جلب معلومات الفيديو (العنوان، التاريخ، المدة)"""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(part='snippet,contentDetails', id=video_id)
        response = request.execute()
        if not response.get('items'):
            return None
        video = response['items'][0]
        return {
            'id': video_id,
            'title': video['snippet']['title'],
            'published_at': video['snippet']['publishedAt'],
            'duration': parse_duration(video['contentDetails']['duration'])
        }
    except Exception as e:
        print(f"⚠️ خطأ في جلب معلومات الفيديو: {e}")
        return None

def get_videos_after(youtube, after_time, max_results=100):
    """جلب الفيديوهات التي نشرت بعد وقت معين (نفس اليوم)"""
    all_videos = []
    next_token = None
    target_date = after_time[:10]
    
    while len(all_videos) < max_results:
        request = youtube.search().list(
            part='snippet',
            channelId=CHANNEL_ID,
            maxResults=min(50, max_results - len(all_videos)),
            order='date',
            type='video',
            publishedAfter=after_time,
            pageToken=next_token
        )
        response = request.execute()
        
        for item in response.get('items', []):
            vid = item['id']['videoId']
            pub = item['snippet']['publishedAt']
            # فقط الفيديوهات في نفس اليوم
            if pub[:10] == target_date:
                all_videos.append({
                    'id': vid,
                    'title': item['snippet']['title'],
                    'published_at': pub
                })
        
        next_token = response.get('nextPageToken')
        if not next_token:
            break
    
    return all_videos

def get_videos_from_date(youtube, start_date, max_results=100):
    """جلب الفيديوهات من تاريخ محدد فصاعداً"""
    all_videos = []
    next_token = None
    
    while len(all_videos) < max_results:
        request = youtube.search().list(
            part='snippet',
            channelId=CHANNEL_ID,
            maxResults=min(50, max_results - len(all_videos)),
            order='date',
            type='video',
            publishedAfter=start_date,
            pageToken=next_token
        )
        response = request.execute()
        
        for item in response.get('items', []):
            all_videos.append({
                'id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt']
            })
        
        next_token = response.get('nextPageToken')
        if not next_token:
            break
    
    return all_videos

def find_next_video(last_video):
    """البحث عن الفيديو التالي بعد الـ ID المحدد"""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    print(f"\n📌 آخر فيديو معالج:")
    print(f"   ID: {last_video['id']}")
    print(f"   التاريخ: {last_video['published_at']}")
    print(f"   المدة: {last_video['duration']} ثانية")
    
    # الخطوة 1: البحث في نفس اليوم بعد الـ ID
    print(f"\n🔍 البحث في نفس اليوم بعد {last_video['published_at']}")
    same_day_videos = get_videos_after(youtube, last_video['published_at'])
    
    if same_day_videos:
        print(f"📊 تم العثور على {len(same_day_videos)} فيديو في نفس اليوم")
        for v in same_day_videos:
            info = get_video_info(v['id'])
            if info and info['duration'] < 60:
                print(f"\n✅ تم العثور على فيديو مناسب (نفس اليوم)")
                return info
            elif info:
                print(f"   ⏭️  تخطي: {v['title'][:40]}... ({info['duration']} ثانية)")
    else:
        print("   لا يوجد فيديوهات في نفس اليوم بعد الـ ID")
    
    # الخطوة 2: الانتقال إلى اليوم التالي
    dt = datetime.fromisoformat(last_video['published_at'].replace('Z', '+00:00'))
    next_day = (dt + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
    
    print(f"\n🔍 البحث من تاريخ {next_day}")
    next_videos = get_videos_from_date(youtube, next_day)
    
    if not next_videos:
        print("   لا يوجد فيديوهات في الأيام التالية")
        return None
    
    print(f"📊 تم العثور على {len(next_videos)} فيديو في الأيام التالية")
    
    for v in next_videos:
        info = get_video_info(v['id'])
        if info and info['duration'] < 60:
            print(f"\n✅ تم العثور على فيديو مناسب (يوم لاحق)")
            return info
        elif info:
            print(f"   ⏭️  تخطي: {v['title'][:40]}... ({info['duration']} ثانية)")
    
    print("   ❌ لم يتم العثور على أي فيديو مناسب")
    return None

def download_video(url, title):
    """تحميل فيديو باستخدام yt-dlp"""
    VIDEO_FOLDER.mkdir(parents=True, exist_ok=True)
    
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_title}.mp4"
    file_path = VIDEO_FOLDER / filename
    
    cookies_path = COOKIES_FILE if COOKIES_FILE.exists() else None
    
    command = [
        "yt-dlp",
        "--js-runtime", "node",
        "--remote-components", "ejs:github",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(file_path),
        url
    ]
    
    if cookies_path:
        command.insert(1, "--cookies")
        command.insert(2, str(cookies_path))
    
    try:
        print(f"📥 تحميل: {title}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0 and file_path.exists():
            print(f"✅ تم التحميل: {filename}")
            return str(file_path)
        else:
            print(f"⚠️ فشل التحميل: {result.stderr[:200]}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ انتهى وقت التحميل")
        return None
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return None

async def upload_to_story(video_path, title):
    """رفع الفيديو كستوري على تيليجرام"""
    try:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.start()
        
        print("✅ متصل بتليجرام")
        print("📤 رفع الفيديو...")
        uploaded = await client.upload_file(video_path)
        
        video_attributes = types.DocumentAttributeVideo(
            duration=0, w=720, h=1280, supports_streaming=True
        )
        
        print("🚀 نشر القصة...")
        await client(functions.stories.SendStoryRequest(
            peer='me',
            media=types.InputMediaUploadedDocument(
                file=uploaded,
                mime_type='video/mp4',
                attributes=[video_attributes]
            ),
            privacy_rules=[types.InputPrivacyValueAllowAll()],
            caption=f"🎬 {title}",
            period=86400
        ))
        
        print("✅ تم النشر!")
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ فشل النشر: {e}")
        send_telegram_msg(f"❌ فشل نشر الستوري: {str(e)[:100]}")
        return False

def cleanup_video(video_path):
    """حذف الفيديو المحلي بعد النجاح"""
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"🗑️ تم حذف {os.path.basename(video_path)}")
    except Exception as e:
        print(f"⚠️ فشل الحذف: {e}")

def save_last_video(video_info):
    """حفظ معلومات آخر فيديو تم معالجته"""
    data = {
        'id': video_info['id'],
        'title': video_info['title'],
        'published_at': video_info['published_at'],
        'duration': video_info['duration']
    }
    with open(LAST_VIDEO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 تم حفظ معلومات آخر فيديو في {LAST_VIDEO_FILE}")

def load_last_video():
    """تحميل معلومات آخر فيديو تم معالجته"""
    if LAST_VIDEO_FILE.exists():
        try:
            with open(LAST_VIDEO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

async def main():
    print("=" * 60)
    print("🚀 بدء تشغيل السكربت - معالجة فيديو واحد بالترتيب التسلسلي")
    print("=" * 60)
    
    # تحميل معلومات آخر فيديو معالج
    last_video = load_last_video()
    
    if not last_video:
        print("⚠️ لا يوجد فيديو محفوظ، يرجى تحديد أول فيديو يدوياً")
        print("📝 قم بإنشاء ملف last_video.json بالمحتوى:")
        print('''
{
  "id": "معرف_الفيديو",
  "title": "عنوان الفيديو",
  "published_at": "2026-01-01T00:00:00Z",
  "duration": 0
}
''')
        send_telegram_msg("⚠️ لا يوجد فيديو محفوظ، يرجى تحديد أول فيديو")
        return
    
    # البحث عن الفيديو التالي
    print("\n🔍 البحث عن الفيديو التالي...")
    next_video = find_next_video(last_video)
    
    if not next_video:
        print("✨ لا يوجد فيديو تالٍ للمعالجة")
        send_telegram_msg("✨ لا يوجد فيديو جديد للمعالجة")
        return
    
    print("\n" + "=" * 60)
    print(f"🎬 الفيديو التالي:")
    print(f"   ID: {next_video['id']}")
    print(f"   العنوان: {next_video['title']}")
    print(f"   المدة: {next_video['duration']} ثانية")
    print(f"   التاريخ: {next_video['published_at']}")
    print(f"   الرابط: https://youtube.com/shorts/{next_video['id']}")
    print("=" * 60)
    
    send_telegram_msg(f"📥 جاري تحميل: {next_video['title'][:50]}...")
    
    # تحميل الفيديو
    video_url = f"https://youtube.com/shorts/{next_video['id']}"
    video_path = download_video(video_url, next_video['title'])
    
    if not video_path:
        print("❌ فشل التحميل")
        send_telegram_msg("❌ فشل تحميل الفيديو")
        return
    
    # رفع الستوري
    success = await upload_to_story(video_path, next_video['title'])
    
    if success:
        save_last_video(next_video)
        cleanup_video(video_path)
        print("\n🎉 تم بنجاح!")
        send_telegram_msg(f"✅ تم نشر الستوري:\n{next_video['title'][:100]}")
    else:
        print("\n⚠️ فشل النشر، لم يتم حفظ الفيديو")

if __name__ == "__main__":
    asyncio.run(main())
