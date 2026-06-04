"""
enhance/ai/mock_cnn.py
======================
Mock CNN model for enhancement decisions (Fase 27F).

Architecture:
    Input (13) → Linear(13→8) → Sigmoid → Linear(8→3) → Sigmoid → Output (3)

This is NOT a trained model. Weights are hand-calibrated to approximate the
heuristic decision matrix from Fase 1 (_apply_decision_matrix). The purpose
is to validate the AI pipeline interface before a real model is trained.

Hidden neurons (semantic roles):
    h0: noise_high       — fires when σ > ~0.10 (NOISE_STRONG_THR)
    h1: noise_medium     — fires when σ > ~0.05 (NOISE_MEDIUM_THR)
    h2: noise_kills      — fires when σ > ~0.08 (NOISE_KILLS_SHARPEN)
    h3: needs_sharpen    — fires when sharpness < ~0.30 (SHARP_NEEDED_THR)
    h4: sharp_ok         — fires when sharpness > ~0.80 (SHARP_OK_THR)
    h5: banding_high     — fires when severity > ~0.60 (BANDING_STRONG_THR)
    h6: banding_moderate — fires when severity > ~0.30 (BANDING_LIGHT_THR)
    h7: clean_content    — fires when σ low + sharpness high + severity low

Output mapping:
    [0] denoise_weight  ← h0 + h1 (excite), h7 (inhibit)
    [1] sharpen_weight  ← h3 (excite), h2 + h4 (inhibit)
    [2] deband_weight   ← h5 + h6 (excite), h7 (inhibit)

Inference: ~0.01ms per call (pure NumPy matmul + sigmoid).
Swap path: Replace this file with real_model.py implementing EnhanceModel.
"""

from __future__ import annotations

import numpy as np

from .interface import EnhanceModel


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


class MockCNN(EnhanceModel):
    """
    2-layer sigmoid mock model with fixed pre-calibrated weights.

    Approximates the Fase 1 heuristic decision matrix:
        - sigma > thresholds → denoise weight increases
        - sigma > NOISE_KILLS_SHARPEN → sharpen suppressed
        - sharpness < thresholds → sharpen weight increases
        - banding severity > thresholds → deband weight increases
        - Clean content (low σ, high sharpness, low severity) → all weights ≈ 0
    """

    def __init__(self) -> None:
        super().__init__()

        # ── Layer 1: Linear(13→8) ──────────────────────────────────────────
        # W1[i, j] = weight from feature j to hidden neuron i
        # Features: [σ, lf_ratio, uniformity, severity, grad_score, flat_pct,
        #            sharpness, texture, edges, freq_low, freq_mid, freq_high,
        #            detail_score]
        # Indices:   0  1          2           3         4          5
        #            6          7        8      9         10        11
        #            12

        self._W1 = np.zeros((8, 13), dtype=np.float32)
        self._b1 = np.zeros(8, dtype=np.float32)

        # h0: noise_high — sigmoid transition at σ ≈ 0.10
        self._W1[0, 0] = 40.0
        self._b1[0] = -4.0  # 40 * 0.10 = 4.0 → centered at σ=0.10

        # h1: noise_medium — sigmoid transition at σ ≈ 0.05
        self._W1[1, 0] = 40.0
        self._b1[1] = -2.0  # 40 * 0.05 = 2.0 → centered at σ=0.05

        # h2: noise_kills_sharpen — sigmoid transition at σ ≈ 0.08
        self._W1[2, 0] = 50.0
        self._b1[2] = -4.0  # 50 * 0.08 = 4.0 → centered at σ=0.08

        # h3: needs_sharpen — sigmoid transition at sharpness ≈ 0.30 (inverted)
        self._W1[3, 6] = -20.0
        self._b1[3] = 6.0   # -20 * 0.30 + 6 = 0 → centered at sharpness=0.30

        # h4: sharp_ok — sigmoid transition at sharpness ≈ 0.80
        self._W1[4, 6] = 15.0
        self._b1[4] = -12.0  # 15 * 0.80 = 12 → centered at sharpness=0.80

        # h5: banding_high — sigmoid transition at severity ≈ 0.60
        self._W1[5, 3] = 10.0
        self._b1[5] = -6.0  # 10 * 0.60 = 6 → centered at severity=0.60

        # h6: banding_moderate — sigmoid transition at severity ≈ 0.30
        self._W1[6, 3] = 10.0
        self._b1[6] = -3.0  # 10 * 0.30 = 3 → centered at severity=0.30

        # h7: clean_content — fires when σ low, sharpness high, severity low
        self._W1[7, 0] = -30.0   # penalize noise
        self._W1[7, 3] = -8.0    # penalize banding
        self._W1[7, 6] = 8.0     # reward sharpness
        self._b1[7] = -2.0

        # ── Layer 2: Linear(8→3) ──────────────────────────────────────────
        # W2[i, j] = weight from hidden neuron j to output i
        # Hidden: [h0_noise_hi, h1_noise_med, h2_noise_kills, h3_need_sharp,
        #          h4_sharp_ok, h5_band_hi, h6_band_mod, h7_clean]

        self._W2 = np.zeros((3, 8), dtype=np.float32)
        self._b2 = np.zeros(3, dtype=np.float32)

        # Output 0: denoise_weight ← h0 + h1 excite, h7 inhibits
        # Stronger noise dependency + more negative bias = requires actual
        # noise signal before triggering (fixes false positive on unsharp clean)
        self._W2[0, 0] = 2.5    # noise_high → strong denoise
        self._W2[0, 1] = 1.5    # noise_medium → moderate denoise
        self._W2[0, 7] = -1.0   # clean → mild suppress
        self._b2[0] = -2.0

        # Output 1: sharpen_weight ← h3 excites, h2 + h4 inhibit
        self._W2[1, 2] = -5.0   # noise_kills → strong suppression
        self._W2[1, 3] = 3.0    # needs_sharpen → excite
        self._W2[1, 4] = -2.0   # sharp_ok → suppress
        self._b2[1] = -0.5

        # Output 2: deband_weight ← h5 + h6 excite, h7 inhibits
        self._W2[2, 5] = 1.5    # banding_high → strong deband
        self._W2[2, 6] = 1.2    # banding_moderate → moderate deband
        self._W2[2, 7] = -1.0   # clean → suppress deband
        self._b2[2] = -1.4      # Fix: clean content deband 0.131→0.092 (abaixo de _AI_ACTIVATION_THR=0.1)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        13-dim input → 3-dim output [0, 1].

        Args:
            features: shape (13,), dtype float32

        Returns:
            shape (3,), dtype float32, values in [0.0, 1.0]
                [denoise_weight, sharpen_weight, deband_weight]

        Raises:
            ValueError: if features shape is not (13,)
        """
        features = np.asarray(features, dtype=np.float32)
        if features.shape != (self.FEATURE_DIM,):
            raise ValueError(
                f"Expected feature vector shape ({self.FEATURE_DIM},), "
                f"got {features.shape}"
            )

        # Layer 1: hidden = sigmoid(W1 @ features + b1)
        hidden = _sigmoid(self._W1 @ features + self._b1)

        # Layer 2: output = sigmoid(W2 @ hidden + b2)
        output = _sigmoid(self._W2 @ hidden + self._b2)

        return output.astype(np.float32)

    def name(self) -> str:
        return "MockCNN_v1_sigmoid_2layer"
