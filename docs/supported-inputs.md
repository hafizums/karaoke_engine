# Supported inputs

Related: [API reference](api-reference.md) · [ASS karaoke](ass-karaoke.md) · [Troubleshooting](troubleshooting.md)

`karaoke_engine` routes transcript files by extension in `KaraokeEngine.create_ass()` and `KaraokeEngine.render_video()`:

| Extension | Parser | `source_format` | Word timing |
|-----------|--------|-----------------|-------------|
| `.json` | Whisper JSON | `whisper_json` | Real per-word timestamps |
| `.srt` | SRT | `srt_approx` | Approximate (even split) |
| `.vtt` | WebVTT | `vtt_approx` | Approximate (even split) |

Any other extension raises `UnsupportedTranscriptFormatError`.

## Whisper JSON — best for karaoke

Use OpenAI Whisper `verbose_json` output with word-level timestamps. This is the only supported input with **real** karaoke timing.

### Supported JSON shapes

1. **Root-level words** (common from OpenAI API):

```json
{
  "text": "Aku cinta padamu",
  "words": [
    {"word": "Aku", "start": 0.0, "end": 0.4},
    {"word": "cinta", "start": 0.4, "end": 0.75},
    {"word": "padamu", "start": 0.75, "end": 1.55}
  ]
}
```

2. **Segment-level words** (`segments[].words`):

```json
{
  "segments": [
    {
      "words": [
        {"word": "Hello", "start": 0.0, "end": 0.3},
        {"word": "world", "start": 0.3, "end": 0.6}
      ]
    }
  ]
}
```

### API normalization

The parser normalizes zero-duration words (`start == end`) from real OpenAI responses to a minimum duration of 0.01 seconds so validation and ASS generation succeed.

### Example file

`examples/whisper_sample.json`

## SRT — approximate word timing

SRT files provide cue-level start/end times, not per-word timestamps. The engine splits each cue duration evenly across whitespace-separated words.

### Example

```srt
1
00:00:01,000 --> 00:00:03,500
Hello world!
```

Two words over 2.5 seconds → ~1.25 s per word (approximate).

### `source_format`

`srt_approx`

### Example file

`examples/sample.srt`

## VTT / WebVTT — approximate word timing

Same approximation strategy as SRT: cue duration divided evenly across words.

### Example

```vtt
WEBVTT

00:00:01.000 --> 00:00:03.500
Hello world!
```

### `source_format`

`vtt_approx`

### Example file

`examples/sample.vtt`

## Why SRT/VTT timing is approximate

| Aspect | Whisper JSON | SRT / VTT |
|--------|--------------|-----------|
| Input granularity | Per word | Per cue/line |
| Karaoke accuracy | High | Low / estimated |
| Use case | Production karaoke | Fallback when only captions exist |
| `source_format` | `whisper_json` | `srt_approx` / `vtt_approx` |

SRT and VTT cannot recover true syllable or word alignment from cue timing alone. The engine documents this via `source_format` so callers can branch on quality expectations.

## Loading transcripts directly

Lower-level APIs bypass `KaraokeEngine` file routing:

```python
from karaoke_engine import load_whisper_json, load_srt, load_vtt

doc_json = load_whisper_json("transcript.json")
doc_srt = load_srt("captions.srt")
doc_vtt = load_vtt("captions.vtt")
```

Each returns a validated `KaraokeDocument` with the appropriate `source_format`.
