# Cineon Pipeline — Referência Técnica Completa

Pipeline de 5 nós do `Reels_Encoder_v2_FINAL.py` — Cineon Mode.
Processamento per-frame em float32 via PyAV + NumPy, estilo DaVinci Resolve.

**Stack obrigatório:** `colour-science`, `numpy`, `opencv-python`, `av` (PyAV), `scipy`

---

## Visão geral do fluxo

```
Frame uint8 (PyAV decode)
        │
        ▼
[uint8 → float32 normalizado 0–1]
        │
        ▼
[Nó 1] DWG Input Transform
  BT.709 gamma decode → linear scene-referred
  Linear BT.709 → ACEScg (wide gamut working space)
        │
        ▼
[Nó 2] Tone & Gamut Mapping
  S-curve adaptativa (skin_ratio + color_temp_proxy do analyze_source)
  Soft-clip out-of-gamut
  ACEScg → linear BT.709
        │
        ▼
[Nó 3] Cineon Log Encoding
  Linear → Cineon log (intermediário para compatibilidade da LUT)
        │
        ▼
[Nó 4] LUT Application
  FilmLook_Portra400_SkinPriority_D65.cube (tetrahedral)
  colour-science: LUT3D.apply()
        │
        ▼
[MCTF] Temporal Consistency (Farneback + EMA)
  Alinhamento óptico + blend EMA com frame anterior
        │
        ▼
[Nó 5] Output
  RPDF dithering (_build_dither())
  float32 → uint8 [0–255]
  → PyAV encode → libx264 → MP4
```

---

## Estado entre frames

O pipeline é **stateful** — o MCTF precisa do frame anterior graded.
Reinicializar ao começar um novo Reel (não entre frames do mesmo clipe).

```python
@dataclass
class CineonState:
    prev_graded: np.ndarray | None = None   # último frame pós-LUT, float32
    lut3d:       object           = None    # colour LUT3D carregada uma vez
    features:    dict             = None    # saída de analyze_source.analyze()
    ema_alpha:   float            = 0.7     # derivado de temporal_noise

def reset_state() -> CineonState:
    return CineonState()
```

---

## Pré-processamento: uint8 → float32

```python
import av
import numpy as np

def frame_to_float32(av_frame: av.VideoFrame) -> np.ndarray:
    """
    Converte frame PyAV para array float32 normalizado [0.0, 1.0].
    Formato de trabalho: RGB float32 HWC.
    """
    bgr_uint8 = av_frame.to_ndarray(format="bgr24")
    rgb_uint8 = bgr_uint8[..., ::-1]                        # BGR → RGB
    return (rgb_uint8.astype(np.float32) / 255.0)
```

---

## Nó 1 — DWG Input Transform

### Objetivo
Linearizar o gamma BT.709 e expandir para o espaço de trabalho wide gamut
(ACEScg / AP1). O wide gamut evita clipping de primárias saturadas durante
as operações de tone mapping e gamut mapping que vêm a seguir.

### Fórmulas

**BT.709 gamma decode (OETF inversa):**

```
Para V ≤ 0.081:    L = V / 4.5
Para V > 0.081:    L = ((V + 0.099) / 1.099)^(1/0.45)
```

**Matrix BT.709 → ACEScg (via colour-science):**

```
M_BT709_to_ACES = colour.matrix_RGB_to_RGB(
    colour.RGB_COLOURSPACES['ITU-R BT.709'],
    colour.RGB_COLOURSPACES['ACEScg']
)
```

Valores da matrix (referência, D65 → D60 adapt. Bradford):
```
[ 0.6131,  0.3395,  0.0474 ]
[ 0.0701,  0.9163,  0.0136 ]
[ 0.0206,  0.1096,  0.8698 ]
```

### Implementação

```python
import colour
import numpy as np

# Cache da matrix — calcular uma vez, reusar
_M_BT709_TO_ACES: np.ndarray | None = None

def _get_bt709_to_aces_matrix() -> np.ndarray:
    global _M_BT709_TO_ACES
    if _M_BT709_TO_ACES is None:
        _M_BT709_TO_ACES = colour.matrix_RGB_to_RGB(
            colour.RGB_COLOURSPACES['ITU-R BT.709'],
            colour.RGB_COLOURSPACES['ACEScg'],
            chromatic_adaptation_transform='Bradford',
        )
    return _M_BT709_TO_ACES


def node1_dwg_input(rgb_nonlinear: np.ndarray) -> np.ndarray:
    """
    Nó 1: BT.709 gamma decode + expansão para ACEScg (DWG proxy).

    Input:  RGB float32 [0, 1] com gamma BT.709
    Output: RGB float32 scene-linear em ACEScg (pode exceder [0,1])
    """
    # 1a. BT.709 OETF inversa → linear (colour-science)
    rgb_linear = colour.cctf_decoding(rgb_nonlinear, function='ITU-R BT.709')
    rgb_linear = np.maximum(rgb_linear, 0.0)   # eliminar negativos de rounding

    # 1b. Matriz BT.709 linear → ACEScg
    M  = _get_bt709_to_aces_matrix()
    out = np.einsum('...c,dc->...d', rgb_linear, M)

    return out.astype(np.float32)
```

### Notas de log footage

Se o source for S-Log2, S-Log3, C-Log, V-Log: substituir o decode BT.709
pela função de decode específica antes da matrix. colour-science suporta:

```python
# S-Log2 (Sony)
colour.cctf_decoding(v, function='S-Log2')

# S-Log3 (Sony)
colour.cctf_decoding(v, function='S-Log3')

# C-Log (Canon) — usar LogC3 como proxy
colour.cctf_decoding(v, function='Log3G10')  # aproximação
```

---

## Nó 2 — Tone & Gamut Mapping

### Objetivo
Comprimir highlights HDR que excedem [0, 1] após a expansão de gamut, aplicar
S-curve adaptativa baseada nos features do `analyze_source.py`, e mapear de
volta para BT.709 linear (ready para o Cineon log no Nó 3).

### S-curve adaptativa

A S-curve usa a fórmula de Hable (Uncharted 2), com parâmetros derivados das
features de análise:

```
f(x) = (x * (A*x + C*B) + D*E) / (x * (A*x + B) + D*F) - E/F

Onde A-F são parâmetros que controlam shoulder (highlights) e toe (shadows).
```

Os parâmetros são ajustados dinamicamente:

```python
def _hable_partial(x: np.ndarray, A: float, B: float, C: float,
                   D: float, E: float, F: float) -> np.ndarray:
    return (x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F) - E / F


def _build_tone_params(skin_ratio: float, color_temp_proxy: float) -> dict:
    """
    Deriva parâmetros da S-curve Hable a partir de features de análise.
    skin_ratio alto → shoulder mais suave (preserva gradiente de pele).
    color_temp_proxy > 1.3 → compensação de white balance warm.
    """
    # Shoulder strength: reduz com skin_ratio (menos compressão de highlights perto de pele)
    shoulder = max(0.10, 0.22 - skin_ratio * 0.08)

    # Toe strength: fixo — sombras sempre preservadas
    toe_strength = 0.30

    params = {
        "A": shoulder,           # shoulder strength
        "B": 0.50,               # linear strength
        "C": 0.10,               # linear angle
        "D": toe_strength,       # toe strength
        "E": 0.02,               # toe numerator
        "F": 0.30,               # toe denominator
        "W": 11.2,               # linear white point
    }

    # Compensação de white balance para fonte quente (warm shift)
    if color_temp_proxy > 1.3:
        # Leve resfriamento proporcional ao desvio
        wb_shift = min((color_temp_proxy - 1.3) * 0.05, 0.08)
        params["wb_r_gain"] = 1.0 - wb_shift
        params["wb_b_gain"] = 1.0 + wb_shift * 0.7
    else:
        params["wb_r_gain"] = 1.0
        params["wb_b_gain"] = 1.0

    return params


def _soft_clip(x: np.ndarray, limit: float = 1.0, softness: float = 0.05) -> np.ndarray:
    """
    Soft clip: comprime suavemente acima de (limit - softness) em vez de hard clip.
    Preserva detalhe de highlight sem clipping abrupto.
    """
    knee = limit - softness
    above = x > knee
    x_soft = x.copy()
    # Curva quadrática suave no shoulder
    t = (x[above] - knee) / softness
    x_soft[above] = knee + softness * (2 * t - t * t) / 2.0
    return np.clip(x_soft, 0.0, limit)
```

### Gamut mapping ACEScg → BT.709

```python
_M_ACES_TO_BT709: np.ndarray | None = None

def _get_aces_to_bt709_matrix() -> np.ndarray:
    global _M_ACES_TO_BT709
    if _M_ACES_TO_BT709 is None:
        _M_ACES_TO_BT709 = colour.matrix_RGB_to_RGB(
            colour.RGB_COLOURSPACES['ACEScg'],
            colour.RGB_COLOURSPACES['ITU-R BT.709'],
            chromatic_adaptation_transform='Bradford',
        )
    return _M_ACES_TO_BT709
```

### Implementação do Nó 2

```python
def node2_tone_gamut(rgb_aces: np.ndarray, features: dict) -> np.ndarray:
    """
    Nó 2: Tone mapping (Hable adaptativo) + gamut mapping ACEScg → BT.709 linear.

    Input:  RGB float32 ACEScg scene-linear (pode exceder [0,1])
    Output: RGB float32 BT.709 linear [0, 1]
    """
    skin_ratio      = features.get("skin_ratio",       0.0)
    color_temp_proxy = features.get("color_temp_proxy", 1.0)

    p = _build_tone_params(skin_ratio, color_temp_proxy)

    # Correção de white balance antes do tone map
    rgb_wb = rgb_aces.copy()
    rgb_wb[..., 0] *= p["wb_r_gain"]
    rgb_wb[..., 2] *= p["wb_b_gain"]

    # S-curve Hable
    A, B, C, D, E, F, W = p["A"], p["B"], p["C"], p["D"], p["E"], p["F"], p["W"]
    rgb_tm = _hable_partial(rgb_wb, A, B, C, D, E, F)
    white  = _hable_partial(np.full_like(rgb_wb, W), A, B, C, D, E, F)
    rgb_tm = rgb_tm / (white + 1e-10)   # normalizar pelo white point

    # Soft clip (previne hard-clip em highlights residuais)
    rgb_tm = _soft_clip(rgb_tm, limit=1.0, softness=0.04)

    # Gamut mapping ACEScg → BT.709 linear
    M   = _get_aces_to_bt709_matrix()
    out = np.einsum('...c,dc->...d', rgb_tm, M)

    # Garantir range válido pós-matrix (out-of-gamut residual → soft clip)
    return np.clip(out, 0.0, 1.0).astype(np.float32)
```

---

## Nó 3 — Cineon Log Encoding

### Objetivo
Converter de linear BT.709 para Cineon log antes de aplicar a LUT. A
`FilmLook_Portra400_SkinPriority_D65.cube` foi construída esperando input
em Cineon log — aplicá-la em linear produziria resultado incorreto.

### Fórmula

A fórmula Cineon log normalizada usada neste pipeline:

```
Encode (linear → log):
    out = log10(max(lin, 1e-10)) / (0.002 × 1023) + 0.669

Decode (log → linear):
    lin = 10^((log - 0.669) × 0.002 × 1023)
```

**Derivação dos constantes:**
- `0.669` = ponto de referência de brancos (code value 685 / 1023 ≈ 0.669)
- `0.002` = incremento de densidade de referência do filme Cineon original
- `1023` = range 10-bit normalizado para [0, 1]

**Pontos de controle (derivados da fórmula acima — slope = 0.002×1023 = 2.046):**
```
lin = 0.0    → log = 0.000  (black point, após np.clip — fórmula crua dá negativo)
lin = 0.18   → log ≈ 0.305  (18% grey)
lin = 1.0    → log = 0.669  (white reference)
lin = 2.0    → log ≈ 0.816  (1 stop acima do branco)
```

> **Nota de reconciliação:** versões anteriores deste documento listavam
> 0.18→0.435 e 2.0→0.718, valores que **não** seguem da fórmula `log10(lin)/2.046
> + 0.669` (que produz 0.305 e 0.816). Os asserts de `_validate_cineon_constants()`
> abaixo foram alinhados aos valores corretos — antes disso, a função abortava o
> pipeline na inicialização com `AssertionError`. Esta é a fórmula/curva para a
> qual a `FilmLook_Portra400_SkinPriority_D65.cube` foi construída.

### Implementação

```python
# Constantes Cineon log
_CINEON_REF_WHITE  = 0.669        # code value normalizado para lin=1.0
_CINEON_DENSITY    = 0.002        # incremento de densidade de referência
_CINEON_RANGE      = 1023.0       # range 10-bit (normalizado para [0,1])
_CINEON_SLOPE      = _CINEON_DENSITY * _CINEON_RANGE   # = 2.046


def cineon_encode(linear: np.ndarray) -> np.ndarray:
    """
    Nó 3: Linear BT.709 [0, 1] → Cineon log [0, 1].
    Clip suave abaixo de 1e-10 para evitar log10(0).
    """
    lin_safe = np.maximum(linear, 1e-10)
    log      = np.log10(lin_safe) / _CINEON_SLOPE + _CINEON_REF_WHITE
    return np.clip(log, 0.0, 1.0).astype(np.float32)


def cineon_decode(log: np.ndarray) -> np.ndarray:
    """Inverso: Cineon log [0, 1] → linear [0, 1]."""
    return np.power(10.0, (log - _CINEON_REF_WHITE) * _CINEON_SLOPE).astype(np.float32)


# Checkpoint de validação
def _validate_cineon_constants():
    """Verificar pontos de controle da fórmula. Chamar uma vez na inicialização."""
    checks = [(0.18, 0.305, 0.005), (1.0, 0.669, 0.001), (2.0, 0.816, 0.005)]
    for lin, expected_log, tol in checks:
        got = float(cineon_encode(np.array([lin], dtype=np.float32))[0])
        assert abs(got - expected_log) < tol, \
            f"Cineon constant error: lin={lin} → log={got:.4f} (expected {expected_log}±{tol})"
```

---

## Nó 4 — LUT Application (Portra400)

### Objetivo
Aplicar a `FilmLook_Portra400_SkinPriority_D65.cube` via interpolação tetraédrica.
A LUT foi construída para input em **Cineon log** — é exatamente o que o Nó 3 produz.

### Carregamento da LUT (uma vez, não por frame)

```python
import colour

def load_lut(lut_path: str) -> colour.LUT3D:
    """
    Carrega a LUT 3D uma vez na inicialização do pipeline.
    colour-science suporta .cube (Adobe/Resolve), .3dl e .clf.
    """
    lut = colour.io.read_LUT(lut_path)

    if not isinstance(lut, colour.LUT3D):
        # Converter LUT1D ou LUT sequence se necessário
        if hasattr(lut, 'LUTs'):
            lut = colour.LUTSequence(*lut.LUTs).as_LUT(colour.LUT3D)
        else:
            raise TypeError(f"LUT não é 3D: {type(lut)}")

    return lut
```

### Aplicação por frame

```python
def node4_lut(cineon_frame: np.ndarray, lut3d: colour.LUT3D) -> np.ndarray:
    """
    Nó 4: Aplicar LUT 3D Portra400 com interpolação tetraédrica.

    Input:  RGB float32 Cineon log [0, 1]
    Output: RGB float32 graded [0, 1]
    """
    # colour-science: LUT3D.apply() aceita array HWC float32
    graded = lut3d.apply(
        cineon_frame,
        interpolator=colour.algebra.table_interpolation_tetrahedral,
    )
    return np.clip(graded, 0.0, 1.0).astype(np.float32)
```

### Validação da LUT antes do pipeline

```python
def validate_lut_gamut(lut3d: colour.LUT3D, n_samples: int = 1000) -> dict:
    """
    Verifica se a LUT tem output fora de [0, 1] (indica construção incorreta).
    Amostras aleatórias no domain da LUT.
    """
    samples = np.random.uniform(0.0, 1.0, (n_samples, 3)).astype(np.float32)
    output  = lut3d.apply(samples,
                          interpolator=colour.algebra.table_interpolation_tetrahedral)
    out_of_gamut = (output < 0.0) | (output > 1.0)
    ratio = float(out_of_gamut.any(axis=1).mean())
    return {
        "out_of_gamut_ratio": ratio,
        "max_value":  float(output.max()),
        "min_value":  float(output.min()),
        "status":     "OK" if ratio < 0.01 else "WARNING — LUT tem output fora de gamut",
    }
```

---

## MCTF — Temporal Consistency

### Posição no pipeline
O MCTF é aplicado **após o Nó 4** (pós-LUT, pré-output). Trabalha no espaço
graded para que a consistência temporal preserve a aparência final, não o linear.

### Derivação do peso EMA a partir de `temporal_noise`

O peso EMA é derivado do `temporal_noise` do `analyze_source.py` uma única vez
na inicialização, não por frame:

```python
def derive_ema_alpha(temporal_noise: float) -> float:
    """
    Mapeia temporal_noise do analyze_source para peso EMA do MCTF.
    temporal_noise baixo = source estável → EMA agressiva (mais smoothing).
    temporal_noise alto  = muita variação  → EMA suave (preservar transições).
    """
    if temporal_noise < 5.0:
        return 0.90    # fonte muito estável (tripé, pouca variação)
    elif temporal_noise < 12.0:
        return 0.70    # variação moderada (handheld leve, vento)
    else:
        return 0.50    # variação alta (movimento, flash, cortes rápidos)
```

### Alinhamento com Farneback optical flow

```python
import cv2

def _farneback_warp(frame_curr: np.ndarray,
                    frame_prev: np.ndarray) -> np.ndarray:
    """
    Alinha frame_curr para frame_prev via Farneback optical flow + remap.
    Ambos os frames: float32 RGB [0, 1].
    Retorna frame_curr warpado para o espaço de frame_prev.
    """
    # Converter para uint8 gray para optical flow (mais rápido e suficiente)
    curr_gray = (frame_curr[..., 0] * 0.2126 +
                 frame_curr[..., 1] * 0.7152 +
                 frame_curr[..., 2] * 0.0722)
    prev_gray = (frame_prev[..., 0] * 0.2126 +
                 frame_prev[..., 1] * 0.7152 +
                 frame_prev[..., 2] * 0.0722)

    curr_u8 = np.clip(curr_gray * 255, 0, 255).astype(np.uint8)
    prev_u8 = np.clip(prev_gray * 255, 0, 255).astype(np.uint8)

    flow = cv2.calcOpticalFlowFarneback(
        prev_u8, curr_u8, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2,
        flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN,
    )

    h, w = frame_curr.shape[:2]
    grid_x, grid_y = np.meshgrid(np.arange(w, dtype=np.float32),
                                  np.arange(h, dtype=np.float32))

    map_x = np.clip(grid_x + flow[..., 0], 0, w - 1)
    map_y = np.clip(grid_y + flow[..., 1], 0, h - 1)

    warped = cv2.remap(frame_curr, map_x, map_y,
                       interpolation=cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    return warped.astype(np.float32)


def mctf_ema(frame_graded: np.ndarray,
             state: 'CineonState') -> tuple[np.ndarray, 'CineonState']:
    """
    MCTF: alinha frame anterior e aplica EMA para consistência temporal.

    Desativar se motion_magnitude > 25 (Farneback falha com movimento extremo).
    """
    if state.prev_graded is None:
        # Primeiro frame — sem referência, retornar sem blend
        state.prev_graded = frame_graded.copy()
        return frame_graded, state

    # Alinhar frame anterior para o frame atual
    prev_aligned = _farneback_warp(state.prev_graded, frame_graded)

    # EMA blend
    alpha  = state.ema_alpha
    blended = alpha * prev_aligned + (1.0 - alpha) * frame_graded

    state.prev_graded = blended.copy()
    return blended.astype(np.float32), state
```

### Quando desativar o MCTF

```python
def should_use_mctf(features: dict) -> bool:
    """
    MCTF é contraproducente com muito movimento — Farneback gera ghosting.
    """
    motion = features.get("motion_magnitude", 0.0)
    return motion <= 25.0
```

---

## Nó 5 — Output com RPDF Dithering

### Objetivo
Converter float32 [0, 1] para uint8 [0, 255] com dithering RPDF para prevenir
banding em gradientes suaves.

### RPDF vs TPDF

```
RPDF (Rectangular): ruído uniforme ±0.5 LSB — mais simples, menos correlacionado
TPDF (Triangular):  soma de dois RPDF — espectro mais plano, preferido em áudio
```

Para vídeo 8-bit com conteúdo cinematográfico, RPDF é suficiente e tem overhead
menor. `_build_dither()` usa RPDF conforme implementado no encoder.

### Implementação

```python
def _build_dither(shape: tuple) -> np.ndarray:
    """
    RPDF dithering: noise uniforme ±0.5 LSB no espaço [0, 1].
    Chamar por frame — novo noise a cada frame (não reusar).
    """
    half_lsb = 0.5 / 255.0
    return np.random.uniform(-half_lsb, half_lsb, shape).astype(np.float32)


def node5_output(frame_graded: np.ndarray) -> np.ndarray:
    """
    Nó 5: float32 [0, 1] → uint8 [0, 255] com RPDF dithering.

    Output: BGR uint8 HWC (formato para PyAV VideoFrame)
    """
    # Dithering antes do clip e cast
    dither    = _build_dither(frame_graded.shape)
    dithered  = frame_graded + dither

    # Clip e conversão
    rgb_uint8 = np.clip(dithered * 255.0, 0, 255).astype(np.uint8)

    # RGB → BGR para PyAV (que espera bgr24)
    return rgb_uint8[..., ::-1]
```

---

## Orquestração completa do pipeline

```python
def process_frame_cineon(av_frame:    av.VideoFrame,
                         state:       CineonState,
                         use_mctf:    bool = True) -> tuple[np.ndarray, CineonState]:
    """
    Pipeline completo: PyAV frame → BGR uint8 graded.
    Retorna (bgr_uint8, state_atualizado).

    Integração no Reels_Encoder_v2_FINAL.py:
        state = CineonState()
        state.lut3d    = load_lut(LUT_CINEON)
        state.features = analyze("input.mp4").features.__dict__
        state.ema_alpha = derive_ema_alpha(state.features["temporal_noise"])
        use_mctf = should_use_mctf(state.features)

        for frame in container.decode(video_stream):
            bgr, state = process_frame_cineon(frame, state, use_mctf)
            # escrever bgr no output container via PyAV
    """
    # Pré-processamento
    rgb_f32 = frame_to_float32(av_frame)

    # Nó 1: DWG Input Transform
    rgb_aces = node1_dwg_input(rgb_f32)

    # Nó 2: Tone & Gamut Mapping
    rgb_lin_bt709 = node2_tone_gamut(rgb_aces, state.features or {})

    # Nó 3: Cineon Log Encoding
    cineon_log = cineon_encode(rgb_lin_bt709)

    # Nó 4: LUT Application
    graded = node4_lut(cineon_log, state.lut3d)

    # MCTF (entre Nó 4 e 5)
    if use_mctf:
        graded, state = mctf_ema(graded, state)

    # Nó 5: Output com dithering
    bgr_out = node5_output(graded)

    return bgr_out, state
```

---

## Inicialização do pipeline

```python
def init_cineon_pipeline(lut_path: str,
                         analysis_result) -> tuple[CineonState, bool]:
    """
    Inicializa o estado do pipeline Cineon para um novo Reel.
    Chamar uma vez por arquivo — nunca entre frames do mesmo clipe.

    analysis_result: AnalysisResult de scripts/analyze_source.py
    """
    features = analysis_result.features.__dict__

    # Validar LUT antes de processar
    lut3d = load_lut(lut_path)
    lut_check = validate_lut_gamut(lut3d)
    if lut_check["out_of_gamut_ratio"] > 0.01:
        import warnings
        warnings.warn(f"LUT gamut warning: {lut_check['status']}")

    # Validar constantes Cineon log
    _validate_cineon_constants()

    state = CineonState(
        lut3d    = lut3d,
        features = features,
        ema_alpha = derive_ema_alpha(features.get("temporal_noise", 5.0)),
    )
    use_mctf = should_use_mctf(features)

    return state, use_mctf
```

---

## Considerações de memória e performance

| Operação | Custo por frame 1080×1920 |
|---|---|
| float32 RGB array | ~25 MB |
| Farneback optical flow | ~15 MB (buffers internos) |
| LUT3D.apply() tetrahedral | ~8 MB temporário |
| Peak total por frame | ~60–70 MB |

**Para batches maiores:** processar frame a frame, não em batch. O overhead de
memória por frame é manejável; em batch de 30 frames seria ~1.8 GB só de buffers.

**Bottleneck real:** `node2_tone_gamut` (einsum + Hable) e `_farneback_warp`
(Farneback é O(pixels × levels)). Ambos podem ser acelerados com:
- `node2`: `np.dot` em lugar de `einsum` para a matrix (marginalmente mais rápido)
- `_farneback_warp`: reduzir `levels` de 3 para 2 se `motion_magnitude < 5`

---

## Checkpoints de debugging

```python
def debug_frame_stats(label: str, arr: np.ndarray) -> None:
    """Inserir entre nós durante debugging para rastrear range e distribuição."""
    print(f"[{label}] shape={arr.shape} dtype={arr.dtype} "
          f"min={arr.min():.4f} max={arr.max():.4f} "
          f"mean={arr.mean():.4f} std={arr.std():.4f}")

# Uso:
# debug_frame_stats("Nó1 out (ACEScg)",     rgb_aces)
# debug_frame_stats("Nó2 out (BT.709 lin)", rgb_lin_bt709)
# debug_frame_stats("Nó3 out (Cineon log)", cineon_log)
# debug_frame_stats("Nó4 out (graded)",     graded)

# Valores esperados:
# Nó 1: max pode exceder 1.0 (wide gamut — normal)
# Nó 2: range [0.0, 1.0] após soft-clip
# Nó 3: range [0.0, 1.0] — Cineon log normalizado
# Nó 4: range [0.0, 1.0] — LUT output válida
# Nó 5: uint8 [0, 255]
```
