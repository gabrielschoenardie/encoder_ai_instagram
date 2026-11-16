<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3F: entrega segura (R-01, R-02, R-11)

Data: 2026-11-16 | Branch: `fix/p3f-safe-delivery-r01-r02-r11` (base `cb30f3a` = `origin/main`). Escopo e decisões aprovados pelo usuário.

## Regras do ciclo

- **Sem commit, sem push, sem merge.** Sem `git add`. Sem `git reset --hard`, `git clean`, `git stash`, `git checkout --`.
- Pendências preexistentes NÃO são suas e não podem ser tocadas: `.claude/memory/PLAN.md`, `docs/terminal-ui-masterplan.md` (exclusão), `Reels_Encoder_AI.ico`, `docs/*.md` não rastreados, `videos/` (contém master real do usuário — testes só em `tmp_path`).
- Arquivos permitidos: `reporter.py`, `ui/tui_driver.py`, `Reels_Encoder_v2_FINAL.py` (só P3F-1b), `ui/tui/state.py`, `ui/tui/screens.py`, e os testes `ui/test_reporter.py`, `ui/test_tui_driver.py`, `ui/tui/test_state.py`, `ui/tui/test_screens.py`, `test_render_queue.py`. `render_queue.py` não deve precisar mudar.
- Não remover teste existente; atualizar expectativa incompatível. Não mexer nos testes de Ctrl+C durante encode ativo (devem continuar apagando o parcial).
- Testes com sincronização por `threading.Event`, sem `sleep` arbitrário; tudo em `tmp_path`; efeitos observáveis (arquivos, eventos, códigos), não "função foi chamada".
- Python: `venv\Scripts\python.exe`. Lint: `python -m ruff check .`.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata em STATE.md; não improvisar nem ampliar escopo (nada de P3G/P3H/L2/P3I).

## Tarefas (agente alvo: `executor-pesado`, na ordem)

| ID | arquivo | tarefa |
| --- | --- | --- |
| P3F-1a | `reporter.py` | `CancelRequested` passa a herdar de `BaseException`. Em `CancelControl`: novo atributo `cancel_stage` (inicia `None`); `request_cancel` e `force_cancel` gravam `cancel_stage = self.stage` **sob `_lock`, junto com o `_flag.set()`**, só na primeira vez que a flag é marcada. `force_cancel` passa a usar o lock. |
| P3F-1b | `Reels_Encoder_v2_FINAL.py` `_render_pass` (laço ~3674-3790) | Antes do `except Exception as e:` do laço de frames, acrescentar `except _rep.CancelRequested:` que marca `error_occurred = True` e um flag local `cancelled = True` (sem imprimir traceback). No bloco `if error_occurred:`, depois do terminate/wait/kill e do `if interrupted: raise KeyboardInterrupt`, `if cancelled: raise _rep.CancelRequested()`. Nada mais muda no motor. Objetivo: o FFmpeg do Cineon é encerrado antes de o cancelamento propagar. |
| P3F-2 | `ui/tui_driver.py` | **R-02.** Novo helper de limpeza de falha, usado por `run_single` (só se o output não preexistia) e `run_batch` (sempre; o job só roda se o output não existia), chamado **depois** de `R.Error`/`JobDone` já emitidos. Política: (1) se `<saída>_temp.mp4` existe → não apagar nada, `R.Info` de aviso (ver textos); (2) se `control.stage` final é `QC` ou `DONE` → não apagar, `R.Info` "Falha após o encode — master mantido sem QC concluído: {nome}"; (3) caso contrário `render_queue.discard_partial_output(job)`; removeu → `R.Info(f"output parcial removido: {nome}")`; não removeu e o arquivo existe → os dois avisos já existentes ("NÃO foi possível remover…" + "Este arquivo está incompleto e NÃO passou pelo controle de qualidade…"), extraídos para um helper único compartilhado com `_cancel_cleanup`. Códigos de saída e eventos atuais inalterados (single 1; batch segue a fila e termina 1). |
| P3F-3 | `ui/tui_driver.py` | **R-01.** (a) Em `_run_one`, no `except KeyboardInterrupt`, depois da espera, anexar ao próprio exc `worker_finished = worker_done.is_set()` antes do `raise`; no caminho normal, se `worker_done.wait(WORKER_WAIT_S)` der False, tratar igual (não tocar em arquivos). (b) `_temp_path(output)` = `output.replace(".mp4", "_temp.mp4")` (espelha o motor, linha ~3887). (c) Reescrever `_cancel_cleanup` com a política da tabela abaixo, usada nos três pontos de cancelamento (Ctrl+C single, Ctrl+C batch, `result == "cancelado"` nos dois). O estágio é `control.cancel_stage` (não `control.stage`, que vira `QC` depois de remux interrompido). |
| P3F-4 | `ui/tui/state.py`, `ui/tui/screens.py` | Novo campo `master_kept: bool = False` em `UIState`, ligado quando chega `R.Info` cujo texto começa com "Master mantido" (mesmo padrão de `removal_failed`). Em `partial_wording`, antes dos demais casos: `master_kept` → `f"master mantido: {name}"`. |
| P3F-5 | testes | Ver seção Testes. |
| P3F-6 | — | Rodar: `python -m pytest ui/test_tui_driver.py test_render_queue.py ui/test_reporter.py ui/tui/test_state.py ui/tui/test_state_batch.py ui/tui/test_screens.py -q --timeout=60`; depois `python -m pytest -q --timeout=120`; `python -m ruff check .`; `git diff --check`. Registrar números reais. Falha fora do P3F: confirmar se é preexistente com `git stash`-free method (rodar o mesmo teste isolado e ler a causa; NÃO usar stash/checkout) e registrar em FINDINGS.md. |

### Política de `_cancel_cleanup` (decisão aprovada)

Sempre emitir `R.Cancel("terminated")` primeiro. `created_here` = output não existia antes do job.

| condição | ação |
| --- | --- |
| worker não terminou em `WORKER_WAIT_S` | não tocar em arquivo nenhum; `R.Info` de aviso; fim |
| `created_here` e `cancel_stage[0]` ∈ {`FINALIZING`,`QC`,`DONE`} e `_temp.mp4` existe | não apagar nada (nem destino, nem temp, nem relatórios); `R.Info` de aviso de restauração indeterminada; **não** emitir "Master mantido" |
| idem, sem temp, output existe, estágio `QC` | manter master; remover só relatórios QC novos (não preexistentes); `R.Info("Master mantido — QC não concluído.")` |
| idem, estágio `FINALIZING` | manter master; remover relatórios novos; `R.Info("Master mantido — remux não confirmado (átomo colr) e QC não concluído.")` |
| idem, estágio `DONE` | manter master **e** relatórios; `R.Info("Master mantido — QC concluído.")` |
| qualquer outro caso | comportamento atual (descartar output criado nesta sessão, relatórios novos, `Cancel("cleaned", removed)`, avisos YF1 se não removeu). Nunca apagar `_temp.mp4`. |

Nos casos de master mantido: não chamar `discard_partial_output`; a remoção de relatórios não depende de remoção do MP4; emitir `R.Cancel("cleaned", False)` para a UI fechar o ciclo, **sem** o aviso "NÃO foi possível remover". Retorno 130 nos dois caminhos; batch emite `QueueDone(130)` e não inicia jobs seguintes.

Textos de aviso (podem ser constantes no driver):
- worker: `"O encoder não encerrou em {N} s — nenhum arquivo foi alterado. {nome} pode estar incompleto e NÃO passou pelo controle de qualidade."`
- temp presente: `"Restauração do remux falhou ou é indeterminada — nada foi apagado. {nome_temp} pode conter o master original; {nome} NÃO foi validado e será tratado como pronto se continuar na pasta."`

## Testes (P3F-5)

`ui/test_reporter.py`
- `except Exception` não absorve `CancelRequested` (emit dentro de `try/except Exception` após cancel → propaga); `issubclass(CancelRequested, Exception)` é False.
- `cancel_stage` grava o estágio do instante de `force_cancel` e de `request_cancel`, e não muda quando um `Stage` posterior é emitido.

`ui/test_tui_driver.py`
- Atualizar (renomear para refletir o novo comportamento) `test_ctrl_c_during_qc_deletes_new_master`: master existe, conteúdo idêntico aos bytes completos escritos, retorno 130, `R.Info` "Master mantido — QC não concluído.", nenhum `Cancel("cleaned", True)`, nenhum "NÃO foi possível remover".
- Atualizar `test_ctrl_c_during_qc_removes_new_certificate_keeps_preexisting`: master fica; `.qc.json` novo some; `.qc.html` preexistente fica com conteúdo "antigo".
- Atualizar `test_batch_ctrl_c_during_qc_removes_new_certificate`: master do job 0 fica íntegro; relatórios novos somem; um relatório preexistente fica; job 1 não inicia (sem `JobStart(1)`, encoder chamado 1 vez); último evento `QueueDone(130)`; retorno 130.
- R-11 no driver: body cancela e chama `rep.emit` dentro de `try/except Exception`, com código depois que não pode rodar → retorno 130, código posterior não executou, nenhum `R.Error`, job não fica "processando". Falha normal (`ValueError`) continua 1 com `R.Error`.
- Remux (encoder simulado reproduzindo o motor: emite `Stage(FINALIZING,"remux")`, move output → `_temp.mp4`, espera Event): (i) Ctrl+C no remux com restauração bem-sucedida (fake devolve temp → output e emite `Stage(QC)`, que levanta) → master mantido com bytes originais, temp ausente, mensagem de remux não confirmado; (ii) restauração falha (fake deixa destino truncado + temp) → os dois arquivos permanecem, aviso cita o `_temp.mp4`, sem "Master mantido"; (iii) Ctrl+C em `FINALIZING` e o fake conclui o remux (escreve destino final, remove temp) → mantido; (iv) tecla C (`request_cancel`) durante `FINALIZING` com restauração ok → mantido, retorno 130; (v) Ctrl+C em `Stage(DONE)` → master e relatórios mantidos.
- Timeout do worker: `monkeypatch.setattr(D, "WORKER_WAIT_S", valor curto)`, body bloqueado em Event até o fim do teste → arquivos intactos, aviso emitido, retorno 130; liberar o Event no final.
- R-02 single: body cria output com bytes parciais identificáveis e levanta → retorno 1, output ausente, `R.Error` presente. Variante com output preexistente → arquivo não é removido pela limpeza. Variante com `discard_partial_output` forçado a False → avisos "NÃO foi possível remover" e "NÃO passou pelo controle de qualidade", retorno 1.
- R-02 batch: 1ª execução cria parcial e falha em um job → parcial ausente, `JobDone(falha)`, retorno 1, o outro job roda normalmente; 2ª execução (encoder agora ok) → `JobStart` para o job que falhou e nenhum `JobSkip` para ele. Variante remoção malsucedida → aviso, retorno 1.

`ui/tui/test_state.py` / `ui/tui/test_screens.py`
- `R.Info("Master mantido — QC não concluído.")` liga `master_kept`; tela de cancelado mostra "master mantido: {nome}".

Motor (P3F-1b): se existir harness simulado viável (ver `enhance/test_ffmpeg_tracked.py`, `enhance/test_cineon_e2e.py`), teste que um `CancelRequested` levantado pelo reporter no laço encerra o FFmpeg (terminate chamado) e propaga `CancelRequested`. Se não for viável sem FFmpeg real ou sem refatorar, registrar em STATE.md como **não verificado por teste automatizado** — não inventar.

## Retorno

STATE.md: anexar `## Ciclo P3F` com `ID | done ou blocked | arquivo | resultado em 1 linha`, mais os comandos de teste e contagens reais (passed/failed/skipped). Retorno ao Orquestrador: uma linha por ID + contagens; ponteiro, não conteúdo.

## Adendo P3F-7 / P3F-8 (aprovado pelo usuário em 2026-11-16; agente alvo: `executor`)

Tarefas P3F-1a a P3F-6 já estão `done` — não refazer. Mesmas regras do ciclo (sem commit, sem `git add`, sem tocar pendências preexistentes).

| ID | arquivo | tarefa |
| --- | --- | --- |
| P3F-7 (P3FF1) | `reporter.py`, `ui/tui_driver.py`, testes | Novo método em `CancelControl` (ex.: `begin_job()`) que, sob `_lock`, zera `stage` e `cancel_stage` (não mexe na flag). `run_batch` chama-o no início de cada job executado, antes de `_run_one`. Testes: (a) `ui/test_reporter.py` — o método zera os dois campos; (b) `ui/test_tui_driver.py` — batch em que o job 0 termina ok (chega a `Stage(DONE)`) e o job 1 cria parcial e falha **sem emitir nenhum Stage** → parcial do job 1 é removido (sem o reset, `_failure_cleanup` leria `DONE` do job 0 e manteria o arquivo). |
| P3F-8 (P3FF2) | `ui/tui/state.py`, `ui/tui/screens.py`, testes | Novo campo `kept_unvalidated: bool = False` em `UIState`, ligado por `R.Info` cujo texto começa com "Restauração do remux falhou" ou "O encoder não encerrou" (prefixos de `TEMP_PRESENT_MSG` e `WORKER_STUCK_MSG` do driver). Em `partial_wording`, logo após o caso `master_kept`: `kept_unvalidated` → `f"arquivo mantido SEM validação: {name} — veja o LOG"`. Testes em `ui/tui/test_state.py` e `ui/tui/test_screens.py` para os dois cenários, usando os textos reais formatados a partir das constantes do driver. |
| P3F-9 | — | Rodar `python -m pytest ui/test_tui_driver.py ui/test_reporter.py ui/tui/test_state.py ui/tui/test_screens.py -q --timeout=60`, `python -m ruff check .`, `git diff --check`. Não rodar a suíte completa. Marcar P3FF1/P3FF2 como resolvidos em FINDINGS.md e anexar linhas em STATE.md. |

## Adendo P3F-10 (P3FF3 — aprovado pelo usuário em 2026-11-16; agente alvo: `executor-pesado`)

P3F-1a a P3F-9 estão `done` e commitados em `8c150a9`. Mesmas regras do ciclo; **sem commit e sem `git add`** (o Orquestrador faz).

| ID | arquivo | tarefa |
| --- | --- | --- |
| P3F-10 | novo `tests/test_cineon_cancel.py` (ou, se `tests/` não for coletado pelo pytest/der conflito de import, `enhance/test_cineon_cancel.py` ou `ui/test_cineon_cancel.py` — escolher o que a config do pytest coleta e justificar) | Teste unitário do laço de frames de `_render_pass` (closure dentro de `run_ffmpeg_with_cineon`), **sem FFmpeg real e sem vídeo**: chamar `run_ffmpeg_with_cineon` com `unittest.mock.patch`/`monkeypatch` nas dependências (probe, hardware, LUT, loudness, `av.open` devolvendo container falso com alguns frames sintéticos pequenos, `subprocess.Popen` devolvendo `MagicMock` com `stdin`, `stdout`, `stderr`, `poll` → None, `terminate`, `wait`, `kill`, `pid`). Usar como referência de mocks `enhance/test_cineon_constants_guard.py`, `enhance/test_cineon_color_io.py`, `enhance/test_ffmpeg_tracked.py`. O reporter é um fake cujo `emit` levanta `reporter.CancelRequested` no primeiro `Progress`. Provar: (a) `proc.terminate()` foi chamado **antes** de a exceção chegar ao chamador (ex.: registrar ordem de chamadas / assert dentro de `pytest.raises`); (b) `pytest.raises(CancelRequested)` — não vira `RuntimeError` nem é engolido; (c) o remux não é executado (output não é movido para `_temp.mp4`). Incluir contraprova: erro comum no laço (ex.: `emit` levantando `ValueError`) continua virando `RuntimeError("Encoding interrompido…")` com terminate chamado. **Não alterar `Reels_Encoder_v2_FINAL.py`**; se o teste for inviável sem alterar o motor → `blocked` com o motivo exato. Verificar que o teste falha se o `except _rep.CancelRequested` for ignorado (raciocínio ou mutação temporária desfeita à mão — sem git checkout/stash). |
| P3F-11 | `.claude/memory/STATE.md`, `.claude/memory/FINDINGS.md` | Anexar linha P3F-10 em STATE.md; marcar P3FF3 como resolvido em FINDINGS.md. Rodar: o teste novo + `ui/test_tui_driver.py` (`-q --timeout=60`), `python -m ruff check .`, `git diff --check`. Registrar contagens reais. |

Situação do ciclo após P3F-10: completo. Resta apenas, como opcional, ensaio manual de Ctrl+C no QC e no remux com FFmpeg real.

---

## Arquivado — plano anterior (PR #76, concluído e mergeado em `cb30f3a`; não executar)

Branch: `chore/launcher-ajustes-manuais` (PR #76). Data: 2026-10-11.

### Causa (confirmada no log do CI, run 38184361310)

Os 9 testes `Resolve-Binaries` falham nas três jobs que rodam `launcher.ps1` (Windows, Ubuntu e Windows PowerShell 5.1): "Script de instalacao do FFmpeg nao encontrado: ROOT\tools\fetch_ffmpeg.ps1". O bloco de auto-instalação do FFmpeg em `launcher.ps1` (passo 3 de `Resolve-Binaries`) roda quando `ffmpeg` ou `ffprobe` não existem no caminho configurado. Os testes usam uma raiz falsa sem esses binários e sem `tools/fetch_ffmpeg.ps1`, e não simulam o bloco novo.

### Regra

Alterar **somente** `tests/launcher.Tests.ps1`. Não alterar `launcher.ps1`, `launcher.cmd` nem `tools/fetch_wt_portable.ps1`: o usuário fez ajustes manuais nesses três arquivos e pediu para mantê-los como estão.

### Tarefas

| ID | agente alvo | tarefa |
| --- | --- | --- |
| RB-1 | `executor` | No bloco `Describe 'Resolve-Binaries'` (contexto `todos os binarios presentes` e `Windows Terminal ausente (binario opcional)`), fazer os binários simulados existirem antes da chamada: criar arquivos vazios em `TestDrive:` nos caminhos que `launch-config.json` define para ffmpeg, ffprobe e python, ou mockar `Test-Path` apenas para esses caminhos. Preferir criar os arquivos, sem mudar as asserções existentes. |
| RB-2 | `executor` | Acrescentar um teste novo: com ffmpeg ausente e `tools/fetch_ffmpeg.ps1` ausente na raiz falsa, `Resolve-Binaries` lança erro que contém "Script de instalacao do FFmpeg nao encontrado". Esse teste deve passar com o código atual. |
| RB-3 | `executor` | Rodar `Invoke-Pester -Path ./tests -CI` (Pester 5.7.1). Esperado: zero falhas. Rodar `ruff check .`. |
| RB-4 | `executor` | Commit só de `tests/launcher.Tests.ps1`, mensagem `test(launcher): simula binarios presentes em Resolve-Binaries e cobre ausencia do fetch_ffmpeg`, com as linhas de atribuição: `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>` e `Claude-Session: https://claude.ai/code/session_01RWHTxzEisM7reDQnLqn1Nh`. Sem push. Nunca `git add -A`. |

### Retorno

Uma linha por ID (RB-1 a RB-4): veredito, SHA do commit e total de testes Pester (passou/falhou). Se a correção exigir alterar `launcher.ps1`, parar com `blocked` e a pergunta exata.
