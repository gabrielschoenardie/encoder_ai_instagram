# Cineon Pipeline — Referência Técnica Completa

Pipeline de 5 nós do `Reels_Encoder_v2_FINAL.py` — Cineon Mode (`--cineon-pipeline on`).
Processamento per-frame em float32, implementado em `cineon_pipeline.py`.

**Stack:** `numpy` (obrigatório), `colour-science` (obrigatório — sem fallback manual,
ver Nó 3), `cupy` (opcional, GPU). PyAV faz a decodificação de frames em
`Reels_Encoder_v2_FINAL.py`, fora deste módulo.

> Este documento descreve o código real em `cineon_pipeline.py`. Se você notar
> qualquer divergência entre este texto e o código, o código é a fonte da
> verdade — atualize este arquivo, não o contrário.

---

## Visão geral do fluxo

```
Frame uint8 (PyAV decode, em Reels_Encoder_v2_FINAL.py)
        │
        ▼
[uint8 → float32 normalizado 0–1]
        │
        ▼
[Node 1] CST IN — node1_cst_in()
  Rec.709 gamma decode (eotf_rec709) → Rec.709 linear
  Matriz Rec.709 → DWG (MATRIX_REC709_TO_DWG)
  DWG linear → DWG Intermediate log (oetf_davinci_intermediate)
        │
        ▼
[Node 2] Primary — node2_primary()
  Exposure (stops, ancorado no 18% grey — _stops_to_log_offset)
  Saturation (split luma/chroma no espaço log)
  Lift / Gamma / Gain (log wheels, opcionais)
        │
        ▼
[Node 3] CST OUT — node3_cst_out()
  DWG Intermediate → DWG linear (eotf_davinci_intermediate)
  Tone mapping (apply_tone_mapping_davinci — soft-knee, 100 nits, knee=0.8, adaptation=9.0)
  Matriz DWG → Rec.709 (MATRIX_DWG_TO_REC709)
  Gamut mapping (apply_gamut_mapping_saturation_compression — knee=0.9)
  Rec.709 linear → Cineon Log (log_encoding_cineon)
        │
        ▼
[Node 4] Bridge — node4_cst_bridge()
  Passthrough (Node 3 já produz Cineon Log — nó preservado por arquitetura)
        │
        ▼
[Node 5] Portra 400 LUT — node5_portra400()
  FilmLook_Portra400_SkinPriority_D65.cube via LUT3D.apply() (trilinear)
  Output pode exceder [0,1] (shoulder/toe unclamped — ver color-pipeline.md)
        │
        ▼
[Consumidor — Reels_Encoder_v2_FINAL.py, fora do pipeline de 5 nós]
  quantize_uint8_dithered(): clip [0,1] → ×255 → dither RPDF opcional → round → uint8
        │
        ▼
FFmpeg pipe (stdin) → libx264 → MP4
```

**Sem estado entre frames:** cada frame é processado independentemente por
`process_frame_full_pipeline()`. Não há blending temporal, MCTF, optical flow
ou EMA — cada chamada recebe só o frame atual e os parâmetros de grading
(`exposure_offset`, `saturation`), não um objeto de estado.

---

## Backend: NumPy vs CuPy

`get_array_backend()` (linhas 70-81) retorna CuPy se instalado e uma GPU CUDA
estiver disponível, senão NumPy. `xp`/`backend_name` no nível de módulo
expõem o backend ativo. Nenhuma das funções do pipeline abaixo dependem
diretamente disso — são escritas em NumPy puro; o backend serve para uso
externo/futuro, não é injetado automaticamente nas funções de nó.

---

## Cor: matrizes e transfer functions

### DaVinci Wide Gamut (DWG) — não ACEScg

O espaço de trabalho intermediário é **DWG (DaVinci Wide Gamut)**, não ACEScg.
Primárias e whitepoint (`DWG_PRIMARIES`, `DWG_WHITEPOINT_D65`, linhas 91-98,
fonte: DaVinci Resolve Color Management Technical Guide):

```
Red:   (0.8000,  0.3130)
Green: (0.1682,  0.9877)
Blue:  (0.0790, -0.1155)
White: D65 (0.3127, 0.3290)
```

`build_rgb_to_xyz_matrix()` (linha 109) deriva RGB→XYZ a partir de primárias +
whitepoint; `MATRIX_REC709_TO_DWG` / `MATRIX_DWG_TO_REC709` (linhas 151-159)
são pré-computadas uma vez no import via `XYZ` como espaço intermediário.

### Transfer functions

| Função | Linha | Direção | Notas |
|---|---|---|---|
| `oetf_rec709` / `eotf_rec709` | 167 / 191 | Rec.709 gamma ↔ linear | `colour.models.oetf_BT709`/`oetf_inverse_BT709`; fallback manual (piecewise ITU-R) se colour-science ausente |
| `oetf_davinci_intermediate` / `eotf_davinci_intermediate` | 253 / 296 | DWG Intermediate log ↔ linear | `colour.models.oetf_DaVinciIntermediate` (ou `log_encoding_DaVinciIntermediate` em versões antigas); fallback manual aproximado |
| `log_encoding_cineon` / `log_decoding_cineon` | 330 / (após) | Cineon Log ↔ Rec.709 linear | `colour.models.log_encoding_Cineon`/`log_decoding_Cineon` — **exige colour-science**, levanta `RuntimeError` sem ela (sem fallback manual, ver nota abaixo) |
| `eotf_gamma_24` / `oetf_gamma_24` | 214 / 234 | Gamma 2.4 (BT.1886) ↔ linear | Utilitário definido mas **não usado** pelo pipeline de 5 nós ativo |

**Nota sobre `log_encoding_cineon`/`log_decoding_cineon`:** uma versão anterior
tinha um fallback manual para quando `colour-science` não estava instalada,
mas a fórmula estava errada (mapeava branco linear para o próprio black code
— produzia imagem preta). Como `colour-science` é dependência obrigatória do
pipeline Cineon (`requirements.txt`), o fallback foi removido: as funções
agora falham alto com `RuntimeError` em vez de produzir cor incorreta
silenciosamente. Ver `enhance/test_cineon_log_encoding.py`.

**Fórmula Cineon Log (via colour-science, Kodak standard):**
```
y = (685 + 300 · log10(x · (1 - black_offset) + black_offset)) / 1023
black_offset = 10^((95 - 685) / 300) ≈ 0.005012
```
Pontos de referência: `lin=0.0 → log≈0.0928` (black), `lin=0.18 → log≈0.457`
(18% grey), `lin=1.0 → log≈0.6697` (white reference — este é o valor que a
LUT Portra 400 espera como pico de branco, ver `CLAUDE.md` seção LUTs).

---

## Node 1 — CST IN (`node1_cst_in`, linha 407)

```
Rec.709 Gamma → [eotf_rec709] → Rec.709 Linear
              → [MATRIX_REC709_TO_DWG] → DWG Linear
              → [oetf_davinci_intermediate] → DWG Intermediate (log, unbounded)
```

Input: Rec.709 gamma float32 `[0, 1]`. Output: DWG Intermediate log, pode
exceder `[0, 1]` (highlights).

---

## Node 2 — Primary (`node2_primary`, linha 440)

Ajustes de grading no espaço DWG Intermediate (log), na ordem:

1. **Exposure** — `_stops_to_log_offset(stops)` (linha ~440) converte stops
   fotográficos em offset aditivo no log, ancorado no 18% grey: avalia
   `oetf_davinci_intermediate` em `0.18` e em `0.18 · 2^stops` e usa a
   diferença. Não é um fator constante — a curva DI tem offset aditivo, então
   a inclinação log-por-stop varia com o nível (~0.071-0.073 no range útil).
   `exposure_offset=1.0` dobra exatamente a luminância no 18% grey.
2. **Saturation** — separa luma (`frame.mean(axis=2)`) e chroma no espaço
   log, multiplica o chroma por `saturation`.
3. **Lift / Gamma / Gain** — color wheels clássicos (opcionais, default
   neutro): lift soma nas sombras, gamma aplica `power` preservando sinal,
   gain multiplica.

Ver `enhance/test_cineon_exposure.py` para a cobertura de regressão do
exposure.

---

## Node 3 — CST OUT (`node3_cst_out`, linha 512)

```
DWG Intermediate → [eotf_davinci_intermediate] → DWG Linear
                 → [apply_tone_mapping_davinci] → DWG Linear (comprimido, ≤1.0)
                 → [MATRIX_DWG_TO_REC709] → Rec.709 Linear
                 → [apply_gamut_mapping_saturation_compression] → Rec.709 Linear (in-gamut)
                 → [log_encoding_cineon] → Cineon Log [0, 1]
```

### Tone mapping (`apply_tone_mapping_davinci`, linha 582)

Soft-knee exponencial: abaixo de `knee` (default `0.8`, normalizado para
`max_output_nits=100`), passthrough linear; acima, compressão que se
aproxima assintoticamente de `1.0`:

```
normalized = linear / (max_output_nits / 100.0)
slope = 1.0 / (1.0 + adaptation)
tone_mapped = normalized                                              se normalized <= knee
            = knee + (1.0 - knee) · (1 - exp(-slope · (normalized - knee)))   se normalized > knee
```

`knee` precisa ser `< 1.0` para a compressão ter efeito (`(1.0 - knee)` é o
"tamanho" da faixa de compressão disponível) — um `knee=1.0` colapsa a curva
num hard clip `min(x, 1.0)` independente de `adaptation` (bug corrigido, ver
`enhance/test_cineon_tonemap.py`).

### Gamut mapping (`apply_gamut_mapping_saturation_compression`, linha 603)

Mesmo formato de soft-knee, aplicado à **magnitude do chroma** (não à
luminância) para comprimir saturação fora do gamut Rec.709 preservando hue:
`knee=0.9`, `max_saturation=1.0`.

---

## Node 4 — Bridge (`node4_cst_bridge`, linha 688)

Passthrough puro — `return frame_cineon.astype(np.float32)`. Existe apenas
para preservar a arquitetura de 5 nós; historicamente (Fase 26) o tone/gamut
mapping foi realocado do Nó 5 para o Nó 3 (evitando um roundtrip de Gamma 2.4
que causava quantização), e o Nó 4 ficou como ponto de transição vazio entre
o CST e a aplicação da LUT.

---

## Node 5 — Portra 400 LUT (`node5_portra400` + `LUT3D`, linhas 714-899)

`LUT3D` (linha 714) é um parser/aplicador de `.cube` próprio (não usa
`colour.LUT3D`):
- `_load_cube_file()`: lê `LUT_3D_SIZE` + pontos RGB, valida contagem
  (`lut_size³`), reshape `(N, N, N, 3)` — ordem Adobe `.cube` (R varia mais
  rápido, B mais devagar).
- `apply()`: clipa a **coordenada de lookup** de entrada para `[0, 1]`
  (domínio da LUT), interpola **trilinear** (8 vértices vizinhos, sem
  interpolador tetraédrico), retorna o resultado **sem clipar a saída** — o
  output pode exceder `[0, 1]` se a LUT foi baked unclamped (é o caso da
  `FilmLook_Portra400_SkinPriority_D65.cube` — ver `CLAUDE.md` seção LUTs
  para o porquê).

`node5_portra400()` é `return lut.apply(frame_cineon)` — nenhum
processamento adicional.

---

## Orquestração (`process_frame_full_pipeline`, linha 901)

```
frame_dwg          = node1_cst_in(frame_rec709_gamma)
frame_dwg_graded    = node2_primary(frame_dwg, exposure_offset, saturation)
frame_cineon        = node3_cst_out(frame_dwg_graded)
frame_cineon_pass   = node4_cst_bridge(frame_cineon)
frame_output        = node5_portra400(frame_cineon_pass, portra_lut)
```

Chamado uma vez por frame a partir do loop de decode PyAV em
`Reels_Encoder_v2_FINAL.py` (`run_ffmpeg_with_cineon`).

---

## Quantização final (fora deste módulo)

`quantize_uint8_dithered()` vive em `cineon_pipeline.py` mas é chamada pelo
consumidor em `Reels_Encoder_v2_FINAL.py`, não faz parte dos 5 nós:

```
scaled = frame_float32 * 255.0
scaled += uniform(-0.5, +0.5, size=scaled.shape)   # RPDF, se rng != None
uint8_out = clip(round(scaled), 0, 255).astype(uint8)
```

`rng=None` desativa o dither (equivalente a `--dither off`) mas ainda
arredonda em vez de truncar. Controlado pela flag `--dither` (`auto`/`on`/
`off`, default `auto`). Ver `CLAUDE.md` seção "Final quantization" e
`enhance/test_cineon_dither.py`.

---

## O que NÃO existe neste pipeline

Versões anteriores deste documento descreviam uma arquitetura que nunca foi
implementada. Para evitar recomendar algo inexistente numa sessão futura:

- **Sem ACEScg** — o espaço de trabalho wide-gamut é DWG (DaVinci Wide
  Gamut), não ACEScg.
- **Sem curva de Hable** — o tone mapping é o soft-knee exponencial de
  `apply_tone_mapping_davinci` (acima), não a S-curve de Uncharted 2.
- **Sem MCTF / consistência temporal** — não há optical flow (Farneback),
  EMA, nem qualquer estado entre frames. Cada frame é processado isolado.
- **Sem dithering por nó** — o dither RPDF acontece uma única vez, na
  quantização final (`quantize_uint8_dithered`), não dentro do Nó 5.
- **Sem `_validate_cineon_constants()`** — não há checkpoint de validação de
  constantes chamado na inicialização. As constantes Cineon vêm direto de
  `colour.models.log_encoding_Cineon`, não de constantes locais reimplementadas.
- **Sem interpolação tetraédrica** — `LUT3D.apply()` é trilinear.

---

## Considerações de memória e performance

| Operação | Custo por frame 1080×1920 |
|---|---|
| float32 RGB array | ~25 MB |
| `LUT3D.apply()` (trilinear, 8 vértices) | ~8 MB temporário |
| Peak total por frame | ~35–45 MB |

Processamento é sempre frame a frame (sem batching) — o loop em
`Reels_Encoder_v2_FINAL.py` escreve cada frame no pipe do FFmpeg assim que
`process_frame_full_pipeline()` retorna.

---

## Checkpoints de debugging

```python
def debug_frame_stats(label: str, arr: np.ndarray) -> None:
    """Inserir entre nós durante debugging para rastrear range e distribuição."""
    print(f"[{label}] shape={arr.shape} dtype={arr.dtype} "
          f"min={arr.min():.4f} max={arr.max():.4f} "
          f"mean={arr.mean():.4f} std={arr.std():.4f}")

# Uso:
# debug_frame_stats("Node1 out (DWG intermediate)", frame_dwg)
# debug_frame_stats("Node2 out (DWG graded)",        frame_dwg_graded)
# debug_frame_stats("Node3 out (Cineon log)",        frame_cineon)
# debug_frame_stats("Node5 out (LUT, unclamped)",    frame_output)

# Valores esperados:
# Node 1: pode exceder 1.0 (DWG wide gamut — normal)
# Node 2: mesma faixa do Node 1, deslocada por exposure/saturation
# Node 3: range [0.0, 1.0] — Cineon log normalizado (log_encoding_cineon clipa)
# Node 5: pode exceder [0.0, 1.0] — shoulder/toe unclamped da LUT; o clip
#         final acontece só em quantize_uint8_dithered()
```
