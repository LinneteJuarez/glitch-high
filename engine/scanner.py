from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


@dataclass(frozen=True)
class MediaAsset:
    path: Path
    kind: str


def scan_inputs(root: Path) -> list[MediaAsset]:
    """Return supported media in deterministic path order without modifying files."""
    folders = (("video", VIDEO_EXTENSIONS), ("image", IMAGE_EXTENSIONS), ("audio", AUDIO_EXTENSIONS))
    assets: list[MediaAsset] = []
    for kind, extensions in folders:
        base = root / "inputs" / ("videos" if kind == "video" else "images" if kind == "image" else "audio")
        if base.exists():
            assets.extend(MediaAsset(p, kind) for p in base.rglob("*") if p.is_file() and p.suffix.lower() in extensions)
    return sorted(assets, key=lambda item: item.path.as_posix().lower())
