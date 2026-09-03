<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AR: normalizar EOL de `cineon_pipeline.py` e `enhance_visualizer.py` para LF (fecha AKF1)

Data: 2026-09-03 | Ciclo: AR | Origem: `.claude/memory/FINDINGS.md` § `AKF1` (Ciclo AK, 2026-08-25), aberto desde então.

## Diagnóstico

Remedido hoje, não presumido do achado — mesma disciplina que corrigiu o `I-a` no Ciclo
AO. Os números do `AKF1` seguem válidos (com uma diferença de tamanho esperada, ver
abaixo):

| arquivo | blob | worktree | tamanho hoje |
|---|---|---|---|
| `cineon_pipeline.py` | CRLF | CRLF | 43588 bytes (era 43548 no achado — diferença de 40 bytes bate com a linha do fix do Ciclo AN, `cineon_pipeline.py:810`, que alongou uma linha) |
| `enhance_visualizer.py` | CRLF | CRLF | 22785 bytes, inalterado |

Confirmado: **nenhum outro `.py` rastreado no repo tem CRLF** — varredura em todos os
arquivos de `git ls-files '*.py'` exceto os dois. Os dois entraram no repo já em CRLF, no
commit inicial `ce992c3` ("Add files via upload"), e nunca foram tocados por uma
normalização — não é regressão de ciclo nenhum.

**Diferente dos `.cube` do próprio Ciclo AK, aqui não há razão técnica para CRLF.** O
`.gitattributes` atual já documenta a exceção deliberada dos `.cube` (`*.cube -text`,
comentário citando o gerador). Para `.py`, Python não distingue CRLF de LF na execução —
não há motivo funcional, e o resto do repo já convencionou LF.

### Seguro renormalizar — verificado byte a byte

Contei todo byte `\r` (`0x0D`) contra todo par `\r\n` nos dois arquivos: idênticos nos
dois (`1097`/`1097` em `cineon_pipeline.py`, `580`/`580` em `enhance_visualizer.py`). Não
há `\r` solto nem `\r\n` como literal de string dentro de uma linha — todo `\r` é
terminador de linha. Renormalizar para LF é conversão pura de quebra de linha, sem efeito
semântico no código.

Confirmado também: o `ruff` (estendido ao repo inteiro no Ciclo AO) não tem regra sensível
a EOL no `select` (`E4`, `E7`, `E9`, `F`, `I`) — a mudança não interage com o gate de lint.

## Desenho

**Decisão: normalizar os dois arquivos para LF, e fixar via `.gitattributes` para que a
inconsistência não volte.** A alternativa seria pinar CRLF como intencional (o caminho que
o Ciclo AK escolheu para os `.cube`) — mas não há razão técnica para isso aqui, e o
próprio texto do `AKF1` já apontava que "renormalizar para LF" era uma das duas saídas
válidas.

**Regra do `.gitattributes`: `*.py text eol=lf`, não uma entrada por arquivo.** Duas
razões, ambas já aplicadas neste projeto de sessão para sessão:

1. Uma entrada por arquivo protege só os dois arquivos de hoje. Um `.py` novo, editado por
   alguém com `core.autocrlf=true` (que é exatamente a config desta máquina — verificado
   `git config --get core.autocrlf` → `true`), reintroduziria CRLF sem ninguém decidir
   isso — a mesma classe de "lista que envelhece calada" que o `AJF1` denunciou no alvo do
   pytest e que o Ciclo AO evitou ao trocar `ruff check enhance/` por `ruff check .` em vez
   de listar diretório por diretório.
2. `text eol=lf` força LF no checkout **independente** do `core.autocrlf` de quem clona —
   fecha o vetor de recorrência, não só o sintoma atual.

**Renormalização escopada, não repo-wide.** O `AK1` já tentou `git add --renormalize .`
para o repo inteiro e foi revertido por estar fora de escopo — a lição já está registrada
em `FINDINGS.md`. Este ciclo renormaliza só os dois arquivos nomeados no achado:
`git add --renormalize cineon_pipeline.py enhance_visualizer.py`.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AR1 | Acrescentar ao `.gitattributes`: `*.py text eol=lf`, com comentário explicando a decisão (por que LF, por que pattern e não arquivo a arquivo). Não tocar na entrada existente de `*.cube`. | executor | `.gitattributes` | `git diff --stat` mostra 1 arquivo, linha(s) adicionada(s), entrada de `.cube` intacta |
| AR2 | `git add --renormalize cineon_pipeline.py enhance_visualizer.py` **só** nesses dois arquivos — não repo-wide. Confirmar que `git diff -b main..HEAD -- cineon_pipeline.py enhance_visualizer.py` (diff ignorando espaço em branco/EOL) é vazio, ou seja, a única mudança é terminador de linha. | executor | `cineon_pipeline.py`, `enhance_visualizer.py` | `file cineon_pipeline.py enhance_visualizer.py` reporta ASCII/UTF-8 sem CRLF; `git diff -b` vazio nos dois |
| AR3 | Confirmar que nenhum outro arquivo do repo foi tocado pelo `--renormalize` escopado (`git status --porcelain` só deve listar os dois `.py` + `.gitattributes`), rodar suíte Python completa e `ruff check .`. | executor | — | `git status --porcelain -- '*.py' '.gitattributes'` só lista os 3 arquivos esperados; `461 passed`; `ruff check .` limpo |
| AR4 | Fechar `AKF1` com CI real verde. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI |

## Critério de aceite decisivo — diff semântico vazio

A prova de que a renormalização não alterou comportamento não é "os testes passam" — é
`git diff -b` (ignora mudança de espaço em branco/EOL) entre o commit antes e depois do
AR2, restrito aos dois arquivos, vazio. Se aparecer qualquer linha nesse diff, algo além
do terminador mudou e o ciclo para para eu investigar antes de prosseguir.

## Critérios de aceite

- `.gitattributes` ganha só a entrada `*.py text eol=lf` (mais comentário). A entrada de
  `*.cube -text` do Ciclo AK fica intacta.
- `cineon_pipeline.py` e `enhance_visualizer.py` passam a ter blob e worktree em LF.
  Nenhum outro arquivo é tocado pela renormalização.
- `git diff -b` vazio nos dois arquivos entre antes/depois — só terminador de linha mudou.
- Suíte Python: `461 passed`, sem regressão.
- `ruff check .`: limpo, sem violação nova (confirma que o Ciclo AO segue cobrindo o
  repo inteiro sem reação à mudança de EOL).
- CI real verde nos jobs de `ci.yml` e `pylint.yml`. O Pester não toca nesses dois
  arquivos Python — não há razão para variar, mas confirmar `Tests Passed: 91` mesmo assim,
  por disciplina.

## Notas de execução

- Não normalizar CRLF→LF por edição manual de texto (sed, Edit tool linha a linha) — usar
  `git add --renormalize`, que é a ferramenta correta para isso e não arrisca introduzir
  diferença de conteúdo por acidente de encoding.
- Não rodar `git add --renormalize .` (sem escopo) — é exatamente o que o `AK1` fez e foi
  revertido. Nomear os dois arquivos explicitamente no comando.
- Não tocar na entrada `*.cube -text` existente no `.gitattributes`, nem em qualquer outro
  arquivo além dos dois nomeados no achado.
- **Nunca usar `git add -A` nem `git add .`** — o repositório tem arquivos não rastreados
  (`961576A_Hollywood_2Pass.qc.html`, `961576A_Hollywood_2Pass.qc.json`,
  `docs/fila-interrupcao.md`, `docs/launcher-portavel-reels-encoder.md`,
  `docs/windows-ci-e-interrupcao-robusta.md`, `testResults.xml`, `videos/`) que não
  pertencem a ciclo nenhum. Adicionar por caminho explícito.
- Ao verificar a suíte pós-mudança, checar o exit code real do `pytest`, não o de um pipe
  (`| tail`) — armadilha já registrada em `STATE.md` § "Ciclo AP", e que se repetiu na
  minha própria verificação do merge do Ciclo AP.
- Não fechar o ciclo com base em execução local. A prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
