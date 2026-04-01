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
# تحديد مسار المجلد الحالي (story)
CURRENT_DIR = Path(__file__).parent.absolute()
# تحديد المسار الجذر (المجلد الرئيسي للمستودع)
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
    """جلب تفاصيل الفيديو (المدة والعنوان) من YouTube API"""
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
            
            return {
                'duration': duration_seconds,
                'title': title
            }
        
        return None
    except Exception as e:
        print(f"⚠️ خطأ في جلب تفاصيل الفيديو: {e}")
        return None

def get_next_videos_from_channel(last_video_id):
    """الحصول على قائمة الفيديوهات التي تلي الـ ID المحدد"""
    if not YOUTUBE_API_KEY:
        print("🔴 خطأ: YOUTUBE_API_KEY غير موجود")
        return []
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # جلب أحدث الفيديوهات من القناة
        request = youtube.search().list(
            part='snippet',
            channelId=CHANNEL_ID,
            maxResults=20,
            order='date',
            type='video'
        )
        response = request.execute()
        
        videos = []
        found_last = False
        
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            
            # إذا لم نجد الـ ID بعد، نستمر بالبحث
            if not found_last:
                if video_id == last_video_id:
                    found_last = True
                continue
            
            # بعد العثور على الـ ID، نضيف الفيديوهات التالية
            videos.append({
                'id': video_id,
                'title': title,
                'link': f"https://www.youtube.com/shorts/{video_id}"
            })
        
        return videos
        
    except Exception as e:
        print(f"🔴 خطأ في YouTube API: {e}")
        return []

def find_first_suitable_video(videos):
    """البحث عن أول فيديو مناسب (Shorts وأقل من 60 ثانية) من القائمة"""
    for video in videos:
        print(f"\n📹 فحص الفيديو: {video['title'][:50]}...")
        
        # جلب تفاصيل الفيديو (المدة)
        details = get_video_details(video['id'])
        
        if not details:
            print(f"   ⚠️ لا يمكن جلب تفاصيل الفيديو")
            continue
        
        print(f"   ⏱️  المدة: {details['duration']} ثانية")
        
        # التحقق من أن الفيديو Shorts (من العنوان أو المدة)
        is_shorts = ('#shorts' in video['title'].lower() or 'short' in video['title'].lower())
        is_short_duration = details['duration'] < 60
        
        if is_shorts and is_short_duration:
            print(f"   ✅ فيديو مناسب: {details['duration']} ثانية")
            return {
                'id': video['id'],
                'title': video['title'],
                'link': video['link'],
                'duration': details['duration']
            }
        elif is_shorts and not is_short_duration:
            print(f"   ⏭️  تم التخطي: المدة {details['duration']} ثانية تتجاوز 59 ثانية")
        elif not is_shorts and is_short_duration:
            print(f"   ⏭️  تم التخطي: ليس فيديو Shorts")
        else:
            print(f"   ⏭️  تم التخطي: غير مناسب")
    
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
    """الدالة الرئيسية - معالجة فيديو واحد فقط في كل مرة"""
    print("=" * 60)
    print("🚀 بدء تشغيل السكربت - البحث عن فيديو Shorts مناسب")
    print("📌 سيتم معالجة فيديو واحد فقط في هذا التشغيل")
    print("=" * 60)
    
    # تحميل آخر ID تم معالجته
    last_id = load_last_processed_id()
    
    if not last_id:
        print("⚠️ لا يوجد ID محفوظ. سيتم البدء من أول فيديو")
    else:
        print(f"📌 آخر فيديو معالج: {last_id}")
    
    # الحصول على الفيديوهات التي تلي الـ ID
    print("\n🔍 جلب الفيديوهات الجديدة...")
    next_videos = get_next_videos_from_channel(last_id)
    
    if not next_videos:
        print("✨ لا يوجد فيديوهات جديدة")
        return
    
    print(f"📊 تم العثور على {len(next_videos)} فيديو جديد")
    
    # البحث عن أول فيديو مناسب
    print("\n🔎 البحث عن أول فيديو Shorts بمدة أقل من 60 ثانية...")
    suitable_video = find_first_suitable_video(next_videos)
    
    if not suitable_video:
        print("❌ لم يتم العثور على أي فيديو Shorts مناسب (أقل من 60 ثانية)")
        return
    
    print("\n" + "=" * 60)
    print(f"🎬 تم العثور على فيديو مناسب:")
    print(f"   العنوان: {suitable_video['title']}")
    print(f"   المدة: {suitable_video['duration']} ثانية")
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
        print("🔄 في التشغيل القادم، سيتم معالجة الفيديو التالي")
        print("=" * 60)
    else:
        print("\n⚠️ فشل نشر الستوري، تم الاحتفاظ بالفيديو محلياً")
        print("💡 لن يتم حفظ ID الفيديو حتى ينجح النشر")

if __name__ == "__main__":
    asyncio.run(main())
