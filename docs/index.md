# karaoke_engine documentation

**Version:** `0.1.0`

`karaoke_engine` is a lightweight, server-friendly Python library that converts transcript files into ASS karaoke subtitles and optionally burns them into video with system FFmpeg.

The package is designed for backend services and batch jobs. It does **not** transcribe audio or call external APIs on its own.

## Common workflows

| Goal | Typical path |
|------|----------------|
| Whisper JSON → ASS | [Quickstart](quickstart.md) → [API reference](api-reference.md) |
| SRT/VTT fallback → ASS | [Supported inputs](supported-inputs.md) → [Quickstart](quickstart.md) |
| ASS → burned-in MP4 | [FFmpeg rendering](ffmpeg-rendering.md) |
| Full real API smoke test | [Real OpenAI smoke test](real-openai-smoke-test.md) |
| Deploy in production | [Production usage](production-usage.md) |
| Debug issues | [Troubleshooting](troubleshooting.md) |

## Documentation map

| Document | Description |
|----------|-------------|
| [Quickstart](quickstart.md) | Install, test, and first ASS/video outputs |
| [Installation](installation.md) | Python, dev install, FFmpeg, optional OpenAI SDK |
| [Supported inputs](supported-inputs.md) | Whisper JSON, SRT, VTT formats and `source_format` values |
| [API reference](api-reference.md) | Public classes, functions, and exceptions |
| [ASS karaoke](ass-karaoke.md) | `\kf` timing, styles, presets, escaping |
| [FFmpeg rendering](ffmpeg-rendering.md) | `render_video()`, options, probing, errors |
| [Real OpenAI smoke test](real-openai-smoke-test.md) | Manual end-to-end script (not pytest) |
| [Production usage](production-usage.md) | Server integration, security, job queues |
| [Troubleshooting](troubleshooting.md) | Common failures and fixes |
| [Development](development.md) | Repo layout, tests, contributing rules |
| [Release](release.md) | Checklist, tagging, changelog |

## What the engine does

- Parse OpenAI Whisper `verbose_json` with word timestamps
- Parse SRT and WebVTT with **approximate** per-word timing
- Segment long lines into readable karaoke lines
- Generate ASS subtitles with `\kf` fill timing
- Optionally render MP4 with FFmpeg subtitle burn-in

## What the engine does not do

- Transcribe audio inside the package
- Call OpenAI or any API inside the package
- Require PyTorch, CUDA, local Whisper, or local LLM
- Bundle FFmpeg or provide a web UI
- Include Frappe integration or browser rendering

See also the project [README](../README.md) and [CHANGELOG](../CHANGELOG.md).
