<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AQ: eliminar o warning de Node 20 nos workflows de CI (fecha AQF1)

Data: 2026-09-03 | Ciclo: AQ | Origem: auditoria a pedido do usuário sobre os workflows de CI/CD, não de achado pré-existente em `FINDINGS.md`. Registrado como `AQF1` neste ciclo.

## Diagnóstico

Runs mais recentes de cada workflow (`33768491188` em `ci.yml`, `33768491217` em
`pylint.yml`), ambos verdes, `91 Passed, 0 Failed` no Pester. **Sem problema
funcional.** O achado é puramente de warning, mas com prazo real.

`##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are
being forced to run on Node.js 24` aparece em 9 jobs, com culpados diferentes por job:

| job | actions citadas |
|---|---|
| `Lint (ruff)` | `actions/checkout@v4`, `actions/setup-python@v5` |
| `Tests` (4 pernas) | `actions/cache@v4`, `actions/checkout@v4`, `actions/setup-python@v5` |
| `Pester` (2 pernas) | `actions/checkout@v4` |
| `Pylint` (2 pernas, workflow separado) | `actions/checkout@v4`, `actions/setup-python@v3` |

Três actions, duas delas (`checkout`, `cache`) idênticas nos dois workflows; a terceira
(`setup-python`) já estava inconsistente entre os dois — `v5` em `ci.yml`, `v3` em
`pylint.yml`. Investigado via `git log --follow -p`: `pylint.yml` foi criado em
2026-06-04 com `@v3` (`13a82bd`) e nunca mais foi tocado nessa linha, nem quando `ci.yml`
foi ajustado para `@v5` depois. Não é decisão técnica registrada — é arquivo esquecido.

**Não é urgência de hoje.** O runner já força Node 24 para essas actions desde
2026-06-02 (rollout gradual do GitHub), e o shim de compatibilidade está funcionando —
é exatamente esse fallback que o warning descreve, e passa limpo em todo job. O que muda
em 2026-09-16 (a força-padrão completa, remoção do Node 20 do runner) não é o
comportamento de execução — já é Node 24 forçado agora — é que a válvula de escape
(`ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true`, vetada por instrução explícita do
usuário) deixa de existir. Hoje há rede de segurança se o shim falhar; em ~13 dias, não
há.

### Versões-alvo — a primeira major com Node 24, não a mais nova

Verificado via changelog/release notes de cada projeto (não por "parecer antiga"):

| action | hoje | alvo | por que essa major e não a mais nova |
|---|---|---|---|
| `actions/checkout` | `v4` | `v5` | primeira com Node 24. `v6` muda onde credenciais são persistidas (separa em arquivo próprio); `v7` bloqueia checkout de fork PR em `pull_request_target`/`workflow_run` — nenhum dos dois gatilhos é usado neste repo (`ci.yml` só tem `push`/`pull_request`), então `v6`/`v7` seriam mudança de comportamento sem necessidade |
| `actions/setup-python` | `v5` (`ci.yml`) / `v3` (`pylint.yml`) | `v6` | primeira com Node 24. Único requisito é runner ≥2.327.1 — já satisfeito, os runners já rodam Node 24 hoje. `v7` remove o input `pip-install`, que nenhum dos dois workflows usa — não muda nada aqui, mas não há razão para ir além do necessário |
| `actions/cache` | `v4` | `v5` | primeira com Node 24, confirmada por múltiplas fontes da comunidade |

`setup-python@v3→v6` em `pylint.yml` é o item de menor confiança direta (salto de 3
majors, sem changelog verificado passo a passo), mas converge para a **mesma** versão que
`ci.yml` já roda com sucesso hoje — reduz inconsistência em vez de introduzir risco novo.
`pylint.yml` só usa o input `python-version`, sem `cache:` nem qualquer input que tenha
mudado nesse intervalo.

## Desenho

Bump de string de versão, 8 linhas, dois arquivos. Nenhum input, step, trigger, matriz
ou job muda.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AQ1 | Em `ci.yml`: `actions/checkout@v4` → `@v5` (linhas 14, 37, 72), `actions/setup-python@v5` → `@v6` (linhas 17, 40), `actions/cache@v4` → `@v5` (linha 45). Em `pylint.yml`: `actions/checkout@v4` → `@v5` (linha 13), `actions/setup-python@v3` → `@v6` (linha 15). Só as 8 linhas de versão. | executor | `.github/workflows/ci.yml`, `.github/workflows/pylint.yml` | `git diff --stat` mostra 2 arquivos, 8 linhas trocadas |
| AQ2 | Validar sintaxe YAML dos dois arquivos (`python -c "import yaml; yaml.safe_load(open(...))"` ou equivalente) antes de commitar. Rodar a suíte Python completa localmente para confirmar baseline antes do CI. | executor | — | YAML parseia sem erro; `461 passed` |
| AQ3 | Fechar o ciclo com CI real verde, confirmando especificamente: (a) o warning `##[warning]Node.js 20 is deprecated` não aparece mais em nenhum job dos dois workflows; (b) `Tests Passed: 91` mantido nas duas pernas do Pester; (c) suíte Python sem regressão nas quatro pernas. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI, checado nome a nome, não por cor agregada |

## Critério de aceite decisivo — ausência do warning, não a cor

Mesma disciplina dos Ciclos AN/AO/AP: CI verde não é a prova. Os dois workflows já
estavam verdes com o warning presente. A prova é a **ausência** da linha
`##[warning]Node.js 20 is deprecated` no log de `Complete job` de cada um dos 9 jobs
(7 de `ci.yml` + 2 de `pylint.yml`). Um job que ficar verde mas ainda imprimir o warning
significa que alguma action não foi de fato re-pinada, ou que uma quarta action
Node20-alvo não apareceu nesta auditoria.

## Critérios de aceite

- `ci.yml` e `pylint.yml` mudam em **exatamente 8 linhas no total** — só a string de
  versão de cada `uses:`. Nenhum input, `with:`, trigger, matriz, ou step novo.
- Nenhum `.py`, `.ps1`, ou arquivo de teste alterado. Este ciclo não toca em código.
- Pester: **91/91**, nas duas pernas, mantendo o pin `-RequiredVersion 5.7.1` intacto
  (fechado no Ciclo AP — este ciclo não mexe nisso).
- Suíte Python: `461 passed`, sem regressão.
- Warning de Node 20 ausente nos 9 jobs — verificado nome a nome no log, não por
  contagem agregada nem pela cor do run.
- `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` não aparece em nenhum arquivo do repo, antes
  nem depois do ciclo.

## Notas de execução

- Não escolher a versão mais nova de cada action "já que estamos mexendo". O alvo é a
  primeira major com Node 24 — instrução explícita do usuário contra upgrade além do
  necessário.
- Não tocar em `launcher.ps1`, nos arquivos de teste Pester, na versão do Pester, na
  matriz Python 3.11/3.12, na matriz Ubuntu+Windows, no pin do ruff, no passo de
  validação de `requirements.txt`, ou na lógica de chave de cache.
- Nunca usar `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` como solução, mesmo
  temporariamente durante depuração — vetado por instrução explícita do usuário.
- **Nunca usar `git add -A` nem `git add .`** — o repositório tem arquivos não
  rastreados (`961576A_Hollywood_2Pass.qc.html`, `961576A_Hollywood_2Pass.qc.json`,
  `docs/fila-interrupcao.md`, `docs/launcher-portavel-reels-encoder.md`,
  `docs/windows-ci-e-interrupcao-robusta.md`, `videos/`) que não pertencem a ciclo
  nenhum. Adicionar por caminho explícito.
- Não fechar o ciclo com base em execução local. A prova é log real do CI, e
  especificamente a ausência do warning nome a nome.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
