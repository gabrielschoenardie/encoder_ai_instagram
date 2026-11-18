# Reels Encoder — Phase 2: TUI Interaction + Visual Specification

> **Documento histórico (Fase 2, 28/09/2026).** Especificação de design anterior à implementação. Onde diverge do comportamento atual, os requisitos abaixo **não** valem; **a implementação atual prevalece** — guia de uso em [`tui.md`](tui.md). Diferenças conhecidas:
>
> | Especificação (histórica) | Comportamento atual |
> |---|---|
> | Canvas exclusivo de 120 × 40; SIZE GUARD abaixo disso (§G, §W, D-02) | Mínimo **80×24** com layout compacto; layout completo a partir de **120×40**; abaixo de 80×24, aviso "amplie para 80×24" |
> | Tecla `C` + modal CANCELAR ENCODE? (§E, §S, D-09, D-10, D-11) | Sem tecla `C` nem modal: **Ctrl+C** é a única interrupção (master mantido no QC; parcial removido no PASS) |
> | SIZE GUARD com `[ESC] usar o wizard clássico`; wizard de linha como fallback (§A, §AC) | **Menu clássico retirado**; fora dos requisitos de terminal a TUI sai com erro e código 1 |
> | Sem "Novo encode" na v1 (§V, D-19) | **NOVO ENCODE** (`N`) nas telas finais |
>
> Os caminhos de exemplo nos wireframes são ilustrativos.

Repo `gabrielschoenardie/encoder_ai_instagram` @ `main` · 2026-09-28 · specification only. The repository was not modified; this document lives in the design project.
Source of truth for current behaviour: `Phase_1_Technical_Audit.md` (Phase 1), plus direct reads of `ui/config.py`, `ui/launcher.py`, `ui/dashboard.py`, `render_queue.py`, `ebu_meter.py`.

**Canvas:** 120 columns × 40 rows, exclusively. No other layouts are specified.

### Conventions used in this document

| Tag | Meaning |
|:--|:--|
| `[EXISTING]` | Supported by the current code today. |
| `[DERIVED]` | Displayable from data the code already computes, with no change to encoding behaviour. |
| `[NEW UI ONLY]` | New presentation/interaction; engine untouched. |
| `[REQUIRES ENGINE SEAM]` | Needs a Reporter/Event hook in Phase 3 (additive, default-preserving). |
| `[NOT CURRENTLY SUPPORTED]` | Would need new engine functionality. Never shown as available. |
| `NEEDS REVIEW` | The codebase does not give enough information. Must be resolved before implementing that item. |

**Wireframe notation.** Wireframes are drawn at exactly 120 × 40. Values inside them are illustrative (a 60 s, 1800-frame, 1080×1920 source); only the labels, structure and data sources are normative.

| Mark | Rendering |
|:--|:--|
| `▎▸ text` | **Focused** element: whole row in `tab.active` style (bold ink `#13141a` on indigo `#5b6cff`). |
| `▎Name` in a rail/tab bar | **Active** tab/step (same `tab.active` style, no `▸`). |
| `●` / `○` | Selected / unselected option. |
| `░[X]` | Disabled key or control (muted, dim). |
| `⠹` | Braille spinner, violet (`accent`). |
| `▓` / `█` / `░` | Pass 1 fill / Pass 2 or single-pass fill / empty track. |
| `↻ ×N` | N consecutive FFmpeg stat lines collapsed into one row (display only). |

---

## A. Design Principles

1. **The encoder is the source of truth.** The TUI edits an `EncodeConfig`, hands `to_namespace()` to the engine, and renders events. It holds no encoding logic.
2. **Preserve the Premiere workspace.** Same palette, named styles, box vocabulary (`ROUNDED` panels, `DOUBLE` hero/MASTER QC, `SIMPLE` strips), uppercase left-aligned panel titles, letter-spaced headlines, job strip → progress header → Program/Timeline/Performance → Log hierarchy.
3. **One screen, one owner.** One full-screen render loop. No nested `Live`. No engine writes to the screen in TUI mode.
4. **Keyboard-first, always legible focus.** Exactly one focused element per screen, shown by shape (`▎▸`) and colour, never by hover.
5. **Show only what the engine knows.** Every value in DETAILS carries its provenance (CFG / DET / CALC / LIVE / QC). Missing data renders as `—`, never as a guess.
6. **User choice vs engine automation stays visible.** Preset-fixed values, user choices, defaults and engine automation are rendered in separate, labelled regions.
7. **Diagnostics are never reduced.** FFmpeg stderr stays complete and raw where it matters (LOG, ERROR). Display-level collapsing never touches the stored buffers.
8. **Additive.** Classic CLI and line wizard are untouched and remain the fallback.
9. **Quiet motion.** Motion is limited to what exists today: braille spinner, bar pulse sweep, and the 1.2 s seal reveal. Screen changes are instant.

## B. Information Architecture

```text
TUI
├── HOME ─────────────── preset menu (1–5) · SYSTEM readiness
│   ├── 1 Encode rápido (FFmpeg) ─┐
│   ├── 2 Film look (Cineon) ─────┤→ SOURCE (file) → CONFIGURATION (preset fields)
│   ├── 3 Batch de pasta ─────────┘→ SOURCE (folder) → CONFIGURATION (batch fields)
│   ├── 4 Tools (utilitários) ───→ FERRAMENTAS submenu → suspended terminal → HOME
│   └── 5 Configurar avançado… ──→ SOURCE (file|folder) → ADVANCED CONFIGURATION (5 tabs)
├── PREVIEW ───────────── verification (REVISAR → ADVANCED CONFIGURATION with current config)
├── READY TO ENCODE ───── final review · START ENCODE
├── ENCODING (single)             ├── BATCH QUEUE (batch)
│   ├── DETAILS  [D]              │   ├── DETAILS [D] of selected job
│   ├── LOG      [L]              │   ├── LOG [L] of selected job
│   └── CANCEL   [C] (modal)      │   └── CANCEL [C] (modal, whole queue)
├── QC / DELIVERY ─────── live post-encode QC (single)
├── COMPLETED ─────────── single: ENCODE COMPLETE · batch: FILA — RELATÓRIO FINAL
└── ERROR ─────────────── ENCODING / DEPENDENCY / VALIDATION / CANCELLED
Guards: SIZE GUARD (terminal < 120×40) · TOOLS suspension
```

The flow rail in row 2 of every screen shows the conceptual flow `HOME › SOURCE › CONFIG › PREVIEW › READY › ENCODE › QC › DELIVERY` (batch: `… READY › QUEUE › REPORT`). It is a position indicator, not navigable.

## C. Screen Map

| # | Screen | Reached from | Leaves to | Tags |
|:-:|:--|:--|:--|:--|
| 1 | HOME | TUI start, COMPLETED/ERROR (NEEDS REVIEW, see V) | SOURCE, FERRAMENTAS, exit | `[EXISTING]` flows, `[NEW UI ONLY]` layout |
| 2 | SOURCE | HOME | CONFIGURATION / ADVANCED, HOME | `[EXISTING]` validation |
| 3 | CONFIGURATION | SOURCE (presets 1–3) | PREVIEW, SOURCE | `[EXISTING]` fields |
| 4 | ADVANCED CONFIGURATION | SOURCE (preset 5), PREVIEW → REVISAR | PREVIEW, back | `[EXISTING]` `_flow_advanced` fields |
| 5 | PREVIEW | CONFIGURATION, ADVANCED | READY, ADVANCED | `[EXISTING]` `settings_preview` |
| 6 | READY TO ENCODE | PREVIEW | ENCODING / BATCH QUEUE, PREVIEW | `[DERIVED]` + `[NEW UI ONLY]` |
| 7 | ENCODING | READY | QC, ERROR, CANCELLED | `[REQUIRES ENGINE SEAM]` |
| 8 | ENCODING DETAILS | ENCODING / QUEUE `[D]` | back `[D]`/`[ESC]` | `[DERIVED]` + seam |
| 9 | ENCODING LOG | ENCODING / QUEUE `[L]` | back `[L]`/`[ESC]` | `[EXISTING]` stderr deque + seam |
| 10 | CANCEL CONFIRMATION | ENCODING / QUEUE `[C]` | ENCODING (keep) / CANCEL_REQUESTED | `[EXISTING]` cancel path + seam |
| 11 | COMPLETED | QC (single), QUEUE end (batch) | exit | `[EXISTING]` payload + seam |
| 12 | QC / DELIVERY | ENCODING | COMPLETED | `[EXISTING]` `run_post_encode_qc` + seam |
| 13 | ERROR | any engine failure, preflight, validation, cancel | exit / CONFIGURATION (validation only) | `[EXISTING]` diagnostics |
| 14 | BATCH QUEUE | READY (batch) | COMPLETED (report), ERROR | `[EXISTING]` `QueueJob` + seam |

## D. State Machine

### D.1 Application (screen) states

```text
                 ┌──────────────── ESC ────────────────┐
HOME ──ENTER──► SOURCE ──valid──► CONFIG|ADVANCED ──► PREVIEW ──► READY ──START──► RUN
 ▲  │ 4                                ▲      REVISAR   │                          │
 │  └► TOOLS (suspended) ──────► HOME  └───────────────┘                          ▼
 │                                                          RUN = ENCODING job states (D.2)
 └── ESC on HOME = exit TUI ("Cancelado pelo usuário.")          or BATCH QUEUE (D.3)
```

### D.2 Encoding job states

```text
PREPARING ─► PROBING ─► ANALYZING ─► ENCODING ─────────────────────► QC ─► COMPLETED
                                     │ crf:    SINGLE PASS
                                     │ 2pass:  PASS 1 ─► BETWEEN_PASSES ─► PASS 2
                                     │ Cineon: FILM RENDER (crf)  or  PASS 1 ─► PASS 2 (2pass)
 any state before QC ── C + confirm ──► CANCEL_REQUESTED ──► CANCELLED
 any state before QC ── Ctrl+C ───────► CANCEL_REQUESTED ──► CANCELLED   (existing path)
 any state ── exception ──────────────► ERROR
```

| State | Entered when | Source today | Visual |
|:--|:--|:--|:--|
| PREPARING | worker starts `_encode_single_file` | hardware detection inside pipelines (audit H#10) | spinner, rail step active |
| PROBING | duration/frames/fps/resolution/HDR probes | `get_video_duration`, `get_total_frames`, `get_input_fps`, `detect_hdr_metadata` | spinner |
| ANALYZING | enhance analysis, AI preflight heatmaps, MCTF mask, loudnorm measurement — each only if enabled | `_encode_single_file`, `run_ffmpeg*`, `analyze_audio_loudness` | spinner + sub-step name |
| SINGLE PASS / FILM RENDER | `_run_encoding` (crf) or Cineon frame loop | existing | `█` bar, % , ETA |
| PASS 1 | first `_run_encoding` call in 2pass | existing | `▓` bar, label ANÁLISE |
| BETWEEN_PASSES | `_analyze_pass1_log` + `_adaptive_2pass_x264_params` | existing | indeterminate spinner, no % |
| PASS 2 | second `_run_encoding` call | existing | `█` bar, label ENCODE FINAL |
| QC | `run_post_encode_qc` | existing | sub-steps, seal reveal |
| COMPLETED | QC returns | existing | DOUBLE hero |
| CANCEL_REQUESTED | user confirmed C, or Ctrl+C received | new UI state over existing path | amber `⚠` banner in header |
| CANCELLED | worker exited after interrupt and partial-output handling | existing messages | amber CANCELLED card |
| ERROR | `CalledProcessError` or other exception | existing | red ERROR screen |

State names are driven by `stage` events (AA). The TUI never infers a stage from timing. The exact order of sub-steps inside ANALYZING is **NEEDS REVIEW** (the audit did not trace `run_ffmpeg` line by line); the TUI renders sub-steps in the order events arrive and does not hard-code them.

### D.3 Batch states

Queue: `LISTING → RUNNING → FINISHED | INTERRUPTED`. Jobs map 1:1 to `QueueJob.status`:

| `QueueJob.status` | Display | Glyph (existing `STATUS_SYMBOLS`) |
|:--|:--|:--|
| `aguardando` | QUEUED | `·` |
| `processando` | ENCODING | `⏳` in the table today; TUI uses the braille spinner (emoji is double-width) |
| `ok` | COMPLETED | `✓` |
| `pulado` | SKIPPED | `○` |
| `interrompido` | CANCELLED | `⚡` |
| `falha` | FAILED | `✗` |

## E. Keyboard Interaction Model

Global rules: keys act on the focused element; there are no hidden keys; the footer (row 39) lists every active key for the current screen; mouse input is ignored.

| Key | Wizard screens (HOME → READY) | ENCODING / QUEUE | DETAILS / LOG | Modals & result screens |
|:--|:--|:--|:--|:--|
| `↑` `↓` | move focus between fields/items | QUEUE: select job | LOG: scroll · DETAILS: — | ERROR: scroll stderr |
| `←` `→` | change value of focused field · switch tab when tab bar focused · move between buttons · move text cursor in a path field | — | LOG: switch filter | move between buttons |
| `ENTER` | activate / continue / validate path | — | — | activate focused button |
| `ESC` | back one screen · on HOME: exit TUI | — | return to dashboard | CANCEL modal: keep encoding |
| `SPACE` | toggle on/off field | — | — | — |
| `1`–`5` | HOME only: focus and open that flow (mirrors today's typed number) | — | — | — |
| `D` | — | open DETAILS | toggle back | — |
| `L` | — | open LOG | toggle back | — |
| `C` | — | open CANCEL modal | open CANCEL modal | — |
| `Ctrl+C` | existing wizard cancel ("Cancelado pelo usuário.") | existing interrupt path | existing interrupt path | existing interrupt path |
| printable chars | typed into focused path/number field | ignored | ignored | ignored |

**Encoding hotkeys are exactly `D`, `L`, `C`, `Ctrl+C`.** Footer text during encoding: `[D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt`. When DETAILS or LOG is open, its key is shown in the active style (`▎[D]`). No pause, resume, quit, skip-job or priority keys exist.

**Ctrl+C is never consumed as a key.** The key reader must leave signal generation enabled (POSIX: `ISIG` on / cbreak, not raw; Windows: processed input on) so SIGINT / `CTRL_C_EVENT` reach the existing handlers. Verification of this on Windows Terminal is **NEEDS REVIEW** (see AF).

## F. Focus Model

- Exactly one focused element per screen. Focus is shown by `▎▸` and the `tab.active` style across the full row of the element. Colour is never the only cue.
- Focus order is top-to-bottom, left-to-right within a panel; panels are visited in reading order. Read-only regions (FIXADO PELO PRESET, PADRÕES, ENGINE AUTOMATION, SETTINGS summary, SYSTEM) are never focusable.
- Disabled fields are skipped by `↑`/`↓`.
- Focus is restored when returning to a screen (per-screen `focus_id` in UIState).
- In tabbed ADVANCED CONFIGURATION, focus has two levels: tab bar or field list. `↑` on the first field moves to the tab bar; `↓` from the tab bar enters the first enabled field.

| Screen | Default focus |
|:--|:--|
| HOME | preset 1 (matches `ask_choice(..., default=1)`) or last used preset in this session |
| SOURCE | path field |
| CONFIGURATION | first editable field |
| ADVANCED CONFIGURATION | first enabled field of the Source tab |
| PREVIEW | CONTINUAR ▶ READY (default of today's "Iniciar encode?" is yes) |
| READY | START ENCODE |
| ENCODING | global action state (no focusable element; hotkeys only) |
| BATCH QUEUE | the ENCODING job; follows the active job until the user moves focus |
| QC / DELIVERY | no focusable element while CHECKING |
| COMPLETED | SAIR |
| ERROR | SAIR |
| CANCEL modal | CONTINUAR ENCODE (the safe option) |

| Element state | Representation |
|:--|:--|
| focused | `▎▸` + bold ink on indigo, full row |
| selected (option chosen, not focused) | `●` indigo + bold `text` |
| unselected option | `○` muted |
| disabled | muted text, value shown, reason on the line below in `label` style, skipped by focus |
| processing | violet braille spinner before the label |
| active tab | `▎Name` in `tab.active` |
| inactive tab | `Name` muted |
| focused tab bar | active tab gets `▸` as well: `▎▸Name` |

## G. 120 × 40 Layout System

```text
row  1        HEADER  identity ("REELS ENCODER  v2.1.0") left · global status right
row  2        HEADER  flow rail
row  3        HEADER  ─ rule (SIMPLE)
rows 4–37     MAIN    34 rows × 118 columns (1-column margin left and right)
row 38        FOOTER  ─ rule
row 39        FOOTER  key hints for the current screen
row 40        FOOTER  message line (notifications, provenance legend, inline hints)
```

- No outer frame: the three strips replace it and save 2 columns and 2 rows.
- Columns: full width 118; two-up 58 + 2 + 58; workstation split 72 + 2 + 44 or 76 + 2 + 40; three-up 38 + 2 + 38 + 2 + 38; dashboard 30 + 1 + 43 + 1 + 43.
- Panel padding: `(0, 1)` inside all TUI panels (the wizard's `(1, 2)` would cost 4 rows per panel at 40 rows).
- Paths are middle-elided with the existing `_short_path` rule, adapted to the available width.
- The background is not painted (as today); `ink` is used only as text colour on indigo.
- Emoji glyphs (`🎞 🎧 ✨`) are not used in fixed-width TUI regions (double-width); existing ASCII/Unicode glyph tables from `theme.glyphs()` are used instead.

---

## H. HOME

- **Purpose:** entry point; choose one of the five existing flows.
- **User goal:** start the right flow, confirm the system is ready.
- **Layout:** DOUBLE banner (7 rows) · menu 58 × 17 | selected-flow description 58 × 17 · SYSTEM strip 118 × 5.
- **Hierarchy:** banner → menu (focus) → description of focused flow → readiness.
- **Components:** `banner` `[EXISTING]`; menu list `[NEW UI ONLY]` using the existing labels from `PRESETS` verbatim; flow description `[DERIVED]` from preset factories and `EncodeConfig.output_path` rules; SYSTEM strip `[DERIVED]` from `ui.binaries` / `ui.preflight.missing_ffmpeg_binaries` and terminal size. Hardware is shown as "detectado no início do encode" because detection runs inside the pipelines today (audit H#10) — no early detection call.
- **Focus:** preset 1. **Keys:** `↑↓` `ENTER` `1–5` `ESC`.
- **States:** normal; ffplay missing → `⚠ ffplay` (optional, meters skipped, as today); ffmpeg/ffprobe missing → DEPENDENCY ERROR (W) instead of HOME; terminal smaller than 120 × 40 → SIZE GUARD.
- **Transition in:** TUI start (after preflight). **Out:** ENTER/1–5 → SOURCE, or FERRAMENTAS for 4; ESC → exit TUI with the existing "Cancelado pelo usuário." message after the screen is restored.

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ▎HOME      SOURCE     CONFIG     PREVIEW     READY     ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
 ║                                                                                                                    ║
 ║   R E E L S   E N C O D E R                                                                                        ║
 ║                                                                                                                    ║
 ║   Premiere Workspace · UI interativa · v2.1.0                                                                      ║
 ║                                                                                                                    ║
 ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

 ╭─ SELECIONE UM FLUXO ───────────────────────────────────╮  ╭─ FLUXO · ENCODE RÁPIDO (FFMPEG) ───────────────────────╮
 │                                                        │  │                                                        │
 │ ▎▸ 1   Encode rápido (FFmpeg)                          │  │ FFmpeg native · Hollywood LUT                          │
 │                                                        │  │                                                        │
 │    2   Film look (Cineon)                              │  │ fixado pelo preset   cineon off · mode crf · lut on    │
 │                                                        │  │ você escolhe         Enquadramento · FPS · Modo        │
 │    3   Batch de pasta                                  │  │                                                        │
 │                                                        │  │ saída crf            <nome>_Hollywood_CRF18.mp4        │
 │    4   Tools (utilitários)                             │  │ saída 2pass          <nome>_Hollywood_2Pass.mp4        │
 │                                                        │  │                                                        │
 │    5   Configurar avançado…                            │  │ engine decide        VBV por duração · hardware tier   │
 │                                                        │  │                      lookahead · alvo de loudness      │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 ╰────────────────────────────────────────────────────────╯  ╰────────────────────────────────────────────────────────╯

 ╭─ SYSTEM ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓ ffmpeg   bin\ffmpeg.exe          ✓ ffprobe  bin\ffprobe.exe          ✓ ffplay  bin\ffplay.exe  (opcional)        │
 │ ✓ terminal 120 × 40                ● glyphs   Unicode                 ● hardware  detectado no início do encode    │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯



────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [↑↓] Navigate   [ENTER] Select   [1–5] Jump   [ESC] Exit

```

**FERRAMENTAS (option 4).** Same layout, menu replaced by the existing `TOOLS` list + "Voltar". ENTER suspends the TUI (leave full-screen, restore cooked input), runs the tool exactly as `_flow_tools` does (`subprocess.run`, cwd repo root, "Pressione Enter para continuar"), then resumes on FERRAMENTAS. `[EXISTING]` behaviour, `[NEW UI ONLY]` suspension.

```text
╭─ FERRAMENTAS ──────────────────────────────────────────╮
│                                                        │
│ ▎▸ 1   Verificador de instalação                       │
│    2   Comparar frames (interativo)                    │
│    3   Timestamp → frame (interativo)                  │
│    4   Limpar cache                                    │
│    5   Voltar                                          │
│                                                        │
│ ENTER suspende a TUI e executa a ferramenta            │
│ no terminal; volta após "Pressione Enter"              │
│                                                        │
│                                                        │
│                                                        │
╰────────────────────────────────────────────────────────╯
```

## I. SOURCE

- **Purpose:** pick the input file (presets 1, 2) or folder (preset 3); preset 5 also chooses the type, mirroring "É um batch de pasta?".
- **User goal:** a valid source and a clear view of where output will go.
- **Layout:** SOURCE panel 76 × 26 | PROGRAM 40 × 26 · PRÓXIMO strip 118 × 4.
- **Components:** type selector (enabled only for preset 5) `[EXISTING]`; path field `[NEW UI ONLY]` with the existing quote-stripping; status `[EXISTING]` existence check; metadata `[DERIVED]` from `probe_source_dims` (dimensions only); PROGRAM via `viewer_frame` `[EXISTING]`; output name `[DERIVED]` from `EncodeConfig.output_path`; batch count `[DERIVED]` from `find_video_files`.
- **No new analysis:** duration, fps and HDR are not probed here; they appear during PROBING.

| Validation state | When | Visual |
|:--|:--|:--|
| `CHECKING` | after ENTER while the existence check and `probe_source_dims` run (off the UI thread) | `⠹ CHECKING` violet |
| `VALID` | path exists (file for 1/2/5-file, folder for 3/5-folder) | `✓ VALID` green |
| `NOT FOUND` | path does not exist (today `ask_path` re-prompts) | `✗ NOT FOUND` red, focus stays in field |
| `INVALID` | empty after quote stripping, or wrong kind (folder given for a file) | `✗ INVALID` red — whether today's `ask_path`/`ask_folder` distinguish the kind: **NEEDS REVIEW** |

`probe_source_dims` failing is not an error (it is best-effort today): status stays VALID, metadata shows `—`, PROGRAM shows the fallback frame. Batch folder with 0 videos: behaviour of the current batch path is **NEEDS REVIEW**; the TUI shows `⚠ nenhum vídeo encontrado` and does not invent a rule to block.

- **Focus:** path field. **Keys:** typing, `←→` cursor, `ENTER` validate → continue when VALID, `↑↓` between type selector and path (preset 5), `ESC` back.
- **Transition in:** from HOME. **Out:** VALID + ENTER → CONFIGURATION (1–3) or ADVANCED (5); ESC → HOME.

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ✓ HOME   ▎SOURCE      CONFIG     PREVIEW     READY     ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

 ╭─ SOURCE · ENCODE RÁPIDO (FFMPEG) ────────────────────────────────────────╮  ╭─ PROGRAM ────────────────────────────╮
 │                                                                          │  │                                      │
 │ TIPO        ● Arquivo único     ○ Pasta (batch)     fixado pelo fluxo    │  │          ┌────────────────┐          │
 │                                                                          │  │          │                │          │
 │ CAMINHO                                                                  │  │          │                │          │
 │ ▎ C:\Users\gabriel\Videos\reels\clip_final.mov▏                           │  │          │                │          │
 │   aspas externas são removidas · ENTER valida                            │  │          │                │          │
 │                                                                          │  │          │                │          │
 │ STATUS      ✓ VALID       arquivo encontrado                             │  │          │                │          │
 │                                                                          │  │          │                │          │
 │ METADADOS   1080 × 1920 · portrait 9:16                                  │  │          │      9:16      │          │
 │                                                                          │  │          │                │          │
 │ SAÍDA       C:\Users\gabriel\Videos\reels\clip_final_Hollywood_CRF18.mp4 │  │          │                │          │
 │             muda com Modo (crf / 2pass)                                  │  │          │                │          │
 │                                                                          │  │          │                │          │
 │                                                                          │  │          │                │          │
 │                                                                          │  │          │                │          │
 │                                                                          │  │          └────────────────┘          │
 │                                                                          │  │                                      │
 │                                                                          │  │          source 1080 × 1920          │
 │                                                                          │  │               contain                │
 │                                                                          │  │                                      │
 │                                                                          │  │                                      │
 │                                                                          │  │                                      │
 │                                                                          │  │                                      │
 ╰──────────────────────────────────────────────────────────────────────────╯  ╰──────────────────────────────────────╯

 ╭─ PRÓXIMO ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ CONFIG · Encode rápido (FFmpeg) → Enquadramento · FPS · Modo                                                       │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [type] Path   [ENTER] Validate / Continue   [↑↓] Field   [ESC] Back

```

Batch variant (main region, left panel only):

```text
╭─ SOURCE · BATCH DE PASTA ────────────────────────────────────────────────╮
│                                                                          │
│ TIPO        ○ Arquivo único     ● Pasta (batch)     fixado pelo fluxo    │
│                                                                          │
│ PASTA                                                                    │
│ ▎ C:\Users\gabriel\Videos\reels▏                                          │
│                                                                          │
│ STATUS      ✓ VALID       12 vídeos encontrados                          │
│                                                                          │
│ SAÍDA       ○ mesma pasta     ● pasta separada                           │
│             C:\Users\gabriel\Videos\reels\export                         │
│             saídas existentes são puladas (engine)                       │
│                                                                          │
╰──────────────────────────────────────────────────────────────────────────╯
```

## J. CONFIGURATION

- **Purpose:** the preset's own short question set, shown as one form instead of sequential prompts.
- **User goal:** make the few choices the preset asks, and see what is fixed, defaulted and automatic.
- **Layout:** WHAT/WHERE/HOW/QUALITY/AUDIO/OUTPUT strip 118 × 4 · form 72 × 29 | PADRÕES 44 × 14 over ENGINE AUTOMATION 44 × 15.
- **Hierarchy:** summary strip → user choices (focus) → fixed by preset → defaults → engine automation.

| Preset | Fixed by factory | User fields (same order, labels, options as `ui/launcher.py`) |
|:--|:--|:--|
| 1 Encode rápido | `cineon_pipeline=off, mode=crf, lut=on` | Enquadramento (contain/cover) · FPS (auto/24/25/30/60) · Modo (crf/2pass) |
| 2 Film look | `cineon_pipeline=on, mode=crf` | Exposure offset (EV, −2..+2) · Saturação (0..2) · Enquadramento |
| 3 Batch de pasta | `batch=<folder>, cineon=off, mode=crf, lut=on` | Definir pasta de saída separada? (+ Pasta de saída) · Usar film look (Cineon)? |

- **Field types:** select → `●/○` row, `←→` changes; toggle → `○ on ● off`, `SPACE` or `←→`; number → value box, `←→` steps (EV 0.1, saturação 0.05) and typing edits; value validated by `EncodeConfig` (Pydantic) on commit — out-of-range shows the error inline and the value is not applied (VALIDATION state, W). Step sizes are `[NEW UI ONLY]`; typing keeps every value reachable.
- **Region rules:** PADRÕES lists `EncodeConfig` defaults not asked by this preset (editable only through Configurar avançado…); ENGINE AUTOMATION lists VBV-by-duration, hardware tier → x264 preset, fps-aware lookahead and the `instagram` loudness target with the tag AUTO. None of these are presets or options.
- **Focus:** first field. **Keys:** `↑↓` `←→` `SPACE` `ENTER` `ESC`.
- **States:** normal; field error (red inline); batch output-dir field disabled until "pasta de saída separada" is on.
- **Transition in:** from SOURCE. **Out:** CONTINUAR (or ENTER on last field) → PREVIEW; ESC/VOLTAR → SOURCE (config kept).

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ✓ HOME   ✓ SOURCE   ▎CONFIG      PREVIEW     READY     ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ WHAT     clip_final.mov               WHERE    …\reels\ (ao lado da fonte)  HOW      FFmpeg native · crf           │
 │ QUALITY  LUT on · enhance on          AUDIO    loudnorm on · EBU meter on   OUTPUT   30 fps · contain · scale auto │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ CONFIGURAÇÃO · ENCODE RÁPIDO (FFMPEG) ──────────────────────────────╮  ╭─ PADRÕES · Configurar avançado… ─────────╮
 │                                                                      │  │ não perguntados neste fluxo              │
 │ ▎▸ Enquadramento      ● contain     ○ cover                           │  │                                          │
 │       contain = letterbox · cover = recorte para 9:16                │  │ Downscale 4K→1080p    auto               │
 │                                                                      │  │ Performance           balanced           │
 │    FPS                ○ auto   ○ 24   ○ 25   ● 30   ○ 60             │  │ Threads               0 (auto)           │
 │                                                                      │  │ HDR→SDR · Tonemap     auto · mobius      │
 │    Modo               ● crf     ○ 2pass                              │  │ Enhance · AI · MCTF   on · off · off     │
 │       crf → _Hollywood_CRF18 · 2pass → _Hollywood_2Pass              │  │ Dither                auto               │
 │                                                                      │  │ Loudnorm · EBU meter  on · on            │
 │                                                                      │  │ Perfil de hardware    on                 │
 │ FIXADO PELO PRESET                             somente leitura       │  │                                          │
 │    Pipeline Cineon    off                                            │  │                                          │
 │    Hollywood LUT      on                                             │  ╰──────────────────────────────────────────╯
 │                                                                      │  ╭─ ENGINE AUTOMATION ──────────────────────╮
 │                                                                      │  │ decidido pelo engine durante o encode    │
 │                                                                      │  │ não é escolha do usuário                 │
 │                                                                      │  │                                          │
 │                                                                      │  │ AUTO  VBV por duração da fonte           │
 │                                                                      │  │ AUTO  Hardware tier → preset x264        │
 │                                                                      │  │ AUTO  Lookahead fps-aware                │
 │                                                                      │  │ AUTO  Alvo instagram −14 LUFS            │
 │                                                                      │  │       −1.5 dBTP · LRA 11                 │
 │                                                                      │  │                                          │
 │    [ ◀ VOLTAR ]                            [ CONTINUAR ▶ PREVIEW ]   │  │ valores reais: [D] Details no encode     │
 │                                                                      │  │                                          │
 │                                                                      │  │                                          │
 │                                                                      │  │                                          │
 ╰──────────────────────────────────────────────────────────────────────╯  ╰──────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [↑↓] Field   [←→] Change   [SPACE] Toggle   [ENTER] Continue   [ESC] Back

```

## K. ADVANCED CONFIGURATION

- **Purpose:** every option `_flow_advanced` asks today, as five navigable tabs (`SECTIONS`): Source · Color/LUT · Audio · Enhance · Export.
- **User goal:** full control with an always-visible summary.
- **Layout:** tab bar (row 4) + rule · fields 74 × 29 | SETTINGS summary 42 × 29.
- **Components:** `tab_bar` `[EXTEND]` to focusable; field rows `[NEW UI ONLY]`; SETTINGS summary `[DERIVED]` from the working `EncodeConfig` copy.

| Tab | Fields (labels verbatim) | Conditional rule (as today) |
|:--|:--|:--|
| Source | FONTE (read-only, set in SOURCE) · Pipeline Cineon (film look)? · Enquadramento · FPS · Downscale 4K→1080p · Modo de encode · Performance | — |
| Color/LUT | Exposure offset (EV) · Saturação — **or** — Aplicar Hollywood LUT? · HDR→SDR · Tonemap | Cineon on → Exposure/Saturação enabled, LUT disabled ("n/a com Cineon"); Cineon off → the reverse |
| Audio | Loudnorm EBU R128 (-14 LUFS)? · Monitor EBU R128 pós-encode (FFplay)? | — |
| Enhance | Enhancement engine (denoise/sharpen/deband)? · Decisões via AI (mock CNN)? · MCTF mask video (anti-flicker)? · Dither (ruído anti-banding) | enhance off → AI and MCTF disabled; AI off → MCTF disabled and forced `off` (as `_flow_advanced` sets `mctf="off"`) |
| Export | Exibir perfil de hardware? · Threads (0 = auto) | — |

- Conditionally hidden prompts become **disabled rows** with a reason, so the layout does not jump. The resulting `EncodeConfig` must equal what `_flow_advanced` would produce for the same answers (golden test, AG).
- Preset 5 with a batch source: `_flow_advanced` rebuilds the config from `preset_batch`, discarding earlier values. The TUI must reproduce that exact result; **NEEDS REVIEW** whether that reset is intended.
- `report`, `cineon_lut`, `debug` are CLI-only today and are not exposed (shown read-only in SETTINGS under "SOMENTE CLI").
- **Focus:** first enabled field of Source. **Keys:** `←→` (tab or value, by focus level), `↑↓`, `SPACE`, `ENTER`, `ESC`.
- **Transition in:** SOURCE (preset 5) or PREVIEW → REVISAR (base = current config, like `_flow_advanced(con, base=cfg)`). **Out:** CONTINUAR → PREVIEW; ESC → previous screen with edits kept in the working copy. Discarding edits is **NEEDS REVIEW** (today there is no way back mid-flow).

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ✓ HOME   ✓ SOURCE   ▎CONFIG      PREVIEW     READY     ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  ▎Source      Color/LUT      Audio      Enhance      Export
 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

 ╭─ SOURCE ───────────────────────────────────────────────────────────────╮  ╭─ SETTINGS ─────────────────────────────╮
 │                                                                        │  │ SOURCE                                 │
 │ FONTE                        clip_final.mov         definida em SOURCE │  │   cineon off · contain · 30 fps        │
 │                                                                        │  │   scale auto · crf · balanced          │
 │ ▎▸ Pipeline Cineon (film look)?   ○ on       ● off                     │  │                                        │
 │    Enquadramento                  ● contain  ○ cover                   │  │ COLOR/LUT                              │
 │    FPS                            ○ auto  ○ 24  ○ 25  ● 30  ○ 60       │  │   LUT on · HDR auto · mobius           │
 │    Downscale 4K→1080p             ● auto     ○ off                     │  │                                        │
 │    Modo de encode                 ● crf      ○ 2pass                   │  │ AUDIO                                  │
 │    Performance                    ○ quality  ● balanced  ○ speed       │  │   loudnorm on · EBU meter on           │
 │                                                                        │  │                                        │
 │                                                                        │  │ ENHANCE                                │
 │                                                                        │  │   enhance on · AI off · MCTF off       │
 │                                                                        │  │   dither auto                          │
 │                                                                        │  │                                        │
 │                                                                        │  │ EXPORT                                 │
 │                                                                        │  │   hardware on · threads 0              │
 │                                                                        │  │                                        │
 │                                                                        │  │ SOMENTE CLI (não editável aqui)        │
 │                                                                        │  │   report on · cineon_lut padrão        │
 │                                                                        │  │                                        │
 │                                                                        │  │ SAÍDA                                  │
 │                                                                        │  │   clip_final_Hollywood_CRF18.mp4       │
 │                                                                        │  │                                        │
 │                                                                        │  │ • = alterado nesta sessão              │
 │    [ ◀ VOLTAR ]                           [ CONTINUAR ▶ PREVIEW ]      │  │                                        │
 │                                                                        │  │                                        │
 │                                                                        │  │                                        │
 ╰────────────────────────────────────────────────────────────────────────╯  ╰────────────────────────────────────────╯


────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [←→] Tab / Change   [↑↓] Field   [SPACE] Toggle   [ENTER] Continue   [ESC] Back

```

## L. PREVIEW

- **Purpose:** verify the job before arming it. Not a configuration surface.
- **User goal:** confirm source, output and settings are right.
- **Layout:** violet `PREVIEW · src → out` card 118 × 28 containing PROGRAM 34 × 20 | EXPORT SETTINGS 78 × 20, then the quality chip row; action row.
- **Components:** `settings_preview` content `[EXISTING]` (the rows shown are its current rows; the wireframe list is illustrative — exact row set **NEEDS REVIEW** against `ui/components.py`), `program_split`/`viewer_frame` `[EXISTING]`, `quality_row` with the existing chips `LUT · Loudnorm · Enhance · AI · MCTF · Dither · EBU Meter` and their existing pass/warn logic `[EXISTING]`.
- **Focus:** CONTINUAR. **Keys:** `←→` `ENTER` `ESC`.
- **States:** normal; no source dims → fallback frame; batch → PROGRAM shows the fallback frame and "pasta · N vídeos".
- **Transition in:** from CONFIGURATION/ADVANCED. **Out:** CONTINUAR → READY; REVISAR → ADVANCED (base = current config), as today's "Revisar configurações?"; ESC → the configuration screen it came from.

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ▎PREVIEW      READY     ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╭─ PREVIEW · clip_final.mov → clip_final_Hollywood_CRF18.mp4 ────────────────────────────────────────────────────────╮
 │                                                                                                                    │
 │ ╭─ PROGRAM ──────────────────────╮  ╭─ EXPORT SETTINGS ──────────────────────────────────────────────────────────╮ │
 │ │                                │  │                                                                            │ │
 │ │        ┌────────────────┐      │  │ Fonte            …\Videos\reels\clip_final.mov                             │ │
 │ │        │                │      │  │ Saída            …\Videos\reels\clip_final_Hollywood_CRF18.mp4             │ │
 │ │        │                │      │  │                                                                            │ │
 │ │        │                │      │  │ Pipeline         FFmpeg native                                             │ │
 │ │        │                │      │  │ Modo             crf                                                       │ │
 │ │        │                │      │  │ FPS              30                                                        │ │
 │ │        │                │      │  │ Enquadramento    contain                                                   │ │
 │ │        │      9:16      │      │  │ Downscale        auto                                                      │ │
 │ │        │                │      │  │ LUT              on                                                        │ │
 │ │        │                │      │  │ HDR · Tonemap    auto · mobius                                             │ │
 │ │        │                │      │  │ Loudnorm         on                                                        │ │
 │ │        │                │      │  │ Enhance          on · AI off · MCTF off                                    │ │
 │ │        │                │      │  │ Dither           auto                                                      │ │
 │ │        │                │      │  │ Performance      balanced · threads 0                                      │ │
 │ │        └────────────────┘      │  │                                                                            │ │
 │ │                                │  │                                                                            │ │
 │ │     contain · 1080 × 1920      │  │                                                                            │ │
 │ ╰────────────────────────────────╯  ╰────────────────────────────────────────────────────────────────────────────╯ │
 │                                                                                                                    │
 │ ✓ LUT    ✓ Loudnorm    ✓ Enhance    ⚠ AI    ⚠ MCTF    ✓ Dither    ✓ EBU Meter                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

                                                                            [ ◀ REVISAR ]        ▎▸ CONTINUAR ▶ READY




────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [←→] Choose   [ENTER] Select   [ESC] Back

```

## M. READY TO ENCODE

- **Purpose:** the armed state. Replaces today's `Confirm.ask("Iniciar encode com estas configurações?")` with a deliberate screen.
- **User goal:** see what will run, in what order, and what the delivery check will be, then start.
- **Layout:** DOUBLE hero 118 × 7 · KEY SETTINGS 58 × 15 | PIPELINE PLAN 58 × 15 · QC / DELIVERY 118 × 6 · action row.
- **Components:** hero `[NEW UI ONLY]` using the DOUBLE hero box; KEY SETTINGS `[DERIVED]`; PIPELINE PLAN `[DERIVED]` from config only (e.g. ANALYZING lists enhance only if `enhance=on`, loudness only if `loudnorm=on`; ENCODING shows "passe único CRF", "PASS 1 / 2 + PASS 2 / 2" or "FILM RENDER"); QC / DELIVERY `[DERIVED]` lists the ten existing checks and the report/meter behaviour from `report` and `ebu_meter` (batch: meters suppressed, as the engine does).
- **Focus:** START ENCODE. **Keys:** `←→` `ENTER` `ESC`.
- **States:** normal only (validation already happened). `_validate_args_consistency` runs on START; failure → VALIDATION ERROR.
- **Transition in:** from PREVIEW. **Out:** START → ENCODING (single) or BATCH QUEUE; ESC/PREVIEW → PREVIEW.

```text
 REELS ENCODER  v2.1.0                                                                                          ● READY
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ▎READY      ENCODE     QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
 ║                                                                                                                    ║
 ║   READY TO ENCODE                                                                                                  ║
 ║                                                                                                                    ║
 ║   clip_final.mov   ▸   clip_final_Hollywood_CRF18.mp4                                                              ║
 ║   1 · Encode rápido (FFmpeg)                                                                                       ║
 ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

 ╭─ KEY SETTINGS ─────────────────────────────────────────╮  ╭─ PIPELINE PLAN ────────────────────────────────────────╮
 │ SOURCE     clip_final.mov · 1080 × 1920                │  │ derivado da configuração                               │
 │ OUTPUT     clip_final_Hollywood_CRF18.mp4              │  │                                                        │
 │ PRESET     1 · Encode rápido (FFmpeg)                  │  │ ○ PREPARING   hardware · validação                     │
 │                                                        │  │ ○ PROBING     duração · frames · fps · HDR             │
 │ MODO       crf · 1 passe                               │  │ ○ ANALYZING   enhance · loudness da fonte              │
 │ FPS        30 · contain · scale auto                   │  │ ○ ENCODING    passe único CRF                          │
 │ COR        LUT on · HDR auto · mobius                  │  │ ○ QC          EBU R128 · checks do master              │
 │ ÁUDIO      loudnorm on · alvo instagram                │  │ ○ COMPLETED   MASTER QC · certificado                  │
 │ ENHANCE    on · AI off · MCTF off · dither auto        │  │                                                        │
 │ PERF       balanced · threads 0                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 ╰────────────────────────────────────────────────────────╯  ╰────────────────────────────────────────────────────────╯

 ╭─ QC / DELIVERY ────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ 10 checks no master   Container · Video · Resolution · Bit Depth · Color · FPS                                     │
 │                       Loudness · True Peak · Codec · Sample Rate                                                   │
 │ certificado           clip_final_Hollywood_CRF18.qc.html · .qc.json        monitor EBU   FFplay ANTES / DEPOIS     │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

    [ ◀ PREVIEW ]                                                                                  ▎▸   START ENCODE


────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [←→] Choose   [ENTER] Start encode   [ESC] Back to preview

```

## N. ENCODING DASHBOARD

- **Purpose:** primary screen; live, stateful view of one job.
- **User goal:** know the stage, progress, time left and health at a glance; reach details, log and cancel.
- **Layout (rows in MAIN):** JOB STRIP 1 · PROGRESS HEADER 7 · gap 1 · PROGRAM 30 × 13 | TIMELINE 43 × 13 | PERFORMANCE 43 × 13 · gap 1 · LOG 118 × 11.
- **Hierarchy:** stage + pass tracks → timeline numbers → performance → log.

| Region | Content | Tag |
|:--|:--|:--|
| JOB STRIP | source name + dims ▸ output name · pipeline · mode | `[EXISTING]` `job_strip` |
| PROGRESS HEADER | stage rail; one track per pass with %, ETA or ✓ duration | `[EXTEND]` header; stages `[REQUIRES ENGINE SEAM]` |
| PROGRAM | `viewer_frame` with fit | `[EXISTING]` |
| TIMELINE | pass · frame/total · fps · speed · eta · elapsed (pass) · job elapsed | frame…elapsed `[EXISTING]`; pass `[REQUIRES ENGINE SEAM]`; job elapsed `[DERIVED]` |
| PERFORMANCE | cpu/ram gauges, ram used (psutil) · threads · performance · tier | gauges `[EXISTING]`; threads/performance `[DERIVED]` from config; tier `[REQUIRES ENGINE SEAM]` (hardware event), shape of `HardwareProfile` fields **NEEDS REVIEW** |
| LOG | last 9 curated rows: SYSTEM/INFO/WARNING events + FFmpeg lines, stat lines collapsed | `[EXISTING]` stderr deque + `[REQUIRES ENGINE SEAM]` for events |

**Available vs future metrics**

| Currently available | How | Possible future (not shown in v1) |
|:--|:--|:--|
| frame, total frames, % | `frame=` parse + `get_total_frames` / Cineon counter | FFmpeg `bitrate=`, `size=`, `time=`, `q=` parsed from the same stderr line — `[REQUIRES ENGINE SEAM]`, no command change |
| fps (instantaneous Δframe/Δt) | `update_frame` math | smoothed fps — `[NEW UI ONLY]` but would change displayed numbers; not adopted |
| speed = fps / source fps | same | FFmpeg's own `speed=` |
| ETA | remaining / fps | combined job ETA across passes — `[NOT CURRENTLY SUPPORTED]` (no pass-duration model) |
| elapsed | wall clock | — |
| cpu, ram | psutil | per-process cpu of FFmpeg — `[NOT CURRENTLY SUPPORTED]` |
| raw FFmpeg lines | stderr deque | — |

Bitrate is visible only inside raw FFmpeg lines in LOG; no bitrate field is rendered.

- **Focus:** none (global hotkeys). **Keys:** `D` `L` `C` `Ctrl+C`.
- **States:** processing (default); warning (any WARNING event → amber count badge `⚠ 1` in the LOG title); CANCEL_REQUESTED (S); error → ERROR screen; total frames unknown/fallback → % still computed as today (behaviour of `get_total_frames` fallbacks unchanged).
- **Refresh:** render tick 10 Hz; progress applied at most 10 Hz; spinner and pulse from the existing rules.
- **Transition in:** START. **Out:** QC stage → QC / DELIVERY; error → ERROR; cancelled → CANCELLED.

```text
 REELS ENCODER  v2.1.0                                                                            ⠹ ENCODING · PASS 2/2
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 SOURCE  clip_final.mov  1080×1920    ▸    OUTPUT  clip_final_Hollywood_2Pass.mp4                 FFmpeg native · 2pass
 ╭─ ENCODING · PASS 2 / 2 ────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ▎● PASS 2    ○ QC    ○ COMPLETED                            │
 │                                                                                                                    │
 │ PASS 1 / 2   ANÁLISE        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   100.0%   ✓ 00:01:12                 │
 │ PASS 2 / 2   ENCODE FINAL ⠹ ███████████████████████████████░░░░░░░░░░░░░░░░░    64.0%   ETA 00:00:41               │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ PROGRAM ──────────────────╮ ╭─ TIMELINE ──────────────────────────────╮ ╭─ PERFORMANCE ───────────────────────────╮
 │     ┌────────────────┐     │ │ pass           2 / 2 · ENCODE FINAL     │ │ cpu     ████████░░░░    71%             │
 │     │                │     │ │ frame          1 152 / 1 800            │ │ ram     ██████░░░░░░    48%             │
 │     │                │     │ │ fps            28.4                     │ │ ram used              7.8 GB            │
 │     │                │     │ │ speed          0.95x                    │ │                                         │
 │     │                │     │ │ eta            00:00:41                 │ │ threads               0 (auto)          │
 │     │                │     │ │ elapsed        00:02:05                 │ │ performance           balanced          │
 │     │                │     │ │ job elapsed    00:03:17                 │ │ tier                  high              │
 │     │                │     │ │                                         │ │                                         │
 │     └────────────────┘     │ │                                         │ │                                         │
 │   contain · 1080 × 1920    │ │                                         │ │                                         │
 │                            │ │                                         │ │                                         │
 ╰────────────────────────────╯ ╰─────────────────────────────────────────╯ ╰─────────────────────────────────────────╯

 ╭─ LOG ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ SYSTEM   ANALYZING concluído                                                                                       │
 │ SYSTEM   PASS 1 / 2 concluído · 00:01:12                                                                           │
 │ SYSTEM   log do pass 1 analisado · parâmetros adaptativos do pass 2                                                │
 │ SYSTEM   PASS 2 / 2 iniciado                                                                                       │
 │ FFMPEG   rc lookahead 90 · ref frames 4 · keyint 60 · b frames 3                                                   │
 │ FFMPEG   frame= 1152 fps= 28 q=24.0 size=   18432kB time=00:00:38.40 bitrate=3932.2kbits/s speed=0.95x   ↻ ×1152   │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt

```

## O. TWO-PASS EXPERIENCE

Both passes live inside one PROGRESS HEADER titled with the job, never as two dashboards (today each pass creates a fresh dashboard titled "ENCODING"). The pass-1 track stays visible, completed, during pass 2.

- PASS 1 uses `▓` fill and the label ANÁLISE; PASS 2 uses `█` fill and ENCODE FINAL. The difference is texture + label + position, not colour alone.
- BETWEEN_PASSES shows an indeterminate spinner on the PASS 2 row with "analisando log do pass 1 · parâmetros adaptativos" (`_analyze_pass1_log`, `_adaptive_2pass_x264_params`). No percentage is invented.
- No combined job percentage: passes do not take equal time, so a single % would be misleading. Job elapsed is shown in TIMELINE.
- Whether native PASS 1 writes a null output (Cineon pass 1 uses `-an -f null` per STATE.md BD4) is **NEEDS REVIEW**; the label ANÁLISE does not claim it.
- Pass boundaries come from a `pass` event at the two `_run_encoding` call sites `[REQUIRES ENGINE SEAM]`.

PASS 1 active:

```text
╭─ ENCODING · PASS 1 / 2 ────────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ▎● PASS 1    ○ PASS 2    ○ QC    ○ COMPLETED                            │
│                                                                                                                    │
│ PASS 1 / 2   ANÁLISE      ⠹ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    37.0%   ETA 00:00:46               │
│ PASS 2 / 2   ENCODE FINAL   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   aguardando                          │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Between passes:

```text
╭─ ENCODING · ENTRE PASSES ──────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ◐ PASS 2    ○ QC    ○ COMPLETED                             │
│                                                                                                                    │
│ PASS 1 / 2   ANÁLISE        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   100.0%   ✓ 00:01:12                 │
│ PASS 2 / 2   ENCODE FINAL ⠹ analisando log do pass 1 · parâmetros adaptativos                                      │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

PASS 2 active:

```text
╭─ ENCODING · PASS 2 / 2 ────────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ▎● PASS 2    ○ QC    ○ COMPLETED                            │
│                                                                                                                    │
│ PASS 1 / 2   ANÁLISE        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   100.0%   ✓ 00:01:12                 │
│ PASS 2 / 2   ENCODE FINAL ⠹ ███████████████████████████████░░░░░░░░░░░░░░░░░    64.0%   ETA 00:00:41               │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Both passes done, QC running:

```text
╭─ POST-ENCODE QC ───────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ✓ PASS 2    ▎● QC    ○ COMPLETED                            │
│                                                                                                                    │
│ PASS 1 / 2   ANÁLISE        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   100.0%   ✓ 00:01:12                 │
│ PASS 2 / 2   ENCODE FINAL   ████████████████████████████████████████████████   100.0%   ✓ 00:01:52                 │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## P. CINEON EXPERIENCE

Cineon uses the same dashboard, DETAILS, LOG, CANCEL, QC and COMPLETED screens. Only these differ:

- Stage name FILM RENDER (crf) or PASS 1 / PASS 2 (2pass, same two-pass rules as O).
- Header row 5: static PIPELINE chain `DWG → PRIMARY → TONE/GAMUT → CINEON LOG → PORTRA LUT` with configured exposure and saturation `[DERIVED]` from config. Per-node progress or timing is `[NOT CURRENTLY SUPPORTED]`.
- Progress comes from the Python frame counter in the Cineon loop (as today) through the same `progress` event; stderr lines come from its 50-line buffer and arrive in bursts (binary `readline`), which the LOG handles without change.
- JOB STRIP shows `Film look (Cineon)` and the `_Cineon_Film.mp4` output.
- In the TUI path the Cineon loop stops driving `ResolveProgressHUD`/its own `Live` and emits events instead. **In the classic CLI path `ResolveProgressHUD` stays as is** (no visual change to classic output).
- No change to the frame pipeline, pipe feeding, dithering or FFmpeg arguments.

```text
 REELS ENCODER  v2.1.0                                                                         ⠹ ENCODING · FILM RENDER
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 SOURCE  clip_final.mov  1080×1920    ▸    OUTPUT  clip_final_Cineon_Film.mp4                  Film look (Cineon) · crf
 ╭─ ENCODING · FILM LOOK (CINEON) ────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ▎● FILM RENDER    ○ QC    ○ COMPLETED                                   │
 │                                                                                                                    │
 │ FILM RENDER  CRF         ⠹ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░    41.2%   ETA 00:01:58                │
 │                                                                                                                    │
 │ PIPELINE  DWG → PRIMARY → TONE/GAMUT → CINEON LOG → PORTRA LUT          exposure +0.0 EV · saturação 1.00          │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ PROGRAM ──────────────────╮ ╭─ TIMELINE ──────────────────────────────╮ ╭─ PERFORMANCE ───────────────────────────╮
 │     ┌────────────────┐     │ │ pass           1 / 1 · FILM RENDER      │ │ cpu     ████████░░░░    71%             │
 │     │                │     │ │ frame          742 / 1 800              │ │ ram     ██████░░░░░░    48%             │
 │     │                │     │ │ fps            8.9                      │ │ ram used              7.8 GB            │
 │     │                │     │ │ speed          0.30x                    │ │                                         │
 │     │                │     │ │ eta            00:01:58                 │ │ threads               0 (auto)          │
 │     │                │     │ │ elapsed        00:01:23                 │ │ performance           balanced          │
 │     │                │     │ │ job elapsed    00:01:51                 │ │ tier                  high              │
 │     │                │     │ │                                         │ │                                         │
 │     └────────────────┘     │ │                                         │ │                                         │
 │   contain · 1080 × 1920    │ │                                         │ │                                         │
 │                            │ │                                         │ │                                         │
 ╰────────────────────────────╯ ╰─────────────────────────────────────────╯ ╰─────────────────────────────────────────╯

 ╭─ LOG ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ SYSTEM   ANALYZING concluído · enhance aplicado antes dos passes                                                   │
 │ SYSTEM   FILM RENDER iniciado · LUT FilmLook_Portra400_SkinPriority_D65.cube                                       │
 │ FFMPEG   frame=  742 fps=8.9 q=23.0 size=    9216kB time=00:00:24.73 bitrate=3052.1kbits/s speed=0.30x    ↻ ×58    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │ buffer Cineon: 50 linhas                                                                                           │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt

```

## Q. ENCODING DETAILS

- **Purpose:** technical view of the running job. **User goal:** check what the engine configured, detected and calculated.
- **Layout:** live mini progress row · two rows of three 38 × 15 panels: VIDEO · COLOR · ENCODING / AUDIO · PERFORMANCE · INPUT · OUTPUT.
- **Provenance tag on every value:** `CFG` (from `EncodeConfig`), `DET` (probed from the source), `CALC` (computed by the engine: VBV preset, tier, loudness measurement, enhance profile), `LIVE` (updates during encode), `QC` (probed from the output by `probe_video_info` at post-encode QC; shows `—` until then).

| Category | Values | Source / tag |
|:--|:--|:--|
| VIDEO | codec (libx264) CFG · profile, level, pix fmt, bit depth, out res → QC · src res DET · fps CFG · src fps DET · fit, scale CFG | `probe_video_info` returns codec/profile/level/pix_fmt/size/fps for the output `[EXISTING]`; pre-encode output profile/level are not known to the UI |
| COLOR | src HDR DET · HDR→SDR, tonemap, LUT, dither CFG · primaries/transfer/matrix → QC | `detect_hdr_metadata`; output triplet from `probe_video_info`. **Color range is not probed anywhere → not shown** `[NOT CURRENTLY SUPPORTED]` |
| ENCODING | mode CFG · pass LIVE · VBV preset and values CALC · ingest cap CALC (2pass) · x264 preset CALC · lookahead/ref/keyint/bframes DET (x264 config lines the reader already sees) · enhance profile CALC | `get_vbv_preset`, `VBV_PRESETS`, `_INGEST_MAX_*`, hardware tier; seam needed for CALC values. Labels of the VBV triple **NEEDS REVIEW** |
| AUDIO | loudnorm, targets, EBU meter CFG · source loudness CALC · output codec/sample rate → QC | `analyze_audio_loudness`, `LOUDNORM_TARGETS`, `probe_audio_codec`. Output codec args (`_audio_output_args`) not audited → not shown pre-QC |
| PERFORMANCE | fps, speed, cpu, ram LIVE · threads, performance CFG · tier CALC | dashboard math, psutil |
| INPUT · OUTPUT | input CFG · duration DET · frames CALC · output CFG · report files CFG | `get_video_duration` (its 30 s fallback is not flagged by the engine → **NEEDS REVIEW**), `get_total_frames` |

- **Focus:** none. **Keys:** `D` or `ESC` back; `L`, `C`, `Ctrl+C` as on the dashboard.
- **States:** pre-QC (`—` in QC rows) · QC complete (QC rows filled) · cancelled/error (frozen snapshot).
- **Transition in:** `D` from dashboard or QUEUE (selected job). **Out:** `D`/`ESC` → where it came from; `L` → LOG.

```text
 REELS ENCODER  v2.1.0                                                                             ⠹ ENCODING · DETAILS
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ⠹ PASS 2 / 2  ENCODE FINAL   ██████████████████████████░░░░░░░░░░░░░░   64.0%   ETA 00:00:41   elapsed 00:02:05

 ╭─ VIDEO ────────────────────────────╮  ╭─ COLOR ────────────────────────────╮  ╭─ ENCODING ─────────────────────────╮
 │ codec      H.264 libx264       CFG │  │ src HDR    não                 DET │  │ mode       2pass               CFG │
 │ profile    —                    QC │  │ HDR→SDR    auto                CFG │  │ pass       2 / 2              LIVE │
 │ level      —                    QC │  │ tonemap    mobius              CFG │  │ VBV        short ≤30 s        CALC │
 │ pix fmt    —                    QC │  │ LUT        Hollywood on        CFG │  │ VBV kbps   9800/11000/14850   CALC │
 │ bit depth  —                    QC │  │ dither     auto                CFG │  │ ingest cap 12000/15000        CALC │
 │ src res    1080×1920           DET │  │                                    │  │ x264 presetslow               CALC │
 │ out res    —                    QC │  │ primaries  —                    QC │  │ lookahead  90                  DET │
 │ fps        30                  CFG │  │ transfer   —                    QC │  │ ref frames 4                   DET │
 │ src fps    29.97               DET │  │ matrix     —                    QC │  │ keyint     60                  DET │
 │ fit        contain             CFG │  │                                    │  │ b frames   3                   DET │
 │ scale      auto                CFG │  │                                    │  │ enhance    perfil ativo       CALC │
 │                                    │  │                                    │  │                                    │
 │                                    │  │                                    │  │                                    │
 ╰────────────────────────────────────╯  ╰────────────────────────────────────╯  ╰────────────────────────────────────╯

 ╭─ AUDIO ────────────────────────────╮  ╭─ PERFORMANCE ──────────────────────╮  ╭─ INPUT · OUTPUT ───────────────────╮
 │ loudnorm   on                  CFG │  │ fps        28.4               LIVE │  │ input      clip_final.mov      CFG │
 │ alvo I     −14 LUFS            CFG │  │ speed      0.95x              LIVE │  │ duração    60.0 s              DET │
 │ alvo TP    −1.5 dBTP           CFG │  │ cpu        71 %               LIVE │  │ frames     1 800              CALC │
 │ alvo LRA   11 LU               CFG │  │ ram        48 % · 7.8 GB      LIVE │  │                                    │
 │ fonte I    −19.2 LUFS         CALC │  │                                    │  │ output     …_2Pass.mp4         CFG │
 │                                    │  │ threads    0 (auto)            CFG │  │ report     .qc.html/.json      CFG │
 │ codec      —                    QC │  │ performancebalanced            CFG │  │                                    │
 │ sample rate—                    QC │  │ tier       high               CALC │  │                                    │
 │ EBU meter  on                  CFG │  │                                    │  │                                    │
 │                                    │  │                                    │  │                                    │
 │                                    │  │                                    │  │                                    │
 │                                    │  │                                    │  │                                    │
 │                                    │  │                                    │  │                                    │
 ╰────────────────────────────────────╯  ╰────────────────────────────────────╯  ╰────────────────────────────────────╯

────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ▎[D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt
 CFG configurado · DET detectado · CALC calculado · LIVE ao vivo · QC medido no master · [D] ou [ESC] volta
```

## R. ENCODING LOG

- **Purpose:** readable, complete diagnostics during the encode. **User goal:** see what happened and what FFmpeg is saying.
- **Layout:** mini progress row · filter tabs + follow indicator · 28 log rows · status row.

| Category | Source | Distinguishable today? |
|:--|:--|:--|
| FFMPEG | every stderr line (native 400-line deque, Cineon 50) and the x264 config lines | yes `[EXISTING]` |
| SYSTEM | TUI-side lifecycle from events: stage/pass start and end, files written, cancel | `[REQUIRES ENGINE SEAM]` |
| INFO | engine `console.print` messages routed through `reporter.info` | `[REQUIRES ENGINE SEAM]` |
| WARNING | engine yellow warnings (preflight heatmaps, MCTF, EBU audit soft failures) via `reporter.warning` | `[REQUIRES ENGINE SEAM]` |
| ERROR | error event + stderr tail on failure | `[REQUIRES ENGINE SEAM]` |

- FFmpeg's own warnings/errors inside stderr are **not** re-classified by pattern matching; they stay FFMPEG.
- Stat lines (`frame=` …) are collapsed into the latest one with a `↻ ×N` counter per run of consecutive stat lines. Display only: the deque, `CalledProcessError.stderr` and the printed tail are unchanged.
- Follow mode: on by default; `↑` pauses it; reaching the end with `↓` resumes it.
- **Keys:** `↑↓` scroll, `←→` filter, `L`/`ESC` back, `D`, `C`, `Ctrl+C`.
- **States:** following · paused · empty filter ("nenhuma linha nesta categoria").
- **Transition in:** `L`. **Out:** `L`/`ESC` → previous view; `D` → DETAILS.

```text
 REELS ENCODER  v2.1.0                                                                                 ⠹ ENCODING · LOG
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ⠹ PASS 2 / 2  ENCODE FINAL   ██████████████████████████░░░░░░░░░░░░░░   64.0%   ETA 00:00:41   elapsed 00:02:05

 ▎ALL      FFMPEG      SYSTEM      INFO      WARNING      ERROR             seguindo ▼ · 16 eventos · 400 linhas stderr
 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 SYSTEM   PREPARING
 INFO     Encode CRF 18 / 2-Pass - Hollywood LUT Transport
 INFO     Hardware Detection · perfil exibido (show_hardware on)
 SYSTEM   PROBING · 60.0 s · 1 800 frames · 29.97 fps
 INFO     Source aspect · portrait 9:16
 SYSTEM   ANALYZING
 INFO     Enhancement report · denoise / sharpen / deband
 INFO     Dither · auto
 INFO     Loudnorm · medição da fonte (pass de análise)
 SYSTEM   PASS 1 / 2 iniciado
 FFMPEG   rc lookahead 90 · ref frames 4 · keyint 60 · b frames 3
 FFMPEG   frame= 1800 fps= 25 q=-0.0 Lsize=N/A time=00:01:00.00 bitrate=N/A speed=0.83x                   ↻ ×1800
 SYSTEM   PASS 1 / 2 concluído · 00:01:12
 SYSTEM   log do pass 1 analisado · parâmetros adaptativos do pass 2
 SYSTEM   PASS 2 / 2 iniciado
 FFMPEG   frame= 1152 fps= 28 q=24.0 size=   18432kB time=00:00:38.40 bitrate=3932.2kbits/s speed=0.95x   ↻ ×1152












 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 fim do log · ↓ no fim = seguindo
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [D] Details   ▎[L] Log   [C] Cancel   [Ctrl+C] Interrupt
 [↑↓] rolar (pausa o seguimento)   [←→] filtro   [L] ou [ESC] volta ao dashboard
```

## S. CANCEL CONFIRMATION

- **Purpose:** prevent an accidental `C` from destroying a long encode, and explain what cancelling does.
- **Layout:** amber 64 × 12 modal centred over the live dashboard (rows 14–25, cols 29–92 of the screen). The dashboard keeps updating behind it.
- **Content:** active stage and %, "uses the existing interrupt path", partial output path.
- **Focus:** CONTINUAR ENCODE. **Keys:** `←→` choose, `ENTER` confirm, `ESC` keep encoding, `Ctrl+C` existing interrupt (no confirmation, as today). D/L/C disabled while open.
- **On confirm → CANCEL_REQUESTED:** the TUI invokes the same actions the existing Ctrl+C path performs — `terminate_active_ffmpeg()` and, after the worker exits, `discard_partial_output` semantics (3 attempts, locked-file warning). No new termination mechanism. How the main thread signals the worker so the engine's own `except KeyboardInterrupt` cleanup runs is `[REQUIRES ENGINE SEAM]`; precedent: `render_queue.run_job` already handles `KeyboardInterrupt` on the main thread while the encode runs in a worker. Cineon registers each pass via `_register_ffmpeg` (STATE.md BD4) and also has its own kill path; confirming both are covered by `terminate_active_ffmpeg` is **NEEDS REVIEW**.
- **Windows:** Ctrl+C is also delivered to the FFmpeg child; FFmpeg may exit first and the worker may see `CalledProcessError`. When a cancel was requested, the TUI classifies the outcome as CANCELLED, not ENCODING ERROR.
- During QC the output is complete; TUI cancel is disabled there (`░[C]`). What Ctrl+C does during QC today is **NEEDS REVIEW** (it must not delete a finished master).
- **Transition in:** `C`. **Out:** keep → previous view; confirm → CANCEL_REQUESTED → CANCELLED (W).

```text
 REELS ENCODER  v2.1.0                                                                                        ⚠ CANCEL?
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 SOURCE  clip_final.mov  1080×1920    ▸    OUTPUT  clip_final_Hollywood_2Pass.mp4                 FFmpeg native · 2pass
 ╭─ ENCODING · PASS 2 / 2 ────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ▎● PASS 2    ○ QC    ○ COMPLETED                            │
 │                                                                                                                    │
 │ PASS 1 / 2   ANÁLISE        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   100.0%   ✓ 00:01:12                 │
 │ PASS 2 / 2   ENCODE FINAL ⠹ ███████████████████████████████░░░░░░░░░░░░░░░░░    64.0%   ETA 00:00:41               │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ PROGRAM ──────────────────╮ ╭─ TIMELINE ──────────────────────────────╮ ╭─ PERFORMANCE ───────────────────────────╮
 │     ┌────────────────┐   ╭─ CANCELAR ENCODE? ───────────────────────────────────────────╮██░░░░    71%             │
 │     │                │   │                                                              │░░░░░░    48%             │
 │     │                │   │ O encode está ativo · PASS 2 / 2 · 64.0%                     │        7.8 GB            │
 │     │                │   │                                                              │                          │
 │     │                │   │ Cancelar usa o caminho de interrupção existente:             │        0 (auto)          │
 │     │                │   │ encerra o FFmpeg e remove a saída parcial                    │        balanced          │
 │     │                │   │ …\reels\clip_final_Hollywood_2Pass.mp4                       │        high              │
 │     │                │   │                                                              │                          │
 │     └────────────────┘   │       ▎▸ CONTINUAR ENCODE            CANCELAR ENCODE         │                          │
 │   contain · 1080 × 1920  │                                                              │                          │
 │                          │                                                              │                          │
 ╰──────────────────────────╰──────────────────────────────────────────────────────────────╯──────────────────────────╯

 ╭─ LOG ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ SYSTEM   ANALYZING concluído                                                                                       │
 │ SYSTEM   PASS 1 / 2 concluído · 00:01:12                                                                           │
 │ SYSTEM   log do pass 1 analisado · parâmetros adaptativos do pass 2                                                │
 │ SYSTEM   PASS 2 / 2 iniciado                                                                                       │
 │ FFMPEG   rc lookahead 90 · ref frames 4 · keyint 60 · b frames 3                                                   │
 │ FFMPEG   frame= 1152 fps= 28 q=24.0 size=   18432kB time=00:00:38.40 bitrate=3932.2kbits/s speed=0.95x   ↻ ×1152   │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [←→] Choose   [ENTER] Confirm   [ESC] Keep encoding   [Ctrl+C] Interrupt
 dashboard continua atualizando atrás do diálogo · D / L / C desativados enquanto aberto
```

CANCEL_REQUESTED header:

```text
╭─ ENCODING · PASS 2 / 2 ────────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ PASS 1    ⚠ PASS 2    ○ QC    ○ COMPLETED                            │
│                                                                                                                    │
│ ⚠ CANCELAMENTO SOLICITADO · encerrando FFmpeg · aguardando o processo sair                                        │
│   saída parcial …\clip_final_Hollywood_2Pass.mp4 · removendo (até 3 tentativas)                                    │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## T. BATCH QUEUE

- **Purpose:** one screen for the whole folder run; replaces the nested `Live` arrangement in the TUI path only.
- **User goal:** see every job's state, the active job's progress, and the queue ETA.
- **Layout:** queue strip 1 · RENDER QUEUE 118 × 20 (header + 12 visible rows; scrolls beyond) · ACTIVE JOB 58 × 11 | LOG · JOB 58 × 11.

| Column | Width | Content | Tag |
|:--|:-:|:--|:--|
| JOB | 5 | index | `[EXISTING]` |
| FILE | 30 | input basename, elided | `[EXISTING]` |
| STATUS | 14 | mapping in D.3 | `[EXISTING]` |
| PROGRESS | 28 | active: live bar · done: full · others: empty | active bar `[REQUIRES ENGINE SEAM]` |
| ETA | 9 | active: pass ETA · finished: actual duration (today's "Duração") · queued: — | duration `[EXISTING]`, ETA seam |
| RESULT | 18 | ok: MASTER QC verdict · skipped: "saída já existe" · failed: short reason · cancelled: "interrompido" | verdict `[REQUIRES ENGINE SEAM]` (payload is returned today but not surfaced) |

- Title keeps the existing format `Job n de N · ETA mm:ss` from `estimate_eta`/`format_eta`.
- Unchanged behaviour: skip-existing, output directory, worker thread, `discard_partial_output`, EBU meter suppression in batch, exit codes (0 ok, 1 any failure, 130 interrupted).
- **Focus:** the ENCODING job (follows it). **Keys:** `↑↓` select job, `D` details of selected, `L` log of selected, `C` cancel the queue (the existing interruption stops the whole queue — there is no per-job skip), `Ctrl+C`.
- Log of a finished job is `QueueJob.log` (captured text, truncated to 4 000 chars in the final report as today). A job interrupted mid-encode has an empty log today (documented in `run_job`); the TUI shows "log indisponível para job interrompido".
- **States:** LISTING (spinner while `find_video_files` runs) · RUNNING · FINISHED → report · INTERRUPTED → report with ⚡ count.
- **Transition in:** START from READY. **Out:** FINISHED/INTERRUPTED → FILA — RELATÓRIO FINAL (V).

```text
 REELS ENCODER  v2.1.0                                                                                   ⠹ BATCH · 4/12
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎QUEUE      REPORT
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 BATCH  C:\Users\gabriel\Videos\reels  ·  12 arquivos   ▸   saída: mesma pasta                      FFmpeg native · crf

 ╭─ RENDER QUEUE · Job 4 de 12 · ETA 18:40 ───────────────────────────────────────────────────────────────────────────╮
 │ JOB    FILE                            STATUS          PROGRESS                      ETA        RESULT             │
 │ ────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
 │ 01     intro_take1.mov                 ✓ COMPLETED     ████████████████████  100%    02:41      ★ DELIVERY READY   │
 │ 02     intro_take2.mov                 ○ SKIPPED                                     —          saída já existe    │
 │ 03     drone_01.mp4                    ✗ FAILED                                      01:07      FFmpeg · ver [L]   │
 │ ▎▸     clip_final.mov                  ⠹ ENCODING      █████████████░░░░░░░   64%    00:41                          │
 │ 05     bts_cozinha.mp4                 · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 06     bts_sala.mp4                    · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 07     entrevista_a.mov                · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 08     entrevista_b.mov                · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 09     broll_01.mp4                    · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 10     broll_02.mp4                    · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 11     outro.mov                       · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │ 12     teaser.mov                      · QUEUED        ░░░░░░░░░░░░░░░░░░░░          —                             │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ JOB 04 · ENCODING ────────────────────────────────────╮  ╭─ LOG · JOB 04 ─────────────────────────────────────────╮
 │ ⠹ ███████████████████████░░░░░░░░░░░░░   64.0%         │  │ SYSTEM   ENCODING · passe único CRF                    │
 │                                                        │  │ FFMPEG   frame= 1152 fps= 28 q=24.0 … ↻ ×1152          │
 │ frame     1 152 / 1 800      fps   28.4                │  │                                                        │
 │ speed     0.95x              eta   00:00:41            │  │                                                        │
 │ elapsed   00:02:05                                     │  │                                                        │
 │                                                        │  │                                                        │
 │ saída     clip_final_Hollywood_CRF18.mp4               │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │ EBU meter suprimido no batch (existente)               │
 ╰────────────────────────────────────────────────────────╯  ╰────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [↑↓] Select job   [D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt

```

## U. QC / DELIVERY

- **Purpose:** show the existing post-encode QC as it runs. **User goal:** know whether the master is deliverable.
- **Layout:** job strip 1 · QC header 118 × 5 (stage rail + sub-steps) · EBU R128 — AUDITORIA PÓS-ENCODE 118 × 9 · MASTER QC (DOUBLE) 118 × 14 · DELIVERY 118 × 5.
- **Components:** EBU table (ANTES/DEPOIS/Alvo, 5 rows, existing ✓/⚠ flags) `[EXISTING]`; `delivery_seal` + seal reveal `[EXISTING]`; DELIVERY strip `[DERIVED]` from `write_report` return and meter launch result.
- **Checks (existing, not extended):** Container, Video, Resolution, Bit Depth, Color, FPS (`build_video_checks`) + Loudness, True Peak, Codec, Sample Rate (`build_delivery_checks`).

| QC state | Rule (existing) | Visual |
|:--|:--|:--|
| CHECKING | measurement/probe running | `⠹` per sub-step |
| PASS | check `passed is True` | `✓` green |
| WARNING | `passed is None` (unavailable or informational, e.g. non-1080×1920 from contain) | `●`/`⚠` amber — glyph per `quality_chip(None)`, **NEEDS REVIEW** |
| FAIL | `passed is False` | `✗`/`⚠` red |
| DELIVERY READY | `failed == 0` | gold `★ D E L I V E R Y   R E A D Y ★` |
| REVISAR ENTREGA | any failure | amber `⚠ R E V I S A R   E N T R E G A ⚠` |

- FFplay meter windows open after the seal (single-file, `ebu_meter=on`, ffplay available), detached, as today; the TUI keeps running and does not take focus back.
- **Focus:** none. **Keys:** `D` `L` `Ctrl+C`; `C` disabled.
- **Transition in:** QC stage event. **Out:** QC done → COMPLETED.

```text
 REELS ENCODER  v2.1.0                                                                                             ⠹ QC
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ✓ ENCODE   ▎QC      DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 SOURCE  clip_final.mov  1080×1920    ▸    OUTPUT  clip_final_Hollywood_CRF18.mp4                   FFmpeg native · crf
 ╭─ POST-ENCODE QC ───────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓ PREPARING    ✓ PROBING    ✓ ANALYZING    ✓ ENCODING    ▎● QC    ○ COMPLETED                                      │
 │ ✓ EBU R128 medido    ✓ master probe    ⠹ selo MASTER QC    ○ certificado    ○ monitor FFplay                       │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 ╭─ EBU R128 — AUDITORIA PÓS-ENCODE ──────────────────────────────────────────────────────────────────────────────────╮
 │ Métrica                   ANTES (original)      DEPOIS (final)        Alvo                                         │
 │ ──────────────────────────────────────────────────────────────────────────────────────────                         │
 │ Integrated (LUFS-I)       −19.2 ⚠               −14.1 ✓               −14                                         │
 │ True Peak (dBTP)          −0.3 ⚠                −1.6 ✓                ≤ −1.5                                      │
 │ Loudness Range (LU)       8.4                   7.9                   ~11                                          │
 │ Codec                     aac                   aac                   AAC-LC                                       │
 │ Sample Rate (Hz)          48000                 48000                 48000                                        │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 ╔═ MASTER QC ════════════════════════════════════════════════════════════════════════════════════════════════════════╗
 ║                                                                                                                    ║
 ║ ✓ Container     MP4                             ✓ Loudness      −14.1 LUFS                                         ║
 ║ ✓ Video         H.264 High@4.0                  ✓ True Peak     −1.6 dBTP                                          ║
 ║ ✓ Resolution    1080x1920                       ✓ Codec         aac                                                ║
 ║ ✓ Bit Depth     8-bit                           ✓ Sample Rate   48000                                              ║
 ║ ✓ Color         BT.709                                                                                             ║
 ║ ✓ FPS           30 fps                                                                                             ║
 ║                                                                                                                    ║
 ║                                         ★  D E L I V E R Y   R E A D Y  ★                                          ║
 ║                                                                                                                    ║
 ║                                                                                                                    ║
 ║                                                                                                                    ║
 ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
 ╭─ DELIVERY ─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ certificado   gravando clip_final_Hollywood_CRF18.qc.html · .qc.json                                               │
 │ monitor EBU   abre 2 janelas FFplay (ANTES / DEPOIS) após o selo                                                   │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [D] Details   [L] Log   ░[C] Cancel   [Ctrl+C] Interrupt
 saída completa · cancelamento pela TUI desativado no QC
```

## V. COMPLETED

- **Purpose:** unambiguous end state. **User goal:** know it finished, where the file is, and whether it is deliverable.
- **Layout:** DOUBLE hero 118 × 8 (`✓ ENCODE COMPLETE` + verdict line) · OUTPUT 58 × 14 | MASTER QC · RESUMO 58 × 14 · DELIVERY 118 × 5 · action row.
- **Data:** report payload (`output.size_human`, `encode.duration_human`, `video`, `audio.after`, `summary.passed/warnings/failed/ready`) `[EXISTING]` via `qc` event `[REQUIRES ENGINE SEAM]`; `report=off` → DELIVERY shows "certificado desativado (--report off)".
- **Actions:** SAIR (default; ends the process with the existing exit code), VER QC (returns to the QC screen, static), VER LOG (LOG, static). "Novo encode" (loop back to HOME) is **not** in v1: process-level globals (`_ACTIVE_FFMPEG`, cached binaries) are not proven safe for a second job in one process → **NEEDS REVIEW**.
- **Keys:** `←→` `ENTER`.
- **Transition in:** after QC. **Out:** SAIR → restore terminal, exit.

```text
 REELS ENCODER  v2.1.0                                                                                      ✓ COMPLETED
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ✓ ENCODE   ✓ QC   ▎DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
 ║                                                                                                                    ║
 ║   ✓  ENCODE COMPLETE                                                                                               ║
 ║                                                                                                                    ║
 ║   ★  D E L I V E R Y   R E A D Y  ★                                                                                ║
 ║                                                                                                                    ║
 ║                                                                                                                    ║
 ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

 ╭─ OUTPUT ───────────────────────────────────────────────╮  ╭─ MASTER QC · RESUMO ───────────────────────────────────╮
 │ arquivo    clip_final_Hollywood_CRF18.mp4              │  │ ✓ 10 passaram     ⚠ 0 avisos     ✗ 0 falhas           │
 │ pasta      C:\Users\gabriel\Videos\reels               │  │                                                        │
 │ tamanho    18.4 MB                                     │  │ veredito   DELIVERY READY                              │
 │ encode     1m 52s                                      │  │                                                        │
 │                                                        │  │ ✓ Container · Video · Resolution · Bit Depth           │
 │ vídeo      H.264 High@4.0 · 1080x1920 · 30 fps         │  │ ✓ Color · FPS                                          │
 │ cor        BT.709 · 8-bit                              │  │ ✓ Loudness · True Peak · Codec · Sample Rate           │
 │ áudio      aac · 48000 · −14.1 LUFS · −1.6 dBTP        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 │                                                        │  │                                                        │
 ╰────────────────────────────────────────────────────────╯  ╰────────────────────────────────────────────────────────╯

 ╭─ DELIVERY ─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ certificado   clip_final_Hollywood_CRF18.qc.html · clip_final_Hollywood_CRF18.qc.json                              │
 │ monitor EBU   2 janelas FFplay abertas · feche-as quando terminar a inspeção                                       │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

    ▎▸ SAIR           VER QC           VER LOG



────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [←→] Choose   [ENTER] Select

```

REVISAR ENTREGA hero variant:

```text
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                    ║
║   ✓  ENCODE COMPLETE                                                                                               ║
║                                                                                                                    ║
║   ⚠  R E V I S A R   E N T R E G A  ⚠                                                                            ║
║   1 falha · True Peak −0.6 dBTP (alvo ≤ −1.5)                                                                      ║
║                                                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

Batch end — FILA — RELATÓRIO FINAL (same counts and wording as `render_final_report`; ENTER on a failed row shows its captured log):

```text
╭─ FILA — RELATÓRIO FINAL ───────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                    │
│ ✓ Sucesso        10 / 12          ★ DELIVERY READY 9   ⚠ REVISAR ENTREGA 1                                        │
│ ○ Pulados         1 / 12                                                                                           │
│ ✗ Falhas          1 / 12          drone_01.mp4 → FFmpeg código 1   [ENTER] ver log capturado                       │
│                                                                                                                    │
│ Tempo total da fila   27:14                               código de saída   1 (há falhas)                          │
│                                                                                                                    │
│                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## W. ERROR STATES

- **Purpose:** keep every existing diagnostic, organised.
- **Layout (ENCODING ERROR):** red `error_card` 118 × 8 · FFMPEG STDERR 118 × 19 (the same 40 native / 50 Cineon lines printed today, raw, scrollable) · ESTADO 118 × 4 (stage, last frame, partial-output status) · action row.
- **Focus:** SAIR. **Keys:** `↑↓` scroll, `←→`, `ENTER`.
- `--debug` traceback: when `debug=True`, a TRACEBACK section follows the stderr panel (scroll). Hint text is the existing `error_card` hint.
- Whether a partial output is removed after an encoding error (not a cancel) is not established by the audit → the ESTADO row states only that it may exist (**NEEDS REVIEW**).
- Exit codes are unchanged; single-file error/interrupt codes **NEEDS REVIEW** (batch: 1 / 130; validation: 2; dependency: 1).

| Type | Trigger (existing) | Screen | Recovery |
|:--|:--|:--|:--|
| ENCODING ERROR | `CalledProcessError` / exception in worker | full screen (below) | SAIR |
| DEPENDENCY ERROR | `missing_ffmpeg_binaries` at preflight | `dependency_error_card` (DOUBLE red) instead of HOME | SAIR (exit 1) |
| VALIDATION ERROR | Pydantic field error (inline) or `_validate_args_consistency` at START | inline on the field / banner on READY | fix field / back to CONFIGURATION (exit 2 only if not recoverable in UI — **NEEDS REVIEW**) |
| CANCELLED | cancel or Ctrl+C | amber card with "⚠ Encode interrompido pelo usuário" + partial-output result | SAIR |

```text
 REELS ENCODER  v2.1.0                                                                                          ✗ ERROR
 ✓ HOME   ✓ SOURCE   ✓ CONFIG   ✓ PREVIEW   ✓ READY   ▎ENCODE      QC     DELIVERY
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ╭─ ENCODING ERROR ───────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                                                                                                    │
 │ ✗ FFmpeg terminou com erro durante PASS 2 / 2                                                                      │
 │   CalledProcessError · returncode 1                                                                                │
 │                                                                                                                    │
 │   use --debug para o traceback completo                                                                            │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ FFMPEG STDERR · últimas 40 de 400 linhas ─────────────────────────────────────────────────────────────────────────╮
 │ frame= 1150 fps= 28 q=24.0 size=   18390kB time=00:00:38.33 bitrate=3930.4kbits/s speed=0.95x                      │
 │ [mov,mp4,m4a,3gp,3g2,mj2 @ 0x…] stream 0, offset 0x…: partial file                                                 │
 │ Error while decoding stream #0:0: Invalid data found when processing input                                         │
 │ [out#0/mp4 @ 0x…] video:18390KiB audio:612KiB …                                                                    │
 │ Conversion failed!                                                                                                 │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │                                                                                                                    │
 │ ▲ ↑↓ rola as 40 linhas · texto bruto, sem reformatação                                                             │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 ╭─ ESTADO ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ estágio   PASS 2 / 2 · frame 1 150 / 1 800        saída parcial   pode existir: …\clip_final_Hollywood_2Pass.mp4   │
 │                                                                                                                    │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
    ▎▸ SAIR           VER LOG COMPLETO
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 [↑↓] Scroll   [←→] Choose   [ENTER] Select

```

DEPENDENCY ERROR:

```text
╔═ DEPENDÊNCIA AUSENTE ══════════════════════════════════════════════════════════════════╗
║                                                                                        ║
║ ✗ ffmpeg não encontrado                                                                ║
║   procurado em REELS_FFMPEG → .\bin → PATH                                             ║
║                                                                                        ║
║   instale em .\bin ou defina REELS_FFMPEG · código de saída 1                          ║
║                                                                                        ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
```

VALIDATION ERROR (inline):

```text
╭─ CONFIGURAÇÃO · FILM LOOK (CINEON) ──────────────────────────────────╮
│                                                                      │
│ ▎▸ Exposure offset (EV)   [ +2.5▏]      −2 .. +2                       │
│       ✗ fora do intervalo · valor não aplicado                       │
│                                                                      │
│    Saturação              [ 1.00 ]      0 .. 2                       │
╰──────────────────────────────────────────────────────────────────────╯
```

CANCELLED:

```text
╭─ CANCELLED ────────────────────────────────────────────────────────────────────────────╮
│                                                                                        │
│ ⚠ Encode interrompido pelo usuário                                                    │
│                                                                                        │
│   saída parcial removida  …\clip_final_Hollywood_2Pass.mp4                             │
│   (ou ✗ não foi possível remover: arquivo em uso — remova manualmente)                 │
│                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────╯
```

SIZE GUARD (terminal smaller than 120 × 40 at start or after resize; the TUI waits for resize, ESC falls back to the classic wizard):

```text
╭────────────────────────────────────────────────────────────────────╮
│                                                                    │
│ TUI requer 120 × 40                                                │
│ terminal atual 100 × 30                                            │
│                                                                    │
│ redimensione a janela para continuar                               │
│ [ESC] usar o wizard clássico                                       │
│                                                                    │
╰────────────────────────────────────────────────────────────────────╯
```

---

## X. Visual State System

Only the existing palette and named styles.

| State | Glyph | Foreground | Background | Weight | Used for |
|:--|:--|:--|:--|:--|:--|
| NORMAL | — | text `#e6e8ef` / label muted `#8a8fa3` | — | value bold | values, labels |
| FOCUSED | `▎▸` | ink `#13141a` | indigo `#5b6cff` | bold | focused row/button (`tab.active`) |
| SELECTED | `●` | indigo | — | bold | chosen option |
| DISABLED | — | muted, dim | — | normal | disabled field/key `░[C]` |
| PROCESSING | braille spinner | violet `#a06bff` | — | normal | stages, CHECKING |
| ACTIVE | `▎Name` / `●` | ink on indigo / indigo | indigo for tabs | bold | active tab, active stage, ENCODING job |
| QUEUED | `·` / `○` | muted | — | normal | pending stages and jobs |
| SUCCESS | `✓` | green `#3ddc84` | — | bold | done stages, PASS checks, VALID |
| WARNING | `⚠` | amber `#ffb454` | — | bold | warnings, CANCEL modal border, REVISAR ENTREGA |
| ERROR | `✗` | red `#ff5c7a` | — | bold | errors, FAIL, NOT FOUND/INVALID |
| CANCELLED | `⚡` (queue) / `⚠` | amber | — | bold | cancelled job/encode |
| DELIVERY | `★` | gold `#d4af37` | — | bold | DELIVERY READY only |
| INFO | — | cyan `#33d6e0` | — | normal | paths, dimensions, perf values |

Borders: panels indigo (`panel.border`); progress header and PREVIEW card violet (`accent`); hero/MASTER QC DOUBLE; ERROR card red; CANCEL modal amber. Gauges keep green/amber/red at 60/85 %.

## Y. Component Inventory

| Component | Decision | Use in TUI |
|:--|:--|:--|
| `banner` | KEEP | HOME |
| `tab_bar` | EXTEND | focusable tabs, flow rail |
| `program_panel` / `viewer_frame` | REUSE | SOURCE, PREVIEW, dashboard |
| `program_split` | REUSE | PREVIEW |
| `properties_panel` | REUSE | EXPORT SETTINGS, KEY SETTINGS, DETAILS panels |
| `info_card` | REUSE | SYSTEM, PADRÕES, ENGINE AUTOMATION, DELIVERY |
| `quality_chip` / `quality_row` | KEEP | PREVIEW chips, SYSTEM readiness |
| `log_panel` | EXTEND | categories, collapsing, scroll, filters |
| `job_strip` | KEEP | dashboard, QC |
| `gauge_bar` | KEEP | PERFORMANCE |
| `notification` | REUSE | footer message line |
| `error_card` | EXTEND | ENCODING ERROR with scrollable stderr |
| `dependency_error_card` | KEEP | DEPENDENCY ERROR |
| `settings_preview` | REUSE (content) | PREVIEW; wizard keeps the original |
| `delivery_seal` / `play_delivery_seal` | KEEP | QC, COMPLETED |
| `EncodeDashboard` | EXTEND | event-driven; duck-typed API kept for classic path |
| `render_queue.build_table` | KEEP (classic) | TUI gets a themed queue table (NEW) |
| app header / flow rail / key footer | NEW | every screen |
| form field rows (select, toggle, number, path) | NEW | SOURCE, CONFIGURATION, ADVANCED |
| stage rail + pass tracks | NEW | dashboard header |
| modal | NEW | CANCEL |
| queue table (themed) | NEW | BATCH QUEUE |
| details grid with provenance tags | NEW | DETAILS |
| Cineon pipeline chain row | NEW | Cineon header |
| size guard | NEW | guard screen |
| `ui/prompts.py` | KEEP | classic wizard only |

## Z. UIState Model

UI-only state; no engine logic, no copies of engine calculations.

```text
UIState
├── screen            enum of section C screens + overlays {details, log, cancel_modal}
├── focus             {screen → focus_id}, tab index, focus level (tabs | fields)
├── terminal          {cols, rows, size_ok}
├── preset            1..5
├── config            EncodeConfig (working copy; the only config object)
├── source            {kind file|folder, path, validation VALID|INVALID|NOT_FOUND|CHECKING, dims?, video_count?}
├── output            {path (from EncodeConfig.output_path / engine done event)}
├── job               {stage, substep, passes[{index, total, label, frame, total_frames, fps, speed, eta, started, ended}],
│                      started, cancel_state none|requested|done, hardware?, probe?, analysis?}
├── queue             [{index, input, output, status (QueueJob.status), started, finished, result?, log_ref}], eta, selected
├── logs              ring of LogEntry{category, text, stat_collapse_count}; reference to engine stderr deque
├── qc                {checks[(label, value, passed)], before, after, ready, report_paths[], meters_opened}
├── error             {kind, message, stderr_tail, returncode, traceback?}
└── notifications     queue of {level, text, ttl}
```

`progress` values are copied from events as sent; the UI does not recompute fps, speed or ETA.

## AA. Reporter / Event Model

Contract: the engine calls methods on an optional `reporter`. `ConsoleReporter` (default) reproduces today's output byte for byte. `QueueReporter` (TUI) puts immutable event records on one `queue.Queue`. Events carry `job_id` (batch index or 0) and a monotonic timestamp added by the reporter.

| Event | Payload | Source (emitter) | When | UI consumer | Data exists today? | Phase 3 change |
|:--|:--|:--|:--|:--|:--|:--|
| `stage` | name, substep? | `_encode_single_file`, `run_ffmpeg`, `run_ffmpeg_with_cineon`, QC | entering each D.2 state/sub-step | header rail, LOG SYSTEM | implicit (rules/prints) | add calls |
| `info` | text, style hint | every `console.print`/`console.rule` in engine | same places | LOG INFO | yes (printed) | replace prints with `reporter.info` (console impl prints identical string) |
| `warning` | text | yellow soft-failure prints | same | LOG WARNING, badge | yes | same |
| `hardware` | HardwareProfile fields | `detect_hardware` in pipelines | PREPARING | PERFORMANCE tier, DETAILS | yes | emit object; field list **NEEDS REVIEW** |
| `probe` | duration, total_frames, source_fps, width, height, hdr | probe functions | PROBING | TIMELINE totals, DETAILS | yes | emit |
| `analysis` | kind (enhance, loudness, pass1_log, preflight, mctf), result summary | analyzers | ANALYZING / BETWEEN_PASSES | DETAILS CALC rows, LOG | yes | emit |
| `pass` | index, total, label | `_run_encoding` call sites, Cineon passes | pass start/end | pass tracks | index implicit | emit |
| `x264_config` | lines | `_run_encoding` (dim lines) | start of pass | DETAILS DET rows, LOG | yes (printed) | emit |
| `progress` | frame, total, fps, speed, eta, elapsed | `ffmpeg_live_reader` (native), Cineon loop | per update, throttled ≤10 Hz | bars, TIMELINE | yes | call reporter instead of `live.update` in TUI mode |
| `log` | line | stderr readers (same line appended to deque) | each line | LOG FFMPEG | yes | forward; deque unchanged |
| `qc` | checks, before, after, targets, ready, report paths | `run_post_encode_qc` | during/after QC | QC, COMPLETED | yes (payload returned) | split print vs data; seal animation rendered by TUI |
| `meters` | opened count | QC meter launch | after seal | DELIVERY strip | yes (printed) | emit |
| `done` | output path, payload ref, seconds | `_encode_single_file` end | job end | COMPLETED | yes | emit |
| `error` | kind, message, stderr_tail, returncode, cmd?, traceback? | `_run_encoding`, Cineon, `main` handlers | failure | ERROR | yes | emit instead of printing in TUI mode |
| `cancel` | phase requested/terminated/cleaned, partial_removed, locked_path? | interrupt handlers, `discard_partial_output` | cancellation | CANCEL_REQUESTED, CANCELLED | yes (messages) | emit |
| `queue_init` / `job_start` / `job_skip` / `job_done` / `queue_done` | job list; index; reason; status, result; summary | batch block in `main` / `render_queue` | batch lifecycle | BATCH QUEUE, report | yes | move presentation out of `main` for TUI path only |
| future `stats` | bitrate, size, time, q, ffmpeg speed | same stderr line | per stat line | not rendered in v1 | parsable, not parsed | optional later; no command change |

## AB. TUI ↔ Encoder Boundary

| TUI owns | Encoder owns |
|:--|:--|
| screens, navigation, focus, keys | probing, hardware detection |
| editing `EncodeConfig` (validated by the model) | filter graphs, color, LUT, HDR/tonemap |
| rendering progress, logs, queue, QC | x264 params, VBV, 2-pass adaptation |
| log categorisation for display | FFmpeg arguments and process lifecycle |
| provenance labelling | audio / loudnorm |
| terminal size, suspend/resume for Tools | Cineon, enhancement, dithering |
| translating cancel intent into the existing interrupt actions | QC measurement, report writing, output naming |
| | partial-output cleanup, exit codes |

The TUI passes exactly `EncodeConfig.to_namespace()` and must call `_validate_args_consistency` before starting.

## AC. Classic CLI Compatibility

- Classic CLI (`argparse` flags) and the line wizard (`--ui` / no input) are unchanged, including `ResolveProgressHUD` for Cineon and the current batch `Live` table.
- The TUI is a separate entry. Options (decision D-01): **A** a separate module/console script (`python -m ui.tui`, `reels-encoder-tui`) that reuses main's preflight, validation and dispatch after they are extracted into callable functions; **B** a new additive `--tui` flag. A keeps `--help` byte-identical; B is simpler to launch. Recommendation: A. **NEEDS REVIEW** by the owner, including whether `launcher.ps1` gets a third Windows Terminal tab.
- The TUI starts only on an interactive TTY with VT support and ≥ 120 × 40; otherwise it offers the classic wizard.
- Engine functions receive `reporter=None` by default, which selects `ConsoleReporter` = current behaviour.

## AD. Single Live / Worker Architecture

```text
MAIN THREAD                       KEY THREAD                 WORKER THREAD
render loop (one full-screen      stdlib reader (msvcrt /    _encode_single_file(ns, reporter=QueueReporter)
Live, 10 Hz) ◄── events ──┐       termios cbreak)            or batch driver
UIState reducer           │          │ key events              │ engine events
KeyboardInterrupt handler │          ▼                         ▼
                          └──────── one queue.Queue ◄──────────┘
```

- One screen owner: the main thread. The worker never opens a `Live` and never writes to the terminal in TUI mode.
- Engine prints not yet migrated to the reporter must not reach the screen: in TUI mode the global console is redirected to a capture sink that feeds LOG as INFO. This is a safety net, not the design.
- `KeyboardInterrupt` arrives on the main thread (as in `render_queue.run_job`); the handler runs the existing cleanup actions and waits for the worker.
- Tools: the main thread stops the Live and the key thread, restores the terminal, runs the tool, then resumes.
- FFplay meters are detached processes; nothing waits on them.

## AE. 120 × 40 Geometry

| Screen | Header | Main (rows) | Footer | Main regions (cols × rows) |
|:--|:-:|:-:|:-:|:--|
| HOME | 3 | 34 | 3 | banner 118×7 · menu 58×17 + flow 58×17 · SYSTEM 118×5 |
| SOURCE | 3 | 34 | 3 | SOURCE 76×26 + PROGRAM 40×26 · PRÓXIMO 118×4 |
| CONFIGURATION | 3 | 34 | 3 | strip 118×4 · form 72×29 + (PADRÕES 44×14 / AUTOMATION 44×15) |
| ADVANCED | 3 | 34 | 3 | tabs 118×2 · fields 74×29 + SETTINGS 42×29 |
| PREVIEW | 3 | 34 | 3 | card 118×28 (PROGRAM 34×20 + EXPORT SETTINGS 78×20 + chips) · actions 1 |
| READY | 3 | 34 | 3 | hero 118×7 · KEY 58×15 + PLAN 58×15 · QC 118×6 · actions 1 |
| ENCODING | 3 | 34 | 3 | strip 118×1 · header 118×7 · PROGRAM 30×13 + TIMELINE 43×13 + PERFORMANCE 43×13 · LOG 118×11 |
| DETAILS | 3 | 34 | 3 | mini 118×1 · 6 panels 38×15 |
| LOG | 3 | 34 | 3 | mini 1 · tabs 1 · rule 1 · 28 rows · rule 1 · status 1 |
| CANCEL | 3 | 34 | 3 | dashboard + modal 64×12 at main row 11, col 28 |
| BATCH QUEUE | 3 | 34 | 3 | strip 1 · queue 118×20 · ACTIVE 58×11 + LOG 58×11 |
| QC | 3 | 34 | 3 | strip 1 · header 118×5 · EBU 118×9 · MASTER QC 118×14 · DELIVERY 118×5 |
| COMPLETED | 3 | 34 | 3 | hero 118×8 · OUTPUT 58×14 + RESUMO 58×14 · DELIVERY 118×5 · actions 1 |
| ERROR | 3 | 34 | 3 | card 118×8 · stderr 118×19 · ESTADO 118×4 · actions 1 |

## AF. Engineering Constraints

| Constraint (audit) | Consequence for the TUI |
|:--|:--|
| Engine prints to the global console | reporter migration before the TUI ships; capture sink as safety net |
| `_run_encoding` owns Popen + reader + Live | optional `reporter`; in TUI mode skip own Live; hot path, called twice in 2pass |
| Cineon owns its own loop and HUD | same seam; classic path keeps `ResolveProgressHUD` |
| Batch nested Live in `main` | TUI path gets its own batch driver built on `render_queue` state; classic path untouched |
| Native reader relies on text-mode universal newlines; Cineon reads binary | do not change pipes or add `-progress` |
| Reader threads update counters without locks | events are copied into the queue; UI never reads engine objects across threads |
| Ctrl+C on Windows also hits FFmpeg | classify by cancel flag; test on Windows Terminal |
| Existing cancel + partial cleanup (3 retries, locked handle) | reuse, don't reimplement |
| Legacy console → ASCII glyph fallback | keep `theme.glyphs()`; TUI refuses without VT support |
| Hardware detected inside pipelines | no pre-encode hardware display |
| Output naming duplicated (`main`, `EncodeConfig.output_path`) | UI shows `output_path` pre-run and the engine's `done` path after; add a parity test |
| Launcher path must call `_validate_args_consistency` | TUI calls it at START |

## AG. Phase 3 Implementation Sequence

1. Resolve the NEEDS REVIEW items that block steps 2–5 (cancel coverage for Cineon, Ctrl+C during QC, exit codes, entry point choice).
2. Golden tests: classic console output (record mode) for crf, 2pass, Cineon crf/2pass, batch, cancel, error; plus captured FFmpeg argv per scenario.
3. Introduce `Reporter` + `ConsoleReporter`; thread `reporter=None` through `_run_encoding`, Cineon, `_encode_single_file`, QC.
4. Verify zero visible regression (goldens byte-identical, argv identical).
5. `QueueReporter` + worker-thread execution for single file in the TUI path.
6. Cancel and Ctrl+C in the worker model, verified on Windows Terminal (moved earlier than in the draft: the worker model changes where `KeyboardInterrupt` lands).
7. Key reader (stdlib) with signal generation preserved; size guard.
8. Focus model and form components.
9. Screens: HOME → SOURCE → CONFIGURATION/ADVANCED → PREVIEW → READY → ENCODING (+DETAILS, LOG, CANCEL) → QC → COMPLETED → ERROR. The unified dashboard (native + Cineon) is built here, in the TUI only.
10. Batch queue last (highest risk: interrupt, skip-existing, cleanup, exit codes).
11. Windows Terminal verification pass (glyph widths, colours, resize, Tools suspension, FFplay windows).
12. Final parity: same inputs through classic CLI and TUI produce identical argv and, with fixed threads, identical output hashes; QC payloads equal.

---

## AH. Traceability Matrix

| Existing capability / code area | Current behaviour | TUI screen | TUI component | Event needed | Risk | Phase 3 change |
|:--|:--|:--|:--|:--|:--|:--|
| `PRESETS`, `_run_launcher` | numbered menu, typed choice | HOME | menu list | — | low | new screen |
| `ui.preflight`, `ui.binaries` | dependency card, exit 1 | HOME / DEPENDENCY ERROR | SYSTEM strip | — | low | reuse |
| `ask_path` / `ask_folder` | loop until exists, quotes stripped | SOURCE | path field | — | low | port validation |
| `probe_source_dims` | best-effort dims | SOURCE, PREVIEW | PROGRAM | — | low | call off UI thread |
| `_flow_quick/_cineon/_batch` | sequential prompts | CONFIGURATION | form rows | — | low | form per preset |
| `_flow_advanced`, `SECTIONS` | tab bar printed, prompts | ADVANCED | tabs + rows | — | medium (conditional rules, batch reset) | parity test |
| `settings_preview`, chips | printed card | PREVIEW | card | — | low | reuse |
| `Confirm.ask` start/revise | y/n | PREVIEW, READY | buttons | — | low | new screens |
| `_validate_args_consistency` | exit 2 | READY | banner | — | low | call at START |
| `_encode_single_file` stages | rules + prints | ENCODING | stage rail | stage, info, warning | medium | reporter calls |
| `_run_encoding` + `EncodeDashboard` | Live, frame parse | ENCODING | header, TIMELINE | progress, log, pass | medium | reporter kwarg |
| 2pass double call, `_analyze_pass1_log` | two dashboards | ENCODING | pass tracks | pass, analysis | medium | emit at call sites |
| Cineon loop + `ResolveProgressHUD` | legacy HUD | ENCODING (Cineon) | same dashboard | progress, log, pass | medium | reporter in loop |
| psutil perf | gauges | ENCODING | PERFORMANCE | — | low | reuse |
| stderr deque 400/50 | LOG panel, error tail | LOG, ERROR | log view | log, error | low | forward lines |
| x264 config lines | dim prints | DETAILS, LOG | details grid | x264_config | low | emit |
| VBV presets, tiers, loudness | internal | CONFIGURATION (AUTO), DETAILS | automation panel | analysis, hardware | low | emit values |
| `terminate_active_ffmpeg`, Ctrl+C handlers | interrupt + cleanup | CANCEL, CANCELLED | modal | cancel | high | main-thread signalling |
| `render_queue` + batch in `main` | nested Live, capture | BATCH QUEUE | queue table | queue_* , job_* | high | TUI batch driver |
| `run_post_encode_qc`, seal, report | prints, animation, files | QC, COMPLETED | EBU table, seal | qc, meters, done | medium | split data/print |
| `_print_encode_error`, `error_card` | red card, `--debug` | ERROR | error screen | error | low | emit |
| `_flow_tools` | subprocess, Enter | FERRAMENTAS | suspension | — | medium (terminal restore) | suspend/resume |

## AI. Non-Negotiable Preservation List

The TUI implementation must not change: encoding output; FFmpeg command semantics and arguments; VBV behaviour and presets; x264 parameters and 2-pass adaptation; filters; color pipeline, LUTs, HDR/tonemap; audio pipeline and loudnorm; Cineon processing and frame pipeline; enhancement and AI decisions; dithering; QC tests and their meaning; report contents; output naming; skip-existing, output-dir, worker and cleanup behaviour in batch; exit codes; classic CLI output and interaction; line wizard; existing Ctrl+C behaviour; stderr buffers and printed tails; partial-output cleanup; the five user-selectable workflows and their labels; `EncodeConfig` options and defaults.

Allowed to change (TUI path only): presentation, navigation, focus, visual state, interaction model, screen composition.

## AJ. Design Decision Register

| # | Decision | Rationale | Current code support | Implementation impact | Risk |
|:--|:--|:--|:--|:--|:--|
| D-01 | Separate TUI entry (module/script) over a `--tui` flag | keeps `--help` and parser byte-identical | none | extract main's dispatch into functions | medium · NEEDS REVIEW |
| D-02 | 120 × 40 only; size guard below | stated target; one precise layout | Rich measures size | guard screen | low |
| D-03 | No outer frame; 3-row header, 3-row footer | saves space; fewer borders | — | layout shell | low |
| D-04 | Focus = `▎▸` + `tab.active` style | reuses existing active style; shape + colour | `tab.active` | new rows | low |
| D-05 | Digits 1–5 on HOME | keeps today's typed-number habit | `ask_choice` | HOME only | low |
| D-06 | Hidden conditional prompts become disabled rows | stable layout, visible reasons | `_flow_advanced` rules | parity test | low |
| D-07 | `report`, `cineon_lut`, `debug` not exposed | no new options in the interactive path | CLI only | none | low |
| D-08 | PREVIEW and READY are separate | PREVIEW verifies settings; READY shows the run plan and QC scope | preview card + confirm | one extra ENTER vs today | low |
| D-09 | Encoding hotkeys only D, L, C, Ctrl+C | requirement; no pause in engine | Ctrl+C only | key thread | low |
| D-10 | C always confirms; Ctrl+C never | protects long encodes; keeps established interrupt | Ctrl+C path | modal | low |
| D-11 | Cancel disabled during QC | output is complete | — | footer state | low · Ctrl+C in QC NEEDS REVIEW |
| D-12 | One header for both passes; `▓` vs `█`; no combined % | same-job clarity; avoid false precision | two dashboards today | pass events | medium |
| D-13 | No bitrate field in v1 | not parsed today | raw line only | none | low |
| D-14 | Provenance tags in DETAILS | never fabricate values | data exists across functions | seam events | medium |
| D-15 | Stat lines collapsed in display only | readability without losing data | deque unchanged | log view | low |
| D-16 | Cineon unified in TUI only; classic keeps `ResolveProgressHUD` | classic CLI must not change | HUD seam missing | reporter in Cineon loop | medium |
| D-17 | Batch queue replaces nested Live in TUI path only | single screen owner | nested Live today | TUI batch driver | high |
| D-18 | Per-job verdict in RESULT column | payload already returned | not surfaced | qc event per job | medium |
| D-19 | No "Novo encode" loop in v1 | process globals not proven reusable | exits after job | none | low · NEEDS REVIEW |
| D-20 | No background painting; no emoji in fixed regions | matches current look; avoids width bugs | `theme.glyphs()` | none | low |
| D-21 | Motion limited to spinner, pulse, seal reveal | existing motion vocabulary | exists | none | low |

## AK. NEEDS REVIEW Index

1. Entry point: separate script vs `--tui` flag; `launcher.ps1` tab (AC, D-01).
2. `ask_path`/`ask_folder`: file-vs-folder kind distinction (I).
3. Batch folder with zero videos: current behaviour (I).
4. `_flow_advanced` batch branch resetting the config via `preset_batch` (K).
5. Discarding edits when leaving ADVANCED (K).
6. Exact row set of `settings_preview` (L).
7. Sub-step order inside ANALYZING in `run_ffmpeg` / Cineon (D.2).
8. Native pass 1 output target (O).
9. `HardwareProfile` fields for PERFORMANCE/DETAILS (N, AA).
10. VBV triple labels in `VBV_PRESETS` (Q).
11. Flag for `get_video_duration` 30 s fallback (Q).
12. `terminate_active_ffmpeg` coverage of Cineon passes (S).
13. Ctrl+C behaviour during QC (S, U).
14. Partial output after an encoding error (W).
15. Single-file exit codes for error and interrupt (W).
16. `quality_chip(None)` glyph for QC WARNING (U).
17. Reusing the process for a second job (V, D-19).
18. Ctrl+C key-reader behaviour on Windows Terminal (E, AF).
