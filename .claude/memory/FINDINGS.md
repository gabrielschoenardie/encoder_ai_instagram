<!-- Escreve: qualquer agente que encontrar bug fora do escopo atual. Lê: Orquestrador. -->
# FINDINGS

## Auditoria matemática Cineon + LUT — 2026-07-18 (bugs confirmados)

Evidência: leitor (extratos verbatim) + executor (audit_tmp/audit_cineon_math.py, audit_tmp/audit_lut.py; brutos em STATE.md). Veredito: Orquestrador.

| ID | categoria | arquivo:linha ou coord .cube | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------------------------------|------------------------|------------|--------------------|
| A3 | validação de constantes | cineon_pipeline.py / Reels_Encoder_v2_FINAL.py (ausente) | `_validate_cineon_constants` não existe no codebase; guard de constantes Cineon nunca roda | S2 | esperado: função valida 95/685/300/black_offset no caminho Cineon; medido: grep = 0 ocorrências |
| F2 | LUT black point | FilmLook_Portra400_SkinPriority_D65.cube @ (0,0,0) | Toe da LUT produz preto negativo; fora do critério [0, 0.05] | S3 | esperado: output(0) ∈ [0, 0.05]; medido: −0.025429 |
| E3d | doc vs código (ordem de ops) | cineon-pipeline.md:55 vs cineon_pipeline.py:982 | Doc descreve clip antes de dither/round; nessa ordem 255.5 arredonda p/ 256 → overflow uint8 | S3 | esperado (doc): clip[0,1]→×255→dither→round; código (correto): ×255→dither→round→clip[0,255] |

### Contexto dos vereditos

- **A3 (S2):** único bug estrutural. O escopo do PLAN.md referencia a função como parte do
  pipeline; ela nunca foi escrita (ou foi removida). As constantes estão corretas hoje
  (A2/B1 PASS via colour-science), mas nada impede regressão silenciosa.
- **F2 (S3, mitigado):** entrada real da LUT no pipeline é ≥ 0.0928 — `log_encoding_cineon`
  (node3) clipa em [0,1] e lin=0 → 0.0928; output(0.0928) = +1.58e-05 (são). O toe negativo
  só é atingível usando a .cube standalone (Resolve/FFmpeg lut3d) fora deste pipeline.
- **E3d (S3):** código está correto; o bug é do documento. Corrigir a linha do fluxo em
  cineon-pipeline.md num ciclo de docs.

### Status (2026-07-25)

| ID | status | onde |
|----|--------|------|
| A3 | em correção | PLAN.md 2026-07-25, itens G1–G3 |
| E3d | em correção | PLAN.md 2026-07-25, item G4 |
| F2 | **fechado — limitação aceita** | ver abaixo |

**F2 não será corrigido.** A entrada real da LUT neste pipeline é ≥ 0.0928
(`log_encoding_cineon` clipa em [0,1]; lin=0 → 0.0928) e `output(0.0928) = +1.58e-05`,
são. O toe negativo só é alcançável usando a `.cube` standalone (Resolve, `lut3d` do
FFmpeg) fora deste pipeline; corrigi-lo alteraria o grade Portra em toda a faixa baixa
para consertar um caso que o pipeline nunca produz.
**Condição de reabertura:** se a `.cube` passar a ser distribuída para uso standalone,
F2 volta a valer.

### Não-bugs (medidos, dentro do critério — registro para não reabrir)

- **F5 convexidade:** 2ª derivada +0.932 em t∈[0.9,1.0] (não-compressiva), mas critério da
  tabela (clip antes de t=0.95 / erro no peak) não disparou: derivada mín 8.53 > 0, peak
  1.64e-3 ≪ 3.5e-2. Faixa t>0.67 é superwhite inatingível para neutros (matriz DWG→709
  preserva neutralidade; log ≤ 0.6697). Não é bug.
- **F4 skin hue:** Δhue até −4.40° (< 5°). LUT não é identity na região de pele (eixo
  neutro é identity a 4e-16; pele desloca warm) — consistente com "SkinPriority", não bug.
- **A2/B1/B2/D2/D3/D4:** matemática do pipeline confere com colour-science/fórmulas
  canônicas com Δ ≤ 3.2e-4 (a maioria ≤ 1e-6). C1/C2/B3/D1/E1/E2: ordem, defaults e
  política de clamp conferem com o canônico (extratos no histórico do leitor).
