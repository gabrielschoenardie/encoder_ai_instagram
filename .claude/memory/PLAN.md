<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo Z: remover opção 5 "Instalar FFmpeg completo" do menu Ferramentas

Data: 2026-08-17 | Ciclo: Z | Origem: pedido direto do usuário.

## Diagnóstico

`ui/launcher.py:55-61` define a constante `TOOLS`, uma lista de tuplas
`(label, cmd)` renderizada como o menu "Ferramentas" (`_flow_tools`,
linhas 152-166). O dispatch é por índice — `TOOLS[choice - 1]` — sem
`if/elif` por opção, então remover a tupla da linha 60 (opção 5,
"Instalar FFmpeg completo" → `tools/fetch_ffmpeg.ps1`) reordena o menu
automaticamente (a antiga opção 6 "Voltar" passa a ser a opção 5) sem
exigir nenhuma outra mudança de dispatch.

Fora de escopo: `tools/fetch_ffmpeg.ps1` (script em si) e o hint de erro
em `launcher.ps1:176,180` que aponta para ele — o pedido é remover a
*opção de menu*, não o instalador. Não deletar o script.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| Z1 | Remover a tupla `("Instalar FFmpeg completo", [...])` de `TOOLS` em `ui/launcher.py:60`. Atualizar `docs/launcher-portavel-reels-encoder.md` (linhas 55, 86, 226) removendo a referência à opção de menu, se a doc listar as opções numeradas. Atualizar `ui/test_launcher.py`: `test_tools_flow_runs_tool_then_returns_to_menu` e `test_tools_flow_subprocess_exception_does_not_crash` hardcodam `ask_choice=[..., 6, ...]` assumindo "Voltar" = índice 6 (5 itens em `TOOLS` + 1); com `TOOLS` em 4 itens, "Voltar" passa a ser índice 5 — ajustar a sequência de índices desses 2 testes para bater com o novo tamanho do menu, sem mudar o que cada teste verifica. | `executor` | `ui/launcher.py`, `docs/launcher-portavel-reels-encoder.md`, `ui/test_launcher.py` | `py_compile ui/launcher.py` limpo; `python -m pytest ui/ -q` sem regressão (baseline: mesmas 4 falhas nominais pré-existentes, ver Notas); commit feito — **done**, commit `bf6d637` |
| Z2 | Revisão de control-flow do wizard pós-remoção (índices de menu, `cfg` vinculado, ordem de dispatch). | `ui-flow-reviewer` | `ui/launcher.py` | veredito: sem branch morto, sem drift de índice — reporta ponteiro + veredito — **done**, `FLOW OK`, sem achados; `pytest ui/ -v` → 128 passed, 2 failed (as 2 falhas nominais pré-existentes, sem relação) |

## Notas de execução

- Baseline de regressão a preservar: `python -m pytest test_render_queue.py enhance/ ui/ -q` → `388 passed, 4 failed` (falhas nominais pré-existentes, listadas em ciclos anteriores: `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`).
- Não remover/alterar `tools/fetch_ffmpeg.ps1` nem o hint em `launcher.ps1`.
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do commit). Detalhe vai para `STATE.md`.
