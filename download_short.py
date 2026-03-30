import os
import subprocess

def download_video(url):
    output_dir = "shorts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # أوامر بسيطة ومباشرة: استخدم الكوكيز، هات أفضل جودة، احفظها في مجلد shorts
    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "-f", "bestvideo+bestaudio/best", 
        "--merge-output-format", "mp4",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"جاري التحميل باستخدام الكوكيز لأعلى دقة متاحة...")
        subprocess.run(command, check=True)
        print("تم التحميل بنجاح!")
    except subprocess.CalledProcessError:
        print("فشل التحميل. قد تكون الكوكيز منتهية الصلاحية أو محظورة.")
        exit(1)

if __name__ == "__main__":
    # الرابط المطلوب
    video_url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(video_url)
