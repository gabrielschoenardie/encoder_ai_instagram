"""
enhance/analyzers/banding.py
============================
Banding analysis: histogram gaps, gradient quantization, flat region ratio.

All inputs: float32 [0.0–1.0] RGB frame (H, W, 3).
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class BandingResult:
    severity: float         # [0.0–1.0] composite banding severity
    gradient_score: float   # [0.0–1.0] gradient quantization artifact level
    flat_region_pct: float  # [0.0–1.0] fraction of frame with flat gradients


def analyze_banding(frame: np.ndarray) -> BandingResult:
    """
    Detect banding artifacts from a single float32 [0,1] RGB frame.

    Returns BandingResult with severity, gradient_score, flat_region_pct.
    """
    # Work in 8-bit luma space (banding is a quantization artifact)
    luma = 0.2126 * frame[..., 0] + 0.7152 * frame[..., 1] + 0.0722 * frame[..., 2]
    luma_8 = np.clip(luma * 255.0, 0, 255).astype(np.uint8)

    # ── Histogram gap score ───────────────────────────────────────────────────
    hist, _ = np.histogram(luma_8, bins=256, range=(0, 256))
    # Gaps: zero-count bins between non-zero bins in mid-tones (16–240)
    mid_hist = hist[16:240]
    nonzero_mask = mid_hist > 0
    if nonzero_mask.any():
        nz_indices = np.where(nonzero_mask)[0]
        span = int(nz_indices[-1] - nz_indices[0]) + 1
        gap_count = int(np.sum(mid_hist[nz_indices[0]:nz_indices[-1]+1] == 0))
        histogram_gap_score = float(gap_count / max(1, span))
    else:
        histogram_gap_score = 0.0

    # ── Gradient quantization score ───────────────────────────────────────────
    # DCT-based: banding produces discrete level transitions in smooth gradients
    # Use diff variance — high variance with low local std = quantization steps
    gy = np.diff(luma_8.astype(np.int16), axis=0)
    gx = np.diff(luma_8.astype(np.int16), axis=1)
    # Count pixels where |gradient| == 1 (quantization step boundary)
    step_y = float(np.mean(np.abs(gy) == 1))
    step_x = float(np.mean(np.abs(gx) == 1))
    gradient_score = float(np.clip((step_y + step_x) / 2.0, 0.0, 1.0))

    # ── Flat region percentage ────────────────────────────────────────────────
    # Regions where local std < threshold (candidate banding regions)
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(luma, size=8)
    local_sq_mean = uniform_filter(luma ** 2, size=8)
    local_var = np.clip(local_sq_mean - local_mean ** 2, 0.0, None)
    local_std = np.sqrt(local_var)
    flat_threshold = 0.02  # < 2% variation = flat region
    flat_region_pct = float(np.mean(local_std < flat_threshold))

    # ── Composite severity ────────────────────────────────────────────────────
    severity = float(np.clip(
        0.4 * histogram_gap_score +
        0.3 * gradient_score +
        0.3 * flat_region_pct,
        0.0, 1.0
    ))

    return BandingResult(
        severity=severity,
        gradient_score=gradient_score,
        flat_region_pct=flat_region_pct,
    )