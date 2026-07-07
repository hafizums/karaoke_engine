"""Packaging and release-readiness metadata checks."""

from __future__ import annotations

import importlib
import re
import subprocess
from pathlib import Path

import pytest

import karaoke_engine

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
README_PATH = REPO_ROOT / "README.md"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
RELEASE_SCRIPT_PATH = REPO_ROOT / "scripts" / "release_check.py"
RELEASE_CHECKLIST_PATH = REPO_ROOT / "RELEASE_CHECKLIST.md"
EXAMPLES_DIR = REPO_ROOT / "examples"

EXPECTED_EXAMPLES = (
    "whisper_sample.json",
    "sample.srt",
    "sample.vtt",
)

ARTIFACT_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
)

PUBLIC_EXPORTS = (
    "KaraokeEngine",
    "CreateAssResult",
    "RenderOptions",
    "AssWriter",
    "KaraokeStyle",
    "segment_document",
    "load_whisper_json",
    "load_srt",
    "load_vtt",
    "render_ass_to_video",
    "probe_video",
)


def test_package_imports_cleanly() -> None:
    importlib.reload(karaoke_engine)


def test_root_public_exports_work() -> None:
    for name in PUBLIC_EXPORTS:
        assert hasattr(karaoke_engine, name), f"missing export: {name}"
        assert name in karaoke_engine.__all__


def test_package_version_is_0_1_0() -> None:
    assert karaoke_engine.__version__ == "0.1.0"
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in content


def test_runtime_dependencies_remain_empty() -> None:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    assert "dependencies = []" in content
    assert "torch" not in content.lower()
    assert "openai" not in content.lower()


def test_dev_extra_contains_pytest() -> None:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    assert re.search(r'dev\s*=\s*\["pytest', content)


def test_readme_exists() -> None:
    assert README_PATH.is_file()


def test_changelog_exists() -> None:
    assert CHANGELOG_PATH.is_file()


def test_example_files_exist() -> None:
    for filename in EXPECTED_EXAMPLES:
        path = EXAMPLES_DIR / filename
        assert path.is_file(), f"missing example file: {filename}"


def test_release_script_exists() -> None:
    assert RELEASE_SCRIPT_PATH.is_file()


def test_release_checklist_exists() -> None:
    assert RELEASE_CHECKLIST_PATH.is_file()


def test_no_generated_artifacts_tracked() -> None:
    git_dir = REPO_ROOT / ".git"
    if not git_dir.is_dir():
        pytest.skip("not a git repository")

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for entry in tracked:
        parts = Path(entry).parts
        if any(part in ARTIFACT_PATTERNS for part in parts):
            raise AssertionError(f"tracked artifact path: {entry}")
        if entry.endswith(".egg-info") or ".egg-info" in parts:
            raise AssertionError(f"tracked egg-info path: {entry}")


def test_no_packaging_artifacts_present_at_repo_root() -> None:
    for dirname in ("dist", "build"):
        path = REPO_ROOT / dirname
        if path.exists():
            raise AssertionError(f"generated artifact present: {path}")

    for egg_info in REPO_ROOT.glob("*.egg-info"):
        raise AssertionError(f"generated artifact present: {egg_info}")


def test_gitignore_excludes_generated_artifacts() -> None:
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.is_file()
    content = gitignore_path.read_text(encoding="utf-8")
    for pattern in ("__pycache__/", ".pytest_cache/", "*.egg-info/", "dist/", "build/"):
        assert pattern in content
