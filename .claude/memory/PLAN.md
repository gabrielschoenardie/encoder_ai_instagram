<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AO: estender o gate de lint ao repo (fecha AJF4, ABF3, I-a)

Data: 2026-09-03 | Ciclo: AO | Origem: `.claude/memory/FINDINGS.md` § `I-a` (Ciclo I), § `ABF3` (Ciclo AB), § `AJF4` (Ciclo AJ) — três registros do mesmo gap, adiados desde 2026-07-25.

## Diagnóstico

`.github/workflows/ci.yml:25` roda `ruff check enhance/ --output-format=github`. `ui/`,
`tools/`, os módulos da raiz e `.claude/skills/.../scripts/` nunca passam por lint
automatizado. O CI não pode pegar regressão de lint fora de `enhance/`.

### O débito de 58 violações não existe mais — medido, não presumido

Os três achados descrevem o mesmo gap, mas o `I-a` acrescenta um número que virou a razão
para adiar: "58 erros E4/E7/E9/F fora de `enhance/`; só 17 auto-fixáveis". Esse número é de
2026-07-25 e **está obsoleto**. Medição de hoje, `ruff 0.14.10`, mesmo `select` do
`pyproject.toml` (`E4`, `E7`, `E9`, `F`, `I`):

| área | violações |
|---|---|
| `enhance/` | 0 |
| `ui/` | 0 |
| `tools/` | 0 |
| raiz (`.py` rastreados) | 0 |
| `.claude/skills/.../scripts/` | 0 |
| **`ruff check .` (repo inteiro, 72 arquivos)** | **0** |

O débito foi pago em algum ciclo entre julho e hoje sem que nenhum dos três achados fosse
atualizado — mesmo padrão de `XF2`, `XF3` e `AJF1`, reconciliados no Ciclo AN. Não há
triagem a fazer. **Este ciclo é uma linha de configuração, não um ciclo de decisão.**

Os `per-file-ignores` do `pyproject.toml` mascaram 15 erros. Verificado que os quatro são
legítimos e já documentados com comentário no próprio arquivo (imports de probe dentro de
`try/except ImportError`, `import version` que é o próprio smoke-check, `E402` depois de
`sys.path.insert`). Não mexer neles.

### A lacuna é real hoje — medida por injeção

Injetando `import os, sys` + `x=1;y=2` em um arquivo de cada área nova, revertendo em
seguida:

| arquivo | `ruff check enhance/` | `ruff check .` |
|---|---|---|
| `ui/probe.py` | passa (cego) | 4 erros |
| `tools/verificador_instalacao.py` | passa (cego) | 2 erros |
| `ebu_meter.py` (raiz) | passa (cego) | 4 erros |
| `.claude/skills/.../analyze_source.py` | passa (cego) | 4 erros |

### Determinismo já resolvido

O ruff **já está pinado** no CI (`ci.yml:22`, `pip install ruff==0.14.10`), a mesma versão
usada nesta medição. Não há aqui o risco de versão flutuante do `UF3` (Pester com
`-MinimumVersion` sem teto), e a medição local é fiel ao que o CI vai fazer. Nada a mudar
nesse ponto.

## Desenho

Trocar o alvo por `.` em vez de listar diretórios: `ruff check .` respeita o `.gitignore`
(verificado — `venv/` e `audit_tmp/` ficam fora, 0 arquivos deles na lista) e passa a
cobrir automaticamente qualquer diretório novo. Listar diretórios à mão recria a mesma
classe de defeito — uma lista que envelhece em silêncio, que é exatamente o que o `AJF1`
denunciou quando `tools/` ficou fora do alvo do pytest.

**Decisão: `ruff check . --output-format=github`.**

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AO1 | Trocar `ruff check enhance/` por `ruff check .` em `.github/workflows/ci.yml:25`, mantendo `--output-format=github`. Uma linha. Não tocar no step de install nem no pin de versão. | executor | `.github/workflows/ci.yml` | `git diff --stat` mostra 1 arquivo, 1 linha |
| AO2 | Matriz de mutação do gate: para cada uma das 4 áreas novas, injetar uma violação, rodar `ruff check enhance/` **e** `ruff check .`, registrar que a primeira passa e a segunda falha, **reverter**. Colar a tabela medida em `STATE.md`. | executor | `.claude/memory/STATE.md` | 4/4 áreas com `enhance/` cego e `.` pegando; `git status --porcelain -- '*.py'` vazio ao fim |
| AO3 | Fechar `I-a`, `ABF3` e `AJF4` com CI real verde; registrar que o débito de 58 do `I-a` já não existia. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI |

## Por que o AO2 existe

Trocar a linha e ver o CI verde **não prova nada**: o CI já estava verde antes, com o
alvo estreito. Um gate que não gateia é indistinguível de um gate que funciona enquanto o
código está limpo — e o código está limpo hoje. A prova de que a mudança fecha o gap é a
injeção: `enhance/` cego e `.` pegando, nas quatro áreas. É a mesma disciplina dos Ciclos
AM e AN, e a razão de não aceitar "CI verde" como evidência de cobertura nova.

## Critérios de aceite

- `.github/workflows/ci.yml` muda em **exatamente uma linha**. Sem tocar no pin do ruff,
  no `output-format`, nos outros jobs, ou no `pyproject.toml`.
- Nenhuma alteração em `.py` de produto ou de teste. Este ciclo não paga débito de lint —
  não há débito a pagar. Se aparecer violação, ela é regressão de outro ciclo e vira
  achado novo, não conserto aqui.
- Os `per-file-ignores` do `pyproject.toml` ficam intactos.
- `git status --porcelain -- '*.py'` vazio ao fim do AO2 — nenhuma violação injetada
  sobrevive.
- Suíte completa: `461 passed`, sem regressão (este ciclo não toca em código, então
  qualquer mudança na contagem é sinal de erro).
- CI real verde nos 7 jobs, com o job `Lint (ruff)` rodando o alvo novo.

## Notas de execução

- **Reverter cada injeção do AO2 antes da próxima.** Use `cp` para backup e restauração,
  ou `git checkout --` no arquivo. Conferir `git status --porcelain -- '*.py'` vazio ao
  final.
- Não adicionar `ruff format`, `--fix`, regras novas ao `select`, ou qualquer outro
  linter. O escopo é o alvo do comando, nada mais.
- Não fechar o ciclo com base em execução local. A prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
