"""
enhance/processor.py
====================
FASE 27D — Per-frame enhancement processor for Cineon pipeline (Mode 2).

Public API:
    fn = get_enhance_fn(profile)   # None if nothing to do → zero overhead
    if fn is not None:
        frame = fn(frame)          # float32 [0,1] RGB in-place compatible

Frame contract:
    - Input:  np.ndarray shape (H, W, 3), dtype float32, values [0.0–1.0]
    - Output: np.ndarray shape (H, W, 3), dtype float32, values [0.0–1.0]
    - Colour space: Rec.709 gamma (pre-Cineon, post-resize)

Pipeline order (always):
    denoise → deband_smooth → sharpen

Rationale for order:
    1. Denoise first — removes random noise before edge-sensitive operations.
    2. Deband smooth — gradient reconstruction on flat regions (edge-protected).
    3. Sharpen last — amplifies clean edges, never amplifies noise residuals.

Dependencies: NumPy (always), OpenCV (bilateral/nlmeans), SciPy (gaussian).
OpenCV and SciPy are imported lazily inside each filter to keep import cost zero
when the enhancement engine is instantiated but no video is processed yet.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import numpy as np

from .profile import EnhanceProfile

logger = logging.getLogger(__name__)

# ── Internal constants ────────────────────────────────────────────────────────

# Bilateral filter parameters (d=0 → computed from sigma_space)
_BILATERAL_D = 0           # diameter: 0 means auto-compute from sigma_space
_BILATERAL_SIGMA_COLOR_SCALE = 0.15   # sigma_color = strength * scale (float32)
_BILATERAL_SIGMA_SPACE_BASE = 5.0     # sigma_space baseline (pixels)
_BILATERAL_SIGMA_SPACE_SCALE = 5.0    # extra space sigma from strength

# NLMeans parameters
_NLM_H_SCALE = 0.12        # h = strength * scale (search window energy)
_NLM_TEMPLATE_WINDOW = 7   # pixels
_NLM_SEARCH_WINDOW = 21    # pixels

# Gaussian denoising
_GAUSSIAN_SIGMA_SCALE = 3.0  # sigma = strength * scale

# Unsharp mask
_SHARPEN_BLUR_SIGMA_BASE = 1.0    # base sigma for blurring step
_SHARPEN_BLUR_SIGMA_SCALE = 1.0   # extra sigma from radius param
_SHARPEN_AMOUNT_SCALE = 1.5       # amount = strength * scale

# Adaptive deband — heatmap-guided
_ADAPTIVE_DEBAND_GRAD_SIGMA  = 1.0   # pre-smooth luma before gradient (isolates noise)
_ADAPTIVE_DEBAND_VAR_SIZE    = 7     # local variance window (aligned with banding.py)
_ADAPTIVE_DEBAND_TEX_THR     = 0.015 # Laplacian energy > thr → texture → protect
_ADAPTIVE_DEBAND_MASK_SMOOTH = 8.0   # mask Gaussian sigma (cinematic soft transitions)
_ADAPTIVE_DEBAND_SIGMA_SCALE = 5.0   # smooth_sigma = strength * scale
_ADAPTIVE_DEBAND_SIGMA_MAX   = 7.0   # max deband Gaussian sigma
_LAPLACIAN_K = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)


# ── Banding heatmap helper ────────────────────────────────────────────────────

def _banding_heatmap(luma: np.ndarray) -> np.ndarray:
    """
    Float32 [0,1] spatial banding risk map. HIGH = banding risk.

    Same logic as codec_lab_analyzer.banding_map() but:
    - pure float32 (no uint8 round-trip)
    - percentile p99 normalisation (robust to outliers)
    - pre-smoothed luma to isolate banding vs noise
    """
    from scipy.ndimage import sobel, uniform_filter, gaussian_filter

    luma_sm = gaussian_filter(luma, sigma=_ADAPTIVE_DEBAND_GRAD_SIGMA)

    gx = sobel(luma_sm, axis=1)
    gy = sobel(luma_sm, axis=0)
    grad = np.hypot(gx, gy)

    luma_sq   = uniform_filter(luma_sm ** 2, size=_ADAPTIVE_DEBAND_VAR_SIZE)
    luma_m    = uniform_filter(luma_sm,      size=_ADAPTIVE_DEBAND_VAR_SIZE)
    local_std = np.sqrt(np.clip(luma_sq - luma_m ** 2, 0.0, None))

    p99_g = float(np.percentile(grad,      99)) + 1e-10
    p99_s = float(np.percentile(local_std, 99)) + 1e-10
    grad_n = np.clip(grad      / p99_g, 0.0, 1.0)
    std_n  = np.clip(local_std / p99_s, 0.0, 1.0)

    # Low gradient + low variance → banding risk (HIGH value)
    return (1.0 - np.clip(0.6 * grad_n + 0.4 * std_n, 0.0, 1.0)).astype(np.float32)


# ── Denoise filters ───────────────────────────────────────────────────────────

def _apply_denoise(
    frame: np.ndarray,
    strength: float,
    method: str,
) -> np.ndarray:
    """
    Apply denoise filter to float32 [0,1] RGB frame.

    Args:
        frame:    (H, W, 3) float32 [0,1]
        strength: [0.0–1.0] from EnhanceProfile.denoise_strength
        method:   "nlmeans" | "bilateral" | "gaussian"

    Returns:
        Denoised frame (same shape, float32 [0,1]).
    """
    if method == "nlmeans":
        return _denoise_nlmeans(frame, strength)
    elif method == "bilateral":
        return _denoise_bilateral(frame, strength)
    else:  # "gaussian" or fallback
        return _denoise_gaussian(frame, strength)


def _denoise_nlmeans(frame: np.ndarray, strength: float) -> np.ndarray:
    """NLMeans via OpenCV fastNlMeansDenoisingColored on uint8 proxy."""
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not available; falling back to Gaussian denoise.")
        return _denoise_gaussian(frame, strength)

    # Convert to uint8 [0,255] for OpenCV
    frame_u8 = np.clip(frame * 255.0, 0, 255).astype(np.uint8)

    # h parameter: filter strength in [1, 30] range for uint8 space
    h = float(np.clip(strength * _NLM_H_SCALE * 255.0, 1.0, 30.0))
    hColor = h * 0.8  # slightly less aggressive on chroma

    denoised_u8 = cv2.fastNlMeansDenoisingColored(
        frame_u8,
        None,
        h=h,
        hColor=hColor,
        templateWindowSize=_NLM_TEMPLATE_WINDOW,
        searchWindowSize=_NLM_SEARCH_WINDOW,
    )
    return denoised_u8.astype(np.float32) / 255.0


def _denoise_bilateral(frame: np.ndarray, strength: float) -> np.ndarray:
    """Bilateral filter via OpenCV — edge-preserving denoise."""
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not available; falling back to Gaussian denoise.")
        return _denoise_gaussian(frame, strength)

    # OpenCV bilateralFilter operates on uint8 or float32
    # Using float32 directly to avoid quantisation round-trip
    sigma_color = float(np.clip(strength * _BILATERAL_SIGMA_COLOR_SCALE, 0.01, 0.5))
    sigma_space = float(_BILATERAL_SIGMA_SPACE_BASE + strength * _BILATERAL_SIGMA_SPACE_SCALE)

    # bilateralFilter expects values in [0, 255] space when dtype is float32
    # We work in [0,1] but pass sigma_color scaled accordingly
    # → work in uint8 space for reliable behaviour across platforms
    frame_u8 = np.clip(frame * 255.0, 0, 255).astype(np.uint8)
    sigma_color_u8 = sigma_color * 255.0

    denoised_u8 = cv2.bilateralFilter(
        frame_u8,
        d=_BILATERAL_D,
        sigmaColor=sigma_color_u8,
        sigmaSpace=sigma_space,
    )
    return denoised_u8.astype(np.float32) / 255.0


def _denoise_gaussian(frame: np.ndarray, strength: float) -> np.ndarray:
    """Gaussian smoothing via SciPy ndimage (fallback / light denoise)."""
    from scipy.ndimage import gaussian_filter
    sigma = float(np.clip(strength * _GAUSSIAN_SIGMA_SCALE, 0.1, 3.0))
    # Apply per-channel
    result = np.stack([
        gaussian_filter(frame[..., c], sigma=sigma)
        for c in range(3)
    ], axis=-1)
    return result.astype(np.float32)


# ── Deband smooth ─────────────────────────────────────────────────────────────

def _apply_deband_smooth(
    frame: np.ndarray,
    strength: float,
) -> np.ndarray:
    """
    Adaptive debanding guided by spatial banding heatmap.

    1. banding_map  — float32 [0,1]: HIGH where banding risk exists (low grad + low var)
    2. texture_mask — float32 [0,1]: HIGH where texture exists (Laplacian) → protect
    3. deband_mask  = banding_map * (1 − texture_mask): spatial blend weight
    4. Gaussian-smooth the mask → cinematic soft transitions, no hard block edges
    5. Blend: frame * (1 − mask) + gaussian_smoothed * mask

    Args:
        frame:    (H, W, 3) float32 [0,1]
        strength: [0.0–1.0] from EnhanceProfile.deband_strength

    Returns:
        Frame with adaptive heatmap-guided deband applied (same shape, float32 [0,1]).
    """
    from scipy.ndimage import gaussian_filter, convolve

    luma = (0.2126 * frame[..., 0]
            + 0.7152 * frame[..., 1]
            + 0.0722 * frame[..., 2])

    # ── 1. Spatial banding heatmap ────────────────────────────────────────────
    band_map = _banding_heatmap(luma)

    # ── 2. Texture protection (Laplacian energy) ──────────────────────────────
    lap = convolve(luma, _LAPLACIAN_K, mode='reflect')
    tex_mask = np.clip(np.abs(lap) / _ADAPTIVE_DEBAND_TEX_THR, 0.0, 1.0)

    # ── 3. Adaptive deband mask ───────────────────────────────────────────────
    raw_mask    = band_map * (1.0 - tex_mask)
    smooth_mask = gaussian_filter(raw_mask, sigma=_ADAPTIVE_DEBAND_MASK_SMOOTH)
    deband_mask = np.clip(smooth_mask * strength, 0.0, 1.0)

    if float(deband_mask.max()) < 0.005:
        return frame

    # ── 4. Gaussian smooth per channel ───────────────────────────────────────
    sigma = float(np.clip(
        strength * _ADAPTIVE_DEBAND_SIGMA_SCALE, 0.5, _ADAPTIVE_DEBAND_SIGMA_MAX
    ))
    smoothed = np.stack(
        [gaussian_filter(frame[..., c], sigma=sigma) for c in range(3)], axis=-1
    )

    # ── 5. Spatial blend ─────────────────────────────────────────────────────
    mask3 = deband_mask[..., np.newaxis]
    return np.clip(
        frame * (1.0 - mask3) + smoothed * mask3, 0.0, 1.0
    ).astype(np.float32)


# ── Perceptual sharpen ────────────────────────────────────────────────────────

def _apply_perceptual_sharpen(
    frame: np.ndarray,
    strength: float,
    radius: float,
) -> np.ndarray:
    """
    Perceptual unsharp mask — high-frequency selective boost.

    Operates entirely in float32 space; no uint8 round-trip.
    Uses frequency-selective mask to avoid amplifying noise residuals:
    only boosts mid-to-high frequencies above a local contrast threshold.

    Args:
        frame:    (H, W, 3) float32 [0,1]
        strength: [0.0–1.0] from EnhanceProfile.sharpen_strength
        radius:   [1.0–2.0] from EnhanceProfile.sharpen_radius

    Returns:
        Sharpened frame (same shape, float32 [0,1]).
    """
    from scipy.ndimage import gaussian_filter

    blur_sigma = float(_SHARPEN_BLUR_SIGMA_BASE + radius * _SHARPEN_BLUR_SIGMA_SCALE)
    amount = float(strength * _SHARPEN_AMOUNT_SCALE)

    # Unsharp mask: result = original + amount * (original - blur)
    result_channels = []
    for c in range(3):
        ch = frame[..., c]
        blurred = gaussian_filter(ch, sigma=blur_sigma)
        detail = ch - blurred

        # Perceptual gate: only sharpen where local contrast is meaningful
        # (avoids amplifying flat noise)
        local_contrast = np.abs(detail)
        contrast_gate = np.clip(local_contrast / 0.02, 0.0, 1.0)  # soft gate

        sharpened = ch + amount * detail * contrast_gate
        result_channels.append(sharpened)

    result = np.stack(result_channels, axis=-1)
    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ── Public API ────────────────────────────────────────────────────────────────

def get_enhance_fn(
    profile: EnhanceProfile,
) -> Optional[Callable[[np.ndarray], np.ndarray]]:
    """
    Build and return a per-frame enhancement function from an EnhanceProfile.

    Returns None if no enhancement is needed (zero overhead in the encode loop).

    The returned callable:
        - Accepts:  np.ndarray (H, W, 3) float32 [0.0–1.0] — Rec.709 gamma
        - Returns:  np.ndarray (H, W, 3) float32 [0.0–1.0] — same colour space
        - Is safe to call per-frame inside the Cineon PyAV encode loop.

    Pipeline order: denoise → deband_smooth → sharpen
    """
    if not profile.any_enabled:
        return None

    # Capture parameters at build time (closure is immutable during encode)
    _denoise_enabled = profile.denoise_enabled
    _denoise_strength = profile.denoise_strength
    _denoise_method = profile.denoise_method

    _deband_enabled = profile.deband_enhance_enabled
    _deband_strength = profile.deband_strength

    _sharpen_enabled = profile.sharpen_enabled
    _sharpen_strength = profile.sharpen_strength
    _sharpen_radius = profile.sharpen_radius

    def _enhance_frame(frame: np.ndarray) -> np.ndarray:
        """
        Apply enhancement pipeline to a single float32 [0,1] RGB frame.

        Order: denoise → deband_smooth → sharpen
        """
        result = frame.astype(np.float32)  # ensure dtype (no copy if already f32)

        # Step 1: Denoise
        if _denoise_enabled:
            result = _apply_denoise(result, _denoise_strength, _denoise_method)

        # Step 2: Deband smooth
        if _deband_enabled:
            result = _apply_deband_smooth(result, _deband_strength)

        # Step 3: Sharpen (always last — operates on clean material)
        if _sharpen_enabled:
            result = _apply_perceptual_sharpen(result, _sharpen_strength, _sharpen_radius)

        return np.clip(result, 0.0, 1.0).astype(np.float32)

    return _enhance_frame
