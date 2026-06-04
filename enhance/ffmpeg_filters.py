"""
enhance/ffmpeg_filters.py
=========================
FASE 27D — FFmpeg filter string generator for Mode 1 (FFmpeg pipeline).

Public API:
    vf = build_enhance_filtergraph(profile)   # None if nothing to do
    if vf:
        video_filter = vf + "," + video_filter   # prepend to existing -vf

Filter string format:
    "deband=...,nlmeans=...,unsharp=..."
    (deband → denoise → sharpen — always this order)

Rationale for FFmpeg order:
    1. deband first  — remove quantization bands before noise-sensitive ops.
    2. denoise second — removes noise from the deband result.
    3. unsharp last  — sharpens clean material; never amplifies banding or noise.

All parameter computations are deterministic from the EnhanceProfile;
no FFmpeg subprocess is invoked here — pure string generation.

FFmpeg filter notes:
    nlmeans  : s (h) must be ≥ 1.0 in FFmpeg's implementation.
    hqdn3d   : luma_spatial:chroma_spatial:luma_tmp:chroma_tmp
               Used as bilateral/gaussian proxy (FFmpeg has no bilateral).
    unsharp  : lx:ly:la:cx:cy:ca  (luma + chroma kernel, amount)
               la  = luma sharpening amount  (positive = sharpen)
               ca  = 0.0 (no chroma sharpening — avoids colour fringing)
    deband   : 1thr:2thr:3thr:range:blur
               thr = per-component threshold, normalized float [0.00003, 0.5]
               blur= 1 (linear smooth — preserves luma edges better than avg)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .profile import EnhanceProfile

logger = logging.getLogger(__name__)

# ── FFmpeg parameter scales ────────────────────────────────────────────────────

# nlmeans
_NLM_S_MIN = 1.0      # FFmpeg minimum for nlmeans s parameter
_NLM_S_MAX = 10.0
_NLM_S_SCALE = 12.0   # strength [0,1] → s = clip(strength * scale, min, max)
_NLM_P = 7            # patch size (pixels)
_NLM_R = 15           # search window radius (pixels)

# hqdn3d (bilateral/gaussian proxy)
_HQDN3D_LUMA_SCALE = 8.0     # luma spatial = clip(strength * scale, 0.5, 14.0)
_HQDN3D_CHROMA_SCALE = 6.0   # chroma spatial = clip(strength * scale, 0.5, 10.0)
_HQDN3D_LUMA_TMP = 3.0       # temporal luma (constant)
_HQDN3D_CHROMA_TMP = 3.0     # temporal chroma (constant)

# CAS (Contrast Adaptive Sharpening) — substitui unsharp no path pré-LUT
_CAS_STR_SCALE = 0.5          # cas_strength = sharpen_strength * scale
_CAS_STR_MAX   = 0.65         # cap (0.0–1.0 é o range do filtro cas)

# deblock — remoção de artefatos DCT de compressão H.264/H.265
_DEBLOCK_FILTER = "weak"      # "weak" = conservador, não afeta bordas limpas
_DEBLOCK_BLOCK  = 4           # tamanho do bloco DCT (H.264 usa 4×4 e 8×8)

# deband
_DEBAND_RANGE = 16            # pixel search range
_DEBAND_BLUR = 1              # 1 = linear smooth (better edge preservation)
_DEBAND_THR_SCALE = 0.06      # strength [0,1] → thr in FFmpeg normalized range [0.00003, 0.5]
_DEBAND_THR_MIN = 0.003       # minimum threshold to have effect
_DEBAND_THR_MAX = 0.06        # max threshold before blurring too aggressively

# ── Blue-noise dithering (FASE 30A) ──────────────────────────────────────────
_DITHER_C0S_MIN = 2           # amplitude mínima efetiva (~0.8% de 255 ≈ 0.8 LSBs)
_DITHER_C0S_MAX = 6           # amplitude máxima antes de ser visível (~2.4% ≈ 2.4 LSBs)
_DITHER_FLAGS   = "t+u"       # temporal + uniforme (RPDF): cada frame diferente, distribuição plana

# ── Filter fragment builders ──────────────────────────────────────────────────

def _build_nlmeans(strength: float) -> str:
    """nlmeans=s={s}:p={p}:r={r}"""
    s = float(max(_NLM_S_MIN, min(_NLM_S_MAX, strength * _NLM_S_SCALE)))
    return f"nlmeans=s={s:.2f}:p={_NLM_P}:r={_NLM_R}"


def _build_hqdn3d(strength: float) -> str:
    """hqdn3d={ls}:{cs}:{lt}:{ct}"""
    ls = float(max(0.5, min(14.0, strength * _HQDN3D_LUMA_SCALE)))
    cs = float(max(0.5, min(10.0, strength * _HQDN3D_CHROMA_SCALE)))
    return (
        f"hqdn3d={ls:.2f}:{cs:.2f}"
        f":{_HQDN3D_LUMA_TMP:.1f}:{_HQDN3D_CHROMA_TMP:.1f}"
    )


def _build_cas(strength: float) -> str:
    """
    CAS — Contrast Adaptive Sharpening (AMD).

    Edge-adaptive: sharpens bordas genuínas, ignora áreas flat/ruidosas.
    Substitui unsharp no pipeline pré-LUT — não amplifica artefatos DCT.
    """
    s = float(min(_CAS_STR_MAX, strength * _CAS_STR_SCALE))
    return f"cas=strength={s:.3f}"


def _build_deblock() -> str:
    """
    deblock — remoção de blocos DCT de compressão H.264/H.265.

    filter=weak: conservador, age apenas nos artefatos mais evidentes sem
    borrar bordas limpas. Deve ser aplicado ANTES do denoise.
    """
    return f"deblock=filter={_DEBLOCK_FILTER}:block={_DEBLOCK_BLOCK}"


def _build_deband(strength: float) -> str:
    """
    deband=1thr={t}:2thr={t}:3thr={t}:range={r}:blur={b}

    Uses identical thresholds for all three components (Y/Cb/Cr).
    Thresholds in FFmpeg normalized range [0.00003, 0.5].
    """
    thr = float(max(_DEBAND_THR_MIN, min(_DEBAND_THR_MAX, strength * _DEBAND_THR_SCALE)))
    return (
        f"deband=1thr={thr:.5f}:2thr={thr:.5f}:3thr={thr:.5f}"
        f":range={_DEBAND_RANGE}:blur={_DEBAND_BLUR}"
    )


def _build_dither(strength: float = 0.5) -> str:
    """
    Blue-noise dithering via FFmpeg noise filter (FASE 30A).

    Aplicado entre zscale e format=yuv420p para quebrar a coerência
    espacial dos degraus de quantização ANTES da codificação final.

    Por que funciona contra o re-encoding do Instagram:
      1. O gradiente tem banding determinístico → degraus em posições fixas.
      2. O noise (mesmo white temporal) jitteriza as posições dos degraus.
      3. O codec libx264 / Instagram HEVC vê um sinal sem coerência espacial
         de banding → os DCT low-AC coeficientes não carregam a "linha de banding".
      4. O gradiente reconstruído é perceptualmente suave (HVS integra espacialmente).

    Flags 't+u' (temporal + uniforme / RPDF): padrão diferente por frame com distribuição
    plana → todos os valores em [-c0s, +c0s] igualmente prováveis. RPDF é superior à
    Gaussiana (default) para dithering pois cobre a faixa inteira de forma uniforme.
    Amplitude c0s=4 (1.6% de 255 ≈ 1.5 LSBs): abaixo do limiar de percepção HVS (~2%).

    Upgrade path (FASE 30B): substituir por void-and-cluster blue-noise PNG texture
    para espectro spatial verdadeiramente blue (energia concentrada em altas freq.).

    Args:
        strength: [0.0–1.0] → mapeado linearmente para c0s [_DITHER_C0S_MIN, _DITHER_C0S_MAX]
                  Default 0.5 → c0s=4 (calibrado para conteúdo SDR 8-bit).
    """
    c0s = int(round(_DITHER_C0S_MIN + strength * (_DITHER_C0S_MAX - _DITHER_C0S_MIN)))
    c0s = max(_DITHER_C0S_MIN, min(_DITHER_C0S_MAX, c0s))
    return f"noise=c0s={c0s}:c0f={_DITHER_FLAGS}"


# ── Video mask detection (FASE 29A) ──────────────────────────────────────────

def _is_video_mask(path: Optional[str]) -> bool:
    """Retorna True se o path aponta para um arquivo de vídeo (não PNG/imagem estática).

    Vídeos de máscara MCTF não precisam de -stream_loop -1 (são frame-sincronizados).
    PNGs estáticos precisam de -stream_loop -1 para durar todo o encode.
    Retorna False para None (sem máscara).
    """
    if not path:
        return False
    return os.path.splitext(path.lower())[1] in {".mp4", ".mkv", ".avi", ".mov", ".webm"}


# ── Public API ────────────────────────────────────────────────────────────────

def build_pre_lut_filtergraph(profile: EnhanceProfile) -> Optional[str]:
    """
    Pipeline de restauração PRÉ-LUT (ordem Hollywood DI):
      deblock → denoise → deband → CAS

    Aplicado em yuv nativo (antes de format=gbrpf32le) para evitar
    problemas de compatibilidade de formato com filtros pós-LUT.

    Ordem profissional:
    1. deblock — remove blocos DCT antes que o denoise os suavize
    2. denoise — reduz ruído temporal/espacial no sinal limpo
    3. deband  — corrige banding (gradiente incorreto)
    4. CAS     — sharpening edge-adaptive (não amplifica artefatos planos)

    Returns None se nenhum filtro estiver ativo.
    """
    if not profile.any_enabled:
        return None

    fragments = []

    # 1. Deblock (primeiro — remove blocos DCT antes do denoise)
    if profile.deblock_enabled:
        fragments.append(_build_deblock())
        logger.debug("enhance pre-lut: deblock filter=%s block=%d", _DEBLOCK_FILTER, _DEBLOCK_BLOCK)

    # 2. Denoise
    if profile.denoise_enabled:
        method = profile.denoise_method
        strength = profile.denoise_strength
        if method == "nlmeans":
            fragments.append(_build_nlmeans(strength))
            logger.debug("enhance pre-lut: nlmeans s=%.2f", strength * _NLM_S_SCALE)
        else:
            fragments.append(_build_hqdn3d(strength))
            logger.debug("enhance pre-lut: hqdn3d (method=%s) strength=%.2f", method, strength)

    # 3. Deband
    if profile.deband_enhance_enabled:
        fragments.append(_build_deband(profile.deband_strength))
        logger.debug(
            "enhance pre-lut: deband thr=%.5f",
            profile.deband_strength * _DEBAND_THR_SCALE,
        )

    # 4. CAS (substitui unsharp — edge-adaptive, não amplifica artefatos)
    if profile.sharpen_enabled:
        fragments.append(_build_cas(profile.sharpen_strength))
        logger.debug(
            "enhance pre-lut: cas strength=%.3f",
            min(_CAS_STR_MAX, profile.sharpen_strength * _CAS_STR_SCALE),
        )

    return ",".join(fragments) if fragments else None


def build_selective_filtergraph(
    profile: EnhanceProfile,
    main_vf_tail: str,
    deband_mask_path: Optional[str] = None,
    sharpen_mask_path: Optional[str] = None,
) -> Optional[tuple]:
    """
    Constrói um filter_complex FFmpeg que aplica deband e CAS de forma
    SELETIVA usando máscaras espaciais PNG (grayscale).

    Onde máscara = 255 (branco/vermelho no JET) → filtro aplicado.
    Onde máscara = 0   (preto/azul no JET)     → frame original preservado.

    Implementação: alphamerge + overlay por stream seletivo.
    - Deblock e denoise permanecem GLOBAIS (sem máscara).
    - Deband seletivo via deband_mask (risco de banding por pixel).
    - CAS seletivo via sharpen_mask (detalhe/borda por pixel).

    Args:
        profile:           EnhanceProfile com flags de cada filtro.
        main_vf_tail:      String de filtros FFmpeg do pipeline principal
                           (lut3d, scale, format, etc.) que vem APÓS o enhance.
        deband_mask_path:  Caminho para PNG grayscale da máscara de deband.
                           None = deband aplicado globalmente (sem máscara).
        sharpen_mask_path: Caminho para PNG grayscale da máscara de sharpen.
                           None = CAS aplicado globalmente (sem máscara).

    Returns:
        Tupla (filter_complex_str, extra_inputs, map_label) ou None se
        nenhum filtro seletivo estiver disponível (fallback para -vf global).

        extra_inputs: lista de args FFmpeg para os inputs de máscara,
                      a serem adicionados APÓS o -i principal do vídeo.
                      Ex: ["-stream_loop", "-1", "-i", "mask.png"]
        map_label:    label de saída do filter_complex, ex: "[vout]"
    """
    has_deband  = bool(deband_mask_path)  and profile.deband_enhance_enabled
    has_sharpen = bool(sharpen_mask_path) and profile.sharpen_enabled

    # Retorna None → caller usa modo global -vf sem alteração
    if not has_deband and not has_sharpen:
        return None

    extra_inputs: list = []
    chains: list = []
    current = "[0:v]"   # stream de vídeo (sempre input 0)
    mask_idx = 1        # próximo índice de input para máscaras

    # ── 1. Deblock (global — sem máscara) ────────────────────────────────────
    if profile.deblock_enabled:
        chains.append(f"{current} {_build_deblock()} [deblocked]")
        current = "[deblocked]"
        logger.debug("selective: deblock (global)")

    # ── 2. Denoise (global — sem máscara) ────────────────────────────────────
    if profile.denoise_enabled:
        if profile.denoise_method == "nlmeans":
            dn = _build_nlmeans(profile.denoise_strength)
        else:
            dn = _build_hqdn3d(profile.denoise_strength)
        chains.append(f"{current} {dn} [denoised]")
        current = "[denoised]"
        logger.debug("selective: denoise (global) method=%s", profile.denoise_method)

    # ── 3. Deband (seletivo ou global) ───────────────────────────────────────
    if profile.deband_enhance_enabled:
        db_frag = _build_deband(profile.deband_strength)
        if has_deband:
            if _is_video_mask(deband_mask_path):
                extra_inputs.extend(["-i", deband_mask_path])                     # vídeo MCTF — sincronizado
            else:
                extra_inputs.extend(["-stream_loop", "-1", "-i", deband_mask_path])  # PNG estático — loop
            chains.append(f"{current} split=2 [orig_db][for_db]")
            chains.append(f"[for_db] {db_frag} [debanded]")
            # alphamerge exige que o primeiro input tenha canal alpha → converter para yuva420p
            chains.append(f"[debanded] format=yuva420p [debanded_yuva]")
            chains.append(f"[{mask_idx}:v] format=gray [dmask]")
            chains.append(f"[debanded_yuva][dmask] alphamerge [debanded_alpha]")
            chains.append(f"[orig_db][debanded_alpha] overlay=format=yuv420 [after_db]")
            current = "[after_db]"
            mask_idx += 1
            logger.debug("selective: deband SELETIVO (mask=%s)", deband_mask_path)
        else:
            chains.append(f"{current} {db_frag} [after_db]")
            current = "[after_db]"
            logger.debug("selective: deband global (sem máscara disponível)")

    # ── 4. CAS (seletivo ou global) ──────────────────────────────────────────
    if profile.sharpen_enabled:
        cas_frag = _build_cas(profile.sharpen_strength)
        if has_sharpen:
            if _is_video_mask(sharpen_mask_path):
                extra_inputs.extend(["-i", sharpen_mask_path])                      # vídeo MCTF — sincronizado
            else:
                extra_inputs.extend(["-stream_loop", "-1", "-i", sharpen_mask_path])  # PNG estático — loop
            chains.append(f"{current} split=2 [orig_cas][for_cas]")
            chains.append(f"[for_cas] {cas_frag} [sharpened]")
            # alphamerge exige que o primeiro input tenha canal alpha → converter para yuva420p
            chains.append(f"[sharpened] format=yuva420p [sharpened_yuva]")
            chains.append(f"[{mask_idx}:v] format=gray [smask]")
            chains.append(f"[sharpened_yuva][smask] alphamerge [sharpened_alpha]")
            chains.append(f"[orig_cas][sharpened_alpha] overlay=format=yuv420 [enhanced]")
            current = "[enhanced]"
            mask_idx += 1
            logger.debug("selective: CAS SELETIVO (mask=%s)", sharpen_mask_path)
        else:
            chains.append(f"{current} {cas_frag} [enhanced]")
            current = "[enhanced]"
            logger.debug("selective: CAS global (sem máscara disponível)")

    # ── 5. Pipeline principal (LUT, scale, format, etc.) ─────────────────────
    chains.append(f"{current} {main_vf_tail} [vout]")

    filter_complex = "; ".join(chains)
    map_label = "[vout]"
    return filter_complex, extra_inputs, map_label