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
        # جلب أفضل جودة (حتى 1080p) لضمان قبول GitHub للملف
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        "--no-playlist",
        url
    ]

    try:
        print(f"جاري تحميل المقطع: {url}")
        subprocess.run(command, check=True)
        print("تم التحميل والدمج بنجاح.")
    except subprocess.CalledProcessError:
        print("فشل التحميل. تأكد من صلاحية الكوكيز في Secrets.")
        exit(1)

if __name__ == "__main__":
    # الرابط الجديد الذي طلبته
    target_url = "https://youtube.com/shorts/uqWW1Msoo28?si=__Awzp3Q6t_RmwfT"
    download_video(target_url)
