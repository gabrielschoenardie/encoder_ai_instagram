<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3B: casca da TUI + encode ao vivo

Data: 2026-10-01 | Ciclo: P3B (Phase 3, sub-projeto 1/4) | Spec aprovada pelo usuário.
Ciclo anterior: P3A (canal Encoder → TUI, PR #70, merge `4c95462`).

- Spec: `docs/superpowers/specs/2026-10-01-tui-shell-encode-design.md`
- Plano detalhado (passos, código, testes): `docs/superpowers/plans/2026-10-01-tui-shell-encode.md`

O executor lê os dois inteiros antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

| ID | agente alvo | Task do plano | arquivo(s) | aceite |
|----|-------------|---------------|------------|--------|
| P3B-1 | executor | Task 1 (+ Step 0 baseline) | `ui/tui/__init__.py`, `ui/tui/state.py`, `ui/tui/test_state.py` | testes do reducer verdes; baseline registrado |
| P3B-2 | executor | Task 2 | `ui/tui/keys.py`, `ui/tui/test_keys.py` | decoders e start/stop verdes |
| P3B-3 | executor | Task 3 | `ui/tui/screens.py`, `ui/tui/test_screens.py` | READY e aviso de terminal pequeno; ≤ 120 colunas; sem emoji |
| P3B-4 | executor | Task 4 | idem | ENCODING, modal, DETAILS, LOG |
| P3B-5 | executor | Task 5 | idem | QC, COMPLETED, ERROR, CANCELLED |
| P3B-6 | executor-pesado | Task 6 | `ui/tui/app.py`, `ui/tui/test_app.py` | ciclo de vida, restauração, render nunca derruba o encode |
| P3B-7 | executor | Task 7 | `ui/tui/__main__.py`, `ui/tui/test_main.py` | guarda do terminal, códigos 0/1/2/130 |
| P3B-8 | executor + usuário | Task 8 | scratchpad `p3b\` | roteiro T1–T8 rodado no Windows Terminal |
| P3B-9 | Orquestrador | Task 9 | `.claude/memory/*` | suíte + ruff; push/PR com pedido do usuário |

## Notas de execução

- **Branch:** `claude/ciclo-p3b-tui-shell` (já em checkout; spec em `b4aa09b`). Sem push.
- **Python:** `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`. FFmpeg: `./bin/ffmpeg.exe`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01SXsnXWdtHrM5BGaCfeq1qB`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- STATE.md: anexar `## Ciclo P3B` com `ID | done ou blocked | arquivo | resultado em 1 linha`.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
