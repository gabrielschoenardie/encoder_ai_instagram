<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Auditoria Matemática: Pipeline Cineon + LUT Portra400

Data: 2026-07-18 | Ciclo: auditoria (nenhuma correção neste ciclo)

**Objetivo:** verificar matematicamente que a implementação do Cineon Mode em
`Reels_Encoder_v2_FINAL.py` corresponde às fórmulas canônicas de
`.claude/skills/instagram-reels-encoder/references/cineon-pipeline.md`, e que
`FilmLook_Portra400_SkinPriority_D65.cube` é numericamente sã (whitepoint,
black point, monotonicidade, skin hue, roll-off).

**Escopo fechado (arquivos permitidos):**
- `.claude/skills/instagram-reels-encoder/references/cineon-pipeline.md` (5 nós, fórmulas)
- `Reels_Encoder_v2_FINAL.py`: nós Cineon (node1–node5), `_validate_cineon_constants`, aplicação da LUT em float32
- `FilmLook_Portra400_SkinPriority_D65.cube` (raiz do repo)
- `.claude/skills/instagram-reels-encoder/references/color-pipeline.md` — SÓ ordem de aplicação e espaço de cor
- Scripts de auditoria: criar apenas em `audit_tmp/` (não commitar)

**Fora de escopo:** FFmpeg Mode, VBV, GOP, zones, MCTF, Mock CNN,
`HollywoodCinema_*.cube` e qualquer LUT do FFmpeg Mode. Bug fora do escopo →
uma linha em `FINDINGS.md`, sem investigar.

## Valores canônicos (extraídos de cineon-pipeline.md — referência para todas as tarefas)

Fórmula Cineon log (ref black 95, ref white 685; fator 300 = gamma 0.6 / passo 0.002):

```
y = (685 + 300·log10(x·(1 − black_offset) + black_offset)) / 1023
black_offset = 10^((95 − 685)/300) ≈ 0.005012
Pontos de referência: lin 0.0 → log ≈ 0.0928 | lin 0.18 → ≈ 0.457 | lin 1.0 → ≈ 0.6697
```

DWG primaries / whitepoint: R (0.8000, 0.3130) · G (0.1682, 0.9877) · B (0.0790, −0.1155) · W D65 (0.3127, 0.3290).
Matrizes `MATRIX_REC709_TO_DWG` / `MATRIX_DWG_TO_REC709` não têm coeficientes no doc — recomputar via colour-science (XYZ intermediário, D65).

Tone map soft-knee exponencial (Node 3, em DWG **linear** — sem Hable):

```
normalized  = linear / (max_output_nits / 100.0)
slope       = 1.0 / (1.0 + adaptation)
tone_mapped = normalized                                                  se normalized ≤ knee
            = knee + (1 − knee)·(1 − exp(−slope·(normalized − knee)))     se normalized > knee
Defaults: knee=0.8, max_output_nits=100, adaptation=9.0 (⇒ slope=0.1)
```

Gamut map: soft-knee na magnitude do chroma, hue preservado, `knee=0.9`, `max_saturation=1.0`.

Ordem canônica dos nós (tudo float32, sem uint8 intermediário):

```
node1_cst_in:  Rec709 gamma → eotf_rec709 → Rec709 linear → M_709→DWG → DWG linear → oetf_davinci_intermediate → DWG Intermediate (log, UNBOUNDED)
node2_primary: exposure (_stops_to_log_offset, âncora 18% grey) → saturation (split luma/chroma no log) → lift/gamma/gain
node3_cst_out: eotf_davinci_intermediate → DWG linear → TONE MAP → M_DWG→709 → Rec709 linear → GAMUT MAP → log_encoding_cineon → Cineon log [0,1]
node4_bridge:  passthrough float32 puro
node5_portra:  LUT3D .cube — clip da coordenada de ENTRADA para [0,1], interpolação trilinear, SAÍDA sem clip
```

## Tabela de auditoria

Tolerâncias default: constantes = igualdade exata no fonte; avaliação numérica float32 = |Δ| ≤ 1e−3 salvo indicado. Divergência acima da tolerância = bug confirmado.

| ID | tarefa | agente alvo | critério de "bug confirmado" |
|----|--------|-------------|------------------------------|
| A1 | Extrair constantes da fórmula log/linear no código (`log_encoding_cineon` e inversa): 685, 300, 1023, black_offset ≈ 0.005012 derivado de 95/685/300 | `leitor` | Qualquer constante ≠ canônica, ou black_offset hardcoded divergente da derivação |
| A2 | Avaliar numericamente a função Cineon do código nos 3 pontos de referência (0.0→0.0928, 0.18→0.457, 1.0→0.6697) e round-trip log→lin→log | `executor` | \|Δ\| > 1e−3 em qualquer ponto, ou round-trip \|Δ\| > 1e−4 |
| A3 | Extrair `_validate_cineon_constants`: quais constantes valida e onde é chamada no caminho do Cineon Mode | `leitor` | Valida valores ≠ canônicos, subconjunto incompleto, ou nunca é invocada |
| B1 | Comparar `MATRIX_REC709_TO_DWG` / `MATRIX_DWG_TO_REC709` do código vs matrizes recomputadas via colour-science a partir dos primaries DWG + D65 canônicos | `executor` | max \|Δ coef\| > 1e−4 |
| B2 | Round-trip matricial: M_709→DWG · M_DWG→709 ≈ identidade | `executor` | max \|Δ\| > 1e−6 |
| B3 | Extrair a cadeia de transforms do node1 (eotf_rec709 → matriz → oetf_davinci_intermediate) com espaços de entrada/saída | `leitor` | Transform ausente, trocado ou fora de ordem vs cadeia canônica |
| C1 | Extrair a ordem interna do node3: eotf (log→**linear**) ANTES do tone map; matriz DWG→709 depois do tone map; gamut map depois da matriz; `log_encoding_cineon` por último | `leitor` | Tone map aplicado em log, ou qualquer inversão na sequência |
| C2 | Extrair o loop per-frame: nós executam 1→2→3→4→5, tudo float32, sem uint8/clamp entre nós | `leitor` | Ordem divergente, dtype intermediário ≠ float32, ou clamp intermediário |
| C3 | Extrair de `color-pipeline.md` a ordem de aplicação e espaços de cor documentados, p/ cruzar com `cineon-pipeline.md` e o código | `leitor` | Docs divergem entre si ou do código quanto a ordem/espaço |
| D1 | Extrair control points no código: tone map `knee=0.8`, `adaptation=9.0`, `max_output_nits=100`; gamut `knee=0.9`, `max_saturation=1.0` | `leitor` | Qualquer default ≠ canônico |
| D2 | Testar continuidade e compressão do tone map do código: contínuo em `normalized=knee`, monotônico crescente, assíntota ≤ 1.0 | `executor` | Descontinuidade > 1e−6 no knee, derivada negativa, ou output > 1.0 |
| D3 | Testar preservação de hue do gamut map: cor fora do gamut → hue angle antes/depois | `executor` | Δhue > 0.5° em amostras fora de gamut |
| D4 | Testar `_stops_to_log_offset`: +1 stop no log DWG Intermediate ⇔ ×2 em linear (âncora 18% grey) | `executor` | \|razão linear − 2.0\| > 1e−3 |
| E1 | Extrair saída do node1/entrada do node2: DWG Intermediate deve ficar unbounded (highlights > 1.0 preservados até o tone map) | `leitor` | clip/clamp na saída do node1 ou entrada do node2 |
| E2 | Extrair a aplicação da LUT: coordenada de entrada clipada a [0,1], trilinear, saída SEM clip, float32 fim-a-fim | `leitor` | Falta clip de entrada, clip indevido de saída, ou cast p/ uint8 dentro do apply |
| E3 | Extrair o pós-node5: clamp final [0,1] existe SÓ após node5, antes da quantização uint8 (com dither — commit e7c3891) | `leitor` | Clamp final ausente, ou clamp adicional entre nós 1–5 |
| F1 | Amostrar .cube — eixo neutro/whitepoint D65: (t,t,t) em grade; saída deve permanecer neutra; no branco Cineon (0.6697) saída ≈ branco esperado | `executor` | Desvio de neutralidade max \|canal−média\| > 1e−2 em qualquer t |
| F2 | Amostrar .cube — black point: entrada em 0.0 e no black Cineon (0.0928); saída próxima de preto, sem lift nem crush | `executor` | Saída no black fora de [0, 0.05], ou output(0) > output(0.0928) |
| F3 | Amostrar .cube — monotonicidade: eixo neutro e eixos R/G/B por canal, saída não-decrescente | `executor` | Qualquer derivada discreta < −1e−4 |
| F4 | Amostrar .cube — skin hue Portra: patch de tons de pele (em Cineon log), medir Δhue entrada→saída | `executor` | Δhue > 5° em qualquer amostra de pele (baseline identity: esperado ≈ 0°) |
| F5 | Amostrar .cube — roll-off de highlights: topo do eixo neutro com derivada decrescente (compressiva), sem hard clip prematuro; clipping conhecido no peak = 2.93e−2 (documentado) | `executor` | Derivada zero/clip antes de t=0.95, ou erro no peak > 3.5e−2 |
| F6 | Verificar .cube — integridade: `LUT_3D_SIZE` coerente com nº de pontos, DOMAIN_MIN/MAX = [0,1], sem NaN/Inf; ordem Adobe (R varia mais rápido) confere com o reshape do parser | `executor` | Header inconsistente, NaN/Inf, ou ordem de reshape do parser invertida |

## Notas de execução

- **Consolidação de scripts:** o `executor` DEVE agrupar A2+B1+B2+D2+D3+D4 num único
  script (`audit_tmp/audit_cineon_math.py`) e F1–F6 noutro (`audit_tmp/audit_lut.py`).
  Não commitar `audit_tmp/`. Saída: tabela `ID | medido | esperado | Δ | PASS/FAIL`.
  Os scripts importam as funções reais de `Reels_Encoder_v2_FINAL.py` — não reimplementar
  a lógica auditada; reimplementar apenas o LADO esperado (colour-science / fórmulas acima).
- **Tarefas de `leitor`** (A1, A3, B3, C1–C3, D1, E1–E3): retornar trechos verbatim com
  número de linha; o veredito de comparação é do Orquestrador. Agrupar num único dispatch.
- **Resultados:** cada agente appenda em `STATE.md` (append-only): ID, resultado bruto,
  PASS/FAIL pelo critério da tabela. Orquestrador consolida o veredito final.
- **Nenhuma correção neste ciclo** — auditoria apenas. Correções entram num PLAN.md novo.
