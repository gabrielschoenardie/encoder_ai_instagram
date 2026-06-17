# EBU Meter — Post-encode QC mode

**Date:** 2026-06-17
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

After every encode completes, automatically **audit** the final file's audio
against the EBU R128 standard and, optionally, open a **graphical EBU R128
meter** (FFplay) for visual QC and a before/after (original vs final)
comparison.

Inspired by [`ebu-meter.rs`](https://github.com/NapoleonWils0n/ffmpeg-rust-scripts/blob/master/src/bin/ebu-meter.rs),
whose entire mechanism is a single FFplay `lavfi` graph:

```
ffplay -hide_banner -v error -window_title "<title>" -f lavfi \
  -i "amovie='<escaped_path>',ebur128=video=1:meter=18:dualmono=true:target=<I>[out0][out1]"
```

`ebur128=video=1` renders the broadcast-style meter (gauge + scrolling
loudness history + true-peak); `meter=18` sets the +18 LU scale; `dualmono=true`
matches the encoder's mono handling; `target` draws the target line. Path
escaping: `\` → `\\`, `:` → `\:`. No `showwaves`/`showspectrum` — `ebur128`'s
own video output is the display.

## Non-goals / constraints

- The **loudnorm 2-pass** path remains the sole, official normalization method.
  This feature only *measures* and *visualizes*; it never alters audio.
- The **automatic measurement always runs** after an encode (single and batch).
- The **FFplay visualization is opt-out** (`--ebu-meter`, default `on`), and is
  **force-disabled in batch mode** to avoid spawning N windows.
- QC must **never** block the encode result nor fail the run: missing audio,
  unparseable summary, or absent `ffplay` degrade gracefully with a warning.

## Architecture

New module **`ebu_meter.py`** at repo root (next to `cineon_pipeline.py`),
keeping the ~4000-line entry point lean. It mirrors the loudnorm pattern in
`Reels_Encoder_v2_FINAL.py`: **pure builders/parsers** (unit-testable, no
subprocess) plus thin impure runners.

| Function | Purity | Role |
|---|---|---|
| `build_ebur128_measure_cmd(file)` | pure | `ffmpeg -hide_banner -nostats -i <f> -af ebur128=peak=true -f null -` |
| `parse_ebur128_summary(stderr)` | pure | regex over the `Summary:` block → `{"I", "TP", "LRA"}` (floats) or `None` |
| `build_ffplay_meter_args(file, target_i, title)` | pure | the reference's FFplay `lavfi` arg list, incl. path escaping |
| `probe_audio_codec(file)` | impure | ffprobe → `(codec_name, sample_rate)` |
| `measure_loudness(file)` | impure | run measure cmd, parse summary → `dict` or `None` |
| `launch_meter_window(file, target_i, title)` | impure | `subprocess.Popen` (detached/non-blocking), guarded by `shutil.which("ffplay")` |
| `run_post_encode_qc(original, output, target, show_meter, console)` | impure | orchestrate: measure both files, print Rich comparison table, conditionally open the two windows |

### Measurement engine — `ebur128` (canonical EBU R128)

`ebur128=peak=true` prints a `Summary:` to stderr at EOF:

```
[Parsed_ebur128_0 @ ...] Summary:

  Integrated loudness:
    I:         -14.0 LUFS
    Threshold: -24.7 LUFS

  Loudness range:
    LRA:         7.5 LU
    ...

  True peak:
    Peak:       -1.5 dBFS
```

Parse `I:` (LUFS), `LRA:` (LU), and the `True peak` → `Peak:` (dBFS ≈ dBTP).
Codec + sample rate from ffprobe (`stream=codec_name,sample_rate`). This audit
is independent of loudnorm's internal estimate.

### Comparison report (always runs)

A Rich table, **ANTES (original) vs DEPOIS (final)**, with target column and
pass/warn flags:

- Integrated: `✓` if within target ±1.0 LU, else `⚠`
- True Peak: `✓` if ≤ target TP (−1.5 dBTP), else `⚠`
- LRA / Codec / Sample Rate: informational
- Any column that could not be measured shows `—`.

Target values are read from `LOUDNORM_TARGETS[target]` in the encoder
(I = −14, TP = −1.5, LRA = 11 for `instagram`).

### FFplay windows — two, detached, opt-out

Two `Popen` windows using the exact reference filtergraph:

- `"EBU R128 — ANTES (original): <name>"`
- `"EBU R128 — DEPOIS (final): <name>"`

Non-blocking (terminal returns immediately). If `ffplay` is not on PATH, print a
single warning and skip the windows — measurement output is still shown.

## CLI + wiring

- New flag `--ebu-meter {on,off}` (default `on`). Controls **only** the FFplay
  windows; measurement is unconditional.
- Hook at the end of `_encode_single_file()` (after
  `analyze_with_mediainfo(output_file)`):
  `run_post_encode_qc(input_file, output_file, target="instagram", show_meter=…)`.
- `_encode_single_file` gains `is_batch: bool = False`. The batch loop passes
  `is_batch=True`, which forces `show_meter=False`. Single-file path uses
  `args.ebu_meter == "on"`.

## Testing

`enhance/test_ebu_meter.py` — pure functions only (no subprocess), matching the
`test_loudnorm.py` style:

- `build_ebur128_measure_cmd` shape and flags.
- `parse_ebur128_summary` against a real summary fixture; malformed / silent
  (`-inf`, missing fields) → `None`; partial sections handled.
- `build_ffplay_meter_args`: filtergraph content (`ebur128=video=1:meter=18`),
  `target` injection, and path escaping (`\` → `\\`, `:` → `\:`).

## Failure modes (all graceful, non-fatal)

| Condition | Behavior |
|---|---|
| No audio stream | column shows `—`; QC continues |
| ffmpeg/ffprobe missing or errors | warning; skip that measurement |
| Summary unparseable / silent (`-inf`) | `measure_loudness` → `None`; `—` |
| `ffplay` not on PATH | warning; skip windows; table still printed |
| Batch mode | windows suppressed; measurement per file still runs |
