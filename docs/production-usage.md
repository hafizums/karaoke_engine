# Production usage

Related: [API reference](api-reference.md) · [FFmpeg rendering](ffmpeg-rendering.md) · [Troubleshooting](troubleshooting.md) · [Real OpenAI smoke test](real-openai-smoke-test.md)

## Recommended server workflow

`karaoke_engine` is a **library**, not a web service. Your application owns orchestration:

```
1. Obtain transcript (your app calls OpenAI or loads existing file)
2. Save transcript to temp/storage path
3. karaoke_engine.create_ass() or render_video()
4. Store output ASS/MP4
5. Clean up temp files
```

The engine never calls OpenAI. Transcription stays in your app layer.

## Job queue pattern

Typical async job:

| Step | Worker action |
|------|---------------|
| Enqueue | `{transcript_path, video_path?, output_id}` |
| Validate | Check paths, extensions, file size limits |
| Process | `create_ass()` or `render_video()` |
| Store | Upload ASS/MP4 to object storage |
| Notify | Webhook / DB status update |

Use timeouts on FFmpeg (`RenderOptions.timeout_seconds`) and cap input duration at the app level.

## Temp and output directories

```python
import tempfile
from pathlib import Path
from karaoke_engine import KaraokeEngine

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    ass_out = tmp_path / "karaoke.ass"
    mp4_out = tmp_path / "karaoke_output.mp4"

    engine = KaraokeEngine()
    engine.render_video(
        video_path=uploaded_video,
        transcript_path=uploaded_json,
        output_path=mp4_out,
        ass_output_path=ass_out,
    )
    # Copy mp4_out / ass_out to durable storage
```

- Use per-job isolated directories
- Avoid world-readable temp dirs for sensitive lyrics
- Set retention policy (delete after N days)

## FFmpeg availability checks

Before accepting render jobs:

```python
import shutil

def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
```

Fail fast with a clear message if render is requested but tools are missing.

## Logging recommendations

Log structured metadata from results:

```python
result = engine.create_ass(...)
logger.info(
    "ass_created",
    extra={
        "ass_path": str(result.ass_path),
        "source_format": result.source_format,
        "line_count": result.line_count,
        "word_count": result.word_count,
    },
)
```

For render failures, capture `RenderError` message and FFmpeg stderr from `RenderVideoResult` when using lower-level APIs.

## Integrating without coupling

Keep boundaries clear:

| Layer | Responsibility |
|-------|----------------|
| Your API / worker | Auth, quotas, OpenAI calls, storage |
| `karaoke_engine` | Parse → validate → segment → ASS → optional FFmpeg |

Pass file paths or in-memory JSON through parsers (`parse_whisper_json`) if you do not need the high-level engine.

## Frappe / audio_stem (future integration)

Not included in this package. A Frappe app or `audio_stem` service would:

1. Transcribe audio via OpenAI in **app code**
2. Save `verbose_json` to disk or bench storage
3. Call `KaraokeEngine` as a pure subtitle/render step

No Frappe hooks or DocTypes exist in `karaoke_engine` today.

## Security notes

| Risk | Mitigation |
|------|------------|
| Path traversal | Validate and canonicalize paths; reject `..` in user input |
| Untrusted transcript text | Engine escapes ASS dialogue; still validate source |
| ASS injection | Validator blocks raw `{...}` override tags in word text |
| Server path leakage | Return object URLs, not internal filesystem paths |
| Large files | Enforce max upload size and duration in **your** app |
| OpenAI keys | Never in repo; env/secret manager only; not in engine package |
| FFmpeg command injection | Engine uses `subprocess` list args, `shell=False` |

## Quality guidance

| Input | Production recommendation |
|-------|---------------------------|
| `whisper_json` | Preferred for karaoke |
| `srt_approx` / `vtt_approx` | Fallback only; warn users about approximate timing |

Check `result.source_format` and surface quality warnings in your UI.

## Error handling in workers

```python
from karaoke_engine.errors import (
    AssGenerationError,
    RenderError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)

try:
    result = engine.render_video(...)
except UnsupportedTranscriptFormatError:
    # 400 bad input
    ...
except TranscriptValidationError:
    # 422 invalid transcript
    ...
except RenderError:
    # 502 / retryable infra
    ...
except AssGenerationError:
    # 500 disk/IO
    ...
```

## Scaling notes

- ASS generation is CPU-light and safe to run in-process
- FFmpeg burn-in is CPU-heavy; run render workers separately
- No GPU required by this library
- No PyTorch/CUDA/local Whisper
