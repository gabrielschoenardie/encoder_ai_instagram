<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3E: polimento final da TUI

Data: 2026-10-06 | Ciclo: P3E (Phase 3, sub-projeto 4/4) | Escopo aprovado pelo usuário; plano aguardando revisão.
Ciclo anterior: P3D (PR #72) + chore `.vscode` (PR #73, `cbe545d`).

- Plano detalhado (passos, testes, decisões): `docs/superpowers/plans/2026-10-06-tui-polish-p3e.md`
- Specs: `docs/Phase_2_TUI_Specification.md`, `docs/superpowers/specs/2026-10-06-tui-batch-queue-design.md`
- Catálogo dos itens: `.claude/memory/FINDINGS.md` linhas 1457–1526

O executor lê o plano inteiro antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

| Task | item | agente alvo |
| --- | --- | --- |
| 1 | P3BF2 mensagem da guarda (console legado) | `executor` |
| 2 | P3BF3 `-Tui` no launcher | `executor` |
| 3 | P3AF4 + P3BF4 `run_job` BaseException e 10 Hz | `executor` |
| 4 | P3DF2 Ctrl+C com modal aberto | `executor` |
| 5 | P3CF2 + P3DF1 checagem de caminho sem congelar | `executor-pesado` |
| 6 | P3CF5 teclas POSIX | `executor` |
| 7 | P3CF6 `à` no Windows | `executor` |
| 8 | P3BF1 teste intermitente | `executor` (skill `superpowers:systematic-debugging`) |
| 9a/9b/9c | dívida visual P3B / P3C / P3D | `executor` |
| 10 | fechamento, checagem manual, PR | Orquestrador + usuário |

## Notas de execução

- **Branch:** `claude/ciclo-p3e-tui-polish` (= `main` `cbe545d`, sem commits próprios ainda). Sem push.
- **Python:** `venv\Scripts\python.exe`. Testes: `python -m pytest test_render_queue.py enhance ui tools -q --timeout=60`. Lint: `python -m ruff check .`. Pester: `Invoke-Pester -Path ./tests -CI`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01GKk7GDXVcy4z54k1avkrhG`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, `.claude/memory/*`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- Não tocar `Reels_Encoder_v2_FINAL.py`, `cineon_pipeline.py`, `enhance/` (exceto o teste da Task 8).
- STATE.md: anexar `## Ciclo P3E` com `ID | done ou blocked | arquivo | resultado em 1 linha`; sem commit.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.

## Fechamento (2026-10-09)

| Task | item | commit | situação |
| --- | --- | --- | --- |
| 1 | P3BF2 guarda console legado | 427b126 | feita |
| 2 | P3BF3 `-Tui` | b962274 | feita; conhost e Windows Terminal confirmados pelo usuário |
| 3 | P3AF4 + P3BF4 | 6c92a8b | feita |
| 4 | P3DF2 Ctrl+C com modal | b7f26d0 | feita; confirmado pelo usuário (cancela a fila) |
| 5 | P3CF2 + P3DF1 | b978600 | feita |
| 6 | P3CF5 teclas POSIX | cfde098 | feita |
| 7 | P3CF6 `à` | eb14d8c | feita; regressão das setas corrigida em e05855b; `à` em ABNT2 corrigido em 2dbc2ce (confirmado pelo usuário) |
| 8 | P3BF1 teste intermitente | — | não reproduzido em 300 execuções; aberto S4 |
| 9a | visual P3B | 54714ab | feita |
| 9b | visual P3C | 4ab4d91 | 4 feitos, 1 já feito; item 9b-2 saiu do P3E (P3EF2) |
| 9c | visual P3D e lacunas | 4c69cc1 | feita |
| 10 | fechamento | este commit | documentos atualizados; push e PR conforme autorização do usuário |

Fora do P3E: P3EF1 (probe de 5–7 s), P3EF2 (campo desativado), P3AF1 (emoji no HUD), P3BF1 (S4).
Itens já corrigidos antes do P3E e apenas reconferidos: P3CF1, P3CF4, pytest-timeout. P3AF2 medido: goldens dão SKIP por ambiente, não quebram a CI.
