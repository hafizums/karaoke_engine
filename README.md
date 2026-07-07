# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

**Status:** initial release candidate (`0.1.0`).

Convert transcript files (Whisper JSON, SRT, VTT) into ASS karaoke subtitles and optionally burn them into MP4 with system FFmpeg.

## Documentation

Full docs live in [`docs/`](docs/index.md):

| Guide | Topic |
|-------|-------|
| [docs/index.md](docs/index.md) | Documentation home |
| [docs/quickstart.md](docs/quickstart.md) | Install, test, first ASS output |
| [docs/supported-inputs.md](docs/supported-inputs.md) | Whisper JSON vs SRT/VTT |
| [docs/api-reference.md](docs/api-reference.md) | Public API |
| [docs/ass-karaoke.md](docs/ass-karaoke.md) | `\kf` timing and styles |
| [docs/ffmpeg-rendering.md](docs/ffmpeg-rendering.md) | Video burn-in |
| [docs/real-openai-smoke-test.md](docs/real-openai-smoke-test.md) | Manual OpenAI + FFmpeg smoke test |
| [docs/production-usage.md](docs/production-usage.md) | Server integration |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common problems |
| [docs/development.md](docs/development.md) | Contributing |
| [docs/release.md](docs/release.md) | Release checklist |

## Features

- Parse Whisper JSON, SRT, and WebVTT transcripts
- Segment long lines into readable karaoke lines
- Generate ASS karaoke subtitles with `\kf` timing
- Optionally burn subtitles into MP4 with system FFmpeg
- Validate documents and styles for production use

## Supported inputs

| Format | Extension | Word timing | `source_format` | Notes |
|--------|-----------|-------------|-----------------|-------|
| Whisper JSON | `.json` | Real per-word timing | `whisper_json` | Best option for karaoke |
| SRT | `.srt` | Approximate | `srt_approx` | Cue duration split evenly across words |
| WebVTT | `.vtt` | Approximate | `vtt_approx` | Cue duration split evenly across words |

> **Warning:** SRT and VTT provide line-level cues only. Word timing is **approximate** — not true karaoke accuracy. Use Whisper JSON whenever possible.

## What it does not do

- Transcribe audio
- Call OpenAI or any external API (inside the package)
- Require PyTorch, CUDA, or local Whisper
- Bundle FFmpeg
- Provide web UI, browser rendering, or Frappe integration

## Server requirements

- Python 3.10+
- Optional: system `ffmpeg` and `ffprobe` on `PATH` for video rendering

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
python scripts/release_check.py
```

See [docs/installation.md](docs/installation.md) and [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## Quick usage: JSON → ASS

```python
from karaoke_engine import KaraokeEngine, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="examples/whisper_sample.json",
    output_path="karaoke.ass",
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path, result.source_format)  # whisper_json
```

## Quick usage: video render

Requires FFmpeg on `PATH`. See [docs/ffmpeg-rendering.md](docs/ffmpeg-rendering.md).

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

See [docs/production-usage.md](docs/production-usage.md).

## Lower-level APIs

- `parse_whisper_json()` / `load_whisper_json()`
- `parse_srt_text()` / `load_srt()`
- `parse_vtt_text()` / `load_vtt()`
- `segment_document()`
- `AssWriter`
- `build_ffmpeg_ass_burn_command()` / `render_ass_to_video()`
- `probe_video()`

Documented in [docs/api-reference.md](docs/api-reference.md).

## Examples

Sample files in `examples/`:

- `whisper_sample.json` — Whisper JSON with real word timestamps
- `sample.srt` — SRT fallback with approximate word timing
- `sample.vtt` — WebVTT fallback with approximate word timing

## Release checks

```bash
python -m pytest -q
python scripts/release_check.py
```

Optional: pytest runs a tiny FFmpeg smoke test when `ffmpeg` and `ffprobe` are on `PATH`; otherwise skipped.

Do not publish to PyPI unless explicitly decided. Tag manually when ready:

```bash
git tag v0.1.0
git push origin v0.1.0
```

See [docs/release.md](docs/release.md) and [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## Manual real OpenAI karaoke video smoke test

> **Warning:** Uses **real OpenAI API credits**. Not part of normal pytest.

`scripts/real_openai_karaoke_video_smoke.py` proves the full workflow:

`media → OpenAI whisper-1 → karaoke_engine → .ass → FFmpeg → karaoke_output.mp4`

- Requires `OPENAI_API_KEY` in environment (never printed by script)
- Requires `pip install openai` (not a core runtime dependency)
- Requires network and FFmpeg/FFprobe for video render

**PowerShell:**

```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
python scripts/real_openai_karaoke_video_smoke.py demo.mp4
```

**Audio with generated test video:**

```powershell
python scripts/real_openai_karaoke_video_smoke.py demo.mp3 --make-test-video
```

Full details: [docs/real-openai-smoke-test.md](docs/real-openai-smoke-test.md)

Expected outputs in `real_api_smoke_output/`:

- `openai_whisper_transcript.json`
- `karaoke.ass`
- `karaoke_output.mp4` (when video render runs)
