# Adaptive Content Analysis — Parâmetros por IA, não por Preset

Metodologia de análise de conteúdo que deriva parâmetros de encode dinamicamente
a partir das características reais do material. Nenhum preset fixo: cada encode
é resultado de medições objetivas do source.

Integra com o pipeline `Reels_Encoder_v2_FINAL.py` — especialmente o pacote
`enhance/` e o Mock CNN (vetor 13D → 3D).

---

## Princípio central

Presets fixos por tipo de cena falham porque o mesmo "tipo" de cena pode ter
características completamente distintas: uma cerimônia em church escura tem
noise profile completamente diferente de uma cerimônia em outdoor com sol.

O pipeline correto é:

```
Source → Análise objetiva → Vetor de features → Derivação de parâmetros → Encode
```

Cada etapa é mensurável, reproduzível e justificável por engenharia.

---

## Etapa 1 — Extração do Vetor de Features

O Mock CNN do `enhance/` opera sobre um vetor 13D. Estas são as 13 dimensões
e como extraí-las via FFprobe/FFmpeg antes de qualquer encode:

### Dimensões 1–4: Noise Profile

```python
import cv2
import numpy as np

def extract_noise_features(frame_bgr):
    """
    Retorna 4 features de noise a partir de um frame representativo.
    Usar 3–5 frames espaçados uniformemente no vídeo para média robusta.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    yuv  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YUV).astype(np.float32)

    # Feature 1: Laplacian variance — noise espacial em luma
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    luma_noise = float(laplacian.var())

    # Feature 2: Chromatic noise — variância nos canais Cr e Cb
    cr_var = float(yuv[:,:,1].var())
    cb_var = float(yuv[:,:,2].var())
    chroma_noise = (cr_var + cb_var) / 2.0

    # Feature 3: Block noise — variância média em blocos 8×8 (proxy de DCT noise)
    # Versão vetorizada: O(1) via reshape, evita loop Python por bloco
    h, w   = gray.shape
    bh, bw = (h // 8) * 8, (w // 8) * 8
    B      = gray[:bh, :bw].reshape(h // 8, 8, w // 8, 8)
    mu     = B.mean(axis=(1, 3), keepdims=True)
    block_noise = float(((B - mu) ** 2).mean(axis=(1, 3)).mean())

    # Feature 4: Temporal noise — diferença entre frames consecutivos
    # (calcular sobre par de frames, não frame único)
    # Retorna 0.0 se chamado com frame único; usar compute_temporal_noise() abaixo

    return {
        "luma_noise":   luma_noise,     # Laplacian variance: 0–500+ (low=<50, high=>200)
        "chroma_noise": chroma_noise,   # Chroma variance: 0–300+ (low=<30, high=>100)
        "block_noise":  block_noise,    # Block DCT variance: 0–200+
    }

def compute_temporal_noise(frame_a, frame_b):
    """Diferença absoluta média entre frames consecutivos (temporal flickering)."""
    diff = cv2.absdiff(
        cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)
    ).astype(np.float32)
    return float(diff.mean())  # 0–50+ (low=<3, high=>15)
```

### Dimensões 5–7: Scene Complexity

```python
def extract_complexity_features(frame_bgr, prev_frame_bgr=None):
    """Complexidade espacial e temporal da cena."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # Feature 5: Spatial complexity — gradiente médio (detalhe de borda)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    spatial_complexity = float(np.sqrt(gx**2 + gy**2).mean())

    # Feature 6: Entropy — distribuição de informação no frame
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist = hist / hist.sum()
    hist = hist[hist > 0]
    entropy = float(-np.sum(hist * np.log2(hist)))

    # Feature 7: Motion magnitude (Farneback optical flow — MCTF)
    motion_magnitude = 0.0
    if prev_frame_bgr is not None:
        prev_gray = cv2.cvtColor(prev_frame_bgr, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        motion_magnitude = float(np.sqrt(flow[...,0]**2 + flow[...,1]**2).mean())

    return {
        "spatial_complexity": spatial_complexity,  # 0–80+ (low=<15, high=>50)
        "entropy":            entropy,              # 0–8 bits (low=<5, complex=>7)
        "motion_magnitude":   motion_magnitude,    # 0–30+ px/frame (low=<2, high=>10)
    }
```

### Dimensões 8–10: Highlight & Shadow Distribution

```python
def extract_tonal_features(frame_bgr):
    """Distribuição tonal: highlights, sombras, midtones."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    # Feature 8: Highlight load — percentual de pixels acima de 0.87 (220/255)
    highlight_load = float((gray > 0.87).mean())

    # Feature 9: Shadow load — percentual de pixels abaixo de 0.06 (16/255)
    shadow_load = float((gray < 0.06).mean())

    # Feature 10: Midtone variance — variância na zona 0.2–0.8 (zona de skin tones)
    midtone_mask = (gray >= 0.2) & (gray <= 0.8)
    midtone_variance = float(gray[midtone_mask].var()) if midtone_mask.any() else 0.0

    return {
        "highlight_load":   highlight_load,    # 0–1 (crítico se >0.15)
        "shadow_load":      shadow_load,       # 0–1 (crítico se >0.20)
        "midtone_variance": midtone_variance,  # 0–0.1 (pele: 0.03–0.07)
    }
```

### Dimensões 11–13: Skin Tone & Color Space

```python
def extract_skin_color_features(frame_bgr):
    """Presença de skin tones e características de espaço de cor."""
    # Feature 11: Skin tone ratio (YCrCb detection)
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    # Range YCrCb para skin tones: Y=80–240, Cr=133–173, Cb=77–127
    skin_mask = (
        (ycrcb[:,:,0] >= 80)  & (ycrcb[:,:,0] <= 240) &
        (ycrcb[:,:,1] >= 133) & (ycrcb[:,:,1] <= 173) &
        (ycrcb[:,:,2] >= 77)  & (ycrcb[:,:,2] <= 127)
    )
    skin_ratio = float(skin_mask.mean())

    # Feature 12: Saturação média — detecta cenas dessaturadas vs vibrantes
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mean_saturation = float(hsv[:,:,1].mean()) / 255.0

    # Feature 13: Color temperature proxy — razão R/B do canal médio
    b_mean = float(frame_bgr[:,:,0].mean())
    r_mean = float(frame_bgr[:,:,2].mean())
    color_temp_proxy = r_mean / (b_mean + 1e-6)  # >1=quente, <1=frio

    return {
        "skin_ratio":         skin_ratio,         # 0–1 (close de rosto: >0.3)
        "mean_saturation":    mean_saturation,    # 0–1
        "color_temp_proxy":   color_temp_proxy,   # 0.5–2.5
    }
```

---

## Etapa 2 — Derivação de Parâmetros a partir das Features

Nenhuma regra "se cena X usar preset Y". Cada parâmetro é derivado
continuamente das features medidas:

### Derivação do pipeline de denoise

```python
def derive_denoise_params(features: dict) -> dict:
    """
    Deriva parâmetros de denoise adaptativos.
    Input: dicionário com todas as 13 features.
    Output: parâmetros para o filtro FFmpeg ou VideoNoiseAnalyzer.
    """
    luma   = features["luma_noise"]
    chroma = features["chroma_noise"]
    temporal = features.get("temporal_noise", 0.0)
    skin   = features["skin_ratio"]

    # Threshold de decisão por método
    # Estes valores foram calibrados empiricamente; ajustar se o material
    # do encoder mostrar divergência com a análise do VideoNoiseAnalyzer
    LUMA_LOW    = 50.0
    LUMA_HIGH   = 200.0
    CHROMA_HIGH = 80.0
    TEMPORAL_HIGH = 12.0

    method = "none"
    params = {}

    if luma < LUMA_LOW and chroma < 30.0 and temporal < 5.0:
        # Ruído mínimo — sem denoise ou safeguard ultra-leve
        method = "hqdn3d_minimal"
        params = {"luma_s": 0.5, "chroma_s": 0.3, "luma_t": 0.3, "chroma_t": 0.2}

    elif luma < LUMA_HIGH and chroma < CHROMA_HIGH and temporal < TEMPORAL_HIGH:
        # Noise moderado — vaguedenoiser, velocidade/qualidade adequados
        method = "vaguedenoiser"
        # Threshold escala linearmente com o nível de noise medido
        threshold = 1.5 + (luma / LUMA_HIGH) * 1.5      # range: 1.5–3.0
        threshold = min(threshold, 2.5)                  # cap: nunca > 2.5 com skin presente
        if skin > 0.25:
            threshold = min(threshold, 2.0)              # proteção de pele
        method_type = "soft" if skin > 0.15 else "hard"
        params = {"threshold": round(threshold, 2), "method": method_type, "nsteps": 6}

    elif chroma > CHROMA_HIGH or temporal > TEMPORAL_HIGH or luma > LUMA_HIGH:
        # Noise alto: chromatic severo, temporal, ou coarse — BM3D
        method = "bm3d"
        # sigma_spatial escala com luma noise
        sigma_spatial = 0.04 + (luma / 500.0) * 0.04    # range: 0.04–0.08
        # sigma_chroma escala com chroma noise
        sigma_chroma  = 0.03 + (chroma / 300.0) * 0.03  # range: 0.03–0.06
        # Limitar sigma se skin presente (evitar waxy)
        if skin > 0.30:
            sigma_spatial = min(sigma_spatial, 0.05)
            sigma_chroma  = min(sigma_chroma,  0.04)
        params = {
            "sigma_spatial": round(sigma_spatial, 3),
            "sigma_chroma":  round(sigma_chroma,  3),
        }

    # Componente temporal separado (hqdn3d temporal)
    if temporal > 8.0 and method != "bm3d":
        params["temporal_pre"] = {
            "luma_t":   round(min(temporal / 4.0, 4.0), 1),
            "chroma_t": round(min(temporal / 5.0, 3.0), 1),
        }

    return {"method": method, "params": params}
```

### Derivação dos parâmetros x264

```python
def derive_x264_params(features: dict, duration_s: float) -> dict:
    """
    Deriva aq-strength, subme, psy-rd e rc-lookahead adaptativos.
    """
    skin      = features["skin_ratio"]
    spatial   = features["spatial_complexity"]
    motion    = features["motion_magnitude"]
    midtone_v = features["midtone_variance"]
    highlight = features["highlight_load"]

    # aq-strength: maior quando skin presente (precisa de bits nos midtones)
    # reduzir em cenas de alto movimento (evita shimmer temporal)
    aq_strength = 0.8
    if skin > 0.25:
        aq_strength += 0.1 * (skin / 0.5)       # +0.1 a +0.2 para close de rosto
    if motion > 15.0:
        aq_strength -= 0.1                        # -0.1 para movimento rápido
    if highlight > 0.20:
        aq_strength -= 0.05                       # reduzir em cenas muito claras
    aq_strength = round(max(0.6, min(aq_strength, 1.2)), 2)

    # subme: maior complexidade espacial → ME mais fino
    subme = 8
    if spatial > 50.0 or motion > 20.0:
        subme = 9
    elif spatial < 15.0 and motion < 3.0:
        subme = 7   # cena simples, economizar tempo de encode

    # psy-rd: detalhe perceptual — ativo quando textura é o ponto da cena
    psy_rd = 0.0
    if spatial > 40.0 and skin < 0.15:
        psy_rd = 1.0   # B-roll de textura
    elif spatial > 25.0 and skin < 0.30:
        psy_rd = 0.8

    # rc-lookahead: proporcional ao GOP e à variabilidade de cena
    rc_lookahead = 60
    if motion > 20.0:
        rc_lookahead = 40   # cena com muita variação: lookahead menor é mais eficiente

    # deblock: suavizar em cenas com skin dominante
    # IMPORTANTE: deblock usa sub-args separados por VÍRGULA (alpha,beta).
    # Dentro de -x264-params o separador de parâmetros é ':', então "deblock=-1:-1"
    # quebra o parse (vira deblock=-1 + token solto). Ver references/x264-param-syntax.md.
    deblock = "0,0"
    if skin > 0.30:
        deblock = "-1,-1"   # deblocking mais suave → preserva textura de pele

    return {
        "aq_strength":   aq_strength,
        "subme":         subme,
        "psy_rd":        psy_rd,
        "rc_lookahead":  rc_lookahead,
        "deblock":       deblock,
    }
```

### Derivação do rolloff de highlights

```python
def derive_highlight_rolloff(features: dict) -> str | None:
    """
    Retorna o parâmetro -vf curves= se highlight_load justificar rolloff.
    Retorna None se rolloff não é necessário.
    Nota: shadow_load não influencia o rolloff — afeta apenas o lift de sombras
    no nó 2 do Cineon Mode (tone mapping). Ver references/encoder-modes.md.
    """
    h = features["highlight_load"]

    if h < 0.05:
        return None   # highlights normais, sem rolloff

    # Intensity do rolloff escala com o load de highlights medido
    # knee_point: onde começa o rolloff (0.75–0.90 IRE)
    # knee_output: quanto comprime no topo (0.92–0.97)
    knee_point  = max(0.75, 0.92 - h * 0.8)    # mais load → knee mais cedo
    knee_output = 0.97 - h * 0.15               # mais load → mais compressão no topo
    knee_point  = round(knee_point,  3)
    knee_output = round(knee_output, 3)

    rolloff = (
        f"curves=r='0/0 {knee_point}/{knee_point} 1.0/{knee_output}':"
        f"g='0/0 {knee_point}/{knee_point} 1.0/{knee_output}':"
        f"b='0/0 {knee_point}/{knee_point} 1.0/{knee_output}'"
    )
    return rolloff
```

---

## Etapa 2b — GOP Adaptativo via Pass-1 de Cortes

Antes da Etapa 3, `analyze_source.py` executa um **Pass-1 leve via ffprobe** que
extrai os timestamps reais de todos os I-frames do source. Essa estrutura de cortes
medida alimenta `derive_gop()` para produzir um GOP calibrado ao ritmo real do
material — não a um preset por tipo de cena.

### analyze_cut_structure() — Medição

```python
def analyze_cut_structure(video_path: str, fps: float = 30.0) -> dict:
    """
    Roda ffprobe no source e extrai:
      cut_count, cut_timestamps[], mean/min/max_cut_interval,
      cut_regularity_cv, rhythm ∈ {single_take, regular, irregular}
    """
    # ffprobe -show_entries frame=pts_time,pict_type → filtra pict_type='I'
    # intervals = diffs entre timestamps consecutivos
    # cv = std(intervals) / mean(intervals)
    # rhythm: single_take se mean > 10s; regular se cv < 0.35; senão irregular
```

### derive_gop() — Decisão em três camadas

```python
def derive_gop(features, cut_structure, duration_s, fps) -> dict:
    """
    Camada 1 — ritmo medido (evidência primária):
      single_take        → keyint=2.0s
      regular (CV<0.35)  → keyint=mean_interval (cap 2.0s)
      irregular          → keyint=min_interval × 1.2 (com headroom)

    Camada 2 — motion + complexidade:
      motion > 20 px/frame      → comprimir GOP para ≤1.5s
      motion < 3 + single_take  → GOP máximo 2.0s

    Camada 3 — tipo de conteúdo:
      skin_ratio > 0.30 + spatial_complexity < 30 → GOP moderado (≤1.5s)

    Hard cap: keyint ≤ 60 frames (regra Instagram, nunca violada).
    """
```

### Três estratégias de aplicação

| Estratégia | Critério | Saída |
|---|---|---|
| `fixed` | Cortes regulares (CV < 0.20) | `keyint=N:scenecut=40` |
| `scenecut_only` | Single take / ffprobe falhou | `keyint=60:scenecut=40` |
| `dual_coverage` | Cortes irregulares | `keyint=N:scenecut=50` + `-force_key_frames "t1,t2,t3,..."` (timestamps do Pass-1) |

A estratégia `dual_coverage` usa os timestamps reais dos I-frames do source
medidos no Pass-1, filtrados para excluir bordas (< 0.5s) e capped em 20 cortes.
FFmpeg garante I-frame exato em cada timestamp — abordagem determinística que
não depende de filtros auxiliares.

### Acesso via AnalysisResult

```python
result = analyze("video.mp4")
result.gop_profile         # dict completo
result.gop_profile["keyint"]            # int — frames
result.gop_profile["scenecut"]          # int — 0-60
result.gop_profile["force_keyframes"]   # str|None — expressão FFmpeg
result.gop_profile["strategy"]          # 'fixed' | 'scenecut_only' | 'dual_coverage'
result.gop_profile["cut_rhythm"]        # 'regular' | 'irregular' | 'single_take'
result.gop_profile["reasoning"]         # list[str] — auditoria da decisão
```

`build_ffmpeg_cmd()` injeta `-force_key_frames` como flag separada quando a
estratégia é `dual_coverage`. Para `fixed` e `scenecut_only`, apenas
`keyint:scenecut` vão dentro de `-x264-params`.

> Documentação completa de exemplos por tipo de conteúdo
> (highlight film, cerimônia, dança): `references/vbv-rate-control.md`
> seção "GOP Structure — Otimização Adaptativa de Keyframes".

---

> **Por que dois thresholds de CV?** São eixos distintos e deliberados:
> `analyze_cut_structure()` usa **CV < 0.35** para rotular o *ritmo*
> (`regular`/`irregular`) — uma classificação grossa para leitura humana e GOP.
> A *estratégia de aplicação* usa o corte mais estrito **CV < 0.20** para `fixed`
> vs `dual_coverage`: mesmo cortes levemente irregulares (banda 0.20–0.35) se
> beneficiam do seguro determinístico do `-force_key_frames`. Ritmo é o rótulo;
> estratégia é a decisão de robustez.

---

## Etapa 2c — Alocação de Bits por Shot (x264 zones)

Reaproveita a **mesma estrutura de cortes** já medida no Pass-1 (Etapa 2b) para
distribuir bits de forma desigual entre os shots — mais bits onde a complexidade
exige, menos onde o plano é estático. É o equivalente single-pass do "encode por
cena" do cinema, e não custa um pass extra: os cortes já foram medidos.

```python
def derive_zones(video_path, cut_structure, features, duration_s, fps=30):
    """
    Para cada segmento entre cortes, amostra a complexidade (Sobel) e deriva um
    multiplicador de bitrate (x264 zones, opção b=). Budget-preserving: a média
    ponderada por frames dos multiplicadores é normalizada para ~1.0, então o
    -b:v/VBV global continua válido e o maxrate/bufsize segue sendo o teto rígido.

    Retorna None (sem zones) quando não há o que diferenciar:
      single_take / fallback / < 2 cortes / demanda uniforme entre shots.
    """
```

| Saída | Significado |
|---|---|
| `zones` | string x264 `s,e,b=m/s,e,b=m/...` (frames + multiplicador por shot) |
| `zone_count` | nº de shots com alocação não-neutra |
| `budget_effective` | média ponderada dos multiplicadores (alvo ~1.0; VBV é o teto) |

Multiplicadores são clampados a **[0.70, 1.40]** (nenhum shot é faminto nem
estoura), os ranges são garantidamente ascendentes e sem overlap (x264 é estrito),
e shots dentro de ±0.04 de 1.0 são omitidos (usam a alocação default). `zones`
coexiste com `-force_key_frames` — mecanismos independentes.

> Documentação completa, sintaxe e exemplos por tipo de conteúdo:
> **`references/segment-bit-allocation.md`**.

---

## Etapa 3 — Montagem do -vf chain adaptativo

```python
def build_vf_chain(features: dict, duration_s: float, lut_path: str = None) -> str:
    """
    Monta a string -vf completa de forma adaptativa.
    Ordem obrigatória: temporal_pre → denoise_main → rolloff → lut3d → scale → fps
    """
    filters = []

    denoise = derive_denoise_params(features)
    x264    = derive_x264_params(features, duration_s)
    rolloff = derive_highlight_rolloff(features)

    # Pré-filtro temporal (se necessário, antes do denoise principal)
    if "temporal_pre" in denoise["params"]:
        t = denoise["params"]["temporal_pre"]
        filters.append(
            f"hqdn3d=0.5:0.5:{t['luma_t']}:{t['chroma_t']}"
        )

    # Denoise principal
    m = denoise["method"]
    p = denoise["params"]

    if m == "hqdn3d_minimal":
        filters.append(f"hqdn3d={p['luma_s']}:{p['chroma_s']}:{p['luma_t']}:{p['chroma_t']}")
    elif m == "vaguedenoiser":
        filters.append(
            f"vaguedenoiser=threshold={p['threshold']}:method={p['method']}:nsteps={p['nsteps']}"
        )
    elif m == "bm3d":
        # BM3D roda exclusivamente no pipeline float32 do Cineon Mode (enhance/ package).
        # Não existe como filtro FFmpeg neste encoder — nunca usar frei0r=bm3d.
        # Se bm3d foi selecionado e o modo ainda é ffmpeg, o analyze() em
        # scripts/analyze_source.py já escalou para cineon automaticamente.
        # Fallback defensivo para FFmpeg Mode puro:
        sigma = p.get("sigma_spatial", 0.05)
        threshold = round(min(1.5 + sigma * 20, 2.5), 2)
        filters.append(
            f"vaguedenoiser=threshold={threshold}:method=soft:nsteps=8"
        )

    # Rolloff de highlights (se necessário)
    if rolloff:
        filters.append(rolloff)

    # LUT 3D
    if lut_path:
        filters.append(f"lut3d={lut_path}:interp=tetrahedral")

    # Dithering RPDF — obrigatório no Cineon Mode antes da conversão float32 → 8-bit
    # No FFmpeg Mode o pipeline já é 8-bit, dithering não se aplica aqui
    # (o _build_dither() do Cineon Mode é aplicado no PyAV pipeline, não aqui)
    # Para uso puramente FFmpeg Mode com LUT, o noise mínimo abaixo previne banding:
    # filters.append("noise=alls=1:allf=u")  # descomente se necessário

    # Scale e FPS — sempre por último
    filters.append("scale=1080:1920:flags=lanczos")
    filters.append("fps=30")

    return ",".join(filters)
```

---

## Etapa 4 — Relatório de análise adaptativa

Quando gerar parâmetros para o usuário, sempre incluir o raciocínio derivado
da análise — nunca apenas os valores finais. Formato padrão:

```
ANÁLISE ADAPTATIVA — [nome do arquivo]
─────────────────────────────────────────────
Noise profile:
  Luma noise (Laplacian):  XXX  [low/moderate/high]
  Chroma noise:            XXX  [low/moderate/high]
  Temporal noise:          XXX  [low/moderate/high]
  → Método derivado: [vaguedenoiser/BM3D/hqdn3d] com [parâmetros]

Complexidade:
  Spatial complexity:  XXX
  Motion magnitude:    XXX px/frame
  → aq-strength derivado: X.X | subme: X

Skin tones:
  Skin ratio:  X.XX  [baixo/moderado/alto]
  → deblock: [-1,-1 / 0,0] | aq proteção: [sim/não]

Highlights:
  Highlight load:  X.XX  → rolloff [ativo/inativo]
  [se ativo: knee_point=X.XXX, knee_output=X.XXX]

Parâmetros finais derivados:
  -vf "[chain completo]"
  -x264-params "ref=4:bframes=2:aq-mode=3:aq-strength=X.X:me=umh:subme=X:rc-lookahead=XX:deblock=X,X:keyint=60:min-keyint=1:scenecut=40:vbv-init=0.90"
─────────────────────────────────────────────
```

---

## Integração com Reels_Encoder_v2_FINAL.py

### FFmpeg Mode
- LUT padrão: `HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube`
- A análise adaptativa alimenta o `enhance/` package
- O Mock CNN (13D → 3D) usa exatamente as dimensões descritas na Etapa 1
- Output do CNN: [denoise_intensity, color_adjustment, sharpness_factor]

### Cineon Mode
- LUT padrão: `FilmLook_Portra400_SkinPriority_D65.cube`
- Pipeline 5-nós: DWG transforms → tone/gamut mapping → Cineon log → LUT → output
- A análise de skin_ratio e color_temp_proxy alimenta diretamente o nó de tone mapping
- MCTF (EMA): o temporal_noise feature define o peso da EMA
  - temporal_noise baixo (<5) → peso EMA alto (0.9) — mais smoothing temporal
  - temporal_noise alto (>15) → peso EMA baixo (0.5) — menos smoothing, preserva transições
- Dithering (`_build_dither()` RPDF): sempre ativo no Cineon Mode para prevenir banding
  na conversão float32 → 8-bit

### Ponto de hook recomendado no enhance/

```python
# No enhance/analyzer.py (ou equivalente)
features = {
    **extract_noise_features(representative_frame),
    **extract_complexity_features(frame, prev_frame),
    **extract_tonal_features(representative_frame),
    **extract_skin_color_features(representative_frame),
    "temporal_noise": compute_temporal_noise(frame_a, frame_b),
}

# Derivar e retornar para o pipeline
denoise_params = derive_denoise_params(features)
x264_params    = derive_x264_params(features, duration_s)
vf_chain       = build_vf_chain(features, duration_s, lut_path=LUT_PATH)
```
