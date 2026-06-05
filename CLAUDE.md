# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Validate installation
python tools/verificador_instalacao.py

# Run all AI module tests
python -m pytest enhance/ -v

# Run a single test file
python -m pytest enhance/test_mock_cnn.py -v
python -m pytest enhance/test_processors.py -v

# Basic encode (FFmpeg pipeline)
python Reels_Encoder_v2_FINAL.py input.mp4

# Cineon film emulation encode
python Reels_Encoder_v2_FINAL.py input.mp4 --cineon-pipeline on

# Encode with AI enhancement
python Reels_Encoder_v2_FINAL.py input.mp4 --enhance on --enhance-ai on

# Batch encode a folder
python Reels_Encoder_v2_FINAL.py --batch ./clips/ --output-dir ./reels/

# Diagnostic heatmaps
python enhance_visualizer.py input.mp4
```

## Architecture

### Two encode pipelines

**Pipeline 1 — FFmpeg Native** (default): FFmpeg subprocess with filter graph. Fast (~30–60 fps). Uses `HollywoodCinema_Ultimate_v6.7B_*.cube` LUT and optional AI-driven filter graph built in `enhance/ffmpeg_filters.py`.

**Pipeline 2 — Cineon** (`--cineon-pipeline on`): Frame-by-frame processing via PyAV decode → NumPy processing → FFmpeg pipe → libx264. Slower (~5–15 fps CPU) but film-grade. Implemented in `cineon_pipeline.py`. Pipeline order per frame: **Resize → Linear → Tonemap → BT709 → CAS → YUV420P**.

### AI Enhancement module (`enhance/`)

Analyzes 5 sampled frames (at 10/25/50/75/90% of duration), extracts 13 features, runs them through `MockCNN` (13→8→3 sigmoid network), and produces weights for three adaptive filters. The module is designed so `MockCNN` can later be swapped for a real ONNX/PyTorch model by implementing `EnhanceModel` from `enhance/ai/interface.py`.

Key files:
- `enhance/analyzers/` — `noise.py`, `banding.py`, `detail.py` produce the 13-feature vector
- `enhance/ai/mock_cnn.py` — hand-calibrated weights approximating heuristic decision matrix
- `enhance/processor.py` — per-frame chain: `denoise → deband_smooth → sharpen`; returns `None` if no enhancement needed (zero overhead)
- `enhance/ffmpeg_filters.py` — converts `EnhanceProfile` weights into FFmpeg filter graph strings (used by Pipeline 1)
- `enhance/sampler.py` — PyAV-based frame extraction at strategic positions

### iPhone / rotation handling

Rotation is delegated entirely to FFmpeg's auto-rotate. PyAV handles scale. Never use `transpose` + `noautorotate` together — see memory for context.

### HDR pipeline order

When processing HDR input (`--hdr auto`), FFmpeg tone-mapping is applied. The correct order is Resize → Linear → Tonemap → BT709 → CAS → YUV420P. Tonemap params: `desat=2`, `npl=200`.

### Audio

Loudness normalization uses EBU R128 two-pass (`--loudnorm on`, default): target -14 LUFS, true-peak -1 dBTP. Implemented via FFmpeg `loudnorm` filter with analysis pass.

### LUTs

Two `.cube` files in root:
- `FilmLook_Portra400_SkinPriority_D65.cube` — used in Cineon pipeline (Node 5, trilinear 3D interpolation)
- `HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube` — used in FFmpeg pipeline (`--lut on`)

### Entry point

`Reels_Encoder_v2_FINAL.py` (~4000 lines) owns all CLI argument parsing, hardware detection, VBV bitrate selection, and dispatches to either the FFmpeg subprocess path or the Cineon pipeline in `cineon_pipeline.py`.
