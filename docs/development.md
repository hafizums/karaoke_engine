# Development

Related: [Installation](installation.md) · [Release](release.md) · [Troubleshooting](troubleshooting.md)

## Repository structure

```
karaoke_engine/
├── karaoke_engine/          # Main package
│   ├── engine.py              # KaraokeEngine high-level API
│   ├── models.py              # KaraokeDocument, Word, etc.
│   ├── validators.py          # Document validation
│   ├── segmenter.py           # Line segmentation
│   ├── ass/                   # ASS writer, styles, escape
│   ├── parsers/               # whisper_json, srt, vtt
│   ├── render/                # ffmpeg, probe
│   └── utils/                 # timecode helpers
├── examples/                  # Sample transcript files
├── scripts/
│   ├── release_check.py
│   └── real_openai_karaoke_video_smoke.py  # manual only
├── tests/
├── docs/                      # This documentation
├── README.md
├── CHANGELOG.md
└── RELEASE_CHECKLIST.md
```

## Setup

```bash
python -m venv .venv
pip install -e ".[dev]"
```

## Test commands

```bash
python -m pytest -q
python scripts/release_check.py
```

### Test modules (high level)

| Module | Focus |
|--------|-------|
| `test_whisper_json.py` | Whisper parser |
| `test_engine.py` | KaraokeEngine.create_ass |
| `test_engine_render.py` | render_video (mocked FFmpeg) |
| `test_examples_workflow.py` | End-to-end example files |
| `test_packaging_readiness.py` | Metadata and release hygiene |
| `test_validation_hardening.py` | Validator rules |

FFmpeg subprocess calls are **mocked** in normal tests except optional skip-if-missing smoke tests.

## Examples workflow

Bundled examples in `examples/`:

- `whisper_sample.json`
- `sample.srt`
- `sample.vtt`

`tests/test_examples_workflow.py` exercises `create_ass()` for all three.

## Optional smoke tests

| Test | Requires |
|------|----------|
| pytest `test_optional_ffmpeg_*` | ffmpeg + ffprobe on PATH |
| `scripts/real_openai_karaoke_video_smoke.py` | OPENAI_API_KEY, openai pkg, network, FFmpeg |

Do not add OpenAI calls to pytest.

## How to add a parser

1. Create `karaoke_engine/parsers/your_format.py`
2. Return `KaraokeDocument` with a distinct `source_format`
3. Call `ensure_valid_document()` before return
4. Add `load_*` / `parse_*` functions
5. Export from `karaoke_engine/parsers/__init__.py` and `karaoke_engine/__init__.py`
6. Register extension in `engine._load_transcript()`
7. Add tests and docs in [Supported inputs](supported-inputs.md)

Keep parsers pure — no network, no ML.

## How to add a style preset

1. Add `@classmethod` on `KaraokeStyle` in `ass/styles.py`
2. Use valid ASS color strings and alignment 1–9
3. Add test in `test_style_hardening.py`
4. Document in [ASS karaoke](ass-karaoke.md)

## Contribution rules

| Rule | Reason |
|------|--------|
| No PyTorch / CUDA / local Whisper | Keep engine lightweight |
| No OpenAI calls inside package | Transcription is app responsibility |
| No browser / Playwright rendering | Server-side only |
| No bundled FFmpeg | External system dependency |
| No runtime deps unless essential | `dependencies = []` |
| Mock FFmpeg in tests | CI without binaries |
| Do not break public API lightly | Gate 8+ stability |

## Code style

- Python 3.10+ typing
- `dataclass(frozen=True, slots=True)` for value objects
- `pathlib.Path` for file paths
- `subprocess` with list args, `shell=False`

## Local manual checks before PR

```bash
python -m pytest -q
python scripts/release_check.py
```

See [Release](release.md) for tagging workflow.
