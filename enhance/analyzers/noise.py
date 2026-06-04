"""
enhance/analyzers/noise.py
==========================
Noise analysis: Gaussian high-pass sigma estimator, FFT low-frequency ratio,
adaptive-grid spatial uniformity.

All inputs: float32 [0.0–1.0] RGB frame (H, W, 3).

Upgrade notes (v2):
  sigma        — Gaussian high-pass (σ=1.0) + MAD / 0.6745.
                 hp = luma − LP isolates noise + fine detail.
                 Better noise/texture separation than Laplacian.
  low_freq_ratio — Circular FFT mask (radius = min(H,W)//8) on full luma.
                 Fraction of total power inside the low-freq disc.
                 Low → noise-dominant.  High → banding/DCT/gradients.
  uniformity   — Adaptive 8×8 grid (64 blocks).  At 1080p each block is
                 ~240×135 px; 4× more samples than the old 4×4 grid.
"""

from __future__ import annotations
import functools
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter


@functools.lru_cache(maxsize=8)
def _fft_mask(h: int, w: int) -> np.ndarray:
    """Boolean circular mask for the low-frequency disc in a centred FFT spectrum.

    Radius = min(h, w) // 8  (inner 12.5% of the shorter dimension).
    Cached by (h, w) — computed once per unique resolution.
    """
    cy, cx = h // 2, w // 2
    radius = min(h, w) // 8
    y, x = np.ogrid[:h, :w]
    return (y - cy) ** 2 + (x - cx) ** 2 <= radius ** 2


@dataclass
class NoiseResult:
    sigma: float           # [0.0–1.0] normalised noise sigma
    low_freq_ratio: float  # [0.0–1.0] fraction of residual energy at low freqs
    uniformity: float      # [0.0–1.0] spatial uniformity of noise (1 = uniform)


def analyze_noise(frame: np.ndarray) -> NoiseResult:
    """
    Estimate noise from a single float32 [0, 1] RGB frame.

    Returns NoiseResult with sigma, low_freq_ratio, uniformity.
    """
    # Convert to luma (Rec.709 coefficients)
    luma = (0.2126 * frame[..., 0]
            + 0.7152 * frame[..., 1]
            + 0.0722 * frame[..., 2])

    H, W = luma.shape

    # ── σ via Gaussian high-pass MAD estimator ───────────────────────────────
    # hp = luma − LP(σ=1.0): removes smooth structure, retains noise + fine detail.
    # MAD / 0.6745 → robust σ estimate (Gaussian distribution assumption).
    highpass = luma - gaussian_filter(luma, sigma=1.0)
    mad = np.median(np.abs(highpass - np.median(highpass)))
    sigma = float(mad / 0.6745)
    sigma = float(np.clip(sigma, 0.0, 1.0))

    # ── FFT low-frequency ratio — circular mask ───────────────────────────────
    # Centred power spectrum of full luma (fftshift moves DC to centre).
    # Circular mask radius = min(H,W)//8 isolates the low-freq disc.
    # Mask is cached by resolution — computed only once per unique (H, W).
    F_shift = np.fft.fftshift(np.fft.fft2(luma))
    power = np.abs(F_shift) ** 2
    mask = _fft_mask(H, W)
    low_energy = float(power[mask].sum())
    total_energy = float(power.sum()) + 1e-10
    low_freq_ratio = float(np.clip(low_energy / total_energy, 0.0, 1.0))

    # ── Spatial uniformity — adaptive 8×8 grid ────────────────────────────────
    # 64 blocks (vs old 4×4 = 16).  At 1080p each block ≈ 240×135 px.
    # CV (coefficient of variation) across block stds measures whether noise
    # is spatially homogeneous (film grain) or localised (compression patches).
    grid = 8
    bh, bw = max(1, H // grid), max(1, W // grid)
    block_sigmas = [
        float(np.std(luma[r * bh:(r + 1) * bh, c * bw:(c + 1) * bw]))
        for r in range(grid) for c in range(grid)
        if luma[r * bh:(r + 1) * bh, c * bw:(c + 1) * bw].size > 0
    ]
    if block_sigmas:
        mean_s = float(np.mean(block_sigmas)) + 1e-10
        cv = float(np.std(block_sigmas)) / mean_s
        uniformity = float(np.clip(1.0 - cv, 0.0, 1.0))
    else:
        uniformity = 1.0

    return NoiseResult(sigma=sigma, low_freq_ratio=low_freq_ratio, uniformity=uniformity)
