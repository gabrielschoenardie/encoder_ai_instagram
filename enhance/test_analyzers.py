"""
enhance/test_analyzers.py
=========================
Unit tests for the three content analyzers that feed the enhancement signal
chain: ``analyzers/noise.py``, ``analyzers/banding.py``, ``analyzers/detail.py``.

Every profile decision ultimately traces back to the 13 features these
analyzers extract, yet they were previously reachable only through a live
video file. These tests drive them with synthetic NumPy frames (uniform,
Gaussian-noise, gradient ramp, checkerboard) so the metrics can be validated
in isolation, deterministically, with no I/O.

Assertions favour direction and bounds (which are robust) over exact magnitudes
(which are sensitive to kernel constants).

Run: python -m pytest enhance/test_analyzers.py -v
  or: python enhance/test_analyzers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from enhance.analyzers.noise import NoiseResult, analyze_noise, _fft_mask
from enhance.analyzers.banding import BandingResult, analyze_banding
from enhance.analyzers.detail import DetailResult, analyze_detail


# ── Synthetic frame builders ─────────────────────────────────────────────────

def _uniform(h=128, w=128, level=0.5):
    """Perfectly flat gray frame."""
    return np.full((h, w, 3), level, dtype=np.float32)


def _gaussian_noise(h=128, w=128, level=0.5, sigma=0.1, seed=0):
    """Flat gray + i.i.d. Gaussian noise, clipped to [0, 1]."""
    rng = np.random.default_rng(seed)
    base = np.full((h, w, 3), level, dtype=np.float32)
    noise = rng.normal(0.0, sigma, size=base.shape).astype(np.float32)
    return np.clip(base + noise, 0.0, 1.0)


def _gradient_ramp(h=128, w=128, amplitude=0.25):
    """Gentle horizontal luminance ramp (banding-prone when quantized to 8-bit).

    A shallow slope means each 8-bit level spans several pixels, so quantization
    produces flat plateaus separated by single-level (|gradient|==1) steps — the
    classic banding signature. A full 0→1 ramp would jump ~2 levels per pixel
    and never trigger the single-step detector.
    """
    ramp = np.linspace(0.0, amplitude, w, dtype=np.float32)
    frame = np.repeat(ramp[None, :], h, axis=0)
    return np.stack([frame, frame, frame], axis=-1)


def _checkerboard(h=128, w=128, cell=1):
    """High-frequency checkerboard (rich edges / high-freq energy)."""
    yy, xx = np.indices((h, w))
    board = ((yy // cell + xx // cell) % 2).astype(np.float32)
    return np.stack([board, board, board], axis=-1)


# ── Noise analyzer ────────────────────────────────────────────────────────────

def test_noise_returns_result_type():
    r = analyze_noise(_uniform())
    assert isinstance(r, NoiseResult)


def test_noise_fields_in_range():
    r = analyze_noise(_gaussian_noise(sigma=0.08))
    for v in (r.sigma, r.low_freq_ratio, r.uniformity):
        assert 0.0 <= v <= 1.0


def test_noise_uniform_frame_has_near_zero_sigma():
    r = analyze_noise(_uniform())
    assert r.sigma < 0.01


def test_noise_sigma_increases_with_noise():
    clean = analyze_noise(_uniform())
    noisy = analyze_noise(_gaussian_noise(sigma=0.1))
    assert noisy.sigma > clean.sigma
    assert noisy.sigma > 0.02  # would trip at least the light denoise threshold


def test_noise_sigma_monotonic_with_level():
    sigmas = [analyze_noise(_gaussian_noise(sigma=s)).sigma for s in (0.02, 0.06, 0.12)]
    assert sigmas == sorted(sigmas)


def test_noise_low_freq_ratio_drops_with_high_freq_noise():
    """Flat frame is all DC (high low-freq ratio); noise pushes energy outward."""
    clean = analyze_noise(_uniform())
    noisy = analyze_noise(_gaussian_noise(sigma=0.15))
    assert clean.low_freq_ratio > noisy.low_freq_ratio


def test_noise_handles_non_square_frame():
    r = analyze_noise(_gaussian_noise(h=90, w=160, sigma=0.05))
    assert 0.0 <= r.sigma <= 1.0


# ── FFT mask (noise internal) ────────────────────────────────────────────────

def test_fft_mask_shape_and_dtype():
    m = _fft_mask(64, 48)
    assert m.shape == (64, 48)
    assert m.dtype == bool


def test_fft_mask_is_centered_disc():
    """Center pixel is inside the disc; far corner is outside."""
    m = _fft_mask(128, 128)
    assert m[64, 64]
    assert not m[0, 0]
    assert m.sum() > 0


def test_fft_mask_radius_scales_with_size():
    """Larger frames yield a larger low-freq disc (radius = min//8)."""
    small = _fft_mask(64, 64).sum()
    large = _fft_mask(256, 256).sum()
    assert large > small


# ── Banding analyzer ──────────────────────────────────────────────────────────

def test_banding_returns_result_type():
    r = analyze_banding(_uniform())
    assert isinstance(r, BandingResult)


def test_banding_fields_in_range():
    r = analyze_banding(_gradient_ramp())
    for v in (r.severity, r.gradient_score, r.flat_region_pct):
        assert 0.0 <= v <= 1.0


def test_banding_uniform_frame_is_flat():
    """A flat frame is almost entirely 'flat region' (low local std)."""
    r = analyze_banding(_uniform())
    assert r.flat_region_pct > 0.9


def test_banding_gradient_has_quantization_steps():
    """A smooth ramp quantized to 8-bit produces |gradient|==1 step boundaries."""
    ramp = analyze_banding(_gradient_ramp())
    noisy = analyze_banding(_gaussian_noise(sigma=0.15))
    # The ramp's controlled single-level steps register more than random noise.
    assert ramp.gradient_score > noisy.gradient_score


def test_banding_noise_reduces_flat_regions():
    flat = analyze_banding(_uniform())
    noisy = analyze_banding(_gaussian_noise(sigma=0.1))
    assert flat.flat_region_pct > noisy.flat_region_pct


# ── Detail analyzer ───────────────────────────────────────────────────────────

def test_detail_returns_result_type():
    r = analyze_detail(_uniform())
    assert isinstance(r, DetailResult)


def test_detail_fields_in_range():
    r = analyze_detail(_checkerboard())
    for v in (r.sharpness, r.texture_complexity, r.edge_density,
              r.freq_low, r.freq_mid, r.freq_high, r.detail_score):
        assert 0.0 <= v <= 1.0


def test_detail_uniform_frame_has_no_sharpness():
    r = analyze_detail(_uniform())
    assert r.sharpness < 0.01
    assert r.edge_density < 0.01


def test_detail_checkerboard_is_sharper_than_uniform():
    sharp = analyze_detail(_checkerboard())
    flat = analyze_detail(_uniform())
    assert sharp.sharpness > flat.sharpness
    assert sharp.edge_density > flat.edge_density


def test_detail_uniform_energy_is_low_frequency():
    """A constant frame's energy lives entirely in the low band."""
    r = analyze_detail(_uniform())
    assert r.freq_low > r.freq_high


def test_detail_checkerboard_has_more_high_freq_than_uniform():
    sharp = analyze_detail(_checkerboard())
    flat = analyze_detail(_uniform())
    assert sharp.freq_high > flat.freq_high


def test_detail_handles_non_square_frame():
    r = analyze_detail(_checkerboard(h=90, w=160))
    assert 0.0 <= r.detail_score <= 1.0


# ── Test harness (mirrors test_mock_cnn.py) ──────────────────────────────────

ALL_TESTS = [
    test_noise_returns_result_type,
    test_noise_fields_in_range,
    test_noise_uniform_frame_has_near_zero_sigma,
    test_noise_sigma_increases_with_noise,
    test_noise_sigma_monotonic_with_level,
    test_noise_low_freq_ratio_drops_with_high_freq_noise,
    test_noise_handles_non_square_frame,
    test_fft_mask_shape_and_dtype,
    test_fft_mask_is_centered_disc,
    test_fft_mask_radius_scales_with_size,
    test_banding_returns_result_type,
    test_banding_fields_in_range,
    test_banding_uniform_frame_is_flat,
    test_banding_gradient_has_quantization_steps,
    test_banding_noise_reduces_flat_regions,
    test_detail_returns_result_type,
    test_detail_fields_in_range,
    test_detail_uniform_frame_has_no_sharpness,
    test_detail_checkerboard_is_sharper_than_uniform,
    test_detail_uniform_energy_is_low_frequency,
    test_detail_checkerboard_has_more_high_freq_than_uniform,
    test_detail_handles_non_square_frame,
]


def run_all():
    print("=" * 60)
    print("  Content Analyzers Unit Tests")
    print("=" * 60)
    passed = 0
    failed = 0
    for test_fn in ALL_TESTS:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test_fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("=" * 60)
    print(f"  Results: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
