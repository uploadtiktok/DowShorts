import os
import subprocess

def download_video(url):
    output_dir = "shorts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--js-runtime", "node", # إخبار البرنامج باستخدام نود لحل التحدي
        "-f", "bestvideo+bestaudio/best", # جلب أعلى دقة فيديو وصوت
        "--merge-output-format", "mp4",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"جاري جلب أعلى دقة متاحة باستخدام الكوكيز...")
        subprocess.run(command, check=True)
        print("تم التحميل بنجاح!")
    except subprocess.CalledProcessError:
        print("فشل التحميل. تأكد من تحديث الكوكيز في GitHub Secrets.")
        exit(1)

if __name__ == "__main__":
    video_url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(video_url)
