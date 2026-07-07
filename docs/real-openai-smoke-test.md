# Real OpenAI smoke test

Related: [Quickstart](quickstart.md) · [Supported inputs](supported-inputs.md) · [FFmpeg rendering](ffmpeg-rendering.md) · [Troubleshooting](troubleshooting.md)

## Purpose

`scripts/real_openai_karaoke_video_smoke.py` is a **manual** script that proves the full pipeline:

```
audio/video → OpenAI whisper-1 → verbose_json → karaoke_engine → .ass → FFmpeg → .mp4
```

## Important limitations

| Topic | Detail |
|-------|--------|
| pytest | **Not** part of normal test suite |
| API cost | Uses **real OpenAI API credits** |
| Network | Required |
| `OPENAI_API_KEY` | Required in environment; never printed or stored |
| `openai` package | Install manually: `pip install openai` |
| FFmpeg / FFprobe | Required when video render runs |
| Core package | `karaoke_engine` does **not** call OpenAI |

## Prerequisites

```bash
pip install -e ".[dev]"
pip install openai
ffmpeg -version
ffprobe -version
```

## Set API key

**Windows CMD:**

```cmd
set OPENAI_API_KEY=sk-your-key-here
python -c "import os; print('ok' if os.environ.get('OPENAI_API_KEY') else 'missing')"
```

**Windows PowerShell:**

```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
python -c "import os; print('ok' if os.environ.get('OPENAI_API_KEY') else 'missing')"
```

**Linux/macOS:**

```bash
export OPENAI_API_KEY=sk-your-key-here
```

The verify command must print `ok` in the **same terminal** before running the script.

## Commands

### Video input (MP4 uses input as render source)

```cmd
python scripts/real_openai_karaoke_video_smoke.py samples/test_song.mp4
```

### Audio-only with generated black test video

```cmd
python scripts/real_openai_karaoke_video_smoke.py samples/test_song.mp3 --make-test-video
```

### Audio with explicit background video

```cmd
python scripts/real_openai_karaoke_video_smoke.py samples/test_song.mp3 --video samples/background.mp4
```

### Optional output directory

```cmd
python scripts/real_openai_karaoke_video_smoke.py demo.mp3 --make-test-video --output-dir my_output
```

## Script steps

1. Transcribe with `whisper-1`, `verbose_json`, `timestamp_granularities=["word"]`
2. Save `openai_whisper_transcript.json`
3. Validate word timestamps exist
4. `KaraokeEngine.create_ass()` → `karaoke.ass` with `SegmentOptions(max_words_per_line=5)`
5. `KaraokeEngine.render_video()` → `karaoke_output.mp4` with `RenderOptions(crf=23, preset="veryfast")` (when video render applies)

Audio-only without `--video` or `--make-test-video` stops after ASS creation (not a failure).

## Expected outputs

Default directory: `real_api_smoke_output/`

| File | Description |
|------|-------------|
| `openai_whisper_transcript.json` | Raw API verbose_json |
| `karaoke.ass` | Generated karaoke subtitles |
| `karaoke_output.mp4` | Final video (when render runs) |
| `test_video.mp4` | Black video from audio (only with `--make-test-video`) |

## Safety notes

- **Never commit** API keys to git
- **Never print** keys in logs or scripts
- **Do not run** in CI by default
- **Do not add** OpenAI calls inside `karaoke_engine` package code
- Rotate keys if exposed

## OpenAI API quirks

Real Whisper responses may include words with `start == end`. The Whisper JSON parser normalizes these to a minimum 0.01 s duration before ASS generation.

## Exit codes

- `0` — all requested steps passed
- non-zero — failure with `FAIL [step]:` message on stderr
