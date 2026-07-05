---
name: encode-qc
description: >-
  Run full Instagram-compliance QC on a rendered output file — structural
  validation (codec/profile/level/color/VBV/aspect), EBU R128 loudness audit
  (-14 LUFS / -1.5 dBTP), and optional VMAF fidelity when a source is given.
  Invoke as: /encode-qc <output.mp4> [source.mp4]
disable-model-invocation: true
---

# /encode-qc — post-encode compliance check

Arguments: `$ARGUMENTS` = `<output-file> [source-file]`

The first argument is the encoded file to audit. If a second argument is given,
it is the original source and enables a VMAF fidelity score.

Run these against the output file and report a concise, scannable QC verdict
(most important first). Do **not** re-encode anything — this is read-only QC.

## Steps

1. **Structural + compliance validation**
   ```bash
   bash .claude/skills/instagram-reels-encoder/scripts/validate_encode.sh "<output>"
   ```
   If it fails on `python3` (common on Windows), fall back to `python` or read
   values directly with `ffprobe -of json`.

2. **Loudness audit (independent of the encoder's own loudnorm estimate)**
   ```bash
   ffmpeg -hide_banner -nostats -i "<output>" -af ebur128=peak=true -f null - 2>&1 | tail -20
   ```
   Parse `Summary:` → Integrated LUFS-I and True Peak dBTP.

3. **VMAF (only if a source arg was provided)**
   ```bash
   bash .claude/skills/instagram-reels-encoder/scripts/measure_vmaf.sh "<source>" "<output>" 5
   ```

## Report
- **Verdict:** `DELIVERY READY ✓` or `REVISAR ⚠` (one line).
- **Video:** codec/profile/level · resolution/aspect · color · VBV — each ✓/⚠/✗.
- **Audio:** LUFS-I · dBTP · codec/rate — each ✓/⚠/✗ vs −14 ±1 / ≤ −1.5 dBTP.
- **VMAF:** mean score (skip if no source). ≥93 transparent, flag <90.
- **Fixes:** for each ✗/⚠, the exact encoder flag to change; else "no action".
