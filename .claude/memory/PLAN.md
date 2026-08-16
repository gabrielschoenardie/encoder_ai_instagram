<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo X: progresso ao vivo durante o job (VF2)

Data: 2026-08-16 | Ciclo: X | Origem: usuário testou o fix do `VF1` (Ciclo W) no
terminal real e reportou que o `--batch` "parece travado" durante um job — sem
crash, sem erro, só sem nenhum sinal visual de progresso. Achado:
`.claude/memory/FINDINGS.md` § "Ciclo W, gap de UX descoberto ao corrigir VF1"
(`VF2`). Plano detalhado (código literal):
`docs/superpowers/plans/2026-08-16-render-queue-live-progress.md`.

## Diagnóstico

`render_queue.run_job` (Ciclo V) chama `encode_fn()` de forma **bloqueante**
— o loop principal do `--batch` fica parado esperando o encode inteiro
terminar, sem chance de redesenhar a tabela nesse meio-tempo. `rich.live.Live`
só repinta o que foi explicitamente mandado via `.update()`; sem chamadas
novas durante o job, a tabela fica congelada do início ao fim.

Antes do Ciclo W, a barra "MCTF masks" (que não passava pela nossa captura,
por usar o console global do Rich — achado `VF1`) era, sem querer, o único
sinal de vida visível durante um job longo. Corrigir `VF1` removeu esse sinal
acidental e expôs o gap real do design original do Ciclo V.

Fix: `run_job` roda `encode_fn` numa `threading.Thread` em background; o
loop principal chama um callback `on_tick` a cada ~250ms enquanto a thread
roda, redesenhando a tabela. `build_table` calcula a duração **ao vivo**
(`time.time() - job.started_at`) para o job com `status == "processando"`,
em vez do `"—"` estático atual — um cronômetro que incrementa é a prova
visual mais direta de "ainda rodando" vs. "travado". Não recria o conflito
de dois `Live`s do `VF1`: nenhuma `Progress`/`Live` nova é criada, só
chamadas a `live.update()` do mesmo `Live` que já existe.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| X1 | Reescrever `run_job` (thread + `on_tick`/`tick_interval`) e o cálculo de duração em `build_table` (ao vivo para `status == "processando"`), TDD: 2 testes novos primeiro (`on_tick` chamado múltiplas vezes durante um encode fake de 0.2s; duração ticking na tabela), confirmar que falham do jeito certo, então implementar. Código literal: plano § Task 1. | `executor` | `render_queue.py`, `test_render_queue.py` | `python -m pytest test_render_queue.py -v` → 14 passed |
| X2 | Fiar `on_tick=_refresh_table` no loop `--batch`: extrair a lógica duplicada de `remaining=...; live.update(...)` numa função local `_refresh_table()` dentro do `with Live(...) as live:`, chamada tanto no caminho "pulado" quanto após cada `run_job`, e passada como `on_tick` pro `run_job`. Código literal: plano § Task 2. | `executor` | `Reels_Encoder_v2_FINAL.py` | `py_compile` limpo; `python -m pytest test_render_queue.py enhance/ ui/ -q` → só as 4 falhas nominais do baseline, zero novas |
| X3 | Smoke test real: batch de 1 clipe, confirmar (via teste automatizado do X1 + inspeção manual da saída) que a coluna Duração incrementa de verdade enquanto o job roda, não só no final. Colar saída real em `STATE.md` § `## Ciclo X`. Passo a passo: plano § Task 3. | `executor` | `.claude/memory/STATE.md` | evidência de duração ticking (ou nota explícita se a captura não-interativa não registrar os frames intermediários); suíte completa sem regressão |

## Notas de execução

- Baseline de regressão a preservar (inalterado desde os ciclos V/W): 4
  falhas nominais pré-existentes — `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`,
  `enhance/test_ebu_meter.py::test_ffplay_args_basic`,
  `ui/test_readme_assets.py::test_anchor_strings_present`,
  `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`.
- X1 e X2 são sequenciais (X2 consome a assinatura nova de `run_job` que X1
  define); X3 depende de X2 commitado.
- Não mexer no design de captura de log (`console.capture()` continua
  envolvendo o encode inteiro, agora dentro da thread) nem no fix do `VF1`
  (barra do MCTF continua desligada em batch) — escopo é só dar sinal de
  vida durante o job.
- `on_tick` só é chamado a partir da mesma thread principal que já possui o
  `Live` — a thread de background só roda `encode_fn`, nunca toca em `live`
  nem em `render_queue`/`console` diretamente.
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
