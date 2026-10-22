from __future__ import annotations

import random
from dataclasses import dataclass
from .analyzer import MediaInfo
from .scanner import MediaAsset


@dataclass(frozen=True)
class TimelineClip:
    asset: MediaAsset
    input_index: int
    duration: float
    media_start: float = 0.0
    image_seconds: float = 2.0
    source_reused: bool = False


def validate_phases(phases: list[dict]) -> None:
    if not phases:
        raise ValueError("El preset debe definir al menos una fase.")
    cursor = 0.0
    for phase in phases:
        start, end = float(phase["start"]), float(phase["end"])
        if start != cursor or not 0 <= start < end <= 1:
            raise ValueError("Las fases deben ser contiguas y cubrir [0, 1].")
        cursor = end
    if cursor != 1.0:
        raise ValueError("Las fases deben terminar exactamente en 1.0.")


def build_timeline(infos: list[MediaInfo], image_seconds: float = 2.0,
                   target_duration: float | None = None, fragment_seconds: float = 4.0,
                   seed: int | None = None):
    if image_seconds <= 0 or fragment_seconds <= 0:
        raise ValueError("image_seconds y fragment_seconds deben ser positivos.")
    if target_duration is not None and target_duration <= 0:
        raise ValueError("La duración objetivo debe ser positiva.")
    warnings: list[str] = []
    valid = [info for info in infos if info.compatible]
    visuals = [info for info in valid if info.asset.kind in {"video", "image"}]
    audio = [info.asset for info in valid if info.asset.kind == "audio"]
    segments: list[tuple[MediaInfo, float, float]] = []
    for info in visuals:
        if info.asset.kind == "image":
            segments.append((info, 0.0, image_seconds))
            continue
        duration = info.duration or 0.0
        if duration <= 0:
            warnings.append(f"Se omitió vídeo sin duración válida: {info.asset.path.name}")
            continue
        start = 0.0
        while start < duration - 0.001:
            length = min(fragment_seconds, duration - start)
            if length >= 0.05:
                segments.append((info, start, length))
            start += length
    if not segments:
        return [], audio, [*warnings, "No hay fuentes visuales compatibles."]
    if seed is not None:
        random.Random(seed).shuffle(segments)
    if target_duration is None:
        selected = segments
    else:
        total = sum(item[2] for item in segments)
        if total < target_duration:
            warnings.append(f"Fuentes insuficientes ({total:.2f}s); se reutilizarán segmentos para llegar a {target_duration:.2f}s.")
        selected = []
        elapsed, cursor = 0.0, 0
        while elapsed < target_duration - 0.001:
            info, start, length = segments[cursor % len(segments)]
            length = min(length, target_duration - elapsed)
            selected.append((info, start, length))
            elapsed += length
            cursor += 1
    clips = [TimelineClip(info.asset, index, length, start, image_seconds, index >= len(segments))
             for index, (info, start, length) in enumerate(selected)]
    return clips, audio, warnings
