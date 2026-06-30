---
name: instagram-reels-encoder
metadata:
  version: 2.0.0
description: >
  Use this skill for ANY Instagram Reels (9:16) encoding task: FFmpeg params, VBV
  rate control, adaptive AI analysis, denoise, color/LUT pipeline, VMAF, GOP, or
  Instagram ingest compliance. Trigger for: FFmpeg, Reels, H.264, VBV, BM3D,
  vaguedenoiser, hqdn3d, LUT 3D, VMAF, VMAF NEG, recompression, CRF, BT.709, GOP,
  LUFS, blocking, banding, waxy skin, Cineon mode/log, DWG, colour-science, Hable
  tone mapping, RPDF dithering, ACEScg, HollywoodCinema/Portra400 LUT, x264 zones,
  segment bit allocation, premium x264 stack, x264-params syntax (colon vs comma),
  MCTF, Meta/Instagram. Also: "gera o comando FFmpeg", "parâmetros para Reels",
  "risco de recompressão", "valida conformidade Instagram", "medir VMAF", "análise
  adaptativa", "derivar parâmetros", "pipeline Cineon", "aloca bits por shot".
  Encapsulates "Metodologia Gabriel": adaptive AI (no fixed presets),
  analyze_source.py, validate_encode.sh, measure_vmaf.sh, 5-node Cineon pipeline,
  artifact diagnosis, GOP, x264 zones, VMAF NEG.
---

# Instagram Reels Encoder — Metodologia Gabriel

Encoder premium para H.264 8-bit 1080×1920 com foco em **zero recompressão** e **máxima
preservação perceptual** na plataforma Instagram/Meta.

---

## Decisão Rápida: Qual módulo carregar?

| Contexto do usuário | Leia / Execute |
|---|---|
| Pede comando FFmpeg / parâmetros de encode | Este arquivo (seções abaixo) |
| Pergunta sobre VBV, maxrate, bufsize, 2-pass vs CRF | `references/vbv-rate-control.md` |
| Pergunta sobre GOP, keyint, scenecut, I-frames | `references/vbv-rate-control.md` (seção GOP) |
| Pergunta sobre noise, denoise, BM3D, vaguedenoiser | `references/denoise-pipeline.md` |
| Pergunta sobre LUT, BT.709, cor, highlights | `references/color-pipeline.md` |
| Pergunta sobre conformidade Instagram, LUFS, limites técnicos | `references/instagram-ingest-rules.md` |
| **Análise adaptativa de conteúdo / derivação de parâmetros por IA** | **`references/adaptive-analysis.md`** |
| **FFmpeg Mode vs Cineon Mode — quando usar cada um** | **`references/encoder-modes.md`** |
| **Cineon Mode — pipeline 5-nós, fórmulas, colour-science** | **`references/cineon-pipeline.md`** |
| **Blocking, banding, waxy skin, shimmer, clipping, artefatos** | **`references/artifact-diagnosis.md`** |
| **Montar `-x264-params` (colon vs vírgula, stack premium)** | **`references/x264-param-syntax.md`** |
| **Alocação de bits por shot (x264 zones, cinema)** | **`references/segment-bit-allocation.md`** |
| **Executar análise completa do source (Passo 1 automatizado)** | **`scripts/analyze_source.py`** |
| **Validar conformidade técnica pós-encode** | **`scripts/validate_encode.sh`** |
| **Medir qualidade perceptual pós-encode** | **`scripts/measure_vmaf.sh`** |
| Análise de risco / relatório técnico completo | Todos os reference files |

---

## Perfis de Encode — Detecção Automática por Duração

**Regra primária:** sempre perguntar (ou inferir do contexto) a duração do Reel antes de gerar
parâmetros. A duração determina o perfil obrigatório.

### Maximum Quality — Reels ≤ 30s
```
target bitrate : 10000 kbps
maxrate        : 11200 kbps
bufsize        : 15000 kbps
vbv-init       : 0.90
```

### Safe Premium — Reels ≥ 40s
```
target bitrate : 8000 kbps
maxrate        : 9000 kbps
bufsize        : 12500 kbps
vbv-init       : 0.90
```

> **Zona de transição 30–40s:** usar Safe Premium com target=9000 como compromisso seguro.

---

## Template Base FFmpeg — H.264 Instagram Reels

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.0 \
  -pix_fmt yuv420p \
  -vf "scale=1080:1920:flags=lanczos,fps=30" \
  -b:v <TARGET>k \
  -maxrate <MAXRATE>k \
  -bufsize <BUFSIZE>k \
  -x264-params "ref=4:bframes=2:b-adapt=2:trellis=2:mixed-refs=1:aq-mode=3:aq-strength=0.8:me=umh:subme=8:rc-lookahead=60:keyint=60:min-keyint=1:scenecut=40:vbv-init=0.90" \
  -color_primaries bt709 \
  -color_trc bt709 \
  -colorspace bt709 \
  -c:a aac \
  -b:a 128k \
  -ar 44100 \
  -ac 2 \
  -movflags +faststart \
  -y output.mp4
```

Substituir `<TARGET>`, `<MAXRATE>`, `<BUFSIZE>` conforme perfil acima.
> `vbv-init` é parâmetro x264 — sempre dentro de `-x264-params`, nunca como flag FFmpeg standalone.
> O stack premium (`b-adapt=2:trellis=2:mixed-refs=1`) está ativo por padrão. `keyint`,
> `scenecut`, `psy-rd`, `deblock` e `zones` são **derivados adaptativamente** e
> substituem os valores do template — este é só o fallback. Sintaxe e armadilhas
> colon-vs-vírgula: `references/x264-param-syntax.md`.

---

## Workflow Padrão — Metodologia Gabriel

Sempre seguir esta ordem. Não pular etapas.

### Passo 1 — Análise adaptativa do source

Executar `analyze_source.py` — automatiza toda a análise e gera o comando final:

```bash
# Verificar dependências (uma vez, antes do primeiro uso)
pip install -r scripts/requirements.txt
python -c "import av, cv2, numpy, colour, rich; print('OK')"

# Análise completa com recomendação automática de modo
python scripts/analyze_source.py input.mp4

# Com exportação JSON (para log e integração com o encoder)
python scripts/analyze_source.py input.mp4 --json analise.json

# Forçar modo específico
python scripts/analyze_source.py input.mp4 --mode cineon
python scripts/analyze_source.py input.mp4 --mode ffmpeg --frames 10
```

O script extrai o **vetor 13D de features** (noise, complexidade, tonal, skin, cor),
deriva todos os parâmetros, recomenda FFmpeg Mode vs Cineon Mode e imprime o
**comando FFmpeg completo pronto para rodar**.

Ver `references/adaptive-analysis.md` para a metodologia e
`references/encoder-modes.md` para a lógica de seleção de modo.

### Passo 2 — Risk Score de Recompressão

Calcular o score somando os pontos de cada critério. Resposta direta: se score ≥ 5, avisar o usuário antes de gerar o comando.

| Critério | Condição | Pontos |
|---|---|---|
| Bit depth | Source 10-bit ou 12-bit | +4 |
| Codec do source | HEVC/H.265 | +2 |
| Chroma | Source 4:2:2 ou 4:4:4 | +3 |
| Bitrate source | > 15000 kbps | +2 |
| Bitrate source | < 5000 kbps (up-encode) | +1 |
| Color space | Source não-BT.709 sem LUT | +2 |
| FPS | Source 60fps sem conversão | +1 |
| Resolução | Source ≠ 1080×1920 sem scale | +1 |
| Audio | Codec ≠ AAC no source | +1 |

**Score 0–2 →** 🟢 Risco mínimo — encode direto  
**Score 3–4 →** 🟡 Risco moderado — checar os critérios marcados  
**Score 5–7 →** 🔴 Risco alto — recompressão provável, requer conversão  
**Score 8+ →** 🔴 Recompressão garantida — corrigir todos os critérios antes do encode

Critérios de risco adicionais (sem pontuação, mas bloqueantes):
- Noise elevado + CRF sem denoise → blocking em textura pós-recompressão
- Variação extrema de bitrate em janelas curtas → buffering → recompressão adaptativa

### Passo 3 — Derivar pipeline de denoise adaptativamente

**Não usar preset por tipo de cena.** Derivar com base nas features medidas:
- `luma_noise` (Laplacian variance) + `chroma_noise` + `temporal_noise` → método e parâmetros
- `skin_ratio` → cap nos parâmetros para preservar textura de pele
- Ver `references/adaptive-analysis.md` → função `derive_denoise_params()`
- Ver `references/denoise-pipeline.md` para thresholds de referência por método

### Passo 4 — Decidir pipeline de cor
- Source já em BT.709 → passthrough
- Source em S-Log / C-Log / V-Log → converter + aplicar LUT antes do encode
- LUT 3D (.cube) → inserir via `lut3d` filter no -vf chain

Ver `references/color-pipeline.md` para chain de filtros completo.

### Passo 4b — GOP Adaptativo (Pass-1 leve)

`analyze_source.py` executa um **Pass-1 via ffprobe** que extrai os timestamps reais
dos I-frames do source antes do encode. `derive_gop()` combina essa evidência com
`motion_magnitude` e `skin_ratio` para produzir uma das três estratégias:

| Estratégia | Quando ocorre | Parâmetros gerados |
|---|---|---|
| `fixed` | Cortes regulares (CV < 0.20) | `keyint=N:scenecut=40` |
| `scenecut_only` | Plano único ou ffprobe indisponível | `keyint=60:scenecut=40` |
| `dual_coverage` | Cortes irregulares (CV ≥ 0.20) | `keyint=N:scenecut=50` + `-force_key_frames "t1,t2,t3,..."` (timestamps do Pass-1) |

O resultado é exposto em `result.gop_profile` (dict com `keyint`, `scenecut`,
`force_keyframes`, `strategy`, `cut_rhythm`, `reasoning`). Hard cap absoluto:
`keyint ≤ 60` (regra Instagram). Ver `references/vbv-rate-control.md` seção
"GOP Structure" para a lógica completa.

### Passo 4c — Alocação de bits por shot (x264 zones)

Reaproveitando os cortes já medidos no Pass-1, `derive_zones()` distribui mais
bits aos shots complexos e menos aos estáticos — **encode por cena** em
single-pass, com o orçamento global preservado (`maxrate`/`bufsize` seguem como
teto rígido de conformidade). Exposto em `result.zones_profile` (`zones`,
`zone_count`, `budget_effective`). Retorna `None` em single-take, demanda
uniforme ou fallback de ffprobe. `build_ffmpeg_cmd()` injeta `:zones=...`
automaticamente quando aplicável. Ver `references/segment-bit-allocation.md`.

### Passo 5 — Montar comando FFmpeg final
Combinar: perfil VBV + stack premium + denoise filter + color filter + GOP
derivado + zones (se houver). Sempre gerar o comando **completo**, pronto para
rodar — nunca parcial. `build_ffmpeg_cmd()` já injeta `-force_key_frames`
(estratégia `dual_coverage`) e `:zones=` (quando há shots a diferenciar)
automaticamente.

### Passo 6 — Validação pós-encode

Executar os dois scripts em sequência. Ambos obrigatórios para produção final.

```bash
# Passo 6a — Conformidade técnica (instantâneo, sem reference)
bash scripts/validate_encode.sh output.mp4

# Passo 6b — Qualidade perceptual VMAF (requer source original)
# subsample=5 → 5x mais rápido, precisão suficiente para produção
# subsample=1 → todo frame, para validação final de entrega
bash scripts/measure_vmaf.sh source.mp4 output.mp4 5
```

Critérios de aprovação:
- `validate_encode.sh` → "APROVADO" (zero ❌) obrigatório para upload
- `measure_vmaf.sh` usa o modelo **NEG** (`vmaf_v0.6.1neg`) por padrão — não premia
  sharpening/denoise, então o score reflete fidelidade real (override:
  `VMAF_MODEL=vmaf_v0.6.1`). Os targets abaixo já assumem NEG.
- VMAF ≥ 93 para Maximum Quality (≤30s)
- VMAF ≥ 90 para Safe Premium (≥40s)
- VMAF harmonic mean deve estar próximo da mean — delta > 3 indica cenas problemáticas

### Passo 6b — Loop de iteração quando VMAF falha

Se VMAF reprovado, ajustar na ordem abaixo (do mais impactante para o menos):

| VMAF score | Primeiro ajuste | Segundo ajuste | Terceiro ajuste |
|---|---|---|---|
| < 85 | Aumentar `b:v` em +1000 kbps | Verificar se denoise está excessivo | Reduzir `sigma` BM3D em 0.01 |
| 85–89 | Aumentar `aq-strength` +0.1 | Mudar `aq-mode=3` para `aq-mode=2` | 2-pass encode |
| 89–target | Aumentar `rc-lookahead` para 60 | Aumentar `subme` para 9 | Adicionar `psy-rd=0.8` |

**Regra de iteração:** reencoder com um único parâmetro alterado por vez, medir
VMAF novamente com `subsample=5`. Máximo 3 iterações antes de escalar o modo
(FFmpeg → Cineon) ou aceitar o score.

**Quando escalar para Cineon Mode:** VMAF < 88 após 3 iterações em FFmpeg Mode
com `luma_noise > 150` ou `highlight_load > 0.15`. Ver `references/encoder-modes.md`.

### Passo 7 — Relatório Técnico
Quando solicitado, gerar relatório estruturado com:
1. Perfil selecionado + justificativa (duração)
2. Análise de risco de recompressão
3. Pipeline de denoise aplicado (ou justificativa de ausência)
4. Pipeline de cor aplicado
5. Comando FFmpeg gerado
6. Métricas de validação (VMAF, bitrate real, conformidade)
7. Recomendações e alertas

---

## Regras de Ouro — Nunca Violar

1. **Nunca gerar parâmetros sem saber a duração** do Reel. É a variável mais crítica.
2. **Nunca recomendar CRF puro** para Reels de produção — VBV obrigatório para estabilidade.
3. **Nunca omitir `-movflags +faststart`** — quebra o streaming no Instagram.
4. **Nunca usar `-pix_fmt` diferente de `yuv420p`** — Instagram rejeita 4:2:2 e 4:4:4.
5. **Sempre preservar BT.709** no output — não usar colorspace sem confirmar source.
6. **Nunca recomendar bitrate acima de 11200 kbps** — ceiling de ingestão Instagram.
7. **Sempre gerar comandos completos** — incluindo áudio, container e faststart.
8. **Sempre validar com `validate_encode.sh` antes de recomendar upload** — nunca assumir conformidade sem checar.
9. **Sempre interpretar VMAF harmonic mean**, não só a média — delta > 3 entre mean e hm indica cenas com queda brusca de qualidade.
10. **Nunca usar `:` dentro de valores de `-x264-params`.** O separador de params é `:`; apenas `deblock`, `psy-rd` e `zones` carregam vírgula (e `zones` também `/`). `deblock=-1:-1` ou `psy-rd=1.0:0` quebram o parse. Conferir `references/x264-param-syntax.md`.

---

## Comunicação com o Usuário

Gabriel opera em nível de engenharia sênior. Usar terminologia técnica diretamente:
- VBV, CRF, VMAF, BM3D, YUV, BT.709, LUT 3D — sem explicar o básico
- Ir direto ao ponto técnico, sem introduções genéricas
- Sempre justificar escolhas de parâmetros com raciocínio de engenharia
- Quando houver tradeoff (qualidade vs tempo de encode), apresentar ambas as opções
- Responder em português, salvo termos técnicos que não têm tradução precisa
