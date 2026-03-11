#!/bin/bash
# ─────────────────────────────────────────
#   AllInOneBot — VPS Deploy Script
# ─────────────────────────────────────────

echo "🚀 AllInOneBot VPS Setup Starting..."

# 1. System update
apt-get update && apt-get upgrade -y

# 2. Install dependencies
apt-get install -y python3 python3-pip ffmpeg wget unzip screen

# 3. Install mp4decrypt (Bento4)
wget -q https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip
unzip -q Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip
cp Bento4-SDK-*/bin/mp4decrypt /usr/local/bin/
chmod +x /usr/local/bin/mp4decrypt
rm -rf Bento4*

# 4. Install Python packages
pip3 install -r requirements.txt
pip3 install pyromod==3.1.6

echo "✅ All dependencies installed!"
echo ""
echo "📝 Ab config.env fill karo:"
echo "   cp config.env.example config.env"
echo "   nano config.env"
echo ""
echo "▶️  Bot start karne ke liye:"
echo "   screen -S allinonebot"
echo "   python3 main.py"
echo "   (Ctrl+A then D to detach)"
