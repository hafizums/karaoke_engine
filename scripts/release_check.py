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
