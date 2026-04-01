import os
import subprocess
import asyncio
import re
from pathlib import Path
from googleapiclient.discovery import build
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

# ========== CONFIGURATION ==========
CURRENT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = CURRENT_DIR.parent

VIDEO_FOLDER = CURRENT_DIR / "shorts"
LAST_ID_FILE = CURRENT_DIR / "last_story.txt"
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

def get_video_details(video_id):
    """جلب تفاصيل الفيديو (المدة، العنوان، التاريخ)"""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        video_request = youtube.videos().list(
            part='contentDetails,snippet',
            id=video_id
        )
        video_response = video_request.execute()
        if video_response.get('items'):
            item = video_response['items'][0]
            return {
                'duration': parse_duration(item['contentDetails']['duration']),
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt']
            }
        return None
    except Exception as e:
        print(f"⚠️ خطأ في جلب التفاصيل: {e}")
        return None

def get_all_channel_videos(max_results=150):
    """جلب الفيديوهات من القناة مع الترحيل (مرتبة من الأحدث إلى الأقدم)"""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        all_videos = []
        next_page_token = None

        while len(all_videos) < max_results:
            request = youtube.search().list(
                part='snippet',
                channelId=CHANNEL_ID,
                maxResults=min(50, max_results - len(all_videos)),
                order='date',
                type='video',
                pageToken=next_page_token
            )
            response = request.execute()
            for item in response.get('items', []):
                all_videos.append({
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt'],
                    'link': f"https://www.youtube.com/shorts/{item['id']['videoId']}"
                })
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return all_videos
    except Exception as e:
        print(f"🔴 خطأ في جلب الفيديوهات: {e}")
        return []

def find_next_video_after_id(all_videos, last_id):
    """
    إرجاع الفيديو التالي مباشرة بعد الـ ID المحدد (بالترتيب التسلسلي)
    all_videos مرتبة من الأحدث إلى الأقدم
    """
    for i, video in enumerate(all_videos):
        if video['id'] == last_id:
            # الفيديو التالي في الترتيب (الأقدم منه مباشرة)
            if i + 1 < len(all_videos):
                next_video = all_videos[i + 1]
                print(f"✅ تم العثور على الـ ID {last_id}")
                print(f"📹 الفيديو التالي مباشرة: {next_video['title'][:50]}...")
                print(f"🕒 تاريخه: {next_video['published_at']}")
                return [next_video]
            else:
                print(f"⚠️ لا يوجد فيديو بعد {last_id} (هذا آخر فيديو في القائمة)")
                return []
    
    print(f"⚠️ الـ ID {last_id} غير موجود، سيتم البدء من أقدم فيديو")
    # إذا لم نجد الـ ID، نبدأ من أقدم فيديو (آخر عنصر في القائمة)
    if all_videos:
        oldest_video = all_videos[-1]
        print(f"📹 البدء من أقدم فيديو: {oldest_video['title'][:50]}...")
        return [oldest_video]
    return []

def download_video(url, title):
    """تحميل فيديو باستخدام yt-dlp"""
    VIDEO_FOLDER.mkdir(parents=True, exist_ok=True)
    
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_title}.mp4"
    file_path = VIDEO_FOLDER / filename
    
    cookies_path = COOKIES_FILE if COOKIES_FILE.exists() else None
    
    # نفس الأمر الناجح من الكود الأصلي
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

def save_last_processed_id(video_id):
    """حفظ ID آخر فيديو تم معالجته"""
    with open(LAST_ID_FILE, 'w') as f:
        f.write(video_id)
    print(f"💾 تم حفظ ID: {video_id}")

def load_last_processed_id():
    """تحميل آخر ID تم معالجته"""
    if LAST_ID_FILE.exists():
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return None

async def main():
    print("=" * 60)
    print("🚀 بدء تشغيل السكربت - معالجة فيديو واحد بالترتيب التسلسلي")
    print("=" * 60)
    
    # قراءة آخر ID
    last_id = load_last_processed_id()
    if last_id:
        print(f"📌 آخر فيديو معالج: {last_id}")
    else:
        print("⚠️ لا يوجد ID محفوظ، البدء من أقدم فيديو")
    
    # جلب الفيديوهات
    print("\n🔍 جلب فيديوهات القناة...")
    all_videos = get_all_channel_videos(max_results=150)
    
    if not all_videos:
        print("❌ لا يوجد فيديوهات")
        send_telegram_msg("❌ لا يوجد فيديوهات في القناة")
        return
    
    print(f"📊 تم جلب {len(all_videos)} فيديو (من الأحدث إلى الأقدم)")
    
    # الحصول على الفيديو التالي مباشرة
    if last_id:
        candidates = find_next_video_after_id(all_videos, last_id)
    else:
        # إذا لم يكن هناك ID، نبدأ من أقدم فيديو
        if all_videos:
            candidates = [all_videos[-1]]
            print(f"📊 البدء من أقدم فيديو")
    
    if not candidates:
        print("✨ لا يوجد فيديو تالٍ للمعالجة")
        send_telegram_msg("✨ لا يوجد فيديو جديد للمعالجة")
        return
    
    # الفيديو المرشح (واحد فقط)
    video = candidates[0]
    
    # التحقق من المدة
    print(f"\n📹 فحص الفيديو: {video['title'][:50]}... | {video['published_at']}")
    details = get_video_details(video['id'])
    
    if not details:
        print("❌ لا يمكن جلب تفاصيل الفيديو")
        return
    
    print(f"   ⏱️  المدة: {details['duration']} ثانية")
    
    # إذا كان الفيديو أطول من 59 ثانية، يتم تخطيه وحفظ ID الخاص به
    if details['duration'] >= 60:
        print(f"   ❌ الفيديو مدته {details['duration']} ثانية (يتجاوز 59 ثانية)")
        print(f"   ⚠️ سيتم تخطيه وحفظ ID الخاص به لتجنب التكرار")
        # حفظ ID هذا الفيديو حتى لا نتعامل معه مرة أخرى
        save_last_processed_id(video['id'])
        send_telegram_msg(f"⚠️ تم تخطي فيديو:\n{video['title'][:50]}\nالسبب: المدة {details['duration']} ثانية (>59)")
        print("💾 تم حفظ ID الفيديو المتخطي، سيتم معالجة التالي في التشغيل القادم")
        return
    
    print("\n" + "=" * 60)
    print(f"🎬 الفيديو المختار:")
    print(f"   العنوان: {video['title']}")
    print(f"   المدة: {details['duration']} ثانية")
    print(f"   النشر: {video['published_at']}")
    print("=" * 60)
    
    send_telegram_msg(f"📥 جاري تحميل: {video['title'][:50]}...")
    
    # تحميل الفيديو
    video_path = download_video(video['link'], video['title'])
    if not video_path:
        print("❌ فشل التحميل")
        send_telegram_msg("❌ فشل تحميل الفيديو")
        return
    
    # رفع الستوري
    success = await upload_to_story(video_path, video['title'])
    
    if success:
        save_last_processed_id(video['id'])
        cleanup_video(video_path)
        print("\n🎉 تم بنجاح!")
        send_telegram_msg(f"✅ تم نشر الستوري:\n{video['title'][:100]}")
    else:
        print("\n⚠️ فشل النشر، لم يتم حفظ ID")

if __name__ == "__main__":
    asyncio.run(main())
