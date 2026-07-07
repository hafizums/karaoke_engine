# FFmpeg rendering

Related: [API reference](api-reference.md) · [Quickstart](quickstart.md) · [Troubleshooting](troubleshooting.md)

## Overview

FFmpeg is an **optional external dependency**. `karaoke_engine` does not bundle or install it.

`KaraokeEngine.render_video()`:

1. Resolves PlayRes (optional FFprobe)
2. Creates ASS via `create_ass()`
3. Burns ASS into video with FFmpeg `ass` filter

## Requirements

Both must be on `PATH`:

```bash
ffmpeg -version
ffprobe -version
```

## Basic usage

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="output/karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
```

## RenderOptions

| Field | Default | Description |
|-------|---------|-------------|
| `crf` | `18` | x264 quality (0–51, lower = better) |
| `preset` | `"veryfast"` | x264 speed preset |
| `video_codec` | `"libx264"` | Video encoder |
| `audio_codec` | `"copy"` | Audio stream handling |
| `timeout_seconds` | `1800.0` | Subprocess timeout |
| `overwrite` | `True` | Pass `-y` to FFmpeg |

### Example: smaller file, slower encode

```python
RenderOptions(crf=23, preset="medium", audio_codec="copy")
```

### Example: re-encode audio

```python
RenderOptions(audio_codec="aac")
```

Use when `audio_codec="copy"` fails (incompatible container/codec). See [Troubleshooting](troubleshooting.md).

## Sidecar ASS behavior

By default, ASS is written next to the output video:

```
output/karaoke_output.mp4
output/karaoke_output.ass   ← default sidecar path
```

Override with `ass_output_path`:

```python
engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="output/karaoke_output.mp4",
    ass_output_path="output/karaoke.ass",
)
```

## Auto probe resolution

When `auto_probe_resolution=True` (default) and `play_res_x` or `play_res_y` is `None`, the engine calls `probe_video()` to match ASS PlayRes to the input video.

Disable for fixed dimensions:

```python
engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="output.mp4",
    play_res_x=1920,
    play_res_y=1080,
    auto_probe_resolution=False,
)
```

## FFmpeg command built internally

`build_ffmpeg_ass_burn_command()` produces a list like:

```
ffmpeg -y -i <video> -vf ass=<escaped-ass-path> -c:v libx264 -crf 18 -preset veryfast -c:a copy <output>
```

- Uses `shell=False`
- ASS paths are escaped for Windows drive letters and quotes

## Path validation

`render_ass_to_video()` checks:

- Video and ASS paths exist and are files
- Output path is not an existing **directory**
- Paths are non-empty in command builder

## Common FFmpeg errors

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Failed to execute FFmpeg` | Binary not on PATH | Install FFmpeg |
| `Input video file does not exist` | Wrong path | Verify `video_path` |
| `ASS subtitle file does not exist` | ASS step failed | Fix transcript/ASS first |
| `exit code != 0` + codec error | Audio copy incompatible | `RenderOptions(audio_codec="aac")` |
| ASS filter parse error (Windows) | Path escaping | Upgrade to latest engine; check path has no odd characters |
| Timeout | Long video | Increase `timeout_seconds` |

## Lower-level API

```python
from karaoke_engine import build_ffmpeg_ass_burn_command, render_ass_to_video, RenderOptions

command = build_ffmpeg_ass_burn_command(
    video_path="in.mp4",
    ass_path="subs.ass",
    output_path="out.mp4",
    options=RenderOptions(),
)
# Inspect command before running, or:
result = render_ass_to_video(
    video_path="in.mp4",
    ass_path="subs.ass",
    output_path="out.mp4",
)
```

`RenderVideoResult` includes `return_code` and `stderr` for logging.
