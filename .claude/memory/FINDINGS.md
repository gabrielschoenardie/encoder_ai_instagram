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

## Achado — 2026-08-14 (ciclo Q, launcher.ps1 — validação de integração)

Evidência: executor-pesado (execução real de ponta a ponta, Steps 0-7 do plano `docs/superpowers/plans/2026-08-13-launcher-portavel.md` § Task 9; saídas brutas em `STATE.md` § "Ciclo Q"). Veredito: Orquestrador. Nenhum dos dois itens abaixo foi corrigido — Task 9 é validação, não correção; fora do escopo do plano atual.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| QF1 | robustez de erro | launcher.ps1 (bloco `try`/`catch` em torno do `pip install`, linha ~286) | `$ErrorActionPreference="Stop"` + saída de comando nativo fundida (`*>&1`) transforma `[notice]` do pip em `NativeCommandError` de mensagem vazia | S3 | esperado: erro só se pip falhar de verdade; medido: qualquer chamador que funde streams (CI, wrapper) dispara catch mesmo com pip OK, e o catch estoura de novo porque `$_.Exception.Message` vazio viola `[Parameter(Mandatory)][string]$Message` de `Write-LauncherLog` |
| QF2 | isolamento portátil incompleto | launcher.ps1 (`-SkipValidation`) + `tools/fetch_ffmpeg.ps1` (instala via winget, global) | `-SkipValidation` não é observável ponta-a-ponta: o próprio `fetch_ffmpeg.ps1` do Task 2 do fluxo de validação deixa `ffmpeg` no `PATH` global, então pular a validação do `./bin/ffmpeg.exe` local não produz erro — o encoder acha o binário global de qualquer forma | S4 | esperado (spec "Falhas tratadas"): validação pulada expõe erro de dentro do encoder se FFmpeg realmente ausente; medido: encode roda normal (exit 0) porque há FFmpeg no PATH global; não reproduzido nesta máquina só renomeando o binário local |

### Status

| ID | status | onde |
|----|--------|------|
| QF2 | esclarecido — sem mudança de comportamento | ciclo R (R1a/R1b, comentários em `launcher.ps1` linhas ~12 e ~267) |
| QF1 | corrigido — ciclo T | ciclo T (T1a/T1b/T1c escopam `$ErrorActionPreference = "Continue"` só ao redor de cada chamada nativa em `New-ProjectVenv`/`Install-Requirements`/`Write-VenvLock`, restaurando em `finally`; T2a/T2b confirmam que o repro sintético sobrevive agora em Windows PowerShell 5.1 e pwsh 7.5.1; T2c confirma `pip install` real via `Install-Requirements` sob 5.1 com `*>&1` — ver `STATE.md` § "Ciclo T") |

### Contexto

- **QF1:** não afeta o uso normal (duplo-clique ou shell interativo, sem fusão de streams) — só chamadores que capturam `*>&1` (ex.: CI, harness de automação, ou `Tee-Object` como o usado para provar o Step 3 da Task 9). Resultado observado: stack trace do PowerShell no lugar de uma mensagem útil, **depois** de o setup já ter dado certo (falso negativo de falha).
- **QF2:** não é um bug do `launcher.ps1` isoladamente — é uma interação entre dois scripts do próprio plano (`fetch_ffmpeg.ps1` deixa FFmpeg global; `-SkipValidation` só teria efeito visível numa máquina sem FFmpeg em lugar nenhum do PATH). Se o objetivo for isolamento portátil estrito, vale considerar preferir `./bin/ffmpeg.exe` mesmo quando há uma cópia global no PATH.

## Achado — 2026-08-15 (ciclo U, infra/CI — não é bug do `launcher.ps1`)

Evidência: executor-pesado (Task 6 do plano `docs/superpowers/plans/2026-08-14-pester-launcher.md`; saídas brutas em `STATE.md` § "Ciclo U", evidência U6-b). Achado **bloqueia a U6**: sem run de `CI`, não existe a evidência dos dois legs que a task pede.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| UF1 | cobertura de gatilho de CI | `.github/workflows/ci.yml:4-7` | Filtro `branches:` do `push` não cobre branches de worktree; job `pester` nunca roda nelas | S3 | esperado: push de branch de trabalho dispara `CI` (lint + tests + pester); medido: `worktree-pester-launcher` não casa com `main`/`claude/**`/`feature/**` → zero run de `CI`; só o `Pylint` (`on: [push]`, sem filtro) rodou |
| UF2 | cobertura de motor no CI | `.github/workflows/ci.yml` (job `pester`, `shell: pwsh` nos dois legs) | Nenhum leg roda Windows PowerShell 5.1 — o motor de produção do launcher e o único onde `QF1` reproduzia | S3 | esperado: matriz cobre o motor real do usuário final; medido: os dois legs rodam pwsh 7.6.4 Core (`C:\Program Files\PowerShell\7\pwsh.EXE` no leg Windows); o que varia é o SO, não o motor |
| UF3 | versão de dependência não fixada no CI | `.github/workflows/ci.yml` (job `pester`, `Install-Module`/`Import-Module -MinimumVersion 5.5.0`) | `-MinimumVersion` sem teto: o CI segue silenciosamente o major mais novo do Pester disponível no runner | S4 | esperado: versão de Pester determinística entre runs; medido: runners têm 6.1.0 e 5.9.0, a suíte rodou sob a 6.x (banner `Running tests from 2 files.` vs `Starting discovery in 2 files.` da 5.7.1 local) — passou, mas por acaso, não por escolha |

### Contexto

- **UF1 (S3):** não é regressão do ciclo U — o filtro é anterior e nunca foi problema porque
  os ciclos passados trabalharam em `main` ou em branches `claude/**` (ex.: PR #38). O ciclo U
  é o primeiro a rodar num worktree isolado nativo, cuja convenção de nome (`worktree-*`) fica
  fora do filtro. O efeito colateral é maior agora: o job `pester` criado em U5 só existe no
  `ci.yml`, então **nenhum** teste do launcher roda em branch de worktree, e o `Pylint` verde
  dá falsa sensação de "CI passou".
- Não corrigido neste ciclo: `ci.yml` está fora da lista de arquivos da U6, e mudar gatilho de
  CI é decisão de escopo do Orquestrador. As três saídas possíveis (PR para `main`, push para
  nome que case com o filtro, ou alterar o filtro/adicionar `workflow_dispatch`) estão
  descritas no fim de `STATE.md` § "Ciclo U".
- Também vale avaliar, no mesmo item futuro, se `pull_request: branches: [main]` deve ganhar
  `workflow_dispatch` — hoje não há como forçar um run de `CI` pelo `gh` sem abrir PR.
- **Contornado na própria U6, não corrigido.** Ruling do humano: abrir o PR #39
  (`worktree-pester-launcher` → `main`, sem merge) só para acionar o gatilho
  `on.pull_request`. Funcionou — run `31921343582`, `CI` verde nos 5 jobs. O veredito do
  achado não muda: continua sendo defeito de infra do `ci.yml`, não do `launcher.ps1`, e o
  arquivo **não** foi editado. Efeito colateral a não esquecer: o PR #39 fica aberto como
  instrumento de diagnóstico e não deve ser mergeado por engano.
- **UF2 (S3):** o `windows-latest` do GitHub Actions só oferece pwsh 7 como `shell: pwsh`;
  cobrir 5.1 exigiria um passo com `shell: powershell` (que existe nesse runner). Enquanto
  isso não for feito, a única evidência de que a suíte passa em Windows PowerShell 5.1 é
  local (máquina do usuário, Tasks 1-4 — ver `STATE.md` § "Ciclo U", evidências U6-c e
  U6-k). Como o `QF1` só reproduzia em 5.1, essa é a lacuna de cobertura mais relevante que
  sobrou do ciclo: uma regressão específica de 5.1 passaria verde no CI hoje.
- **UF3 (S4):** os dois achados anteriores (`UF1`, `UF2`) e este são a mesma família — o job
  `pester` funciona, mas depende do que o runner traz por acaso. Não é um impedimento para
  corrigir o `UF2`: `Find-Module Pester -MinimumVersion 6.0.0` reporta
  `PowerShellVersion required: 5.1` para a 6.1.0, ou seja, a 6.x declara suporte a Windows
  PowerShell 5.1 (verificado, não presumido — a suposição inicial de que a 6 exigiria pwsh 7
  estava errada). O risco do `UF3` é só de determinismo: a suíte foi escrita e validada
  localmente sob 5.7.1 e roda no CI sob a 6.x sem ninguém ter decidido isso, então uma
  quebra futura de compatibilidade do Pester chegaria como falha surpresa num run que não
  mudou nada do repo. Fixar com `-MaximumVersion` ou `-RequiredVersion` resolve.

## Achado — 2026-08-16 (ciclo V, regressão da fila de render) — CORRIGIDO no ciclo W

Evidência: usuário reportou com captura de tela real (barra "MCTF masks" piscando linha a
linha durante `--batch` real com `--mctf on --enhance-ai on`). Orquestrador confirmou a
causa via leitura direta de `enhance_visualizer.py:488-496` e do call site em
`Reels_Encoder_v2_FINAL.py:3933-3947`.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| VF1 | regressão introduzida pelo Ciclo V | `enhance_visualizer.py:489` (`Progress(...)` sem `console=`) vs `Reels_Encoder_v2_FINAL.py` (novo `Live(tabela)` do `--batch`) | Dois displays `rich` ao vivo simultâneos (console global do MCTF + `console` da fila) brigam pela mesma região do terminal | S3 | esperado: um único display ao vivo por vez durante o batch; medido: barra "MCTF masks" pisca a cada frame, sobreposta à tabela da fila |

- **VF1 (S3):** só ocorre com `--mctf on` **e** `--enhance-ai on` explícitos (default de
  `--mctf` é `off`) — batch padrão não é afetado. Antes do Ciclo V não havia conflito porque
  nada mais desenhava no terminal durante o loop `--batch`; a fila nova (`with Live(...) as
  live:`, `Reels_Encoder_v2_FINAL.py`) introduziu o segundo display concorrente.
  `generate_mctf_mask_video()` usa `Progress(...)` sem `console=` explícito, então cai no
  console global singleton do Rich (`rich.get_console()`), diferente do `console` que a fila
  usa — por isso não colide com erro (`LiveError`), só visualmente. Mesmo padrão já usado
  para suprimir o medidor EBU em batch (`_show_meter = ... and not is_batch`,
  `Reels_Encoder_v2_FINAL.py:4011`) resolve: `show_progress: bool` novo em
  `generate_mctf_mask_video`, `Progress(..., disable=not show_progress)`, repassado como
  `show_progress=not is_batch` no call site.

**Corrigido (ciclo W, commits `6d86eb6` + `035c53d`):** `show_progress: bool = True`
adicionado à assinatura de `generate_mctf_mask_video`; `Progress(..., disable=not
show_progress)`; call site passa `show_progress=not is_batch`. Smoke test real com
`--batch --mctf on --enhance-ai on` confirmou 0 ocorrências de "MCTF masks" na saída,
máscaras geradas de verdade (`mctf_deband_mask.mp4` 211290216 bytes,
`mctf_sharpen_mask.mp4` 513079464 bytes — `disable=True` só desliga o desenho, não a
lógica), fila terminou `✓ Sucesso: 1/1` sem flicker, zero regressão na suíte.

## Achado — 2026-08-16 (ciclo W, gap de UX descoberto ao corrigir VF1) — corrigindo no ciclo X

Evidência: usuário testou o fix do VF1 no terminal real e reportou que o `--batch` "parece
travado" durante um job — sem crash, sem erro, só sem nenhum sinal visual de progresso.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| VF2 | gap de UX no design original do Ciclo V | `render_queue.py` (`run_job`, `build_table`) | Nenhum sinal de progresso durante um job em andamento; tabela só atualiza em transição de status | S3 | esperado: usuário distingue "rodando" de "travado" durante um job longo; medido: coluna Duração mostra `—` estático do início ao fim do job, nenhuma atualização entre "processando" e "ok"/"falha" |

- **VF2:** consequência direta do design original do spec do Ciclo V (`docs/superpowers/specs/2026-08-16-render-queue-design.md` § "Por que capturar output em vez de deixá-lo rolar"): capturar e esconder TODO output por-job durante o batch, incluindo qualquer indicador de progresso legítimo. Antes do ciclo W, a barra do MCTF (que não passava pela nossa captura, por usar o console global do Rich — ver `VF1`) era, sem querer, o único sinal de vida visível durante um job. Ao corrigir `VF1` (suprimir a barra do MCTF em batch), esse sinal acidental desapareceu, expondo o gap real: `run_job` bloqueia o loop principal por toda a duração do encode, e `Live` só repinta o que foi explicitamente mandado via `.update()` — sem chamadas novas durante o job, a tabela fica congelada. Fix: `run_job` roda o encode numa thread em background e chama um callback `on_tick` a cada ~250ms; `build_table` calcula a duração ao vivo (`time.time() - job.started_at`) para o job em "processando", dando um cronômetro que incrementa visivelmente. Ver `.claude/memory/PLAN.md` § Ciclo X.

## Achado — 2026-08-17 (ciclo X, auditoria pós-fila) — corrigindo no ciclo Y

Evidência: leitura direta de `Reels_Encoder_v2_FINAL.py:4367-4383` e `render_queue.py:124-129`; comparação com o handler single-file em `:4411-4424`.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| XF1 | perda de integridade de entrega | `Reels_Encoder_v2_FINAL.py:4378-4383` | Ctrl+C no batch não remove o output parcial; skip posterior trata o truncado como pronto | S2 | esperado: arquivo parcial removido e refeito na próxima execução; medido: `.mp4` truncado permanece e vira `○ pulado` |
| XF2 | perda de diagnóstico | `render_queue.py:124-129` | `job.log` só é preenchido em falha; saída de job bem-sucedido com avisos é descartada | S3 | esperado: avisos recuperáveis após a fila; medido: buffer capturado descartado no retorno de `run_job` |
| XF3 | UX incorreta | `Reels_Encoder_v2_FINAL.py:4364` | `remaining` conta só `aguardando`; job em execução fica fora do ETA | S4 | esperado: ETA > 0 enquanto há encode rodando; medido: `ETA: 00:00` durante todo o último job |

- **XF1:** O caminho single-file protege o usuário desde o PR #22 (`:4411-4424`: snapshot de pré-existência, `os.remove` guardado, saída 130). O caminho de batch nunca ganhou equivalente — em `:4380-4383` ele apenas para o `Live`, imprime um aviso e sai com 1. Como o loop pula qualquer job cujo output já exista (`:4368`), o arquivo truncado é promovido a "pronto" na execução seguinte. O risco prático é entregar vídeo cortado. Correção no `.claude/memory/PLAN.md` § Ciclo Y.
- **XF2:** `run_job` captura stdout do job na worker thread (`render_queue.py:109-114`) mas só transfere para `job.log` dentro do ramo de falha (`:127`). Antes do Ciclo V essa saída rolava visível no terminal; agora some. Não há `--verbose` nem log em arquivo para recuperar.
- **XF3:** O bug é inteiramente do chamador. `estimate_eta` multiplica a média pelo `remaining` que recebe, e o engine passa apenas a contagem de `aguardando` — o job `processando` fica de fora. No último job, `remaining == 0` e o título exibe `ETA: 00:00` durante o encode inteiro.

## Achado — 2026-08-17 (ciclo Y, smoke test real da Task 5) — não corrigido

Evidência: execução real do `--batch` interrompida dentro da janela de escrita do ffmpeg; saída completa colada em `.claude/memory/STATE.md` § "Ciclo Y — interrupção segura, log e ETA — 2026-08-17" § "Achado novo — YF1".

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| YF1 | perda de integridade de entrega (residual do XF1) | `render_queue.py:51-64`, `Reels_Encoder_v2_FINAL.py:4393-4406` | No Windows o ffmpeg órfão segura o arquivo; remoção falha em silêncio e o parcial vira `○ pulado` | S2 | esperado: parcial removido e job refeito; medido: parcial de 1310768 bytes sobreviveu e virou `○ pulado` na execução seguinte |

- **YF1:** o fix do `XF1` cobre o caso comum (interrupção antes de o ffmpeg criar a saída) — provado no smoke test da Task 5: `exit=130`, `⚡ Interrompidos: 1/3`, job interrompido refeito na execução seguinte. Resta uma janela: quando a interrupção cai **enquanto o ffmpeg escreve** o `.mp4` (medido: t≈113 s a t≈135 s de um job de ~140 s), o `os.remove` de `discard_partial_output` falha com `OSError` porque o subprocesso ffmpeg — que o handler não encerra — ainda mantém o arquivo aberto. O `except OSError: return False` engole o erro, nada é impresso, e a linha `● output parcial removido:` nunca aparece. Pior: o ffmpeg órfão sobrevive à saída do Python e termina de escrever sozinho, deixando um `.mp4` de tamanho "normal" que nunca passou pelo pós-encode (remux do átomo `colr`, `.qc.json`/`.qc.html`) — e que a execução seguinte marca `○ pulado`, exatamente o sintoma que o `XF1` queria eliminar.
- Correção provável (fora do escopo do Ciclo Y): guardar o `Popen` do ffmpeg do job e chamar `terminate()`/`kill()` no handler de `KeyboardInterrupt` antes de tentar remover, e/ou tornar a falha de remoção visível em vez de silenciosa (avisar que o arquivo pode estar truncado). O `except OSError: return False` foi decisão deliberada do Ciclo Y ("nunca levanta") e continua correta — falta o `terminate()` e o aviso.
- O caminho single-file (`Reels_Encoder_v2_FINAL.py:4435-4447`) tem a mesma estrutura (`os.remove` guardado por `except OSError: pass`) e provavelmente a mesma janela; não medido nesta task.

## Achado — 2026-08-18 (ciclo AB, auditoria de cobertura de CI) — corrigindo no ciclo AC

Evidência: leitura de `.github/workflows/ci.yml`; comparação entre o comando do job `tests` e a localização real dos arquivos de teste; contraste entre a suíte verde em Linux (`392 passed`) e a nota do `STATE.md` § AB7 ("4 falhas nominais pré-existentes"), registrada em execução Windows. Confirmação adicional nesta máquina Windows: execução real local do repositório produziu `4 failed, 388 passed` — as 4 falhas: `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| ABF1 | ponto cego de CI | `.github/workflows/ci.yml` (job `tests`) | Nenhum job de Python roda em Windows; 4 falhas conhecidas nunca são observadas | S2 | esperado: suíte verde na plataforma de produção; medido: 4 falhas registradas só à mão, invisíveis ao CI |
| ABF2 | cobertura ausente | `.github/workflows/ci.yml` (job `tests`) | `pytest enhance/ ui/` não alcança `test_render_queue.py`, na raiz | S2 | esperado: 23 testes da fila no CI; medido: zero — nunca executados em plataforma alguma |
| ABF3 | débito de lint | `.github/workflows/ci.yml` (job `lint`) | `ruff check enhance/` deixa engine, `ui/`, `render_queue.py` e `tools/` sem lint | S3 | esperado: lint no repo; medido: 1 de 5 áreas coberta |

- **ABF1:** O produto é distribuído para Windows (`launcher.ps1` é o caminho canônico de entrada desde o Ciclo AA), e o job `pester` já roda em `windows-latest`. O job `tests`, porém, é `runs-on: ubuntu-latest` com matriz só de versão de Python. As 4 falhas de Windows são conhecidas por relato manual e vinham sendo normalizadas como "baseline nominal" — o padrão de fadiga de alarme que o Ciclo Y eliminou em Linux e que segue vivo em Windows. **Os nomes dos 4 testes não estão confirmados**: a lista que circulou veio de uma execução obsoleta. Descobrir a lista real é a Task 3.
- **ABF2:** O job `tests` executa `pytest enhance/ ui/ -v --timeout=60`. O `test_render_queue.py` mora na raiz do repo, fora dos dois diretórios. Consequência: os 23 testes da fila de render — 14 do Ciclo X mais os 9 do Ciclo Y — nunca rodaram no CI. Toda a validação do modo `--batch` depende hoje de execução manual. É o achado mais barato de corrigir e o de maior retorno.
- **ABF3:** Registrado e **adiado deliberadamente**. Alargar o `ruff` para o repo inteiro num arquivo de 4453 linhas que nunca foi lintado produz um volume de erros que exige ciclo próprio; misturá-lo aqui inviabilizaria a revisão do Ciclo AC.
