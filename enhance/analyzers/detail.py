"""
enhance/analyzers/detail.py
===========================
Detail / sharpness analysis: Laplacian variance, texture complexity, edge density,
frequency band decomposition (low / mid / high).

All inputs: float32 [0.0–1.0] RGB frame (H, W, 3).
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class DetailResult:
    sharpness: float           # [0.0–1.0] Laplacian variance normalised
    texture_complexity: float  # [0.0–1.0] local texture richness
    edge_density: float        # [0.0–1.0] fraction of pixels on edges
    freq_low: float            # [0.0–1.0] relative low-freq energy
    freq_mid: float            # [0.0–1.0] relative mid-freq energy
    freq_high: float           # [0.0–1.0] relative high-freq energy
    detail_score: float        # [0.0–1.0] composite detail score


def analyze_detail(frame: np.ndarray) -> DetailResult:
    """
    Analyse spatial detail from a single float32 [0,1] RGB frame.
    """
    from scipy.ndimage import gaussian_filter, sobel

    luma = 0.2126 * frame[..., 0] + 0.7152 * frame[..., 1] + 0.0722 * frame[..., 2]

    # ── Sharpness via Laplacian variance ────────────────────────────────────
    laplacian_k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    from scipy.ndimage import convolve
    lap = convolve(luma, laplacian_k, mode='reflect')
    lap_var = float(np.var(lap))
    # Normalise: empirically ~0.001 = very soft, ~0.01+ = sharp
    sharpness = float(np.clip(lap_var / 0.015, 0.0, 1.0))

    # ── Edge density via Sobel ───────────────────────────────────────────────
    sx = sobel(luma, axis=1)
    sy = sobel(luma, axis=0)
    edge_mag = np.hypot(sx, sy)
    edge_threshold = 0.05
    edge_density = float(np.mean(edge_mag > edge_threshold))

    # ── Texture complexity via local std ────────────────────────────────────
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(luma, size=7)
    local_sq = uniform_filter(luma ** 2, size=7)
    local_var = np.clip(local_sq - local_mean ** 2, 0.0, None)
    texture_complexity = float(np.clip(np.mean(np.sqrt(local_var)) * 10.0, 0.0, 1.0))

    # ── Frequency band decomposition ─────────────────────────────────────────
    # Low: σ=8, Mid: σ=2–8, High: < σ=2
    low_pass_8 = gaussian_filter(luma, sigma=8.0)
    low_pass_2 = gaussian_filter(luma, sigma=2.0)
    low_band = low_pass_8
    mid_band = low_pass_2 - low_pass_8
    high_band = luma - low_pass_2

    total_energy = float(np.mean(luma ** 2)) + 1e-10
    freq_low = float(np.clip(np.mean(low_band ** 2) / total_energy, 0.0, 1.0))
    freq_mid = float(np.clip(np.mean(mid_band ** 2) / total_energy, 0.0, 1.0))
    freq_high = float(np.clip(np.mean(high_band ** 2) / total_energy, 0.0, 1.0))

    # ── Composite detail score ───────────────────────────────────────────────
    detail_score = float(np.clip(
        0.4 * sharpness +
        0.3 * texture_complexity +
        0.3 * edge_density,
        0.0, 1.0
    ))

    return DetailResult(
        sharpness=sharpness,
        texture_complexity=texture_complexity,
        edge_density=edge_density,
        freq_low=freq_low,
        freq_mid=freq_mid,
        freq_high=freq_high,
        detail_score=detail_score,
    )