import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .audio import mix_filter
from .effects import glitch_transition_filter, visual_filter
from .output_manager import OutputReservation
from .timeline import TimelineClip


def resolve_tool(root: Path, name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    bundled = root.parent / "tools" / "ffmpeg" / "ffmpeg-master-latest-win64-gpl" / "bin" / f"{name}.exe"
    if bundled.exists():
        return str(bundled)
    raise FileNotFoundError(f"No se encontró {name} en PATH ni en las herramientas del proyecto.")


def render(root: Path, clips: list[TimelineClip], audio_assets: list, reservation: OutputReservation, preset: dict) -> tuple[Path, str]:
    if not clips:
        raise RuntimeError("No hay vídeos o imágenes en inputs/videos o inputs/images.")
    ffmpeg = resolve_tool(root, "ffmpeg")
    ffprobe = resolve_tool(root, "ffprobe")
    durations = [clip.duration for clip in clips]
    total_duration = sum(durations)
    starts: list[float] = []
    cursor = 0.0
    for duration in durations:
        starts.append(cursor)
        cursor += duration
    phases = preset["montage"]["phases"]
    aspect_strategy = preset.get("render", {}).get("aspect_strategy", "crop")
    output = reservation.video_path
    root.joinpath("temp").mkdir(exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    clip_paths: list[Path] = []
    concat_path = root / "temp" / f"concat_{run_id}.txt"
    concat_video = root / "temp" / f"concat_{run_id}.mp4"
    try:
        # Process each visual independently so Windows never receives one huge
        # filter graph command line when a montage contains many sources.
        for clip, duration, start in zip(clips, durations, starts):
            temp_clip = root / "temp" / f"clip_{run_id}_{len(clip_paths):03d}.mp4"
            input_args = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error"]
            if clip.asset.kind == "image":
                input_args += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(clip.asset.path)]
            else:
                input_args += ["-ss", f"{clip.media_start:.3f}", "-t", f"{duration:.3f}", "-i", str(clip.asset.path)]
            graph = ";".join([
                visual_filter(0, "v0", duration, start, total_duration, phases, aspect_strategy),
                glitch_transition_filter("v0", "g0", duration, phases),
            ])
            input_args += [
                "-filter_complex", graph, "-map", "[g0]", "-an", "-r", "30",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", str(temp_clip),
            ]
            subprocess.run(input_args, check=True)
            clip_paths.append(temp_clip)

        concat_path.write_text("".join(f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in clip_paths), encoding="utf-8")
        subprocess.run([
            ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(concat_path), "-c", "copy", "-an", str(concat_video),
        ], check=True)

        if audio_assets:
            final_args = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-i", str(concat_video)]
            for asset in audio_assets:
                final_args += ["-i", str(asset.path)]
            audio_indexes = list(range(1, len(audio_assets) + 1))
            audio_result = mix_filter(audio_indexes)
            audio_graph = f"{audio_result[0]};{audio_result[1]}apad=whole_dur={total_duration:.3f},atrim=duration={total_duration:.3f}[aout_final]"
            final_args += ["-filter_complex", audio_graph, "-map", "0:v", "-map", "[aout_final]", "-vf", f"tpad=stop_mode=clone:stop_duration={total_duration:.3f},trim=duration={total_duration:.3f},setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-t", f"{total_duration:.3f}", "-shortest", "-movflags", "+faststart", str(output)]
        else:
            final_args = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-i", str(concat_video), "-vf", f"tpad=stop_mode=clone:stop_duration={total_duration:.3f},trim=duration={total_duration:.3f},setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv,format=yuv420p", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-color_range", "tv", "-t", f"{total_duration:.3f}", "-movflags", "+faststart", str(output)]
        subprocess.run(final_args, check=True)
    finally:
        for path in clip_paths + [concat_path, concat_video]:
            path.unlink(missing_ok=True)
        if output.exists() and output.stat().st_size == 0:
            output.unlink(missing_ok=True)
    return output, ffprobe
