# Changelog

All notable changes to `karaoke_engine` are documented in this file.

## [0.1.0] - Unreleased

### Added

- Gate 1: package foundation with typed models, exceptions, ASS escaping, and timecode helpers.
- Gate 2: ASS karaoke writer with `KaraokeStyle` presets and `\kf` timing.
- Gate 3: Whisper `verbose_json` parser with word-level timestamps.
- Gate 4: configurable karaoke line segmenter.
- Gate 5: high-level `KaraokeEngine.create_ass()` API.
- Gate 6: optional FFmpeg/FFprobe video rendering via `KaraokeEngine.render_video()`.
- Gate 7: SRT and VTT fallback parsers with approximate word timing.
- Gate 8: production hardening, examples, README/CHANGELOG updates, and expanded validation.
- Gate 9: release checklist, packaging checks, example workflow tests, and release script.

### Notes

- Runtime dependencies remain empty; `pytest` is available via the `dev` extra.
- FFmpeg is an optional external system dependency for video rendering.
- SRT and VTT inputs use approximate per-word timing, not true karaoke timestamps.
