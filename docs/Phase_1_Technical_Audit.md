# Reels Encoder AI — Terminal UI Technical Audit

> **Documento histórico (Fase 1, 28/09/2026).** Retrato do código *antes* da TUI atual: os números de linha, o wizard de linha (`ui/launcher.py`) e a ausência de TUI descritos aqui não correspondem mais ao repositório. A referência a "masterplan §3.2" aponta para `docs/terminal-ui-masterplan.md`, removido do repositório. **A implementação atual prevalece** — guia de uso em [`tui.md`](tui.md).

Repo `gabrielschoenardie/encoder_ai_instagram` @ `main` · audited 2026-09-28 · read-only, nothing modified.
Line numbers refer to `Reels_Encoder_v2_FINAL.py` (4 649 lines) unless another file is named.

---

## A. Executive Summary

- The app is a **synchronous, single-process Python CLI** (`argparse`) with an **additive Rich-based UI package** (`ui/`). There is **no TUI framework** (no Textual/curses/prompt_toolkit), no raw keyboard handling and no hand-written ANSI; everything is rendered through **Rich** (`Console`, `Panel`, `Table`, `Live`, `rich.prompt`).
- The UI is split into two phases: a **line-by-line prompt wizard** (`ui/launcher.py`) that produces an `argparse.Namespace`, then a **Rich `Live` dashboard** during encode (`ui/dashboard.py`). Prompts never run inside `Live`.
- The **`argparse.Namespace` is already a clean contract** between UI and engine (`ui/config.py::EncodeConfig.to_namespace`). That is the best existing seam.
- The weak point is the other direction: **the engine renders its own output**. Encoding functions call the global `console` directly (rules, hardware table, enhance report, loudnorm messages, errors) and **own the `Live` loop and the FFmpeg subprocess together** (`_run_encoding`, `run_ffmpeg_with_cineon`, batch loop in `main`). There is no event/callback API.
- Progress comes from **parsing `frame=` out of FFmpeg's default stderr stats** (no `-progress`). fps / speed / ETA are **computed in Python** from frame deltas; FFmpeg's own `fps=`, `bitrate=`, `speed=`, `time=` fields are ignored.
- The **Cineon pipeline bypasses the Premiere dashboard** and still uses the legacy `ResolveProgressHUD` (line 3570).
- A more interactive TUI is feasible as a presentation layer if the engine gains an **optional, default-preserving reporter hook**; the encode engine itself (filters, VBV, color, FFmpeg args) does not need to change.

---

## B. Current Architecture

### Entry points
| Entry | What it does |
|---|---|
| `launcher.ps1` (Windows bootstrap) | Creates `./venv`, validates `bin/ffmpeg.exe`/`ffprobe.exe` + `libx264`, `lut3d`, `zscale` (`launch-config.json`), opens Windows Terminal tabs *Setup* (`--hardware-info`) and *Encode* (`--ui`). Passes no encode params. |
| `python Reels_Encoder_v2_FINAL.py [...]` | `main()` (4422) |
| `reels-encoder` console script | same `main()` via `pyproject.toml` |

### Major modules
| Module | Role |
|---|---|
| `Reels_Encoder_v2_FINAL.py` | Monolith: CLI parser, hardware detection, probing, filter-graph builders, x264/VBV params, loudnorm, both pipelines, batch, main dispatch |
| `cineon_pipeline.py` | 5-node float32 film pipeline (DWG → primary → tone/gamut → Cineon log → Portra LUT), dithered quantize |
| `enhance/` | Sampler (5 frames), analyzers (noise/banding/detail), `MockCNN` 13→8→3, `EnhanceProfile`, FFmpeg filter builders, NumPy processors |
| `enhance_visualizer.py` | AI preflight heatmaps, MCTF mask video (own Rich `Progress`) |
| `ebu_meter.py` | Post-encode EBU R128 audit, video checks, FFplay meter windows, report payload |
| `render_queue.py` | Batch job state (`QueueJob`), live table, ETA, worker thread, partial-output cleanup, final report |
| `ui/` | Theme, config model, prompts, components, launcher, dashboard, probe, binaries, preflight, aspect, report (HTML/JSON certificate) |
| `tools/` | Standalone utilities launched from the *Tools* menu via `subprocess.run` |

### Key classes / functions
- `HardwareProfile` (394), `detect_hardware` (416), `_calculate_recommendations` (470), `print_hardware_profile` (542)
- `ResolveProgressHUD` (735), `ffmpeg_live_reader` (793)
- Probing: `get_video_duration` (818), `get_total_frames` (842), `get_input_fps` (900), `get_input_resolution` (950), `VideoProbe`/`probe_video` (1022/1043), `detect_hdr_metadata` (643)
- Audio: `analyze_audio_loudness` (1394), `build_loudnorm_filter` (1493), `_audio_output_args` (1531)
- x264: `_x264_params_string` (1551), `_analyze_pass1_log` (1643), `_adaptive_2pass_x264_params` (1769), `get_vbv_preset` (892)
- Execution: `_run_ffmpeg_tracked` (206), `terminate_active_ffmpeg` (254), `_run_encoding` (2025)
- Pipelines: `run_ffmpeg` (2487), `run_ffmpeg_with_cineon` (3154)
- Dispatch: `_encode_single_file` (4030), `build_parser` (4178), `_validate_args_consistency` (4399), `parse_cli` (4411), `main` (4422)

### Configuration systems
1. **argparse** (`build_parser`) — canonical, ~25 flags.
2. **`EncodeConfig`** (Pydantic v2, `ui/config.py`) — mirrors argparse dest names 1:1, validates choices/ranges, `to_namespace()`/`from_namespace()`, `output_path()` duplicating main's naming.
3. **`launch-config.json`** — bootstrap only (paths, min Python, required encoders/filters).
4. **Env vars** `REELS_FFMPEG/FFPROBE/FFPLAY` — binary pinning (`ui/binaries.py`).

### FFmpeg integration
- Binaries resolved once at import: env → `./bin` → PATH → bare name (`ui/binaries.py`, imported guarded at 176).
- Analysis calls: `subprocess.check_output` (ffprobe) and `_run_ffmpeg_tracked` (registered for Ctrl-C).
- Encode: `subprocess.Popen` in `_run_encoding` (FFmpeg-native) and in `run_ffmpeg_with_cineon` (stdin rawvideo pipe fed by PyAV + NumPy).
- One global `_ACTIVE_FFMPEG` slot guarded by a lock; `terminate_active_ffmpeg()` kills it.

### Logging
- No `logging` module. All output is `console.print` on the global themed console (160–164).
- FFmpeg stderr kept in bounded deques (400 lines native, 50 lines Cineon).
- AI decisions appended to `enhance_ai_log.json`.
- Batch captures each job's console output with `console.capture()` into `QueueJob.log` (truncated to 4 000 chars in the final report).

### Error handling
- `CalledProcessError` raised with collected stderr on non-zero exit; last 40 (native) / 50 (Cineon) lines printed in red.
- Top-level: `_print_encode_error` → `ui.components.error_card` (hint to use `--debug`), traceback only with `--debug`.
- Soft failures (preflight heatmaps, MCTF, EBU audit) are caught and printed as yellow warnings; the encode continues.
- Missing FFmpeg → `dependency_error_card`, exit 1.

### Input / output handling
- Single: input path must exist; output next to input: `_Cineon_Film.mp4` / `_Hollywood_CRF18.mp4` / `_Hollywood_2Pass.mp4`.
- Batch: `find_video_files(folder)`; output to `--output-dir` or same folder; **existing outputs are skipped** (`pulado`).
- Post-encode: `<base>.qc.html` + `<base>.qc.json` when `--report on`.

---

## C. Current Terminal UI

### Files that control the UI
| File | Responsibility |
|---|---|
| `ui/theme.py` | `PALETTE`, Rich `THEME` named styles, box constants, Unicode/ASCII glyph tables, `get_console()` |
| `ui/components.py` | Pure renderables: `banner`, `tab_bar`, `_aspect_frame`/`viewer_frame`, `program_panel`, `program_split`, `properties_panel`, `info_card`, `quality_chip`/`quality_row`, `log_panel`, `job_strip`, `gauge_bar`, `notification`, `error_card`, `dependency_error_card`, `settings_preview`, `delivery_seal`, `_seal_reveal_frame`, `play_delivery_seal` |
| `ui/prompts.py` | `render_choice_menu`, `ask_choice`, `ask_path`, `ask_folder`, `ask_toggle`, `ask_select`, `ask_number` |
| `ui/launcher.py` | `run_launcher` → `_run_launcher`, `_flow_quick`, `_flow_cineon`, `_flow_batch`, `_flow_tools`, `_flow_advanced` |
| `ui/dashboard.py` | `EncodeDashboard` (duck-types `ResolveProgressHUD`), `make_dashboard` |
| `render_queue.py` | `build_table`, `render_final_report` (batch UI — **not themed**, uses raw `[green]`/`[red]`/`[bold magenta]`) |
| `ebu_meter.py` | ANTES/DEPOIS audit table + `play_delivery_seal` |
| Engine | `print_hardware_profile`, `print_enhance_report`, `ResolveProgressHUD`, dozens of inline `console.print`/`console.rule` |

### How menus work
- `render_choice_menu` prints a rounded panel of numbered options (`" 1 "` in `tab.active` style + label).
- `ask_choice` then calls `rich.prompt.Prompt.ask("> ", choices=["1".."n"])`. The user **types a number and presses Enter**.
- Toggles use `Confirm.ask` (y/n); selects use `Prompt.ask(choices=[...])` (type the literal value); numbers loop until valid.

### Input capture / keyboard
- **Line-buffered `input()` via `rich.prompt`**. No arrow keys, no hotkeys, no raw mode, no `msvcrt`/`termios`, no key listener during encode.
- Ctrl-C and EOF are the only "keys" handled: `run_launcher` catches `EOFError`/`KeyboardInterrupt` → "Cancelado pelo usuário." and returns `None`.

### Output refresh
- Wizard: **append-only scroll** — every tab bar, menu and preview card is printed below the previous one. Nothing is cleared or redrawn.
- Encode: `rich.live.Live(hud.render(), refresh_per_second=7)` with a manual `live.update(hud.render())` every 100 ms (native) or every frame (Cineon).
- Batch: outer `Live(table, refresh_per_second=4)` refreshed by `on_tick` every 250 ms.
- Seal: short transient `Live` (24 steps / 1.2 s, 30 fps) then static print.

### State model
- **Not state-based.** The wizard is imperative control flow; state is a single mutable `EncodeConfig` passed through flows. The dashboard holds counters (`current_frame`, `fps`, `eta`...) but no screen/focus state. `SECTIONS` tabs are printed as a progress marker, not navigable.

### ANSI / TUI framework
- No direct ANSI escapes. No alternate screen buffer. No TUI framework. Rich handles color downgrade; `theme.glyphs()` downgrades to ASCII on legacy Windows / non-UTF-8 consoles; `_ensure_utf8_streams()` reconfigures stdout/stderr.

---

## D. Current User Flow

| Stage | What the user sees | Expected input | Handler | State created/modified |
|---|---|---|---|---|
| Launch | Nothing yet | CLI args (or none) | `main` → `parse_cli` | `args` Namespace |
| `--hardware-info` | Rule "🔧 Hardware Detection" + table | — | `detect_hardware`, `print_hardware_profile` | exits 0 |
| Preflight | Red DOUBLE-box "DEPENDÊNCIA AUSENTE" only on failure | — | `ui.preflight.missing_ffmpeg_binaries`, `dependency_error_card` | exit 1 on missing |
| Launcher trigger | — | `--ui` or no input & no `--batch` | `main` 4459 | — |
| Banner | DOUBLE-box slate, gradient letter-spaced "R E E L S   E N C O D E R", subtitle "Premiere Workspace · UI interativa · v2.1.0" | — | `C.banner` | — |
| Preset menu | "Selecione um fluxo" 1–5 | number, default 1 | `ask_choice` | `preset` int |
| Source selection | Prompt "Arquivo de vídeo de entrada" / "Pasta com os vídeos" | path (quotes stripped), loops until it exists | `ask_path` / `ask_folder` | `cfg.input` / `cfg.batch` |
| Configuration (preset) | Sequential prompts per preset (see §E) | select / number / y-n | `_flow_quick` / `_flow_cineon` / `_flow_batch` | `EncodeConfig` fields |
| Configuration (advanced) | Tab bar printed before each group: Source → Color/LUT → Audio → Enhance → Export; ~18 prompts, conditional on Cineon / enhance / AI | per prompt | `_flow_advanced` | deep-copied `EncodeConfig` |
| Tools | "Ferramentas" menu, runs script, "Pressione Enter para continuar" | number, Enter | `_flow_tools` (subprocess, cwd repo root) | loops back to preset menu |
| Preview | Violet-bordered card "PREVIEW · src → out": Program monitor (aspect frame from `ffprobe`), EXPORT SETTINGS properties, quality chips row | — | `probe_source_dims`, `C.settings_preview` | `src_dims` |
| Confirm | "Iniciar encode com estas configurações?" → if no, "Revisar configurações?" → advanced flow again | y/n | `_run_launcher` loop | returns Namespace or `None` |
| Validation | Red "Erro:" line on failure | — | `_validate_args_consistency` (only `--output-dir` without `--batch`); Pydantic already validated ranges | exit 2 |
| Pre-encode analysis | Yellow rule "🎬 Encode CRF 18 / 2-Pass - Hollywood LUT Transport" or magenta "🎬 Encode Cineon Film Emulation Pipeline"; hardware table; source aspect; enhance/AI analysis + report; dither note; loudnorm pass-1 message; x264 diagnostics | — | `_encode_single_file`, `run_ffmpeg`, `run_ffmpeg_with_cineon` | probe, hw profile, enhance profile, loudness stats, filter graph, cmd |
| Encoding / progress | FFmpeg native: job strip + "🎞 ENCODING" progress panel + Program viewer + TIMELINE + PERFORMANCE + LOG (Premiere dashboard). 2-pass: dashboard runs twice. Cineon: legacy plain HUD (Frame/FPS/Speed/ETA + green bar) | Ctrl-C only | `_run_encoding` + `EncodeDashboard` / Cineon loop + `ResolveProgressHUD` | HUD counters, `stderr_tail` |
| Completion | EBU ANTES/DEPOIS table, animated MASTER QC seal (DELIVERY READY / REVISAR ENTREGA), optional 2 FFplay meter windows, `.qc.html/.qc.json` written | close FFplay windows | `ebu_meter.run_post_encode_qc`, `play_delivery_seal`, `ui.report.write_report` | report files |
| Batch | Listing of files, live table "Job n de N · ETA", per-job encode output captured (not shown live), final report | Ctrl-C | batch block in `main`, `render_queue.*` | `QueueJob` list |
| Error | Red FFmpeg tail + `error_card` | — | `_run_encoding`, `_print_encode_error` | exit code |
| Cancellation | "⚠ Encode interrompido pelo usuário" / "⚠ Fila interrompida…", partial output removed (3 retries) or red warning if file is locked | Ctrl-C | `main` except blocks, `terminate_active_ffmpeg`, `discard_partial_output` | exit 130 in batch |

---

## E. Encoding Engine

### Launcher presets (the actual "profiles" exposed to users)
Base is `EncodeConfig()` defaults: `mode=crf, fps=30, scale=auto, fit=contain, performance=balanced, threads=0, lut=on, hdr=auto, tonemap=mobius, loudnorm=on, ebu_meter=on, cineon=off, exposure=0.0, saturation=1.0, enhance=on, enhance_ai=off, mctf=off, dither=auto, report=on, show_hardware=on`.

| Preset | Factory | Forces | Then asks |
|---|---|---|---|
| 1 · Encode rápido (FFmpeg) | `preset_quick_ffmpeg` | `cineon_pipeline=off, mode=crf, lut=on` (identical to defaults) | fit, fps, mode |
| 2 · Film look (Cineon) | `preset_film_cineon` | `cineon_pipeline=on, mode=crf` | exposure (−2..+2), saturation (0..2), fit |
| 3 · Batch de pasta | `preset_batch` | `batch=folder, cineon=off, mode=crf, lut=on` | separate output dir?, Cineon on/off |
| 4 · Tools | — | runs `tools/*.py` | — |
| 5 · Configurar avançado… | `_flow_advanced` | nothing | every option across 5 tabs |

### Engine-side automatic profiles (not user-selectable)
- **VBV presets by duration** (`VBV_PRESETS`, 290): ultra_short ≤15 s 10 000/11 200/15 000 kbps; short ≤30 s 9 800/11 000/14 850; medium ≤45 s 8 500/9 500/12 825; long ≤60 s 8 000/9 000/12 150; extra_long ≤90 s (and fallback) 6 500/7 500/10 125; all `vbv_init 0.9`. Ingest caps 12 000 avg / 15 000 peak.
- **Hardware tiers** (`HARDWARE_TIERS`): ultra (≥16 cores/32 GB, veryslow, lookahead 120), high (≥6/16, slow, 90), medium (≥4/8, medium, 60), low (≥2/4, fast, 60); lookahead also made fps-aware (`_fps_aware_lookahead`).
- **Loudness targets** (`LOUDNORM_TARGETS`): instagram −14 LUFS / −1.5 dBTP / LRA 11 (the only one used by the pipelines); youtube, broadcast defined.
- **Tonemap** mobius / reinhard / hable; **performance** quality / balanced / speed (mapping inside `run_ffmpeg` not audited in detail — out of UI scope).
- **Output naming** encodes the profile: `_Cineon_Film`, `_Hollywood_CRF18`, `_Hollywood_2Pass`.

### Orchestration
`_encode_single_file` → optional AI preflight heatmaps → optional MCTF mask video → dither flag → `run_ffmpeg(...)` or `run_ffmpeg_with_cineon(...)` (both take ~15 keyword args mapped from `args`) → `run_post_encode_qc(...)`. All blocking, all on the calling thread.

---

## F. FFmpeg Progress Architecture

| Aspect | FFmpeg-native (`_run_encoding`) | Cineon (`run_ffmpeg_with_cineon`) |
|---|---|---|
| Source | FFmpeg default stats on **stderr** (no `-progress`, no `-stats_period`) | Python's own `frame_count` after each frame is written to stdin; stderr `frame=` also parsed |
| Pipe | `stderr=PIPE, text=True, encoding=utf-8, errors=ignore`, stdout → DEVNULL | `stdin=PIPE`, `stderr=PIPE` **binary**, stdout → DEVNULL |
| Reader | `ffmpeg_live_reader` daemon thread, `iter(pipe.readline, "")` — text mode's universal newlines split FFmpeg's `\r` stat lines | nested `ffmpeg_stderr_reader` thread, `readline` on bytes (splits on `\n` only, so `\r` stats arrive in bursts; harmless because the main loop updates from `frame_count`) |
| Parsed fields | `frame=` only (digits filtered) | `frame=` only |
| Ignored fields | `fps=`, `q=`, `size=`, `time=`, `bitrate=`, `speed=`, `dup/drop` | same |
| fps | `Δframe / Δt` between consecutive updates, floor 0.1 (instantaneous, not smoothed) | same |
| speed | `fps / source_fps` | same |
| total frames | `get_total_frames`: container `nb_frames`, else `duration × r_frame_rate`, else `duration × 30` | `round(duration × output_fps)` |
| ETA | `remaining_frames / fps`, formatted `HH:MM:SS` | same |
| Duration | `get_video_duration` (ffprobe, fallback 30 s) | same |
| Extra | x264 config lines (`rc lookahead`, `ref frames`, `keyint`, `b frames`) printed dim above the Live region | — |
| Refresh | Live 7 Hz + manual update every 100 ms | Live 7 Hz + update **every frame** |
| Dashboard | `make_dashboard` (Premiere), fallback `ResolveProgressHUD` | **always `ResolveProgressHUD`** |
| 2-pass | Pass 1 and pass 2 each get a fresh dashboard, both titled "ENCODING" | pipeline rendered twice |

**Stderr preservation:** yes. Every stderr line goes into `stderr_tail` (`deque(maxlen=400)` native / `50` Cineon) and is attached to `CalledProcessError.stderr`; the tail (40 / 50 lines) is printed on failure. The same deque feeds the dashboard's LOG panel (last 5 lines), which means the LOG panel shows raw FFmpeg stat lines, not curated events.

---

## G. Existing Design System

**Concept:** Adobe Premiere Pro workspace (masterplan §3.2) with the "Hollywood Mastering Suite" delivery seal adopted as a post-encode accent.

### Palette (`ui/theme.py::PALETTE`)
| Token | Hex | Use |
|---|---|---|
| ink | `#13141a` | background reference (not painted in terminal; painted in HTML certificate) |
| indigo | `#5b6cff` | primary, panel borders, active tab bg, bar fill |
| violet | `#a06bff` | accent, titles, panel titles, bar pulse, preview card border |
| cyan | `#33d6e0` | info, dims, output path, perf values |
| amber | `#ffb454` | warn, cover-crop markers, gauge 60–85 % |
| green | `#3ddc84` | ok chips, gauge < 60 % |
| red | `#ff5c7a` | errors, gauge ≥ 85 % |
| gold | `#d4af37` | DELIVERY READY seal |
| text | `#e6e8ef` | values (bold) |
| muted | `#8a8fa3` | labels, inactive tabs, bar background, log text |

### Named styles
`primary` bold indigo · `accent` violet · `info` cyan · `ok/warn/err` bold green/amber/red · `title`, `panel.title` bold violet · `label` muted · `value` bold text · `seal` bold gold · `*.dim` variants · `tab.active` bold ink on indigo · `tab.inactive` muted · `panel.border` indigo · `bar.complete` indigo · `bar.pulse` violet · `bar.back` muted.

### Structure
- Boxes: `PANEL_BOX = ROUNDED` (standard panels), `HEAVY_BOX = DOUBLE` (banner, dependency error, MASTER QC), `GRID_BOX = SIMPLE` (tab bar, job strip, toasts).
- Panel titles: UPPERCASE, left-aligned (`PROGRAM`, `EXPORT SETTINGS`, `TIMELINE`, `PERFORMANCE`, `LOG`, `MASTER QC`, `PREVIEW · …`).
- Padding: `(1, 2)` for content panels, `(0, 1)` for strips/log, `(0, 2)` for the progress header.
- Label/value grids: label column right-aligned muted, value column bold text; column gap 1–2.
- Letter-spaced headlines: `R E E L S   E N C O D E R`, `D E L I V E R Y   R E A D Y`, `R E V I S A R   E N T R E G A`.
- Gradient: per-character indigo → violet on the banner title and a 28-block `█` bar.

### Indicators & glyphs
`✓ ⚠ ✗ ● ▸ ★ █ ░ ▎ 🎞 🎧 ✨` with ASCII fallbacks `OK ! x * > * # - | [F] [A] *`.
- Quality chip: `✓ label` ok / `⚠ label` warn / `● label` muted-neutral.
- Active tab: ` ▎ Name ` on indigo; inactive: ` Name ` muted.
- Menu index: ` 1 ` in tab.active style.
- Progress: braille spinner `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (ASCII `|/-\`) + 40-cell `█/░` bar with a 3-cell violet pulse sweeping the filled part + `  64.0%`.
- Gauge: 12-cell `█/░`, green / amber / red at 60 / 85 %.
- Program monitor: aspect-shaped frame (portrait 16 cols, square 18, landscape 28); `contain` = `░` letterbox rows, `cover` = violet `█` edges with amber `●` crop marks.
- Batch statuses (`render_queue.py`, off-theme): `· ⏳ ✓ ✗ ○ ⚡`.

### Hierarchy
job strip (identity) → progress header (violet border) → three-column Program / Timeline / Performance → Log strip. Wizard: banner → menu → tab bar → prompts → preview card.

**Inconsistencies to be aware of** (not changes, just facts): Cineon HUD and `render_queue` tables use Rich default colors (`[cyan]`, `[green]`, `[magenta]`, `SIMPLE_HEAD` box) instead of the theme; engine rules use `bold yellow` / `bold magenta` / `bold cyan`; prompts' `[dim]` "Pressione Enter" isn't a theme token.

---

## G.2 Responsiveness

- **Width:** Rich auto-detects terminal width on each render. `program_split` and the dashboard columns use `Table.grid(expand=True)` with `ratio=1` columns; the aspect frame has a **fixed width** (`w + 4` = 20/22/32 cols); banner and preview card stretch to console width.
- **Height:** not considered. `Live` renders in the normal buffer; if the dashboard is taller than the terminal, Rich crops/scrolls (default `vertical_overflow="ellipsis"`).
- **Wrapping:** Rich wraps text; paths are middle-elided (`_short_path`, 30 chars) to protect panel titles.
- **Responsive layout:** only the "viewer present / absent" branch in the dashboard (3 vs 2 columns). No breakpoints.
- **Minimum size:** no check, no warning. Narrow terminals will squeeze the three columns.
- **Resize:** Rich re-measures at each refresh (7 Hz), so resizes are picked up during `Live`; the wizard's already-printed output isn't reflowed.

---

## G.3 Dependencies (UI-relevant)

| Concern | Library |
|---|---|
| Terminal rendering, colors, panels, tables, rules, columns, alignment | `rich` ≥13 |
| Live refresh | `rich.live.Live` |
| Progress bars | hand-drawn `rich.text.Text` (`EncodeDashboard._progress_bar`, `gauge_bar`); `rich.progress.Progress` only in `enhance_visualizer.py` |
| Keyboard / input | `rich.prompt.Prompt` / `Confirm` (built on `input()`) |
| Terminal dimensions | Rich `Console` auto-detection; `ebu_meter._get_screen_size` for FFplay window placement (screen, not terminal) |
| Perf metrics | `psutil` |
| Config validation | `pydantic` v2 |
| Threads | stdlib `threading`, `collections.deque` |
| Encoding I/O | `subprocess`, `av` (PyAV), `numpy`, `colour-science`, optional `cv2` |
| Terminal host | Windows Terminal (portable, in `bin/WindowsTerminal`) or PowerShell fallback |

---

## H. UI ↔ Encoder Coupling

| # | Coupling point | Where | Nature |
|---|---|---|---|
| 1 | **Shared global `console`** | 160–164; used everywhere | Engine functions print directly (rules, hardware table, enhance report, loudnorm, dither, errors, x264 diag). A TUI owning the screen would be written over. |
| 2 | **`_run_encoding` owns subprocess + reader thread + `Live` + HUD** | 2025–2094 | Process lifecycle and rendering are one function. No way to observe progress without also rendering. |
| 3 | **Cineon loop owns decode + pipe + `Live` + HUD** | 3570–3700 | Same, plus hard-coded `ResolveProgressHUD` (no seam at all). |
| 4 | `ffmpeg_live_reader` prints | 816 | A reader thread writes to the console. |
| 5 | **Batch loop in `main()` owns `Live` table** | 4522–4590 | Queue presentation lives in the entry point; per-job `_run_encoding` opens a second `Live` inside a worker thread under `console.capture()`. |
| 6 | Post-encode QC prints + animates + spawns FFplay | `ebu_meter.run_post_encode_qc` | QC measurement and presentation are one call. |
| 7 | Engine imports UI pieces guarded | 160, 169, 176, 2037, 4165, 4439, 4460 | Good: additive, falls back. |
| 8 | **Namespace contract** | `EncodeConfig.to_namespace` → `main` → `_encode_single_file` | Good seam, UI → engine, already validated by Pydantic + `_validate_args_consistency`. |
| 9 | Output-name logic duplicated | `main` (4494, 4602), `EncodeConfig.output_path` | Drift risk if one changes. |
| 10 | Hardware detection happens inside pipelines | 2520, 3248 | Can't show hardware in the UI before encode without calling it twice. |

Layer map today:
```
UI ............ ui/launcher, ui/prompts, ui/components, ui/dashboard, render_queue.build_table
interaction ... rich.prompt (line input), Ctrl-C
app state ..... EncodeConfig → argparse.Namespace   (clean)
orchestration . main() batch/single, _encode_single_file      ← prints
FFmpeg ........ _run_encoding / Cineon loop                   ← renders Live + owns Popen
output ........ ebu_meter QC + ui.report                      ← prints + animates
```

---

## I. Architectural Risks

| Risk | Detail |
|---|---|
| **Blocking input** | All prompts are blocking `input()`; there is no non-blocking key reader. Adding hotkeys during encode needs a background key thread (`msvcrt` on Windows, `termios`/`tty` on POSIX — stdlib, but platform-specific). |
| **Two writers, one screen** | Any engine `console.print` while a full-screen/alt-screen TUI is active will corrupt it. Today Rich `Live` tolerates prints (it redraws below them); a custom full-screen layout will not. |
| **Nested Live** | Batch runs `_run_encoding`'s `Live` inside a worker thread while the queue's `Live` is active on the same console, under `console.capture()`. Behaviour depends on the Rich version; `FINDINGS.md` VF1 already documents flicker from two live displays (MCTF `Progress` + queue table). |
| **Subprocess handling** | Single `_ACTIVE_FFMPEG` slot; `_run_ffmpeg_tracked` saves/restores it. Parallel jobs or a UI-spawned probe would need care. Cineon has its own terminate/kill path (3720) separate from `terminate_active_ffmpeg`. |
| **stderr/stdout** | Native reader relies on text-mode universal newlines to split `\r`; switching to binary or adding `-progress pipe:1` changes parsing. Stats go to the same deque as errors, so the LOG panel and the error tail are the same data. |
| **Threading** | Reader threads are daemons updating HUD counters without locks (single-writer ints, currently safe under the GIL). Batch encode runs in a worker thread; `KeyboardInterrupt` is delivered only to the main thread (handled in `run_job`). |
| **Async** | None; introducing asyncio would touch every blocking call. |
| **Cursor control** | Rich `Live` hides the cursor and redraws in place; a crash inside `Live` can leave the cursor hidden on some Windows hosts. No alternate screen used today. |
| **Signals / cancellation** | Only Ctrl-C. On Windows, Ctrl-C is also delivered to the FFmpeg child in the same console group, so FFmpeg may exit before Python's handler runs (see STATE.md CTRL_C_EVENT notes). No pause/resume. Partial-output removal retries for locked handles. A UI "Cancel" button must reuse `terminate_active_ffmpeg` + `discard_partial_output` to keep parity. |
| **Windows compatibility** | Legacy conhost: no truecolor/emoji → ASCII glyph fallback exists; the `🎞 🎧 ✨` emoji are double-width and can misalign fixed-width frames. Windows Terminal is the primary target. Raw key input differs per platform. |
| **FFplay windows** | Launched non-blocking after encode; a TUI that stays open must not assume focus. |
| **Validation bypass** | Launcher path skips `parser.parse_args` but is re-validated by `_validate_args_consistency` (FINDINGS ALF1 fixed). Any new UI must keep calling it. |

---

## J. Proposed Future TUI Architecture

Principle: the encoder stays the source of truth; the TUI only **produces a Namespace** and **consumes events**.

```
┌──────────────────────────────────────────────────────┐
│ INTERACTIVE TUI (ui/)                                 │
│  screens: Home · Configure (tabs) · Preview ·         │
│           Encode · Queue · QC                         │
│  main thread: render loop (Rich Live, one only)       │
│             + key reader thread (stdlib)              │
│  state: UIState { screen, focus, EncodeConfig, jobs,  │
│                   progress, log, qc }                 │
└───────────────┬───────────────────────▲───────────────┘
   Namespace    │                       │ events (queue.Queue)
   + cancel()   ▼                       │
┌──────────────────────────────────────────────────────┐
│ REPORTER SEAM (new, tiny)                            │
│  Reporter protocol: stage(name) · info/warn(msg) ·   │
│  probe(dict) · progress(frame,total,fps,speed,eta) · │
│  log(line) · qc(checks, ready) · done(path) · error  │
│  ConsoleReporter = today's behaviour (default)       │
│  QueueReporter   = pushes events to the TUI          │
└───────────────┬──────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────┐
│ EXISTING ENCODER (unchanged logic)                    │
│  _encode_single_file · run_ffmpeg · Cineon · QC       │
│  profiles / VBV / color / filters / FFmpeg args       │
└──────────────────────────────────────────────────────┘
```

Key points:
1. **One screen owner.** The TUI holds the only `Live`. The engine never opens its own `Live` when a non-console reporter is active; `_run_encoding` and the Cineon loop call `reporter.progress(...)` instead of `live.update`.
2. **Default path unchanged.** `ConsoleReporter` wraps the exact current prints and `Live` usage, so CLI output stays byte-identical.
3. **Engine runs in a worker thread**, like `render_queue.run_job` already does; the main thread renders and reads keys. Cancel = `terminate_active_ffmpeg()` + `discard_partial_output()` (same as Ctrl-C today).
4. **Progress stays frame-based** (current math in `EncodeDashboard.update_frame`) so numbers match today; optionally also forward FFmpeg's `bitrate=`/`speed=` fields from the same stderr line later, without changing the command.
5. **Rich only, no new dependencies**: Rich `Layout` + `Live(screen=True)` for a full-screen mode, keyboard via `msvcrt` (Windows) / `termios` (POSIX). Line-prompt wizard remains as fallback for dumb terminals and piped stdin.
6. **Design language reused as-is** from `ui/theme.py` and `ui/components.py`; Cineon HUD and batch table get the same components.

---

## K. Minimal File Change Plan

| # | File / function | Change | Risk |
|---|---|---|---|
| 1 | `ui/state.py` (new) | `UIState` dataclass, pure | SAFE |
| 2 | `ui/events.py` (new) | `Reporter` protocol, `ConsoleReporter`, `QueueReporter` | SAFE |
| 3 | `ui/keys.py` (new) | stdlib key reader (`msvcrt` / `termios`), fallback to line input | LOW RISK (platform code, isolated) |
| 4 | `ui/screens/*.py` (new) | Screens built from existing `components.py` renderables | SAFE |
| 5 | `ui/components.py` | Add renderables (queue table, stage list, focus states); keep existing signatures | SAFE |
| 6 | `ui/launcher.py` | Add interactive path behind a capability check; keep `run_launcher()` contract (returns Namespace/None) | LOW RISK |
| 7 | `ui/dashboard.py` | Accept events instead of only `update_frame`; keep duck-typed API | LOW RISK |
| 8 | `render_queue.py::build_table` | Themed version in `ui/`, original kept for CLI | SAFE |
| 9 | `_run_encoding` (2025) | Optional `reporter=None` kwarg; if set, skip own `Live`, forward progress/log | MEDIUM RISK (hot path, 2-pass calls it twice) |
| 10 | Cineon loop (3570–3700) | Same optional reporter; route through `make_dashboard` seam | MEDIUM RISK (frame loop, pipe, interrupt path) |
| 11 | `_encode_single_file` (4030) / `run_ffmpeg` / `run_ffmpeg_with_cineon` | Thread `reporter` through; replace direct `console.print` with `reporter.info/warn` whose console implementation prints the identical string | MEDIUM RISK (many call sites; must stay byte-identical) |
| 12 | `ebu_meter.run_post_encode_qc` | Return checks/payload to reporter instead of only printing | LOW RISK |
| 13 | `main()` batch block (4480–4595) | When TUI is active, delegate queue presentation to the TUI; CLI path untouched | HIGH RISK (interrupt, skip-existing, partial cleanup, exit codes) |
| 14 | `main()` launcher branch (4459) | Choose interactive vs line wizard | LOW RISK |
| — | VBV, x264, filters, color, loudnorm, FFmpeg args, output naming | **No change** | — |

---

## L. Recommended Implementation Sequence

1. **Freeze behaviour:** add golden-output tests for CLI console text (record mode) for single CRF, 2-pass, Cineon, batch, cancel. Gate every later step on them.
2. **Reporter seam, console-only:** introduce `ConsoleReporter` and thread it through `_run_encoding` → `_encode_single_file` with zero visible change. Verify goldens.
3. **Unify dashboards:** route the Cineon HUD through `make_dashboard` (visual change only in `--ui`/default path; decide whether classic CLI keeps `ResolveProgressHUD`).
4. **Worker-thread encode + QueueReporter** for single-file in the UI path only; main thread owns the single `Live`. Cancel via existing `terminate_active_ffmpeg` / `discard_partial_output`.
5. **Key reader** (stdlib) + focus model; keep line prompts as fallback (non-TTY, legacy console, `--ui --classic` style switch).
6. **Interactive screens** (Configure tabs, Preview, Encode, QC) built from existing components.
7. **Batch/Queue screen** last, replacing the nested-Live arrangement in the UI path only.
8. **Min-size handling** (warn below N×M, collapse viewer column) and Windows Terminal + legacy PowerShell verification.

Open items to confirm before the visual/interaction spec: target minimum terminal size; whether classic CLI output must stay byte-identical (recommended) or may adopt the theme; whether hotkeys during encode (pause is **not** supported by the engine today — only cancel) are in scope.
