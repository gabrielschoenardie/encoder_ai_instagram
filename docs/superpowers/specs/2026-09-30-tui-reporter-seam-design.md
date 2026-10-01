# B-4 — Canal Encoder → TUI (Reporter seam) — Design

Data: 2026-09-30 · Status: aprovado em conversa, aguardando revisão do arquivo
Origem: Phase 2 Sign-off, blocker B-4. Referências: `docs/Phase_2_TUI_Specification.md` §AA, §AB, §AD, §AF, §AG.
`RE` = `Reels_Encoder_v2_FINAL.py`; linhas do snapshot `main` @ `e54bae2`.

## 1. Objetivo e critério de sucesso

Definir o contrato pelo qual o encoder informa a TUI, para a Phase 3 implementar sem decidir arquitetura.

Sucesso:

1. Com `reporter=None`, o CLI clássico e o line wizard produzem saída de console e argv FFmpeg **byte a byte idênticos** ao baseline.
2. A TUI recebe tudo o que desenha por eventos imutáveis numa fila; nunca lê objetos do encoder entre threads.
3. Nenhuma mudança semântica no encoder (Sign-off §8; prompt §5).

## 2. Decisões fechadas neste design

| ID | Decisão |
|----|---------|
| S-1 | Migração em duas etapas (opção **C**). **V1**: só dados que viram painel passam pelo reporter; `console.print` existentes ficam no código. **Etapa 2** (ciclos futuros, um arquivo/área por ciclo, cada um com golden): frases migram para `info`/`warning` com etiqueta. |
| S-2 | Sem `ConsoleReporter`. `reporter=None` é o comportamento atual; não existe objeto que reimprime. |
| S-3 | No modo TUI, a captura do console remove marcação Rich e **emoji/símbolos** antes de mostrar no LOG. |
| S-4 | Com reporter, o encoder não abre `Live`/HUD próprio; o objeto HUD continua contando e o reporter recebe cópia dos contadores. |
| S-5 | Batch da TUI tem condutor próprio sobre `render_queue`; o bloco batch de `main()` não é tocado. |
| S-6 | `C` desligada nas etapas `mctf_mask` e `QC`; Ctrl+C sempre ativo (D-10, D-11, D-22). |

## 3. Peças

```text
 CLI clássico / wizard                          TUI
 chama o encoder SEM reporter                   chama o encoder COM QueueReporter
          │                                              │
          ▼                                              ▼
 ┌──────────────────────────── ENCODER (o mesmo) ─────────────────────────────┐
 │ reporter is None → caminho atual, linha por linha                          │
 │ reporter set     → sem Live/HUD próprio; reporter.emit(evento) nos pontos  │
 └────────────────────────────────────────────────────────────────────────────┘
                                                         │ eventos
                                                         ▼
                                                 queue.Queue ──► tela da TUI
```

1. **`reporter.py`** (raiz, ao lado de `render_queue.py`): dataclasses `frozen=True` dos eventos, cada uma com `job_id: int` (0 em single-file) e `ts: float` (`time.monotonic()`, preenchido pelo reporter); classe `QueueReporter(queue)` com `emit(event)`. Não importa nada de `ui/` nem de `RE`.
2. **Parâmetro `reporter=None`** em: `_encode_single_file`, `run_ffmpeg`, `run_ffmpeg_with_cineon`, `_run_encoding`, `_render_pass` (Cineon), `run_post_encode_qc`. Cada chamada nova é guardada por `if reporter is not None:`. `generate_mctf_mask_video` **não** recebe reporter: o `Stage` da máscara é emitido por `_encode_single_file`, e no modo TUI a chamada usa o parâmetro existente `show_progress=False` (o mesmo que o batch já passa, `RE:4074`), para a barra de progresso da máscara não ir para a captura.
3. **Captura do console** (§6).
4. **Três threads** (spec §AD; validado no B-3): principal (única dona da tela; recebe Ctrl+C), teclado (`msvcrt.getwch`, não consome Ctrl+C — B-3 T1–T5), encode (nunca escreve no terminal).

Inalterado: argv FFmpeg, pipes e threads de leitura de stderr, `_ACTIVE_FFMPEG`, `terminate_active_ffmpeg`, `discard_partial_output`, cleanup, exit codes, handlers `except KeyboardInterrupt`.

## 4. Eventos (V1)

| Evento | Campos | Emissor · momento | Consumidor TUI |
|--------|--------|-------------------|----------------|
| `Stage` | `name`, `substep: str \| None` | ao entrar em cada etapa (§4.1) | trilha do cabeçalho, LOG SYSTEM, regra de `C` |
| `Hardware` | os 17 campos de `HardwareProfile` (`RE:394–413`) | após `detect_hardware` (native `RE:2520`, Cineon `RE:3248`) | PERFORMANCE, DETAILS |
| `Probe` | `duration`, `total_frames`, `fps`, `width`, `height`, `is_hdr` | após `probe_video` (`RE:2564`, `RE:3208`) | TIMELINE, DETAILS |
| `EncodeParams` | `vbv_key`, `target`, `maxrate`, `bufsize`, `vbv_init`, `x264_preset`, `mode` | após `get_vbv_preset` (`RE:2717`, `RE:3326`) | DETAILS (CALCULATED) |
| `Pass` | `index`, `total`, `label`, `phase: "start" \| "end"` | em volta de cada passe | trilhas de passe (D-12) |
| `Progress` | `frame`, `total`, `fps`, `speed`, `eta`, `elapsed` | onde hoje há `live.update(hud.render())`; ≤ 10 Hz | barras, TIMELINE |
| `FfmpegLine` | `line` | mesmas threads de stderr (`RE:2055`, `RE:3597`), mesma linha que vai para o deque | LOG FFMPEG |
| `Info` | `text` | coletor da captura (§6) | LOG INFO |
| `Qc` | payload já montado por `run_post_encode_qc` | fim do QC | QC, DELIVERY |
| `Done` | `output_path`, `seconds` | fim de `_encode_single_file` | COMPLETED |
| `Error` | `kind`, `message`, `stderr_tail`, `returncode`, `traceback` | onde o erro já é tratado; wrapper da thread de encode (§7) | ERROR |
| `Cancel` | `phase: requested \| terminated \| cleaned`, `partial_removed: bool` | handlers de interrupção e cancelamento da TUI | CANCEL / CANCELLED |
| `QueueInit` / `JobStart` / `JobSkip` / `JobDone` / `QueueDone` | lista de jobs; índice; motivo; `status`+resultado; resumo | condutor batch da TUI (§8) | BATCH QUEUE, RESULT (D-18) |

Regras: eventos são cópias imutáveis; campo sem dado no momento fica `None` (D-13); nenhum marcador de fallback inventado (duração 30 s continua sem flag — Sign-off #11).

### 4.1 Ordem de `Stage` (auditada — Sign-off #7)

```text
NATIVE : PREPARING → [ANALYZING·preflight] → [ANALYZING·mctf_mask] → PROBING → ANALYZING·enhance
         → ANALYZING·loudness → PASS 1 → BETWEEN_PASSES·pass1_log → PASS 2 → QC → DONE
CINEON : PREPARING → [ANALYZING·preflight] → [ANALYZING·mctf_mask] → PROBING → ANALYZING·loudness
         → ANALYZING·enhance → PASS 1 → BETWEEN_PASSES·pass1_log → PASS 2 → FINALIZING·remux → QC → DONE
```

CRF: um passe, sem `BETWEEN_PASSES`. `ANALYZING·mctf_mask` só com MCTF ativo, emitido em `_encode_single_file` antes de `generate_mctf_mask_video` (`RE:4070`); o `Stage` seguinte encerra o período. A TUI renderiza na ordem de chegada, sem ordem fixa (spec §128).

## 5. HUD → `Progress`

Em `_run_encoding` (`RE:2059`) e no loop Cineon (`RE:3613`):

```text
sem reporter (hoje)                      com reporter
with Live(hud.render()) as live:         (sem Live)
  loop: live.update(hud.render())        loop: reporter.emit(Progress(<cópia dos contadores do HUD>))
```

Leitura de stderr, parsing, ETA e o objeto HUD não mudam. `is_batch` continua suprimindo o que suprime hoje (`RE:4074`, `RE:4146`).

## 6. Captura do console (modo TUI)

1. Antes de iniciar a thread de encode, a TUI troca o destino de saída do `console` global de `RE` (`RE:163`) por um coletor e guarda o original.
2. Limpeza, em ordem: (a) texto sem marcação/ANSI (coletor configurado sem cor); (b) remove caracteres Unicode de categoria `So` (outros símbolos: emoji, `✓`, `⚠`, `─`), variation selectors (U+FE0E/U+FE0F) e ZWJ (U+200D); (c) colapsa espaços; (d) descarta linhas vazias.
3. Cada linha limpa → `Info` na fila.
4. Restauração do destino original em `finally`, sempre (sucesso, erro, Ctrl+C, cancelamento).
5. A tela da TUI usa um `Console` próprio, nunca o de `RE`.

## 7. Thread de encode e erros

A função que roda o encode na thread captura `BaseException` exceto `KeyboardInterrupt` (que só chega na principal) e emite `Error` com traceback. Exit codes iguais ao clássico (Sign-off #15): sucesso 0; erro 1; Ctrl+C 130; validação 2 só se não recuperável na UI.

Single-file na TUI reproduz `RE:4613–4645`: `output_preexisted` medido antes; no Ctrl+C, `terminate_active_ffmpeg()`, `discard_partial_output` só se `not output_preexisted` (D-11 — inclusive durante QC), mesmas mensagens como `Cancel`/`Info`, exit 130.

## 8. Batch na TUI

- Bloco batch de `main()` (`RE:4479–4590`) intocado.
- Condutor da TUI reusa: `find_video_files`, a mesma regra de skip de output existente (`RE:4551`), `render_queue.QueueJob`, `render_queue.run_job(job, encode_fn, console, on_tick)` (`render_queue.py:144`), `discard_partial_output`.
- A thread principal chama `run_job`; `on_tick` esvazia a fila e redesenha. `KeyboardInterrupt` chega à principal dentro de `run_job` (`render_queue.py:172–185`), como no clássico.
- Ctrl+C: `terminate_active_ffmpeg()` e `discard_partial_output(job)` do job corrente sem checar pré-existência (D-11), exit 130.
- Exit: 0 sem vídeos (`RE:4488`); 1 se algum `falha`; 0 se todos ok; 130 interrompido.

## 9. Tecla `C`

```text
C → modal → Confirmar → flag cancel_requested = True → terminate_active_ffmpeg()
  → encode termina com erro → wrapper vê cancel_requested → classifica como Cancel (não Error)
  → mesma limpeza do Ctrl+C (§7 / §8) → exit 130
```

Alcance = o de `terminate_active_ffmpeg()`: encode native, Cineon pass 1 e 2, remux, loudnorm. `C` desligada (`░[C]`) com `Stage` `ANALYZING·mctf_mask` ou `QC`. Ctrl+C nunca abre modal (D-10).

## 10. Testes

1. **Golden antes da mudança** (lavfi curto): saída de console + argv FFmpeg para CRF, 2-pass, Cineon CRF, Cineon 2-pass. Após o seam, com `reporter=None`, byte a byte idênticos.
2. **Sequência de eventos** por modo conforme §4.1, incluindo `mctf_mask` com MCTF ativo.
3. **Captura**: remove marcação e `So`/VS/ZWJ, descarta vazias, restaura em exceção.
4. **Paridade**: mesma config via clássico e via caminho TUI → mesmo argv; com threads fixas, mesmo hash do output.
5. **Windows Terminal manual**: T1–T5 do B-3 com encode real pela TUI.

Todos os testes usam `tmp_path`; nada na raiz do repo.

## 11. Fora de escopo

Telas da TUI (HOME … ERROR), foco, teclado além de D/L/C, geometria 120×40, etapa 2 da migração (S-1), reuso de processo (D-19), registro dos processos da máscara MCTF em `_ACTIVE_FFMPEG` (D-22).
