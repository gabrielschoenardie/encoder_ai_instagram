<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo Y: interrupção segura, log preservado e ETA correto (XF1/XF2/XF3)

Data: 2026-08-17 | Ciclo: Y | Origem: auditoria pós-fila (Ciclo X) — achados
`XF1`/`XF2`/`XF3` em `.claude/memory/FINDINGS.md` § "Achado — 2026-08-17
(ciclo X, auditoria pós-fila)". Plano detalhado (código literal):
`docs/superpowers/plans/2026-08-17-fila-interrupcao.md`. Spec:
`docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md`.

## Diagnóstico

`XF1`: `Ctrl+C` durante `--batch` para o `Live`, imprime um aviso e sai com
1 — sem remover o `.mp4` truncado do job em andamento. Como o loop pula
qualquer job cujo output já exista, o arquivo parcial é promovido a
"pronto" na execução seguinte, entregando vídeo cortado. O caminho
single-file já resolve isso desde o PR #22; o batch nunca ganhou
equivalente.

`XF2`: `run_job` captura a saída de cada job via `console.capture()` na
worker thread, mas só transfere o buffer para `job.log` no ramo de falha.
Avisos legítimos de um job bem-sucedido (preflight, MCTF, dither) são
descartados sem deixar rastro.

`XF3`: `estimate_eta` multiplica a média de duração pelo `remaining` que
recebe, e o chamador só passa a contagem de jobs `aguardando` — o job
`processando` fica fora da conta. No último job da fila, `remaining == 0`
e o ETA exibe `00:00` durante o encode inteiro.

Causa raiz comum ao XF1: desde o Ciclo X, `encode_fn` roda numa daemon
thread; o CPython só entrega `KeyboardInterrupt` à main thread (bloqueada
em `on_tick()`/`worker.join(...)`), então o `except Exception` interno de
`_target` nunca vê o sinal e o fechamento do job nunca executa. Detalhe
completo do mecanismo: spec § Architecture.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| Y1 | Registrar os achados XF1/XF2/XF3 e abrir o ciclo: FINDINGS.md, spec, plano salvo, este PLAN.md. Detalhe: plano § Task 1. | `executor` | `docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md`, `docs/superpowers/plans/2026-08-17-fila-interrupcao.md`, `.claude/memory/FINDINGS.md`, `.claude/memory/PLAN.md` | arquivos criados/atualizados conforme o plano; commit feito |
| Y2 | `render_queue.py`: preservar `job.log` em qualquer desfecho de `run_job` (XF2) e estender `estimate_eta` com `in_flight_elapsed` (XF3), TDD. Detalhe: plano § Task 2. | `executor` | `render_queue.py`, `test_render_queue.py` | `python -m pytest test_render_queue.py -v` → 18 passed |
| Y3 | `render_queue.py`: status `"interrompido"` + `discard_partial_output` + `run_job` marca e repropaga `KeyboardInterrupt` (XF1), TDD. Detalhe: plano § Task 3. | `executor` | `render_queue.py`, `test_render_queue.py` | `python -m pytest test_render_queue.py -v` → 23 passed |
| Y4 | Engine: ligar `estimate_eta(..., in_flight_elapsed=...)` e `discard_partial_output` no loop `--batch`, sair com 130 na interrupção. Detalhe: plano § Task 4. | `executor` | `Reels_Encoder_v2_FINAL.py` | `py_compile` limpo; `python -m pytest test_render_queue.py enhance/ ui/ -q` → 384 passed, 4 failed nominais |
| Y5 | Smoke test real de interrupção + evidência colada no STATE.md; marcar Y1..Y5 como done no PLAN.md. Detalhe: plano § Task 5. | `executor-pesado` | `.claude/memory/STATE.md`, `.claude/memory/PLAN.md` | evidência real de `exit=130`, ausência de `.mp4` truncado, job refeito na execução seguinte, ETA > `00:00` no último job (ou achado novo registrado se algo divergir) |

## Notas de execução

- Baseline de regressão a preservar (inalterado desde os ciclos V/W/X):
  `python -m pytest test_render_queue.py enhance/ ui/ -q` → `379 passed, 4
  failed`. As 4 falhas nominais pré-existentes — `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`,
  `enhance/test_ebu_meter.py::test_ffplay_args_basic`,
  `ui/test_readme_assets.py::test_anchor_strings_present`,
  `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`.
- Y1 é pré-requisito de Y2-Y5 (produz os IDs `XF1`/`XF2`/`XF3` citados nas
  mensagens de commit). Y2 e Y3 tocam os mesmos dois arquivos e devem ser
  sequenciais (Y3 assume a assinatura de `estimate_eta` que Y2 introduz).
  Y4 consome as interfaces de Y2 e Y3. Y5 depende de Y4 commitado.
- Não alterar o caminho single-file (`Reels_Encoder_v2_FINAL.py:4411-4424`)
  — já correto, fora de escopo.
- Não ampliar o escopo para `<base>_temp.mp4` órfão do remux do átomo
  `colr` — registrar como achado novo se observado no smoke test, não
  corrigir neste ciclo.
- Mudança de comportamento deliberada: `--batch` passa a sair com **130**
  em interrupção (hoje sai `1`), alinhando com o caminho single-file.
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
