<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AS: desacoplar `test_render_queue.py` da cor do terminal (fecha ACF2)

Data: 2026-09-03 | Ciclo: AS | Origem: `.claude/memory/FINDINGS.md` § `ACF2` (Ciclo AC, 2026-08-18), aberto desde então. Priorizado à frente de `ALF1`/`J-b` por decisão do usuário, dado o histórico de recorrência.

## Diagnóstico

Reproduzido nesta investigação, não presumido do achado: `FORCE_COLOR=3 COLORTERM=truecolor
python -m pytest test_render_queue.py -q` → **4 failed, 22 passed**, as mesmas 4 do
registro original:

```
test_run_job_marks_success_and_keeps_log
test_run_job_marks_failure_and_captures_log
test_render_final_report_lists_failure_with_captured_log
test_render_final_report_counts_interrupted
```

Causa: os quatro constroem `Console(file=io.StringIO(), ...)` sem `force_terminal`, e o
`rich` (14.2.0) consulta a variável de ambiente `FORCE_COLOR` para decidir se emite ANSI
— mesmo quando o `file` é um `StringIO`, que não é um terminal de verdade. O ambiente
vence a detecção correta.

### Não é achado isolado — recorrência real, três incidentes nesta sessão

Este `ACF2` já bateu três vezes: na Task 4 do Ciclo AC (origem do achado), na minha
verificação do merge do Ciclo AP, e no `AR3` do Ciclo AR — sempre pelo mesmo mecanismo,
sempre custando investigação para provar que não é regressão do código. Não é um achado
parado; é um gerador ativo de falso alarme a cada ciclo que toca `test_render_queue.py`
de qualquer forma, direta ou indireta.

### Correção ao fix sugerido no achado original

O texto do `ACF2` sugeria duas saídas: `no_color=True` nos `Console` de teste, ou
comparar contra o texto sem ANSI. **Testei `no_color=True` e não é suficiente** — ele
suprime cor mas não estilo (negrito). O caso real de falha usa `[bold]1[/bold]/[bold]2[/bold]`,
que sob `FORCE_COLOR` produz `\x1b[1;33m1\x1b[0m\x1b[33m/\x1b[0m\x1b[1;33m2\x1b[0m` —
`no_color=True` teria removido só o `33` (cor), deixando o `1` (negrito) e ainda quebrando
a asserção de substring `1/2`.

**`force_terminal=False` funciona** — testado nas mesmas condições exatas do repro
(`FORCE_COLOR=3 COLORTERM=truecolor`): zero bytes ESC na saída, `1/2` intacto. É também o
parâmetro documentado do `rich.Console` para forçar "não é terminal" independente do
ambiente — não é gambiarra, é o uso pretendido do parâmetro. Confirmado sem efeito
colateral em ambiente limpo: `Console(file=StringIO())` sem `force_terminal` já
auto-detecta `isatty()==False` num `StringIO`, então passar `force_terminal=False`
explicitamente é no-op fora do cenário `FORCE_COLOR`.

### Escopo: todos os `Console` do arquivo de teste, não só os 4 que falham hoje

`test_render_queue.py` tem **10** instanciações de `Console(...)`. Só 4 falham sob
`FORCE_COLOR` hoje — as outras 6 sobrevivem por acidente de asserção (checam presença de
símbolo isolado, ou uma sequência de caracteres tipo `"TAIL-MARKER"` que o `rich` não
teria razão de estilizar caractere a caractere), não porque sejam robustas ao ambiente.
Corrigir só as 4 deixaria as outras 6 na mesma condição de fragilidade latente — a mesma
classe de "verde pelo motivo errado" que motivou fechar o `AJF3`, e o mesmo raciocínio que
levou o Ciclo AO a trocar `ruff check enhance/` por `ruff check .` em vez de listar
diretório por diretório, e o Ciclo AR a fixar `*.py text eol=lf` por padrão em vez de por
arquivo. Este ciclo aplica `force_terminal=False` às **10** instanciações.

## Desenho

Acrescentar `force_terminal=False` a cada `Console(...)` em `test_render_queue.py`. Só
isso — nenhuma mudança em `render_queue.py` (código de produto). O acoplamento é
inteiramente do lado do teste: os testes constroem seus próprios `Console` para capturar
saída, e são esses objetos — não o `Console` real que a aplicação usa em produção — que
precisam ser determinísticos.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AS1 | Acrescentar `force_terminal=False` a cada uma das 10 instanciações de `Console(...)` em `test_render_queue.py`. Nenhuma outra mudança no arquivo. Não tocar em `render_queue.py`. | executor | `test_render_queue.py` | `git diff` mostra só a adição do parâmetro, 10 ocorrências |
| AS2 | Provar a correção sob as condições exatas do repro: `FORCE_COLOR=3 COLORTERM=truecolor python -m pytest test_render_queue.py -q` → `26 passed`, 0 failed. Rodar também em ambiente limpo (sem essas variáveis) e confirmar contagem idêntica — a mudança não pode alterar comportamento fora do cenário de bug. | executor | — | ambas as execuções, `26 passed` nas duas, colado em `STATE.md` |
| AS3 | Suíte completa (`python -m pytest test_render_queue.py enhance/ ui/ tools/ -q`) sob `FORCE_COLOR=3 COLORTERM=truecolor` e sem — `461 passed` nos dois casos. Checar exit code real, não de pipe. | executor | — | `461 passed` × 2, exit 0 nos dois |
| AS4 | Fechar `ACF2` com CI real verde. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI |

## Critério de aceite decisivo — o teste do próprio bug

A prova não é só "CI verde" — o CI nunca teve esse problema, porque o runner não exporta
`FORCE_COLOR` (já registrado no achado original). A prova é rodar a suíte **com as
variáveis do repro exportadas**, localmente, e confirmar `26 passed` em
`test_render_queue.py` (22 que já passavam + os 4 que falhavam) e `461 passed` na suíte
inteira. Um CI verde sem essa checagem local não teria detectado a doença nem detecta a
cura.

## Critérios de aceite

- `test_render_queue.py` é o único arquivo alterado. `render_queue.py` (produto)
  permanece intocado.
- As 10 instanciações de `Console(...)` recebem `force_terminal=False`; nenhum outro
  parâmetro, assert, ou estrutura de teste muda.
- `FORCE_COLOR=3 COLORTERM=truecolor pytest test_render_queue.py -q` → `26 passed`.
- Suíte completa sob as mesmas variáveis → `461 passed`.
- Suíte completa em ambiente limpo → `461 passed`, contagem idêntica (a mudança não
  altera nada fora do cenário de bug).
- CI real verde (o CI não reproduz o bug, mas confirma ausência de regressão nas
  plataformas de produção).

## Notas de execução

- Não tocar em `render_queue.py`. O acoplamento é só do lado do teste.
- Não usar `no_color=True` — testado e insuficiente (não remove negrito). Usar
  `force_terminal=False`.
- Não usar `NO_COLOR=1` como variável de ambiente do CI ou de wrapper de teste — a
  correção é no construtor do `Console`, não uma variável de ambiente adicional para
  lembrar de exportar.
- **Nunca use `git add -A` nem `git add .`** — o repositório tem arquivos não rastreados
  (`961576A_Hollywood_2Pass.qc.html`, `961576A_Hollywood_2Pass.qc.json`,
  `docs/fila-interrupcao.md`, `docs/launcher-portavel-reels-encoder.md`,
  `docs/windows-ci-e-interrupcao-robusta.md`, `testResults.xml`, `videos/`) que não
  pertencem a ciclo nenhum. Adicionar por caminho explícito.
- Ao verificar suíte, checar o exit code real do `pytest`, nunca o de um `| tail` —
  armadilha já registrada em `STATE.md` § "Ciclo AP" e repetida no `AR3`.
- Ao anexar sua seção ao `STATE.md`, começar com `## Ciclo AS` e cabeçalho de tabela.
- Não fechar o ciclo com base só em CI verde — o CI não reproduz o cenário do bug. A prova
  decisiva é a execução local com `FORCE_COLOR`/`COLORTERM` exportados.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
