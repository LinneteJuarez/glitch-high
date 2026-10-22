# GLITCH HIGH

A reusable Codex Agent Skill and Python/FFmpeg montage engine. Creates chaotic image montages with RGB shifts, displaced fragments, rotating glitch stickers, frame repeats, freezes and CRT interference.

## Requirements

Windows, Python 3.11+, uv, FFmpeg and ffprobe available in PATH. No third-party Python dependencies. HyperFrames is not required. Windows is the supported platform for concurrency-safe output reservation.

## Install

Clone this repository into your Codex skills directory as `glitch-high`, or keep the entire checkout in your project and install that folder as a skill. Keep `SKILL.md`, `engine`, `presets`, and `pyproject.toml` together; installing only SKILL.md is insufficient. Reload Codex's skills after installation.

## Use

From the checkout directory:

```powershell
New-Item -ItemType Directory -Force inputs/images, inputs/audio, inputs/videos, outputs, temp
uv run python -m engine.main --check-tools
uv run python -m engine.main --duration 10 --label first_montage
```

Put your own media in `inputs/images` and `inputs/audio`. Default selection is five distinct random images and one random audio. Images remain fully fitted with bars; sticker layers intentionally crop duplicated fragments. Missing audio produces a silent montage. With fewer than five images, the engine reports the shortage.

In Codex: `Use $glitch-high to create a 10-second montage from my inputs.`

Use `--seed 12345` to repeat source selection, `--no-audio` for a silent render, `--all-sources` for all media, or `--synthetic` for an explicit technical test when no visuals are available. Selection reproducibility assumes unchanged inputs and configuration; byte-identical videos are not guaranteed.

## Outputs

Each run reserves `outputs/glitch_NNNN/glitch_NNNN.mp4`, plus `metadata.json` and `edit_plan.json`. IDs persist in `outputs/index.json`; Windows file locking protects simultaneous reservations. Failed renders retain their IDs and errors. Previous outputs are retained.

Export: MP4, 1920x1080, 30 FPS, H.264, yuv420p, AAC when selected. Validation probes stream properties and fully decodes the output with FFmpeg. Rapid flashes and high-contrast distortion are inherent in this aesthetic.

## Scope and limitations

Stickers are geometric fragment cutouts, not automatic semantic subject masks. Audio is selected and mixed, but cuts are not automatically beat-detected. Source selection is seeded; the current preset stores phase effects, while edit plans reference the preset path. Keep a copy of the preset alongside a plan if you change it later.

This distribution contains code and configuration only. No user images, audio, videos, credentials, binaries, or generated renders are included. Supply media you have permission to use.
