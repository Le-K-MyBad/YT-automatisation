#!/usr/bin/env python3
"""Create a minimal test video file for relaxing_video."""

import subprocess
import sys

def create_test_video(filename="relaxing.mp4", duration=5):
    """Create a simple black video file with ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=black:s=1280x720:d={duration}",
            "-f", "lavfi",
            "-i", f"sine=f=440:d={duration}",
            "-pix_fmt", "yuv420p",
            "-y",
            filename,
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Created {filename} ({duration}s black video)")
        return True
    except Exception as e:
        print(f"Error creating test video: {e}")
        return False

if __name__ == "__main__":
    success = create_test_video()
    sys.exit(0 if success else 1)
