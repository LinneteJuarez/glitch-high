from __future__ import annotations

from typing import Any


def _phase_value(phases: list[dict[str, Any]], key: str, fallback: float, progress: str) -> str:
    expression = str(fallback)
    for phase in reversed(phases):
        end = float(phase["end"])
        value = phase.get(key, fallback)
        expression = f"if(lt({progress},{end:.6f}),{value},{expression})"
    return expression


def _phase_enable(phase: dict[str, Any], progress: str) -> str:
    return f"between({progress},{float(phase['start']):.6f},{float(phase['end']):.6f})"


def visual_filter(index: int, label: str, duration: float, start: float, total: float, phases: list[dict[str, Any]], aspect_strategy: str = "crop") -> str:
    """Build a phase-aware GLITCH HIGH graph for one visual source."""
    if aspect_strategy not in {"crop", "bars"}:
        raise ValueError("aspect_strategy debe ser 'crop' o 'bars'.")
    progress = f"((t+{start:.6f})/{max(total, 0.001):.6f})"
    progress_pts = f"((T+{start:.6f})/{max(total, 0.001):.6f})"
    skip_interval = _phase_value(phases, "skip_interval", 127, progress)
    skip_span = _phase_value(phases, "skip_span", 2, progress)
    fast_speed = _phase_value(phases, "speed_fast", 0.45, progress_pts)
    slow_speed = _phase_value(phases, "speed_slow", 1.8, progress_pts)
    displacement = _phase_value(phases, "displacement", 18, progress)
    corruption_interval = _phase_value(phases, "corruption_interval", 53, progress)
    ghost_window = _phase_value(phases, "ghost_window", 16, progress)
    repeat_target = total * 0.60
    freeze_target = total * 0.91
    repeat_start = max(0, int((repeat_target - start) * 30))
    freeze_start = max(0, int((freeze_target - start) * 30))
    repeat_loops = max(0, int(max(phase.get("repeat_loops", 0) for phase in phases)))
    freeze_frames = max(1, int(max(phase.get("freeze_frames", 1) for phase in phases)))

    framing = (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080:x='(iw-1920)*abs(sin(t*0.45))':y='(ih-1080)*abs(cos(t*0.31))'"
        if aspect_strategy == "crop" else
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    graph = [
        (
            f"[{index}:v]{framing},"
            f"setsar=1,fps=30,format=yuv444p,"
            f"eq=contrast=1.35:brightness=0.02:saturation=1.8,"
            f"setpts='if(lt(mod(T,3),0.18),PTS*{fast_speed},if(gt(mod(T,3),2.4),PTS*{slow_speed},PTS))',"
            f"select='not(between(mod(n,{skip_interval}),0,{skip_span}))',setpts=N/FRAME_RATE/TB,"
            f"loop=loop={repeat_loops}:size=3:start={repeat_start},"
            f"loop=loop={freeze_frames}:size=1:start={freeze_start},"
            f"split=7[main{index}][ghost{index}][band{index}][block{index}]"
            f"[stickerA{index}][stickerB{index}][vertical{index}]"
        ),
        f"[ghost{index}]hue=h=18:s=1.65,format=rgba,colorchannelmixer=aa=0.30[ghostfx{index}]",
        (
            f"[main{index}][ghostfx{index}]overlay="
            f"x='if(lt(mod(t,41),{ghost_window}),{displacement}*sin(t*24),0)':"
            f"y='if(lt(mod(t,41),{ghost_window}),{displacement}*0.7*cos(t*19),0)':"
            f"enable='lt(mod(t,41),{ghost_window})'[overlay{index}]"
        ),
        f"[band{index}]crop=1920:120:0:420,format=rgba,setpts=PTS-STARTPTS[bandcrop{index}]",
        (
            f"[overlay{index}][bandcrop{index}]overlay="
            f"x='if(lt(mod(t,37),12),{displacement}*sin(t*20),0)':y=420:"
            f"enable='lt(mod(t,37),12)'[bandfx{index}]"
        ),
        f"[block{index}]crop=640:180:0:220,format=rgba,setpts=PTS-STARTPTS[blockcrop{index}]",
        (
            f"[bandfx{index}][blockcrop{index}]overlay="
            f"x='if(lt(mod(t*30,{corruption_interval}),10),120+{displacement}*4*sin(t*31),0)':"
            f"y='if(lt(mod(t*30,{corruption_interval}),10),620,220)':"
            f"enable='lt(mod(t*30,{corruption_interval}),10)'[fragmented{index}]"
        ),
    ]

    # Fragment stickers are intentionally rectangular cutouts, not semantic masks.
    # Keep the underlying full-frame composition intact; crop only duplicate layers.
    graph.extend([
        f"[stickerA{index}]crop=700:700:610:180,scale=420:420,format=rgba,"
        f"drawbox=x=0:y=0:w=iw:h=ih:c=white:t=8,"
        f"rotate='0.42*sin(t*7+{start})':ow=600:oh=600:c=none[cutA{index}]",
        f"[stickerB{index}]crop=520:360:760:350,scale=600:416,hflip,format=rgba,"
        f"drawbox=x=0:y=0:w=iw:h=ih:c=cyan:t=6,"
        f"rotate='-0.6*cos(t*11+{start})':ow=760:oh=760:c=none[cutB{index}]",
        f"[vertical{index}]crop=160:900:880:90,format=rgba,"
        f"rotate=0.24:ow=400:oh=1000:c=none[tear{index}]",
        f"[fragmented{index}][tear{index}]overlay="
        f"x='mod(floor(t*13+{start})*367,1500)':"
        f"y='-180+260*sin(t*23)':enable='lt(mod(t*30,19),8)'[torn{index}]",
        f"[torn{index}][cutA{index}]overlay="
        f"x='mod(floor(t*5+{start})*563,1320)':"
        f"y='mod(floor(t*7+{start})*257,480)':"
        f"enable='gt(mod(t*30,23),5)'[pastedA{index}]",
        f"[pastedA{index}][cutB{index}]overlay="
        f"x='mod(floor(t*9+{start})*379,1160)':"
        f"y='mod(floor(t*6+{start})*193,320)':"
        f"enable='lt(mod(t*30,17),9)'[pastedB{index}]",
    ])
    previous = f"pastedB{index}"
    for phase in phases:
        rgb = phase.get("rgb_shift", {})
        rgb_label = f"rgb{index}_{phase['name']}"
        window = float(phase.get("rgb_window", 0.08))
        graph.append(
            f"[{previous}]rgbashift=rh={rgb.get('rh', 0)}:rv={rgb.get('rv', 0)}:"
            f"gh={rgb.get('gh', 0)}:bv={rgb.get('bv', 0)}:"
            f"enable='{_phase_enable(phase, progress)}*lt(mod(t,2),{window})'[{rgb_label}]"
        )
        previous = rgb_label

    graph.append(
        f"[{previous}]noise=alls={max(int(phase.get('noise', 18)) for phase in phases)}:allf=t+u,"
        f"drawgrid=w=iw:h=8:t=1:c=black@0.18,"
        f"drawbox=x=0:y='mod(t*30,12)*90':w=iw:h=4:c=white@0.26:t=fill:"
        f"enable='lt(mod(t*30,17),3)',"
        f"drawbox=x=0:y=0:w=iw:h=ih:c=black@0.24:t=fill:enable='lt(t,0.16)',"
        f"drawbox=x=0:y=0:w=iw:h=ih:c=white@0.18:t=fill:enable='gt(t,{max(0.0, duration - 0.16):.3f})',"
        f"tpad=stop_mode=clone:stop_duration=1,trim=duration={duration:.3f},"
        f"format=yuv420p,setpts=PTS-STARTPTS[{label}]"
    )
    return ";".join(graph)


def glitch_transition_filter(input_label: str, output_label: str, duration: float, phases: list[dict[str, Any]]) -> str:
    """Add an abrupt fragmented boundary treatment, strongest in COLLAPSE."""
    collapse = next(phase for phase in phases if phase["name"] == "COLLAPSE")
    strength = float(collapse.get("transition_strength", 0.32))
    return (
        f"[{input_label}]drawbox=x='if(lt(mod(t*30,19),7),mod(t*2910,1600),0)':"
        f"y='if(lt(mod(t*30,19),7),mod(t*1290,900),0)':w=320:h=90:"
        f"c=magenta@{strength:.2f}:t=fill:enable='lt(t,0.12)',"
        f"drawbox=x='if(gt(t,{max(0.0, duration - 0.12):.3f}),mod(t*2130,1600),0)':"
        f"y='if(gt(t,{max(0.0, duration - 0.12):.3f}),mod(t*930,900),0)':"
        f"w=480:h=70:c=cyan@{strength:.2f}:t=fill:enable='gt(t,{max(0.0, duration - 0.12):.3f})'[{output_label}]"
    )


def concat_filter(labels: list[str]) -> str:
    return f"{''.join(f'[{label}]' for label in labels)}concat=n={len(labels)}:v=1:a=0[vout]"
