# Encoder Modes — FFmpeg Mode vs Cineon Mode

Guia de decisão para escolha de modo no `Reels_Encoder_v2_FINAL.py`.
A lógica de `recommend_mode()` em `scripts/analyze_source.py` implementa
exatamente este documento — código e documentação estão em sincronia.

---

## Comparativo rápido

| Dimensão | FFmpeg Mode | Cineon Mode |
|---|---|---|
| Velocidade | ~15–40 fps | ~5–10 fps |
| Processamento | Native FFmpeg filter chain | PyAV + NumPy float32 per-frame |
| Precisão de cor | 8-bit YUV ao longo do pipeline | float32 → 8-bit apenas na saída |
| LUT padrão | `HollywoodCinema_Ultimate_v6.7B` | `FilmLook_Portra400_SkinPriority_D65` |
| Consistência temporal | Filtros FFmpeg stateless | MCTF (Farneback + EMA) |
| Dithering | Não aplicado | RPDF via `_build_dither()` — sempre ativo |
| Melhor para | BT.709 controlado, batch, alto movimento | Log footage, skin crítico, highlights complexos |

---

## FFmpeg Mode

### Filosofia do pipeline
Processa tudo dentro do grafo de filtros do FFmpeg, sem sair para Python por frame.
Cada filtro opera em 8-bit YUV, o que é suficiente para fontes já em BT.709 com
exposição controlada. O custo de não ter float32 é tolerável quando o source já
entregou highlights dentro do range.

### LUT: HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube
- **1.5 IRE**: sombras neutras — não há crushing de negros, o que preserva detalhe
  em zonas escuras que o Instagram tenderia a bloquear
- **Instagram8bit**: calibrada especificamente para o pipeline de ingestão do Instagram;
  a curva tonal foi ajustada para sobreviver à compressão sem perda de saturação
- **NeutralShadows**: sem lift de sombras artificial — o que você exporta é o que aparece

### Quando usar FFmpeg Mode
O `recommend_mode()` direciona para FFmpeg quando:

```
1. Source já em BT.709 (codec h264, h265 com tags BT.709)
   AND iluminação controlada (luma_noise < 180 OR skin_ratio < 0.25)

2. Duração > 60s
   → custo do Cineon Mode (3–6× mais lento) inviabiliza o tempo de encode

3. motion_magnitude > 18 px/frame
   → cenas de alto movimento têm VMAF muito similar entre os modos;
     overhead do float32 não se justifica

4. Nenhuma das condições pro-Cineon atingida
   → FFmpeg Mode é o default seguro
```

### Pipeline interno (ordem de filtros)
```
[temporal_pre?] → [denoise] → [highlight_rolloff?] → lut3d → scale=1080:1920 → fps=30
```

### Limitações
- Gradientes muito suaves podem ter banding em 8-bit (use dithering manual se crítico)
- Sem MCTF: cintilação temporal em fontes de baixa qualidade não é suprimida
- Highlights acima de ~235 IRE clipam sem recovery possível

---

## Cineon Mode

### Filosofia do pipeline
Cada frame é processado como array float32 via PyAV + NumPy, passando por um
pipeline de 5 nós no estilo DaVinci Resolve. O float32 garante que nenhuma
operação de cor introduza quantization error acumulado antes do encode final.

### LUT: FilmLook_Portra400_SkinPriority_D65.cube
- **Portra 400**: emulação de filme Kodak Portra 400 — compressão suave de highlights,
  shadows com detalhe preservado, viés de saturação nas meias-tonalidades
- **SkinPriority**: a LUT foi calibrada com ênfase em skin tones em D65 — preserva
  a tonalidade natural de pele sem virar "bronzeado" ou "rosado" artificialmente
- **D65**: white point padrão D65 (6500K), consistente com BT.709

### Pipeline 5-nós (mapa canônico)

> Numeração única, idêntica às funções `node1..node5` do código e ao
> `references/cineon-pipeline.md` (fonte da verdade para fórmulas e código).

```
Frame float32
    ↓
[Nó 1] DWG Input Transform
  BT.709 gamma decode → linear scene-referred
  Linear BT.709 → ACEScg (wide gamut de trabalho)
    ↓
[Nó 2] Tone & Gamut Mapping
  S-curve Hable adaptativa (skin_ratio + color_temp_proxy do analyze_source.py):
    - skin_ratio alto → shoulder mais suave (preserva gradiente de pele)
    - color_temp_proxy > 1.3 → warm shift compensado
  Soft-clip out-of-gamut + ACEScg → BT.709 linear
    ↓
[Nó 3] Cineon Log Encoding (intermediário p/ compatibilidade da LUT)
  Fórmula: out = log10(max(lin, 1e-10)) / (0.002×1023) + 0.669   (slope = 2.046)
  Ver pontos de controle em references/cineon-pipeline.md (Nó 3)
    ↓
[Nó 4] LUT Application
  FilmLook_Portra400_SkinPriority_D65.cube (tetraédrica)
    ↓
[MCTF] Temporal Consistency (Farneback + EMA) — estágio entre Nó 4 e Nó 5
    ↓
[Nó 5] Output
  RPDF dithering (_build_dither()) → float32 → uint8 [0–255]
```

### MCTF — Temporal Consistency (Farneback + EMA)

O MCTF (Motion-Compensated Temporal Filtering) usa optical flow Farneback para
alinhar frames consecutivos e um filtro EMA para suprimir variação temporal.

**O peso EMA é derivado de `temporal_noise` pelo `analyze_source.py`:**

```python
# Lógica MCTF em Cineon Mode
temporal_noise = features.temporal_noise

if temporal_noise < 5:
    ema_alpha = 0.9    # muito smoothing — source estável
elif temporal_noise < 12:
    ema_alpha = 0.7    # smoothing moderado
else:
    ema_alpha = 0.5    # mínimo smoothing — preserva transições bruscas

# Fórmula EMA por canal float32:
# frame_out = ema_alpha * frame_prev_aligned + (1 - ema_alpha) * frame_current
```

**Quando desativar MCTF:** se `motion_magnitude > 25` — optical flow Farneback
falha em cenas de movimento extremo e introduz ghosting.

### Dithering RPDF (`_build_dither()`)

Sempre ativo na conversão float32 → uint8 final. Previne banding em gradientes
suaves que seriam visíveis com quantization direta.

```python
# RPDF (Rectangular Probability Density Function)
def _build_dither(shape):
    """Noise uniforme ±0.5 LSB para dithering antes de conversão 8-bit."""
    return np.random.uniform(-0.5 / 255.0, 0.5 / 255.0, shape).astype(np.float32)

# Aplicar antes do clip + cast
frame_dithered = frame_float32 + _build_dither(frame_float32.shape)
frame_uint8    = np.clip(frame_dithered * 255.0, 0, 255).astype(np.uint8)
```

### Quando usar Cineon Mode

O `recommend_mode()` direciona para Cineon quando **pelo menos uma** condição:

```
1. Source codec: HEVC / ProRes / DNxHD / CineForm
   → log ou intermediário, o float32 pipeline faz diferença real

2. skin_ratio > 0.30 AND 1.0 < color_temp_proxy < 1.9
   → close de rosto com iluminação quente (casamento, portrait)
   → Portra400 SkinPriority é notavelmente melhor que HollywoodCinema

3. highlight_load > 0.18
   → highlights complexos (janelas, spots, velas) que precisam de tone mapping
   → o hard-clip do 8-bit FFmpeg Mode destrói esses highlights

4. luma_noise > 180 AND skin_ratio > 0.25
   → noise alto com pessoas em quadro
   → float32 denoise antes da conversão 8-bit preserva mais textura de pele

CONTRA-INDICADO se:
  - duration_s > 60 (tempo de encode excessivo)
  - motion_magnitude > 18 (ganho de qualidade não justifica o custo)
```

---

## Comparativo de qualidade por cenário

| Cenário | FFmpeg VMAF | Cineon VMAF | Diferença | Recomendação |
|---|---|---|---|---|
| Source BT.709, exposição normal | 93–95 | 93–95 | ~0 | FFmpeg (mais rápido) |
| Source BT.709, highlights > 0.18 | 90–92 | 93–95 | +2–3 | **Cineon** |
| Close de rosto, ISO 400 | 92–93 | 93–96 | +1–3 | **Cineon** |
| Source ISO 3200+ noturno | 88–91 | 91–94 | +3 | **Cineon** |
| Dança / alto movimento 30fps | 90–92 | 90–92 | ~0 | FFmpeg (mais rápido) |
| Log footage (S-Log, C-Log) | — | 92–95 | N/A | **Cineon** (FFmpeg não processa log) |

*Valores VMAF estimados com source Canon 6D / encode Maximum Quality (≤30s).*

---

## Integração com analyze_source.py

```python
from scripts.analyze_source import analyze

# Análise automática → recomendação de modo
result = analyze("input.mp4")

print(f"Modo recomendado: {result.encoder_mode}")
print(f"Razões: {result.mode_reasoning}")
print(f"LUT: {result.lut_path}")

# Forçar modo independente da recomendação
result_forced = analyze("input.mp4", mode_override="cineon")

# Override de LUT
result_custom = analyze("input.mp4", lut_override="/path/to/custom.cube")
```

---

## Regras de ouro por modo

**FFmpeg Mode:**
- Verificar sempre se source está tagueado como BT.709 antes de usar
- Não usar para source com highlight_load > 0.20 — haverá clipping
- Confirmar que a LUT `HollywoodCinema_Ultimate_v6.7B` está no path correto

**Cineon Mode:**
- Nunca desativar o dithering RPDF — banding é garantido em gradientes sem ele
- Desativar MCTF se `motion_magnitude > 25` — ghosting em movimento extremo
- O pipeline é stateful (MCTF mantém estado entre frames) — não processar clips
  fora de ordem; reinicializar o estado entre Reels distintos
- Monitorar memória: float32 1080×1920 por frame = ~8MB — batch de frames simultâneos
  deve respeitar disponibilidade de RAM
