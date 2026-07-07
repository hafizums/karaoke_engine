# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

**Status:** initial release candidate (`0.1.0`).

## Features

- Parse Whisper JSON, SRT, and WebVTT transcripts
- Segment long lines into readable karaoke lines
- Generate ASS karaoke subtitles with `\kf` timing
- Optionally burn subtitles into MP4 with system FFmpeg
- Validate documents and styles for production use

## Supported inputs

| Format | Extension | Word timing | Notes |
|--------|-----------|-------------|-------|
| Whisper JSON | `.json` | Real per-word timing | Best option for karaoke |
| SRT | `.srt` | Approximate | Cue duration split evenly across words |
| WebVTT | `.vtt` | Approximate | Cue duration split evenly across words |

SRT and VTT files usually provide line-level cues only. This engine derives approximate word timings and does **not** claim true word-level karaoke accuracy for those formats.

## What it does not do

- Transcribe audio
- Call OpenAI or any external API
- Require PyTorch, CUDA, or local Whisper
- Bundle FFmpeg

## Server requirements

- Python 3.10+
- Optional: system `ffmpeg` and `ffprobe` on `PATH` for video rendering

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
python scripts/release_check.py
```

See `RELEASE_CHECKLIST.md` for the full pre-tag release workflow.

## Basic ASS generation (Whisper JSON)

```python
from karaoke_engine import KaraokeEngine, KaraokeStyle, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="examples/whisper_sample.json",
    output_path="karaoke.ass",
    style=KaraokeStyle.default_1080p(),
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path)
```

## Basic ASS generation (SRT fallback)

```python
from karaoke_engine import KaraokeEngine

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="examples/sample.srt",
    output_path="karaoke.ass",
)
print(result.source_format)  # srt_approx
```

## Basic video render

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="examples/whisper_sample.json",
    output_path="karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
print(result.output_path)
```

## Error handling

```python
from karaoke_engine import KaraokeEngine
from karaoke_engine.errors import (
    AssGenerationError,
    RenderError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)

engine = KaraokeEngine()

try:
    engine.create_ass(
        transcript_path="transcript.json",
        output_path="karaoke.ass",
    )
except UnsupportedTranscriptFormatError as exc:
    print(f"Unsupported input: {exc}")
except TranscriptValidationError as exc:
    print(f"Invalid transcript: {exc}")
except AssGenerationError as exc:
    print(f"ASS write failed: {exc}")

try:
    engine.render_video(
        video_path="input.mp4",
        transcript_path="transcript.json",
        output_path="karaoke_output.mp4",
    )
except RenderError as exc:
    print(f"Render failed: {exc}")
```

## Production notes

- The engine converts existing transcripts; it does not transcribe audio.
- No OpenAI API calls are made by this package.
- No PyTorch, CUDA, or local Whisper installation is required.
- FFmpeg is optional and must be installed separately for `render_video()`.
- SRT/VTT timing is approximate and should be treated as a fallback path.
- Use Whisper JSON with word timestamps whenever possible for best karaoke quality.

## Lower-level APIs

- `parse_whisper_json()` / `load_whisper_json()`
- `parse_srt_text()` / `load_srt()`
- `parse_vtt_text()` / `load_vtt()`
- `segment_document()`
- `AssWriter`
- `build_ffmpeg_ass_burn_command()` / `render_ass_to_video()`
- `probe_video()`

## Examples

Sample files live in `examples/` for docs and tests:

- `whisper_sample.json` — Whisper JSON with real word timestamps
- `sample.srt` — SRT fallback with approximate word timing
- `sample.vtt` — WebVTT fallback with approximate word timing

## Release checks

Before tagging `v0.1.0`, run:

```bash
python -m pytest -q
python scripts/release_check.py
```

Optional: if system `ffmpeg` and `ffprobe` are installed, pytest also exercises a tiny real render smoke test. Machines without FFmpeg skip that test automatically.

Do not publish to PyPI unless explicitly decided. Tag manually when ready:

```bash
git tag v0.1.0
git push origin v0.1.0
```

See `RELEASE_CHECKLIST.md` for the complete checklist.
