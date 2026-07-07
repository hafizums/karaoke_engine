# Installation

Related: [Quickstart](quickstart.md) · [FFmpeg rendering](ffmpeg-rendering.md) · [Development](development.md)

## Requirements

| Requirement | Required? | Notes |
|-------------|-----------|-------|
| Python 3.10+ | Yes | See `requires-python` in `pyproject.toml` |
| Runtime pip dependencies | No | `dependencies = []` |
| pytest | Dev only | Via `pip install -e ".[dev]"` |
| FFmpeg / FFprobe | Optional | Needed for `render_video()` and probing |
| OpenAI Python SDK | Optional | Manual smoke script only; not part of core engine |

## Editable install (development)

```bash
pip install -e ".[dev]"
```

This installs `karaoke_engine` in editable mode and adds `pytest` for running tests.

## Production install (local / internal)

If you vendor or copy the package into your deployment:

```bash
pip install .
```

No runtime dependencies are pulled in automatically.

## Verify installation

```bash
python -c "import karaoke_engine; print(karaoke_engine.__version__)"
python -m pytest -q
```

## Optional: FFmpeg and FFprobe

`karaoke_engine` does **not** bundle FFmpeg. Install it separately for your OS:

- **Windows:** [ffmpeg.org](https://ffmpeg.org/download.html) or `winget install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `apt install ffmpeg` / `dnf install ffmpeg` (package name may vary)

Verify:

```bash
ffmpeg -version
ffprobe -version
```

Both must be on `PATH` for `KaraokeEngine.render_video()` and `probe_video()`.

## Optional: OpenAI SDK (manual smoke script only)

The core `karaoke_engine` package does **not** call OpenAI. The manual script `scripts/real_openai_karaoke_video_smoke.py` requires the SDK separately:

```bash
pip install openai
```

Set `OPENAI_API_KEY` in your shell before running that script. See [Real OpenAI smoke test](real-openai-smoke-test.md).

## What is not required

- PyTorch
- CUDA
- Local Whisper
- Local LLM
- Playwright or browser tooling
- Frappe
