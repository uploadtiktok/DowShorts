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
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--no-check-certificates",
        "--geo-bypass",
        # تعديل خيار الجودة لجلب أفضل فيديو متاح أياً كانت صيغته ثم تحويله أو دمج أفضل صوت وصورة
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4", # محاولة دمج المخرجات في صيغة mp4
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]

    try:
        print(f"Attempting download with updated formats for: {url}")
        subprocess.run(command, check=True)
        print("Success!")
    except subprocess.CalledProcessError as e:
        print(f"Download failed again. Technical details: {e}")
        exit(1)

if __name__ == "__main__":
    download_video("https://youtube.com/shorts/evdWG0GRlfs?si=DmZ9aa5O6CMURlry")
