import os
import subprocess

def download_video(url):
    output_dir = "shorts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--js-runtime", "node",
        "--remote-components", "ejs:github", # ضروري لفك تشفير الجودات العالية
        "-f", "bestvideo+bestaudio/best",    # أعلى دقة متاحة
        "--merge-output-format", "mp4",      # دمج في mp4
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print("جاري التحميل بأعلى دقة...")
        subprocess.run(command, check=True)
        print("تمت العملية بنجاح.")
    except subprocess.CalledProcessError:
        print("فشل التحميل. تأكد من صحة الكوكيز.")
        exit(1)

if __name__ == "__main__":
    url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(url)
