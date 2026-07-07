# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

## What it does

`karaoke_engine` converts **OpenAI Whisper `verbose_json` transcripts** (with word-level timestamps) into **karaoke `.ass` subtitle files**, and can optionally **burn subtitles into MP4 video** using system FFmpeg:

1. Parse Whisper JSON
2. Optionally segment long lines into readable karaoke lines
3. Write ASS with `\kf` karaoke timing
4. Optionally render burned-in karaoke video with FFmpeg

## What it does not do

- It does **not** transcribe audio.
- It does **not** call OpenAI or any external API.
- It does **not** require PyTorch, CUDA, or local Whisper.
- **SRT** and **VTT** parsers are not implemented yet.

## Supported input

Current supported input is **Whisper JSON with word timestamps** (root-level `words` or `segments[].words`).

## Optional FFmpeg rendering

Video rendering is optional and requires system **`ffmpeg`** and **`ffprobe`** installed on the server. FFmpeg is not bundled with this package.

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Basic ASS usage

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
- `segment_document()`
- `AssWriter`
- `build_ffmpeg_ass_burn_command()` / `render_ass_to_video()`
- `probe_video()`
