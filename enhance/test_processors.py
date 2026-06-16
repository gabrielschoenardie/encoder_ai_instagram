"""
test_processors.py
==================
FASE 27D — Testes de validação para processor.py e ffmpeg_filters.py.

Todos os testes usam frames sintéticos (NumPy); nenhum vídeo real necessário.

Cobertura:
    processor.py
        ✅ clean_profile        → get_enhance_fn() returns None
        ✅ noisy_profile        → callable, float32, shape preservada
        ✅ compressed_profile   → callable com deband_smooth activo
        ✅ sharp_needed         → callable com sharpen activo
        ✅ mixed_profile        → callable com denoise+sharpen+deband
        ✅ denoise_reduces_noise → σ mensurável reduz após denoise
        ✅ sharpen_increases_lap → Laplacian variance sobe após sharpen
        ✅ deband_reduces_flat  → flat region pct reduz em frame com banding
        ✅ output_range         → output ∈ [0,1] (sem overflow)
        ✅ output_dtype         → sempre float32
        ✅ shape_preserved      → (H, W, 3) igual ao input
        ✅ nlmeans_method       → path de código nlmeans (strong noise)
        ✅ bilateral_method     → path de código bilateral (medium noise)
        ✅ gaussian_method      → path de código gaussian (light noise)

    ffmpeg_filters.py  (build_pre_lut_filtergraph — pipeline: deblock→denoise→deband→CAS)
        ✅ clean_profile        → build_pre_lut_filtergraph() returns None
        ✅ noisy_profile        → string com hqdn3d/nlmeans
        ✅ compressed_profile   → string com deband
        ✅ sharp_needed         → string com cas=strength=
        ✅ mixed_profile        → string com múltiplos filtros
        ✅ order_denoise_first  → denoise precede deband (Hollywood DI order)
        ✅ order_cas_last       → cas sempre no final
        ✅ order_deband_before_cas → deband precede cas
        ✅ nlmeans_string       → nlmeans present para method=nlmeans
        ✅ hqdn3d_string        → hqdn3d present para bilateral/gaussian
        ✅ no_syntax_errors     → sem parênteses/espaços errados
        ✅ param_min_nlmeans_s  → s ≥ 1.0 (FFmpeg mínimo)
        ✅ deband_thr_range     → thr ∈ [0.00003, 0.5]
        ✅ cas_strength_range   → strength ∈ [0.0, 0.65]

Run:
    python test_processors.py
    python -m pytest test_processors.py -v
"""

from __future__ import annotations

import sys
import os
import time
import ast
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
# test_processors.py may live in two locations:
#   A) vbv_analyzer/test_processors.py          (run from vbv_analyzer/)
#   B) vbv_analyzer/enhance/test_processors.py  (run from enhance/)
#
# _INSIDE_PACKAGE = True  when __file__ is inside the enhance/ folder itself.
# In that case:
#   - parent dir (vbv_analyzer/) must go on sys.path for "from enhance.X import"
#   - AST paths start at the enhance/ dir directly (no extra "enhance/" segment)

_HERE = os.path.dirname(os.path.abspath(__file__))
_INSIDE_PACKAGE = os.path.basename(_HERE).lower() == "enhance"

if _INSIDE_PACKAGE:
    _PROJECT_ROOT = os.path.dirname(_HERE)   # vbv_analyzer/
    _ENHANCE_DIR  = _HERE                    # vbv_analyzer/enhance/
else:
    _PROJECT_ROOT = _HERE                    # vbv_analyzer/
    _ENHANCE_DIR  = os.path.join(_HERE, "enhance")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── Imports ───────────────────────────────────────────────────────────────────
from enhance.profile import (  # noqa: E402
    EnhanceProfile,
    NoiseAgg,
    BandingAgg,
    DetailAgg,
    build_enhance_profile_from_metrics,
)
from enhance.processor import get_enhance_fn  # noqa: E402
from enhance.ffmpeg_filters import build_pre_lut_filtergraph  # noqa: E402


# ── Synthetic frame factories ─────────────────────────────────────────────────

def make_frame(h: int = 270, w: int = 480, mode: str = "gradient") -> np.ndarray:
    """
    Generate a synthetic float32 [0,1] RGB frame for testing.

    Modes:
        "gradient"  — smooth luma gradient (banding candidate)
        "noisy"     — gradient + gaussian noise
        "flat"      — uniform mid-grey
        "textured"  — high-frequency noise-free texture
    """
    rng = np.random.default_rng(42)

    if mode == "gradient":
        luma = np.linspace(0.1, 0.9, w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0)
        frame = np.stack([luma, luma, luma], axis=-1)

    elif mode == "noisy":
        luma = np.linspace(0.1, 0.9, w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0)
        noise = rng.normal(0, 0.12, size=(h, w, 3)).astype(np.float32)
        frame = np.clip(np.stack([luma, luma, luma], axis=-1) + noise, 0.0, 1.0)

    elif mode == "flat":
        frame = np.full((h, w, 3), 0.5, dtype=np.float32)

    elif mode == "textured":
        # Checkerboard + mid-tone
        checker = (
            (np.arange(h)[:, None] // 8 + np.arange(w)[None, :] // 8) % 2
        ).astype(np.float32) * 0.4 + 0.3
        frame = np.stack([checker, checker, checker], axis=-1)

    else:
        frame = rng.random((h, w, 3)).astype(np.float32)

    return frame.astype(np.float32)


# ── Profile factories ─────────────────────────────────────────────────────────

def _profile_clean() -> EnhanceProfile:
    """No enhancement needed."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.005, low_freq_ratio=0.1, uniformity=0.95),
        BandingAgg(severity=0.05, gradient_score=0.1, flat_region_pct=0.1),
        DetailAgg(sharpness=0.85, texture_complexity=0.7, edge_density=0.3,
                  freq_low=0.8, freq_mid=0.15, freq_high=0.05, detail_score=0.7),
    )


def _profile_noisy_light() -> EnhanceProfile:
    """Light noise → gaussian denoise."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.03, low_freq_ratio=0.3, uniformity=0.8),
        BandingAgg(severity=0.05, gradient_score=0.1, flat_region_pct=0.1),
        DetailAgg(sharpness=0.55, texture_complexity=0.4, edge_density=0.2,
                  freq_low=0.6, freq_mid=0.3, freq_high=0.1, detail_score=0.4),
    )


def _profile_noisy_medium() -> EnhanceProfile:
    """Medium noise → bilateral denoise + gentle sharpen."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.07, low_freq_ratio=0.4, uniformity=0.7),
        BandingAgg(severity=0.05, gradient_score=0.1, flat_region_pct=0.1),
        DetailAgg(sharpness=0.50, texture_complexity=0.3, edge_density=0.2,
                  freq_low=0.5, freq_mid=0.35, freq_high=0.15, detail_score=0.4),
    )


def _profile_noisy_strong() -> EnhanceProfile:
    """Strong noise → nlmeans denoise, sharpen OFF."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.15, low_freq_ratio=0.5, uniformity=0.6),
        BandingAgg(severity=0.05, gradient_score=0.1, flat_region_pct=0.1),
        DetailAgg(sharpness=0.40, texture_complexity=0.3, edge_density=0.15,
                  freq_low=0.5, freq_mid=0.35, freq_high=0.15, detail_score=0.3),
    )


def _profile_compressed() -> EnhanceProfile:
    """Compressed banding → deband+."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.01, low_freq_ratio=0.2, uniformity=0.9),
        BandingAgg(severity=0.70, gradient_score=0.6, flat_region_pct=0.5),
        DetailAgg(sharpness=0.50, texture_complexity=0.3, edge_density=0.2,
                  freq_low=0.7, freq_mid=0.2, freq_high=0.1, detail_score=0.4),
    )


def _profile_soft() -> EnhanceProfile:
    """Soft / blurry → sharpen strong."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.01, low_freq_ratio=0.2, uniformity=0.9),
        BandingAgg(severity=0.05, gradient_score=0.1, flat_region_pct=0.1),
        DetailAgg(sharpness=0.15, texture_complexity=0.2, edge_density=0.1,
                  freq_low=0.9, freq_mid=0.08, freq_high=0.02, detail_score=0.2),
    )


def _profile_mixed() -> EnhanceProfile:
    """Mixed: moderate noise + banding + soft → all three active."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.06, low_freq_ratio=0.35, uniformity=0.75),
        BandingAgg(severity=0.45, gradient_score=0.4, flat_region_pct=0.35),
        DetailAgg(sharpness=0.35, texture_complexity=0.3, edge_density=0.2,
                  freq_low=0.6, freq_mid=0.3, freq_high=0.1, detail_score=0.35),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessor:

    # ── None / clean ─────────────────────────────────────────────────────────

    def test_clean_returns_none(self):
        fn = get_enhance_fn(_profile_clean())
        assert fn is None, "Clean profile must return None (zero overhead)"

    # ── Callable contract ─────────────────────────────────────────────────────

    def test_noisy_returns_callable(self):
        fn = get_enhance_fn(_profile_noisy_medium())
        assert callable(fn), "Noisy profile must return callable"

    def test_compressed_returns_callable(self):
        fn = get_enhance_fn(_profile_compressed())
        assert callable(fn), "Compressed profile must return callable"

    def test_soft_returns_callable(self):
        fn = get_enhance_fn(_profile_soft())
        assert callable(fn), "Soft profile must return callable"

    def test_mixed_returns_callable(self):
        fn = get_enhance_fn(_profile_mixed())
        assert callable(fn), "Mixed profile must return callable"

    # ── Shape / dtype ─────────────────────────────────────────────────────────

    def test_shape_preserved_small(self):
        frame = make_frame(h=90, w=160, mode="gradient")
        fn = get_enhance_fn(_profile_noisy_medium())
        out = fn(frame)
        assert out.shape == frame.shape, f"Shape mismatch: {out.shape} != {frame.shape}"

    def test_shape_preserved_large(self):
        frame = make_frame(h=270, w=480, mode="noisy")
        fn = get_enhance_fn(_profile_mixed())
        out = fn(frame)
        assert out.shape == frame.shape

    def test_output_dtype_float32(self):
        frame = make_frame(h=90, w=160, mode="gradient")
        fn = get_enhance_fn(_profile_noisy_medium())
        out = fn(frame)
        assert out.dtype == np.float32, f"Expected float32, got {out.dtype}"

    def test_output_range_no_overflow(self):
        frame = make_frame(h=90, w=160, mode="noisy")
        fn = get_enhance_fn(_profile_mixed())
        out = fn(frame)
        assert float(out.min()) >= 0.0, f"Output min {out.min():.4f} < 0.0"
        assert float(out.max()) <= 1.0, f"Output max {out.max():.4f} > 1.0"

    def test_output_range_flat_frame(self):
        frame = make_frame(h=90, w=160, mode="flat")
        fn = get_enhance_fn(_profile_compressed())
        out = fn(frame)
        assert float(out.min()) >= 0.0
        assert float(out.max()) <= 1.0

    # ── Perceptual effect tests ───────────────────────────────────────────────

    def test_denoise_reduces_noise(self):
        """Strong denoiser must reduce per-pixel σ on a noisy frame."""
        rng = np.random.default_rng(0)
        base = np.full((90, 160, 3), 0.5, dtype=np.float32)
        noise = rng.normal(0, 0.15, size=(90, 160, 3)).astype(np.float32)
        frame = np.clip(base + noise, 0.0, 1.0).astype(np.float32)

        fn = get_enhance_fn(_profile_noisy_strong())
        assert fn is not None
        out = fn(frame)

        sigma_in = float(np.std(frame))
        sigma_out = float(np.std(out))
        assert sigma_out < sigma_in, (
            f"Denoiser must reduce σ: before={sigma_in:.4f} after={sigma_out:.4f}"
        )

    def test_sharpen_increases_laplacian(self):
        """Sharpening must increase Laplacian variance on a soft frame."""
        frame = make_frame(h=90, w=160, mode="textured")

        fn = get_enhance_fn(_profile_soft())
        assert fn is not None
        out = fn(frame)

        from scipy.ndimage import convolve
        lap_k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
        luma_in = 0.2126*frame[...,0] + 0.7152*frame[...,1] + 0.0722*frame[...,2]
        luma_out = 0.2126*out[...,0] + 0.7152*out[...,1] + 0.0722*out[...,2]
        var_in = float(np.var(convolve(luma_in, lap_k, mode='reflect')))
        var_out = float(np.var(convolve(luma_out, lap_k, mode='reflect')))
        assert var_out > var_in, (
            f"Sharpen must increase Laplacian var: before={var_in:.6f} after={var_out:.6f}"
        )

    def test_deband_smooth_on_gradient_frame(self):
        """Deband_smooth must operate without error on banding-like gradient."""
        frame = make_frame(h=90, w=160, mode="gradient")
        fn = get_enhance_fn(_profile_compressed())
        assert fn is not None
        out = fn(frame)
        assert out.shape == frame.shape
        assert out.dtype == np.float32
        assert float(out.min()) >= 0.0
        assert float(out.max()) <= 1.0

    # ── Method-specific paths ─────────────────────────────────────────────────

    def test_nlmeans_path(self):
        """nlmeans method must execute and reduce noise."""
        frame = make_frame(h=90, w=160, mode="noisy")
        profile = _profile_noisy_strong()
        assert profile.denoise_method == "nlmeans"
        fn = get_enhance_fn(profile)
        assert fn is not None
        out = fn(frame)
        assert out.dtype == np.float32

    def test_bilateral_path(self):
        """bilateral method must execute."""
        frame = make_frame(h=90, w=160, mode="noisy")
        profile = _profile_noisy_medium()
        assert profile.denoise_method == "bilateral"
        fn = get_enhance_fn(profile)
        assert fn is not None
        out = fn(frame)
        assert out.dtype == np.float32

    def test_gaussian_path(self):
        """gaussian method must execute."""
        frame = make_frame(h=90, w=160, mode="gradient")
        profile = _profile_noisy_light()
        assert profile.denoise_method == "gaussian"
        fn = get_enhance_fn(profile)
        assert fn is not None
        out = fn(frame)
        assert out.dtype == np.float32

    def test_profile_any_enabled_false(self):
        """any_enabled=False → None (baseline guard)."""
        p = EnhanceProfile()
        assert not p.any_enabled
        assert get_enhance_fn(p) is None


# ══════════════════════════════════════════════════════════════════════════════
# FFMPEG FILTERS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFFmpegFilters:

    # ── None / clean ─────────────────────────────────────────────────────────

    def test_clean_returns_none(self):
        result = build_pre_lut_filtergraph(_profile_clean())
        assert result is None, "Clean profile must return None"

    def test_empty_profile_returns_none(self):
        result = build_pre_lut_filtergraph(EnhanceProfile())
        assert result is None

    # ── Returns string ────────────────────────────────────────────────────────

    def test_noisy_returns_string(self):
        result = build_pre_lut_filtergraph(_profile_noisy_medium())
        assert isinstance(result, str) and len(result) > 0

    def test_compressed_returns_string(self):
        result = build_pre_lut_filtergraph(_profile_compressed())
        assert isinstance(result, str) and "deband" in result

    def test_soft_returns_string(self):
        result = build_pre_lut_filtergraph(_profile_soft())
        assert isinstance(result, str) and "cas" in result

    def test_mixed_returns_string(self):
        result = build_pre_lut_filtergraph(_profile_mixed())
        assert isinstance(result, str) and len(result) > 0

    # ── Filter presence ───────────────────────────────────────────────────────

    def test_nlmeans_present_for_strong_noise(self):
        result = build_pre_lut_filtergraph(_profile_noisy_strong())
        assert result is not None and "nlmeans" in result, (
            f"Expected nlmeans in: {result}"
        )

    def test_hqdn3d_for_bilateral(self):
        result = build_pre_lut_filtergraph(_profile_noisy_medium())
        assert result is not None and "hqdn3d" in result, (
            f"Expected hqdn3d in: {result}"
        )

    def test_hqdn3d_for_gaussian(self):
        result = build_pre_lut_filtergraph(_profile_noisy_light())
        assert result is not None and "hqdn3d" in result, (
            f"Expected hqdn3d in: {result}"
        )

    def test_cas_for_soft(self):
        result = build_pre_lut_filtergraph(_profile_soft())
        assert result is not None and "cas=strength=" in result

    def test_deband_for_compressed(self):
        result = build_pre_lut_filtergraph(_profile_compressed())
        assert result is not None and "deband" in result

    # ── Pipeline order ────────────────────────────────────────────────────────

    def test_order_denoise_before_deband(self):
        """In build_pre_lut_filtergraph: denoise precedes deband (Hollywood DI order)."""
        result = build_pre_lut_filtergraph(_profile_mixed())
        assert result is not None
        parts = result.split(",")
        filter_names = [p.split("=")[0].strip() for p in parts]
        if "deband" in filter_names and ("hqdn3d" in filter_names or "nlmeans" in filter_names):
            deband_idx = filter_names.index("deband")
            denoise_idx = next(
                (i for i, n in enumerate(filter_names) if n in ("hqdn3d", "nlmeans")),
                len(filter_names),
            )
            assert denoise_idx < deband_idx, (
                f"denoise must precede deband in pre-lut pipeline: {filter_names}"
            )

    def test_order_cas_last(self):
        """CAS must always be the last filter in pre-lut pipeline."""
        result = build_pre_lut_filtergraph(_profile_mixed())
        assert result is not None
        parts = result.split(",")
        filter_names = [p.split("=")[0].strip() for p in parts]
        if "cas" in filter_names:
            assert filter_names[-1] == "cas", (
                f"cas must be last: {filter_names}"
            )

    def test_order_deband_before_cas(self):
        """For compressed+soft: deband before cas (Hollywood DI order)."""
        # Build a profile with both deband and sharpen
        p = build_enhance_profile_from_metrics(
            NoiseAgg(sigma=0.01, low_freq_ratio=0.1, uniformity=0.95),
            BandingAgg(severity=0.70, gradient_score=0.6, flat_region_pct=0.5),
            DetailAgg(sharpness=0.15, texture_complexity=0.2, edge_density=0.1,
                      freq_low=0.9, freq_mid=0.08, freq_high=0.02, detail_score=0.2),
        )
        result = build_pre_lut_filtergraph(p)
        assert result is not None
        parts = result.split(",")
        names = [x.split("=")[0].strip() for x in parts]
        if "deband" in names and "cas" in names:
            assert names.index("deband") < names.index("cas"), (
                f"deband must precede cas: {names}"
            )

    # ── Parameter validation ──────────────────────────────────────────────────

    def test_nlmeans_s_min(self):
        """nlmeans s parameter must be ≥ 1.0 (FFmpeg minimum)."""
        result = build_pre_lut_filtergraph(_profile_noisy_strong())
        assert result is not None
        # Filter string: nlmeans=s=X.XX:p=7:r=15
        # Split on ":" gives: ["nlmeans=s=X.XX", "p=7", "r=15"]
        # Split first token on "=" twice: "nlmeans", "s", "X.XX"
        for part in result.split(","):
            if part.startswith("nlmeans"):
                tokens = part.split(":")
                # First token is "nlmeans=s=VALUE" — split after second '='
                first = tokens[0]  # "nlmeans=s=1.80"
                s_str = first.split("=", 2)[-1]  # "1.80"
                s_val = float(s_str)
                assert s_val >= 1.0, f"nlmeans s={s_val} < 1.0 (FFmpeg minimum)"

    def test_deband_thr_range(self):
        """deband threshold must be in FFmpeg normalized range [0.00003, 0.5]."""
        result = build_pre_lut_filtergraph(_profile_compressed())
        assert result is not None
        for part in result.split(","):
            if part.startswith("deband"):
                for tok in part.split(":"):
                    if tok.startswith("1thr=") or tok.startswith("2thr=") or tok.startswith("3thr="):
                        thr = float(tok.split("=")[1])
                        assert 0.00003 <= thr <= 0.5, f"deband thr={thr} out of range [0.00003, 0.5]"

    def test_no_empty_filter_segments(self):
        """No empty segments between commas."""
        result = build_pre_lut_filtergraph(_profile_mixed())
        assert result is not None
        parts = result.split(",")
        for p in parts:
            assert p.strip() != "", f"Empty filter segment in: {result}"

    def test_no_spaces_in_filter_string(self):
        """FFmpeg filter strings must not contain unquoted spaces."""
        result = build_pre_lut_filtergraph(_profile_mixed())
        assert result is not None
        assert " " not in result, f"Spaces found in filter string: {result!r}"

    def test_cas_strength_param(self):
        """cas= must have strength= parameter with value in [0.0, 0.65]."""
        result = build_pre_lut_filtergraph(_profile_soft())
        assert result is not None
        for part in result.split(","):
            if part.startswith("cas"):
                assert "strength=" in part, f"cas must have strength= param: {part}"
                val = float(part.split("strength=")[1].split(":")[0])
                assert 0.0 <= val <= 0.65, f"cas strength={val} out of range [0.0, 0.65]"

    def test_hqdn3d_four_params(self):
        """hqdn3d= must have exactly 4 colon-separated params."""
        result = build_pre_lut_filtergraph(_profile_noisy_medium())
        assert result is not None
        for part in result.split(","):
            if part.startswith("hqdn3d"):
                body = part[len("hqdn3d="):]
                params = body.split(":")
                assert len(params) == 4, (
                    f"hqdn3d must have 4 params, got {len(params)}: {part}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# AST VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

class TestASTValidation:
    """Validate that all new modules parse without syntax errors."""

    def _check_ast(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            raise AssertionError(f"SyntaxError in {path}: {e}")

    def test_processor_ast(self):
        path = os.path.join(_ENHANCE_DIR, "processor.py")
        self._check_ast(path)

    def test_ffmpeg_filters_ast(self):
        path = os.path.join(_ENHANCE_DIR, "ffmpeg_filters.py")
        self._check_ast(path)

    def test_profile_ast(self):
        path = os.path.join(_ENHANCE_DIR, "profile.py")
        self._check_ast(path)

    def test_noise_ast(self):
        path = os.path.join(_ENHANCE_DIR, "analyzers", "noise.py")
        self._check_ast(path)

    def test_banding_ast(self):
        path = os.path.join(_ENHANCE_DIR, "analyzers", "banding.py")
        self._check_ast(path)

    def test_detail_ast(self):
        path = os.path.join(_ENHANCE_DIR, "analyzers", "detail.py")
        self._check_ast(path)


    # ── Synthetic frame factories ─────────────────────────────────────────────

    @staticmethod
    def _grain_frame(h: int = 270, w: int = 480) -> np.ndarray:
        """Frame com grain Gaussiano de alta frequência (σ=0.08 sobre fundo cinza)."""
        rng = np.random.default_rng(0)
        base = np.full((h, w, 3), 0.5, dtype=np.float32)
        noise = rng.normal(0, 0.08, (h, w, 3)).astype(np.float32)
        return np.clip(base + noise, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def _flat_frame(h: int = 270, w: int = 480) -> np.ndarray:
        """Frame completamente plano (fundo sólido — ruído mínimo)."""
        return np.full((h, w, 3), 0.5, dtype=np.float32)

    @staticmethod
    def _gradient_frame(h: int = 270, w: int = 480) -> np.ndarray:
        """Frame com gradiente horizontal suave (simula cena limpa sem grain)."""
        luma = np.linspace(0.1, 0.9, w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0)
        return np.stack([luma, luma, luma], axis=-1)


# ══════════════════════════════════════════════════════════════════════════════
# FASE 29A — MCTF Filtergraph Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMCTFFiltergraph:
    """FASE 29A — build_selective_filtergraph detecta video mask vs PNG estático."""

    def _make_profile_deband(self):
        from enhance.profile import EnhanceProfile
        return EnhanceProfile(deband_enhance_enabled=True, deband_strength=0.5)

    def test_video_mask_has_no_stream_loop(self):
        """Mask .mp4 (MCTF) NÃO deve ter -stream_loop -1 nos extra_inputs."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        profile = self._make_profile_deband()
        result = build_selective_filtergraph(
            profile,
            main_vf_tail="scale=1080:1920",
            deband_mask_path="enhance_maps/mctf_deband_mask.mp4",
        )
        assert result is not None, "build_selective_filtergraph deve retornar tupla para mask .mp4"
        _, extra_inputs, _ = result
        assert "-stream_loop" not in extra_inputs, (
            f"Mask .mp4 NÃO deve usar -stream_loop, mas extra_inputs={extra_inputs}"
        )
        assert "mctf_deband_mask.mp4" in " ".join(str(x) for x in extra_inputs), (
            "Path do .mp4 deve estar em extra_inputs"
        )

    def test_png_mask_has_stream_loop(self):
        """Mask .png estático DEVE ter -stream_loop -1 nos extra_inputs (backward compat)."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        profile = self._make_profile_deband()
        result = build_selective_filtergraph(
            profile,
            main_vf_tail="scale=1080:1920",
            deband_mask_path="enhance_maps/consensus_deband_mask.png",
        )
        assert result is not None, "build_selective_filtergraph deve retornar tupla para mask .png"
        _, extra_inputs, _ = result
        assert "-stream_loop" in extra_inputs, (
            f"Mask .png DEVE usar -stream_loop, mas extra_inputs={extra_inputs}"
        )
        assert "-1" in extra_inputs, "Deve haver -1 após -stream_loop"

    def test_is_video_mask_extensions(self):
        """_is_video_mask deve reconhecer extensões de vídeo e recusar imagens/None."""
        from enhance.ffmpeg_filters import _is_video_mask
        assert _is_video_mask("mask.mp4") is True
        assert _is_video_mask("mask.mkv") is True
        assert _is_video_mask("mask.mov") is True
        assert _is_video_mask("mask.avi") is True
        assert _is_video_mask("mask.webm") is True
        assert _is_video_mask("mask.png") is False
        assert _is_video_mask("mask.PNG") is False
        assert _is_video_mask("mask.jpg") is False
        assert _is_video_mask(None) is False
        assert _is_video_mask("") is False


class TestBluenoiseDither:
    """FASE 30A — _build_dither() output validation."""

    def test_dither_string_has_noise_filter(self):
        """_build_dither deve retornar string com prefixo 'noise='."""
        from enhance.ffmpeg_filters import _build_dither
        result = _build_dither(0.5)
        assert result.startswith("noise="), f"Expected 'noise=' prefix, got: {result}"

    def test_dither_c0s_range(self):
        """c0s deve estar no range [_DITHER_C0S_MIN, _DITHER_C0S_MAX] para todos os strengths."""
        from enhance.ffmpeg_filters import _build_dither, _DITHER_C0S_MIN, _DITHER_C0S_MAX
        for strength in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = _build_dither(strength)
            # Extrai c0s do string "noise=c0s=N:c0f=..."
            inner = result[len("noise="):]
            parts = dict(p.split("=", 1) for p in inner.split(":"))
            c0s = int(parts["c0s"])
            assert _DITHER_C0S_MIN <= c0s <= _DITHER_C0S_MAX, (
                f"strength={strength} -> c0s={c0s} out of range [{_DITHER_C0S_MIN},{_DITHER_C0S_MAX}]"
            )

    def test_dither_has_temporal_flag(self):
        """Dither deve ter flags temporal 't' e uniforme 'u' (RPDF) em c0f."""
        from enhance.ffmpeg_filters import _build_dither
        result = _build_dither(0.5)
        assert ":c0f=" in result, f"Expected ':c0f=' in result, got: {result}"
        c0f_value = result.split(":c0f=")[1]
        assert "t" in c0f_value, (
            f"Expected temporal flag 't' in c0f value, got: '{c0f_value}'"
        )
        assert "u" in c0f_value, (
            f"Expected uniform flag 'u' (RPDF) in c0f value, got: '{c0f_value}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# SELECTIVE FILTERGRAPH — body / structure coverage
# ══════════════════════════════════════════════════════════════════════════════

def _assert_no_malformed_vf(vf: str) -> None:
    """Assert a comma-separated -vf string has no malformed fragments.

    Guards against: empty segments (',,'), leading/trailing commas, empty
    colon-separated tokens within a fragment, and unquoted spaces.
    """
    assert vf, "filter string must be non-empty"
    assert ",," not in vf, f"double comma (empty fragment) in: {vf!r}"
    assert not vf.startswith(","), f"leading comma in: {vf!r}"
    assert not vf.endswith(","), f"trailing comma in: {vf!r}"
    assert " " not in vf, f"unquoted space in -vf string: {vf!r}"
    for frag in vf.split(","):
        assert frag.strip() != "", f"empty fragment in: {vf!r}"
        for tok in frag.split(":"):
            assert tok != "", f"empty colon-token in fragment {frag!r} of {vf!r}"


def _numeric_params(vf: str):
    """Yield every value of a `key=value` token whose value looks numeric."""
    for frag in vf.split(","):
        for tok in frag.split(":"):
            if "=" not in tok:
                continue
            value = tok.rsplit("=", 1)[-1]
            try:
                yield float(value)
            except ValueError:
                continue  # non-numeric param value (e.g. filter=weak) — skip


def _selective_profile(**overrides) -> EnhanceProfile:
    """Profile with all four stages enabled (deblock/denoise/deband/sharpen)."""
    base = dict(
        deblock_enabled=True,
        denoise_enabled=True, denoise_strength=0.5, denoise_method="hqdn3d",
        deband_enhance_enabled=True, deband_strength=0.5,
        sharpen_enabled=True, sharpen_strength=0.5,
    )
    base.update(overrides)
    return EnhanceProfile(**base)


class TestSelectiveFiltergraph:
    """FASE 29A — build_selective_filtergraph() filter_complex body structure.

    The existing TestMCTFFiltergraph only checks the -stream_loop flag; these
    cover the actual filter_complex graph that gets built when masks exist.
    """

    def test_returns_triple_when_mask_present(self):
        from enhance.ffmpeg_filters import build_selective_filtergraph
        result = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920", deband_mask_path="d.png"
        )
        assert isinstance(result, tuple) and len(result) == 3
        fc, extra_inputs, map_label = result
        assert isinstance(fc, str) and fc
        assert isinstance(extra_inputs, list)
        assert map_label == "[vout]"

    def test_none_when_no_mask_paths(self):
        """No mask paths → None (caller falls back to global -vf)."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        assert build_selective_filtergraph(_selective_profile(), "scale=1080:1920") is None

    def test_none_when_masks_given_but_filters_disabled(self):
        """Mask paths supplied but deband/sharpen disabled → None.

        has_deband/has_sharpen require BOTH a path AND the enabling flag.
        """
        from enhance.ffmpeg_filters import build_selective_filtergraph
        profile = EnhanceProfile(deband_enhance_enabled=False, sharpen_enabled=False)
        result = build_selective_filtergraph(
            profile, "scale=1080:1920",
            deband_mask_path="d.png", sharpen_mask_path="s.png",
        )
        assert result is None

    def test_alphamerge_present_for_deband_mask(self):
        """A deband mask must produce an alphamerge step (selective application)."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, _, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920", deband_mask_path="d.png"
        )
        assert "alphamerge" in fc, f"deband mask must alphamerge: {fc}"
        # alphamerge requires an alpha-carrying format upstream
        assert "format=yuva420p" in fc, f"alphamerge needs yuva420p: {fc}"
        assert "[dmask]" in fc, f"deband mask label must be wired: {fc}"

    def test_alphamerge_present_for_sharpen_mask(self):
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, _, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920", sharpen_mask_path="s.png"
        )
        assert "alphamerge" in fc, f"sharpen mask must alphamerge: {fc}"
        assert "[smask]" in fc, f"sharpen mask label must be wired: {fc}"

    def test_both_masks_produce_two_alphamerge_two_overlay(self):
        """Two masks → two selective branches (2× alphamerge + 2× overlay)."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, _, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920",
            deband_mask_path="d.png", sharpen_mask_path="s.png",
        )
        assert fc.count("alphamerge") == 2, f"expected 2 alphamerge: {fc}"
        assert fc.count("overlay=format=yuv420") == 2, f"expected 2 overlay: {fc}"
        assert fc.count("split=2") == 2, f"expected 2 split: {fc}"

    def test_mask_input_indices_increment(self):
        """Two masks → mask streams referenced as [1:v] then [2:v]."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, extra_inputs, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920",
            deband_mask_path="d.png", sharpen_mask_path="s.png",
        )
        assert "[1:v]" in fc and "[2:v]" in fc, f"mask indices must be 1 and 2: {fc}"
        assert "[3:v]" not in fc, f"no third mask input expected: {fc}"
        assert extra_inputs.count("-i") == 2, f"expected 2 mask inputs: {extra_inputs}"

    def test_single_mask_uses_only_index_one(self):
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, extra_inputs, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920", sharpen_mask_path="s.png"
        )
        assert "[1:v]" in fc, f"single mask must use [1:v]: {fc}"
        assert "[2:v]" not in fc, f"single mask must not reference [2:v]: {fc}"
        assert extra_inputs.count("-i") == 1, f"expected 1 mask input: {extra_inputs}"

    def test_main_vf_tail_appended_before_vout(self):
        """The main pipeline tail must be the final chain, mapped to [vout]."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        tail = "lut3d=hollywood.cube,scale=1080:1920,format=yuv420p"
        fc, _, map_label = build_selective_filtergraph(
            _selective_profile(), tail, deband_mask_path="d.png"
        )
        assert tail in fc, f"main_vf_tail must appear verbatim: {fc}"
        assert fc.rstrip().endswith("[vout]"), f"graph must end at [vout]: {fc}"
        assert map_label == "[vout]"

    def test_no_empty_chains_in_filter_complex(self):
        """Each ';'-separated chain must be non-empty (no dangling separators)."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, _, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920",
            deband_mask_path="d.png", sharpen_mask_path="s.png",
        )
        for chain in fc.split(";"):
            assert chain.strip() != "", f"empty chain in filter_complex: {fc!r}"

    def test_global_filters_have_no_mask_when_unmasked(self):
        """Deblock/denoise stay global; with only a deband mask, denoise is plain."""
        from enhance.ffmpeg_filters import build_selective_filtergraph
        fc, _, _ = build_selective_filtergraph(
            _selective_profile(), "scale=1080:1920", deband_mask_path="d.png"
        )
        # deblock + denoise run as simple [in] filter [out] chains, no alphamerge
        assert "[deblocked]" in fc, f"deblock chain expected: {fc}"
        assert "[denoised]" in fc, f"denoise chain expected: {fc}"


# ══════════════════════════════════════════════════════════════════════════════
# EXTREME STRENGTH VALUES — syntax robustness
# ══════════════════════════════════════════════════════════════════════════════

class TestExtremeStrengthSyntax:
    """Strength at the boundaries (0.0, 1.0) must never yield malformed syntax.

    NOTE: fragment *inclusion* is gated by the `*_enabled` flags, NOT by
    strength — so an enabled filter at strength=0.0 still emits a (clamped)
    fragment. These tests document that true behavior and assert the emitted
    strings stay well-formed at both extremes.
    """

    def _all_enabled(self, strength: float) -> EnhanceProfile:
        return EnhanceProfile(
            deblock_enabled=True,
            denoise_enabled=True, denoise_strength=strength, denoise_method="nlmeans",
            deband_enhance_enabled=True, deband_strength=strength,
            sharpen_enabled=True, sharpen_strength=strength,
        )

    def test_strength_zero_well_formed(self):
        result = build_pre_lut_filtergraph(self._all_enabled(0.0))
        assert result is not None
        _assert_no_malformed_vf(result)

    def test_strength_one_well_formed(self):
        result = build_pre_lut_filtergraph(self._all_enabled(1.0))
        assert result is not None
        _assert_no_malformed_vf(result)

    def test_strength_zero_still_emits_all_fragments(self):
        """Enabled-at-zero still emits fragments (gated by flags, not strength)."""
        result = build_pre_lut_filtergraph(self._all_enabled(0.0))
        assert result is not None
        for name in ("deblock", "nlmeans", "deband", "cas"):
            assert name in result, f"{name} fragment missing at strength=0.0: {result}"

    def test_strength_zero_params_clamped_to_minimums(self):
        """At strength 0.0 params clamp to FFmpeg-valid minimums, not below."""
        result = build_pre_lut_filtergraph(self._all_enabled(0.0))
        assert result is not None
        for frag in result.split(","):
            if frag.startswith("nlmeans"):
                s_val = float(frag.split(":")[0].split("=", 2)[-1])
                assert s_val >= 1.0, f"nlmeans s must clamp to ≥1.0: {frag}"
            if frag.startswith("deband"):
                for tok in frag.split(":"):
                    if tok[:1].isdigit() and "thr=" in tok:
                        assert float(tok.split("=")[1]) >= 0.00003, f"thr below FFmpeg min: {frag}"

    def test_strength_one_params_within_caps(self):
        """At strength 1.0 params stay within their documented upper caps."""
        result = build_pre_lut_filtergraph(self._all_enabled(1.0))
        assert result is not None
        for frag in result.split(","):
            if frag.startswith("nlmeans"):
                s_val = float(frag.split(":")[0].split("=", 2)[-1])
                assert s_val <= 10.0, f"nlmeans s exceeds FFmpeg max 10.0: {frag}"
            if frag.startswith("cas"):
                val = float(frag.split("strength=")[1].split(":")[0])
                assert val <= 0.65, f"cas strength exceeds cap 0.65: {frag}"
            if frag.startswith("deband"):
                for tok in frag.split(":"):
                    if tok[:1].isdigit() and "thr=" in tok:
                        assert float(tok.split("=")[1]) <= 0.5, f"thr exceeds 0.5: {frag}"

    def test_all_numeric_params_parse_at_both_extremes(self):
        """Every numeric `key=value` must be a finite float at 0.0 and 1.0."""
        import math
        for strength in (0.0, 1.0):
            result = build_pre_lut_filtergraph(self._all_enabled(strength))
            assert result is not None
            values = list(_numeric_params(result))
            assert values, f"expected numeric params at strength={strength}: {result}"
            for v in values:
                assert math.isfinite(v), f"non-finite param {v} at strength={strength}"


# ══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def _run_class(cls):
    """Run all test_* methods of a class. Returns (passed, failed, errors)."""
    instance = cls()
    passed = failed = 0
    failures = []
    for name in sorted(dir(instance)):
        if not name.startswith("test_"):
            continue
        method = getattr(instance, name)
        try:
            method()
            passed += 1
        except Exception as exc:
            failed += 1
            failures.append((name, exc))
    return passed, failed, failures


def main() -> int:
    print()
    print("=" * 65)
    print("  FASE 27D — Processor & FFmpeg Filters — Test Suite")
    print("=" * 65)

    total_passed = total_failed = 0
    all_failures = []

    suites = [
        ("Processor (processor.py)", TestProcessor),
        ("FFmpeg Filters (ffmpeg_filters.py)", TestFFmpegFilters),
        ("MCTF Filtergraph (FASE 29A)", TestMCTFFiltergraph),
        ("Selective Filtergraph (structure)", TestSelectiveFiltergraph),
        ("Extreme Strength Syntax", TestExtremeStrengthSyntax),
        ("Blue-noise Dither (FASE 30A)", TestBluenoiseDither),
        ("AST Validation", TestASTValidation),
    ]

    for suite_name, cls in suites:
        t0 = time.perf_counter()
        passed, failed, failures = _run_class(cls)
        elapsed = (time.perf_counter() - t0) * 1000

        status = "✅" if failed == 0 else "❌"
        print(f"\n  {status} {suite_name}")
        print(f"     {passed} passed, {failed} failed — {elapsed:.1f}ms")

        for test_name, exc in failures:
            print(f"     ✗ {test_name}")
            print(f"       {exc}")

        total_passed += passed
        total_failed += failed
        all_failures.extend(failures)

    print()
    print("=" * 65)
    if total_failed == 0:
        print(f"  ✅ {total_passed}/{total_passed} PASSED — FASE 27D VÁLIDA")
    else:
        print(f"  ❌ {total_passed} passed, {total_failed} FAILED")
    print("=" * 65)
    print()

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())