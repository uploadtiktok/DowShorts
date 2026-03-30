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
        # الخدعة الجديدة: إجبار يوتيوب على استخدام مشغل أندرويد لتجاوز القيود
        "--extractor-args", "youtube:player_client=android,ios",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--no-check-certificates",
        "--geo-bypass",
        # تبسيط طلب الجودة لضمان التحميل
        "-f", "bestvideo[ext=mp4]+bestaudio[m4a]/best[ext=mp4]/best",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"Executing deep bypass download for: {url}")
        subprocess.run(command, check=True)
        print("Success! Download completed.")
    except subprocess.CalledProcessError as e:
        print(f"Final attempt failed. YouTube has successfully blocked this IP range.")
        exit(1)

if __name__ == "__main__":
    target_url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(target_url)
