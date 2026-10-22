def mix_filter(input_indexes: list[int]) -> tuple[str, str] | None:
    if not input_indexes:
        return None
    labels = []
    parts = []
    for index in input_indexes:
        label = f"a{index}"
        parts.append(f"[{index}:a]aresample=48000,volume=0.85[{label}]")
        labels.append(f"[{label}]")
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:dropout_transition=2,aresample=async=1:first_pts=0[aout]")
    return ";".join(parts), "[aout]"
