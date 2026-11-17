<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Limpeza P3H: achados P3HF1, P3HF6, P3HF7 + campos mortos do modal

Data: 2026-11-16 | Branch: `chore/p3h-cleanup-findings` (base `5866e61` = `origin/main`, merge do PR #79). Agente alvo: **`executor-pesado`** (toca motor + `ui/tui`).

## Regras

- **Sem commit/push/merge/`git add`.** Sem `reset --hard`, `clean`, `stash`, `checkout --`/`restore` em arquivo que você não criou.
- Pendências preexistentes não são suas: `docs/terminal-ui-masterplan.md` (exclusão), `Reels_Encoder_AI.ico`, `docs/*.md` não rastreados (inclusive `docs/Phase_2_TUI_Specification.md`, que cita o `[C]` — **não editar**), `*.qc.html`/`*.qc.json` na raiz, `videos/`.
- Não tocar `CLAUDE.md`, `.claude/agents/*`, `docs/superpowers/` (histórico).
- Tocou o pipeline FFmpeg → carregar `skill: instagram-reels-encoder` § Regras de Ouro. `-nostdin` não pode mudar nenhum parâmetro de encode.
- Testes sem `sleep` arbitrário, só `tmp_path`. Python: `venv\Scripts\python.exe`.
- Ambíguo → `blocked` com a pergunta exata em STATE.md. Nada além dos itens abaixo (P3HF2–P3HF5 continuam abertos).

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| C-1 | `Reels_Encoder_v2_FINAL.py`, `ebu_meter.py`, `enhance/*.py`, `enhance_visualizer.py` (só se houver chamada FFmpeg) + testes | **P3HF1 `-nostdin`.** Inventariar toda execução de subprocesso do binário **ffmpeg** (não ffprobe/ffplay). Regra: (a) se o stdin do processo **não** é um pipe de dados (`stdin` ausente ou DEVNULL), inserir `"-nostdin"` logo após o binário no comando **e** passar `stdin=subprocess.DEVNULL`; (b) se o FFmpeg lê dados do stdin (`stdin=PIPE` / `pipe:0`), **não** usar `-nostdin` (o stdin já não é o console). Construtores de comando reaproveitados para log/exibição: o `-nostdin` entra onde o comando é montado para execução; ajustar os testes que comparam a lista exata. Listar em STATE.md cada chamada (arquivo:linha → (a)/(b)). Teste novo: os construtores/chamadas do caminho de encode (2-pass, CRF, Cineon, loudnorm, ebur128) carregam `-nostdin` e `stdin=DEVNULL` (monkeypatch de `subprocess.Popen`/`run`). |
| C-2 | `ui/tui/app.py` + `test_app.py` | **P3HF6.** No laço interno de `_session` (antes do encode), tratar `act == "new"` explicitamente como no-op (`continue`), nunca caindo em start. Teste: `action="new"` injetada na HOME não inicia encode. |
| C-3 | `ui/tui/app.py` + `test_app.py` | **P3HF7.** Depois que o worker retorna (single ou batch), aplicar **todos** os eventos da fila antes do `Finished`: repetir `_drain()` até a fila esvaziar (o `_drain` para a cada evento enquanto há ação pendente). No tratamento de `"new"`: se `self.state.worker_stuck`, limpar a ação e continuar esperando (`exit`/`new`), sem resetar. Teste: N no REPORT com o batch fake ainda rodando; o fake emite `QueueDone` e depois o Info de `WORKER_STUCK_MSG` e só então retorna → o Info é aplicado (`worker_stuck=True`, linha no LOG) e a sessão **não** volta à HOME; sem stuck, N continua levando à HOME. |
| C-4 | `ui/tui/state.py`, `ui/tui/screens.py` (se citar), testes em `ui/tui/` | **Campos mortos.** Remover `modal` e `modal_focus` do `UIState` e todos os `modal=None`/`modal_focus=0` restantes. Testes: remover/ajustar os que constroem `modal="CANCEL"` ou assertam `modal` (`test_state.py`, `test_state_config.py`, `test_state_batch.py`, `test_app.py`). Remover qualquer resto da tecla C de cancelamento em código/testes rastreados (grep `CANCEL_UNAVAILABLE`, `cancel_modal`, `"CANCEL"` como modal, `[C] Cancel`), **sem** tocar no backend do Ctrl+C (`R.Cancel`, `cancel_phase`, `CancelControl`). Docs rastreadas ativas (README etc.) já estão sem `[C]` — confirmar com grep. |
| C-5 | — | Rodar `python -m pytest ui/tui -q --timeout=60`; e, por C-1, os testes do motor/áudio afetados (os arquivos que comparam comandos FFmpeg, ex. `enhance/`, `ui/test_tui_driver.py`); `python -m ruff check .`; `git diff --check`. Números reais em STATE.md (§ Limpeza P3H). Marcar P3HF1/P3HF6/P3HF7 como resolvidos em FINDINGS.md. |
