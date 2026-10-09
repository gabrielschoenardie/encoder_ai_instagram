# P3E — Polimento final da TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Cada Task termina com testes verdes e um commit próprio.

**Goal:** Fechar os pendentes S3/S4 do P3A–P3D (launcher, guarda de terminal, fila, teclas, teste intermitente) e a dívida visual da TUI, sem mudar nenhum encode.

**Architecture:** Mudanças pequenas e isoladas em `launcher.ps1`, `ui/tui/*` e `render_queue.py`, cada uma com teste que falha antes. Nenhuma toca `Reels_Encoder_v2_FINAL.py`, `cineon_pipeline.py` nem `enhance/` (Regras de Ouro do encoder intactas).

**Tech Stack:** Python 3.13 (venv do projeto), Rich, pytest (+pytest-timeout), PowerShell 5.1 + Pester 5.7.1.

**Spec:** `docs/Phase_2_TUI_Specification.md` e `docs/superpowers/specs/2026-10-06-tui-batch-queue-design.md`. O catálogo dos itens está em `.claude/memory/FINDINGS.md` linhas 1457–1526 (IDs P3A*–P3D*).

## Global Constraints

- Python: `venv\Scripts\python.exe`. Testes: `venv\Scripts\python.exe -m pytest test_render_queue.py enhance ui tools -q --timeout=60` (espelha o CI). Esperado hoje: 936 coletados.
- Lint: `venv\Scripts\python.exe -m ruff check .` (ruff 0.14.10) limpo antes de cada commit.
- Pester: `Invoke-Pester -Path ./tests -CI` (Pester 5.7.1) para o que tocar `launcher.ps1`.
- Commit por Task; nunca `git add -A`/`.`; terminar com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` e `Claude-Session: https://claude.ai/code/session_01GKk7GDXVcy4z54k1avkrhG`.
- Não commitar `docs/*.md` não rastreados, `videos/`, `.claude/memory/*`, nem a exclusão de `docs/terminal-ui-masterplan.md` (é do usuário).
- Anti-escopo (CLAUDE.md): não refatorar, não criar abstração, sem comentário narrativo. Plano ambíguo ou conflitante com o código → `blocked` com a pergunta exata.

## Itens já resolvidos (não entram; só corrigir o registro)

| ID | situação conferida em 2026-10-06 |
| --- | --- |
| P3CF1 | `ui/probe.py:21-81` usa `timeout=PROBE_TIMEOUT_S` (10 s); teste `test_probe_hung_ffprobe_returns_none_fast`. Corrigido no P3D. |
| P3CF4 | `ui/tui/state.py:227-237` guarda o foco por chave de texto, não por índice. |
| pytest-timeout | declarado em `pyproject.toml` (`dev`), presente no venv e no CI. |
| P3AF2 | Medido no run 37549941700: os goldens `classic_*` dão **SKIP por ambiente** em todas as pernas (ubuntu 3.11: 620 s, 3.12: 389 s; windows: 20 s). Não quebram a CI. Só registrar. |

## Review Focus

1. `SystemExit` dentro do encode de um job da fila com 2+ jobs: o job fica `falha` e o seguinte ainda roda (Task 3).
2. `-Tui` sem Windows Terminal (fallback de janelas PowerShell/conhost): a guarda explica o que fazer, sem abrir tela quebrada (Tasks 1 e 2).
3. Digitar `à` no campo SOURCE no Windows: o caractere entra e a tecla seguinte **não** é engolida (Task 7).
4. Caminho UNC parcial (`\\serv`) no SOURCE: a UI não congela (Task 5).
5. Ctrl+C com o modal LOG/DETAILS aberto no meio de uma fila: sai 130 e o job ativo não fica "processando" (Task 4).
6. Tick de 10 Hz não deixa o encode mais lento nem a UI piscar (Task 3).

---

### Task 1: P3BF2 — mensagem da guarda para console legado (executor)

**Files:**
- Modify: `ui/tui/__main__.py:38-39`
- Test: `ui/tui/test_main.py` (seguir o padrão de `test_terminal_ok_rules`/`test_fallback_runs_classic_main`)

**Interfaces:** Consumes `terminal_ok(console, stdin=None, stdout=None) -> bool` (já existente). Produces nada novo.

- [ ] **Step 1: teste que falha** — com um console falso `legacy_windows=True`, rodar o fluxo de fallback e afirmar que a saída contém `Windows Terminal`; com `legacy_windows=False` e janela pequena, afirmar que **não** contém.
- [ ] **Step 2:** rodar `venv\Scripts\python.exe -m pytest ui/tui/test_main.py -q` → FAIL.
- [ ] **Step 3: implementar** — mantendo a mensagem atual, acrescentar quando `console.legacy_windows`: ` Console legado detectado: abra o launcher no Windows Terminal (wt).` (mesmo estilo `[warn]`).
- [ ] **Step 4:** pytest do arquivo → PASS; `ruff check` limpo.
- [ ] **Step 5: commit** `fix(tui): guarda orienta abrir no Windows Terminal em console legado (P3BF2)`.

### Task 2: P3BF3 — opção da TUI no launcher (executor)

**Decisão do Orquestrador (revisar no plano):** novo switch `-Tui` em `launcher.ps1`. Sem `-Tui` o comportamento não muda (2 abas: Setup + Encode `--ui`). Com `-Tui`, a aba **Encode** passa a rodar `python -m ui.tui`; a aba Setup continua. Sem menu interativo novo (o launcher não tem menu).

**Files:**
- Modify: `launcher.ps1` — bloco `param()` (linhas 8-15), nova função `Build-TuiCommand` ao lado de `Build-AppCommand` (linhas ~509-532), escolha no fluxo (linhas ~619-624)
- Test: `tests/launcher.Tests.ps1` (novo `Describe 'Build-TuiCommand'`, mesmo estilo de `Build-AppCommand`, linhas 158-219)

**Interfaces:**
- Produces: `Build-TuiCommand -VenvPython -RepoRoot -Config [-WorkingDirectory] [-Ffmpeg] [-Ffprobe]` → string igual à de `Build-AppCommand`, terminando em `-m ui.tui` em vez de `<encoderScript> --ui`.

- [ ] **Step 1: testes Pester que falham** — `Build-TuiCommand` termina em `-m ui.tui`; propaga `REELS_FFMPEG`/`REELS_FFPROBE` e `Set-Location` como `Build-AppCommand`; protege caminhos com aspa; `Build-AppCommand` continua terminando em `--ui` (regressão).
- [ ] **Step 2:** `Invoke-Pester -Path ./tests/launcher.Tests.ps1 -CI` → FAIL (função inexistente).
- [ ] **Step 3: implementar** — copiar a estrutura de prefixo de `Build-AppCommand` (sem refatorar a existente) e retornar `"$prefix& $(Protect-PSLiteral -Value $VenvPython) -m ui.tui"`; no `param()` adicionar `[switch]$Tui`; no fluxo, `$encodeCmd = if ($Tui) { Build-TuiCommand ... } else { Build-AppCommand ... }`.
- [ ] **Step 4:** Pester completo (`-Path ./tests -CI`) → PASS.
- [ ] **Step 5:** documentar `-Tui` em 1 linha no `README.md` onde o launcher é descrito (buscar `-SkipValidation`).
- [ ] **Step 6: commit** `feat(launcher): -Tui abre a TUI na aba Encode (P3BF3)`.

### Task 3: P3AF4 + P3BF4 — `run_job` captura `BaseException` e tick de 10 Hz (executor)

**Files:**
- Modify: `render_queue.py:144-193` (`run_job`) — `tick_interval` padrão `0.25` → `0.1`; `failure: BaseException | None`; `except BaseException as exc` em `_target`
- Test: `test_render_queue.py` (ao lado de `test_run_job_calls_on_tick_while_encode_runs`, linha 151)

**Interfaces:** `run_job(job, encode_fn, console, on_tick=None, tick_interval=0.1) -> None` (assinatura igual, só o padrão muda). Antes de alterar, `grep -rn "tick_interval" ui render_queue.py` e conferir se algum chamador (TUI) passa 0.25 explícito; se passar, trocar para o padrão.

- [ ] **Step 1: testes que falham**
```python
def test_run_job_marks_failure_on_system_exit():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO(), force_terminal=False)

    def encode_fn():
        raise SystemExit(1)

    run_job(job, encode_fn, console, tick_interval=0.01)

    assert job.status == "falha"
    assert job.error
    assert job.finished_at is not None


def test_run_job_default_tick_is_10hz():
    import inspect
    assert inspect.signature(run_job).parameters["tick_interval"].default == 0.1
```
- [ ] **Step 2:** `venv\Scripts\python.exe -m pytest test_render_queue.py -q` → os dois FAIL.
- [ ] **Step 3: implementar** como descrito em **Files** (remover o `# noqa: BLE001` se o ruff deixar de exigir; `str(failure)` de `SystemExit(1)` é `"1"` — usar `job.error = str(failure) or type(failure).__name__`).
- [ ] **Step 4:** suíte completa do CI → PASS (nenhum teste usa o padrão antigo; ambos usam override).
- [ ] **Step 5: commit** `fix(queue): SystemExit no encode vira falha e tick padrão 10 Hz (P3AF4, P3BF4)`.

### Task 4: P3DF2 — Ctrl+C com modal aberto na fila (executor)

**Files:**
- Modify: `ui/tui/app.py:131-137` (`_interrupted_code`)
- Test: `ui/tui/test_app*.py` (achar com `grep -rn "test_ctrl_c" ui/tui`; seguir o teste vizinho)

- [ ] **Step 1: teste que falha** — estado de batch com `screen != QUEUE` por causa de modal DETAILS/LOG e job ativo; chamar `_interrupted_code()`; esperar retorno `130` **e** o estado ter recebido `Finished(130)` (job ativo não fica "processando" no resumo).
- [ ] **Step 2:** rodar o teste → FAIL.
- [ ] **Step 3: implementar** — trocar a condição `s.is_batch and s.screen == S.QUEUE` por `s.is_batch and s.screen in (S.QUEUE, S.DETAILS, S.LOG)`. **Não** usar `!= S.REPORT`: em READY de batch a fila ainda não começou e `test_batch_held_enter_after_arm_never_starts_queue` exige que Ctrl+C fique em READY (decisão do Orquestrador após o `blocked` do executor). Ler o redutor de `Finished` e confirmar que ele fecha o modal; se não fechar → `blocked` com a pergunta.
- [ ] **Step 4:** `pytest ui/tui -q` → PASS. **Step 5: commit** `fix(tui): Ctrl+C com modal aberto finaliza a fila (P3DF2)`.

### Task 5: P3CF2 + P3DF1 — checagem de caminho não congela a UI (executor-pesado)

**Decisão do Orquestrador (revisar):** (a) caminho UNC parcial — texto começando em `\\` com menos de 2 separadores depois do prefixo — **não** consulta o disco (status `NOT_FOUND`); (b) `isfile`/`isdir`/`listdir` rodam numa thread descartável com `join(timeout=0.3)`; estourou → status `NOT_FOUND` sem resultado e a próxima tecla reavalia. Sem estado novo no redutor.

**Files:**
- Modify: `ui/tui/app.py:212-239` (`_check_source`, `_check_folder`); no máximo uma função auxiliar privada no mesmo arquivo
- Test: `ui/tui/test_app*.py`

- [ ] **Step 1: testes que falham** — (i) `\\serv` não chama `os.path.isdir/isfile/listdir` (monkeypatch que levanta se chamado); (ii) com `os.path.isdir` trocado por função que dorme 2 s, `_check_source` retorna em < 0.6 s; (iii) caminho válido continua `VALID` e pasta com vídeos continua listando (regressão dos testes P3D).
- [ ] **Step 2:** FAIL. **Step 3:** implementar como descrito. **Step 4:** `pytest ui/tui -q` → PASS. **Step 5: commit** `fix(tui): checagem de caminho com timeout e sem tocar UNC parcial (P3CF2, P3DF1)`.
- Se o redutor exigir estado novo para funcionar → `blocked` com a pergunta exata.

### Task 6: P3CF5 — teclas estendidas no POSIX (executor)

**Files:** Modify `ui/tui/keys.py` (`decode_posix` e a leitura da sequência POSIX) · Test: `ui/tui/test_keys.py`

- [ ] **Step 1: testes que falham**
```python
def test_posix_delete_is_delete():
    assert decode_posix("\x1b[3~") == "DELETE"

def test_posix_pgup_pgdn_are_ignored():
    assert decode_posix("\x1b[5~") is None
    assert decode_posix("\x1b[6~") is None
```
  Mais um teste da camada de leitura: alimentar `\x1b[3~` e garantir que nenhum `~` sobra para o campo de texto (seguir como o teste de `decode_posix` alimenta a leitura; se a leitura é função separada, testá-la).
- [ ] **Step 2:** FAIL. **Step 3:** mapear `"[3~"` → `"DELETE"` em `_ANSI`; a leitura deve consumir a sequência CSI até o byte final (`~` ou letra) e devolver `None` para as não mapeadas. Não-ASCII no POSIX: ler o caractere UTF-8 inteiro em vez de descartar.
- [ ] **Step 4:** `pytest ui/tui/test_keys.py -q` → PASS. **Step 5: commit** `fix(tui): Delete/PgUp/PgDn no POSIX não vazam '~' e aceita não-ASCII (P3CF5)`.

### Task 7: P3CF6 — `à` não engole a tecla seguinte no Windows (executor)

**Files:** Modify `ui/tui/keys.py:11-39` (`decode_windows` e o leitor `getwch`) · Test: `ui/tui/test_keys.py`

- [ ] **Step 1: testes que falham** — leitor com `getwch` simulado: `"\xe0"` seguido de `"K"` **imediatamente** (`kbhit` verdadeiro) → `LEFT`; `"\xe0"` com `kbhit` falso → caractere `à`, e a tecla seguinte (`"a"`) é lida normalmente.
- [ ] **Step 2:** FAIL. **Step 3:** no leitor Windows, só tratar `\xe0` como prefixo se `msvcrt.kbhit()` indicar tecla pendente; `\x00` continua sempre prefixo. Manter `decode_windows(ch, nxt)` e `_WIN_EXT` intactos.
- [ ] **Step 4:** PASS. **Step 5: commit** `fix(tui): 'à' digitado não é tratado como tecla estendida (P3CF6)`.

### Task 8: P3BF1 — teste intermitente `test_red_bt709_full_range` (executor, skill systematic-debugging)

**Files:** investigar `enhance/test_cineon_color_io.py:64-65` e os helpers `_bt709_ycbcr`, `_frame`, `_assert_rgb` (linhas 26-56).

- [ ] **Step 1:** reproduzir: `venv\Scripts\python.exe -m pytest enhance/test_cineon_color_io.py::test_red_bt709_full_range -q --count` não existe; usar laço: 300 execuções em um único comando (`for` de shell) e registrar quantas falham e a mensagem.
- [ ] **Step 2:** se falhar, rodar também a suíte `enhance/test_cineon_color_io.py` inteira em ordem aleatória/repetida para ver se é estado compartilhado (ex.: `_silence_console`, cache de swscale). Causa raiz antes de qualquer correção; **não** alargar a tolerância sem explicar a causa.
- [ ] **Step 3:** corrigir a causa (teste ou código) com teste de regressão determinístico.
- [ ] **Step 4:** se **não** reproduzir em 300 execuções → registrar em STATE (`ID | done | - | não reproduzido em 300 execuções, mantido aberto como S4`) e **não** alterar código.
- [ ] **Step 5: commit** só se houve correção: `fix(test): estabiliza test_red_bt709_full_range (P3BF1)`.

### Task 9: Dívida visual (executor, 3 sub-tarefas, um commit cada)

Fonte literal dos itens: `.claude/memory/FINDINGS.md` linha 1500 (P3B), 1515 (P3C), 1526 (P3D). Cada item ganha **um teste que falha antes** (golden de tela ou assert sobre o texto renderizado, seguindo os testes de `ui/tui/test_screens*.py`). Itens, por sub-tarefa:

- **9a (READY/DETAILS/LOG, P3B):** READY com ~5 linhas vazias; DETAILS com rótulos espremidos e proveniência desalinhada; "PASS · 2"; LOG sem margem; `error_scroll` sem limite; "CANCEL · requested" duplicada.
- **9b (SOURCE/Config, P3C):** "ENTER → CONFIGURATION" não esmaece quando inválido; `field_rows` sem render de campo desativado; choice de uma opção mostra `◂ ▸`; SETTINGS/PREVIEW arredondam números; falta espaço nas ações do READY.
- **9c (P3D):** `new_draft` do preset 4 sem chaves de formulário; ENTER com foco no TIPO não avança; linha de 138 colunas em `screens.py`; lacunas de teste (preset 5-Pasta EMPTY bloqueando, janela da fila nas bordas, D/L a partir da QUEUE, ETA com job ativo acima da média, Cineon "off" nos cenários de paridade).

- [ ] Para cada sub-tarefa: escrever os testes (falham) → ajustar `ui/tui/screens.py`/`widgets` mínimo → `pytest ui/tui -q` e `ruff` verdes → commit `fix(tui): polimento visual <READY/DETAILS/LOG|SOURCE/Config|P3D> (P3E)`.
- Mudou fluxo de menu/seção em `ui/launcher.py`? Não deve; se mudar, acionar `ui-flow-reviewer`.
- Qualquer item sem comportamento observável definível → `blocked` com a pergunta; não inventar.

### Task 10: Fechamento (Orquestrador + `validador`)

- [ ] Suíte completa do CI + `ruff` + Pester verdes; `validador` não é necessário (nenhum encode muda).
- [ ] Checagem manual do usuário: abrir `.\launcher.ps1 -Tui` no Windows Terminal e no conhost; digitar `à` no SOURCE; Ctrl+C no meio de uma fila com LOG aberto.
- [ ] Atualizar `FINDINGS.md` (marcar corrigidos/estáveis), `STATE.md`, `VALIDATION.md`; PR do ciclo P3E.

## Self-Review

- Cobertura: P3BF2 (T1), P3BF3 (T2), P3AF4+P3BF4 (T3), P3DF2 (T4), P3CF2+P3DF1 (T5), P3CF5 (T6), P3CF6 (T7), P3BF1 (T8), dívida visual P3B/P3C/P3D (T9). P3CF1, P3CF4, P3AF2 e `pytest-timeout` documentados como já resolvidos. Fora de escopo por decisão: fila avançada, ABF3, BDF11-13, P3AF1.
- Tasks 5, 6, 7 e 9 dependem de código que o plano não transcreve (`app.py`, `keys.py`, `screens.py`): o executor lê o trecho citado antes de escrever o teste; a divergência vira `blocked`.
