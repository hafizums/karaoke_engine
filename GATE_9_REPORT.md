# Gate 9 Report — Release Tag + Real Workflow Smoke Test

## Status

PASS

## Summary

Gate 9 prepares `karaoke_engine` for a clean initial `0.1.0` release. Packaging readiness tests verify imports, metadata, docs, examples, and artifact hygiene. End-to-end example workflow tests exercise `KaraokeEngine.create_ass()` for Whisper JSON, SRT, and VTT samples, plus an optional real FFmpeg render smoke test that skips when binaries are unavailable. A `scripts/release_check.py` script provides a lightweight pre-tag checklist runner, and README/RELEASE_CHECKLIST documentation was polished for release workflow.

## Files Created

- `tests/test_examples_workflow.py`
- `tests/test_packaging_readiness.py`
- `scripts/release_check.py`
- `RELEASE_CHECKLIST.md`
- `GATE_9_REPORT.md`

## Files Modified

- `README.md`
- `CHANGELOG.md`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* Packaging readiness checks
* Example workflow tests
* Whisper JSON example workflow
* SRT example workflow
* VTT example workflow
* Optional FFmpeg smoke test with skip
* Release check script
* RELEASE_CHECKLIST
* README polish
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* PyPI publishing
* Automatic git tagging
* OpenAI API calls
* Audio transcription
* Local Whisper
* Local LLM
* PyTorch
* CUDA
* Web UI
* Frappe integration
* Browser rendering
* Bundled FFmpeg

## Test Result

Paste the exact command and output:

```
python -m pytest -q
........................................................................ [ 39%]
........................................................................ [ 78%]
........................................                                 [100%]
184 passed in 0.62s
```

## Release Check Result

Paste the exact command and output:

```
python scripts/release_check.py
karaoke_engine release check
repo: C:\Users\froxt\Downloads\karaoke_engine

PASS: package imports cleanly
INFO: package version 0.1.0
PASS: example files exist
PASS: README exists
PASS: CHANGELOG exists
PASS: runtime dependencies remain empty
PASS: example create_ass workflow succeeded

OVERALL: PASS
```

## Important Code Snippets

Paste the full contents of:

* `scripts/release_check.py`

```python
#!/usr/bin/env python3
"""Local release readiness checks before tagging v0.1.0."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
README_PATH = REPO_ROOT / "README.md"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
EXAMPLES_DIR = REPO_ROOT / "examples"
EXPECTED_EXAMPLES = (
    "whisper_sample.json",
    "sample.srt",
    "sample.vtt",
)


def _pass(message: str) -> None:
    print(f"PASS: {message}")


def _fail(message: str) -> None:
    print(f"FAIL: {message}")


def check_import_package() -> bool:
    try:
        import karaoke_engine

        _pass("package imports cleanly")
        print(f"INFO: package version {karaoke_engine.__version__}")
        return True
    except Exception as exc:
        _fail(f"package import failed: {exc}")
        return False


def check_examples_exist() -> bool:
    missing = [
        filename
        for filename in EXPECTED_EXAMPLES
        if not (EXAMPLES_DIR / filename).is_file()
    ]
    if missing:
        _fail(f"missing example files: {', '.join(missing)}")
        return False
    _pass("example files exist")
    return True


def check_docs_exist() -> bool:
    ok = True
    if README_PATH.is_file():
        _pass("README exists")
    else:
        _fail("README missing")
        ok = False
    if CHANGELOG_PATH.is_file():
        _pass("CHANGELOG exists")
    else:
        _fail("CHANGELOG missing")
        ok = False
    return ok


def check_no_runtime_dependencies() -> bool:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    if "dependencies = []" not in content:
        _fail("runtime dependencies are not empty in pyproject.toml")
        return False
    _pass("runtime dependencies remain empty")
    return True


def check_example_create_ass_workflow() -> bool:
    try:
        from karaoke_engine import KaraokeEngine
    except Exception as exc:
        _fail(f"cannot import KaraokeEngine for workflow check: {exc}")
        return False

    engine = KaraokeEngine()
    with tempfile.TemporaryDirectory() as temp_dir:
        output_ass = Path(temp_dir) / "whisper_sample.ass"
        try:
            result = engine.create_ass(
                transcript_path=EXAMPLES_DIR / "whisper_sample.json",
                output_path=output_ass,
            )
        except Exception as exc:
            _fail(f"example create_ass workflow failed: {exc}")
            return False

        if not output_ass.is_file():
            _fail("example create_ass workflow did not create ASS output")
            return False
        content = output_ass.read_text(encoding="utf-8")
        required_sections = ("[Script Info]", "[V4+ Styles]", "[Events]")
        for section in required_sections:
            if section not in content:
                _fail(f"example ASS output missing section: {section}")
                return False
        if result.source_format != "whisper_json":
            _fail(
                "example create_ass workflow returned unexpected source_format: "
                f"{result.source_format!r}"
            )
            return False

    _pass("example create_ass workflow succeeded")
    return True


def main() -> int:
    print("karaoke_engine release check")
    print(f"repo: {REPO_ROOT}")
    print()

    checks = [
        check_import_package,
        check_examples_exist,
        check_docs_exist,
        check_no_runtime_dependencies,
        check_example_create_ass_workflow,
    ]

    results = [check() for check in checks]
    print()
    if all(results):
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

* `RELEASE_CHECKLIST.md`

```markdown
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
```

* any new test files

`tests/test_examples_workflow.py` and `tests/test_packaging_readiness.py` — see repository for full contents.

* updated README release/check section

```markdown
## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
python scripts/release_check.py
```

See `RELEASE_CHECKLIST.md` for the full pre-tag release workflow.

## Examples

Sample files live in `examples/` for docs and tests:

- `whisper_sample.json` — Whisper JSON with real word timestamps
- `sample.srt` — SRT fallback with approximate word timing
- `sample.vtt` — WebVTT fallback with approximate word timing

## Release checks

Before tagging `v0.1.0`, run:

```bash
python -m pytest -q
python scripts/release_check.py
```

Optional: if system `ffmpeg` and `ffprobe` are installed, pytest also exercises a tiny real render smoke test. Machines without FFmpeg skip that test automatically.

Do not publish to PyPI unless explicitly decided. Tag manually when ready:

```bash
git tag v0.1.0
git push origin v0.1.0
```

See `RELEASE_CHECKLIST.md` for the complete checklist.
```

## Example Workflow Outputs

Summarize:

* JSON example result

`KaraokeEngine.create_ass()` on `examples/whisper_sample.json` creates a valid `.ass` file with `[Script Info]`, `[V4+ Styles]`, `[Events]`, and `\kf` tags. `source_format` is `whisper_json`.

* SRT example result

`create_ass()` on `examples/sample.srt` creates `.ass` output with `source_format` `srt_approx`.

* VTT example result

`create_ass()` on `examples/sample.vtt` creates `.ass` output with `source_format` `vtt_approx`.

* FFmpeg smoke test result or skip reason

On this machine FFmpeg and FFprobe are available; `test_optional_ffmpeg_render_workflow` passed by generating a 1-second color video, rendering with `examples/whisper_sample.json`, and verifying both output MP4 and sidecar ASS exist. On machines without FFmpeg, the test is skipped via `shutil.which`.

## Design Decisions

- **Separate Gate 9 test modules**: `test_examples_workflow.py` covers end-to-end engine flows; `test_packaging_readiness.py` covers metadata and release hygiene without duplicating Gate 8 hardening tests.
- **Artifact checks split**: Git-tracked artifact detection plus root-level `dist`/`build`/`egg-info` checks avoid false failures from local `__pycache__` created during pytest runs.
- **Release script stays lightweight**: `release_check.py` validates import, docs, empty runtime deps, and one Whisper JSON workflow without invoking pytest or modifying git.
- **FFmpeg smoke via `KaraokeEngine.render_video()`**: Uses the high-level API with `auto_probe_resolution=False` for deterministic tiny-video rendering.
- **No PyPI or auto-tagging**: Release tooling only validates readiness; tagging remains manual per constraints.

## Risks / Questions

- **Duplicate FFmpeg smoke coverage**: Gate 8 `test_release_readiness.py` still includes a lower-level FFmpeg smoke test; both pass when FFmpeg is installed but add slight redundancy.
- **Artifact presence vs tracked state**: Local `__pycache__` may exist during development; only tracked artifacts and root packaging dirs are enforced strictly.
- **Release script scope**: `release_check.py` does not run SRT/VTT workflows or full pytest; those remain in the test suite.
- **CHANGELOG still unreleased**: Version `0.1.0` is marked unreleased until a manual tag is created.

## Gatekeeper Review Request

Please review Gate 9 and tell me whether it is APPROVED or BLOCKED.
