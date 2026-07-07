# Troubleshooting

Related: [Supported inputs](supported-inputs.md) · [FFmpeg rendering](ffmpeg-rendering.md) · [Real OpenAI smoke test](real-openai-smoke-test.md)

## Missing word timestamps

**Symptom:** `Unsupported Whisper JSON shape` or validation errors.

**Cause:** JSON lacks `words` or `segments[].words` with `start`/`end`.

**Fix:**

- Use OpenAI `verbose_json` with `timestamp_granularities=["word"]`
- Do not use plain `json` or `text` response formats
- See [Supported inputs](supported-inputs.md)

## SRT/VTT timing feels wrong

**Symptom:** Karaoke highlight does not match speech.

**Cause:** SRT/VTT only has cue-level timing; engine splits duration evenly across words (`srt_approx` / `vtt_approx`).

**Fix:** Use Whisper JSON with real word timestamps for production karaoke.

## FFmpeg not found

**Symptom:** `Failed to execute FFmpeg` or `RenderError` mentioning FFmpeg.

**Fix:**

```bash
ffmpeg -version
```

Install FFmpeg and ensure it is on `PATH`. Restart terminal after install.

## FFprobe not found

**Symptom:** Render fails during auto resolution probe.

**Fix:**

```bash
ffprobe -version
```

Usually installed with FFmpeg. Set `auto_probe_resolution=False` and pass explicit `play_res_x` / `play_res_y` as workaround.

## Output video has no subtitles

**Checks:**

1. Does `karaoke.ass` contain `Dialogue:` lines and `\kf` tags?
2. Are subtitle times within video duration?
3. Play rendered file in VLC/mpv — some players hide soft subs
4. Burn-in uses `ass` filter — subtitles are embedded, not a separate track

**Fix:** Verify ASS separately with `create_ass()` before blaming FFmpeg.

## Audio codec copy fails

**Symptom:** FFmpeg exit non-zero; error mentions audio stream.

**Cause:** `RenderOptions(audio_codec="copy")` cannot copy into target container.

**Fix:**

```python
RenderOptions(audio_codec="aac", crf=23, preset="veryfast")
```

## Font looks different

**Symptom:** ASS uses `Arial` but player shows another font.

**Cause:** Font resolution is OS/player dependent. ASS specifies `font_name` only.

**Fix:** Install target font on render machine or customize `KaraokeStyle.font_name`. Test on deployment OS.

## Subtitle off-screen

**Symptom:** Text clipped or too low/high.

**Cause:** PlayRes mismatch with video dimensions.

**Fix:**

- Match `play_res_x/y` to video size
- Use `KaraokeStyle.mobile_1080x1920()` for portrait
- Adjust `margin_v`, `alignment`

## Windows path escaping problems

**Symptom:** FFmpeg `ass` filter cannot parse path; errors mention `original_size`.

**Cause:** Drive letter or special characters in ASS path on Windows.

**Fix:** Use latest engine (quoted escaped paths). Avoid spaces in temp paths if issues persist.

## OpenAI API key missing (smoke script)

**Symptom:** `FAIL [env]: OPENAI_API_KEY is not visible`

**Cause:** Wrong shell syntax or different terminal.

**Fix:**

- PowerShell: `$env:OPENAI_API_KEY = "sk-..."`
- CMD: `set OPENAI_API_KEY=sk-...`
- Verify: `python -c "import os; print('ok' if os.environ.get('OPENAI_API_KEY') else 'missing')"`

See [Real OpenAI smoke test](real-openai-smoke-test.md).

## File too large for transcription API

**Symptom:** OpenAI API error on large media in smoke script.

**Cause:** OpenAI Whisper API file size limits (check current OpenAI docs).

**Fix:** Trim audio, compress, or split files in **your app** before calling API. Not handled inside `karaoke_engine`.

## ASS exists but video render fails

**Workflow:**

1. Confirm ASS opens and shows events
2. Run FFmpeg manually with `build_ffmpeg_ass_burn_command()` output
3. Check `RenderError` message for codec/path issues
4. Confirm output path is not an existing directory

## Zero-duration words from OpenAI

**Symptom:** `Word end time must be greater than start time` when `start == end`.

**Cause:** OpenAI Whisper API sometimes returns equal start/end timestamps.

**Fix (current parser behavior):** The Whisper JSON parser sets
`end = start + 0.01` seconds when `end <= start`. Ensure you are on a build
that includes this normalization. See
[Supported inputs](supported-inputs.md#zero-duration-word-normalization-current-parser-behavior).

## Validation: overlapping words

**Symptom:** Warnings in `ValidationReport` but ASS still generates.

**Cause:** Overlaps beyond 1 ms tolerance are warnings, not hard errors.

**Fix:** Acceptable for some API output; inspect transcript quality if sync looks wrong.

## Tests skip FFmpeg smoke

**Symptom:** pytest passes but FFmpeg tests show `skipped`.

**Cause:** `ffmpeg`/`ffprobe` not on PATH — intentional.

**Fix:** Install FFmpeg to run optional real smoke tests locally.
