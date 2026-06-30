#!/usr/bin/env python3
"""
analyze_source.py — Análise adaptativa de source para Reels_Encoder_v2_FINAL
Metodologia Gabriel

Uso:
  python scripts/analyze_source.py input.mp4
  python scripts/analyze_source.py input.mp4 --json relatorio.json
  python scripts/analyze_source.py input.mp4 --frames 10 --mode cineon

Integração no encoder:
  from scripts.analyze_source import analyze, AnalysisResult
  result = analyze("video.mp4")
  print(result.vf_chain)
  print(result.ffmpeg_command)
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

import av
import cv2
import numpy as np

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

# ─── LUTs padrão por modo ─────────────────────────────────────────────────────
LUT_FFMPEG = "HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube"
LUT_CINEON = "FilmLook_Portra400_SkinPriority_D65.cube"


# ─── Estruturas de dados ──────────────────────────────────────────────────────
@dataclass
class FeatureVector:
    """Vetor 13D de features extraídas do source. Ver adaptive-analysis.md."""
    # Grupo 1: Noise profile
    luma_noise:         float = 0.0  # Laplacian variance (0–500+; low<50, high>200)
    chroma_noise:       float = 0.0  # Variância Cr+Cb (0–300+; low<30, high>80)
    block_noise:        float = 0.0  # Block DCT variance 8×8 (0–200+)
    temporal_noise:     float = 0.0  # Diferença inter-frame (0–50+; low<5, high>12)
    # Grupo 2: Scene complexity
    spatial_complexity: float = 0.0  # Gradiente Sobel médio (0–80+; low<15, high>50)
    entropy:            float = 0.0  # Shannon entropy bits (0–8; low<5, complex>7)
    motion_magnitude:   float = 0.0  # Farneback optical flow px/frame (0–30+)
    # Grupo 3: Tonal distribution
    highlight_load:     float = 0.0  # % pixels > 220/255 (0–1; crítico >0.15)
    shadow_load:        float = 0.0  # % pixels < 16/255 (0–1; crítico >0.20)
    midtone_variance:   float = 0.0  # Variância zona 0.2–0.8 (pele: 0.03–0.07)
    # Grupo 4: Skin & color
    skin_ratio:         float = 0.0  # Máscara YCrCb (0–1; close rosto >0.30)
    mean_saturation:    float = 0.0  # HSV saturation média (0–1)
    color_temp_proxy:   float = 1.0  # Razão R/B (>1.05=quente, <0.95=frio)


@dataclass
class AnalysisResult:
    """Resultado completo da análise adaptativa."""
    features:            FeatureVector
    duration_s:          float
    fps:                 float
    resolution:          tuple
    source_codec:        str
    source_bitrate:      int
    vbv_profile:         dict
    denoise_method:      str
    denoise_params:      dict
    x264_opts:           dict
    rolloff_filter:      str | None
    vf_chain:            str
    encoder_mode:        str          # "ffmpeg" | "cineon"
    mode_reasoning:      list         # lista de razões
    lut_path:            str
    ffmpeg_command:      str
    recompression_score: int
    gop_profile:         dict = field(default_factory=dict)
    zones_profile:       dict | None = None
    frames_analyzed:     int = 0


# ─── Frame extraction via PyAV ────────────────────────────────────────────────
def _open_meta(video_path: str) -> dict:
    """Extrai metadados do container sem decodificar frames."""
    with av.open(video_path) as c:
        vs = c.streams.video[0]
        dur = float(c.duration / av.time_base) if c.duration else 0.0
        if dur <= 0 and vs.duration and vs.time_base:
            dur = float(vs.duration * vs.time_base)
        return {
            "fps":     float(vs.average_rate or 30),
            "width":   vs.codec_context.width,
            "height":  vs.codec_context.height,
            "codec":   vs.codec_context.name,
            "duration": dur,
            "bitrate": int(c.bit_rate or 0) // 1000,
        }


def extract_frames(video_path: str, n: int = 7) -> list[np.ndarray]:
    """
    Extrai n frames representativos via PyAV.
    Posições: 10%–90% da duração, evitando fade-in/out dos extremos.
    """
    frames = []
    ratios = np.linspace(0.10, 0.90, n)

    with av.open(video_path) as container:
        vs = container.streams.video[0]
        vs.codec_context.skip_frame = "NONREF"

        dur = float(container.duration / av.time_base) if container.duration else 30.0
        if dur <= 0 and vs.duration and vs.time_base:
            dur = float(vs.duration * vs.time_base)

        tb = float(vs.time_base) if vs.time_base else 1 / 30

        for r in ratios:
            seek_ts = int(dur * r / tb)
            try:
                container.seek(seek_ts, stream=vs)
                for frame in container.decode(vs):
                    frames.append(frame.to_ndarray(format="bgr24"))
                    break
            except Exception:
                continue

    return frames


def extract_temporal_pairs(video_path: str, n_pairs: int = 3) -> list[tuple]:
    """
    Extrai pares de frames consecutivos para medir temporal noise.
    Dois frames em sequência imediata a 25%, 50% e 75% da duração.
    """
    pairs = []
    with av.open(video_path) as container:
        vs = container.streams.video[0]
        vs.codec_context.skip_frame = "NONREF"

        dur = float(container.duration / av.time_base) if container.duration else 30.0
        tb  = float(vs.time_base) if vs.time_base else 1 / 30

        for r in np.linspace(0.25, 0.75, n_pairs):
            seek_ts = int(dur * r / tb)
            try:
                container.seek(seek_ts, stream=vs)
                pair = []
                for frame in container.decode(vs):
                    pair.append(frame.to_ndarray(format="bgr24"))
                    if len(pair) == 2:
                        break
                if len(pair) == 2:
                    pairs.append((pair[0], pair[1]))
            except Exception:
                continue

    return pairs


# ─── Feature extraction ───────────────────────────────────────────────────────
def _noise(bgr: np.ndarray) -> dict:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    yuv  = cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV).astype(np.float32)

    luma_noise   = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    chroma_noise = (float(yuv[:, :, 1].var()) + float(yuv[:, :, 2].var())) / 2.0

    # Block noise vetorizado — O(1) vs O(W*H/64) do loop original
    h, w   = gray.shape
    bh, bw = (h // 8) * 8, (w // 8) * 8
    B      = gray[:bh, :bw].reshape(h // 8, 8, w // 8, 8)
    mu     = B.mean(axis=(1, 3), keepdims=True)
    block_noise = float(((B - mu) ** 2).mean(axis=(1, 3)).mean())

    return {"luma_noise": luma_noise, "chroma_noise": chroma_noise,
            "block_noise": block_noise}


def _complexity(bgr: np.ndarray, prev: np.ndarray | None = None) -> dict:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    spatial = float(np.sqrt(gx ** 2 + gy ** 2).mean())

    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    h    = hist / hist.sum()
    h    = h[h > 0]
    entropy = float(-np.sum(h * np.log2(h)))

    motion = 0.0
    if prev is not None:
        pg   = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            pg, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        motion = float(np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean())

    return {"spatial_complexity": spatial, "entropy": entropy,
            "motion_magnitude": motion}


def _tonal(bgr: np.ndarray) -> dict:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    mid_mask = (g >= 0.2) & (g <= 0.8)
    return {
        "highlight_load":   float((g > 0.87).mean()),
        "shadow_load":      float((g < 0.06).mean()),
        "midtone_variance": float(g[mid_mask].var()) if mid_mask.any() else 0.0,
    }


def _skin_color(bgr: np.ndarray) -> dict:
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    skin_mask = (
        (ycc[:, :, 0] >= 80)  & (ycc[:, :, 0] <= 240) &
        (ycc[:, :, 1] >= 133) & (ycc[:, :, 1] <= 173) &
        (ycc[:, :, 2] >= 77)  & (ycc[:, :, 2] <= 127)
    )
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    b   = float(bgr[:, :, 0].mean())
    r   = float(bgr[:, :, 2].mean())
    return {
        "skin_ratio":        float(skin_mask.mean()),
        "mean_saturation":   float(hsv[:, :, 1].mean()) / 255.0,
        "color_temp_proxy":  r / (b + 1e-6),
    }


def _temporal_noise(a: np.ndarray, b: np.ndarray) -> float:
    return float(cv2.absdiff(
        cv2.cvtColor(a, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(b, cv2.COLOR_BGR2GRAY),
    ).astype(np.float32).mean())


def _robust_mean(lst: list[float]) -> float:
    """Média aparada: remove 1 outlier de cada extremo se n ≥ 5."""
    s = sorted(lst)
    if len(s) >= 5:
        s = s[1:-1]
    return float(np.mean(s))


def aggregate_features(frames: list[np.ndarray],
                       pairs: list[tuple]) -> FeatureVector:
    """Agrega features de múltiplos frames com remoção de outliers."""
    ns = [_noise(f) for f in frames]
    cs = [_complexity(frames[i], frames[i - 1] if i > 0 else None)
          for i in range(len(frames))]
    ts = [_tonal(f) for f in frames]
    ss = [_skin_color(f) for f in frames]
    tn = [_temporal_noise(a, b) for a, b in pairs] if pairs else [0.0]

    def m(lst, k): return _robust_mean([d[k] for d in lst])

    return FeatureVector(
        luma_noise         = m(ns, "luma_noise"),
        chroma_noise       = m(ns, "chroma_noise"),
        block_noise        = m(ns, "block_noise"),
        temporal_noise     = float(np.mean(tn)),
        spatial_complexity = m(cs, "spatial_complexity"),
        entropy            = m(cs, "entropy"),
        motion_magnitude   = m(cs, "motion_magnitude"),
        highlight_load     = m(ts, "highlight_load"),
        shadow_load        = m(ts, "shadow_load"),
        midtone_variance   = m(ts, "midtone_variance"),
        skin_ratio         = m(ss, "skin_ratio"),
        mean_saturation    = m(ss, "mean_saturation"),
        color_temp_proxy   = m(ss, "color_temp_proxy"),
    )


# ─── Parameter derivation ─────────────────────────────────────────────────────
def derive_vbv(duration_s: float) -> dict:
    if duration_s <= 30:
        return {"target": 10000, "maxrate": 11200, "bufsize": 15000,
                "vbv_init": 0.90, "label": "Maximum Quality (≤30s)"}
    elif duration_s >= 40:
        return {"target": 8000, "maxrate": 9000, "bufsize": 12500,
                "vbv_init": 0.90, "label": "Safe Premium (≥40s)"}
    else:
        return {"target": 9000, "maxrate": 10000, "bufsize": 13500,
                "vbv_init": 0.90, "label": "Transição (30–40s)"}


def derive_denoise(f: FeatureVector) -> tuple[str, dict]:
    """Deriva método e parâmetros de denoise do vetor de features."""
    luma, chroma, temp, skin = (f.luma_noise, f.chroma_noise,
                                f.temporal_noise, f.skin_ratio)
    params: dict = {}

    if luma < 50 and chroma < 30 and temp < 5:
        return "hqdn3d_minimal", {
            "luma_s": 0.5, "chroma_s": 0.3, "luma_t": 0.3, "chroma_t": 0.2
        }

    elif luma < 200 and chroma < 80 and temp < 12:
        cap       = 2.0 if skin > 0.25 else 3.0
        threshold = round(min(1.5 + (luma / 200.0) * 1.5, cap), 2)
        method_t  = "soft" if skin > 0.15 else "hard"
        params    = {"threshold": threshold, "method": method_t, "nsteps": 6}
        if temp > 8:
            params["temporal_pre"] = {
                "luma_t":   round(min(temp / 4.0, 4.0), 1),
                "chroma_t": round(min(temp / 5.0, 3.0), 1),
            }
        return "vaguedenoiser", params

    else:
        s_cap = 0.05 if skin > 0.30 else 0.08
        c_cap = 0.04 if skin > 0.30 else 0.06
        return "bm3d", {
            "sigma_spatial": round(min(0.04 + (luma / 500.0) * 0.04, s_cap), 3),
            "sigma_chroma":  round(min(0.03 + (chroma / 300.0) * 0.03, c_cap), 3),
        }


def derive_x264(f: FeatureVector) -> dict:
    """Deriva parâmetros x264 adaptativos a partir das features."""
    aq = 0.8
    if f.skin_ratio > 0.25:
        aq += 0.1 * (f.skin_ratio / 0.5)
    if f.motion_magnitude > 15:
        aq -= 0.1
    if f.highlight_load > 0.20:
        aq -= 0.05
    aq = round(max(0.6, min(aq, 1.2)), 2)

    subme = 9 if (f.spatial_complexity > 50 or f.motion_magnitude > 20) \
            else 7 if (f.spatial_complexity < 15 and f.motion_magnitude < 3) \
            else 8

    psy_rd = (1.0 if f.spatial_complexity > 40 and f.skin_ratio < 0.15
              else 0.8 if f.spatial_complexity > 25 and f.skin_ratio < 0.30
              else 0.0)

    return {
        "aq_strength":  aq,
        "subme":        subme,
        "psy_rd":       psy_rd,
        "rc_lookahead": 40 if f.motion_magnitude > 20 else 60,
        "deblock":      "-1,-1" if f.skin_ratio > 0.30 else "0,0",
    }


def derive_rolloff(f: FeatureVector) -> str | None:
    """Deriva rolloff de highlights se highlight_load justificar."""
    if f.highlight_load < 0.05:
        return None
    kp = round(max(0.75, 0.92 - f.highlight_load * 0.8), 3)
    ko = round(max(0.90, 0.97 - f.highlight_load * 0.15), 3)
    return (f"curves=r='0/0 {kp}/{kp} 1.0/{ko}':"
            f"g='0/0 {kp}/{kp} 1.0/{ko}':"
            f"b='0/0 {kp}/{kp} 1.0/{ko}'")


def recommend_mode(f: FeatureVector, duration_s: float,
                   meta: dict) -> tuple[str, list[str]]:
    """
    Retorna (modo, razões[]) — 'ffmpeg' ou 'cineon'.
    Lógica completa documentada em references/encoder-modes.md.
    """
    pro_cineon: list[str] = []
    pro_ffmpeg: list[str] = []

    codec = meta.get("codec", "").lower()
    if any(x in codec for x in ["hevc", "prores", "dnxhd", "cineform"]):
        pro_cineon.append(f"codec {codec} sugere log/intermediário")

    if f.skin_ratio > 0.30 and 1.0 < f.color_temp_proxy < 1.9:
        pro_cineon.append(
            f"skin_ratio={f.skin_ratio:.2f} + temp_proxy={f.color_temp_proxy:.2f} "
            f"→ Portra400 SkinPriority"
        )

    if f.highlight_load > 0.18:
        pro_cineon.append(
            f"highlight_load={f.highlight_load:.3f} "
            f"→ tone mapping float32 superior"
        )

    if f.luma_noise > 180 and f.skin_ratio > 0.25:
        pro_cineon.append(
            f"noise alto ({f.luma_noise:.0f}) com skin → float32 preserva textura"
        )

    if duration_s > 60:
        pro_ffmpeg.append(f"duração {duration_s:.0f}s > 60s → custo Cineon elevado")
    if f.motion_magnitude > 18:
        pro_ffmpeg.append(
            f"motion={f.motion_magnitude:.1f} → FFmpeg Mode adequado e mais rápido"
        )
    if not pro_cineon:
        pro_ffmpeg.append("source BT.709, iluminação controlada → FFmpeg suficiente")

    if len(pro_cineon) >= len(pro_ffmpeg):
        return "cineon", pro_cineon or ["pipeline float32 preferido"]
    else:
        return "ffmpeg", pro_ffmpeg


def recompression_score(meta: dict) -> int:
    """Score 0–10 de risco de recompressão. Ver SKILL.md Passo 2."""
    s = 0
    codec = meta.get("codec", "").lower()
    if "hevc" in codec or "h265" in codec: s += 2
    if meta.get("bitrate", 0) > 15000:    s += 2
    if meta.get("bitrate", 0) < 5000:     s += 1
    if meta.get("width", 1080) != 1080:   s += 1
    if round(meta.get("fps", 30)) == 60:  s += 1
    return s


def analyze_cut_structure(video_path: str, fps: float = 30.0) -> dict:
    """
    Pass-1 leve: analisa a estrutura real de cortes do source via ffprobe.

    Extrai timestamps de todos os I-frames do vídeo e deriva:
    - cut_timestamps: lista de timestamps (s) de cada I-frame
    - cut_count: total de cortes detectados
    - mean_cut_interval: intervalo médio entre I-frames (s)
    - min_cut_interval: menor intervalo (s) — define o keyint mínimo seguro
    - max_cut_interval: maior intervalo (s)
    - cut_regularity: coeficiente de variação (0=cortes regulares, >0.5=irregulares)
    - rhythm: 'regular' | 'irregular' | 'single_take'
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "frame=pts_time,pict_type",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _cut_structure_fallback("ffprobe indisponível ou timeout")

    timestamps: list[float] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[1].strip() == "I":
            try:
                timestamps.append(float(parts[0]))
            except ValueError:
                continue

    if len(timestamps) < 2:
        return _cut_structure_fallback("I-frames insuficientes para análise")

    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    mean_iv   = float(np.mean(intervals))
    min_iv    = float(np.min(intervals))
    max_iv    = float(np.max(intervals))
    std_iv    = float(np.std(intervals))
    cv        = std_iv / mean_iv if mean_iv > 0 else 0.0  # coeficiente de variação

    if len(timestamps) <= 2 or mean_iv > 10.0:
        rhythm = "single_take"
    elif cv < 0.35:
        rhythm = "regular"
    else:
        rhythm = "irregular"

    return {
        "cut_count":        len(timestamps) - 1,
        "cut_timestamps":   timestamps[:50],       # cap para JSON compacto
        "mean_cut_interval": round(mean_iv, 3),
        "min_cut_interval":  round(min_iv, 3),
        "max_cut_interval":  round(max_iv, 3),
        "cut_regularity_cv": round(cv, 3),
        "rhythm":            rhythm,
        "fps":               fps,
        "fallback":          False,
        "fallback_reason":   "",
    }


def _cut_structure_fallback(reason: str) -> dict:
    """Retorna estrutura de corte neutra quando ffprobe falha."""
    return {
        "cut_count":         0,
        "cut_timestamps":    [],
        "mean_cut_interval": 2.0,
        "min_cut_interval":  1.0,
        "max_cut_interval":  2.0,
        "cut_regularity_cv": 0.0,
        "rhythm":            "regular",
        "fps":               30.0,
        "fallback":          True,
        "fallback_reason":   reason,
    }


def derive_gop(features: FeatureVector, cut_structure: dict,
               duration_s: float, fps: float = 30.0) -> dict:
    """
    Deriva GOP adaptativo a partir da estrutura real de cortes + features do source.

    Decisão em três camadas:
      1. Estrutura de cortes reais (cut_structure) — evidência primária
      2. motion_magnitude + spatial_complexity — evidência secundária
      3. Tipo de conteúdo (skin_ratio, duração) — refinamento final

    Retorna:
      keyint        : GOP máximo em frames
      min_keyint    : GOP mínimo em frames (sempre 1)
      scenecut      : sensibilidade de detecção de corte (0=off, 40=padrão)
      force_keyframes: expressão FFmpeg para force_key_frames (ou None)
      strategy      : 'fixed' | 'scenecut_only' | 'dual_coverage'
      reasoning     : lista de razões para auditoria
    """
    rhythm   = cut_structure.get("rhythm", "regular")
    mean_iv  = cut_structure.get("mean_cut_interval", 2.0)
    min_iv   = cut_structure.get("min_cut_interval", 1.0)
    cv       = cut_structure.get("cut_regularity_cv", 0.0)
    fallback = cut_structure.get("fallback", False)
    motion   = features.motion_magnitude
    skin     = features.skin_ratio
    sc_cmplx = features.spatial_complexity
    reasoning: list[str] = []

    # ── Camada 1: ritmo de corte medido ──────────────────────────────────────
    if fallback:
        reasoning.append("ffprobe indisponível → heurística por motion_magnitude")
        keyint_s = 2.0  # fallback seguro
    elif rhythm == "single_take":
        reasoning.append(f"plano único / poucos cortes (mean_interval={mean_iv:.1f}s) → GOP máximo")
        keyint_s = 2.0
    elif rhythm == "regular":
        # Cortes regulares: keyint = intervalo médio arredondado para frames
        keyint_s = min(mean_iv, 2.0)  # nunca exceder 2s (regra Instagram)
        reasoning.append(
            f"cortes regulares (CV={cv:.2f}) → keyint baseado em mean_interval={mean_iv:.2f}s"
        )
    else:  # irregular
        # Cortes irregulares: usar o mínimo detectado como anchor, com headroom
        keyint_s = min(max(min_iv * 1.2, 1.0), 2.0)
        reasoning.append(
            f"cortes irregulares (CV={cv:.2f}) → keyint ancorado em "
            f"min_interval={min_iv:.2f}s × 1.2"
        )

    # ── Camada 2: motion + complexidade ──────────────────────────────────────
    if motion > 20 and not fallback:
        # Alto movimento: reduzir GOP para garantir I-frames em transições
        keyint_s = min(keyint_s, 1.5)
        reasoning.append(f"motion={motion:.1f} px/frame → GOP comprimido para ≤1.5s")
    elif motion < 3 and rhythm == "single_take":
        # Plano estático longo: GOP máximo, máxima eficiência
        keyint_s = 2.0
        reasoning.append(f"motion={motion:.1f} + single_take → GOP máximo 2.0s")

    # ── Camada 3: tipo de conteúdo ────────────────────────────────────────────
    if skin > 0.30 and sc_cmplx < 30:
        # Close de rosto em plano estático — pequenos ajustes de expressão
        # não justificam I-frames frequentes, mas pele é sensível a artefatos de P-frame
        keyint_s = min(keyint_s, 1.5)
        reasoning.append(
            f"skin_ratio={skin:.2f} alto + spatial_complexity={sc_cmplx:.1f} baixo "
            f"→ GOP moderado para proteger textura de pele"
        )

    # ── Converter para frames ─────────────────────────────────────────────────
    keyint = max(1, min(round(keyint_s * fps), 60))  # hard cap: 60 frames (Instagram)

    # ── Estratégia de aplicação ───────────────────────────────────────────────
    if fallback or rhythm == "single_take":
        # Fallback ou plano único: scenecut interno do x264 é suficiente
        strategy       = "scenecut_only"
        scenecut       = 40
        force_kf       = None
        reasoning.append("estratégia: scenecut interno x264 (scenecut=40)")

    elif rhythm == "regular" and cv < 0.20:
        # Cortes muito regulares: keyint fixo é mais eficiente que force_key_frames
        strategy       = "fixed"
        scenecut       = 40  # manter como safety net
        force_kf       = None
        reasoning.append(
            "estratégia: keyint fixo (cortes regulares CV<0.20) + scenecut safety net"
        )

    else:
        # Cortes irregulares ou ritmo misto: cobertura dupla determinística.
        # Em vez de expr:gte(scene,X) — que requer filtro auxiliar e é não-determinística —
        # usar os timestamps reais medidos no Pass-1 como lista explícita.
        # FFmpeg garante I-frame exato em cada timestamp da lista.
        strategy = "dual_coverage"
        scenecut = 50  # mais sensível como safety net adicional

        # Selecionar até 20 cortes mais significativos (limite prático do FFmpeg)
        # Filtrar timestamps muito próximos do início (< 0.5s) e do fim
        ts_list = cut_structure.get("cut_timestamps", [])
        ts_filtered = [t for t in ts_list if t > 0.5 and t < duration_s - 0.5][:20]

        if ts_filtered:
            force_kf = ",".join(f"{t:.3f}" for t in ts_filtered)
            reasoning.append(
                f"estratégia: dual coverage — scenecut=50 + "
                f"force_key_frames com {len(ts_filtered)} timestamps medidos no Pass-1"
            )
        else:
            # Sem timestamps utilizáveis, cair para scenecut_only
            strategy = "scenecut_only"
            scenecut = 40
            force_kf = None
            reasoning.append(
                "estratégia: scenecut_only (timestamps do Pass-1 sem cortes utilizáveis)"
            )

    return {
        "keyint":          keyint,
        "min_keyint":      1,
        "scenecut":        scenecut,
        "force_keyframes": force_kf,
        "strategy":        strategy,
        "keyint_s":        round(keyint / fps, 3),
        "reasoning":       reasoning,
        "cut_rhythm":      rhythm,
        "mean_cut_interval_s": cut_structure.get("mean_cut_interval", 2.0),
    }


# ─── VF chain & command builder ──────────────────────────────────────────────
def build_vf_chain(f: FeatureVector, method: str, params: dict,
                   rolloff: str | None, lut: str, mode: str) -> str:
    parts: list[str] = []

    # Temporal pre-filter
    if "temporal_pre" in params:
        t = params["temporal_pre"]
        parts.append(f"hqdn3d=0.5:0.5:{t['luma_t']}:{t['chroma_t']}")

    # Denoise principal
    if method == "hqdn3d_minimal":
        p = params
        parts.append(
            f"hqdn3d={p['luma_s']}:{p['chroma_s']}:{p['luma_t']}:{p['chroma_t']}"
        )
    elif method == "vaguedenoiser":
        parts.append(
            f"vaguedenoiser=threshold={params['threshold']}"
            f":method={params['method']}:nsteps={params['nsteps']}"
        )
    elif method == "bm3d":
        # BM3D roda no pipeline float32 do Cineon Mode (enhance/ package).
        # Nunca é inserido como filtro FFmpeg — não existe frei0r=bm3d no encoder.
        # Se este branch for atingido com mode="ffmpeg", o analyze() já deve ter
        # escalado para "cineon" automaticamente antes de chamar build_vf_chain().
        # Fallback defensivo: vaguedenoiser com parâmetros conservadores.
        sigma = params.get("sigma_spatial", 0.05)
        threshold = round(min(1.5 + sigma * 20, 2.5), 2)
        parts.append(
            f"vaguedenoiser=threshold={threshold}:method=soft:nsteps=8"
        )

    # Rolloff
    if rolloff:
        parts.append(rolloff)

    # LUT 3D
    parts.append(f"lut3d={lut}:interp=tetrahedral")

    # Dithering RPDF — obrigatório no Cineon Mode (float32 → 8-bit)
    if mode == "cineon":
        parts.append("noise=alls=1:allf=u")

    # Scale + FPS — sempre por último
    parts.append("scale=1080:1920:flags=lanczos")
    parts.append("fps=30")

    return ",\\\n    ".join(parts)


# ─── Alocação de bits por shot (x264 zones) — Módulo cinema ────────────────────
def _sample_segment_demand(video_path: str, t_mid: float, fps: float) -> float:
    """Amostra 1 frame no meio do segmento e retorna um proxy de demanda de bits
    (complexidade espacial via Sobel). Barato: 1 seek + 1 decode por shot."""
    try:
        with av.open(video_path) as container:
            vs = container.streams.video[0]
            vs.codec_context.skip_frame = "NONREF"
            tb = float(vs.time_base) if vs.time_base else 1 / 30
            container.seek(int(max(t_mid, 0.0) / tb), stream=vs)
            for frame in container.decode(vs):
                g  = cv2.cvtColor(frame.to_ndarray(format="bgr24"), cv2.COLOR_BGR2GRAY)
                gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
                gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
                return float(np.sqrt(gx**2 + gy**2).mean())
    except Exception:
        pass
    return 0.0


def derive_zones_core(segments: list, fps: float, total_frames: int,
                      sensitivity: float = 0.55, mult_min: float = 0.70,
                      mult_max: float = 1.40, neutral_eps: float = 0.04) -> dict | None:
    """
    Núcleo puro/testável. segments: list[(t_start, t_end, demand>0)].
    Deriva multiplicadores de bitrate por shot (x264 zones, opção b=).

    Budget-preserving: a média ponderada por frames dos multiplicadores é
    normalizada para ~1.0 (2 passes com clipping), então o -b:v/VBV global
    continua válido — zones apenas REDISTRIBUI bits entre shots, o maxrate/
    bufsize segue sendo o teto rígido de conformidade Instagram.
    """
    if not segments or len(segments) < 2:
        return None
    ranges = []
    for ts, te, d in segments:
        s = max(0, int(round(ts * fps)))
        e = min(total_frames - 1, int(round(te * fps)) - 1)
        if e > s:
            ranges.append([s, e, max(float(d), 1e-6)])
    ranges.sort(key=lambda r: r[0])
    for i in range(len(ranges) - 1):                  # x264 exige ranges sem overlap
        if ranges[i][1] >= ranges[i + 1][0]:
            ranges[i][1] = ranges[i + 1][0] - 1
    ranges = [r for r in ranges if r[1] > r[0]]
    if len(ranges) < 2:
        return None

    demands = np.array([r[2] for r in ranges])
    frames  = np.array([r[1] - r[0] + 1 for r in ranges], float)
    mult = np.clip(1.0 + sensitivity * ((demands - demands.mean()) / demands.mean()),
                   mult_min, mult_max)
    for _ in range(2):                                # normaliza p/ preservar budget
        mult = mult / ((mult * frames).sum() / frames.sum())
        mult = np.clip(mult, mult_min, mult_max)

    parts = [f"{s},{e},b={m:.2f}" for (s, e, _), m in zip(ranges, mult)
             if abs(m - 1.0) >= neutral_eps]
    if not parts:
        return None
    return {
        "zones":          "/".join(parts),
        "zone_count":     len(parts),
        "budget_effective": round(float((mult * frames).sum() / frames.sum()), 3),
    }


def derive_zones(video_path: str, cut_structure: dict, features: "FeatureVector",
                 duration_s: float, fps: float = 30.0, max_segments: int = 16) -> dict | None:
    """
    Wrapper: usa a estrutura de cortes JÁ medida no Pass-1 para alocar bits por
    shot. Amostra a complexidade de cada segmento e deriva a string x264 zones.

    Retorna None (sem zones) quando não há o que diferenciar:
      - single_take / fallback / menos de 2 cortes
      - demanda uniforme entre shots (núcleo retorna None)
    """
    if cut_structure.get("fallback") or cut_structure.get("rhythm") == "single_take":
        return None
    ts = cut_structure.get("cut_timestamps", [])
    if len(ts) < 3:
        return None
    bounds = sorted(set([0.0] + list(ts) + [duration_s]))
    segs = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
            if bounds[i + 1] - bounds[i] > 0.3]            # ignora micro-segmentos
    if len(segs) > max_segments:                            # mantém a string compacta
        segs = segs[:max_segments]
    total_frames = int(round(duration_s * fps))
    sampled = [(a, b, _sample_segment_demand(video_path, (a + b) / 2.0, fps))
               for a, b in segs]
    sampled = [(a, b, d) for a, b, d in sampled if d > 0]   # descarta seeks que falharam
    return derive_zones_core(sampled, fps, total_frames)


def build_ffmpeg_cmd(vf: str, x264: dict, vbv: dict, gop: dict,
                     zones: dict | None = None,
                     output: str = "output_reels.mp4") -> str:
    keyint   = gop.get("keyint", 60)
    scenecut = gop.get("scenecut", 40)
    force_kf = gop.get("force_keyframes")

    # Stack x264 premium: trellis=2 (RD trellis em todos os MBs), b-adapt=2
    # (placement ótimo de B-frames), mixed-refs=1 (seleção de ref por 8x8).
    # Justificado nos bitrates 8–11 Mbps onde o alvo é qualidade perceptual máxima.
    x264_opts = (
        f"ref=4:bframes=2:b-adapt=2:trellis=2:mixed-refs=1"
        f":aq-mode=3:aq-strength={x264['aq_strength']}"
        f":me=umh:subme={x264['subme']}:rc-lookahead={x264['rc_lookahead']}"
        f":deblock={x264['deblock']}"
        f":keyint={keyint}:min-keyint=1:scenecut={scenecut}"
        f":vbv-init={vbv['vbv_init']}"
    )
    if x264["psy_rd"] > 0:
        x264_opts += f":psy-rd={x264['psy_rd']},0"
    if zones and zones.get("zones"):
        x264_opts += f":zones={zones['zones']}"

    # force_key_frames vai no -vf como filtro select ou como flag separada
    force_kf_flag = (
        f"  -force_key_frames \"{force_kf}\" \\\n" if force_kf else ""
    )

    return (
        f'ffmpeg -i input.mp4 \\\n'
        f'  -c:v libx264 -profile:v high -level:v 4.0 -pix_fmt yuv420p \\\n'
        f'  -vf "{vf}" \\\n'
        f'  -b:v {vbv["target"]}k -maxrate {vbv["maxrate"]}k '
        f'-bufsize {vbv["bufsize"]}k \\\n'
        f'{force_kf_flag}'
        f'  -x264-params "{x264_opts}" \\\n'
        f'  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \\\n'
        f'  -c:a aac -b:a 128k -ar 44100 -ac 2 \\\n'
        f'  -movflags +faststart -y {output}'
    )


# ─── Main orchestration ───────────────────────────────────────────────────────
def analyze(video_path: str, n_frames: int = 7,
            lut_override: str | None = None,
            mode_override: str | None = None) -> AnalysisResult:
    """
    Ponto de entrada principal. Importável pelo Reels_Encoder_v2_FINAL.py.

    Exemplo de integração no enhance/ package:
        from scripts.analyze_source import analyze
        result = analyze(input_path, n_frames=7)
        # result.features       → FeatureVector com 13D
        # result.gop_profile    → GOP derivado (keyint, scenecut, force_keyframes, strategy)
        # result.vf_chain       → string para -vf do FFmpeg
        # result.ffmpeg_command → comando completo pronto
    """
    p = Path(video_path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {video_path}")

    meta   = _open_meta(str(p))
    frames = extract_frames(str(p), n=n_frames)
    if not frames:
        raise RuntimeError(f"Nenhum frame extraído: {video_path}")

    pairs    = extract_temporal_pairs(str(p))
    features = aggregate_features(frames, pairs)

    dur = meta["duration"]
    fps = meta["fps"]

    # ── Pass-1: análise de cortes reais via ffprobe ───────────────────────────
    # Roda antes de qualquer encode — alimenta derive_gop() com evidência real
    cut_structure = analyze_cut_structure(str(p), fps=fps)

    vbv           = derive_vbv(dur)
    dm, dp        = derive_denoise(features)
    x264          = derive_x264(features)
    ro            = derive_rolloff(features)
    gop           = derive_gop(features, cut_structure, dur, fps)
    zones         = derive_zones(str(p), cut_structure, features, dur, fps)
    mode, reasons = recommend_mode(features, dur, meta)
    rc            = recompression_score(meta)

    # BM3D é exclusivo do Cineon Mode — escalar automaticamente se FFmpeg foi recomendado
    if dm == "bm3d" and mode == "ffmpeg" and not mode_override:
        mode = "cineon"
        reasons = [
            "BM3D selecionado pela análise de noise → requer pipeline float32",
            "escalado automaticamente para Cineon Mode",
        ] + reasons

    if mode_override:
        mode    = mode_override
        reasons = [f"forçado via --mode {mode_override}"]

    lut = lut_override or (LUT_CINEON if mode == "cineon" else LUT_FFMPEG)
    vf  = build_vf_chain(features, dm, dp, ro, lut, mode)
    cmd = build_ffmpeg_cmd(vf, x264, vbv, gop, zones)

    return AnalysisResult(
        features=features,
        duration_s=dur,
        fps=fps,
        resolution=(meta["width"], meta["height"]),
        source_codec=meta["codec"],
        source_bitrate=meta["bitrate"],
        vbv_profile=vbv,
        denoise_method=dm,
        denoise_params=dp,
        x264_opts=x264,
        rolloff_filter=ro,
        vf_chain=vf,
        encoder_mode=mode,
        mode_reasoning=reasons,
        lut_path=lut,
        ffmpeg_command=cmd,
        recompression_score=rc,
        gop_profile=gop,
        zones_profile=zones,
        frames_analyzed=len(frames),
    )


# ─── Rich terminal report ─────────────────────────────────────────────────────
def _lvl(val: float, low: float, high: float,
         labels=("low", "moderate", "high"),
         colors=("green", "yellow", "red")) -> str:
    if val < low:   return f"[{colors[0]}]{labels[0]}[/{colors[0]}]"
    if val < high:  return f"[{colors[1]}]{labels[1]}[/{colors[1]}]"
    return f"[{colors[2]}]{labels[2]}[/{colors[2]}]"


def print_report(r: AnalysisResult, title: str = "") -> None:
    if not HAS_RICH:
        print(json.dumps(asdict(r), indent=2, default=str))
        return

    c = console
    f = r.features
    c.print()
    c.print(Panel(
        f"[bold cyan]ANÁLISE ADAPTATIVA[/bold cyan]"
        f"{'  —  ' + title if title else ''}\n"
        f"[dim]Metodologia Gabriel · Reels_Encoder_v2_FINAL.py[/dim]",
        box=box.DOUBLE_EDGE,
    ))

    # ── Source ──
    src = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    src.add_column(style="dim", min_width=14)
    src.add_column()
    src.add_row("Arquivo",    title or "—")
    src.add_row("Resolução",  f"{r.resolution[0]}×{r.resolution[1]}")
    src.add_row("FPS",        f"{r.fps:.2f}")
    src.add_row("Codec",      r.source_codec)
    src.add_row("Duração",    f"{r.duration_s:.1f}s")
    src.add_row("Bitrate",    f"{r.source_bitrate} kbps")
    src.add_row("Frames",     f"{r.frames_analyzed} amostrados")
    c.print(Panel(src, title="[bold]SOURCE[/bold]", border_style="blue"))

    # ── Feature vector ──
    ft = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    ft.add_column("Feature",         style="dim", min_width=24)
    ft.add_column("Valor",           justify="right", min_width=8)
    ft.add_column("Nível",           min_width=10)
    ft.add_column("Impacto",         style="dim")

    ft.add_row("luma_noise",         f"{f.luma_noise:.1f}",
               _lvl(f.luma_noise, 50, 200),         "método de denoise principal")
    ft.add_row("chroma_noise",       f"{f.chroma_noise:.1f}",
               _lvl(f.chroma_noise, 30, 80),         "sigma chromático BM3D")
    ft.add_row("block_noise",        f"{f.block_noise:.1f}",
               _lvl(f.block_noise, 20, 100),         "risco de blocking DCT")
    ft.add_row("temporal_noise",     f"{f.temporal_noise:.2f}",
               _lvl(f.temporal_noise, 5, 12),        "temporal pre-filter / MCTF EMA")
    ft.add_row("spatial_complexity", f"{f.spatial_complexity:.1f}",
               _lvl(f.spatial_complexity, 15, 50),   "subme · psy-rd · GOP")
    ft.add_row("entropy",            f"{f.entropy:.2f}",
               _lvl(f.entropy, 5, 7),                "compressibilidade geral")
    ft.add_row("motion_magnitude",   f"{f.motion_magnitude:.2f}",
               _lvl(f.motion_magnitude, 3, 15),      "rc-lookahead · aq-strength")
    ft.add_row("highlight_load",     f"{f.highlight_load:.4f}",
               _lvl(f.highlight_load, 0.05, 0.15),   "rolloff · tone mapping")
    ft.add_row("shadow_load",        f"{f.shadow_load:.4f}",
               _lvl(f.shadow_load, 0.10, 0.25),      "shadow lift / crush risk")
    ft.add_row("midtone_variance",   f"{f.midtone_variance:.5f}",
               _lvl(f.midtone_variance, 0.02, 0.06), "aq-strength skin zone")
    ft.add_row("skin_ratio",         f"{f.skin_ratio:.4f}",
               _lvl(f.skin_ratio, 0.10, 0.30,
                    labels=("baixo", "moderado", "alto"),
                    colors=("dim", "yellow", "green")),
               "cap denoise · deblock · Portra LUT")
    ft.add_row("mean_saturation",    f"{f.mean_saturation:.3f}",
               _lvl(f.mean_saturation, 0.20, 0.60),  "saturação da cena")
    ft.add_row("color_temp_proxy",   f"{f.color_temp_proxy:.3f}",
               "[green]quente[/green]" if f.color_temp_proxy > 1.05
               else "[blue]frio[/blue]" if f.color_temp_proxy < 0.95
               else "[dim]neutro[/dim]",
               "seleção de LUT / tone mapping")

    c.print(Panel(ft, title="[bold]FEATURE VECTOR 13D[/bold]", border_style="cyan"))

    # ── Parâmetros derivados ──
    def denoise_str():
        m, p = r.denoise_method, r.denoise_params
        if m == "hqdn3d_minimal":
            return f"hqdn3d {p['luma_s']}:{p['chroma_s']}:{p['luma_t']}:{p['chroma_t']}"
        if m == "vaguedenoiser":
            s = f"vaguedenoiser thr={p['threshold']} method={p['method']} nsteps={p['nsteps']}"
            if "temporal_pre" in p:
                s += f" + temporal_pre luma_t={p['temporal_pre']['luma_t']}"
            return s
        if m == "bm3d":
            return f"BM3D σ_spatial={p['sigma_spatial']} σ_chroma={p['sigma_chroma']}"
        return m

    rc_score = r.recompression_score
    rc_color = "red" if rc_score >= 5 else "yellow" if rc_score >= 3 else "green"

    pd = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    pd.add_column(style="dim", min_width=18)
    pd.add_column()
    pd.add_row("Perfil VBV",      f"[bold]{r.vbv_profile['label']}[/bold]")
    pd.add_row("  b:v / maxrate", f"{r.vbv_profile['target']} / {r.vbv_profile['maxrate']} kbps")
    pd.add_row("  bufsize",       f"{r.vbv_profile['bufsize']} kbps")
    pd.add_row("Denoise",         denoise_str())
    pd.add_row("aq-strength",     str(r.x264_opts["aq_strength"]))
    pd.add_row("subme",           str(r.x264_opts["subme"]))
    pd.add_row("psy-rd",          str(r.x264_opts["psy_rd"]) if r.x264_opts["psy_rd"] else "off")
    pd.add_row("rc-lookahead",    str(r.x264_opts["rc_lookahead"]))
    pd.add_row("deblock",         r.x264_opts["deblock"])
    if r.zones_profile and r.zones_profile.get("zones"):
        z = r.zones_profile
        pd.add_row("Bit-alloc (zones)",
                   f"[cyan]{z['zone_count']} shots[/cyan] "
                   f"[dim](budget {z['budget_effective']:.2f})[/dim]")
    pd.add_row("Highlight rolloff",
               "[green]ativo[/green]" if r.rolloff_filter else "[dim]não necessário[/dim]")
    pd.add_row("Recomp. risk",
               f"[{rc_color}]{rc_score}/10 — "
               f"{'🔴 alto' if rc_score >= 5 else '🟡 moderado' if rc_score >= 3 else '🟢 mínimo'}"
               f"[/{rc_color}]")

    c.print(Panel(pd, title="[bold]PARÂMETROS DERIVADOS[/bold]", border_style="green"))

    # ── GOP Profile ──
    g = r.gop_profile
    if g:
        strategy_color = {
            "fixed":         "green",
            "scenecut_only": "yellow",
            "dual_coverage": "cyan",
        }.get(g.get("strategy", ""), "dim")
        strategy_label = {
            "fixed":         "FIXED KEYINT",
            "scenecut_only": "SCENECUT ONLY",
            "dual_coverage": "DUAL COVERAGE",
        }.get(g.get("strategy", ""), g.get("strategy", "—"))
        rhythm_color = {
            "regular":     "green",
            "irregular":   "yellow",
            "single_take": "dim",
        }.get(g.get("cut_rhythm", ""), "dim")

        gop_tbl = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        gop_tbl.add_column(style="dim", min_width=22)
        gop_tbl.add_column()
        gop_tbl.add_row("Ritmo de corte",
                        f"[{rhythm_color}]{g.get('cut_rhythm', '—')}[/{rhythm_color}]")
        gop_tbl.add_row("Intervalo médio",
                        f"{g.get('mean_cut_interval_s', 0):.2f}s")
        gop_tbl.add_row("keyint derivado",
                        f"[bold]{g.get('keyint', 60)} frames[/bold] "
                        f"({g.get('keyint_s', 2.0):.2f}s @ {r.fps:.0f}fps)")
        gop_tbl.add_row("min-keyint",      "1")
        gop_tbl.add_row("scenecut",        str(g.get("scenecut", 40)))
        gop_tbl.add_row("force_key_frames",
                        f"[cyan]{g.get('force_keyframes')}[/cyan]"
                        if g.get("force_keyframes")
                        else "[dim]não aplicado[/dim]")
        gop_tbl.add_row("Estratégia",
                        f"[bold {strategy_color}]{strategy_label}[/bold {strategy_color}]")
        if g.get("reasoning"):
            gop_tbl.add_row("", "")
            for rz in g["reasoning"]:
                gop_tbl.add_row("[dim]·[/dim]", f"[dim]{rz}[/dim]")
        c.print(Panel(gop_tbl, title="[bold]GOP ADAPTATIVO[/bold]", border_style="magenta"))

    # ── Encoder mode ──
    mode_color = "magenta" if r.encoder_mode == "cineon" else "yellow"
    mode_label = "🎬  CINEON MODE" if r.encoder_mode == "cineon" else "⚡  FFMPEG MODE"
    lut_name   = Path(r.lut_path).name
    reasons    = "\n".join(f"  · {rz}" for rz in r.mode_reasoning)
    c.print(Panel(
        f"[bold {mode_color}]{mode_label}[/bold {mode_color}]\n\n"
        f"LUT:  [bold]{lut_name}[/bold]\n\n"
        f"[dim]Razões:[/dim]\n{reasons}",
        title="[bold]MODO RECOMENDADO[/bold]",
        border_style=mode_color,
    ))

    # ── VF chain ──
    c.print(Panel(
        f"[bold]-vf[/bold]\n[cyan]{r.vf_chain}[/cyan]",
        title="[bold]VF CHAIN[/bold]",
        border_style="cyan",
    ))

    # ── Comando FFmpeg ──
    c.print(Panel(
        r.ffmpeg_command,
        title="[bold green]COMANDO FFMPEG — pronto para rodar[/bold green]",
        border_style="green",
    ))
    c.print()


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="analyze_source.py — Análise adaptativa para Reels_Encoder_v2_FINAL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python scripts/analyze_source.py video.mp4\n"
            "  python scripts/analyze_source.py video.mp4 --json resultado.json\n"
            "  python scripts/analyze_source.py video.mp4 --mode cineon --frames 10\n"
        ),
    )
    ap.add_argument("input",            help="Arquivo de vídeo source")
    ap.add_argument("--frames",  type=int, default=7, metavar="N",
                    help="Frames a amostrar (padrão: 7, mais = mais preciso)")
    ap.add_argument("--json",    metavar="PATH", nargs="?", const="analysis.json",
                    help="Exportar JSON (padrão: analysis.json)")
    ap.add_argument("--lut",     metavar="PATH",
                    help="Override do caminho da LUT")
    ap.add_argument("--mode",    choices=["ffmpeg", "cineon"],
                    help="Forçar modo (ignora recomendação automática)")
    ap.add_argument("--output",  default="output_reels.mp4",
                    help="Nome do arquivo de saída no comando gerado")

    args = ap.parse_args()

    try:
        result = analyze(
            args.input,
            n_frames=args.frames,
            lut_override=args.lut,
            mode_override=args.mode,
        )
    except (FileNotFoundError, RuntimeError) as e:
        print(f"\nERRO: {e}\n", file=sys.stderr)
        sys.exit(1)

    print_report(result, title=Path(args.input).name)

    if args.json is not None:
        out = args.json if isinstance(args.json, str) else "analysis.json"
        Path(out).write_text(json.dumps(asdict(result), indent=2, default=str))
        msg = f"JSON salvo: {out}"
        console.print(f"[dim]{msg}[/dim]") if HAS_RICH else print(msg)


if __name__ == "__main__":
    main()
