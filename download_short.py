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
        # هذا الخيار هو المفتاح لحل مشكلة n challenge
        "--remote-components", "ejs:github",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--no-check-certificates",
        "--geo-bypass",
        # محاولة جلب أفضل جودة متاحة مدمجة أو دمجها يدوياً
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"Starting secure download with remote components for: {url}")
        # استخدام Popen لمتابعة المخرجات مباشرة
        process = subprocess.run(command, check=True)
        print("Success! Video downloaded.")
    except subprocess.CalledProcessError as e:
        print(f"Critical Failure: {e}")
        exit(1)

if __name__ == "__main__":
    target_url = "https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry"
    download_video(target_url)
