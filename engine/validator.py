from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run_decode(path: Path, ffmpeg: str) -> None:
    result = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-map", "0", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"El archivo no se puede decodificar: {result.stderr.strip()[-1000:]}")


def validate(path: Path, ffprobe: str, ffmpeg: str | None = None, expected_duration: float | None = None) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"El archivo final no existe o está vacío: {path}")
    result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("El archivo final no contiene un stream de vídeo.")
    duration_raw = data.get("format", {}).get("duration")
    duration = float(duration_raw) if duration_raw is not None else 0.0
    checks = {
        "exists_nonzero": True,
        "container_mp4": "mp4" in str(data.get("format", {}).get("format_name", "")).split(","),
        "resolution_1920x1080": video.get("width") == 1920 and video.get("height") == 1080,
        "fps_30": video.get("r_frame_rate") == "30/1",
        "codec_h264": video.get("codec_name") == "h264",
        "pixel_format_yuv420p": video.get("pix_fmt") == "yuv420p",
        "duration_positive": duration > 0,
    }
    if expected_duration is not None:
        checks["duration_matches_request"] = abs(duration - expected_duration) <= 0.05
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    if has_audio:
        checks["audio_aac"] = any(stream.get("codec_type") == "audio" and stream.get("codec_name") == "aac" for stream in streams)
    if ffmpeg is not None:
        _run_decode(path, ffmpeg)
        checks["decodable"] = True
        checks["reproducible"] = True
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Validación final fallida: " + ", ".join(failed))
    return {
        "path": str(path), "container": data.get("format", {}).get("format_name"),
        "video_codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
        "fps": video.get("r_frame_rate"), "pixel_format": video.get("pix_fmt"), "has_audio": has_audio,
        "audio_codec": next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), None),
        "duration": data.get("format", {}).get("duration"), "validation": checks,
    }
