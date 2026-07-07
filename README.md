# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

## What it does

`karaoke_engine` converts subtitle transcripts into **karaoke `.ass` subtitle files**, and can optionally **burn subtitles into MP4 video** using system FFmpeg:

1. Parse Whisper JSON, SRT, or VTT
2. Optionally segment long lines into readable karaoke lines
3. Write ASS with `\kf` karaoke timing
4. Optionally render burned-in karaoke video with FFmpeg

## What it does not do

- It does **not** transcribe audio.
- It does **not** call OpenAI or any external API.
- It does **not** require PyTorch, CUDA, or local Whisper.

## Supported input

- **Whisper JSON with word timestamps** — best option; provides real per-word karaoke timing.
- **SRT** — supported with **approximate** word timing derived by evenly splitting each cue duration across its words. SRT files usually do not contain true word-level timestamps.
- **VTT (WebVTT)** — supported with **approximate** word timing using the same cue-duration split approach. VTT files usually do not contain true word-level timestamps.

## Optional FFmpeg rendering

Video rendering is optional and requires system **`ffmpeg`** and **`ffprobe`** installed on the server. FFmpeg is not bundled with this package.

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Basic ASS usage (Whisper JSON)

```python
from karaoke_engine import KaraokeEngine, KaraokeStyle, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="transcript.json",
    output_path="karaoke.ass",
    style=KaraokeStyle.default_1080p(),
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path)
```

## Basic ASS usage (SRT fallback)

```python
from karaoke_engine import KaraokeEngine

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="lyrics.srt",
    output_path="karaoke.ass",
)
print(result.source_format)  # srt_approx
```

## Basic video render usage

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
print(result.output_path)
```

## Lower-level APIs

You can also use the components directly:

- `parse_whisper_json()` / `load_whisper_json()`
- `parse_srt_text()` / `load_srt()`
- `parse_vtt_text()` / `load_vtt()`
- `segment_document()`
- `AssWriter`
- `build_ffmpeg_ass_burn_command()` / `render_ass_to_video()`
- `probe_video()`
