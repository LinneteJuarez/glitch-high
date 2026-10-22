from pathlib import Path
import subprocess

from .scanner import MediaAsset


def create_synthetic_visual(root: Path, ffmpeg: str, duration: float = 4.0) -> MediaAsset:
    if duration <= 0:
        raise ValueError("La duración sintética debe ser positiva.")
    target = root / "temp" / "synthetic_test_source.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30", "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)], check=True)
    return MediaAsset(target, "video")
