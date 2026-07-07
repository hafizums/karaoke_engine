# Release Checklist — karaoke_engine v0.1.0

Use this checklist before creating the initial release tag. Do **not** publish to PyPI unless explicitly decided later.

## Pre-release

- [ ] Ensure a clean git working tree (`git status`)
- [ ] Confirm `pyproject.toml` version is `0.1.0`
- [ ] Confirm runtime dependencies remain empty (`dependencies = []`)
- [ ] Verify README and CHANGELOG are up to date
- [ ] Verify example files exist in `examples/`:
  - `whisper_sample.json`
  - `sample.srt`
  - `sample.vtt`
- [ ] Remove local build artifacts if present:
  - `__pycache__/`
  - `.pytest_cache/`
  - `*.egg-info/`
  - `dist/`
  - `build/`

## Automated checks

```bash
python -m pytest -q
python scripts/release_check.py
```

## Optional FFmpeg smoke test

If `ffmpeg` and `ffprobe` are installed on `PATH`, pytest will also run the optional end-to-end render smoke test. On machines without FFmpeg, that test is skipped automatically and does not fail the suite.

To confirm FFmpeg is available:

```bash
ffmpeg -version
ffprobe -version
```

## Manual review

- [ ] README documents supported inputs, production warnings, and examples
- [ ] CHANGELOG includes `0.1.0` notes for Gates 1–9
- [ ] Public exports in `karaoke_engine/__init__.py` match documented APIs
- [ ] No secrets, credentials, or large media files are tracked

## Tagging (manual)

Do **not** auto-tag from scripts. When ready:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Explicitly out of scope for this release

- PyPI publishing
- Audio transcription
- OpenAI API integration
- Local Whisper / PyTorch / CUDA
- Bundled FFmpeg
- Web UI or browser rendering

## Post-tag notes

- Treat `0.1.0` as the initial release candidate for internal or tagged distribution
- FFmpeg remains an optional external dependency for `render_video()`
- SRT/VTT inputs provide approximate word timing only
