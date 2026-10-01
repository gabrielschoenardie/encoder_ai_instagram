# P3B — Casca da TUI + encode ao vivo — Design

Data: 2026-10-01 · Status: aprovado em conversa, aguardando revisão do arquivo
Ciclo: P3B (Phase 3, sub-projeto 1 de 4: P3B casca+encode → P3C configuração → P3D batch → P3E acabamento).
Referências obrigatórias: `docs/Phase_2_TUI_Specification.md` §M, §N, §O, §P, §Q, §R, §S, §U, §V, §W, §X, §AD, §AE, §AF;
`docs/superpowers/specs/2026-09-30-tui-reporter-seam-design.md` (canal P3A); `.claude/memory/FINDINGS.md` § "Ciclo P3A"
(contrato para as telas). `RE` = `Reels_Encoder_v2_FINAL.py`.

## 1. Objetivo e critério de sucesso

`python -m ui.tui` monta a configuração pelo wizard de linha atual e, ao confirmar, entra em tela cheia no READY e segue
ENCODING → QC → COMPLETED / ERROR / CANCELLED, para **um arquivo**, com encode real.

Pronto quando:

1. Testes automáticos (§8) verdes no CI Windows e Linux; suíte completa sem regressão (goldens e paridade P3A intactos).
2. Manual no Windows Terminal (§8.6) passa: native 2-pass e Cineon até o selo; D/L/ESC; modal `C`; `C` recusado no MCTF;
   Ctrl+C no PASS 1; resize durante o encode; sem ffmpeg órfão; terminal utilizável ao sair.
3. CLI clássico e line wizard inalterados (§5 do Sign-off).

## 2. Decisões fechadas

| ID | Decisão |
|----|---------|
| B-1 | Ordem dos ciclos: P3B → P3C → P3D → P3E. |
| B-2 | No P3B a configuração vem de `ui.launcher.run_launcher(console)` (opção A). A confirmação dupla (Confirm do wizard + READY) é transitória; P3C a remove. |
| B-3 | Telas do recorte com fidelidade total aos wireframes da spec (opção A): READY, ENCODING (+2-pass §O, Cineon unificado §P), DETAILS, LOG, modal CANCEL, QC/DELIVERY com revelação do selo, COMPLETED, ERROR (inclui o estado CANCELLED de §S/§W). |
| B-4 | Arquitetura: Rich `Live(screen=True)` único + `UIState` dataclass + reducer puro + render puro (opção A). Sem Textual, sem curses, sem dependência nova. |
| B-5 | Terminal abaixo de 120×40 **durante** o encode: substitui a tela por aviso "terminal pequeno — amplie para 120×40"; o encode continua. |
| B-6 | Tela final fica até ENTER/ESC; sai com o código do condutor. Sem "novo encode" (D-19). |

## 3. Módulos (`ui/tui/`)

| Arquivo | Responsabilidade | Depende de |
|---------|------------------|------------|
| `__main__.py` | (1) guarda do terminal; (2) `run_launcher`; (3) `App(ns).run()` → `sys.exit(code)` | `app`, `ui.launcher`, `RE` |
| `state.py` | `UIState` + `apply(state, ev) -> UIState` (puro, sem I/O, sem relógio próprio: o tempo vem no evento) | `reporter` |
| `keys.py` | thread de teclado → `Key(name)` na fila; `msvcrt` (Windows) / `termios` cbreak com ISIG ligado (POSIX); nunca consome Ctrl+C | stdlib |
| `screens.py` | `render(state, size) -> Renderable`: cabeçalho (3) + corpo (34) + rodapé (3) por tela; componentes novos (hero duplo, faixa de passe, trilho de etapas, modal) | `ui.components`, `ui.theme` |
| `app.py` | dono do `Live`; fila, `CancelControl`, `ConsoleCapture`, redireção de `sys.stderr`, thread de teclado; READY → `run_single` → tela final | `ui.tui_driver`, `ui.tui_capture`, `state`, `screens`, `keys` |

Nenhum arquivo existente do encoder, do condutor (`ui/tui_driver.py`), da captura ou do wizard muda de comportamento.

### 3.1 Fluxo de `__main__`

```text
1. guarda: sys.stdin.isatty() e sys.stdout.isatty(); console = get_console() com console.is_terminal e
   não console.legacy_windows (VT); console.size ≥ 120×40?
   não → mensagem curta + executa RE.main() inalterado (CLI clássico / wizard) e sai com o código dele
2. ns = run_launcher(console)       None → sys.exit(0)
   pré-checagem de binários + RE._validate_args_consistency(ns): mesmas mensagens e códigos que main() (1 / 2)
3. sys.exit(App(ns).run())
```

## 4. Estado (`UIState`) e eventos

Campos (somente dados copiados de eventos ou do `Namespace`):

| Campo | Origem | Uso |
|-------|--------|-----|
| `screen` ∈ READY, ENCODING, DETAILS, LOG, QC, COMPLETED, ERROR, CANCELLED; `modal` ∈ None, CANCEL | reducer | tela atual |
| `config` | `Namespace` | READY, job strip, PERFORMANCE (threads, performance) |
| `stage`, `substep`, `stages_done` | `Stage` | trilho de etapas; regra de `C` |
| `passes: list[PassTrack]` | `Pass` + `Progress` | uma faixa por passe (%, ETA, ou ✓ duração); Pass 1 permanece (D-12); `Pass end` → 100% |
| `timeline` | último `Progress` + `ts` | TIMELINE; job elapsed = `ts` atual − `ts` do primeiro `Stage` |
| `hardware`, `probe`, `encode_params` | eventos homônimos | DETAILS com proveniência CFG/DET/CALC/LIVE (D-14); tier em PERFORMANCE |
| `log: list[LogRow]` (categoria SYSTEM/INFO/WARNING/FFMPEG, texto) | `Stage` (SYSTEM), `Info` (WARNING se casar com `re.search(r"^aviso\b\|\bfalhou\b\|n[ãa]o foi poss[ií]vel", texto, re.IGNORECASE)`, senão INFO), `FfmpegLine` (FFMPEG; texto dividido em `\r` e mantida só a última parte não vazia) | painel LOG (9 linhas) e tela LOG |
| `warnings: int` | linhas WARNING | badge `⚠ N` |
| `qc` | `Qc.payload` | QC/DELIVERY, COMPLETED |
| `result` (`exit_code`, `output_path`, `seconds`, `error`) | `Done`, `Error`, retorno de `run_single` | COMPLETED / ERROR / CANCELLED |
| `cancel_phase` | `Cancel` | CANCEL_REQUESTED → CANCELLED |
| `seal_reveal_start: float \| None` | tick | animação do selo (~1,2 s) |
| `size: (cols, rows)` | tick | aviso de terminal pequeno (B-5) |

Evento de tecla: `Key(name)` com `name` ∈ ENTER, ESC, LEFT, RIGHT, D, L, C (case-insensitive); demais teclas descartadas.
Evento de tick: `Tick(ts, size)`.

### 4.1 Transições

```text
READY ──ENTER──▶ ENCODING ──Stage QC──▶ QC ──Done + selo revelado──▶ COMPLETED
   │ESC → sair 0     │ D ⇄ DETAILS · L ⇄ LOG (ESC volta para ENCODING)
                     │ C ──▶ modal CANCEL ─Confirmar─▶ CANCEL_REQUESTED ─▶ CANCELLED
                     │                     ESC ──▶ fecha modal
                     │ Ctrl+C ──▶ CANCEL_REQUESTED direto (sem modal, D-10)
                     └ Error ──▶ ERROR
```

Regras:

- `C` desenhada `░[C]` e ignorada quando `(stage, substep)` está em `reporter.CANCEL_BLOCKED` (D-22, D-11). Confirmar no modal chama `control.request_cancel()`; se retornar False (corrida de etapa), o modal fecha e nada muda.
- Após qualquer `Cancel`, eventos `Stage`/`Pass`/`Progress` subsequentes são ignorados (contrato P3A).
- Não há `Progress` final garantido: `Pass(phase="end")` fixa a faixa em 100% e grava a duração.
- Campo sem evento correspondente renderiza `—` (D-13). Duração com fallback de 30 s não é marcada (Sign-off #11).
- `exit_code` 0 → COMPLETED; 130 → CANCELLED; 1/2 → ERROR (com o último `Error`, se houver).

## 5. Render

- Região fixa: cabeçalho 3 linhas (marca + versão + status à direita; trilho de abas HOME·SOURCE·CONFIG·PREVIEW·READY·ENCODE·QC·DELIVERY — no P3B as quatro primeiras aparecem como ✓ concluídas), corpo 34 linhas, rodapé 3 linhas com as teclas válidas da tela. Medidas de região conforme §AE.
- Telas implementadas por wireframe da spec: §M READY, §N ENCODING (+§O, §P), §Q DETAILS, §R LOG, §S CANCEL (modal 64×12 na linha 11, coluna 28 do corpo), §U QC/DELIVERY (`delivery_seal` existente, revelado pelo tick), §V COMPLETED (ações reduzidas a SAIR + VER LOG; VER QC volta à QC estática), §W ERROR (card, cauda do stderr, ESTADO).
- Componentes reutilizados: `job_strip`, `viewer_frame`, `gauge_bar`, `log_panel`, `error_card`, `tab_bar`, `delivery_seal`, `quality_chip`. Novos e locais a `screens.py`: hero duplo, faixa de passe, trilho de etapas, modal.
- Motion apenas spinner, pulso da faixa ativa e revelação do selo (D-21). Sem emoji em regiões fixas (D-20): glifos do tema; onde o tema usa 🎧/✨, a TUI usa o equivalente ASCII.
- Nenhuma linha do render excede 120 colunas.

## 6. Teclado (`keys.py`)

- Thread daemon; Windows: `msvcrt.kbhit()`/`getwch()` com espera de 50 ms; teclas estendidas (prefixo `\x00`/`\xe0`) mapeiam setas.
- POSIX: `termios` em cbreak com ISIG ligado (Ctrl+C continua sinal), `select` com timeout; ESC isolado vs sequência de seta por timeout curto; atributos restaurados no `stop()`.
- Ctrl+C nunca é lido como tecla (validado no B-3). `stop()` encerra a thread.

## 7. Ciclo de vida (`app.py`)

```text
entra:   console próprio (get_console) · Live(screen=True) · ConsoleCapture(RE.console, fila) ·
         sys.stderr → coletor (mesma limpeza da captura, eventos Info) · CancelControl(RE.terminate_active_ffmpeg) ·
         thread de teclado
READY:   loop de teclado + tick até ENTER (segue) ou ESC (código 0)
encode:  code = run_single(ns, fila, control, on_tick); on_tick = esvaziar fila → apply → live.update(render)
final:   loop até ENTER/ESC na tela final; devolve code
sai (finally, sempre e nesta ordem): para thread de teclado → restaura sys.stderr → sai da captura → fecha Live → restaura terminal
```

- Fila `queue.Queue()` sem limite (contrato P3A).
- Ctrl+C: durante `run_single`, o condutor trata e devolve 130. No READY, na tela final ou entre o fim do encode e a tela final: `KeyboardInterrupt` capturado em `run()` → código 130 (contrato P3A).
- Exceção não prevista na TUI: o `finally` restaura o terminal antes de o traceback aparecer; código 1.
- Tick a 10 Hz; `Progress` já limitado a 10 Hz pelo reporter.

## 8. Testes

1. **Reducer** (`ui/tui/test_state.py`): cada transição de §4.1; `C` recusada em `mctf_mask` e `QC`; eventos pós-`Cancel` ignorados; `Pass end` = 100%; Pass 1 visível no Pass 2; classificação WARNING; `—` para campos ausentes; mapeamento exit code → tela.
2. **Snapshots de texto** (`ui/tui/test_screens.py`): cada tela renderizada de um `UIState` fixo em console de gravação 120×40; textos-chave da spec ("READY TO ENCODE", "MASTER QC", "★ DELIVERY READY ★", "⚠ REVISAR ENTREGA ⚠", `░[C]`, "PASS 1 / 2"); nenhuma linha > 120 colunas; nenhum caractere de categoria `So` fora dos glifos permitidos do tema nas regiões fixas; aviso de terminal pequeno.
3. **Teclado** (`ui/tui/test_keys.py`): mapeamento de bytes → `Key` (inclui setas estendidas e ESC isolado), por funções puras; a leitura real não é testada no CI.
4. **Ponta a ponta sem terminal** (`ui/tui/test_app.py`): `App` com `Live` em console de gravação e `run_single`/`_encode_single_file` falsos (padrão de `ui/test_tui_driver.py`); teclas injetadas na fila; sequência de telas e código para sucesso (0), erro (1), `C` (130), Ctrl+C (130), ESC no READY (0); restauração de `sys.stderr` e do console mesmo com exceção.
5. **Guarda do terminal** (`ui/tui/test_main.py`): não-TTY ou < 120×40 → chama `RE.main` (monkeypatch); `run_launcher` → None → 0.
6. **Manual no Windows Terminal** (roteiro no scratchpad, padrão B-3/B-4): critério 2 de §1.

## 9. Fora de escopo

HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW (P3C); BATCH QUEUE / RESULT (P3D); aba no `launcher.ps1`, paridade final CLI × TUI, passada de glifos/cores/Tools (P3E); bitrate (D-13); novo encode no mesmo processo (D-19); qualquer mudança no encoder, no condutor P3A ou no wizard.
