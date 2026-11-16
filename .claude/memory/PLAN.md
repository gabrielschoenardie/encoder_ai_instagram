<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3G: TUI única + acesso e resposta (R-03, R-04, R-05)

Data: 2026-11-16 | Branch: `fix/p3g-tui-only-r03-r04-r05` (base `eae27af` = `origin/main`). Decisões aprovadas pelo usuário: remover o modo clássico (wizard) por completo; TUI é a interface única; só Windows.

## Regras do ciclo

- **Sem commit, sem push, sem merge.** Sem `git add`. Sem `git reset --hard`, `git clean`, `git stash`, `git checkout --`/`restore` em arquivo que você não criou.
- Pendências preexistentes NÃO são suas e não podem ser tocadas: `.claude/memory/PLAN.md`, `docs/terminal-ui-masterplan.md` (exclusão), `Reels_Encoder_AI.ico`, `docs/*.md` não rastreados, `*.qc.html`/`*.qc.json` na raiz, `videos/`.
- Não tocar em `CLAUDE.md` nem em `.claude/agents/*` (decisão do usuário; ver FINDINGS).
- Remoção de teste só quando o teste existe **exclusivamente** para o wizard/fallback clássico; listar cada um removido em STATE.md. Os demais: atualizar a expectativa.
- Testes sem `sleep` arbitrário (usar `threading.Event`); só `tmp_path`; efeitos observáveis.
- Python: `venv\Scripts\python.exe`. Lint: `python -m ruff check .`. Pester: `Invoke-Pester -Path ./tests` (pwsh) se disponível.
- Ambíguo ou conflitante com o código → `blocked` com a pergunta exata em STATE.md. Não ampliar escopo (nada de R-06+, P3H, L2, P3I).
- Mapa de referência: extrato do leitor de 2026-11-16 (linhas em `eae27af`; reconfirme antes de editar).

## Tarefas (agente alvo: `executor-pesado`, nesta ordem)

| ID | arquivos | tarefa |
| --- | --- | --- |
| P3G-1a | `ui/launcher.py`, `ui/tui/forms.py`, `ui/tui/app.py`, `ui/__init__.py`, `ui/prompts.py` | **Remover o wizard.** A TUI depende de `ui.launcher.PRESETS` (`forms.py:10`) e `_flow_tools` (`app.py:54`): mover `PRESETS` para `ui/tui/forms.py` e `_flow_tools` (com o que só ele usa) para um módulo da TUI (`ui/tui/tools.py`); depois apagar `ui/launcher.py` e o lazy `run_launcher` de `ui/__init__.py`. Apagar `ui/prompts.py` só se, após a mudança, nada mais o importar. |
| P3G-1b | `Reels_Encoder_v2_FINAL.py` (`main`, `parse_cli`) | Remover `--ui` (`:4474-4479`) e o ramo interativo (`:4543-4565`). Sem `input` e sem `--batch`, `main()` abre a TUI: import tardio de `ui.tui.__main__.main` e `sys.exit(<código>)`. CLI não interativa (input/`--batch`/flags de encode, batch com `Live`, handlers Ctrl+C) **fica como está** — é motor, não modo clássico. Nada mais muda no motor. |
| P3G-1c | `ui/tui/__main__.py`, `ui/tui/state.py` | **R-03 guarda.** Sem fallback para `RE.main()`. Nova constante `FALLBACK_SIZE = (80, 24)` em `state.py` (ao lado de `MIN_SIZE`); `terminal_ok` exige TTY, `is_terminal`, não legado e ≥ 80×24. Se falhar: imprimir erro claro (manter dica de Windows Terminal no console legado; citar o mínimo 80×24) e retornar **1**. Remover `import Reels_Encoder_v2_FINAL` se ficar sem uso. |
| P3G-1d | `ui/tui/state.py`, `ui/tui/screens.py` | **R-03 tela "amplie".** (a) Enquanto `size` < `MIN_SIZE`, `S.apply` ignora `Key` em toda tela que **não** tem encode/fila rodando (HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW, READY e finais). Com encode/fila em andamento o comportamento atual se mantém (cancelar com C etc.). Ctrl+C é sinal e não passa por aqui. (b) `_small` (`screens.py:678`) só diz "o encode continua rodando" quando há encode/QC/fila em andamento; nas demais, texto sem essa linha. Confirmar que o primeiro frame já recebe o tamanho real (o `_tick` aplica `Tick` antes do `render`). |
| P3G-1e | `launcher.ps1`, `launcher.cmd`, `tests/launcher.Tests.ps1` | Remover `Build-AppCommand` (`:612-632`), o parâmetro `-Tui` e o `if ($Tui)` (`:756-761`): o launcher sempre usa `Build-TuiCommand`. `launcher.cmd` deixa de passar `-Tui`. Pester: remover os casos exclusivos de `Build-AppCommand`/`--ui` (`:159-165`, `:249`), manter/ajustar o resto (verificar `:849`). |
| P3G-1f | testes Python | Remover: `ui/test_launcher.py`, `ui/tui/test_parity_wizard.py`, `test_launcher_exposes_version` (`ui/test_version.py:24`), smoke de `render_choice_menu` (`ui/test_components.py:9`) se `ui/prompts.py` for apagado. Reescrever em `ui/tui/test_main.py` os testes de fallback (`:29-56`) para o novo contrato (erro + código 1, sem `RE.main`) e `test_terminal_ok_rules` (100×30 e 80×24 ok; 79×24, 80×23, sem TTY, legado → falso). Atualizar `ui/tui/test_forms.py:23` e `enhance/test_output_dir_and_pipeline_tag.py:212-213` (monkeypatch de `run_launcher`) para o novo ponto. `ui/test_tui_driver.py:596` (`_call_main`) continua válido (CLI com input). Novo: `main()` sem input/batch chama a TUI (monkeypatch). Novos testes P3G-1d: teclas ignoradas em HOME abaixo de 120×40 (estado inalterado), C continua cancelando com encode rodando pequeno, texto de `_small` com/sem "encode continua". |
| P3G-1g | `README.md` | Trocar menções ao wizard/`--ui`/`-Tui` pela TUI (`:87-104`, `:219-226`, `:360`, `:468`, `:682`, `:688-689`). Só o necessário; manter exemplos de CLI com input. |
| P3G-2 | `ui/tui/app.py`, `ui/tui/state.py`, `ui/tui/screens.py`, testes | **R-04 + R-05.** Ver desenho. |
| P3G-3 | — | Rodar `python -m pytest ui/tui -q --timeout=60`; depois `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`; `python -m ruff check .`; Pester se `pwsh` disponível; `git diff --check`. Registrar números reais em STATE.md; problemas fora do escopo em FINDINGS.md. |

### Desenho P3G-2

Causa do congelamento: `_check_source` (`app.py:224-237`) roda dentro de `_session`, entre `_until`; enquanto ele bloqueia (join de 0,3 s + `_probe` até 10 s) nada é desenhado nem drenado.

1. `_check_source` não bloqueia: o atalho UNC parcial continua síncrono (sem disco); o resto vai para uma thread `daemon` que faz o check de disco e publica `S.SourceChecked` em `self._queue` (canal existente, drenado por `_drain` → `S.apply`). Sem `join`, sem caixa de entrada nova. O estado fica em `CHECKING` até o resultado chegar (R-05: disco lento termina sozinho em VALID/NOT_FOUND, sem nova tecla).
2. Arquivo `VALID` → publica `SourceChecked(path, "PROBING")` e roda `_probe` (mesma thread ou outra); ao fim publica `SourceChecked(path, "VALID", dims)`. Probe que falha/retorna `None` → `VALID` com `dims=None` (comportamento atual de dims desconhecidas). Pasta: sem probe (como hoje).
3. Novo status `PROBING`: rótulo "lendo dimensões…" (muted) em `_SOURCE_STATUS` (`screens.py:884-888`); ENTER do SOURCE já exige `VALID` (`state.py:651`) — não muda.
4. Caminho antigo: o redutor já descarta (`state.py:269`). Além disso a thread não inicia o probe se o caminho já não é o atual (leitura de `W.clean_path(self.state.source.text)`); manter o cache `_probed` por caminho.
5. Qualquer exceção na thread → publicar `NOT_FOUND` (disco) ou `VALID` com `dims=None` (probe); o loop nunca cai.
6. `_disk_check`/`PATH_CHECK_S` saem se ficarem sem uso.

Testes P3G-2: disco com atraso controlado por `Event` → `_check_source` retorna imediatamente, estado `CHECKING`, liberado o `Event` e drenada a fila → `VALID` sem tecla; probe bloqueado em `Event` → status `PROBING`, ENTER não avança, render mostra "lendo dimensões…", liberado → `VALID` com dims; caminho trocado antes do fim → resultado descartado; exceção no probe → `VALID`/`None`; exceção no disco → `NOT_FOUND`. Atualizar `test_check_source_slow_disk_does_not_freeze` (`test_app.py:1067`) e `test_check_source_probe_runs_on_caller_thread` (`:1076`), que pinam o comportamento síncrono, e os testes de `_check_source` que esperam resultado imediato (drenar a fila / aguardar evento).

## Fora do escopo

Layouts compactos para 80×24, R-06/R-07/R-10, `ui/probe.py`, CLI não interativa do motor, `CLAUDE.md` e `.claude/agents/ui-flow-reviewer.md` (registrar em FINDINGS como pendência do usuário).

## Adendo P3G-4 (aprovado pelo usuário em 2026-11-16) — agente alvo: `executor`

Mesmas regras do ciclo (sem commit/add/push). Arquivos permitidos: `ui/tui/app.py`, `ui/tui/state.py`, `ui/tui/test_app.py`, `ui/tui/test_state.py`, `ui/tui/test_state_config.py`.

| ID | tarefa |
| --- | --- |
| P3G-4a | **P3GF5.** Em `App._tick` aplicar o `Tick` (tamanho real) **antes** de `_drain`, para que a primeira tecla já veja o tamanho real e seja ignorada abaixo de 120×40. Manter os `try/except` atuais. Teste: terminal pequeno + tecla na fila antes do 1º tick → estado inalterado após `_tick`. |
| P3G-4b | **P3GF6.** O evento `SourceChecked` passa a carregar o tipo verificado (`folder: bool`, default compatível) preenchido pela thread de `_source_worker` conforme o tipo no momento do disparo; o redutor descarta o evento se o caminho **ou** o tipo (`F.is_folder(draft(s))`) não bater com o estado atual. Teste: preset 5, mesmo caminho, alternar TIPO com check do tipo antigo terminando depois → status do tipo atual prevalece. |
| P3G-4c | Rodar `python -m pytest ui/tui -q --timeout=60`, `python -m ruff check .`, `git diff --check`. Atualizar STATE.md (§ Ciclo P3G, adendo) e marcar P3GF5/P3GF6 como resolvidos em FINDINGS.md. |
