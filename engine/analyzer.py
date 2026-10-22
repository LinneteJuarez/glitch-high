from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .scanner import MediaAsset


@dataclass(frozen=True)
class MediaInfo:
    asset: MediaAsset
    duration: float | None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    has_video: bool = False
    has_audio: bool = False
    compatible: bool = False
    error: str | None = None

    def to_dict(self, root: Path | None = None) -> dict:
        path = self.asset.path
        if root is not None:
            try:
                path = path.relative_to(root)
            except ValueError:
                pass
        return {"path": str(path), "kind": self.asset.kind, "duration": self.duration,
                "width": self.width, "height": self.height, "fps": self.fps,
                "video_codec": self.video_codec, "audio_codec": self.audio_codec,
                "sample_rate": self.sample_rate, "channels": self.channels,
                "has_video": self.has_video, "has_audio": self.has_audio,
                "compatible": self.compatible, "error": self.error}


def _fps(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def probe_asset(asset: MediaAsset, ffprobe: str) -> MediaInfo:
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(asset.path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        data = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, TypeError) as exc:
        return MediaInfo(asset, None, compatible=False, error=str(exc))
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    raw_duration = data.get("format", {}).get("duration")
    try:
        duration = float(raw_duration) if raw_duration is not None else None
    except (TypeError, ValueError):
        duration = None
    if asset.kind == "image":
        duration = None
    sample_rate = None
    if audio and str(audio.get("sample_rate", "")).isdigit():
        sample_rate = int(audio["sample_rate"])
    return MediaInfo(
        asset, duration, video.get("width") if video else None, video.get("height") if video else None,
        _fps(video.get("r_frame_rate")) if video else None, video.get("codec_name") if video else None,
        audio.get("codec_name") if audio else None, sample_rate, audio.get("channels") if audio else None,
        bool(video), bool(audio), bool(video) if asset.kind in {"video", "image"} else bool(audio),
    )


def analyze_assets(assets: list[MediaAsset], ffprobe: str) -> list[MediaInfo]:
    return [probe_asset(asset, ffprobe) for asset in assets]
