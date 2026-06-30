# Denoise Pipeline — BM3D, Vaguedenoiser, hqdn3d

Sistema de detecção e remoção de ruído para preservação perceptual máxima no encode.

---

## Tipos de Noise — Classificação Gabriel

| Tipo | Característica visual | Origem típica |
|---|---|---|
| Fine noise | Grain fino, uniforme, luminância | ISO alto, sensor pequeno |
| Coarse noise | Manchas maiores, estrutura visível | ISO extremo, low-light severo |
| Chromatic noise | Variação de cor (verde/magenta) | Canais RGB desbalanceados |
| Temporal noise | Flickering entre frames | Luz artificial pulsante (AC) |

---

## Árvore de Decisão — Qual Filtro Usar

```
Noise ausente ou mínimo
    └── Sem filtro (ou hqdn3d ultralevee: 0.5:0.3:0.3:0.2)

Noise fine (luminância)
    ├── Velocidade prioritária → vaguedenoiser (modo fast)
    └── Qualidade prioritária → BM3D spatial

Noise coarse ou chromatic
    └── BM3D (spatial + chroma) — obrigatório

Noise temporal (flickering)
    ├── hqdn3d temporal → vaguedenoiser → BM3D
    └── ou deflicker + BM3D

Noise misto (fine + temporal + chromatic)
    └── BM3D modo completo (spatial + temporal)
```

---

## hqdn3d — Denoise Leve/Médio

Filtro nativo FFmpeg. Rápido, mas menos preciso. Adequado para noise mínimo.

```bash
# Ultra-leve — só para noise imperceptível (safeguard)
-vf "hqdn3d=0.5:0.3:0.3:0.2"

# Leve — fine noise controlado
-vf "hqdn3d=2:1.5:2:1.5"

# Médio — noise moderado (limite antes de migrar para vaguedenoiser)
-vf "hqdn3d=4:3:4:3"
```

**Parâmetros:** `hqdn3d=luma_spatial:chroma_spatial:luma_temporal:chroma_temporal`

**Limite:** valores acima de 5 em luma_spatial causam perda de textura visível em pele.
Nunca usar `hqdn3d > 6` para conteúdo com pessoas.

---

## Vaguedenoiser — Denoise Rápido Baseado em Wavelets

Alternativa rápida ao BM3D. Preserva bordas melhor que hqdn3d.

```bash
# Modo fine noise — rápido
-vf "vaguedenoiser=threshold=1.8:method=hard:nsteps=6"

# Modo moderado
-vf "vaguedenoiser=threshold=2.5:method=soft:nsteps=6"

# Modo agressivo (coarse noise leve)
-vf "vaguedenoiser=threshold=3.5:method=soft:nsteps=8"
```

**Parâmetros:**
- `threshold`: força da remoção. 1.5–2.5 para uso normal; acima de 3.5 → blur
- `method`: `hard` preserva mais textura; `soft` é mais suave e seguro em skin
- `nsteps`: níveis de decomposição. 6–8 é o sweet spot

**Timing:** ~10–30x mais rápido que BM3D para o mesmo resultado qualitativo em fine noise.

---

## BM3D — Denoise de Alta Qualidade (Gold Standard)

Block-Matching 3D. No `Reels_Encoder_v2_FINAL.py`, o BM3D **não usa frei0r** —
é implementado via PyAV + NumPy no pacote `enhance/`, integrado ao Cineon Mode.
Os parâmetros são derivados pelo `scripts/analyze_source.py` → `derive_denoise()`.

### Integração com o encoder (via enhance/ package)

```python
# analyze_source.py retorna quando BM3D é selecionado:
{
    "method": "bm3d",
    "params": {
        "sigma_spatial": 0.055,   # sigma luma — escala com luma_noise medido
        "sigma_chroma":  0.040,   # sigma chroma — escala com chroma_noise medido
    }
}

# O enhance/ package usa esses parâmetros diretamente no pipeline float32:
# frame_denoised = bm3d.bm3d(frame_float32, sigma_psd=sigma_spatial)
```

### Parâmetros derivados adaptativamente (não presets fixos)

```python
# De derive_denoise() em analyze_source.py:
sigma_spatial = min(0.04 + (luma_noise / 500.0) * 0.04, 0.05 if skin_ratio > 0.30 else 0.08)
sigma_chroma  = min(0.03 + (chroma_noise / 300.0) * 0.03, 0.04 if skin_ratio > 0.30 else 0.06)
```

Referência de valores esperados:
| Condição do source | sigma_spatial | sigma_chroma |
|---|---|---|
| Noise fino, skin presente | 0.040–0.050 | 0.030–0.040 |
| Noise moderado, sem skin | 0.055–0.070 | 0.040–0.050 |
| Noise alto (ISO 3200+) | 0.070–0.080 | 0.050–0.060 |

### Proteção de skin tones em BM3D

Quando `skin_ratio > 0.30`, os sigmas são limitados automaticamente (0.05 / 0.04).
Exceder esses valores em close de rosto resulta em **waxy skin** — ver
`references/artifact-diagnosis.md` seção "Waxy Skin".

**Regra crítica:** VMAF com BM3D deve ser **≥ VMAF sem BM3D** no source. Se cair,
o denoise está removendo textura real — reduzir sigma_spatial em 0.01 e re-testar.

### Performance

BM3D no pipeline float32 do Cineon Mode: 6–12 minutos para Reel típico (30s).
Usar apenas quando `derive_denoise()` seleciona automaticamente — ou seja,
quando `luma_noise > 200 OR chroma_noise > 80 OR temporal_noise > 12`.

---

## Inserção no Chain de Filtros FFmpeg

Denoise sempre vem **antes** do color pipeline e do scale.
Usar `scripts/analyze_source.py` para gerar o chain completo automaticamente.

```bash
# Ordem correta (gerada pelo analyze_source.py)
-vf "hqdn3d=2:1.5:2:1.5,lut3d=lut.cube,scale=1080:1920:flags=lanczos,fps=30"

# Para vaguedenoiser
-vf "vaguedenoiser=threshold=2.0:method=soft:nsteps=6,lut3d=lut.cube,scale=1080:1920:flags=lanczos,fps=30"

# Para temporal pre-filter + vaguedenoiser
-vf "hqdn3d=0.5:0.5:3.0:2.5,vaguedenoiser=threshold=2.0:method=soft:nsteps=6,lut3d=lut.cube,scale=1080:1920:flags=lanczos,fps=30"
```

> **BM3D no FFmpeg Mode:** não disponível nativamente — BM3D requer o pipeline
> float32 do Cineon Mode. Se o source exigir BM3D, considerar upgrade para Cineon Mode.

---

## Impacto no VMAF

| Método | Impacto VMAF | Observação |
|---|---|---|
| hqdn3d leve | +0.5 a +1.5 | Remove noise que confunde VMAF |
| hqdn3d agressivo | -1 a -3 | Perde textura real → VMAF cai |
| vaguedenoiser moderado | +1 a +2 | Sweet spot qualidade/tempo |
| BM3D bem calibrado | +2 a +4 | Melhor resultado perceptual |
| BM3D sobre-aplicado | -2 a -5 | Waxy look — perde detalhe de pele |

**Regra:** medir VMAF com e sem denoise no primeiro frame de 30s para calibrar.
