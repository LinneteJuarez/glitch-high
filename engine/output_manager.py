from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows is the supported target.
    msvcrt = None


@dataclass(frozen=True)
class OutputReservation:
    number: int
    directory: Path
    video_path: Path
    metadata_path: Path
    edit_plan_path: Path


def _lock_file(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    handle = (output_dir / ".sequence.lock").open("a+b")
    if msvcrt is not None:
        handle.seek(0)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    return handle


@contextmanager
def _sequence_lock(output_dir: Path):
    handle = _lock_file(output_dir)
    try:
        yield
    finally:
        if msvcrt is not None:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


def _read_registry(output_dir: Path) -> dict:
    path = output_dir / "index.json"
    if not path.exists():
        return {"version": 1, "next_id": 1, "renders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Existing render folders remain authoritative if a registry is damaged.
        return {"version": 1, "next_id": 1, "renders": []}


def _write_registry(output_dir: Path, registry: dict) -> None:
    path = output_dir / "index.json"
    temporary = output_dir / "index.json.tmp"
    temporary.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def _highest_existing_id(output_dir: Path) -> int:
    highest = 0
    for folder in output_dir.glob("glitch_[0-9][0-9][0-9][0-9]"):
        try:
            highest = max(highest, int(folder.name.split("_", 1)[1]))
        except ValueError:
            continue
    return highest


def reserve_output(root: Path, label: str) -> OutputReservation:
    """Reserve a never-reused output ID atomically and persist it immediately."""
    output_dir = root / "outputs"
    with _sequence_lock(output_dir):
        registry = _read_registry(output_dir)
        used = max(_highest_existing_id(output_dir), int(registry.get("next_id", 1)) - 1)
        number = used + 1
        while True:
            directory = output_dir / f"glitch_{number:04d}"
            try:
                directory.mkdir()
                break
            except FileExistsError:
                number += 1
        now = datetime.now(timezone.utc).isoformat()
        registry.setdefault("renders", []).append({
            "id": number, "directory": directory.name, "label": label,
            "status": "running", "created_at": now,
        })
        registry["next_id"] = number + 1
        _write_registry(output_dir, registry)
    return OutputReservation(number, directory, directory / f"glitch_{number:04d}.mp4", directory / "metadata.json", directory / "edit_plan.json")


def update_output(root: Path, reservation: OutputReservation, status: str, **fields) -> None:
    output_dir = root / "outputs"
    with _sequence_lock(output_dir):
        registry = _read_registry(output_dir)
        for record in registry.setdefault("renders", []):
            if record.get("id") == reservation.number:
                record.update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat(), **fields})
                break
        _write_registry(output_dir, registry)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
