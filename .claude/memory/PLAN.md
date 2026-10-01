<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3A: canal Encoder → TUI (Reporter seam, B-4)

Data: 2026-09-30 | Ciclo: P3A | Origem: Phase 2 Sign-off, blocker B-4. Spec aprovada pelo usuário.
Ciclo anterior: P2-B3 (protótipo Ctrl+C, verificado T1–T5).

- Spec: `docs/superpowers/specs/2026-09-30-tui-reporter-seam-design.md`
- Plano detalhado (passos, código, testes): `docs/superpowers/plans/2026-09-30-tui-reporter-seam.md`

O executor lê os dois inteiros antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

| ID | agente alvo | Task do plano | arquivo(s) | aceite |
|----|-------------|---------------|------------|--------|
| P3A-1 | executor | Task 1 (+ Step 0 branch/baseline) | `reporter.py`, `ui/test_reporter.py` | 7 testes verdes; baseline registrado |
| P3A-2 | executor | Task 2 | `enhance/test_classic_golden.py`, `enhance/golden/*.json` | goldens gravados no HEAD sem mudança no encoder; 3 execuções estáveis |
| P3A-3 | executor-pesado | Task 3 | `Reels_Encoder_v2_FINAL.py`, `enhance/test_reporter_events.py` | eventos native verdes; 4 goldens intactos |
| P3A-4 | executor-pesado | Task 4 | `Reels_Encoder_v2_FINAL.py`, `enhance/test_reporter_events.py` | eventos Cineon verdes; goldens intactos |
| P3A-5 | executor | Task 5 | `ui/tui_capture.py`, `ui/test_tui_capture.py` | 5 testes verdes |
| P3A-6 | executor-pesado | Task 6 | `ui/tui_driver.py`, `ui/test_tui_driver.py` | todos os testes single verdes |
| P3A-7 | executor-pesado | Task 7 | `ui/tui_driver.py`, `ui/test_tui_driver.py` | todos os testes batch verdes |
| P3A-8 | executor | Task 8 | `ui/test_tui_parity.py` | argv e hash idênticos nos 4 cenários |
| P3A-9 | executor + usuário | Task 9 | scratchpad `b4\` | roteiro rodado pelo usuário; resultado em VALIDATION.md |
| P3A-10 | Orquestrador | Task 10 | `.claude/memory/*` | suíte + ruff; Sign-off atualizado |

## Notas de execução

- **Branch:** `claude/ciclo-p3a-reporter-seam` (criada no Step 0 da Task 1, a partir de `main`). Sem push — Orquestrador faz na P3A-10 com pedido do usuário.
- **Python:** `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`. FFmpeg: `./bin/ffmpeg.exe`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01EpBjK17wXCdV8UhXbMm19r`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- STATE.md: anexar `## Ciclo P3A` com `ID | done ou blocked | arquivo | resultado em 1 linha`; saída vermelha pré-fix em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
