"""Seeded default selection: five distinct images and one audio track."""
import random


def select_sources(infos, seed):
    rng = random.Random(seed)
    images = [info for info in infos if info.compatible and info.asset.kind == "image"]
    tracks = [info for info in infos if info.compatible and info.asset.kind == "audio"]
    if not images:
        raise RuntimeError("No hay imágenes compatibles en inputs/images.")
    warnings = []
    if len(images) < 5:
        warnings.append(f"Solo hay {len(images)} imágenes compatibles; se usarán todas.")
    chosen = rng.sample(images, min(5, len(images)))
    if tracks:
        chosen.append(rng.choice(tracks))
    else:
        warnings.append("No hay audio compatible en inputs/audio; el montaje será silencioso.")
    return chosen, warnings
