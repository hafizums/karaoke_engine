# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

## Gate 1 scope

This package currently provides:

- Typed dataclasses for karaoke documents
- Custom exceptions
- ASS timecode helpers
- ASS text escaping
- Validation utilities

Parsing, ASS writing, segmentation, and media tooling are planned for later gates.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
```
