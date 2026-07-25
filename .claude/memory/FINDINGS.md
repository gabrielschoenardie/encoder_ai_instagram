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

## Achado novo — 2026-07-25 (ciclo G)

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|---------------|------------------------|------------|--------------------|
| H1 | doc: valor canônico errado | `references/cineon-pipeline.md:117` | Fórmula e valor declarado se contradizem; o valor está errado desde sempre | S2 | fórmula `10^((95−685)/300)` = **0.0107977**; doc declara "≈ 0.005012" |
| H2 | placement de guard | `cineon_pipeline.py:801` | Guard do node3 vive no loader do node5, sob `if lut_file_path is not None` | S3 | esperado: guard no entry do Cineon Mode; medido: `LUT3D.__init__` |

- **H1 (S2):** a fórmula do doc está certa e bate com `colour-science`
  (`log_encoding_Cineon(0.0) = 0.092864` ⇔ `(685 + 300·log10(0.0107977))/1023`); o número
  `0.005012` ao lado dela é que está errado. O valor errado foi copiado para o PLAN.md do
  ciclo de 2026-07-18 (linha 29) e circulou a auditoria inteira como canônico — não foi
  pego porque a auditoria comparou o **código** contra `colour-science`, nunca contra esta
  linha do doc. O código sempre esteve certo. Corrigir a linha 117 do doc.
- **H2 (S3):** funciona hoje — `Reels_Encoder_v2_FINAL.py:3164-3176` garante que o path da
  LUT existe antes de instanciar `LUT3D`, então o guard roda no Cineon Mode antes do 1º
  frame. Mas a assinatura é `__init__(self, lut_file_path=None)`: um `LUT3D()` sem path
  pula o guard silenciosamente. Correto por convenção de chamada, não por construção.
  Mover para o topo de `run_ffmpeg_with_cineon()`.

## Achado — 2026-07-25 (ciclo infra/CI)

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| I-a | débito de lint pré-existente | `tools/` (37), `.claude/skills/.../scripts` (7), `ui/` (6), raiz (8) | 58 erros E4/E7/E9/F fora de `enhance/`; só 17 auto-fixáveis | S4 | esperado: 0; medido: 58 |

- **I-a (S4):** aparecem porque `[tool.ruff.lint] select` (ciclo I, item I2) passou a valer
  repo-wide com regras explícitas. **Não são regressão** — já existiam sob o default do
  ruff; ninguém viu porque o CI só roda `ruff check enhance/`, e `enhance/` está limpo de
  E/F. Fora do escopo do ciclo I, que trata só de `I001`. Decidir em ciclo próprio: pagar
  os 58, ou estreitar `select` por diretório via `[tool.ruff.lint.per-file-ignores]`.
  Enquanto não decidido, o CI segue verde — ele não olha esses diretórios.

### Status (2026-07-25)

| ID | status | onde |
|----|--------|------|
| A3 | corrigido | ciclo G (G1–G3); call site movido em H2 |
| E3d | corrigido | ciclo G (G4) |
| H1 | corrigido | ciclo H (H1a doc, H1b docstring) |
| H2 | corrigido | ciclo H (H2a/b guard no topo de `run_ffmpeg_with_cineon`, H2c teste do call site) |
| F2 | **fechado — limitação aceita** | ver abaixo |

**F2 não será corrigido.** A entrada real da LUT neste pipeline é ≥ 0.0928
(`log_encoding_cineon` clipa em [0,1]; lin=0 → 0.0928) e `output(0.0928) = +1.58e-05`,
são. O toe negativo só é alcançável usando a `.cube` standalone (Resolve, `lut3d` do
FFmpeg) fora deste pipeline; corrigi-lo alteraria o grade Portra em toda a faixa baixa
para consertar um caso que o pipeline nunca produz.
**Condição de reabertura:** se a `.cube` passar a ser distribuída para uso standalone,
F2 volta a valer.

## Achado — 2026-07-25 (ciclo infra/CI, PLAN J)

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| J-a | config duplicada à mão | `requirements.txt` vs `[project] dependencies` (pyproject.toml) | mesmos 9 pacotes em 2 arquivos; após J2 CI só lê pyproject, requirements.txt vira doc sem execução | S4 | esperado: 1 fonte de verdade; medido: 2 listas mantidas à mão, mesma classe de defeito do ciclo I |

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
