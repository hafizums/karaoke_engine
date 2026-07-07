# ASS karaoke subtitles

Related: [API reference](api-reference.md) · [Supported inputs](supported-inputs.md) · [FFmpeg rendering](ffmpeg-rendering.md)

## What ASS means in this project

`karaoke_engine` generates **Advanced SubStation Alpha (ASS)** subtitle files with karaoke fill effects. Each dialogue line contains per-word `\kf` tags that control how text highlights over time.

Output is UTF-8 with Unix newlines (`\n`), deterministic for the same input.

## `\kf` timing

The writer uses the `\kf` (karaoke fill) override tag. Duration is in **centiseconds** (1/100 second).

For each word:

```
duration_cs = max(1, round((word.end - word.start) * 100))
```

Rendered in dialogue text as:

```
{\kf40}Hello {\kf35}world
```

Minimum duration is **1 centisecond** (0.01 s), even for very short words.

Whisper JSON words with `start == end` are normalized to `end = start + 0.01` in the
parser before ASS generation. See
[Supported inputs](supported-inputs.md#zero-duration-word-normalization-current-parser-behavior).

## Line structure

Each `KaraokeLine` becomes one `Dialogue:` event:

```text
Dialogue: 0,0:00:00.00,0:00:01.55,Karaoke,,0,0,0,,{\kf40}Aku {\kf35}cinta {\kf80}padamu
```

- **Start/end** come from line timestamps (first word start → last word end)
- **Style** name comes from `KaraokeStyle.name` (default `"Karaoke"`)

## Script Info and PlayRes

Default `AssWriter` settings:

| Field | Default |
|-------|---------|
| `PlayResX` | `1920` |
| `PlayResY` | `1080` |
| `Title` | `"Karaoke"` |
| `ScriptType` | `v4.00+` |

`render_video()` can auto-probe input video dimensions when `play_res_x` / `play_res_y` are omitted and `auto_probe_resolution=True`.

## KaraokeStyle presets

| Preset | Resolution target | Font size | Notes |
|--------|-------------------|-----------|-------|
| `KaraokeStyle.default_1080p()` | 1920×1080 landscape | 72 | Default when style is `None` |
| `KaraokeStyle.default_720p()` | 1280×720 landscape | 48 | Smaller outline |
| `KaraokeStyle.mobile_1080x1920()` | 1080×1920 portrait | 64 | Larger vertical margins |

### Custom style example

```python
from karaoke_engine import KaraokeEngine, KaraokeStyle

style = KaraokeStyle(
    name="Karaoke",
    font_name="Arial",
    font_size=64,
    primary_color="&H00FFFFFF",
    secondary_color="&H0000FFFF",
    outline_color="&H00000000",
    back_color="&H64000000",
    bold=False,
    italic=False,
    underline=False,
    strikeout=False,
    scale_x=100,
    scale_y=100,
    spacing=0,
    angle=0.0,
    border_style=1,
    outline=3,
    shadow=1,
    alignment=2,
    margin_l=40,
    margin_r=40,
    margin_v=80,
    encoding=1,
)

engine = KaraokeEngine()
engine.create_ass(
    transcript_path="transcript.json",
    output_path="karaoke.ass",
    style=style,
    play_res_x=1080,
    play_res_y=1920,
)
```

### ASS color format

Colors must match `&HAABBGGRR` or `&HBBGGRR` (hex BGR, optional alpha).

### Alignment

ASS alignment is 1–9 (numpad layout). Default presets use `2` (bottom center).

## Escaping and safety

`escape_ass_text()` escapes:

- `\` → `\\`
- `{` `}` → `\{` `\}`
- newlines → `\N`

Validation rejects raw ASS override tags in transcript **text** (`{...}`) to
prevent injection.

User-supplied lyrics should be treated as untrusted input. The engine escapes
dialogue text, but your app should still validate sources.

## Segmentation interaction

`KaraokeEngine.create_ass(segment=True)` runs `segment_document()` before writing
ASS. This splits long word sequences into multiple dialogue lines based on
[SegmentOptions](api-reference.md#segmentoptions).

## Customization checklist

| Goal | Approach |
|------|----------|
| Bigger text | Increase `font_size` or use `default_1080p()` |
| Portrait video | `mobile_1080x1920()` + matching `play_res_x/y` |
| Shorter lines | `SegmentOptions(max_words_per_line=4)` |
| Different title | `AssWriter(title="My Song")` or pass via engine if exposed |

Currently `create_ass()` passes `title` to `AssWriter` internally.
