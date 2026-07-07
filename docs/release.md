# Release

Related: [Development](development.md) · [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md) · [CHANGELOG](../CHANGELOG.md)

## Current version

- Package version: **0.1.0**
- Intended git tag: **v0.1.0**

Do **not** publish to PyPI unless explicitly decided.

## Pre-release checklist

See [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md) for the full checklist. Summary:

- [ ] Clean git working tree
- [ ] `pyproject.toml` version is `0.1.0`
- [ ] Runtime `dependencies = []`
- [ ] README, CHANGELOG, and `docs/` up to date
- [ ] Example files present in `examples/`
- [ ] No build artifacts (`dist/`, `build/`, `*.egg-info/`)

## Automated checks

```bash
python -m pytest -q
python scripts/release_check.py
```

Both must pass before tagging.

## Optional FFmpeg smoke

If `ffmpeg` and `ffprobe` are installed, pytest runs optional real render smoke tests. Machines without FFmpeg skip them automatically.

Manual full API pipeline:

```bash
python scripts/real_openai_karaoke_video_smoke.py your_file.mp4
```

See [Real OpenAI smoke test](real-openai-smoke-test.md). Not required for release.

## Manual git tag

Scripts do **not** create tags automatically.

```bash
git tag v0.1.0
git push origin v0.1.0
```

## CHANGELOG

Update [CHANGELOG.md](../CHANGELOG.md) before each release with:

- Version and date
- Added / changed / fixed items
- Notes on dependencies and breaking changes

Current `0.1.0` is marked **Unreleased** until tagged.

## PyPI

**Not published** by default. Internal or git-tag distribution only unless you explicitly decide otherwise.

## Post-release

- Treat `0.1.0` as initial release candidate
- FFmpeg remains optional external dependency
- SRT/VTT remain approximate timing sources
- OpenAI integration stays outside the package

## Documentation for releases

Ensure these are current:

- [README.md](../README.md)
- [docs/index.md](index.md)
- [docs/release.md](this file)
