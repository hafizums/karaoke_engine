# Quickstart

Get from zero to a karaoke ASS file (and optionally a rendered video) in a few minutes.

Related: [Installation](installation.md) · [Supported inputs](supported-inputs.md) · [API reference](api-reference.md)

## 1. Create a virtual environment

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

## 2. Install in dev mode

From the repository root:

```bash
pip install -e ".[dev]"
```

## 3. Run tests

```bash
python -m pytest -q
python scripts/release_check.py
```

## 4. Generate ASS from Whisper JSON (best quality)

```python
from karaoke_engine import KaraokeEngine, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="examples/whisper_sample.json",
    output_path="output/karaoke.ass",
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path)
print(result.source_format)  # whisper_json
```

**Expected:** `output/karaoke.ass` containing `[Script Info]`, `[V4+ Styles]`, `[Events]`, and `\kf` tags.

## 5. Generate ASS from SRT or VTT (approximate timing)

```python
from karaoke_engine import KaraokeEngine

engine = KaraokeEngine()

srt_result = engine.create_ass(
    transcript_path="examples/sample.srt",
    output_path="output/from_srt.ass",
)
print(srt_result.source_format)  # srt_approx

vtt_result = engine.create_ass(
    transcript_path="examples/sample.vtt",
    output_path="output/from_vtt.ass",
)
print(vtt_result.source_format)  # vtt_approx
```

> **Warning:** SRT and VTT word timing is approximate. See [Supported inputs](supported-inputs.md).

## 6. Optional: render video with FFmpeg

Requires `ffmpeg` and `ffprobe` on `PATH`. See [FFmpeg rendering](ffmpeg-rendering.md).

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="examples/whisper_sample.json",
    output_path="output/karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
print(result.output_path)
print(result.ass_path)  # sidecar .ass next to output by default
```

**Expected files:**

| File | Description |
|------|-------------|
| `output/karaoke.ass` | Karaoke subtitle file |
| `output/karaoke_output.mp4` | Video with burned-in subtitles (if render ran) |
| `output/karaoke_output.ass` | Default sidecar when using `render_video()` without `ass_output_path` |

When you pass `ass_output_path`, the sidecar is written to that path instead.

## Next steps

- [ASS karaoke details](ass-karaoke.md) — styles and `\kf` timing
- [Production usage](production-usage.md) — integrate into a server
- [Real OpenAI smoke test](real-openai-smoke-test.md) — manual full pipeline with API credits
