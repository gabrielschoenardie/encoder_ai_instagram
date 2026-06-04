"""
enhance/test_mock_cnn.py
========================
Unit tests for MockCNN (Fase 27F).

Cenários:
    1. Clean content → all weights low (< 0.15)
    2. Noisy content → high denoise, sharpen suppressed
    3. Very noisy → denoise maximal, sharpen killed (NOISE_KILLS_SHARPEN)
    4. Compressed/banded → high deband
    5. Unsharp + clean → high sharpen
    6. Unsharp + noisy → sharpen suppressed by noise
    7. Interface contract: shape, dtype, range, name
    8. Error handling: wrong input shape
    9. Consistency: same input → same output (deterministic)

Run: python -m pytest enhance/test_mock_cnn.py -v
  or: python enhance/test_mock_cnn.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly: python enhance/test_mock_cnn.py
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from enhance.ai import EnhanceModel, MockCNN


def _make_features(
    sigma: float = 0.0,
    low_freq_ratio: float = 0.3,
    uniformity: float = 0.8,
    severity: float = 0.0,
    gradient_score: float = 0.1,
    flat_region_pct: float = 0.1,
    sharpness: float = 0.5,
    texture_complexity: float = 0.4,
    edge_density: float = 0.2,
    freq_low: float = 0.4,
    freq_mid: float = 0.3,
    freq_high: float = 0.2,
    detail_score: float = 0.5,
) -> np.ndarray:
    """Helper: build 13-dim feature vector from named parameters."""
    return np.array([
        sigma, low_freq_ratio, uniformity,
        severity, gradient_score, flat_region_pct,
        sharpness, texture_complexity, edge_density,
        freq_low, freq_mid, freq_high, detail_score,
    ], dtype=np.float32)


def test_interface_contract():
    """MockCNN implements EnhanceModel correctly."""
    model = MockCNN()
    assert isinstance(model, EnhanceModel), "MockCNN must inherit EnhanceModel"
    assert callable(model.predict), "predict must be callable"
    assert callable(model.name), "name must be callable"
    assert isinstance(model.name(), str), "name() must return str"
    assert len(model.name()) > 0, "name() must be non-empty"
    print("  [PASS] test_interface_contract")


def test_output_shape_dtype_range():
    """predict() returns shape (3,), float32, values in [0, 1]."""
    model = MockCNN()
    features = _make_features()
    out = model.predict(features)

    assert out.shape == (3,), f"Shape: expected (3,), got {out.shape}"
    assert out.dtype == np.float32, f"Dtype: expected float32, got {out.dtype}"
    assert np.all(out >= 0.0), f"Min value {out.min()} < 0.0"
    assert np.all(out <= 1.0), f"Max value {out.max()} > 1.0"
    print("  [PASS] test_output_shape_dtype_range")


def test_wrong_input_shape():
    """predict() raises ValueError for wrong input shape."""
    model = MockCNN()
    caught = False

    # Too few dimensions
    try:
        model.predict(np.zeros(10, dtype=np.float32))
    except ValueError:
        caught = True
    assert caught, "Should raise ValueError for shape (10,)"

    # Too many dimensions
    caught = False
    try:
        model.predict(np.zeros(20, dtype=np.float32))
    except ValueError:
        caught = True
    assert caught, "Should raise ValueError for shape (20,)"

    # 2D input
    caught = False
    try:
        model.predict(np.zeros((1, 13), dtype=np.float32))
    except ValueError:
        caught = True
    assert caught, "Should raise ValueError for shape (1, 13)"

    print("  [PASS] test_wrong_input_shape")


def test_clean_content():
    """Clean content (low noise, high sharpness, low banding) → all weights low."""
    model = MockCNN()
    features = _make_features(sigma=0.01, sharpness=0.90, severity=0.05)
    out = model.predict(features)

    assert out[0] < 0.15, f"Clean: denoise={out[0]:.4f} should be < 0.15"
    assert out[1] < 0.15, f"Clean: sharpen={out[1]:.4f} should be < 0.15"
    assert out[2] < 0.20, f"Clean: deband={out[2]:.4f} should be < 0.20"
    print(f"  [PASS] test_clean_content (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_noisy_content():
    """Noisy content → high denoise, sharpen suppressed."""
    model = MockCNN()
    features = _make_features(sigma=0.12, sharpness=0.40, severity=0.10)
    out = model.predict(features)

    assert out[0] > 0.60, f"Noisy: denoise={out[0]:.4f} should be > 0.60"
    assert out[1] < 0.10, f"Noisy: sharpen={out[1]:.4f} should be < 0.10 (noise kills)"
    print(f"  [PASS] test_noisy_content (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_very_noisy_sharpen_killed():
    """Very noisy (σ > NOISE_KILLS_SHARPEN=0.08) → sharpen strongly suppressed."""
    model = MockCNN()
    features = _make_features(sigma=0.20, sharpness=0.20, severity=0.10)
    out = model.predict(features)

    assert out[0] > 0.75, f"VeryNoisy: denoise={out[0]:.4f} should be > 0.75"
    assert out[1] < 0.10, f"VeryNoisy: sharpen={out[1]:.4f} should be < 0.10"
    print(f"  [PASS] test_very_noisy_sharpen_killed (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_compressed_banded():
    """Compressed/banded content → high deband weight."""
    model = MockCNN()
    features = _make_features(sigma=0.03, severity=0.70, sharpness=0.50)
    out = model.predict(features)

    assert out[2] > 0.60, f"Compressed: deband={out[2]:.4f} should be > 0.60"
    print(f"  [PASS] test_compressed_banded (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_severe_banding():
    """Severe banding (severity=0.90) → deband very high."""
    model = MockCNN()
    features = _make_features(sigma=0.02, severity=0.90, sharpness=0.50)
    out = model.predict(features)

    assert out[2] > 0.75, f"SevereBanding: deband={out[2]:.4f} should be > 0.75"
    print(f"  [PASS] test_severe_banding (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_unsharp_clean():
    """Clean but unsharp → high sharpen (noise doesn't kill)."""
    model = MockCNN()
    features = _make_features(sigma=0.01, sharpness=0.15, severity=0.05)
    out = model.predict(features)

    assert out[1] > 0.60, f"UnsharpClean: sharpen={out[1]:.4f} should be > 0.60"
    assert out[0] < 0.15, f"UnsharpClean: denoise={out[0]:.4f} should be < 0.15"
    print(f"  [PASS] test_unsharp_clean (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_unsharp_noisy():
    """Unsharp + noisy → sharpen suppressed despite low sharpness."""
    model = MockCNN()
    features = _make_features(sigma=0.12, sharpness=0.15, severity=0.05)
    out = model.predict(features)

    # Noise kills sharpen even though sharpness is low
    assert out[1] < 0.15, f"UnsharpNoisy: sharpen={out[1]:.4f} should be < 0.15"
    assert out[0] > 0.50, f"UnsharpNoisy: denoise={out[0]:.4f} should be > 0.50"
    print(f"  [PASS] test_unsharp_noisy (d={out[0]:.3f} s={out[1]:.3f} b={out[2]:.3f})")


def test_deterministic():
    """Same input → same output (no randomness)."""
    model = MockCNN()
    features = _make_features(sigma=0.07, sharpness=0.45, severity=0.35)
    out1 = model.predict(features)
    out2 = model.predict(features)
    assert np.array_equal(out1, out2), "predict() must be deterministic"
    print("  [PASS] test_deterministic")


def test_two_instances_agree():
    """Two MockCNN instances produce identical results."""
    m1 = MockCNN()
    m2 = MockCNN()
    features = _make_features(sigma=0.05, sharpness=0.60, severity=0.40)
    out1 = m1.predict(features)
    out2 = m2.predict(features)
    assert np.array_equal(out1, out2), "Different instances must agree"
    print("  [PASS] test_two_instances_agree")


# ── Runner ─────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_interface_contract,
    test_output_shape_dtype_range,
    test_wrong_input_shape,
    test_clean_content,
    test_noisy_content,
    test_very_noisy_sharpen_killed,
    test_compressed_banded,
    test_severe_banding,
    test_unsharp_clean,
    test_unsharp_noisy,
    test_deterministic,
    test_two_instances_agree,
]


def run_all():
    print("=" * 60)
    print("  MockCNN Unit Tests — FASE 27F-C")
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
