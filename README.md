# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

## What it does

`karaoke_engine` converts **OpenAI Whisper `verbose_json` transcripts** (with word-level timestamps) into **karaoke `.ass` subtitle files**:

1. Parse Whisper JSON
2. Optionally segment long lines into readable karaoke lines
3. Write ASS with `\kf` karaoke timing

## What it does not do

- It does **not** transcribe audio.
- It does **not** call OpenAI or any external API.
- It does **not** require PyTorch, CUDA, or local Whisper.
- **FFmpeg** and **video rendering** are not implemented yet.
- **SRT** and **VTT** parsers are not implemented yet.

## Supported input

Current supported input is **Whisper JSON with word timestamps** (root-level `words` or `segments[].words`).

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Basic usage

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

## Lower-level APIs

You can also use the components directly:

- `parse_whisper_json()` / `load_whisper_json()`
- `segment_document()`
- `AssWriter`
