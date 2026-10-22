---
name: glitch-high
description: Create, test, validate, or extend reusable GLITCH HIGH audiovisual montages from project-local media with the bundled Python and FFmpeg engine. Use for this engine's montage workflow, not for generic video editing or one-off FFmpeg commands.
metadata:
  short-description: Render reusable GLITCH HIGH montages
---

# GLITCH HIGH

## Activate when

Use this skill when the request is to render, test, validate, inspect, or extend the reusable GLITCH ENGINE montage pipeline. Do not use it for unrelated video questions, generic FFmpeg advice, or a one-off command that does not belong to this project.

## Locate the project

Find the directory containing `engine/main.py`, `presets/glitch_high.json`, and `pyproject.toml`. This public distribution bundles them beside this SKILL.md; use that directory as the engine root unless the user provides another compatible project. Create missing `inputs/images`, `inputs/audio`, `inputs/videos`, `outputs`, and `temp` folders before use. Treat input media as read-only and never delete or overwrite sources. Resolve all engine and preset paths relative to this root, not the shell's arbitrary current directory.

## Run the engine

Run commands from the `GLITCH_ENGINE/` directory. Use the project-managed environment and do not add Python dependencies unless an implemented feature requires them:

```powershell
uv run python -m engine.main --check-tools
uv run python -m engine.main --label montaje_01
uv run python -m engine.main --duration 30 --fragment-seconds 3 --seed 20261021 --label montaje_30s
```

Useful options are `--duration`, `--image-seconds`, `--fragment-seconds`, `--seed`, `--no-audio`, and explicit `--synthetic`. Use `--synthetic` only when compatible visual inputs are unavailable and record that fact in the result metadata.

## Source discovery and edit plan

Default montage selection is five distinct random compatible images from `inputs/images` and exactly one random compatible audio file from `inputs/audio`. The engine generates and persists a fresh seed unless `--seed` is supplied. Do not mix every audio file by default. With fewer than five images, use all available and report the shortage; with no audio, report a silent montage. `--no-audio` remains an explicit override. Use `--all-sources` only when the user requests all media, videos, or a broader selection. Changing duration must not change the five-image selection rule; reuse the selected images as needed.

The engine scans `inputs/videos`, `inputs/images`, and `inputs/audio`, then probes each compatible asset with `ffprobe`. It records duration, dimensions, FPS, codecs, sample rate, and channels. Videos are split into fragments, still images become animated clips, and available audio is mixed as a rhythmic base. If the requested duration exceeds available visuals, reuse is allowed and must be reported in `metadata.json` and `edit_plan.json`.

Use `--seed` when a repeatable selection order is required. The seed and selected clips are persisted in the edit plan; a repeat with the same inputs, preset, duration, fragment size, and seed must produce the same plan.

## GLITCH HIGH treatment

Create glitch stickers from duplicated fragments of the current image: paste cropped duplicate layers with borders, transparent rotated corners, jumps in both axes, different scales and mirrored variants. Keep the original background image fully fitted with bars. Fragment cropping applies only to sticker copies, not to the base image. Current stickers use geometric fragment crops, not automatic semantic subject segmentation. Combine vertical and tilted tears with horizontal corruption and irregular staggered sticker bursts; avoid a uniformly horizontal rhythm.

Preserve the modular treatment implemented by `engine/effects.py`: variable RGB channel shift, frame skipping, frame repeat, digital freeze, displaced bands and blocks, corruption overlays, electronic noise, scanlines/CRT interference, ghost/image overlays, abrupt speed changes, and fragmented boundary transitions. Keep the four preset phases: INTRO, FRAGMENTATION, CHAOS, and COLLAPSE.

Read `presets/glitch_high.json` as the source of truth for phase intensity and output framing. For still images, the skill must use `render.aspect_strategy: bars`: scale each image down proportionally so its complete original frame remains visible, then add bars to fill 1920×1080. Never crop, zoom-crop, or stretch an image. `crop` is reserved for an explicit user request and must never be selected by default.

## Accumulative outputs

Every render must reserve a new monotonic ID under `outputs/glitch_NNNN/`. The folder contains:

- `glitch_NNNN.mp4` (same numeric ID as its folder; for example `glitch_0016/glitch_0016.mp4`). Never use the generic filename `final.mp4` for new renders, so exported files remain distinguishable outside their folders.
- `metadata.json`
- `edit_plan.json`

`outputs/index.json` is the persistent registry and `outputs/.sequence.lock` protects ID reservation against concurrent Windows runs. Never reuse an ID, delete previous outputs, or replace an existing folder. A failed render keeps its reserved folder and records `status: failed` plus the error.

## Required export and validation

The final file must be MP4, 1920×1080, 16:9, 30 FPS, H.264, and `yuv420p`. Include AAC when compatible audio exists; omit audio when no audio is selected or available. Do not report success from the process exit code alone. The engine's validator must confirm file existence and nonzero size, MP4 container, duration, resolution, FPS, H.264, pixel format, AAC when applicable, and complete FFmpeg decoding/reproducibility via `ffprobe` and FFmpeg.

After a render, report the exact absolute path to `glitch_NNNN.mp4` and its JSON sidecars. If validation fails, report the failed checks and keep the failed reservation intact.

## Implementation boundary

Reuse the existing modules in `engine/` (`scanner.py`, `analyzer.py`, `timeline.py`, `effects.py`, `audio.py`, `renderer.py`, `output_manager.py`, `validator.py`, and `main.py`). Extend those modules or the preset when needed; do not reimplement the motor inside this skill and do not use HyperFrames as a substitute for the tested Python+FFmpeg path.
