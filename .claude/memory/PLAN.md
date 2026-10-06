<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3D: batch de pasta na TUI (+ P3CF1)

Data: 2026-10-06 | Ciclo: P3D (Phase 3, sub-projeto 3/4) | Spec aprovada pelo usuário.
Ciclo anterior: P3C (PR #71, merge `a7a39a8`).

- Spec: `docs/superpowers/specs/2026-10-06-tui-batch-queue-design.md` (inclui §10 com as decisões do plano)
- Plano detalhado (passos, código, testes): `docs/superpowers/plans/2026-10-06-tui-batch-queue.md`

O executor lê os dois inteiros antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

Tabela "Agente alvo" no fim do plano (P3D-1 … P3D-10). P3D-7 (App) = `executor-pesado`; demais tarefas de código = `executor`; P3D-9 manual (Orquestrador + usuário); P3D-10 fechamento.

## Notas de execução

- **Branch:** `claude/ciclo-p3d-tui-batch` (spec e plano commitados). Sem push.
- **Python:** `venv\Scripts\python.exe` do projeto. FFmpeg: `./bin/ffmpeg.exe`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01TbDXaJp96AjEew8NRgGyoS`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, `.claude/memory/*`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- STATE.md: anexar `## Ciclo P3D` com `ID | done ou blocked | arquivo | resultado em 1 linha` no caminho `.claude/memory/STATE.md` do repositório; deixar sem commit.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
