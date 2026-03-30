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
        "--remote-components", "ejs:github",
        # استخدام مشغلات الأجهزة المحمولة لتجاوز قيود المتصفح
        "--extractor-args", "youtube:player_client=android,ios",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--no-check-certificates",
        "--geo-bypass",
        # تصحيح الصيغة هنا: استخدام ext=m4a
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"Executing corrected download for: {url}")
        subprocess.run(command, check=True)
        print("Success! Download completed.")
    except subprocess.CalledProcessError as e:
        print(f"Download failed. If this persists, the cookies might be expired.")
        exit(1)

if __name__ == "__main__":
    target_url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(target_url)
