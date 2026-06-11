"""
enhance/test_profile.py
=======================
Unit tests for the heuristic decision matrix and AI-weights conversion in
``enhance/profile.py``.

These functions are the core of the enhancement signal chain: every filter
decision flows from ``_apply_decision_matrix`` (Fase 1 heuristics) or
``_weights_to_profile`` (Fase 2 AI path). Prior to this file they were only
exercised indirectly via processor/ffmpeg fixtures, so threshold regressions
were invisible.

Covered:
    1. Denoise activation across light / medium / strong thresholds
    2. Sharpen strong / gentle paths + NOISE_KILLS_SHARPEN suppression
    3. Deband+ light / strong thresholds
    4. Content classification (clean / noisy / compressed / mixed)
    5. Quality score bounds and direction
    6. AI weights → profile: activation gate, method selection, noise override
    7. Aggregation helpers + center-frame weighting

Run: python -m pytest enhance/test_profile.py -v
  or: python enhance/test_profile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly: python enhance/test_profile.py
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from enhance.profile import (
    BANDING_LIGHT_THR,
    NOISE_KILLS_SHARPEN,
    NOISE_LIGHT_THR,
    NOISE_MEDIUM_THR,
    BandingAgg,
    DetailAgg,
    NoiseAgg,
    _aggregate_banding,
    _aggregate_detail,
    _aggregate_noise,
    _classify_content,
    _compute_quality_score,
    _frame_weights,
    _weights_to_profile,
    build_enhance_profile_from_metrics,
)
from enhance.analyzers.noise import NoiseResult
from enhance.analyzers.banding import BandingResult
from enhance.analyzers.detail import DetailResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile(sigma=0.0, severity=0.0, sharpness=0.5, detail_score=0.5):
    """Build a profile from scalar metrics via the public heuristic API."""
    return build_enhance_profile_from_metrics(
        NoiseAgg(sigma=sigma),
        BandingAgg(severity=severity),
        DetailAgg(sharpness=sharpness, detail_score=detail_score),
    )


# ── Denoise decision ──────────────────────────────────────────────────────────

def test_denoise_off_when_clean():
    """σ below NOISE_LIGHT_THR → no denoise."""
    p = _profile(sigma=0.0)
    assert p.denoise_enabled is False
    assert p.denoise_method == "none"
    assert p.denoise_strength == 0.0


def test_denoise_off_just_below_light_threshold():
    """σ just below the light threshold stays off (boundary is strict >)."""
    p = _profile(sigma=NOISE_LIGHT_THR)
    assert p.denoise_enabled is False


def test_denoise_light_uses_gaussian():
    """NOISE_LIGHT_THR < σ < NOISE_MEDIUM_THR → light denoise via gaussian."""
    p = _profile(sigma=0.03)
    assert p.denoise_enabled is True
    assert p.denoise_method == "gaussian"
    assert 0.1 <= p.denoise_strength < 0.3


def test_denoise_medium_uses_bilateral():
    """NOISE_MEDIUM_THR < σ < NOISE_STRONG_THR → medium denoise via bilateral."""
    p = _profile(sigma=0.07)
    assert p.denoise_enabled is True
    assert p.denoise_method == "bilateral"
    assert 0.3 <= p.denoise_strength < 0.6


def test_denoise_strong_uses_nlmeans():
    """σ > NOISE_STRONG_THR → strong denoise via nlmeans."""
    p = _profile(sigma=0.15)
    assert p.denoise_enabled is True
    assert p.denoise_method == "nlmeans"
    assert p.denoise_strength >= 0.6


def test_denoise_strength_saturates_at_one():
    """Extreme σ must clamp strength to 1.0 (no overshoot)."""
    p = _profile(sigma=0.9)
    assert p.denoise_strength <= 1.0
    assert p.denoise_strength == 1.0


def test_denoise_strength_monotonic_with_sigma():
    """Higher noise → higher denoise strength across the full range."""
    strengths = [_profile(sigma=s).denoise_strength for s in (0.03, 0.07, 0.15, 0.30)]
    assert strengths == sorted(strengths)


# ── Sharpen decision ──────────────────────────────────────────────────────────

def test_sharpen_strong_when_very_soft():
    """sharpness < SHARP_NEEDED_THR → strong sharpen, radius 2.0."""
    p = _profile(sigma=0.0, sharpness=0.2)
    assert p.sharpen_enabled is True
    assert p.sharpen_radius == 2.0
    assert p.sharpen_strength >= 0.5


def test_sharpen_gentle_when_moderately_soft_and_clean():
    """SHARP_NEEDED_THR < sharpness < SHARP_OK_THR and low noise → gentle sharpen."""
    p = _profile(sigma=0.0, sharpness=0.5)
    assert p.sharpen_enabled is True
    assert p.sharpen_radius == 1.0
    assert 0.2 <= p.sharpen_strength < 0.5


def test_sharpen_off_when_already_sharp():
    """sharpness >= SHARP_OK_THR → no sharpen needed."""
    p = _profile(sigma=0.0, sharpness=0.9)
    assert p.sharpen_enabled is False


def test_sharpen_gentle_requires_low_noise():
    """Gentle path is gated on σ <= NOISE_LIGHT_THR: moderate noise blocks it."""
    # sharpness in the gentle band, but noise above light threshold (yet below kill)
    p = _profile(sigma=0.04, sharpness=0.5)
    assert p.sharpen_enabled is False


def test_noise_kills_sharpen():
    """σ > NOISE_KILLS_SHARPEN disables sharpen even for very soft content."""
    p = _profile(sigma=NOISE_KILLS_SHARPEN + 0.01, sharpness=0.1)
    assert p.sharpen_enabled is False
    assert any("noise kills" in r for r in p.reasons)


# ── Deband+ decision ──────────────────────────────────────────────────────────

def test_deband_off_when_no_banding():
    p = _profile(severity=0.0)
    assert p.deband_enhance_enabled is False
    assert p.deband_strength == 0.0


def test_deband_light_threshold():
    """BANDING_LIGHT_THR < severity < BANDING_STRONG_THR → light deband+."""
    p = _profile(severity=0.45)
    assert p.deband_enhance_enabled is True
    assert 0.2 <= p.deband_strength < 0.6


def test_deband_strong_threshold():
    """severity > BANDING_STRONG_THR → strong deband+."""
    p = _profile(severity=0.8)
    assert p.deband_enhance_enabled is True
    assert p.deband_strength >= 0.6


def test_deband_strength_within_bounds():
    """Maximum severity must keep deband strength <= 1.0."""
    p = _profile(severity=1.0)
    assert p.deband_strength <= 1.0


# ── Content classification ──────────────────────────────────────────────────

def test_classify_compressed_takes_priority():
    """Banding above light threshold classifies as compressed regardless of noise."""
    ct = _classify_content(
        NoiseAgg(sigma=0.20),  # also noisy, but banding wins
        BandingAgg(severity=BANDING_LIGHT_THR + 0.01),
        DetailAgg(sharpness=0.9),
    )
    assert ct == "compressed"


def test_classify_noisy():
    ct = _classify_content(
        NoiseAgg(sigma=NOISE_MEDIUM_THR + 0.01),
        BandingAgg(severity=0.0),
        DetailAgg(sharpness=0.9),
    )
    assert ct == "noisy"


def test_classify_clean():
    ct = _classify_content(
        NoiseAgg(sigma=0.0),
        BandingAgg(severity=0.0),
        DetailAgg(sharpness=0.7),
    )
    assert ct == "clean"


def test_classify_mixed_fallback():
    """Low-ish noise, no banding, but soft → falls through to mixed."""
    ct = _classify_content(
        NoiseAgg(sigma=0.0),
        BandingAgg(severity=0.0),
        DetailAgg(sharpness=0.4),  # not > 0.6, so not "clean"
    )
    assert ct == "mixed"


def test_compressed_enables_deblock():
    """A compressed classification must turn on deblock in the public builder."""
    p = build_enhance_profile_from_metrics(
        NoiseAgg(sigma=0.0),
        BandingAgg(severity=BANDING_LIGHT_THR + 0.05),
        DetailAgg(sharpness=0.9),
    )
    assert p.content_type == "compressed"
    assert p.deblock_enabled is True


# ── Quality score ─────────────────────────────────────────────────────────────

def test_quality_score_in_range():
    for sigma in (0.0, 0.05, 0.15, 0.5):
        for sev in (0.0, 0.5, 1.0):
            q = _compute_quality_score(
                NoiseAgg(sigma=sigma), BandingAgg(severity=sev), DetailAgg(detail_score=0.5)
            )
            assert 0.0 <= q <= 1.0


def test_quality_clean_better_than_degraded():
    """Clean, detailed content should score higher than noisy + banded content."""
    clean = _compute_quality_score(
        NoiseAgg(sigma=0.0), BandingAgg(severity=0.0), DetailAgg(detail_score=0.8)
    )
    degraded = _compute_quality_score(
        NoiseAgg(sigma=0.15), BandingAgg(severity=0.8), DetailAgg(detail_score=0.0)
    )
    assert clean > degraded


# ── AI weights → profile (Fase 2) ────────────────────────────────────────────

def _ai_profile(denoise_w, sharpen_w, deband_w, sigma=0.0, severity=0.0):
    return _weights_to_profile(
        np.array([denoise_w, sharpen_w, deband_w], dtype=np.float32),
        NoiseAgg(sigma=sigma),
        BandingAgg(severity=severity),
        DetailAgg(sharpness=0.5, detail_score=0.5),
        model_name="MockTest",
    )


def test_ai_activation_gate_disables_low_weights():
    """Weights at/below the activation threshold produce no enhancement."""
    p = _ai_profile(0.05, 0.05, 0.05)
    assert p.denoise_enabled is False
    assert p.sharpen_enabled is False
    assert p.deband_enhance_enabled is False


def test_ai_denoise_method_by_weight_magnitude():
    """Denoise method is selected from the weight magnitude bands."""
    assert _ai_profile(0.2, 0, 0).denoise_method == "gaussian"
    assert _ai_profile(0.45, 0, 0).denoise_method == "bilateral"
    assert _ai_profile(0.9, 0, 0).denoise_method == "nlmeans"


def test_ai_sharpen_strength_and_radius_scale():
    """Sharpen strength = w*0.5 and radius = 1.0 + w."""
    p = _ai_profile(0, 0.8, 0)
    assert p.sharpen_enabled is True
    assert abs(p.sharpen_strength - 0.4) < 1e-6
    assert abs(p.sharpen_radius - 1.8) < 1e-6


def test_ai_noise_override_beats_high_sharpen_weight():
    """NOISE_KILLS_SHARPEN must override even a confident AI sharpen weight."""
    p = _ai_profile(0, 0.99, 0, sigma=NOISE_KILLS_SHARPEN + 0.01)
    assert p.sharpen_enabled is False
    assert any("noise_kills overrides" in r for r in p.reasons)


def test_ai_deband_enables_deblock_for_compressed():
    """High deband weight + banding metric → compressed classification + deblock."""
    p = _ai_profile(0, 0, 0.8, severity=BANDING_LIGHT_THR + 0.05)
    assert p.deband_enhance_enabled is True
    assert p.content_type == "compressed"
    assert p.deblock_enabled is True


def test_ai_model_name_recorded():
    p = _ai_profile(0.5, 0, 0)
    assert any(r == "ai_model=MockTest" for r in p.reasons)


# ── Aggregation helpers ──────────────────────────────────────────────────────

def test_frame_weights_single_frame():
    assert _frame_weights(1) == [1.0]


def test_frame_weights_center_dominance():
    w = _frame_weights(5)
    assert len(w) == 5
    assert w[2] == 2.0  # center frame doubled
    assert w.count(1.0) == 4


def test_aggregate_noise_weighted_mean():
    """Center frame's value should dominate the weighted aggregate."""
    results = [
        NoiseResult(sigma=0.0, low_freq_ratio=0.0, uniformity=1.0),
        NoiseResult(sigma=0.0, low_freq_ratio=0.0, uniformity=1.0),
        NoiseResult(sigma=1.0, low_freq_ratio=0.0, uniformity=1.0),  # center
        NoiseResult(sigma=0.0, low_freq_ratio=0.0, uniformity=1.0),
        NoiseResult(sigma=0.0, low_freq_ratio=0.0, uniformity=1.0),
    ]
    agg = _aggregate_noise(results, _frame_weights(5))
    # center weight 2 of total 6 → 2/6
    assert abs(agg.sigma - (2.0 / 6.0)) < 1e-9


def test_aggregate_uniform_results_passthrough():
    """Aggregating identical results returns that same value."""
    b = [BandingResult(severity=0.4, gradient_score=0.2, flat_region_pct=0.1)] * 3
    agg = _aggregate_banding(b, _frame_weights(3))
    assert abs(agg.severity - 0.4) < 1e-9
    assert abs(agg.gradient_score - 0.2) < 1e-9

    d = [DetailResult(0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.6)] * 3
    dagg = _aggregate_detail(d, _frame_weights(3))
    assert abs(dagg.sharpness - 0.5) < 1e-9
    assert abs(dagg.detail_score - 0.6) < 1e-9


# ── Test harness (mirrors test_mock_cnn.py) ──────────────────────────────────

ALL_TESTS = [
    test_denoise_off_when_clean,
    test_denoise_off_just_below_light_threshold,
    test_denoise_light_uses_gaussian,
    test_denoise_medium_uses_bilateral,
    test_denoise_strong_uses_nlmeans,
    test_denoise_strength_saturates_at_one,
    test_denoise_strength_monotonic_with_sigma,
    test_sharpen_strong_when_very_soft,
    test_sharpen_gentle_when_moderately_soft_and_clean,
    test_sharpen_off_when_already_sharp,
    test_sharpen_gentle_requires_low_noise,
    test_noise_kills_sharpen,
    test_deband_off_when_no_banding,
    test_deband_light_threshold,
    test_deband_strong_threshold,
    test_deband_strength_within_bounds,
    test_classify_compressed_takes_priority,
    test_classify_noisy,
    test_classify_clean,
    test_classify_mixed_fallback,
    test_compressed_enables_deblock,
    test_quality_score_in_range,
    test_quality_clean_better_than_degraded,
    test_ai_activation_gate_disables_low_weights,
    test_ai_denoise_method_by_weight_magnitude,
    test_ai_sharpen_strength_and_radius_scale,
    test_ai_noise_override_beats_high_sharpen_weight,
    test_ai_deband_enables_deblock_for_compressed,
    test_ai_model_name_recorded,
    test_frame_weights_single_frame,
    test_frame_weights_center_dominance,
    test_aggregate_noise_weighted_mean,
    test_aggregate_uniform_results_passthrough,
]


def run_all():
    print("=" * 60)
    print("  EnhanceProfile Decision Matrix Tests")
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
