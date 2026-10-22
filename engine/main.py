import argparse
import json
import secrets
from pathlib import Path

from .analyzer import analyze_assets
from .renderer import render, resolve_tool
from .scanner import scan_inputs
from .selection import select_sources
from .synthetic import create_synthetic_visual
from .timeline import build_timeline, validate_phases
from .validator import validate
from .output_manager import reserve_output, update_output, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera montajes GLITCH HIGH reutilizables.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--label", default="glitch_high")
    parser.add_argument("--image-seconds", type=float, default=2.0)
    parser.add_argument("--duration", type=float, default=None, help="Duración objetivo en segundos.")
    parser.add_argument("--fragment-seconds", type=float, default=4.0, help="Duración máxima de cada fragmento de vídeo.")
    parser.add_argument("--synthetic", action="store_true", help="Crear un patrón de prueba si no hay fuentes visuales compatibles.")
    parser.add_argument("--no-audio", action="store_true", help="Excluir las fuentes de audio para pruebas visuales.")
    parser.add_argument("--seed", type=int, default=None, help="Semilla determinista para el plan de selección.")
    parser.add_argument("--all-sources", action="store_true", help="Usar todas las fuentes en lugar de cinco imágenes y un audio aleatorios.")
    parser.add_argument("--preset", type=Path, default=Path("presets/glitch_high.json"))
    parser.add_argument("--check-tools", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.check_tools:
        print(json.dumps({"ffmpeg": resolve_tool(root, "ffmpeg"), "ffprobe": resolve_tool(root, "ffprobe")}, indent=2))
        return 0
    ffprobe = resolve_tool(root, "ffprobe")
    ffmpeg = resolve_tool(root, "ffmpeg")
    assets = scan_inputs(root)
    infos = analyze_assets(assets, ffprobe)
    synthetic_used = False
    if not any(info.compatible and info.asset.kind in {"video", "image"} for info in infos):
        if not args.synthetic:
            raise RuntimeError("No hay vídeos o imágenes compatibles. Añade fuentes a inputs o usa --synthetic para una prueba técnica.")
        synthetic = create_synthetic_visual(root, ffmpeg, args.duration or 4.0)
        infos.extend(analyze_assets([synthetic], ffprobe))
        synthetic_used = True
    if args.seed is None:
        args.seed = secrets.randbits(63)
    selection_warnings = []
    selected_infos = infos
    if not args.all_sources and not synthetic_used:
        selected_infos, selection_warnings = select_sources(infos, args.seed)
    clips, audio, warnings = build_timeline(selected_infos, args.image_seconds, args.duration, args.fragment_seconds, args.seed)
    warnings = selection_warnings + warnings
    if args.no_audio:
        audio = []
        warnings.append("Audio excluido explícitamente con --no-audio.")
    if not clips:
        raise RuntimeError("No se pudo construir una secuencia visual compatible. Revisa el análisis de fuentes.")
    preset_path = args.preset if args.preset.is_absolute() else root / args.preset
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    validate_phases(preset["montage"]["phases"])
    reservation = reserve_output(root, args.label)
    phases = [phase["name"] for phase in preset["montage"]["phases"]]
    selected_clips = [{
        "source": str(clip.asset.path.relative_to(root)) if clip.asset.path.is_relative_to(root) else str(clip.asset.path),
        "kind": clip.asset.kind, "media_start": clip.media_start, "duration": clip.duration,
        "source_reused": clip.source_reused,
    } for clip in clips]
    edit_plan = {
        "output_id": reservation.number, "status": "running", "label": args.label,
        "preset": str(preset_path), "intensity": "GLITCH HIGH", "phases": phases,
        "requested_duration": args.duration, "image_seconds": args.image_seconds,
        "fragment_seconds": args.fragment_seconds, "seed": args.seed,
        "no_audio": args.no_audio, "synthetic_used": synthetic_used,
        "selection_mode": "all_sources" if args.all_sources else "five_images_one_audio",
        "warnings": warnings, "selected_clips": selected_clips,
        "audio_inputs": [str(asset.path.relative_to(root)) for asset in audio],
    }
    write_json(reservation.edit_plan_path, edit_plan)
    try:
        output, ffprobe = render(root, clips, audio, reservation, preset)
        metadata = validate(output, ffprobe, ffmpeg, args.duration)
        metadata["status"] = "completed"
        metadata["output_id"] = reservation.number
        metadata["output_directory"] = reservation.directory.name
        metadata["intensity"] = "GLITCH HIGH"
        metadata["preset"] = str(preset_path)
        metadata["phases"] = phases
        metadata["requested_duration"] = args.duration
        metadata["actual_duration"] = float(metadata["duration"]) if metadata.get("duration") else None
        metadata["seed"] = args.seed
        metadata["selection_mode"] = edit_plan["selection_mode"]
        metadata["no_audio"] = args.no_audio
        metadata["warnings"] = warnings
        metadata["synthetic_used"] = synthetic_used
        metadata["source_analysis"] = [info.to_dict(root) for info in infos]
        metadata["selected_clips"] = selected_clips
        metadata["visual_inputs"] = [str(clip.asset.path.relative_to(root)) if clip.asset.path.is_relative_to(root) else str(clip.asset.path) for clip in clips]
        metadata["audio_inputs"] = [str(asset.path.relative_to(root)) for asset in audio]
        write_json(reservation.metadata_path, metadata)
        write_json(reservation.edit_plan_path, {**edit_plan, "status": "completed"})
        update_output(root, reservation, "completed", duration=metadata.get("duration"), output=output.name)
    except Exception as exc:
        failure = {**edit_plan, "status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        write_json(reservation.metadata_path, failure)
        write_json(reservation.edit_plan_path, failure)
        update_output(root, reservation, "failed", error=failure["error"])
        raise
    # ASCII-safe console output keeps Windows PowerShell cp1252 from failing
    # when a source filename contains emoji or other Unicode characters.
    print(json.dumps(metadata, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
