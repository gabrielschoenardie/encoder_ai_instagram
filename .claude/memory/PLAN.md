<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3C: telas de configuração da TUI

Data: 2026-10-05 | Ciclo: P3C (Phase 3, sub-projeto 2/4) | Spec aprovada pelo usuário.
Ciclo anterior: P3B (casca da TUI, merge local `6d1f439`, push `0dffbee`).

- Spec: `docs/superpowers/specs/2026-10-05-tui-config-screens-design.md`
- Plano detalhado (passos, código, testes): `docs/superpowers/plans/2026-10-05-tui-config-screens.md`

O executor lê os dois inteiros antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

| ID | agente alvo | Task do plano | arquivo(s) | aceite |
|----|-------------|---------------|------------|--------|
| P3C-1 | executor | Task 1 | `ui/tui/widgets.py`, `ui/tui/test_widgets.py` | edição pura verde |
| P3C-2 | executor | Task 2 | `ui/tui/forms.py`, `ui/tui/test_forms.py` | espelho do wizard verde |
| P3C-3 | executor | Task 3 | `ui/tui/state.py` (`Key`), `ui/tui/keys.py`, `ui/tui/test_keys.py` | teclas de texto; P3B verde |
| P3C-4 | executor | Task 4 | `ui/tui/state.py`, `ui/tui/test_state_config.py` | HOME/SOURCE/eventos |
| P3C-5 | executor | Task 5 | idem | CONFIGURATION/ADVANCED/PREVIEW |
| P3C-6 | executor | Task 6 | `ui/tui/screens.py`, `ui/tui/test_screens_config.py` | HOME/SOURCE; ≤120 col; sem emoji |
| P3C-7 | executor | Task 7 | idem | CONFIGURATION/ADVANCED/PREVIEW/READY erro |
| P3C-8 | executor-pesado | Task 8 | `ui/tui/app.py`, `ui/tui/test_app.py` | HOME inicial, ações, Tools suspende/retoma |
| P3C-9 | executor | Task 9 | `ui/tui/__main__.py`, `ui/tui/test_main.py` | sem wizard; preflight antes |
| P3C-10 | executor | Task 10 | `ui/tui/test_parity_wizard.py` | 5 cenários com `Namespace` idêntico |
| P3C-11 | Orquestrador + usuário | Task 11 | roteiro | manual no Windows Terminal |
| P3C-12 | Orquestrador | Task 12 | `.claude/memory/*` | suíte + ruff |

## Notas de execução

- **Branch:** `claude/ciclo-p3c-tui-config` (já em checkout; spec em `2243484`). Sem push.
- **Python:** `venv\Scripts\python.exe` do projeto (tem pytest, pytest-timeout e ruff==0.14.10). Nunca venv em `AppData\Local\Temp`. FFmpeg: `./bin/ffmpeg.exe`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01EpBjK17wXCdV8UhXbMm19r`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- STATE.md: anexar `## Ciclo P3C` com `ID | done ou blocked | arquivo | resultado em 1 linha` — **gravar no caminho `.claude/memory/STATE.md` do repositório** (no P3B um executor gravou uma cópia com caminho deformado na raiz).
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
