# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Validate installation
python tools/verificador_instalacao.py

# Run all module tests (AI + interactive UI)
python -m pytest enhance/ ui/ -v

# Run a single test file
python -m pytest enhance/test_mock_cnn.py -v
python -m pytest ui/test_config.py -v

# Interactive Premiere-style UI (launcher wizard)
python Reels_Encoder_v2_FINAL.py            # no args → opens the launcher
python Reels_Encoder_v2_FINAL.py --ui       # force the launcher

# Basic encode (FFmpeg pipeline)
python Reels_Encoder_v2_FINAL.py input.mp4

# Fill the 9:16 frame (crop edges instead of letterboxing)
python Reels_Encoder_v2_FINAL.py input.mp4 --fit cover

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

**Pipeline 1 — FFmpeg Native** (default): FFmpeg subprocess with filter graph. Fast (~30–60 fps). Uses `HollywoodCinema_Ultimate_v6.7B_*.cube` LUT and optional AI-driven filter graph built in `enhance/ffmpeg_filters.py`. `build_video_filter_auto()` dispatches per source: HDR → tonemap (no LUT); SDR → always the 32-bit float pipeline (`build_sdr_float_pipeline`, IDT→LUT→ODT with dither). The legacy 8-bit SDR transport and its `--float` flag were removed — SDR is float-only.

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

### Framing / aspect (`--fit`)

`build_scale_filter()` (in `Reels_Encoder_v2_FINAL.py`) takes a `fit` mode:
- `contain` (default): aspect-fit via `min()` scale factor. The whole frame stays visible; output may end up smaller than the target (e.g. a 3:4 portrait → 1080×1440, no upscaling to fill).
- `cover`: aspect-fill via `max()` scale factor, with a centered `crop=W:H` embedded in the returned filter. Always yields exactly the target (e.g. 1080×1920) with no black bars, cropping the overflow. Because cover emits exact-target dims, the transports' trailing `crop=W:H:0:0` becomes a no-op and the Cineon pipe's `target_resolution` stays consistent — no transport code needed changing.

`fit` is threaded through `_resolve_output_size` → `run_ffmpeg` / `run_ffmpeg_with_cineon`. Test coverage in `enhance/test_scale_filter.py`.

### HDR pipeline order

When processing HDR input (`--hdr auto`), FFmpeg tone-mapping is applied. The correct order is Resize → Linear → Tonemap → BT709 → CAS → YUV420P. Tonemap params: `desat=2`, `npl=200`.

### Audio

Loudness normalization uses EBU R128 two-pass (`--loudnorm on`, default): target -14 LUFS (Instagram), true-peak **-1.5 dBTP** (headroom against IG's AAC transcode), `linear=true`. Pass 1 (`build_loudnorm_measure_filter`) measures with `print_format=json`; Pass 2 (`build_loudnorm_filter`) feeds back `measured_I/TP/LRA/thresh` **and `offset` (target_offset)** for precision. Channel-aware: mono sources get `dual_mono=true` (EBU -3 LU correction), and >2-channel sources are downmixed to stereo *inside* the filter chain (`aformat=channel_layouts=stereo,…`) in **both** passes so measurement and delivery share the same layout (the trailing `-ac 2` is then a no-op). `-14` is the lever that prevents IG re-normalizing the audio; IG always re-encodes, so the goal is minimal alteration, not avoiding recompression. Channel count via `probe_audio_channels` (defaults to stereo on failure). Output: AAC-LC, 48 kHz, stereo, 192 kbps. Test coverage in `enhance/test_loudnorm.py`.

### EBU Meter (post-encode QC)

After every encode, `_encode_single_file()` calls `run_post_encode_qc()` (in `ebu_meter.py`, modeled on NapoleonWils0n's `ebu-meter.rs`). Two parts:

1. **Audit (always runs, single *and* batch):** measures the final file with the canonical `ebur128=peak=true` filter (`-f null`), parsing the `Summary:` block for Integrated LUFS-I / True Peak dBTP / LRA, plus codec + sample rate via ffprobe. Renders an **ANTES (original) vs DEPOIS (final)** Rich table with `✓`/`⚠` flags against `LOUDNORM_TARGETS` (−14 LUFS ±1, ≤ −1.5 dBTP). This is independent of loudnorm's internal estimate — a true post-encode audit. Loudnorm 2-pass remains the *only* normalization; this never alters audio.
2. **Visual monitor (`--ebu-meter`, default `on`; force-disabled in `--batch`):** opens two detached, non-blocking FFplay windows (original + final) using the reference filtergraph `amovie='<esc>',ebur128=video=1:meter=18:dualmono=true:target=<I>[out0][out1]` (path escaping `\`→`\\`, `:`→`\:`). `ebur128=video=1` is itself the broadcast-style meter — no `showwaves`/`showspectrum`.

All failure modes degrade gracefully (no audio / unparseable `-inf` silence → `—`; `ffplay` missing → warning + table still prints; any QC error is caught and never breaks the encode). Pure builders/parsers tested in `enhance/test_ebu_meter.py` (no subprocess).

### LUTs

Two `.cube` files in root:
- `FilmLook_Portra400_SkinPriority_D65.cube` — used in Cineon pipeline (Node 5, trilinear 3D interpolation)
- `HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube` — used in FFmpeg pipeline (`--lut on`)

### Entry point

`Reels_Encoder_v2_FINAL.py` (~4000 lines) owns all CLI argument parsing, hardware detection, VBV bitrate selection, and dispatches to either the FFmpeg subprocess path or the Cineon pipeline in `cineon_pipeline.py`.

### Interactive Terminal UI (`ui/`)

Premiere-Pro-styled interactive layer, added **additively** (the engine monolith is untouched except three small guarded seams). Full design rationale + the 3 evaluated visual concepts live in `docs/terminal-ui-masterplan.md`.

- `ui/theme.py` — single source of truth for the palette (indigo/violet), named Rich styles, box choices, and glyph sets (with ASCII fallback for legacy consoles). `get_console()` is the themed `Console` factory and also nudges stdout/stderr to UTF-8 so emoji/box glyphs don't crash on cp1252 consoles.
- `ui/config.py` — `EncodeConfig` (Pydantic v2) mirrors every `argparse` dest 1:1. `to_namespace()` emits the *exact* `argparse.Namespace` the engine consumes; `from_namespace()` is the inverse. Validates ranges/choices and carries preset factories.
- `ui/components.py` — reusable renderables (tab bar, Program/Properties panels, info cards, quality chips, log panel, settings-preview card). Pure: return Rich renderables, no I/O.
- `ui/prompts.py` — validated interactive input helpers (file/folder path, choice menu, numeric range, toggle). Never run inside `Live`.
- `ui/launcher.py` — `run_launcher()`: banner → preset menu → source pick → (preset or full tabbed config) → settings preview → confirm → returns a `Namespace` (or `None` if cancelled).
- `ui/dashboard.py` — `EncodeDashboard` duck-types `ResolveProgressHUD` (`update_frame()`/`render()`); Premiere-style Live layout with progress + perf monitor (psutil) + a log tail read from the engine's shared stderr deque. `make_dashboard()` is the factory.

**Engine seams (the only edits to `Reels_Encoder_v2_FINAL.py`), all guarded with `try/except` and identical-to-before fallback:**
1. Global `console` adopts `ui.theme.get_console()` if available (else plain `Console()`).
2. `_run_encoding()` uses `ui.dashboard.make_dashboard(...)` if available, else `ResolveProgressHUD`.
3. `main()` opens the launcher when `--ui` is set or no input/`--batch` is given; the returned Namespace flows through the existing single/batch dispatch. Every existing CLI command behaves identically.

Tests: `ui/test_*.py` (config round-trip, theme tokens, component render-smoke, launcher wiring via monkeypatch, dashboard math/render). Run with `python -m pytest ui/ -v`.
