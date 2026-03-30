name: Auto YouTube Shorts & RSS Sync

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  sync_process:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 18

      - name: Install FFmpeg
        run: sudo apt-get install -y ffmpeg

      - name: Install Python Dependencies
        run: pip install yt-dlp requests

      - name: Create Cookies File
        run: echo "${{ secrets.YT_COOKIES }}" > cookies.txt

      - name: Run Main Script
        run: python main.py

      - name: Cleanup Sensitive Data
        if: always()
        run: rm -f cookies.txt

      - name: Commit and Push Changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          
          # إعداد المجلدات والملفات للتأكد من وجودها
          mkdir -p shorts
          touch last_processed_id.json
          
          # إضافة كل التغييرات الجديدة فقط (تجنب fatal error)
          git add shorts/ last_processed_id.json
          
          # إضافة rss.xml فقط إذا تم إنشاؤه
          if [ -f "rss.xml" ]; then
            git add rss.xml
          fi
          
          if git diff --staged --quiet; then
            echo "No changes to commit."
          else
            git commit -m "Sync: New shorts and RSS update"
            git push
          fi
