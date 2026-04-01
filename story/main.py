import os
import subprocess
from pathlib import Path
from googleapiclient.discovery import build
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
import asyncio
from dotenv import load_dotenv
import re
from datetime import datetime

# ========== CONFIGURATION ==========
CURRENT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = CURRENT_DIR.parent

VIDEO_FOLDER = CURRENT_DIR / "shorts"
LAST_ID_FILE = CURRENT_DIR / "last_story.txt"
COOKIES_FILE = ROOT_DIR / "cookies.txt"

# YouTube API Settings
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = "UCLSEQ0cuNz_vJ_H3uXB1R7w"

# Telegram Settings for Story
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
# ====================================

def parse_duration(duration):
    """تحويل مدة الفيديو من تنسيق ISO 8601 إلى ثواني"""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def get_video_details(video_id):
    """جلب تفاصيل الفيديو (المدة والعنوان والتاريخ)"""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        video_request = youtube.videos().list(
            part='contentDetails,snippet',
            id=video_id
        )
        video_response = video_request.execute()
        
        if video_response.get('items'):
            item = video_response['items'][0]
            duration_iso = item['contentDetails']['duration']
            duration_seconds = parse_duration(duration_iso)
            title = item['snippet']['title']
            published_at = item['snippet']['publishedAt']
            
            return {
                'duration': duration_seconds,
                'title': title,
                'published_at': published_at
            }
        
        return None
    except Exception as e:
        print(f"⚠️ خطأ في جلب تفاصيل الفيديو: {e}")
        return None

def get_all_channel_videos(max_results=100):
    """جلب جميع فيديوهات القناة باستخدام الترحيل"""
    if not YOUTUBE_API_KEY:
        print("🔴 خطأ: YOUTUBE_API_KEY غير موجود")
        return []
    
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
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                published_at = item['snippet']['publishedAt']
                
                all_videos.append({
                    'id': video_id,
                    'title': title,
                    'published_at': published_at,
                    'link': f"https://www.youtube.com/shorts/{video_id}"
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token or len(all_videos) >= max_results:
                break
        
        return all_videos
        
    except Exception as e:
        print(f"🔴 خطأ في YouTube API: {e}")
        return []

def find_videos_after_id(all_videos, last_id):
    """البحث عن الفيديوهات التي تأتي بعد الـ ID المحدد (أحدث منه)"""
    try:
        # البحث عن موقع الـ ID في القائمة
        last_index = -1
        for i, video in enumerate(all_videos):
            if video['id'] == last_id:
                last_index = i
                print(f"✅ تم العثور على الـ ID {last_id} في الموقع {i+1}")
                break
        
        if last_index == -1:
            print(f"⚠️ لم يتم العثور على الـ ID {last_id} في القائمة الحالية")
            print(f"🔄 سيتم اعتبار جميع الفيديوهات الـ {len(all_videos)} جديدة")
            return all_videos
        
        # الفيديوهات الأحدث تأتي قبل الـ ID في القائمة (لأن الترتيب من الأحدث للأقدم)
        newer_videos = all_videos[:last_index]
        print(f"📊 تم العثور على {len(newer_videos)} فيديو أحدث من {last_id}")
        
        return newer_videos
        
    except Exception as e:
        print(f"⚠️ خطأ في البحث عن الفيديوهات: {e}")
        return []

def find_first_suitable_video(videos):
    """البحث عن أول فيديو مناسب (Shorts وأقل من 60 ثانية)"""
    for video in videos:
        print(f"\n📹 فحص الفيديو: {video['title'][:50]}...")
        print(f"   🕒 تاريخ النشر: {video['published_at']}")
        
        # جلب تفاصيل الفيديو (المدة)
        details = get_video_details(video['id'])
        
        if not details:
            print(f"   ⚠️ لا يمكن جلب تفاصيل الفيديو")
            continue
        
        print(f"   ⏱️  المدة: {details['duration']} ثانية")
        
        # التحقق من أن الفيديو Shorts (من الرابط أو من العنوان)
        # ملاحظة: فيديوهات القناة قد تكون كلها Shorts ولكن لا تحمل علامة في العنوان
        # لذلك سنعتبر أي فيديو مدته أقل من 60 ثانية مناسباً
        
        is_short_duration = details['duration'] < 60
        
        if is_short_duration:
            print(f"   ✅ فيديو مناسب: {details['duration']} ثانية")
            return {
                'id': video['id'],
                'title': video['title'],
                'link': video['link'],
                'duration': details['duration'],
                'published_at': video['published_at']
            }
        else:
            print(f"   ⏭️  تم التخطي: المدة {details['duration']} ثانية تتجاوز 59 ثانية")
    
    return None

def download_video(url, title):
    """تحميل فيديو واحد"""
    VIDEO_FOLDER.mkdir(parents=True, exist_ok=True)
    
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_title}.mp4"
    file_path = VIDEO_FOLDER / filename
    
    cookies_path = COOKIES_FILE if COOKIES_FILE.exists() else None
    
    command = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(file_path),
        url
    ]
    
    if cookies_path:
        command.insert(1, "--cookies")
        command.insert(2, str(cookies_path))
    
    try:
        print(f"📥 جاري تحميل: {title}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ تم التحميل: {filename}")
            return str(file_path)
        else:
            error_msg = result.stderr.lower()
            if "sign in" in error_msg or "cookie" in error_msg or "forbidden" in error_msg:
                print("🔴 الكوكيز متوقف - يرجى تحديث ملف cookies.txt")
            else:
                print(f"🔴 فشل التحميل: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print("🔴 انتهى وقت التحميل")
        return None
    except Exception as e:
        print(f"🔴 خطأ في التحميل: {e}")
        return None

async def upload_to_story(video_path, title):
    """رفع الفيديو كستوري في تلجرام"""
    try:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.start()
        
        print("✅ تم الاتصال بتلجرام")
        
        print("📤 جاري رفع الفيديو...")
        uploaded_file = await client.upload_file(video_path)
        
        video_attributes = types.DocumentAttributeVideo(
            duration=0,
            w=720,
            h=1280,
            supports_streaming=True
        )
        
        print("🚀 جاري نشر القصة...")
        result = await client(functions.stories.SendStoryRequest(
            peer='me',
            media=types.InputMediaUploadedDocument(
                file=uploaded_file,
                mime_type='video/mp4',
                attributes=[video_attributes]
            ),
            privacy_rules=[types.InputPrivacyValueAllowAll()],
            caption=f"🎬 {title}",
            period=86400
        ))
        
        print("✅ تم نشر الستوري بنجاح!")
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ خطأ في نشر الستوري: {e}")
        return False

def cleanup_video(video_path):
    """حذف الفيديو بعد رفعه"""
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"🗑️ تم حذف الفيديو: {os.path.basename(video_path)}")
            return True
    except Exception as e:
        print(f"⚠️ فشل حذف الفيديو: {e}")
    return False

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
                video_id = f.read().strip()
                return video_id if video_id else None
        except:
            pass
    return None

async def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🚀 بدء تشغيل السكربت - البحث عن فيديو Shorts مناسب")
    print("📌 سيتم معالجة فيديو واحد فقط في هذا التشغيل")
    print("=" * 60)
    
    # تحميل آخر ID
    last_id = load_last_processed_id()
    
    if not last_id:
        print("⚠️ لا يوجد ID محفوظ. سيتم البدء من أول فيديو")
    else:
        print(f"📌 آخر فيديو معالج: {last_id}")
    
    # جلب جميع الفيديوهات (100 فيديو للتأكد من العثور على الـ ID)
    print("\n🔍 جلب فيديوهات القناة...")
    all_videos = get_all_channel_videos(max_results=100)
    
    if not all_videos:
        print("❌ لم يتم العثور على أي فيديوهات")
        return
    
    print(f"📊 تم جلب {len(all_videos)} فيديو")
    
    # البحث عن الفيديوهات الأحدث من الـ ID
    if last_id:
        next_videos = find_videos_after_id(all_videos, last_id)
    else:
        next_videos = all_videos
        print(f"📊 لا يوجد ID محفوظ، سيتم البدء من أول فيديو")
    
    if not next_videos:
        print("✨ لا يوجد فيديوهات جديدة")
        return
    
    # البحث عن أول فيديو مناسب
    print("\n🔎 البحث عن أول فيديو بمدة أقل من 60 ثانية...")
    suitable_video = find_first_suitable_video(next_videos)
    
    if not suitable_video:
        print("❌ لم يتم العثور على أي فيديو مناسب (أقل من 60 ثانية)")
        return
    
    print("\n" + "=" * 60)
    print(f"🎬 تم العثور على فيديو مناسب:")
    print(f"   العنوان: {suitable_video['title']}")
    print(f"   المدة: {suitable_video['duration']} ثانية")
    print(f"   تاريخ النشر: {suitable_video['published_at']}")
    print(f"   الرابط: {suitable_video['link']}")
    print("=" * 60)
    
    # تحميل الفيديو
    video_path = download_video(suitable_video['link'], suitable_video['title'])
    
    if not video_path:
        print("❌ فشل التحميل، سيتم إنهاء السكربت")
        return
    
    # رفع الفيديو كستوري
    success = await upload_to_story(video_path, suitable_video['title'])
    
    if success:
        # حفظ ID الفيديو المعالج
        save_last_processed_id(suitable_video['id'])
        
        # حذف الفيديو المحلي
        cleanup_video(video_path)
        
        print("\n" + "=" * 60)
        print("🎉 تم معالجة فيديو واحد بنجاح!")
        print("💤 سيتم إغلاق السكربت الآن")
        print("=" * 60)
    else:
        print("\n⚠️ فشل نشر الستوري، تم الاحتفاظ بالفيديو محلياً")
        print("💡 لن يتم حفظ ID الفيديو حتى ينجح النشر")

if __name__ == "__main__":
    asyncio.run(main())
