# Terminal UI Masterplan — Premiere-Style Interactive Encoder

> Detailed Implementation Plan for transforming `Reels_Encoder_v2_FINAL.py` into a
> commercial / cinematic-grade product with a modern, interactive terminal experience.
>
> **Status:** Approved · **Author:** Senior Software Architect (Terminal UX) ·
> **Scope:** Additive UI layer (engine untouched) · **Winner concept:** Adobe Premiere Pro Style

---

## 1. Executive Summary

The encoder is a powerful but headless tool: a 4.300-line `argparse` monolith that prints
linear Rich output. This plan adds a **premium interactive layer** without rewriting the
engine:

- An **interactive launcher / wizard** (source → preset → tabbed config → settings preview →
  encode), triggered when the script runs with no work specified or with `--ui`.
- An **upgraded live encode dashboard** (progress, fps/speed/ETA, performance monitor,
  live log) built on Rich `Live`.
- A **cohesive Adobe-Premiere-Pro visual identity** (indigo/violet accent, tabbed header,
  right-side properties panel, card-based quality control).

**Design constraints (locked with stakeholder):**

1. Hybrid interaction (launcher + Rich Live), **not** a full-screen Textual app.
2. **Additive** — the engine monolith is not restructured.
3. **100% backward-compatible CLI** — every existing `argparse` command behaves identically.
4. Visual concept: **Adobe Premiere Pro Style** (the other two concepts are documented for
   comparison but not built).

---

## 2. Current Architecture (as-is)

```
Reels_Encoder_v2_FINAL.py  (~4.300 lines, argparse, ~25 flags)
├─ console = Console()                      # global Rich console (:153)
├─ detect_hardware / print_hardware_profile # hardware profile (:285/:411)
├─ ResolveProgressHUD                       # frame/fps/ETA HUD (:604)
├─ ffmpeg_live_reader(pipe, hud, sink)      # parses `frame=` from stderr (:662)
├─ _run_encoding(cmd, total_frames, fps)    # Popen + Live(hud) loop (:1849)
├─ run_ffmpeg(...)                          # FFmpeg native pipeline (:2224)
├─ run_ffmpeg_with_cineon(...)              # Cineon film pipeline (:2942)
├─ find_video_files(folder)                 # batch discovery (:3834)
├─ _encode_single_file(in, out, args)       # single-file dispatch (:3858)
└─ main()                                    # argparse + batch/single dispatch (:3995)

ebu_meter.py        # post-encode EBU R128 QC (Rich tables ANTES/DEPOIS)
cineon_pipeline.py  # frame-by-frame film pipeline
enhance/            # AI enhancement module (+ pytest suite)
```

**Already present:** Rich (`Console`, `Live`, `Table`, `Panel`, `Confirm`), psutil, a working
frame-progress HUD, and a clean post-encode QC module. This is the foundation the UI builds on.

**Pain points the UI addresses:** no interactivity, no settings preview before a long encode,
no performance monitoring, no visual configuration, ad-hoc styling scattered across `console.print`.

---

## 3. Visual Concepts (comparison)

Three concepts were designed. Each is scored on UX fit, Windows-terminal feasibility, and
implementation complexity. **Premiere wins** (see §3.4).

### 3.1 Concept A — DaVinci Resolve Style

Dark, dense, color-centric. Node-graph metaphor (IDT → LUT → ODT), scopes (waveform/vectorscope
glyphs), teal/orange accents. Echoes the existing `ResolveProgressHUD` naming.

```
┌─ NODES ───────┬─ VIEWER ──────────┬─ SCOPES ────────┐
│ ● IDT         │   ┌───────────┐   │ Waveform        │
│ ● LUT  Hollyw │   │  9:16     │   │ ▁▂▃▅▇█▇▅▃▂▁     │
│ ● CAS  0.35   │   │  preview  │   │ Vectorscope     │
│ ● ODT  +dith  │   └───────────┘   │   · ·  ·        │
├───────────────┴───────────────────┴─────────────────┤
│ TIMELINE  ████████████░░░░ 64%  fps 42  ETA 00:18    │
└──────────────────────────────────────────────────────┘
 [F5] Render   [Space] Pause   [Tab] Panel
```

- **Components:** node list, viewer placeholder, scopes panel, timeline progress, transport bar.
- **Nav flow:** Tab cycles panels → Enter edits node params → F5 renders.
- **Palette:** graphite `#1b1d23` bg, teal `#00b3c8`, orange `#ff7a29`, muted grey text.
- **UX rationale:** familiar to colorists; scopes feel "broadcast-grade".
- **Implementation complexity:** **High** — scopes/viewer imply real-time frame sampling to be
  honest; faking them undercuts the premium claim.

### 3.2 Concept B — Adobe Premiere Pro Style  ★ WINNER

Tabbed workspace (Source · Effects · Export), right-side **Properties** panel, timeline-style
progress, indigo/violet identity. Maps cleanly to a wizard + dashboard built from Rich panels.

```
╔═ REELS ENCODER ════════════════════ Premiere Workspace ═╗
║ [ Source ] [ Color/LUT ] [ Audio ] [ Enhance ] [ Export ]║
╠──────────────────────────────────┬──────────────────────╣
║  PROGRAM                          │  PROPERTIES          ║
║  in:  IMG_9245.mov  4K HDR        │  Resolution 1080×1920║
║  out: ..._Hollywood.mp4           │  Aspect     9:16     ║
║  ┌────────────────────────────┐   │  LUT        Hollywood║
║  │        9:16 target         │   │  Codec      x264 CRF18║
║  └────────────────────────────┘   │  Audio      −14 LUFS ║
║                                   │  Enhance    AI: off  ║
╠──────────────────────────────────┴──────────────────────╣
║ TIMELINE ███████████████░░░░░ 64%  fps 42 · 1.4x · 00:18 ║
║ LOG  ▸ x264: rc-lookahead 40   ▸ tonemap mobius npl 200  ║
╚══════════════════════════════════════════════════════════╝
 [Tab] section   [Enter] edit   [P] preview   [F5] encode
```

- **Components:** tab bar (sections), Program panel (source/output + aspect frame), Properties
  panel (live settings cards), Timeline progress, Log strip, transport hints.
- **Nav flow:** launcher walks sections top-to-bottom (Source→Export) → settings **preview
  card** → confirm → encode dashboard reuses the same Program/Properties/Timeline frame.
- **Palette:** ink `#13141a` bg, indigo `#5b6cff`, violet `#a06bff`, cyan `#33d6e0` accents,
  amber `#ffb454` warnings, green `#3ddc84` ok.
- **UX rationale:** the tab+properties metaphor is the most recognizable editing paradigm; it
  maps 1:1 onto Rich `Layout`/`Panel` without needing live video scopes, so it is **honest**
  (every element shows real data) and **feasible** on Windows terminals.
- **Implementation complexity:** **Medium** — all panels are static renderables fed by real
  config/progress data.

### 3.3 Concept C — Hollywood Mastering Suite

Luxury mastering-room aesthetic: gold/graphite, QC checklist cards, a "DELIVERY READY" seal.

```
╔═══ MASTER QC ════════════════════════════════════╗
║  ✓ Loudness  −14.0 LUFS      ✓ True Peak −1.5 dBTP║
║  ✓ Aspect    9:16            ✓ Color    BT.709    ║
║  ✓ LUT       Hollywood v6.7  ✓ Enhance  AI tuned  ║
║ ────────────────────────────────────────────────  ║
║              ★  D E L I V E R Y   R E A D Y  ★      ║
╚═══════════════════════════════════════════════════╝
```

- **Components:** QC checklist cards, delivery seal, minimal progress.
- **Nav flow:** mostly a *report* surface; weak as an interactive configurator.
- **Palette:** graphite bg, gold `#d4af37`, parchment text.
- **UX rationale:** stunning as a **post-encode** summary, but thin as a configuration UI.
- **Implementation complexity:** **Low-Medium**, but it under-delivers on "interactive
  navigation / dashboard".

### 3.4 Decision Matrix

| Criterion (weight)        | DaVinci | **Premiere** | Hollywood |
|---------------------------|:------:|:-----------:|:--------:|
| UX fit for configure+encode (×3) | 4 | **5** | 2 |
| Honesty (real data, no fake scopes) (×3) | 2 | **5** | 4 |
| Windows terminal feasibility (×2) | 3 | **5** | 4 |
| Visual "premium" impact (×2) | 5 | 4 | **5** |
| Implementation cost (×2, higher=cheaper) | 2 | **4** | 4 |
| **Weighted total** | 33 | **57** | 41 |

**Winner: Adobe Premiere Pro Style.** It is the only concept that is simultaneously a strong
*interactive configurator* and a strong *live dashboard*, while every element renders real data
and survives legacy Windows consoles. The Hollywood "delivery seal" is **adopted as an accent**
inside the Premiere post-encode QC card (best of both).

---

## 4. Proposed Architecture (to-be)

A new optional `ui/` package. The engine treats it as a soft dependency: every call site is
guarded with `try/except ImportError` and falls back to today's behavior.

```
ui/
  __init__.py        # public API: run_launcher(), make_dashboard(), get_console(), THEME
  theme.py           # Premiere palette → Rich Theme, accent tokens, box styles, glyph sets
  config.py          # EncodeConfig (Pydantic v2) ↔ argparse Namespace round-trip + presets
  prompts.py         # validated input helpers (file path, choice menu, numeric range, toggle)
  components.py      # renderables: tab bar, properties panel, info cards, quality chips,
                     #   log/notification panel, section/program panels, settings-preview card
  launcher.py        # interactive flow → returns Namespace (single) or job list (batch)
  dashboard.py       # Premiere Live dashboard (progress + perf monitor + log) + HUD fallback
  test_config.py     # validation + Namespace round-trip (pure, pytest)
  test_components.py # renderables build without error (Console(record=True))
  test_theme.py      # theme tokens present/consistent
```

### 4.1 Data flow

```
run_launcher()
  → pick source (file/folder)         (prompts.py)
  → choose preset                     (config.py presets)
  → edit tabbed sections              (components.py + prompts.py)
  → render settings PREVIEW card      (components.py)
  → confirm
  → EncodeConfig.to_namespace()       (config.py)  ──►  existing _encode_single_file(in, out, ns)
                                                          └► run_ffmpeg / run_ffmpeg_with_cineon
                                                             └► _run_encoding ──► make_dashboard()
```

`EncodeConfig.to_namespace()` emits the **exact** `argparse.Namespace` the engine already
consumes (same attribute names, same `"on"/"off"` string values). The engine cannot tell whether
the Namespace came from `argparse` or the wizard.

### 4.2 Engine seam — the only edits to `Reels_Encoder_v2_FINAL.py`

- **Edit A — `main()` launcher branch** (after `parse_args()`): if no input and no `--batch`,
  **or** `--ui` is set, import `ui.launcher`, run it, dispatch the returned Namespace/jobs through
  the existing single/batch paths. On `ImportError`, keep today's "input required" error.
- **Edit B — `_run_encoding()` dashboard seam** (guarded): try
  `ui.dashboard.make_dashboard(total_frames, fps)`; if present, use it as the `Live` renderable
  and frame sink (it duck-types `update_frame()` like `ResolveProgressHUD`); else use the HUD.
- **Edit C — `--ui` flag** (`action="store_true"`).

All three edits are small, guarded, and inert for real CLI invocations.

### 4.3 Dependency

- **Pydantic v2** (new) — typed validation + readable errors in the wizard. Lazy-imported inside
  `ui/`. Added to `requirements.txt`. Rich/psutil already present. **Textual/Typer not needed.**

---

## 5. Roadmap (phased)

| Phase | Deliverable | Complexity | Validation gate |
|------|-------------|:---------:|-----------------|
| **0** | This masterplan doc (3 concepts, winner, plan) + self-review | M | Doc complete, internally consistent |
| **1** | `ui/theme.py`, `ui/config.py`, `test_config.py`, `test_theme.py` | M | `pytest ui/test_config.py ui/test_theme.py` green; round-trip == argparse defaults |
| **2** | `ui/components.py`, `ui/prompts.py`, `test_components.py` | M | renderables build under `Console(record=True)` |
| **3** | `ui/launcher.py` interactive flow | L | manual: produces valid Namespace for each preset |
| **4** | `ui/dashboard.py` + Edit B seam | L | dashboard renders; HUD fallback identical when ui absent |
| **5** | Edit A + Edit C + batch dashboard + QC restyle | M | classic CLI byte-identical; `--ui` drives full encode |
| **6** | Full pytest, docs (README/CLAUDE.md), manual smoke, final report | M | all gates green in both terminals |

---

## 6. Refactoring List (additive — no engine rewrite)

1. Introduce `ui.theme.get_console()` as the single themed `Console` factory; the engine's
   global `console` adopts it **guarded** (falls back to plain `Console()` if `ui` absent).
2. Extract the Premiere "Program / Properties / Timeline / Log" frame into reusable
   `components.py` renderables, shared by launcher and dashboard.
3. Wrap engine entry points behind `EncodeConfig.to_namespace()` so configuration has **one**
   typed source of truth (Pydantic), instead of scattered `args.*` access.
4. Centralize glyph/emoji choices and ASCII fallbacks in `theme.py` (legacy-console safety).

*Explicitly out of scope:* splitting the monolith into modules, migrating to Typer, rewriting
filter/pipeline code.

---

## 7. Dependencies

| Package | Status | Use |
|---------|--------|-----|
| rich ≥13 | present | all rendering |
| psutil ≥5.9 | present | perf monitor (CPU/RAM) |
| pydantic ≥2 | **new** | `EncodeConfig` validation |
| textual | not used | (hybrid decision) |
| typer | not used | (argparse kept) |

---

## 8. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|:--:|:--:|------------|
| Legacy conhost mangles truecolor/box/emoji | Med | Med | Rich auto-detect; ASCII glyph fallback in `theme.py`; test both terminals |
| `Live` collides with interactive prompts | Med | High | Strict phase separation: prompts finish before any `Live`; never prompt inside `Live` |
| New Pydantic dep unavailable | Low | Med | Lazy import; engine path runs without `ui/` |
| Engine regression from seams | Low | High | All seams guarded with identical-to-today fallback; CLI path never enters UI |
| Wizard produces invalid Namespace | Low | High | Pydantic validation + round-trip test against argparse defaults/choices |
| Scope creep into engine | Med | Med | Additive boundary enforced; refactor list §6 is exhaustive |

---

## 9. Migration Strategy (no breakage)

1. Land `ui/` package first — pure addition, zero engine impact, fully unit-tested.
2. Add the three guarded seams (A/B/C) last; each is a no-op for existing CLI invocations.
3. Keep `ResolveProgressHUD` and the current render path as the permanent fallback.
4. Ship behind discoverability, not replacement: classic commands unchanged; UI appears only
   on no-args / `--ui`.
5. Document the new entry points in README/CLAUDE.md without removing any existing docs.

---

## 10. Implementation Checklist

- [ ] **P0** masterplan doc written, self-reviewed, committed
- [ ] **P1** `theme.py`: Theme, accents, box styles, glyph+ASCII sets, `get_console()`
- [ ] **P1** `config.py`: `EncodeConfig` fields mirror all argparse flags; `to_namespace()` /
      `from_namespace()`; preset factories (quick_ffmpeg, film_cineon, batch)
- [ ] **P1** tests: round-trip equals argparse defaults; validation rejects bad ranges/choices
- [ ] **P2** `components.py`: tab bar, program panel, properties panel, info card, quality chip,
      log panel, settings-preview card
- [ ] **P2** `prompts.py`: file path (exists), folder, single-choice menu, numeric range, toggle
- [ ] **P2** tests: each renderable builds under `Console(record=True)` without error
- [ ] **P3** `launcher.py`: source → preset → tabbed edit → preview → confirm → Namespace/jobs
- [ ] **P4** `dashboard.py`: Premiere Live layout; `update_frame()` duck-type; psutil perf card;
      bounded log tail; `make_dashboard()` factory
- [ ] **P4** Edit B seam in `_run_encoding` (guarded) + HUD fallback verified
- [ ] **P5** Edit A `main()` branch + Edit C `--ui` flag + batch dashboard + QC card restyle
- [ ] **P6** README/CLAUDE.md updates; requirements.txt += pydantic

## 11. Validation Checklist

- [ ] `python -m pytest enhance/ ui/ -v` — all green
- [ ] `python Reels_Encoder_v2_FINAL.py teste.mp4` — classic single encode unchanged
- [ ] `python Reels_Encoder_v2_FINAL.py --batch ./clips/` — batch unchanged
- [ ] `python Reels_Encoder_v2_FINAL.py --hardware-info` — unchanged
- [ ] `python Reels_Encoder_v2_FINAL.py` (no args) — launcher opens
- [ ] `python Reels_Encoder_v2_FINAL.py --ui` — launcher opens, drives a real encode
- [ ] Render verified in **Windows Terminal** and **legacy PowerShell** (glyphs/colors)
- [ ] Dashboard shows progress + fps/speed/ETA + perf + log; QC card renders
- [ ] `git diff` on engine file == only Edits A/B/C, all guarded

## 12. Success Criteria

1. No-args / `--ui` opens the Premiere-style launcher; configuration is fully interactive with a
   settings preview before encode.
2. Every existing CLI command behaves **identically** to today.
3. Encode shows the upgraded dashboard and falls back cleanly when `ui/` is absent.
4. Full test suite (existing + new) passes.
5. Verified in Windows Terminal and legacy PowerShell.

---

## 13. Complexity Estimates (summary)

| Item | Est. effort | Notes |
|------|:--:|-------|
| theme.py | S | palette + glyph tables |
| config.py | M | mirror ~25 flags + round-trip + presets |
| components.py | M | several renderables, shared frame |
| prompts.py | S | thin wrappers over rich.prompt + validation |
| launcher.py | L | orchestration, branching by preset, batch |
| dashboard.py | L | Live layout + perf + log + seam |
| engine seams (A/B/C) | S | 3 small guarded edits |
| tests | M | config/theme/components |
| docs + report | S | README/CLAUDE.md + final report |

---

*End of masterplan. Implementation proceeds one phase at a time, validating after each.*
