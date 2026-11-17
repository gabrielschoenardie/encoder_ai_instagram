<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3H: Tela limpa (R-06, R-07, R-10)

Data: 2026-11-16 | Branch: `fix/p3h-clean-screen-r06-r07-r10` (base `8f7aab2` = `origin/main`). Agente alvo: **`executor-pesado`** (toca `ui/tui`, `ui/tui_capture.py`, `ebu_meter.py`, `enhance_visualizer.py`).

## Regras do ciclo

- **Sem commit, sem push, sem merge, sem `git add`.** Sem `git reset --hard`, `git clean`, `git stash`, `git checkout --`/`restore` em arquivo que você não criou.
- Pendências preexistentes não são suas: `.claude/memory/PLAN.md`, `docs/terminal-ui-masterplan.md` (exclusão), `Reels_Encoder_AI.ico`, `docs/*.md` não rastreados, `*.qc.html`/`*.qc.json` na raiz, `videos/`.
- Não tocar `CLAUDE.md`, `.claude/agents/*`, `launcher.ps1`. Motor (`Reels_Encoder_v2_FINAL.py`): **nada muda** neste ciclo.
- Testes sem `sleep` arbitrário (`threading.Event`), só `tmp_path`, efeitos observáveis. Python: `venv\Scripts\python.exe`.
- Ambíguo/conflitante com o código → `blocked` com a pergunta exata em STATE.md. Nada fora de R-06/R-07/R-10. Achados fora do escopo → FINDINGS.md.
- Linhas citadas são de `8f7aab2`; reconfirme antes de editar.

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| P3H-1 | `ui/tui/app.py`, `ui/tui_capture.py` (se precisar) | **R-06 stdout.** Ver desenho §1. |
| P3H-2 | `ebu_meter.py`, `enhance_visualizer.py` | **R-06 processos filhos.** Ver desenho §2. |
| P3H-3 | `ui/tui/state.py`, `ui/tui/app.py`, `ui/tui/screens.py` | **R-07 NOVO ENCODE.** Ver desenho §3. |
| P3H-4 | `ui/tui/state.py`, `ui/tui/app.py` | **R-10 WARNING no `_tick`.** Ver desenho §4. |
| P3H-5 | testes | Ver § Testes. |
| P3H-6 | — | `python -m pytest ui/tui -q --timeout=60`; `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`; `python -m ruff check .`; `git diff --check`. Números reais em STATE.md (§ Ciclo P3H); VALIDATION.md com o item "R-06 — verificação manual no Windows (FFplay + MCTF + preflight enhance-ai) PENDENTE". |

### Desenho

**§1 — R-06 stdout (P3H-1).** Hoje só `sys.stderr` vai para `_Sink`; `print()` de `enhance_visualizer.run_preflight` (`:322-395`) e `enhance/profile.py` (`:598+`) escreve direto no terminal durante o `Live`. Além disso o `Live` padrão (`app.py:78`) usa `redirect_stdout/redirect_stderr=True`, que joga prints dentro da tela alternativa.
- **Armadilha:** `get_console()` cria `Console` sem `file`; o Rich resolve `sys.stdout` a cada escrita. Trocar `sys.stdout` sem fixar o console manda os próprios frames da TUI para o LOG (tela em branco + laço). Portanto, em `run()`: guardar `orig_stdout = sys.stdout` **antes** do `Live`; se o console da TUI não tiver arquivo explícito (`self._console._file is None`), fixá-lo em `orig_stdout` e restaurar (`None`) no fim.
- Default do `live_factory`: `Live(console=c, screen=True, auto_refresh=False, redirect_stdout=False, redirect_stderr=False)`.
- `sys.stdout = _Sink(self._queue.put)` em todo ponto onde hoje `sys.stderr` é trocado/restaurado: o set em `run()`, os dois `finally` de `run()` e a sequência de parar/retomar em `_run_tools` (stdout real durante `_tools`, `_Sink` de volta depois).
- MCTF: `RE:4157` já passa `show_progress=False` com `reporter`. **Não mexer**; só fixar com teste.

**§2 — R-06 processos filhos (P3H-2).** `sys.stdout` só captura escrita Python; filho com stdio herdado escreve no console.
- `enhance_visualizer.py` `_open_ffmpeg_writer` (`:465`): acrescentar `stdout=subprocess.DEVNULL`.
- `ebu_meter.launch_meter_window` (`:312`): no Windows, `creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` (ffplay sem console herdado; a janela SDL continua abrindo). Fora do Windows, inalterado. O medidor continua abrindo durante a sessão (necessário para R-07 — abrir só na saída da TUI deixaria o 1º de dois encodes sem medidor).

**§3 — R-07 NOVO ENCODE (P3H-3).**
- `state.py`: `ACTIONS` ganha `"new"`. Novo campo `worker_stuck: bool = False`, ligado no ramo `R.Info` quando o texto começa com `"O encoder não encerrou"` (mensagem `WORKER_STUCK_MSG`, `tui_driver.py:92`).
- `final_actions(s)`: acrescentar `"NOVO ENCODE"` **no fim** da tupla (índices atuais ficam válidos) quando `s.preset` (sessão aberta pela HOME) e `not s.worker_stuck`. ENTER sobre ela → `action="new"`. Atalho `N`: tecla chega como `k == "CHAR"` com `ch in "nN"` (`keys.py:15-26`), vale nas telas finais e no `REPORT` (que hoje só trata UP/DOWN/ENTER/ESC, `state.py:705-711`) com as mesmas condições.
- Nova função pública `new_session(s) -> UIState` em `state.py`: **construtor novo** `UIState(config={}, screen=HOME, ...)` carregando **só** `drafts`, `focus`, `home_focus`, `system`, `size`, `now`, `cpu`, `ram`, `ram_used_gb`. Proibido `replace` com lista de campos (sobra de `cancel_phase` descarta Stage/Pass/Progress do 2º encode em `state.py:397`; sobra de `exit_code == 0` pula o QC em `_tick`; `is_batch`, `back`, `seal_reveal_start` também vazam).
- `screens.py`: barra de ações das telas finais já itera `final_actions` (`:701`) — confirmar. `REPORT`: incluir a dica `N novo encode` no rodapé quando disponível.
- `app.py` `_session`: vira laço externo. Após `Finished`, `_until(lambda s: s.action in ("exit", "new"))`; em `"new"`: guardar a linha de resumo deste encode (ver abaixo), descartar tudo da fila (`get_nowait` até vazio, **mesmo objeto de fila** — `ConsoleCapture` e os `_Sink` estão ligados a `self._queue.put`), `self._control = R.CancelControl(terminate=self._terminate)` (o `cancelled` é pegajoso), zerar `_ready_at`/`_last_key_at`, `self.state = S.new_session(self.state)` e voltar ao início do laço.
- Resumo/código de saída: `_summary` hoje olha só a tela final. Acumular uma linha por encode (mesmo texto atual de REPORT/COMPLETED/ERROR/CANCELLED, incluindo o `partial_wording`) e imprimir todas na saída. Sair pela HOME após ≥1 encode **não** imprime "Cancelado pelo usuário." e retorna o código do último encode; sem encode, comportamento atual (0 + mensagem). O launcher não consome o código (`launcher.ps1:731-740` abre aba).

**§4 — R-10 (P3H-4).** `_tick` (`app.py:314-323`) engole exceção do bloco `Tick`/`S.apply` e do `_drain`.
- Nova função pública em `state.py` (padrão de `cancel_unavailable`, `:360`): `internal_warning(s, text)` → linha `WARNING` via `_log`.
- Em cada `except` desses dois blocos: registrar `f"erro interno na TUI: {type(exc).__name__}: {exc}"` **uma vez por `repr(exc)` distinto** (guardar conjunto em `self`), com a própria chamada de registro protegida por `try/except` (o loop nunca cai). O bloco de `render` e o `live.update` ficam como estão.

## Testes (P3H-5)

- **R-06:** (a) `App.run` com console **sem `file` injetado** (`Console(file=None)` + fake live que grava frames): durante a sessão `print("x")` vira `Info("x")` no LOG, `sys.stdout` volta ao original após `run()`, e o console da TUI escreve no stdout original (não no `_Sink`); (b) `_run_tools`: stdout real durante `_tools`, `_Sink` depois; (c) live default construído com `redirect_stdout=False, redirect_stderr=False`; (d) `launch_meter_window` no Windows passa `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` e stdio DEVNULL (monkeypatch `subprocess.Popen`); (e) `_open_ffmpeg_writer` com `stdout=DEVNULL`; (f) `_encode_single_file` com `reporter` chama `generate_mctf_mask_video(..., show_progress=False)` (monkeypatch, sem encode real) — se inviável sem rodar o motor, registrar como `blocked` só este subitem.
- **R-07:** redutor — `final_actions` com/sem `preset`, com `worker_stuck`; ENTER em NOVO ENCODE e `N` em COMPLETED/ERROR/CANCELLED/REPORT → `action="new"`; `new_session` não carrega nenhum campo de encode (comparar com `UIState(config={}, screen=HOME, ...)` campo a campo) e preserva `drafts`. **Fluxo de dois encodes na mesma `App`** (fakes de `run_single`/`run_batch`): 1º encode termina **cancelado (130)**, `N`, HOME → mesmo preset → SOURCE pré-preenchido → … → 2º encode emite `Stage`/`Pass`/`Progress` e termina 0 com QC → estado mostra progresso do 2º (não descartado), chega a QC/COMPLETED na ordem certa, `CancelControl` é outro objeto, resumo final tem as duas linhas, código de saída = 0. Variante batch→single se barata.
- **R-10:** `S.apply` monkeypatchado para lançar no `Tick` → após `_tick` o LOG tem uma linha `WARNING` com o tipo da exceção; dois `_tick` com a mesma exceção → uma linha só; exceção no `_drain` também registra; o loop segue (render chamado).

## Depois do executor

`ui-flow-reviewer` sobre `ui/tui/` (nova ação/atalho em telas finais), conforme CLAUDE.md.

## Fora do escopo

`-nostdin` nos FFmpeg do motor (registrar em FINDINGS: `RE:2061` herda stdin do console e pode ler teclas da TUI), layouts 80×24, P3GF2–P3GF8, motor.

## Adendo P3H-7 (aprovado pelo usuário em 2026-11-16) — agente alvo: `executor`

Mesmas regras do ciclo (sem commit/add/push). Arquivos permitidos: `ui/tui/state.py`, `ui/tui/screens.py`, `ui/tui/test_state.py`, `ui/tui/test_screens.py`, `ui/tui/test_app.py`, `.claude/memory/{STATE,FINDINGS,VALIDATION}.md`.

| ID | tarefa |
| --- | --- |
| P3H-7a | **UF1.** Nas telas finais, o ENTER indexa `final_actions` com `min(s.action_focus, len(actions) - 1)`. Além disso, quando `worker_stuck` liga (ramo `R.Info`), o `action_focus` é reclampado ao novo tamanho de `final_actions`. Teste: COMPLETED com QC, foco em NOVO ENCODE, chega o Info de stuck → foco válido; ENTER não lança exceção e executa a ação focada. |
| P3H-7b | **UF4.** O rodapé (`FOOTER_KEYS` / `screens.py`) de COMPLETED, ERROR e CANCELLED cita `[N] Novo encode` **só quando** NOVO ENCODE está em `final_actions` (mesma condição do REPORT). Teste de render com e sem a ação (sem `preset`; com `worker_stuck`). |
| P3H-7c | **Testes que faltam:** `N` ignorado em QC e LOG abertos a partir de tela final (`action` continua `None`, tela inalterada). Cancelamento no **2º** encode da mesma `App`: o 1º termina 0, NOVO ENCODE, o 2º é cancelado via modal (C → confirmar), o `CancelControl` novo recebe o pedido (`request_cancel` verdadeiro, evento `Cancel` na fila) e o estado termina CANCELLED. |
| P3H-7d | Rodar `python -m pytest ui/tui -q --timeout=60`, `python -m ruff check .`, `git diff --check`. Registrar em STATE.md (§ Ciclo P3H, adendo P3H-7) e marcar UF1/UF4 como resolvidos em VALIDATION.md. UF2/UF3 vão para FINDINGS.md (P3HF6/P3HF7) como latentes não tratados. |
