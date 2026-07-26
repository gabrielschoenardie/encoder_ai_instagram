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

## Achado — 2026-07-25 (ciclo infra/CI, PLAN J) — FECHADO em PLAN L

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| J-a | config duplicada à mão | `requirements.txt` vs `[project] dependencies` (pyproject.toml) | mesmos 9 pacotes em 2 arquivos; após J2 CI só lê pyproject, requirements.txt vira doc sem execução | S4 | esperado: 1 fonte de verdade; medido: 2 listas mantidas à mão, mesma classe de defeito do ciclo I |

**Fechado:** `requirements.txt` agora é `-e .[opencv]` (uma linha, aponta para
`pyproject.toml`) com comentário explícito contra reexpandir a lista. CI ganhou um step
de `pip install --dry-run -r requirements.txt` que acusa se o arquivo divergir de novo.

### Achado novo (não-bloqueante) — descoberto verificando o fechamento de J-a

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| J-b | doc: fallback desatualizado | `MANUAL_INSTALACAO.txt:295-309` (APÊNDICE A) | Lista de fallback manual do requirements.txt já faltava `pydantic`/`scipy` antes deste ciclo; diverge mais agora que o arquivo real é `-e .[opencv]` | S4 | esperado: fallback igual às deps reais; medido: 8 pacotes fixos, faltando 2, formato de lista fixa que o arquivo real não usa mais |

- **J-b (S4, pré-existente, não é regressão deste ciclo):** instrução para o usuário
  criar `requirements.txt` manualmente **se ele não existir** — caminho raro, o arquivo
  sempre existiu no repo. Não é falso hoje (instalaria pacotes desatualizados, mas
  funcionaria), só está defasado. Mesma família de defeito (lista mantida à mão,
  provavelmente a mais antiga de todas). Ciclo futuro: ou apontar o apêndice para
  `pip install -e .[opencv]`, ou removê-lo (o arquivo real nunca falta).

## Achado — 2026-07-25 (ciclo O, auditoria README.md) — FECHADO

Evidência: Orquestrador (leitura direta do README.md + grep/glob no repo + `pytest --collect-only`
+ `git log -p -- requirements.txt`). Sem leitor/executor envolvidos nesta auditoria.

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| O-a | doc: contagem desatualizada | `README.md:434,626,637` | Contagem de testes da UI defasada, repetida 3x | S4 | esperado: contagem real; medido: doc diz "105 testes", `pytest ui/ --collect-only` = 111 |
| O-b | doc: rótulo "opcional" contradiz instalação padrão | `README.md:144` (tabela Requisitos) vs `README.md:81,202` (Quick Start / Instalação Completa) | `opencv-python` marcado opcional mas instalado sempre pelo caminho recomendado | S4 | esperado: rótulo bate com o que os caminhos documentados instalam; medido: `requirements.txt` = `-e .[opencv]` (fechamento J-a) → ambos os caminhos que usam `pip install -r requirements.txt` instalam opencv incondicionalmente; só `pip install .` (seção separada, linha 216) deixa de fora |

- **O-a:** `pytest ui/ --collect-only` conta 111 testes hoje contra os "105" citados no
  texto. Baseline da suíte completa confirmado sem regressão: `4 failed, 342 passed`
  (as 4 falhas são as mesmas de sempre — encoding de console no Windows, não é bug novo).
- **O-b (pré-existente, não é regressão do ciclo J-a/L):** confirmado via `git log -p --
  requirements.txt` que o `requirements.txt` antigo (pré-refactor) já instalava
  `opencv-python` incondicionalmente — estava só sob um comentário "DEPENDÊNCIAS
  OPCIONAIS" cosmético, sem gating real. O ciclo J-a/L1 preservou esse comportamento ao
  migrar para `-e .[opencv]` (decisão correta para não regredir instalação existente),
  mas isso deixa a tabela de Requisitos e a seção "Instalação via pip" descrevendo dois
  caminhos "completos" com composição de dependência diferente, sem nota explicando a
  diferença. Corrigir a documentação, não o `requirements.txt`.

**Fechado (commit `6a9e12f`, push `9b6ed26..6a9e12f`):** O-a — as 3 ocorrências de
"105 testes" em `README.md` (linhas 434/626/637) corrigidas para "111 testes"
(`pytest ui/ --collect-only`). O-b — nota de rodapé da tabela de Requisitos
(`README.md:147`) esclarece que `pip install -r requirements.txt` (Quick Start/Instalação
Completa) instala opencv por padrão via `-e .[opencv]`, e que `pip install .` é o caminho
sem opencv; nenhum marcador `⚪`/`✅` da tabela foi alterado. Executor rodou O1/O2 conforme
`PLAN.md`; evidência (grep de verificação) em `STATE.md`. CI (`CI` + `Pylint`) verde no
commit de fechamento (runs 30182148336/30182148370).

## Achado — 2026-07-25 (ciclo P, markdownlint no README.md) — FECHADO

Evidência: Orquestrador (`npx markdownlint-cli2@0.23.1 README.md` em cópia de scratchpad,
comparado contra `mcp__ide__getDiagnostics` do VS Code — mesmos 112 avisos, mesma
distribuição por regra). Testado `--fix` numa cópia isolada antes de propor qualquer
mudança real no repo.

| ID | categoria | onde | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|------|------------------------|------------|--------------------|
| P-a | débito de lint markdown pré-existente | `README.md` inteiro | 112 avisos `markdownlint`, nunca lintado antes | S4 | esperado: 0; medido: 112 (88 MD060, 11 MD033, 5 MD040, 3 MD032, 2 MD036, 1 cada MD041/MD045/MD034) |

- **P-a:** distribuição por regra — `MD060` (separador de tabela `|---|` vs células
  espaçadas, 88), `MD033` (div/p/img de centralização do banner/badges/capturas, 11),
  `MD040` (5 blocos ```` ``` ```` de diagrama ASCII sem linguagem), `MD032` (3 listas sem
  linha em branco ao redor), `MD036` (2 — nome do autor e tagline final usados como
  ênfase, não heading), `MD041` (README abre com `<div>` do banner, não `# H1`), `MD045`
  (banner sem `alt=`), `MD034` (e-mail solto sem `<>`). 92 dos 112 (`MD060`+`MD032`+`MD034`)
  são auto-fixáveis via `markdownlint-cli2 --fix`, verificado sem alterar conteúdo/render —
  só normaliza espaçamento de pipe de tabela, adiciona linha em branco antes/depois de
  lista, e envolve o e-mail solto em `<>` (autolink, GitHub renderiza como `mailto:`).
  Os 20 restantes (`MD033`×11, `MD036`×2, `MD041`×1) são convenções deliberadas de README
  no GitHub — HTML bruto pra centralizar (não existe alternativa em markdown puro) e
  ênfase que não é heading (viraria heading no TOC do GitHub, poluindo o índice). Decisão:
  não reescrever esse markup — suprimir essas 3 regras via `.markdownlint.jsonc` na raiz
  do repo (mesmo padrão do `per-file-ignores` do ruff: regra desligada com comentário de
  1 linha explicando por quê, não removida às cegas). Os 2 restantes (`MD040`×5, `MD045`×1)
  são conteúdo real faltando — `text` como linguagem dos fences ASCII e `alt=` no banner —
  corrigidos diretamente, sem exceção.

**Fechado:** `.markdownlint.jsonc` criado na raiz (config acima). `README.md` com os 92
fixes automáticos (`markdownlint-cli2 --fix`) + os 6 manuais (`alt=` no banner, `text` nos
5 fences ASCII). Verificado de forma independente pelo Orquestrador, fora do que o
executor reportou: `mcp__ide__getDiagnostics` em `README.md` retorna `diagnostics: []`, e
`npx markdownlint-cli2@0.23.1 README.md` na raiz do repo real confirma 0 avisos. 43 linhas
alteradas em `README.md` (`git diff --stat`), todas cosmética/conteúdo real — nenhuma
mudança de estrutura ou semântica. Achado extra corrigido no próprio `PLAN.md` durante a
redação (não no README): uma célula de tabela do plano tinha `|` literal dentro de crases
sem escapar, quebrando a contagem de colunas (`MD056`, 5 esperadas vs 9 lidas) — reescrita
sem pipes soltos.

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
