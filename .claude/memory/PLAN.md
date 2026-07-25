<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Pinar ruff no CI e tornar a seleção de regras explícita (com I001)

Data: 2026-07-25 | Ciclo: infra/CI | Origem: CI vermelho desde 2026-07-25

**Objetivo:** o CI está vermelho por causa de `pip install ruff` sem pin em
`.github/workflows/ci.yml:22`. CI pegou **ruff 0.16.0**, a máquina local roda
**0.14.10**, e o repo não tem nenhuma config de ruff — então o conjunto de regras é o
default de quem for instalado. O `I001` entrou no default do 0.16.0 e expôs débito de
lint pré-existente. Nenhuma linha de Python mudou entre o último CI verde (`27504cc`,
18/07) e o primeiro vermelho.

Pinar sozinho só adia o problema para o próximo bump. A correção real é a config
explícita: **a seleção de regras vira decisão do repo, não default de versão.**

**Escopo fechado (arquivos permitidos):**
- `.github/workflows/ci.yml` — só a linha 22 (`pip install ruff`)
- `pyproject.toml` — só acrescentar a seção `[tool.ruff.lint]` (já existe o arquivo; **não** criar `ruff.toml`)
- Qualquer `.py` do repo — **exclusivamente** o que `ruff check --fix --select I` alterar

**Fora de escopo:** ampliar o escopo do CI (hoje ele checa só `enhance/`; fica assim),
adicionar regras além das listadas em I2, mexer em lógica de qualquer arquivo.
Bug fora do escopo → uma linha em `FINDINGS.md`, sem investigar.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| I1 | Pinar: `pip install ruff` → `pip install ruff==0.14.10`. Essa é a versão da máquina local, logo CI e o hook `PostToolUse` do `settings.json` passam a rodar o mesmo binário. | `executor` | `.github/workflows/ci.yml` | linha 22 com o pin; nenhuma outra linha do arquivo alterada |
| I2 | Acrescentar ao `pyproject.toml`: `[tool.ruff.lint]` com `select = ["E4", "E7", "E9", "F", "I"]`. São os defaults históricos do ruff **mais** o `I` (isort) que o usuário pediu. Nada além disso. | `executor` | `pyproject.toml` | `ruff check enhance/` passa a reportar os erros de `I001` também na 0.14.10 local |
| I3 | Rodar `ruff check . --fix --select I` no repo inteiro (33 erros, todos auto-fixáveis) e verificar que nada quebrou. Ver as três notas abaixo antes de rodar. | `executor-pesado` | vários `.py` | `ruff check . --select I` → `All checks passed!` **e** `python -m pytest enhance/ ui/ -q` → `4 failed, N passed` com as mesmas 4 do baseline |

## Notas de execução

- **Por que o repo inteiro e não só `enhance/` (14 erros).** O CI checa só `enhance/`,
  então bastariam 14. Mas a config do I2 vale repo-wide, e o hook `PostToolUse` do
  `settings.json` roda `ruff check --fix` em **todo** arquivo `.py` editado. Se os
  outros 19 ficarem, o próximo commit que tocar qualquer um desses arquivos vem com
  reordenação de import de carona, poluindo um diff que não tem nada a ver. Melhor
  pagar os 33 de uma vez, num commit que só faz isso.
- **Por que `executor-pesado` no I3.** É refactor multi-arquivo cruzando `enhance/` +
  pipeline — o gatilho literal do CLAUDE.md. E o risco não é nulo: `Reels_Encoder_v2_FINAL.py`
  tem imports condicionais e lazy. O isort do ruff só reordena **blocos contíguos**, e
  código entre imports funciona como barreira, então a probabilidade de quebra é baixa
  — mas se a suíte quebrar, diagnosticar qual reordenação causou exige julgamento.
  Nesse caso, carregue `superpowers:systematic-debugging`; **não** reverta o arquivo
  inteiro às cegas.
- **`--select I` no comando do I3 não é opcional.** Com a config do I2 no lugar,
  `ruff check .` (sem `--select`) reporta **91** erros: os 33 de import sorting mais
  **58 de E4/E7/E9/F pré-existentes**, concentrados em `tools/` (37), `.claude/scripts`
  (7) e `ui/` (6) — nenhum em `enhance/`, que é o único diretório que o CI checa.
  Desses 58, só 17 são auto-fixáveis. Eles **não são deste ciclo**: já estavam lá antes
  da config e o CI nunca os cobrou. Não os toque; estão registrados em `FINDINGS.md`.
  Rodar `--fix` sem `--select I` sairia do escopo e mexeria em 17 arquivos alheios.
- **Ordem obrigatória:** I1 e I2 antes de I3. Rodar o `--fix` antes da config existir
  usa a seleção default e pode tocar o que não deve.
- **Baseline da suíte:** 4 falhas pré-existentes (2 em `enhance/test_ebu_meter.py`,
  2 de encoding de console em `ui/test_readme_assets.py` e `ui/test_theme.py`).
  Qualquer falha **além** dessas 4 é regressão do I3 — nesse caso o item volta
  `blocked` com o teste e o arquivo identificados.
- **Carregue `superpowers:verification-before-completion`** antes de marcar qualquer ID
  como `done` e cole no STATE.md a saída real do comando.
- Retorno: uma linha por ID. Detalhe no STATE.md.

## Nota sobre bumps futuros (não é tarefa — é a consequência do desenho)

Com o pin + `select` explícito, subir o ruff vira um ato deliberado de três passos:
trocar a versão no `ci.yml`, rodar `ruff check . --fix`, commitar. Uma release nova
do ruff não pode mais mudar o que o CI cobra sem alguém decidir.
