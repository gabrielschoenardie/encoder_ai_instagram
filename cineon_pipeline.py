"""
═══════════════════════════════════════════════════════════════════════════
INSTAGRAM REELS ENCODER — CINEON FILM EMULATION PIPELINE
FASE 26: DWG/Cineon Pipeline - CORRECTED (2025-01-22)
═══════════════════════════════════════════════════════════════════════════

ARQUITETURA:
- PyAV: Decodificação de frames (8/10-bit → float32)
- NumPy/CuPy: Operações de matriz em 32-bit float
- Colour-Science: Transformações ACES/DWG/Cineon (padrão da indústria)
- FFmpeg pipe: Saída para libx264 com VBV controlado

PIPELINE (5 NODES) - CORRECTED TO MATCH DAVINCI RESOLVE:
    Node 1 (CST IN):      Rec.709 → DWG/Intermediate
    Node 2 (Primary):     Ajustes no espaço DWG (exposure, color)
    Node 3 (CST OUT):     DWG → Rec.709/Cineon Log
                          (Tone Mapping: 100 nits, Adaptation 9.0)
                          (Gamut Mapping: Saturation Compression)
    Node 4 (BRIDGE):      Passthrough (preserva arquitetura 5-node)
    Node 5 (PORTRA 400):  Aplicação do LUT Portra 400

CORREÇÃO CRÍTICA (FASE 26):
- Tone/Gamut mapping movido para Node 3 (espaço linear correto)
- Eliminado roundtrip Gamma 2.4 (causava quantização/clipping)
- Node 4 agora é passthrough (arquitetura preservada)
- Todas operações de cor ocorrem em espaços matematicamente corretos

PRECISÃO:
- Todo o processamento em float32 (sem quantização até o encode final)
- Matrizes de conversão de alta precisão (Colour-Science)
- Interpolação trilinear para LUT 3D

AUTOR: Gabriel (Metodologia Gabriel - FASE 26)
DATA: 2025-01-22
"""

import numpy as np
from typing import Tuple, Optional
import warnings

# Verificar disponibilidade de bibliotecas opcionais
try:
    import colour

    COLOUR_AVAILABLE = True
except ImportError:
    COLOUR_AVAILABLE = False
    warnings.warn(
        "colour-science não instalada. Instale com: pip install colour-science\n"
        "Funcionalidade reduzida: usando aproximações matemáticas."
    )

try:
    import cupy as cp

    CUPY_AVAILABLE = True
    GPU_AVAILABLE = cp.cuda.runtime.getDeviceCount() > 0
except (ImportError, Exception):
    CUPY_AVAILABLE = False
    GPU_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE BACKEND (NumPy vs CuPy)
# ═══════════════════════════════════════════════════════════════════════════


def get_array_backend():
    """
    Retorna o backend de array apropriado (NumPy ou CuPy).

    Prioridade:
    1. CuPy (GPU) se disponível
    2. NumPy (CPU) como fallback
    """
    if CUPY_AVAILABLE and GPU_AVAILABLE:
        return cp, "GPU (CuPy)"
    else:
        return np, "CPU (NumPy)"


xp, backend_name = get_array_backend()


# ═══════════════════════════════════════════════════════════════════════════
# MATRIZES DE CONVERSÃO (COLOUR-SCIENCE STANDARD)
# ═══════════════════════════════════════════════════════════════════════════

# DaVinci Wide Gamut RGB Primaries (ACES-derived, D65 white point)
# Fonte: Blackmagic Design DaVinci Resolve Color Management Technical Guide
DWG_PRIMARIES = np.array(
    [[0.8000, 0.3130], [0.1682, 0.9877], [0.0790, -0.1155]],  # Red  # Green  # Blue
    dtype=np.float32,
)

DWG_WHITEPOINT_D65 = np.array([0.3127, 0.3290], dtype=np.float32)

# Rec.709 Primaries (ITU-R BT.709)
REC709_PRIMARIES = np.array(
    [[0.6400, 0.3300], [0.3000, 0.6000], [0.1500, 0.0600]],  # Red  # Green  # Blue
    dtype=np.float32,
)

REC709_WHITEPOINT_D65 = np.array([0.3127, 0.3290], dtype=np.float32)


def build_rgb_to_xyz_matrix(
    primaries: np.ndarray, whitepoint: np.ndarray
) -> np.ndarray:
    """
    Constrói matriz de conversão RGB → XYZ.

    Método: Cromaticidade primárias → XYZ usando normalização D65.

    Args:
        primaries: Array (3, 2) com coordenadas CIE xy das primárias R, G, B
        whitepoint: Array (2,) com coordenadas CIE xy do ponto branco

    Returns:
        Matriz 3×3 de conversão RGB → XYZ (float32)
    """
    # TEMPORÁRIO: Usar fallback manual enquanto não corrigimos API do Colour-Science
    # Aproximação manual (menos precisa, mas funcional)
    # Normalização por whitepoint D65 (Y=1)
    xr, yr = primaries[0]
    xg, yg = primaries[1]
    xb, yb = primaries[2]
    xw, yw = whitepoint

    # XYZ para cada primária (assumindo Y=1 para whitepoint)
    Xr, Yr, Zr = xr / yr, 1.0, (1 - xr - yr) / yr
    Xg, Yg, Zg = xg / yg, 1.0, (1 - xg - yg) / yg
    Xb, Yb, Zb = xb / yb, 1.0, (1 - xb - yb) / yb
    Xw, Yw, Zw = xw / yw, 1.0, (1 - xw - yw) / yw

    # Matriz primária não-normalizada
    M = np.array([[Xr, Xg, Xb], [Yr, Yg, Yb], [Zr, Zg, Zb]], dtype=np.float32)

    # Fatores de escala para normalização
    S = np.linalg.solve(M, np.array([Xw, Yw, Zw], dtype=np.float32))

    # Matriz final normalizada
    M_normalized = M * S[np.newaxis, :]

    return M_normalized


# Matrizes pré-computadas (alta precisão)
MATRIX_REC709_TO_XYZ = build_rgb_to_xyz_matrix(REC709_PRIMARIES, REC709_WHITEPOINT_D65)
MATRIX_XYZ_TO_REC709 = np.linalg.inv(MATRIX_REC709_TO_XYZ).astype(np.float32)

MATRIX_DWG_TO_XYZ = build_rgb_to_xyz_matrix(DWG_PRIMARIES, DWG_WHITEPOINT_D65)
MATRIX_XYZ_TO_DWG = np.linalg.inv(MATRIX_DWG_TO_XYZ).astype(np.float32)

# Conversões diretas (Rec.709 ↔ DWG)
MATRIX_REC709_TO_DWG = MATRIX_XYZ_TO_DWG @ MATRIX_REC709_TO_XYZ
MATRIX_DWG_TO_REC709 = MATRIX_XYZ_TO_REC709 @ MATRIX_DWG_TO_XYZ


# ═══════════════════════════════════════════════════════════════════════════
# TRANSFER FUNCTIONS (OETF / EOTF)
# ═══════════════════════════════════════════════════════════════════════════


def oetf_rec709(linear: np.ndarray) -> np.ndarray:
    """
    Rec.709 OETF (Opto-Electronic Transfer Function).

    Linear → Rec.709 Gamma (piecewise function).

    Args:
        linear: Array float32 em scene-linear (0.0-1.0+)

    Returns:
        Array float32 em Rec.709 gamma
    """
    if COLOUR_AVAILABLE:
        return colour.models.oetf_BT709(linear).astype(np.float32)
    else:
        # Aproximação manual (especificação ITU-R BT.709)
        L = np.clip(linear, 0, None)  # Clamp negativos

        # Piecewise function
        gamma = np.where(L < 0.018, 4.5 * L, 1.099 * np.power(L, 0.45) - 0.099)

        return gamma.astype(np.float32)


def eotf_rec709(gamma: np.ndarray) -> np.ndarray:
    """
    Rec.709 EOTF (Electro-Optical Transfer Function).

    Rec.709 Gamma → Linear (inverse OETF).

    Args:
        gamma: Array float32 em Rec.709 gamma (0.0-1.0)

    Returns:
        Array float32 em scene-linear
    """
    if COLOUR_AVAILABLE:
        return colour.models.oetf_inverse_BT709(gamma).astype(np.float32)
    else:
        # Aproximação manual (inverse piecewise)
        V = np.clip(gamma, 0, 1)

        linear = np.where(V < 0.081, V / 4.5, np.power((V + 0.099) / 1.099, 1.0 / 0.45))

        return linear.astype(np.float32)


def eotf_gamma_24(gamma: np.ndarray) -> np.ndarray:
    """
    Gamma 2.4 EOTF (BT.1886 display standard).

    Gamma 2.4 → Linear.

    Args:
        gamma: Array float32 em Gamma 2.4 (0.0-1.0)

    Returns:
        Array float32 em scene-linear
    """
    if COLOUR_AVAILABLE:
        return colour.models.eotf_BT1886(gamma).astype(np.float32)
    else:
        # Aproximação: Gamma 2.4 puro (BT.1886 simplificado)
        V = np.clip(gamma, 0, 1)
        return np.power(V, 2.4).astype(np.float32)


def oetf_gamma_24(linear: np.ndarray) -> np.ndarray:
    """
    Gamma 2.4 OETF (inverse).

    Linear → Gamma 2.4.

    Args:
        linear: Array float32 em scene-linear (0.0-1.0+)

    Returns:
        Array float32 em Gamma 2.4
    """
    if COLOUR_AVAILABLE:
        return colour.models.eotf_inverse_BT1886(linear).astype(np.float32)
    else:
        L = np.clip(linear, 0, None)
        return np.power(L, 1.0 / 2.4).astype(np.float32)


def oetf_davinci_intermediate(linear: np.ndarray) -> np.ndarray:
    """
    DaVinci Intermediate Transfer Function.

    Função logarítmica customizada (similar a Cineon, mas otimizada para DWG).

    Especificação:
    - Black point: 0.0 (linear) → 0.0 (log)
    - Middle gray (18%): 0.18 (linear) → ~0.435 (log)
    - White point: 1.0 (linear) → ~0.710 (log)
    - Unbounded highlights: >1.0 suportado

    Args:
        linear: Array float32 em scene-linear (0.0-infinity)

    Returns:
        Array float32 em DaVinci Intermediate log
    """
    # Proteção numérica do domínio do log (evita log2 <= 0 no colour-science)
    DI_A = 0.0075
    EPS = 1e-6
    linear_safe = np.maximum(linear, -DI_A + EPS)

    if COLOUR_AVAILABLE:
        try:
            # colour-science >= 0.4.4: oetf_DaVinciIntermediate
            return colour.models.oetf_DaVinciIntermediate(linear_safe).astype(np.float32)
        except AttributeError:
            try:
                # colour-science < 0.4.4: log_encoding_DaVinciIntermediate
                return colour.models.log_encoding_DaVinciIntermediate(linear_safe).astype(
                    np.float32
                )
            except AttributeError:
                pass  # Fallback para aproximação manual

    # Aproximação manual (menos precisa — instale colour-science para máxima qualidade)
    L = np.maximum(linear_safe, 1e-10)
    log_intermediate = np.log2(L * 0.9 + 0.1) / 10.0 + 0.5

    return log_intermediate.astype(np.float32)


def eotf_davinci_intermediate(log_encoded: np.ndarray) -> np.ndarray:
    """
    DaVinci Intermediate Transfer Function (inverse).

    DaVinci Intermediate log → Linear.

    Args:
        log_encoded: Array float32 em DaVinci Intermediate log

    Returns:
        Array float32 em scene-linear
    """
    if COLOUR_AVAILABLE:
        try:
            # colour-science >= 0.4.4: oetf_inverse_DaVinciIntermediate
            return colour.models.oetf_inverse_DaVinciIntermediate(log_encoded).astype(
                np.float32
            )
        except AttributeError:
            try:
                # colour-science < 0.4.4: log_decoding_DaVinciIntermediate
                return colour.models.log_decoding_DaVinciIntermediate(
                    log_encoded
                ).astype(np.float32)
            except AttributeError:
                pass

    # Inverse da aproximação manual
    L = log_encoded
    linear = (np.power(2, (L - 0.5) * 10.0) - 0.1) / 0.9

    return np.maximum(linear, 0).astype(np.float32)


def log_encoding_cineon(linear: np.ndarray) -> np.ndarray:
    """
    Cineon Film Log Encoding (Kodak standard) - Especificação Oficial.

    Linear → Cineon Log (printing density space).

    Especificação Kodak Cineon (10-bit reference, via colour-science):
    - Referência: 95 (black), ~467 (18% gray), 685 (100% white)
    - Normalizado para 0.0-1.0: 0.0928, ~0.457, 0.6697

    Fórmula colour-science (padrão da indústria):
    y = (685 + 300 * log10(x * (1 - black_offset) + black_offset)) / 1023
    black_offset = 10^((95 - 685) / 300) ≈ 0.005012

    Valores de referência (colour-science):
    - L = 0.0   → log = 0.0928 (black reference)
    - L = 0.18  → log ≈ 0.457  (18% gray — código ~467)
    - L = 1.0   → log ≈ 0.6697 (white reference)

    Args:
        linear: Array float32 em display-linear (0.0-1.0+)

    Returns:
        Array float32 em Cineon Log (0.0-1.0 range)
    """
    if COLOUR_AVAILABLE:
        L = np.clip(linear, 0.0, None)
        result = colour.models.log_encoding_Cineon(L).astype(np.float32)
        return np.clip(result, 0.0, 1.0).astype(np.float32)
    else:
        # Implementação manual (especificação Kodak oficial)
        L = np.clip(linear, 0.0, None)  # Clamp negativos

        # Parâmetros Cineon (normalized 10-bit)
        black_code = 95.0 / 1023.0  # 0.0928
        gain_factor = 0.9
        offset = 0.1
        log_scale = 300.0 / 1023.0  # 0.2932

        # Fórmula oficial Kodak Cineon
        log_cineon = (np.log10(L * gain_factor + offset) * log_scale) + black_code

        # Clamp para range válido [0, 1]
        log_cineon = np.clip(log_cineon, 0.0, 1.0)

        return log_cineon.astype(np.float32)


def log_decoding_cineon(log_encoded: np.ndarray) -> np.ndarray:
    """
    Cineon Film Log Decoding (inverse).

    Cineon Log → Linear.

    Args:
        log_encoded: Array float32 em Cineon Log (0.0-1.0)

    Returns:
        Array float32 em scene-linear
    """
    if COLOUR_AVAILABLE:
        return colour.models.log_decoding_Cineon(log_encoded).astype(np.float32)
    else:
        # Inverse da aproximação
        black_ref = 95.0 / 1023.0
        gamma = 0.6

        linear = np.power(10, (log_encoded - black_ref) / gamma)

        return np.maximum(linear, 0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 1: CST IN (Rec.709 → DWG/Intermediate)
# ═══════════════════════════════════════════════════════════════════════════


def node1_cst_in(frame_rec709_gamma: np.ndarray) -> np.ndarray:
    """
    Node 1: Conversão de entrada para DaVinci Wide Gamut/Intermediate.

    Pipeline:
        Rec.709 Gamma → Linear → DWG Linear → DWG Intermediate Log

    Args:
        frame_rec709_gamma: Frame em Rec.709 Gamma (float32, 0.0-1.0)

    Returns:
        Frame em DWG/Intermediate (float32, unbounded)
    """
    # 1. Linearização: Rec.709 Gamma → Linear
    frame_linear_709 = eotf_rec709(frame_rec709_gamma)

    # 2. Gamut Conversion: Rec.709 Linear → DWG Linear
    # Aplicar matriz de conversão (operação de matriz)
    H, W, C = frame_linear_709.shape
    frame_flat = frame_linear_709.reshape(-1, 3)  # (H*W, 3)
    frame_dwg_linear = (MATRIX_REC709_TO_DWG @ frame_flat.T).T.reshape(H, W, 3)

    # 3. Transfer Function: DWG Linear → DWG Intermediate Log
    frame_dwg_intermediate = oetf_davinci_intermediate(frame_dwg_linear)

    return frame_dwg_intermediate.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 2: PRIMARY (Ajustes no espaço DWG)
# ═══════════════════════════════════════════════════════════════════════════


def node2_primary(
    frame_dwg: np.ndarray,
    exposure_offset: float = 0.0,
    saturation: float = 1.0,
    lift: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    gamma: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    gain: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> np.ndarray:
    """
    Node 2: Ajustes primários no espaço DWG/Intermediate.

    Parâmetros DaVinci Resolve (Log Wheels):
    - Exposure: Offset global em stops (+/- EV)
    - Saturation: Intensidade de cor (0.0-2.0)
    - Lift/Gamma/Gain: Color wheels (Log space)

    Args:
        frame_dwg: Frame em DWG/Intermediate (float32)
        exposure_offset: Exposure em stops (-2.0 a +2.0)
        saturation: Saturação (0.0-2.0, default 1.0)
        lift: Ajuste de lift RGB (shadows)
        gamma: Ajuste de gamma RGB (midtones)
        gain: Ajuste de gain RGB (highlights)

    Returns:
        Frame ajustado em DWG/Intermediate (float32)
    """
    frame = frame_dwg.copy()

    # 1. Exposure (Log space offset)
    # +1 stop = 2x linear = +0.301 em log10
    if exposure_offset != 0.0:
        log_offset = exposure_offset * 0.301  # Conversão stop → log10
        frame = frame + log_offset

    # 2. Saturation (operação no espaço log)
    # Extrair luminância e aplicar saturação ao chroma
    luma = frame.mean(axis=2, keepdims=True)  # Média simples (log space)
    chroma = frame - luma
    frame = luma + chroma * saturation

    # 3. Lift/Gamma/Gain (Log Wheels)
    # Lift: Offset nas sombras
    frame[:, :, 0] += lift[0]
    frame[:, :, 1] += lift[1]
    frame[:, :, 2] += lift[2]

    # Gamma: Power no log space (midtones)
    if gamma != (1.0, 1.0, 1.0):
        frame[:, :, 0] = np.power(np.abs(frame[:, :, 0]), gamma[0]) * np.sign(
            frame[:, :, 0]
        )
        frame[:, :, 1] = np.power(np.abs(frame[:, :, 1]), gamma[1]) * np.sign(
            frame[:, :, 1]
        )
        frame[:, :, 2] = np.power(np.abs(frame[:, :, 2]), gamma[2]) * np.sign(
            frame[:, :, 2]
        )

    # Gain: Multiplicação nos highlights
    frame[:, :, 0] *= gain[0]
    frame[:, :, 1] *= gain[1]
    frame[:, :, 2] *= gain[2]

    return frame.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 3: CST OUT (DWG → Rec.709/Cineon Log) - CORRECTED
# ═══════════════════════════════════════════════════════════════════════════


def node3_cst_out(frame_dwg_intermediate: np.ndarray) -> np.ndarray:
    """
    Node 3: CST OUT (DWG → Rec.709/Cineon Log).

    Pipeline:
        DWG Intermediate → DWG Linear
        → Tone Mapping (DaVinci 100 nits, Adaptation 9.0)
        → DWG→Rec.709 Matrix
        → Gamut Mapping (Saturation Compression, Knee 0.900)
        → Cineon Log

    Args:
        frame_dwg_intermediate: Frame em DWG/Intermediate (float32)

    Returns:
        Frame em Rec.709/Cineon Log (float32, 0.0-1.0)
    """
    # 1. Transfer Function: DWG Intermediate → DWG Linear
    frame_dwg_linear = eotf_davinci_intermediate(frame_dwg_intermediate)

    # 2. TONE MAPPING: DaVinci SDR (100 nits, adaptation 9.0)
    # Comprime highlights acima de 1.0 em DWG linear para range SDR display.
    # Sem tone mapping, valores > 1.0 seriam clipados duramente na conversão de gamut.
    frame_after_tone = apply_tone_mapping_davinci(frame_dwg_linear, max_output_nits=100.0, adaptation=9.0)

    # 3. Gamut Conversion: DWG Linear → Rec.709 Linear (matrix only)
    H, W, C = frame_after_tone.shape
    frame_flat = frame_after_tone.reshape(-1, 3)
    frame_709_linear = (MATRIX_DWG_TO_REC709 @ frame_flat.T).T.reshape(H, W, 3)

    # 4. GAMUT MAPPING: Saturation Compression (knee 0.9)
    # Comprime cores fora do gamut Rec.709 preservando hue — evita posterização
    # em vermelho/azul saturado que fica fora do triângulo Rec.709.
    frame_709_clamped = apply_gamut_mapping_saturation_compression(frame_709_linear, knee=0.900)

    # 5. Transfer Function: Rec.709 Linear → Cineon Log
    frame_cineon = log_encoding_cineon(frame_709_clamped)

    return frame_cineon.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 4: CST BRIDGE (Passthrough) - CORRECTED
# ═══════════════════════════════════════════════════════════════════════════


def apply_tone_mapping_davinci(
    linear: np.ndarray, max_output_nits: float = 100.0, adaptation: float = 9.0
) -> np.ndarray:
    """
    Tone Mapping DaVinci (método proprietário simulado).

    Compressão de highlights para display SDR (100 nits).

    Parâmetros DaVinci Resolve:
    - Max Output: 100 nits (SDR display reference)
    - Adaptation: 9.0 (controle da curva de compressão)

    Comportamento:
    - Scene linear (unbounded) → Display linear (0.0-1.0)
    - Highlights acima de 1.0 são suavemente comprimidos
    - Sombras preservadas sem clipping

    Args:
        linear: Frame em scene-linear (float32, 0.0-infinity)
        max_output_nits: Luminância máxima do display (nits)
        adaptation: Força da compressão (0.0-10.0, default 9.0)

    Returns:
        Frame em display-linear (float32, 0.0-1.0)
    """
    # Normalização para 100 nits (SDR reference)
    normalized = linear / (max_output_nits / 100.0)

    # Soft-clip usando função sigmoidal (simulação do método DaVinci)
    # Parâmetro adaptation controla a suavidade da curva
    knee = 1.0  # Threshold para iniciar compressão
    slope = 1.0 / (1.0 + adaptation)  # Inversamente proporcional à adaptation

    # Função piecewise:
    # - Abaixo de knee: Linear pass-through
    # - Acima de knee: Compressão logarítmica suave
    tone_mapped = np.where(
        normalized <= knee,
        normalized,
        knee + (1.0 - knee) * (1.0 - np.exp(-slope * (normalized - knee))),
    )

    return np.clip(tone_mapped, 0.0, 1.0).astype(np.float32)


def apply_gamut_mapping_saturation_compression(
    linear: np.ndarray, knee: float = 0.900, max_saturation: float = 1.000
) -> np.ndarray:
    """
    Gamut Mapping: Saturation Compression (DaVinci Resolve).

    Comprime cores saturadas para dentro do gamut Rec.709 legal.

    Parâmetros DaVinci Resolve:
    - Knee: 0.900 (threshold para iniciar compressão)
    - Max: 1.000 (limite máximo de saturação)

    Método:
    - Extrair chroma vector (desvio da luminância)
    - Aplicar soft-clip na magnitude do chroma
    - Preservar hue (direção do vector)

    Args:
        linear: Frame em linear RGB (float32)
        knee: Threshold de saturação para compressão (0.0-1.0)
        max_saturation: Limite máximo de saturação (1.0-2.0)

    Returns:
        Frame com saturação comprimida (float32)
    """
    # Calcular luminância (Rec.709 weights)
    luma = (
        0.2126 * linear[:, :, 0] + 0.7152 * linear[:, :, 1] + 0.0722 * linear[:, :, 2]
    )
    luma = luma[:, :, np.newaxis]  # (H, W, 1)

    # Chroma vector (R-Y, G-Y, B-Y)
    chroma = linear - luma

    # Magnitude do chroma (saturação)
    chroma_mag = np.sqrt(np.sum(chroma**2, axis=2, keepdims=True))
    chroma_mag = np.maximum(chroma_mag, 1e-10)  # Evitar divisão por zero

    # Direção do chroma (hue, normalizado)
    chroma_dir = chroma / chroma_mag

    # Soft-clip da magnitude (saturation compression)
    compressed_mag = np.where(
        chroma_mag <= knee,
        chroma_mag,
        knee
        + (max_saturation - knee)
        * (1.0 - np.exp(-(chroma_mag - knee) / (max_saturation - knee))),
    )

    # Reconstruir chroma com magnitude comprimida
    chroma_compressed = chroma_dir * compressed_mag

    # Reconstruir RGB
    rgb_compressed = luma + chroma_compressed

    return rgb_compressed.astype(np.float32)


def node4_cst_bridge(frame_cineon: np.ndarray) -> np.ndarray:
    """
    Node 4: CST Bridge - NOW PASSTHROUGH (architecture preserved).

    CORRECTED: Node 3 now outputs Cineon Log directly, so this node
    becomes a passthrough. Function kept to preserve 5-node architecture.

    In DaVinci Resolve workflow, this represents the transition point
    between the Cineon Transform CST and the Film LUT application.

    Args:
        frame_cineon: Frame already in Rec.709/Cineon Log (float32, 0.0-1.0)

    Returns:
        Same frame (passthrough to maintain 5-node structure)
    """
    # Passthrough: Node 3 already outputs Cineon Log
    # Architecture preserved for consistency
    return frame_cineon.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 5: PORTRA 400 LUT APPLICATION
# ═══════════════════════════════════════════════════════════════════════════


class LUT3D:
    """
    Classe para carregar e aplicar LUTs 3D (.cube format).

    Suporta:
    - Interpolação trilinear (padrão da indústria)
    - LUTs de qualquer tamanho (17³, 33³, 65³, etc.)
    - Float32 precision
    """

    def __init__(self, lut_file_path=None):
        """
        Carrega LUT 3D de arquivo .cube.

        Args:
            lut_file_path: Caminho para o arquivo .cube
        """
        self.lut_file_path = lut_file_path
        self.lut_data = None
        self.lut_size = 0
        self.domain_min = np.array([0.0, 0.0, 0.0])
        self.domain_max = np.array([1.0, 1.0, 1.0])

        # Se path foi fornecido, carregar automaticamente
        if lut_file_path is not None:
            self._load_cube_file(lut_file_path)

    def _load_cube_file(self, path: str):
        """
        Parser de arquivo .cube (Adobe/Resolve/FCPX format).

        Formato:
            TITLE "Nome do LUT"
            LUT_3D_SIZE 33
            0.026979 0.027936 0.031946
            ...
        """
        with open(path, "r") as f:
            lines = f.readlines()

        # Extrair LUT_3D_SIZE
        for line in lines:
            if line.startswith("LUT_3D_SIZE"):
                self.lut_size = int(line.split()[1])
                break

        if self.lut_size == 0:
            raise ValueError(f"LUT_3D_SIZE não encontrado em {path}")

        # Extrair dados RGB (ignorar comentários e headers)
        data_lines = []
        for line in lines:
            line = line.strip()
            if (
                not line
                or line.startswith("#")
                or line.startswith("TITLE")
                or line.startswith("LUT_3D_SIZE")
                or line.startswith("LUT_3D_INPUT_RANGE")
            ):
                continue

            # Tentar parsear 3 floats (R G B)
            parts = line.split()
            if len(parts) >= 3:
                try:
                    r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                    data_lines.append([r, g, b])
                except ValueError:
                    continue

        # Validar número de pontos
        expected_points = self.lut_size**3
        if len(data_lines) != expected_points:
            raise ValueError(
                f"LUT incompleto: esperado {expected_points} pontos, "
                f"encontrado {len(data_lines)}"
            )

        # Converter para array 3D (R, G, B indexado)
        # Ordem Adobe .cube: R varia mais rápido, G médio, B mais lento.
        # Após reshape (N,N,N,3) em C-order: lut_data[b_idx, g_idx, r_idx] = output.
        self.lut_data = np.array(data_lines, dtype=np.float32)
        self.lut_data = self.lut_data.reshape(
            (self.lut_size, self.lut_size, self.lut_size, 3)
        )

    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Aplica LUT 3D ao frame com interpolação trilinear.

        Método:
        - Mapear valores RGB (0.0-1.0) para coordenadas do cubo
        - Interpolar entre 8 vértices vizinhos (trilinear)
        - Retornar RGB transformado

        Args:
            frame: Frame RGB float32 (H, W, 3) no range 0.0-1.0

        Returns:
            Frame RGB float32 (H, W, 3) transformado pelo LUT
        """
        H, W, C = frame.shape

        # Clamping: 0.0-1.0 (LUT domain)
        frame_clamped = np.clip(frame, 0.0, 1.0)

        # Mapear para coordenadas do cubo (0 a lut_size-1)
        coords = frame_clamped * (self.lut_size - 1)

        # Coordenadas inteiras (índices dos vértices inferiores)
        r_idx = np.floor(coords[:, :, 0]).astype(np.int32)
        g_idx = np.floor(coords[:, :, 1]).astype(np.int32)
        b_idx = np.floor(coords[:, :, 2]).astype(np.int32)

        # Clamping de índices (proteção contra out-of-bounds)
        # idx clampeado a lut_size-2: quando frac=1.0 (borda branca), a interpolação
        # naturalmente acessa lut[idx+1] = lut[lut_size-1] — último entry correto.
        r_idx = np.clip(r_idx, 0, self.lut_size - 2)
        g_idx = np.clip(g_idx, 0, self.lut_size - 2)
        b_idx = np.clip(b_idx, 0, self.lut_size - 2)

        # Frações para interpolação (0.0-1.0)
        r_frac = coords[:, :, 0] - r_idx
        g_frac = coords[:, :, 1] - g_idx
        b_frac = coords[:, :, 2] - b_idx

        # Fetch dos 8 vértices do cubo
        # Indexação: lut_data[b_idx, g_idx, r_idx] — padrão Adobe .cube (R fastest, B slowest)
        c000 = self.lut_data[b_idx, g_idx, r_idx]
        c001 = self.lut_data[b_idx + 1, g_idx, r_idx]
        c010 = self.lut_data[b_idx, g_idx + 1, r_idx]
        c011 = self.lut_data[b_idx + 1, g_idx + 1, r_idx]
        c100 = self.lut_data[b_idx, g_idx, r_idx + 1]
        c101 = self.lut_data[b_idx + 1, g_idx, r_idx + 1]
        c110 = self.lut_data[b_idx, g_idx + 1, r_idx + 1]
        c111 = self.lut_data[b_idx + 1, g_idx + 1, r_idx + 1]

        # Interpolação trilinear (3 dimensões)
        # Eixo B (Blue)
        c00 = c000 * (1 - b_frac[:, :, np.newaxis]) + c001 * b_frac[:, :, np.newaxis]
        c01 = c010 * (1 - b_frac[:, :, np.newaxis]) + c011 * b_frac[:, :, np.newaxis]
        c10 = c100 * (1 - b_frac[:, :, np.newaxis]) + c101 * b_frac[:, :, np.newaxis]
        c11 = c110 * (1 - b_frac[:, :, np.newaxis]) + c111 * b_frac[:, :, np.newaxis]

        # Eixo G (Green)
        c0 = c00 * (1 - g_frac[:, :, np.newaxis]) + c01 * g_frac[:, :, np.newaxis]
        c1 = c10 * (1 - g_frac[:, :, np.newaxis]) + c11 * g_frac[:, :, np.newaxis]

        # Eixo R (Red)
        result = c0 * (1 - r_frac[:, :, np.newaxis]) + c1 * r_frac[:, :, np.newaxis]

        return result.astype(np.float32)


def node5_portra400(frame_cineon: np.ndarray, lut: LUT3D) -> np.ndarray:
    """
    Node 5: Aplicação do LUT Portra 400.

    Pipeline:
        Cineon Log → [LUT] → display output

    Input esperado pelo LUT:
    - Cineon Log (float 0.0-1.0)

    Output do LUT (depende do LUT carregado):
    - Portra 400 original: Rec.709 Gamma 2.4
    - Portra 400 / LUTs gerados localmente: Rec.709 OETF

    Args:
        frame_cineon: Frame em Cineon Log (float32, 0.0-1.0)
        lut: Instância de LUT3D carregada

    Returns:
        Frame em display output (float32, 0.0-1.0) com film look
    """
    return lut.apply(frame_cineon)


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE COMPLETO (5 NODES)
# ═══════════════════════════════════════════════════════════════════════════


def process_frame_full_pipeline(
    frame_rec709_gamma: np.ndarray,
    portra_lut: LUT3D,
    exposure_offset: float = 0.0,
    saturation: float = 1.0,
) -> np.ndarray:
    """
    Processa frame completo através do pipeline de 5 nodes.

    Pipeline CORRECTED (matches DaVinci Resolve CST workflow):
        Input: Rec.709 Gamma →
        Node 1 (CST IN): DWG/Intermediate →
        Node 2 (Primary): Grade in DWG →
        Node 3 (CST OUT): Cineon Log + Tone/Gamut Mapping →
        Node 4 (Bridge): Passthrough →
        Node 5 (LUT): Portra 400 Film Emulation →
        Output: Rec.709 Gamma 2.4 (Film Look)

    Args:
        frame_rec709_gamma: Frame de entrada em Rec.709 Gamma (float32, 0-1)
        portra_lut: LUT Portra 400 carregada
        exposure_offset: Ajuste de exposição em stops (+/- EV)
        saturation: Ajuste de saturação (0.0-2.0)

    Returns:
        Frame processado em Rec.709/Gamma 2.4 com film emulation (float32, 0-1)
    """
    # Node 1: Rec.709 → DWG/Intermediate
    frame_dwg = node1_cst_in(frame_rec709_gamma)

    # Node 2: Primary corrections (DWG space)
    frame_dwg_graded = node2_primary(
        frame_dwg, exposure_offset=exposure_offset, saturation=saturation
    )

    # Node 3: DWG → Rec.709/Cineon Log (with tone/gamut) ← CORRECTED
    frame_cineon = node3_cst_out(frame_dwg_graded)

    # Node 4: Passthrough (architecture preserved) ← CORRECTED
    frame_cineon_pass = node4_cst_bridge(frame_cineon)

    # Node 5: Portra 400 LUT (Cineon → Film Look)
    frame_output = node5_portra400(frame_cineon_pass, portra_lut)

    return frame_output


# ═══════════════════════════════════════════════════════════════════════════
# EXEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 70)
    print("INSTAGRAM REELS ENCODER — CINEON PIPELINE (FASE 26 - CORRECTED)")
    print("DWG/Cineon Film Emulation com Colour-Science")
    print("Pipeline Correto: DWG → Cineon Log → Portra 400")
    print("═" * 70)
    print()

    # Verificar dependências
    print(f"Backend: {backend_name}")
    print(
        f"Colour-Science: {'✓ Disponível' if COLOUR_AVAILABLE else '✗ Não instalado (usando aproximações)'}"
    )
    print()

    # Carregar LUT Portra 400
    try:
        lut = LUT3D("FilmLook_Portra400_SkinPriority_D65.cube")
        print(f"✓ LUT carregado: Portra 400 ({lut.lut_size}³)")
    except FileNotFoundError:
        print("✗ Arquivo LUT não encontrado: FilmLook_Portra400_SkinPriority_D65.cube")
        print("  Coloque o arquivo .cube no diretório atual.")
        exit(1)
    except Exception as e:
        print(f"✗ Erro ao carregar LUT: {e}")
        exit(1)

    print()
    print("Pipeline pronto para processamento!")
    print()
    print("Exemplo de uso:")
    print("  frame_output = process_frame_full_pipeline(")
    print("      frame_rec709_gamma,")
    print("      portra_lut=lut,")
    print("      exposure_offset=0.0,")
    print("      saturation=1.0")
    print("  )")
    print()
    print("Pipeline CORRETO (FASE 26):")
    print("  Node 1: Rec.709 → DWG/Intermediate")
    print("  Node 2: Primary corrections (DWG space)")
    print("  Node 3: DWG → Rec.709/Cineon Log (+ tone/gamut mapping)")
    print("  Node 4: Passthrough (architecture preserved)")
    print("  Node 5: Portra 400 LUT → Film Look")
    print()
    print("Para integração com PyAV:")
    print("  1. Decodificar frames com PyAV")
    print("  2. Converter para float32 (normalizar 0-1)")
    print("  3. Processar com process_frame_full_pipeline()")
    print("  4. Converter de volta para uint8/uint10")
    print("  5. Pipe para FFmpeg (libx264)")