<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo V: Render Queue profissional (batch de verdade)

Data: 2026-08-16 | Ciclo: V | Origem: pedido direto do usuário. Spec:
`docs/superpowers/specs/2026-08-16-render-queue-design.md`. Plano detalhado
(com o código literal do módulo, dos testes e do diff de integração):
`docs/superpowers/plans/2026-08-16-render-queue.md`.

## Diagnóstico

O `--batch` de `Reels_Encoder_v2_FINAL.py` (bloco `# ─── BATCH MODE ───`,
linhas ~4311-4394) hoje é uma lista sequencial: `for` loop simples,
`console.print`/`console.rule` por arquivo, resumo final em texto puro no
fim. Não há progresso global, ETA, nem visão de status por arquivo enquanto
a fila roda — só se sabe o que aconteceu com um arquivo depois que ele
termina. É o gap identificado pelo usuário frente a qualquer ferramenta de
encode paga (Handbrake queue, Adobe Media Encoder).

O projeto já importa `rich.live.Live`, `rich.table.Table` e `rich.panel.Panel`
(usados no medidor EBU R128) — a fila reaproveita a mesma biblioteca, sem
nova dependência. `render_queue.py` é um módulo novo e isolado (raiz do
projeto, mesmo nível de `ebu_meter.py`); o único arquivo de produção
modificado é `Reels_Encoder_v2_FINAL.py`, e só dentro do bloco `--batch` —
nenhum outro modo (single file, Cineon fora de batch) é tocado.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| V1 | Criar `render_queue.py` (dataclass `QueueJob` + `format_duration`/`format_eta`/`estimate_eta`/`build_table`/`run_job`/`render_final_report`) via TDD: escrever `test_render_queue.py` (12 testes) primeiro, confirmar falha por módulo ausente, então implementar. Código literal: plano § Task 1. | `executor` | `render_queue.py`, `test_render_queue.py` | `python -m pytest test_render_queue.py -v` → 12 passed — **done**, commit `13d2d17` |
| V2 | Integrar a fila no loop `--batch`: `import render_queue` após os imports do `rich`; substituir o loop + resumo atual (linhas ~4339-4394) pelo bloco que constrói `list[QueueJob]`, roda cada job dentro de `with Live(...) as live:`, atualiza a tabela a cada transição de status, e delega o relatório final a `render_queue.render_final_report`. Código literal: plano § Task 2. | `executor` | `Reels_Encoder_v2_FINAL.py` | `py_compile` limpo; `python -m pytest test_render_queue.py enhance/ ui/ -q` → só as 4 falhas nominais do baseline (ver Notas), zero novas — **done**, commit `c0e04e2` (377 passed, 4 failed nominais) |
| V3 | Smoke test real de ponta a ponta (ffmpeg de verdade, já confirmado disponível nesta máquina): 1 clipe válido + 1 arquivo inválido forçando falha, batch rodado duas vezes (2ª vez confirma skip-se-já-existe). Colar saída real em `STATE.md` § `## Ciclo V`. Passo a passo: plano § Task 3. | `executor` | `.claude/memory/STATE.md` | relatório final da fila mostra `1/2` sucesso, `1/2` falha com log capturado, e `pulado` no 2º run; suíte completa roda de novo sem regressão — **done**, commit `2054531` |

## Notas de execução

- Baseline de regressão a preservar (documentado em `STATE.md`, ciclos
  I3/H2c/K7/L4/N7): 4 falhas nominais pré-existentes, nenhuma delas
  relacionada a este ciclo — `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`,
  `enhance/test_ebu_meter.py::test_ffplay_args_basic`,
  `ui/test_readme_assets.py::test_anchor_strings_present`,
  `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`. Qualquer
  falha nova é regressão real, não ruído.
- Sem paralelismo, sem abstração `Queue` reutilizável — só o ponto de uso
  atual (`--batch` da CLI). Ver spec § Non-goals.
- V1 e V2 são sequenciais (V2 consome as funções que V1 define); V3 depende
  de V2 estar commitado. Não paralelizar.
- `render_queue.py` não sabe nada sobre FFmpeg/`EncodeConfig`/pipeline
  Cineon — só recebe uma `encode_fn` já fechada sobre esses detalhes. Não
  vazar lógica de encode para dentro do módulo novo.
- V3 roda ffmpeg real contra arquivos fora do repo (`tempfile.mkdtemp()`);
  não deixar pasta de teste dentro da árvore do projeto. `git status` limpo
  ao final do smoke test é parte do critério de done.
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
