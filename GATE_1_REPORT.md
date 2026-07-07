# Gate 1 Report — Package Foundation

## Status

PASS

## Summary

Gate 1 establishes the `karaoke_engine` Python package foundation with typed frozen dataclasses for karaoke documents, a small exception hierarchy, ASS timecode conversion helpers, ASS text escaping, and validation utilities that enforce timing and text rules. A minimal pytest suite covers models, timecode helpers, and ASS escaping.

## Files Created

- `pyproject.toml`
- `README.md`
- `karaoke_engine/__init__.py`
- `karaoke_engine/models.py`
- `karaoke_engine/errors.py`
- `karaoke_engine/validators.py`
- `karaoke_engine/utils/__init__.py`
- `karaoke_engine/utils/timecode.py`
- `karaoke_engine/ass/__init__.py`
- `karaoke_engine/ass/escape.py`
- `tests/test_timecode.py`
- `tests/test_ass_escape.py`
- `tests/test_models.py`
- `GATE_1_REPORT.md`

## Files Modified

None (greenfield package).

## Dependencies Added

Runtime dependencies: none.

Development dependencies (optional `dev` extra):

- `pytest>=7.0`

Build dependencies:

- `setuptools>=61.0`

## Implemented Scope

Confirm each completed item:

* Typed dataclasses
* Custom exceptions
* Timecode helpers
* ASS escaping
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* Whisper parser
* ASS writer
* Segmenter
* FFmpeg
* SRT parser
* VTT parser
* Web UI
* Frappe integration

## Test Result

```
python -m pytest -q
............                                                             [100%]
12 passed in 0.04s
```

## Important Code Snippets

Paste the full contents of:

* `pyproject.toml`

```toml
[project]
name = "karaoke_engine"
version = "0.1.0"
description = "Lightweight server-friendly karaoke subtitle engine"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "karaoke_engine contributors" }]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["karaoke_engine*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

* `karaoke_engine/models.py`

```python
"""Typed dataclasses for karaoke documents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Word:
    """A single timed word in a karaoke line."""

    text: str
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class KaraokeLine:
    """A line of timed words."""

    words: tuple[Word, ...]
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class KaraokeDocument:
    """A full karaoke transcript document."""

    lines: tuple[KaraokeLine, ...]
    source_format: str = "unknown"


@dataclass(frozen=True, slots=True)
class ValidationWarning:
    """A non-fatal validation issue."""

    code: str
    message: str
    path: str = ""


@dataclass
class ValidationReport:
    """Aggregated validation results."""

    warnings: list[ValidationWarning] = field(default_factory=list)
    errors: list[ValidationWarning] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(ValidationWarning(code=code, message=message, path=path))

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(ValidationWarning(code=code, message=message, path=path))
```

* `karaoke_engine/errors.py`

```python
"""Custom exceptions for karaoke_engine."""


class KaraokeEngineError(Exception):
    """Base exception for all karaoke_engine errors."""


class UnsupportedTranscriptFormatError(KaraokeEngineError):
    """Raised when an input transcript format is not supported."""


class TranscriptValidationError(KaraokeEngineError):
    """Raised when transcript data fails validation."""


class AssGenerationError(KaraokeEngineError):
    """Raised when ASS subtitle generation fails."""
```

* `karaoke_engine/utils/timecode.py`

```python
"""ASS timecode conversion helpers."""

from __future__ import annotations


def seconds_to_centiseconds(seconds: float) -> int:
    """Convert seconds to whole centiseconds."""
    if seconds < 0:
        raise ValueError(f"Timestamp must not be negative: {seconds}")
    return int(round(seconds * 100))


def seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format ``H:MM:SS.cc``."""
    if seconds < 0:
        raise ValueError(f"Timestamp must not be negative: {seconds}")

    total_centiseconds = seconds_to_centiseconds(seconds)
    centiseconds = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
```

* `karaoke_engine/ass/escape.py`

```python
"""ASS text escaping helpers."""

from __future__ import annotations


def escape_ass_text(text: str) -> str:
    """Escape text for safe inclusion in ASS dialogue fields."""
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\\N")
        .replace("\n", "\\N")
        .replace("\r", "\\N")
    )
```

## Design Decisions

- **Immutable models**: `Word`, `KaraokeLine`, `KaraokeDocument`, and `ValidationWarning` use frozen dataclasses with slots for predictable, hashable, memory-efficient structures suitable for server pipelines.
- **Tuples for collections**: Nested `words` and `lines` are tuples rather than lists to reinforce immutability and deterministic iteration.
- **Validation separated from models**: Validation lives in `validators.py` so dataclasses stay lightweight and parsing/generation layers can choose between soft reports (`ValidationReport`) or hard failures (`ensure_valid_document` → `TranscriptValidationError`).
- **ASS override rejection at validation time**: Brace-delimited patterns (`{...}`) are rejected in transcript text before escaping, preventing raw override tags from entering the pipeline.
- **Deterministic timecode rounding**: Centiseconds are derived via `round(seconds * 100)` once, then decomposed into ASS `H:MM:SS.cc` components so formatting and centisecond conversion stay consistent.
- **Minimal dependencies**: Zero runtime dependencies; only `pytest` in the optional `dev` extra.
- **Exception stubs for future gates**: `UnsupportedTranscriptFormatError` and `AssGenerationError` are defined now so later parsers/writers share a consistent error surface.

## Risks / Questions

- **ASS override detection scope**: Validation rejects any `{...}` substring in word text. This is intentionally strict but may reject legitimate lyric punctuation if lyrics ever contain literal braces.
- **Whitespace-only text**: Empty-text validation treats whitespace-only strings as invalid (`not text.strip()`). Confirm this matches expected transcript semantics.
- **Line/word timing consistency**: Line-level `start`/`end` are validated independently from constituent word timings; cross-field consistency (e.g., line start equals first word start) is not enforced in Gate 1.
- **No `__init__.py` in `tests/`**: Pytest discovers tests without a package `tests` module; acceptable for now but may matter if shared fixtures are added later.

## Gate 1 Hygiene Fix

### Files removed

Removed from git tracking and working tree:

- `karaoke_engine.egg-info/` (entire directory)
  - `PKG-INFO`
  - `SOURCES.txt`
  - `dependency_links.txt`
  - `requires.txt`
  - `top_level.txt`
- `karaoke_engine/__pycache__/` (4 `.pyc` files)
- `karaoke_engine/ass/__pycache__/` (2 `.pyc` files)
- `karaoke_engine/utils/__pycache__/` (2 `.pyc` files)
- `tests/__pycache__/` (3 `.pyc` files)
- `.pytest_cache/` (untracked; deleted from working tree)

### `.gitignore` contents

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
*.egg-info/
dist/
build/

# Test / tooling caches
.pytest_cache/

# Virtual environments
.venv/
venv/
```

### Pytest result

```
python -m pytest -q
............                                                             [100%]
12 passed in 0.04s
```

## Gatekeeper Review Request

Please review Gate 1 and tell me whether it is APPROVED or BLOCKED.
