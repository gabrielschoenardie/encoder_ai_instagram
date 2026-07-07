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
| Consistência temporal | Filtros FFmpeg stateless | Também stateless — sem MCTF, cada frame é processado isolado |
| Dithering | RPDF via `_build_dither()` (`enhance/ffmpeg_filters.py`), ativo por padrão via `--dither` | RPDF via `quantize_uint8_dithered()` (`cineon_pipeline.py`), ativo por padrão via `--dither` |
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
- Gradientes muito suaves podem ter banding em 8-bit se `--dither off`
- Sem consistência temporal explícita (nenhum modo tem — ambos processam frame a frame)
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
[Node 1] CST IN — Rec.709 gamma → linear → DWG (DaVinci Wide Gamut) → DWG Intermediate log
    ↓
[Node 2] Primary — exposure (stops, ancorado 18% grey) + saturation + lift/gamma/gain
    ↓
[Node 3] CST OUT — DWG linear → soft-knee tone mapping (knee=0.8) → matrix → BT.709 linear
  → gamut mapping (saturation compression, knee=0.9) → Cineon Log
    ↓
[Node 4] Bridge — passthrough (arquitetura de 5 nós preservada)
    ↓
[Node 5] LUT — FilmLook_Portra400_SkinPriority_D65.cube via LUT3D.apply() (trilinear)
    ↓
[Consumidor, fora dos 5 nós] quantize_uint8_dithered() — dither RPDF opcional + round → uint8
```

Sem MCTF, sem ACEScg, sem curva de Hable — ver `references/cineon-pipeline.md`
para as fórmulas e a seção "O que NÃO existe neste pipeline". O processamento
é **stateless**: cada frame passa por `process_frame_full_pipeline()`
isoladamente, sem blending temporal nem estado entre frames.

### Dithering RPDF (`quantize_uint8_dithered()`)

Ativo por padrão (`--dither auto`) na conversão float32 → uint8 final. Previne
o viés de truncamento e o banding que a quantização direta produziria em
gradientes suaves.

```python
# RPDF (Rectangular Probability Density Function) — cineon_pipeline.py
def quantize_uint8_dithered(frame, rng=None):
    scaled = frame.astype(np.float32) * 255.0
    if rng is not None:
        scaled = scaled + rng.uniform(-0.5, 0.5, size=scaled.shape).astype(np.float32)
    return np.clip(np.round(scaled), 0, 255).astype(np.uint8)
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
- Nunca desativar o dithering RPDF (`--dither off`) sem motivo — banding é garantido
  em gradientes sem ele
- O pipeline é stateless (sem MCTF) — cada frame é independente, não há estado para
  reinicializar entre Reels
- Monitorar memória: float32 1080×1920 por frame = ~25MB — processamento é sempre
  frame a frame, nunca em batch
