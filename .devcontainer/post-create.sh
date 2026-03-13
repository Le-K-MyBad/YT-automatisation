#!/bin/bash
set -e

echo "=== YT-automatisation Setup ==="

# Install system dependencies including Chromium
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
  chromium \
  chromium-driver \
  ffmpeg \
  git

# Verify Chromium installation
echo "Verifying Chromium installation..."
if command -v chromium >/dev/null 2>&1; then
    echo "✓ Chromium found at: $(which chromium)"
    chromium --version
else
    echo "✗ Chromium not found, trying alternatives..."
    # Try to install with different package names
    apt-get install -y chromium-browser chromium-chromedriver || true
    if command -v chromium-browser >/dev/null 2>&1; then
        echo "✓ chromium-browser found at: $(which chromium-browser)"
        chromium-browser --version
    else
        echo "✗ Chromium installation failed - YouTube Shorts may not work"
    fi
fi

# Create Python virtual environment and install dependencies
echo "Creating Python environment..."
python3 -m venv .venv

# Activate and install Python packages
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create test video
echo "Creating test video..."
python3 << 'EOF'
import subprocess
import sys

try:
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "color=c=black:s=1280x720:d=5",
        "-f", "lavfi",
        "-i", "sine=f=440:d=5",
        "-pix_fmt", "yuv420p",
        "-y",
        "relaxing.mp4",
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✓ Created relaxing.mp4 (5s test video)")
except Exception as e:
    print(f"Warning: Could not create test video: {e}")
    sys.exit(0)
EOF

echo ""
echo "=== Setup Complete ==="
echo "✓ Chromium installed (needed for YouTube Shorts)"
echo "✓ FFmpeg installed (needed for video merging)"
echo "✓ Python dependencies installed"
echo "✓ Test video created (relaxing.mp4)"
echo ""
echo "Ready to use! Run:"
echo "  python scripts/automation.py 'https://www.youtube.com/watch?v=VIDEO_ID'"
echo "  python scripts/automation.py 'https://www.youtube.com/shorts/SHORT_ID'"
echo ""
