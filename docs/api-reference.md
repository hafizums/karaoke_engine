# API reference

Related: [Quickstart](quickstart.md) · [Supported inputs](supported-inputs.md) · [ASS karaoke](ass-karaoke.md) · [FFmpeg rendering](ffmpeg-rendering.md)

All symbols below are exported from `karaoke_engine` unless noted.

## KaraokeEngine

High-level orchestrator for parsing, segmentation, ASS generation, and optional video rendering.

```python
from karaoke_engine import KaraokeEngine

engine = KaraokeEngine()
```

### `create_ass()`

Load a transcript (`.json`, `.srt`, or `.vtt`), optionally segment, and write ASS.

```python
result = engine.create_ass(
    transcript_path="examples/whisper_sample.json",
    output_path="output/karaoke.ass",
    style=None,                    # KaraokeStyle | None → default_1080p()
    segment_options=None,          # SegmentOptions | None → defaults
    segment=True,                  # bool — run segmenter
    play_res_x=1920,
    play_res_y=1080,
    title="Karaoke",
)
```

**Returns:** `CreateAssResult`

**Raises:**

- `UnsupportedTranscriptFormatError` — unknown file extension
- `TranscriptValidationError` — invalid transcript data
- `AssGenerationError` — file write failure

### `render_video()`

Create ASS from transcript and burn into video with FFmpeg.

```python
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="output/karaoke_output.mp4",
    ass_output_path=None,          # default: output_path.with_suffix(".ass")
    style=None,
    segment_options=None,
    segment=True,
    play_res_x=None,               # None + auto_probe → probed width
    play_res_y=None,
    title="Karaoke",
    render_options=None,           # RenderOptions()
    auto_probe_resolution=True,    # probe video for PlayRes when x/y omitted
)
```

**Returns:** `RenderKaraokeVideoResult`

**Raises:** Same as `create_ass()`, plus `RenderError` for FFmpeg/FFprobe failures.

---

## Result types

### `CreateAssResult`

| Field | Type | Description |
|-------|------|-------------|
| `ass_path` | `Path` | Written ASS file |
| `line_count` | `int` | Lines in final document |
| `word_count` | `int` | Total words |
| `source_format` | `str` | e.g. `whisper_json`, `srt_approx` |
| `segmented` | `bool` | Whether segmentation ran |

### `RenderKaraokeVideoResult`

Same metadata as `CreateAssResult`, plus:

| Field | Type | Description |
|-------|------|-------------|
| `video_path` | `Path` | Input video |
| `output_path` | `Path` | Rendered MP4 |

---

## KaraokeStyle

ASS V4+ style definition. See [ASS karaoke](ass-karaoke.md) for presets and colors.

```python
from karaoke_engine import KaraokeStyle

style = KaraokeStyle.default_1080p()
# Also: default_720p(), mobile_1080x1920()
```

Invalid values raise `ValueError` at construction time.

---

## SegmentOptions

Controls line breaking when `segment=True`.

```python
from karaoke_engine import SegmentOptions

opts = SegmentOptions(
    max_words_per_line=6,
    max_chars_per_line=38,
    max_line_duration=5.0,
    min_line_duration=0.8,
    pause_break_seconds=0.65,
    punctuation_break_chars=".!?。！？",
    preserve_source_format=True,
)
```

| Field | Default | Description |
|-------|---------|-------------|
| `max_words_per_line` | `6` | Break before exceeding word count |
| `max_chars_per_line` | `38` | Break before exceeding character count |
| `max_line_duration` | `5.0` | Max seconds per line |
| `min_line_duration` | `0.8` | Min duration before punctuation break |
| `pause_break_seconds` | `0.65` | Gap between words that forces break |
| `punctuation_break_chars` | `.!?。！？` | Break after punctuation |
| `preserve_source_format` | `True` | Keep original `source_format` |

---

## RenderOptions

FFmpeg encoding options for burn-in.

```python
from karaoke_engine import RenderOptions

opts = RenderOptions(
    crf=18,
    preset="veryfast",
    video_codec="libx264",
    audio_codec="copy",
    timeout_seconds=1800.0,
    overwrite=True,
)
```

See [FFmpeg rendering](ffmpeg-rendering.md) for details.

---

## Parsers

### Whisper JSON

```python
from karaoke_engine import parse_whisper_json, load_whisper_json

document = parse_whisper_json({"words": [...]})
document = load_whisper_json("transcript.json")
```

### SRT

```python
from karaoke_engine import parse_srt_text, load_srt

document = parse_srt_text(srt_string)
document = load_srt("captions.srt")
```

### VTT

```python
from karaoke_engine import parse_vtt_text, load_vtt

document = parse_vtt_text(vtt_string)
document = load_vtt("captions.vtt")
```

All parsers return `KaraokeDocument` and run validation.

---

## segment_document()

```python
from karaoke_engine import segment_document, SegmentOptions

segmented = segment_document(document, SegmentOptions(max_words_per_line=5))
```

Flattens all words, re-segments into shorter lines, validates output. `source_format` becomes `"segmented"` only when `preserve_source_format=False`.

---

## AssWriter

Lower-level ASS generator. Used internally by `KaraokeEngine.create_ass()`.

```python
from karaoke_engine import AssWriter, KaraokeStyle, load_whisper_json

document = load_whisper_json("transcript.json")
writer = AssWriter(
    style=KaraokeStyle.default_1080p(),
    play_res_x=1920,
    play_res_y=1080,
    title="Karaoke",
)
ass_text = writer.generate(document)
writer.write_to_file(document, "output/karaoke.ass")
```

`generate()` and `write_to_file()` call `ensure_valid_document()` first.

---

## Lower-level render helpers

```python
from karaoke_engine import (
    build_ffmpeg_ass_burn_command,
    render_ass_to_video,
    build_ffprobe_command,
    probe_video,
    RenderOptions,
    VideoInfo,
)
```

| Function | Purpose |
|----------|---------|
| `build_ffmpeg_ass_burn_command()` | Build FFmpeg argv list |
| `render_ass_to_video()` | Run FFmpeg burn-in |
| `build_ffprobe_command()` | Build FFprobe argv list |
| `probe_video()` | Return `VideoInfo` (width, height, duration) |

---

## Exceptions

All inherit from `KaraokeEngineError`.

| Exception | When raised |
|-----------|-------------|
| `UnsupportedTranscriptFormatError` | Bad extension or malformed parser input |
| `TranscriptValidationError` | Document/word validation failure |
| `AssGenerationError` | ASS file write failure |
| `RenderError` | FFmpeg/FFprobe missing, bad paths, non-zero exit |

### Example error handling

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
    engine.create_ass(transcript_path="t.json", output_path="out.ass")
except UnsupportedTranscriptFormatError as exc:
    ...
except TranscriptValidationError as exc:
    ...
except AssGenerationError as exc:
    ...
```

---

## Models (advanced)

```python
from karaoke_engine import KaraokeDocument, KaraokeLine, Word, ValidationReport
```

Typically constructed by parsers, not by application code.
