import os
import subprocess
from pathlib import Path
from googleapiclient.discovery import build
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
import asyncio
from dotenv import load_dotenv
import re

# ========== CONFIGURATION ==========
# تحديد المسارات
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
# ====================================

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
    """جلب الفيديوهات من القناة مع الترحيل"""
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

def find_videos_after_id(all_videos, last_id):
    """إرجاع الفيديوهات الأحدث من last_id"""
    for i, video in enumerate(all_videos):
        if video['id'] == last_id:
            return all_videos[:i]  # الأحدث أولاً
    print(f"⚠️ الـ ID {last_id} غير موجود في آخر {len(all_videos)} فيديو، سيتم التعامل مع الكل كجديد.")
    return all_videos

def find_first_suitable_video(videos):
    """أول فيديو مدته أقل من 60 ثانية"""
    for video in videos:
        print(f"\n📹 فحص: {video['title'][:50]}... | تاريخ: {video['published_at']}")
        details = get_video_details(video['id'])
        if not details:
            continue
        print(f"   ⏱️  المدة: {details['duration']} ثانية")
        if details['duration'] < 60:
            print("   ✅ مناسب")
            return {
                'id': video['id'],
                'title': video['title'],
                'link': video['link'],
                'duration': details['duration'],
                'published_at': video['published_at']
            }
        else:
            print("   ⏭️  تخطي (أطول من 59 ثانية)")
    return None

def download_video(url, title):
    """تحميل فيديو باستخدام yt-dlp مع محاولات متعددة"""
    VIDEO_FOLDER.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    file_path = VIDEO_FOLDER / f"{safe_title}.mp4"

    cookies_path = COOKIES_FILE if COOKIES_FILE.exists() else None

    # محاولة 1: الطريقة الموصى بها
    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "--format", "best[height<=1080]",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-o", str(file_path),
        url
    ]
    if cookies_path:
        cmd.insert(1, "--cookies")
        cmd.insert(2, str(cookies_path))

    try:
        print(f"📥 تحميل: {title}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ تم التحميل: {file_path.name}")
            return str(file_path)

        # محاولة 2: استخدام خيارات إضافية للتغلب على حماية YouTube
        print("⚠️ المحاولة الأولى فشلت، تجربة طريقة بديلة...")
        cmd2 = [
            "yt-dlp",
            "--no-check-certificates",
            "--extractor-args", "youtube:player_client=android,web",
            "--format", "best[height<=1080]",
            "--user-agent", "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "--retries", "10",
            "-o", str(file_path),
            url
        ]
        if cookies_path:
            cmd2.insert(1, "--cookies")
            cmd2.insert(2, str(cookies_path))

        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
        if result2.returncode == 0:
            print(f"✅ تم التحميل (طريقة بديلة): {file_path.name}")
            return str(file_path)

        print(f"❌ فشل التحميل: {result2.stderr[:200]}")
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
        attrs = types.DocumentAttributeVideo(duration=0, w=720, h=1280, supports_streaming=True)
        print("🚀 نشر القصة...")
        await client(functions.stories.SendStoryRequest(
            peer='me',
            media=types.InputMediaUploadedDocument(
                file=uploaded,
                mime_type='video/mp4',
                attributes=[attrs]
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
    with open(LAST_ID_FILE, 'w') as f:
        f.write(video_id)
    print(f"💾 تم حفظ ID: {video_id}")

def load_last_processed_id():
    if LAST_ID_FILE.exists():
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return None

async def main():
    print("=" * 60)
    print("🚀 بدء تشغيل السكربت - فيديو Shorts واحد فقط")
    print("=" * 60)

    last_id = load_last_processed_id()
    if last_id:
        print(f"📌 آخر فيديو معالج: {last_id}")
    else:
        print("⚠️ لا يوجد ID محفوظ، سيتم البدء من الأول")

    # جلب الفيديوهات
    print("\n🔍 جلب فيديوهات القناة...")
    all_videos = get_all_channel_videos(max_results=150)
    print(f"📊 تم جلب {len(all_videos)} فيديو")

    # الفيديوهات الأحدث
    if last_id:
        candidates = find_videos_after_id(all_videos, last_id)
    else:
        candidates = all_videos

    if not candidates:
        print("✨ لا يوجد فيديوهات جديدة")
        return

    # البحث عن فيديو مناسب
    print(f"\n🔎 البحث عن أول فيديو مدته < 60 ثانية (من {len(candidates)} فيديو)...")
    video = find_first_suitable_video(candidates)
    if not video:
        print("❌ لم يتم العثور على فيديو مناسب")
        return

    print("\n" + "=" * 60)
    print(f"🎬 الفيديو المختار:")
    print(f"   العنوان: {video['title']}")
    print(f"   المدة: {video['duration']} ثانية")
    print(f"   النشر: {video['published_at']}")
    print("=" * 60)

    # تحميل
    video_path = download_video(video['link'], video['title'])
    if not video_path:
        print("❌ فشل التحميل، سيتم إنهاء السكربت")
        return

    # رفع
    success = await upload_to_story(video_path, video['title'])
    if success:
        save_last_processed_id(video['id'])
        cleanup_video(video_path)
        print("\n🎉 انتهى بنجاح! (فيديو واحد)")
    else:
        print("\n⚠️ فشل النشر، لم يتم حفظ ID")

if __name__ == "__main__":
    asyncio.run(main())
