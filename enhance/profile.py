"""
enhance/profile.py
==================
EnhanceProfile: dataclass that aggregates analyzer results and drives
the enhancement decision matrix.

Public API:
    profile = build_enhance_profile(input_file, n_sample_frames=5)
    profile = build_enhance_profile_from_metrics(noise_agg, banding_agg, detail_agg)
    print_enhance_report(profile)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .analyzers.noise import NoiseResult, analyze_noise
from .analyzers.banding import BandingResult, analyze_banding
from .analyzers.detail import DetailResult, analyze_detail

# ── Thresholds (heurística Fase 1) ───────────────────────────────────────────

NOISE_LIGHT_THR    = 0.02   # σ > → denoise light
NOISE_MEDIUM_THR   = 0.05   # σ > → denoise medium
NOISE_STRONG_THR   = 0.10   # σ > → denoise strong
NOISE_KILLS_SHARPEN = 0.08  # σ > → sharpen desativado (amplificaria ruído)

BANDING_LIGHT_THR  = 0.30   # severity > → deband+ light
BANDING_STRONG_THR = 0.60   # severity > → deband+ strong

SHARP_NEEDED_THR   = 0.30   # sharpness < → sharpen strong
SHARP_OK_THR       = 0.80   # sharpness > → sharpen desnecessário


# ── Aggregated Metric dataclasses ─────────────────────────────────────────────

@dataclass
class NoiseAgg:
    """Aggregated noise metrics across sampled frames."""
    sigma: float = 0.0
    low_freq_ratio: float = 0.0
    uniformity: float = 1.0


@dataclass
class BandingAgg:
    """Aggregated banding metrics across sampled frames."""
    severity: float = 0.0
    gradient_score: float = 0.0
    flat_region_pct: float = 0.0


@dataclass
class DetailAgg:
    """Aggregated detail metrics across sampled frames."""
    sharpness: float = 0.0
    texture_complexity: float = 0.0
    edge_density: float = 0.0
    freq_low: float = 0.0
    freq_mid: float = 0.0
    freq_high: float = 0.0
    detail_score: float = 0.0


# ── EnhanceProfile ────────────────────────────────────────────────────────────

@dataclass
class EnhanceProfile:
    """
    Complete enhancement decision profile derived from content analysis.

    Consumed by:
      - enhance/processor.py   → per-frame NumPy/OpenCV filters (Cineon mode)
      - enhance/ffmpeg_filters.py → FFmpeg filter string (Mode 1)
    """

    # ── Source ────────────────────────────────────────────────────────────────
    input_file: str = ""
    n_frames_analyzed: int = 0

    # ── Aggregated metrics ────────────────────────────────────────────────────
    noise: NoiseAgg = field(default_factory=NoiseAgg)
    banding: BandingAgg = field(default_factory=BandingAgg)
    detail: DetailAgg = field(default_factory=DetailAgg)

    # ── Denoise decision ──────────────────────────────────────────────────────
    denoise_enabled: bool = False
    denoise_strength: float = 0.0      # [0.0–1.0]
    denoise_method: str = "none"       # "nlmeans" | "bilateral" | "gaussian" | "none"

    # ── Sharpen decision ──────────────────────────────────────────────────────
    sharpen_enabled: bool = False
    sharpen_strength: float = 0.0      # [0.0–1.0]
    sharpen_radius: float = 1.0        # kernel radius [1.0–2.0]

    # ── Deband+ decision ──────────────────────────────────────────────────────
    deband_enhance_enabled: bool = False
    deband_strength: float = 0.0       # [0.0–1.0]

    # ── Deblock decision ──────────────────────────────────────────────────────
    deblock_enabled: bool = False      # DCT block artifact removal (compressed sources)

    # ── Content classification ────────────────────────────────────────────────
    content_type: str = "mixed"        # "clean" | "noisy" | "compressed" | "mixed"
    quality_score: float = 0.5         # [0.0–1.0]

    # ── Diagnostics ───────────────────────────────────────────────────────────
    reasons: List[str] = field(default_factory=list)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def any_enabled(self) -> bool:
        """True if any enhancement filter is active."""
        return (
            self.denoise_enabled
            or self.sharpen_enabled
            or self.deband_enhance_enabled
            or self.deblock_enabled
        )

    @property
    def summary(self) -> str:
        # FIX: ordem correta do pipeline — denoise → deband+ → sharpen
        active = []
        if self.denoise_enabled:
            active.append(f"denoise({self.denoise_method}/{self.denoise_strength:.2f})")
        if self.deband_enhance_enabled:
            active.append(f"deband+({self.deband_strength:.2f})")
        if self.sharpen_enabled:
            active.append(f"sharpen({self.sharpen_strength:.2f}/r{self.sharpen_radius:.1f})")
        if not active:
            return "all_off"
        return " | ".join(active)


# ── Decision matrix ───────────────────────────────────────────────────────────

def _apply_decision_matrix(
    noise: NoiseAgg,
    banding: BandingAgg,
    detail: DetailAgg,
    profile: EnhanceProfile,
) -> None:
    """
    Apply heuristic decision matrix to populate enhancement decisions.
    Modifies profile in-place.
    """
    σ = noise.sigma
    sev = banding.severity
    sharp = detail.sharpness

    # ── Denoise ──────────────────────────────────────────────────────────────
    if σ > NOISE_STRONG_THR:
        profile.denoise_enabled = True
        profile.denoise_strength = min(1.0, (σ - NOISE_STRONG_THR) / 0.10 * 0.4 + 0.6)
        profile.denoise_method = "nlmeans"
        profile.reasons.append(f"denoise=strong (σ={σ:.3f}>{NOISE_STRONG_THR})")
    elif σ > NOISE_MEDIUM_THR:
        profile.denoise_enabled = True
        profile.denoise_strength = 0.3 + (σ - NOISE_MEDIUM_THR) / (NOISE_STRONG_THR - NOISE_MEDIUM_THR) * 0.3
        profile.denoise_method = "bilateral"
        profile.reasons.append(f"denoise=medium (σ={σ:.3f}>{NOISE_MEDIUM_THR})")
    elif σ > NOISE_LIGHT_THR:
        profile.denoise_enabled = True
        profile.denoise_strength = 0.1 + (σ - NOISE_LIGHT_THR) / (NOISE_MEDIUM_THR - NOISE_LIGHT_THR) * 0.2
        profile.denoise_method = "gaussian"
        profile.reasons.append(f"denoise=light (σ={σ:.3f}>{NOISE_LIGHT_THR})")

    # ── Sharpen ───────────────────────────────────────────────────────────────
    noise_kills = σ > NOISE_KILLS_SHARPEN
    if noise_kills:
        profile.reasons.append(f"sharpen=off (σ={σ:.3f}>{NOISE_KILLS_SHARPEN}, noise kills)")
    elif sharp < SHARP_NEEDED_THR:
        profile.sharpen_enabled = True
        profile.sharpen_strength = 0.5 + (SHARP_NEEDED_THR - sharp) / SHARP_NEEDED_THR * 0.5
        profile.sharpen_radius = 2.0
        profile.reasons.append(f"sharpen=strong (sharpness={sharp:.3f}<{SHARP_NEEDED_THR})")
    elif sharp < SHARP_OK_THR and σ <= NOISE_LIGHT_THR:
        profile.sharpen_enabled = True
        profile.sharpen_strength = 0.2 + (SHARP_OK_THR - sharp) / (SHARP_OK_THR - SHARP_NEEDED_THR) * 0.3
        profile.sharpen_radius = 1.0
        profile.reasons.append(f"sharpen=gentle (sharpness={sharp:.3f})")
    elif sharp >= SHARP_OK_THR:
        profile.reasons.append(f"sharpen=off (sharpness={sharp:.3f}>={SHARP_OK_THR}, ok)")

    # ── Deband+ ───────────────────────────────────────────────────────────────
    if sev > BANDING_STRONG_THR:
        profile.deband_enhance_enabled = True
        profile.deband_strength = 0.6 + (sev - BANDING_STRONG_THR) / (1.0 - BANDING_STRONG_THR) * 0.4
        profile.reasons.append(f"deband+=strong (severity={sev:.3f}>{BANDING_STRONG_THR})")
    elif sev > BANDING_LIGHT_THR:
        profile.deband_enhance_enabled = True
        profile.deband_strength = 0.2 + (sev - BANDING_LIGHT_THR) / (BANDING_STRONG_THR - BANDING_LIGHT_THR) * 0.4
        profile.reasons.append(f"deband+=light (severity={sev:.3f}>{BANDING_LIGHT_THR})")


def _classify_content(noise: NoiseAgg, banding: BandingAgg, detail: DetailAgg) -> str:
    """
    Classify content type. Priority: compressed > noisy > clean > mixed.
    """
    if banding.severity > BANDING_LIGHT_THR:
        return "compressed"
    if noise.sigma > NOISE_MEDIUM_THR:
        return "noisy"
    if noise.sigma < NOISE_LIGHT_THR and detail.sharpness > 0.6:
        return "clean"
    return "mixed"


def _compute_quality_score(noise: NoiseAgg, banding: BandingAgg, detail: DetailAgg) -> float:
    """
    Quality score [0=poor, 1=excellent].
    """
    noise_penalty = min(1.0, noise.sigma / 0.15) * 0.35
    banding_penalty = banding.severity * 0.35
    detail_bonus = detail.detail_score * 0.30
    return float(np.clip(1.0 - noise_penalty - banding_penalty + detail_bonus * 0.3, 0.0, 1.0))


# ── Feature vector (13-dim) ───────────────────────────────────────────────────

def _build_feature_vector(
    noise: NoiseAgg,
    banding: BandingAgg,
    detail: DetailAgg,
) -> np.ndarray:
    """
    Build 13-dimensional feature vector for Mock CNN (Fase 27F).

    Dimensions:
      0: noise.sigma
      1: noise.low_freq_ratio
      2: noise.uniformity
      3: banding.severity
      4: banding.gradient_score
      5: banding.flat_region_pct
      6: detail.sharpness
      7: detail.texture_complexity
      8: detail.edge_density
      9: detail.freq_low
      10: detail.freq_mid
      11: detail.freq_high
      12: detail.detail_score
    """
    return np.array([
        noise.sigma,
        noise.low_freq_ratio,
        noise.uniformity,
        banding.severity,
        banding.gradient_score,
        banding.flat_region_pct,
        detail.sharpness,
        detail.texture_complexity,
        detail.edge_density,
        detail.freq_low,
        detail.freq_mid,
        detail.freq_high,
        detail.detail_score,
    ], dtype=np.float32)


# ── AI weights → EnhanceProfile conversion (Fase 27F) ────────────────────────

# Activation threshold: weight below this → filter disabled
_AI_ACTIVATION_THR = 0.1

def _weights_to_profile(
    weights: np.ndarray,
    noise: NoiseAgg,
    banding: BandingAgg,
    detail: DetailAgg,
    input_file: str = "",
    n_frames: int = 0,
    model_name: str = "",
) -> EnhanceProfile:
    """
    Convert continuous AI weights [0,1] to EnhanceProfile fields.

    Args:
        weights: shape (3,) — [denoise_weight, sharpen_weight, deband_weight]
        noise, banding, detail: aggregated metrics (for classification/scoring)
        input_file: source file path
        n_frames: number of frames analyzed
        model_name: AI model identifier for diagnostics

    Returns:
        Populated EnhanceProfile with AI-driven decisions.
    """
    denoise_w = float(weights[0])
    sharpen_w = float(weights[1])
    deband_w = float(weights[2])

    profile = EnhanceProfile(
        input_file=input_file,
        n_frames_analyzed=n_frames,
        noise=noise,
        banding=banding,
        detail=detail,
    )

    # ── Denoise ──────────────────────────────────────────────────────────
    if denoise_w > _AI_ACTIVATION_THR:
        profile.denoise_enabled = True
        profile.denoise_strength = denoise_w
        # Method selection based on weight magnitude
        if denoise_w < 0.3:
            profile.denoise_method = "gaussian"
        elif denoise_w < 0.6:
            profile.denoise_method = "bilateral"
        else:
            profile.denoise_method = "nlmeans"
        profile.reasons.append(
            f"ai_denoise={profile.denoise_method} "
            f"(w={denoise_w:.3f})"
        )
    else:
        profile.reasons.append(f"ai_denoise=off (w={denoise_w:.3f})")

    # ── Sharpen ──────────────────────────────────────────────────────────
    # Hard override: NOISE_KILLS_SHARPEN applies regardless of AI decision
    noise_kills = noise.sigma > NOISE_KILLS_SHARPEN
    if noise_kills:
        profile.reasons.append(
            f"ai_sharpen=off (σ={noise.sigma:.3f}>{NOISE_KILLS_SHARPEN}, "
            f"noise_kills overrides ai w={sharpen_w:.3f})"
        )
    elif sharpen_w > _AI_ACTIVATION_THR:
        profile.sharpen_enabled = True
        profile.sharpen_strength = sharpen_w * 0.5
        profile.sharpen_radius = 1.0 + sharpen_w  # [1.0–2.0]
        profile.reasons.append(f"ai_sharpen=on (w={sharpen_w:.3f})")
    else:
        profile.reasons.append(f"ai_sharpen=off (w={sharpen_w:.3f})")

    # ── Deband+ ──────────────────────────────────────────────────────────
    if deband_w > _AI_ACTIVATION_THR:
        profile.deband_enhance_enabled = True
        profile.deband_strength = deband_w
        profile.reasons.append(f"ai_deband+=on (w={deband_w:.3f})")
    else:
        profile.reasons.append(f"ai_deband+=off (w={deband_w:.3f})")

    # ── Classification & quality (same logic as Fase 1) ──────────────────
    profile.content_type = _classify_content(noise, banding, detail)
    profile.quality_score = _compute_quality_score(noise, banding, detail)

    # Deblock: ativado para conteúdo classificado como comprimido
    if profile.content_type == "compressed":
        profile.deblock_enabled = True
        profile.reasons.append("deblock=on (content_type=compressed)")

    # ── AI model tag ─────────────────────────────────────────────────────
    if model_name:
        profile.reasons.append(f"ai_model={model_name}")

    return profile


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _aggregate_noise(results: List[NoiseResult], weights: List[float]) -> NoiseAgg:
    w = np.array(weights, dtype=np.float64)
    w /= w.sum()
    sigma = float(np.dot(w, [r.sigma for r in results]))
    lfr = float(np.dot(w, [r.low_freq_ratio for r in results]))
    uni = float(np.dot(w, [r.uniformity for r in results]))
    return NoiseAgg(sigma=sigma, low_freq_ratio=lfr, uniformity=uni)


def _aggregate_banding(results: List[BandingResult], weights: List[float]) -> BandingAgg:
    w = np.array(weights, dtype=np.float64)
    w /= w.sum()
    sev = float(np.dot(w, [r.severity for r in results]))
    gs = float(np.dot(w, [r.gradient_score for r in results]))
    fp = float(np.dot(w, [r.flat_region_pct for r in results]))
    return BandingAgg(severity=sev, gradient_score=gs, flat_region_pct=fp)


def _aggregate_detail(results: List[DetailResult], weights: List[float]) -> DetailAgg:
    w = np.array(weights, dtype=np.float64)
    w /= w.sum()
    return DetailAgg(
        sharpness=float(np.dot(w, [r.sharpness for r in results])),
        texture_complexity=float(np.dot(w, [r.texture_complexity for r in results])),
        edge_density=float(np.dot(w, [r.edge_density for r in results])),
        freq_low=float(np.dot(w, [r.freq_low for r in results])),
        freq_mid=float(np.dot(w, [r.freq_mid for r in results])),
        freq_high=float(np.dot(w, [r.freq_high for r in results])),
        detail_score=float(np.dot(w, [r.detail_score for r in results])),
    )


def _frame_weights(n: int) -> List[float]:
    """Center-frame dominance weights."""
    if n == 1:
        return [1.0]
    weights = [1.0] * n
    center = n // 2
    weights[center] = 2.0  # center frame gets 2x weight
    return weights


# ── Public API ────────────────────────────────────────────────────────────────

def build_enhance_profile_from_metrics(
    noise: NoiseAgg,
    banding: BandingAgg,
    detail: DetailAgg,
    input_file: str = "",
    n_frames: int = 0,
) -> EnhanceProfile:
    """
    Build EnhanceProfile from pre-computed aggregated metrics.
    Used for testing and when metrics are already available.
    """
    profile = EnhanceProfile(
        input_file=input_file,
        n_frames_analyzed=n_frames,
        noise=noise,
        banding=banding,
        detail=detail,
    )
    _apply_decision_matrix(noise, banding, detail, profile)
    profile.content_type = _classify_content(noise, banding, detail)
    profile.quality_score = _compute_quality_score(noise, banding, detail)

    # Deblock: ativado para conteúdo classificado como comprimido
    if profile.content_type == "compressed":
        profile.deblock_enabled = True
        profile.reasons.append("deblock=on (content_type=compressed)")

    return profile


def build_enhance_profile(
    input_file: str,
    n_sample_frames: int = 5,
    use_ai: bool = False,
) -> EnhanceProfile:
    """
    Build EnhanceProfile by sampling and analysing frames from a video file.

    Args:
        input_file:     Path to input video file.
        n_sample_frames: Number of frames to sample (default 5).
        use_ai:         When True, use Mock CNN (Fase 27F) for decisions.
                        When False, use heuristic decision matrix (Fase 1).

    Returns:
        EnhanceProfile with all enhancement decisions populated.
    """
    # Import sampler lazily to avoid PyAV dependency at module level
    try:
        from .sampler import sample_frames
        frames = sample_frames(input_file, n_frames=n_sample_frames)
    except Exception as e:
        # Fallback: return neutral profile if sampling fails
        profile = EnhanceProfile(input_file=input_file)
        profile.reasons.append(f"sampling_failed: {e}")
        return profile

    if not frames:
        profile = EnhanceProfile(input_file=input_file)
        profile.reasons.append("no_frames_sampled")
        return profile

    weights = _frame_weights(len(frames))

    noise_results = [analyze_noise(f.data) for f in frames]
    banding_results = [analyze_banding(f.data) for f in frames]
    detail_results = [analyze_detail(f.data) for f in frames]

    noise_agg = _aggregate_noise(noise_results, weights)
    banding_agg = _aggregate_banding(banding_results, weights)
    detail_agg = _aggregate_detail(detail_results, weights)

    if use_ai:
        # ── Fase 2: Mock CNN path ────────────────────────────────────────
        from .ai import MockCNN
        model = MockCNN()
        features = _build_feature_vector(noise_agg, banding_agg, detail_agg)
        ai_weights = model.predict(features)
        profile = _weights_to_profile(
            ai_weights, noise_agg, banding_agg, detail_agg,
            input_file=input_file,
            n_frames=len(frames),
            model_name=model.name(),
        )

        # ── Feature vector logging (JSON) ────────────────────────────────
        try:
            import json
            from datetime import datetime
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "model": model.name(),
                "input_file": os.path.basename(input_file),
                "n_frames": len(frames),
                "feature_vector": features.tolist(),
                "ai_weights": {
                    "denoise": float(ai_weights[0]),
                    "sharpen": float(ai_weights[1]),
                    "deband": float(ai_weights[2]),
                },
                "decisions": {
                    "denoise_enabled": profile.denoise_enabled,
                    "denoise_method": profile.denoise_method,
                    "denoise_strength": profile.denoise_strength,
                    "sharpen_enabled": profile.sharpen_enabled,
                    "sharpen_strength": profile.sharpen_strength,
                    "deband_enabled": profile.deband_enhance_enabled,
                    "deband_strength": profile.deband_strength,
                    "content_type": profile.content_type,
                    "quality_score": profile.quality_score,
                },
            }
            log_dir = os.path.dirname(os.path.abspath(input_file))
            log_path = os.path.join(log_dir, "enhance_ai_log.json")
            # Append mode: accumulate entries
            entries = []
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        entries = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    entries = []
            entries.append(log_data)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # logging failure must never block encode
        # ─────────────────────────────────────────────────────────────────

    else:
        # ── Fase 1: Heuristic decision matrix (default, unchanged) ───────
        profile = build_enhance_profile_from_metrics(
            noise_agg, banding_agg, detail_agg,
            input_file=input_file,
            n_frames=len(frames),
        )

    return profile

def enhance_pipeline_report(
    profile: EnhanceProfile,
    mode: str = "ffmpeg",
    ai: bool = False,
) -> List[str]:
    """
    Generate Rich-formatted report lines for inline console output.

    Args:
        profile: populated EnhanceProfile
        mode: "ffmpeg" or "cineon"
        ai: True if AI path was used

    Returns:
        List of Rich-markup strings for console.print()
    """
    lines = []
    tag = "[AI] " if ai else ""
    pipeline = "FFmpeg filters" if mode == "ffmpeg" else "Cineon per-frame"

    if not profile.any_enabled:
        lines.append(f"[dim]  ✨ Enhance {tag}({pipeline}): all_off — conteúdo limpo[/dim]")
        return lines

    lines.append(f"[cyan]  ✨ Enhance {tag}({pipeline}):[/cyan]")
    lines.append(f"[dim]     Conteúdo: {profile.content_type} | Qualidade: {profile.quality_score:.2f}[/dim]")
    lines.append(f"[dim]     Pipeline: {profile.summary}[/dim]")

    if profile.denoise_enabled:
        lines.append(
            f"[dim]     ├─ Denoise: {profile.denoise_method} "
            f"(strength={profile.denoise_strength:.2f})[/dim]"
        )
    if profile.deband_enhance_enabled:
        lines.append(
            f"[dim]     ├─ Deband+: strength={profile.deband_strength:.2f}[/dim]"
        )
    if profile.sharpen_enabled:
        lines.append(
            f"[dim]     └─ Sharpen: strength={profile.sharpen_strength:.2f} "
            f"radius={profile.sharpen_radius:.1f}[/dim]"
        )

    return lines

def print_enhance_report(profile: EnhanceProfile) -> None:
    """
    Print a formatted console report of the EnhanceProfile.
    """
    print()
    print("=" * 60)
    ai_mode = any(r.startswith("ai_model=") for r in profile.reasons)
    mode_tag = "Fase 2 [AI]" if ai_mode else "Fase 1 [Heurísticas]"
    print(f"  ENHANCEMENT ENGINE — ANÁLISE DE CONTEÚDO — {mode_tag}")
    print("=" * 60)
    if profile.input_file:
        print(f"  Arquivo : {os.path.basename(profile.input_file)}")
    print(f"  Frames  : {profile.n_frames_analyzed}")
    print()
    print("  ── Métricas ──────────────────────────────────────────")
    print(f"  Ruído     σ={profile.noise.sigma:.4f}  "
          f"lf_ratio={profile.noise.low_freq_ratio:.3f}  "
          f"uniformity={profile.noise.uniformity:.3f}")
    print(f"  Banding   severity={profile.banding.severity:.4f}  "
          f"grad={profile.banding.gradient_score:.3f}  "
          f"flat={profile.banding.flat_region_pct:.3f}")
    print(f"  Detalhe   sharpness={profile.detail.sharpness:.4f}  "
          f"texture={profile.detail.texture_complexity:.3f}  "
          f"edges={profile.detail.edge_density:.3f}")
    print(f"  Freq      low={profile.detail.freq_low:.3f}  "
          f"mid={profile.detail.freq_mid:.3f}  "
          f"high={profile.detail.freq_high:.3f}")
    print()
    print("  ── Decisões ──────────────────────────────────────────")
    print(f"  Conteúdo  : {profile.content_type}")
    print(f"  Qualidade : {profile.quality_score:.3f}")
    print(f"  Resumo    : {profile.summary}")
    print()
    if profile.reasons:
        print("  ── Razões ────────────────────────────────────────────")
        for r in profile.reasons:
            print(f"    • {r}")
    print("=" * 60)
    print()
