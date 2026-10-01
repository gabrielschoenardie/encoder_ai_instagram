# P3B Casca da TUI + Encode ao Vivo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m ui.tui` monta a configuração pelo wizard de linha e roda um encode real em tela cheia: READY → ENCODING (+DETAILS/LOG/CANCEL) → QC → COMPLETED / ERROR / CANCELLED.

**Architecture:** Pacote novo `ui/tui/`. `state.py` tem `UIState` imutável e um reducer puro `apply(state, ev)` que consome eventos do encoder (`reporter.*`), teclas (`Key`), ticks (`Tick`) e o fim do encode (`Finished`). `screens.py` desenha a tela atual a partir do estado (função pura). `keys.py` lê teclado em thread sem consumir Ctrl+C. `app.py` é o único dono de um `Live(screen=True)` e chama `ui.tui_driver.run_single` (P3A) com `on_tick` = esvaziar fila → reducer → redesenhar. `__main__.py` faz a guarda do terminal e chama `run_launcher`.

**Tech Stack:** Python ≥ 3.11, Rich (já dependência), psutil (já dependência), stdlib `msvcrt`/`termios`/`tty`/`select`, pytest + pytest-timeout.

**Spec:** `docs/superpowers/specs/2026-10-01-tui-shell-encode-design.md` (ler inteiro). Wireframes e regras por tela: `docs/Phase_2_TUI_Specification.md` §M READY, §N ENCODING, §O 2-pass, §P Cineon, §Q DETAILS, §R LOG, §S CANCEL, §U QC, §V COMPLETED, §W ERROR, §AE geometria. Canal P3A: `reporter.py`, `ui/tui_driver.py`, `ui/tui_capture.py`; contrato: `.claude/memory/FINDINGS.md` § "Ciclo P3A".

## Global Constraints

- Terminal alvo exclusivo 120 × 40 (D-02); nenhuma linha renderizada com mais de 120 colunas.
- Linguagem visual existente (D-03): estilos de `ui.theme.THEME`, glifos de `ui.theme.glyphs()`, `PANEL_BOX` (rounded) e `HEAVY_BOX` (double).
- Sem emoji em regiões fixas (D-20); motion só spinner, pulso e revelação do selo (D-21).
- Durante encoding só `D`, `L`, `C`, Ctrl+C (D-09); `C` sempre abre confirmação, Ctrl+C nunca (D-10); `C` desligada (`░[C]`) em `ANALYZING·mctf_mask` e `QC` (D-22, D-11).
- Duas passadas mostradas por passe, Pass 1 visível no Pass 2, sem % combinado (D-12); `Pass(phase="end")` = 100%.
- Dado ausente renderiza `—` (D-13); proveniência CFG/DET/CALC/LIVE no DETAILS (D-14).
- Exit codes do condutor: 0 sucesso, 1 erro, 2 validação, 130 Ctrl+C/cancel; READY + ESC → 0; Ctrl+C fora do encode → 130.
- Fila `queue.Queue()` sem limite; `sys.stderr` redirecionado durante a TUI; terminal sempre restaurado no `finally`.
- Nenhuma mudança em `Reels_Encoder_v2_FINAL.py`, `reporter.py`, `ui/tui_driver.py`, `ui/tui_capture.py`, `ui/launcher.py`, `render_queue.py`, `ebu_meter.py`.
- Novos módulos com `from __future__ import annotations`. Não refatorar, não adicionar features, não escrever comentários narrativos (CLAUDE.md).
- Suíte canônica: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Testes em `tmp_path`, nada na raiz.

## Review Focus

1. **Exceção dentro do render durante o encode** — `on_tick` roda dentro do loop de `run_job` na thread principal; se o render lançar, a exceção sai de `run_single` com o worker ainda encodando (encode órfão). Esperado: o render nunca derruba o encode; a TUI mostra um painel de erro de render e segue. → `test_render_exception_does_not_escape_on_tick` (Task 6).
2. **Terminal reduzido abaixo de 120×40 no meio do encode** — esperado: aviso no lugar da tela, encode continua, tela volta ao ampliar. → `test_small_terminal_notice` (Task 3) e `test_resize_mid_encode_keeps_running` (Task 6).
3. **Ctrl+C no READY ou na tela final** — esperado: sai com 130 e o terminal/stderr/console restaurados. → `test_ctrl_c_in_ready_returns_130_and_restores` (Task 6).
4. **`Error.stderr_tail` em bytes, `None` ou texto com `\r`** — esperado: a tela ERROR mostra texto legível sem quebrar. → `test_error_screen_handles_bytes_and_none_stderr` (Task 5).
5. **Teclas não mapeadas e repetição rápida de `C`/ENTER** — esperado: ignoradas sem mudar de tela; dois ENTER seguidos no modal não disparam dois cancelamentos. → `test_unmapped_keys_ignored` e `test_double_enter_in_modal_single_cancel` (Task 1).

## File Structure

| arquivo | responsabilidade |
|---------|------------------|
| `ui/tui/__init__.py` | pacote (vazio) |
| `ui/tui/state.py` | `Key`, `Tick`, `Finished`, `PassTrack`, `LogRow`, `UIState`, `apply`, `final_actions`, `cancel_blocked` |
| `ui/tui/keys.py` | `decode_windows`, `decode_posix`, `KeyReader` |
| `ui/tui/screens.py` | `render(state)` + uma função por tela + helpers visuais |
| `ui/tui/app.py` | `App` (ciclo de vida, loop, `on_tick`) |
| `ui/tui/__main__.py` | `main()` (guarda do terminal, wizard, preflight, validação, `App`) |
| `ui/tui/test_state.py`, `test_keys.py`, `test_screens.py`, `test_app.py`, `test_main.py` | testes |

---

### Task 1: `state.py` — estado e reducer

**Files:**
- Create: `ui/tui/__init__.py` (vazio), `ui/tui/state.py`
- Test: `ui/tui/test_state.py`

**Interfaces:**
- Consumes: `reporter` (eventos `Stage`, `Hardware`, `Probe`, `EncodeParams`, `Pass`, `Progress`, `FfmpegLine`, `Info`, `Qc`, `Done`, `Error`, `Cancel`; constantes `PREPARING`…`DONE`, `CANCEL_BLOCKED`).
- Produces: constantes de tela `READY, ENCODING, DETAILS, LOG, QC, COMPLETED, ERROR, CANCELLED`, `FINAL_SCREENS`, `SEAL_REVEAL_S = 1.2`, `MIN_SIZE = (120, 40)`, `LOG_FILTERS = ("TUDO", "SYSTEM", "INFO", "WARNING", "FFMPEG")`; dataclasses `Key(name)`, `Tick(ts, size, cpu=None, ram=None, ram_used_gb=None)`, `Finished(exit_code)`, `PassTrack`, `LogRow(kind, text)`, `UIState`; funções `apply(state, ev) -> UIState`, `cancel_blocked(state) -> bool`, `final_actions(state) -> tuple[str, ...]`, `active_pass(state) -> PassTrack | None`, `filtered_log(state) -> tuple[LogRow, ...]`. `UIState.action` ∈ `None | "start" | "cancel" | "exit"` é lido e zerado pelo `App`.

- [ ] **Step 0: Branch e baseline** — a branch `claude/ciclo-p3b-tui-shell` já existe (spec commitada em `b4aa09b`). Rodar a suíte canônica e registrar a contagem em STATE.md (`## Ciclo P3B`).

- [ ] **Step 1: Write the failing test** — `ui/tui/test_state.py`

```python
import dataclasses

import pytest

import reporter as R
from ui.tui import state as S


def _s(**kw):
    cfg = {"input": "in.mov", "mode": "2pass", "cineon_pipeline": "off"}
    return S.UIState(config=cfg, output_path="out.mp4", **kw)


def _run(s, *evs):
    for ev in evs:
        s = S.apply(s, ev)
    return s


def test_state_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _s().screen = "X"


def test_ready_enter_starts_and_esc_exits_zero():
    s = S.apply(_s(), S.Key("ENTER"))
    assert s.screen == S.ENCODING and s.action == "start"
    s = S.apply(_s(), S.Key("ESC"))
    assert s.action == "exit" and s.exit_code == 0


def test_unmapped_keys_ignored():
    s = _s(screen=S.ENCODING)
    assert S.apply(s, S.Key("X")) == s
    assert S.apply(_s(), S.Key("D")) == _s()


def test_stage_flow_marks_done_and_logs_system():
    s = _run(_s(screen=S.ENCODING),
             R.Stage(R.PREPARING, ts=1.0), R.Stage(R.PROBING, ts=2.0), R.Stage(R.PASS, "1", ts=3.0))
    assert (s.stage, s.substep) == (R.PASS, "1")
    assert s.stages_done == (R.PREPARING, R.PROBING)
    assert s.job_started == 1.0
    assert [r.kind for r in s.log] == ["SYSTEM"] * 3


def test_stage_qc_switches_screen_and_closes_modal():
    s = _s(screen=S.ENCODING, modal="CANCEL")
    s = S.apply(s, R.Stage(R.QC, ts=5.0))
    assert s.screen == S.QC and s.modal is None


def test_pass_tracks_keep_pass1_and_end_is_100():
    s = _run(_s(screen=S.ENCODING),
             R.Pass(1, 2, "Pass 1", "start", ts=10.0),
             R.Progress(50, 100, 25.0, 1.0, "00:00:02", 2.0, ts=11.0),
             R.Pass(1, 2, "Pass 1", "end", ts=14.0),
             R.Pass(2, 2, "Pass 2", "start", ts=14.5),
             R.Progress(10, 100, 25.0, 1.0, "00:00:04", 0.4, ts=15.0))
    p1, p2 = s.passes
    assert p1.done and p1.pct == 100.0 and p1.seconds == pytest.approx(4.0)
    assert not p2.done and p2.pct == pytest.approx(10.0) and p2.eta == "00:00:04"
    assert S.active_pass(s) is p2


def test_c_opens_modal_and_confirm_requests_cancel_once():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), S.Key("C"))
    assert s.modal == "CANCEL" and s.modal_focus == 0
    s = S.apply(s, S.Key("ENTER"))
    assert s.modal is None and s.action is None
    s = _run(s, S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"))
    assert s.action == "cancel" and s.modal is None


def test_double_enter_in_modal_single_cancel():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0),
             S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"))
    s2 = S.apply(s, S.Key("ENTER"))
    assert s.action == "cancel"
    assert s2.modal is None and s2.action == "cancel"


def test_esc_closes_modal_without_cancel():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), S.Key("C"), S.Key("ESC"))
    assert s.modal is None and s.action is None


@pytest.mark.parametrize("stage", [R.Stage(R.ANALYZING, "mctf_mask", ts=1.0), R.Stage(R.QC, ts=1.0)])
def test_c_ignored_when_blocked(stage):
    s = _run(_s(screen=S.ENCODING), stage)
    assert S.cancel_blocked(s)
    assert S.apply(s, S.Key("C")).modal is None


def test_events_after_cancel_ignored():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), R.Cancel("requested", ts=2.0))
    s2 = _run(s, R.Stage(R.QC, ts=3.0), R.Progress(5, 10, 1.0, 1.0, "x", 1.0, ts=3.1))
    assert s2.stage == R.PASS and s2.screen == S.ENCODING and s2.cancel_phase == "requested"


def test_cancel_cleaned_records_partial_removed():
    s = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("cleaned", True, ts=2.0))
    assert s.cancel_phase == "cleaned" and s.partial_removed is True


def test_info_warning_classification_and_ffmpeg_cr():
    s = _run(_s(screen=S.ENCODING),
             R.Info("Aviso: ffprobe falhou, usando duração padrão 30s", ts=1.0),
             R.Info("LUT Portra 400 carregada", ts=1.1),
             R.Info("MCTF falhou: [Errno 22]", ts=1.2),
             R.FfmpegLine("frame=1 fps=1\rframe=2 fps=2\r", ts=1.3))
    assert [r.kind for r in s.log] == ["WARNING", "INFO", "WARNING", "FFMPEG"]
    assert s.warnings == 2
    assert s.log[-1].text == "frame=2 fps=2"


def test_log_filter_cycles_with_left_right():
    s = _run(_s(screen=S.ENCODING), R.Info("a", ts=1.0), R.FfmpegLine("f", ts=1.1), S.Key("L"))
    assert s.screen == S.LOG and s.back == S.ENCODING
    s = _run(s, S.Key("RIGHT"))
    assert S.LOG_FILTERS[s.log_filter] == "SYSTEM"
    s = _run(s, S.Key("RIGHT"), S.Key("RIGHT"), S.Key("RIGHT"))
    assert [r.text for r in S.filtered_log(s)] == ["f"]
    assert S.apply(s, S.Key("ESC")).screen == S.ENCODING


def test_details_toggle_and_payload_events():
    s = _run(_s(screen=S.ENCODING),
             R.Hardware({"tier": "high"}, ts=1.0),
             R.Probe(30.0, 900, 30, 1080, 1920, False, ts=1.1),
             R.EncodeParams("short", 9800, 11000, 14850, 0.9, "slow", "2pass", ts=1.2),
             S.Key("D"))
    assert s.screen == S.DETAILS and s.hardware == {"tier": "high"}
    assert s.probe.width == 1080 and s.encode_params.vbv_key == "short"
    assert S.apply(s, S.Key("D")).screen == S.ENCODING


def test_finished_paths():
    base = _s(screen=S.ENCODING)
    assert S.apply(base, S.Finished(0)).screen == S.COMPLETED
    assert S.apply(base, S.Finished(130)).screen == S.CANCELLED
    assert S.apply(base, S.Finished(1)).screen == S.ERROR
    assert S.apply(base, S.Finished(2)).screen == S.ERROR
    s = _run(base, S.Key("D"), S.Finished(1))
    assert s.screen == S.ERROR


def test_seal_reveal_then_completed():
    payload = {"summary": {"ready": True}, "checks": []}
    s = _run(_s(screen=S.ENCODING), R.Stage(R.QC, ts=1.0), R.Qc(payload, ts=2.0),
             S.Tick(2.1, (120, 40)), S.Finished(0))
    assert s.screen == S.QC and s.seal_reveal_start == 2.1
    s = S.apply(s, S.Tick(2.5, (120, 40)))
    assert s.screen == S.QC
    s = S.apply(s, S.Tick(2.1 + S.SEAL_REVEAL_S, (120, 40)))
    assert s.screen == S.COMPLETED


def test_final_actions_and_exit():
    s = S.apply(_s(screen=S.ENCODING, qc={"summary": {}}), S.Finished(0))
    s = S.apply(s, S.Tick(9.0, (120, 40)))
    s = S.apply(s, S.Tick(99.0, (120, 40)))
    assert s.screen == S.COMPLETED
    assert S.final_actions(s) == ("SAIR", "VER QC", "VER LOG")
    v = _run(s, S.Key("RIGHT"), S.Key("ENTER"))
    assert v.screen == S.QC and v.back == S.COMPLETED
    assert S.apply(v, S.Key("ESC")).screen == S.COMPLETED
    e = S.apply(s, S.Key("ENTER"))
    assert e.action == "exit"
    assert S.final_actions(S.apply(_s(screen=S.ENCODING), S.Finished(1))) == ("SAIR", "VER LOG")


def test_error_scroll_bounds():
    s = S.apply(_s(screen=S.ENCODING), S.Finished(1))
    s = _run(s, S.Key("UP"))
    assert s.error_scroll == 0
    s = _run(s, S.Key("DOWN"), S.Key("DOWN"))
    assert s.error_scroll == 2


def test_tick_records_size_and_perf():
    s = S.apply(_s(), S.Tick(3.0, (100, 30), cpu=12.0, ram=40.0, ram_used_gb=6.5))
    assert s.size == (100, 30) and s.now == 3.0 and s.cpu == 12.0 and s.ram_used_gb == 6.5
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_state.py -v` → FAIL (`ModuleNotFoundError: No module named 'ui.tui'`).

- [ ] **Step 3: Implement** — `ui/tui/__init__.py` vazio; `ui/tui/state.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, replace

import reporter as R

READY = "READY"
ENCODING = "ENCODING"
DETAILS = "DETAILS"
LOG = "LOG"
QC = "QC"
COMPLETED = "COMPLETED"
ERROR = "ERROR"
CANCELLED = "CANCELLED"
FINAL_SCREENS = frozenset({COMPLETED, ERROR, CANCELLED})
OVERLAYS = frozenset({DETAILS, LOG})
SEAL_REVEAL_S = 1.2
MIN_SIZE = (120, 40)
LOG_CAP = 500
LOG_FILTERS = ("TUDO", "SYSTEM", "INFO", "WARNING", "FFMPEG")
_WARNING_RE = re.compile(r"^aviso\b|\bfalhou\b|n[ãa]o foi poss[ií]vel", re.IGNORECASE)


@dataclass(frozen=True)
class Key:
    name: str


@dataclass(frozen=True)
class Tick:
    ts: float
    size: tuple
    cpu: float | None = None
    ram: float | None = None
    ram_used_gb: float | None = None


@dataclass(frozen=True)
class Finished:
    exit_code: int


@dataclass(frozen=True)
class PassTrack:
    index: int
    total: int
    label: str
    pct: float = 0.0
    eta: str | None = None
    started: float | None = None
    seconds: float | None = None
    done: bool = False


@dataclass(frozen=True)
class LogRow:
    kind: str
    text: str


@dataclass(frozen=True)
class UIState:
    config: dict
    output_path: str = ""
    screen: str = READY
    back: str = ENCODING
    modal: str | None = None
    modal_focus: int = 0
    action_focus: int = 0
    log_filter: int = 0
    error_scroll: int = 0
    stage: str | None = None
    substep: str | None = None
    stages_done: tuple = ()
    passes: tuple = ()
    progress: R.Progress | None = None
    job_started: float | None = None
    now: float = 0.0
    size: tuple = MIN_SIZE
    cpu: float | None = None
    ram: float | None = None
    ram_used_gb: float | None = None
    hardware: dict | None = None
    probe: R.Probe | None = None
    encode_params: R.EncodeParams | None = None
    log: tuple = ()
    warnings: int = 0
    qc: dict | None = None
    done: R.Done | None = None
    error: R.Error | None = None
    cancel_phase: str | None = None
    partial_removed: bool | None = None
    exit_code: int | None = None
    seal_reveal_start: float | None = None
    action: str | None = None


def cancel_blocked(s: UIState) -> bool:
    return (s.stage, s.substep) in R.CANCEL_BLOCKED


def active_pass(s: UIState) -> PassTrack | None:
    for track in reversed(s.passes):
        if not track.done:
            return track
    return None


def final_actions(s: UIState) -> tuple:
    if s.screen == COMPLETED or s.back == COMPLETED:
        return ("SAIR", "VER QC", "VER LOG") if s.qc is not None else ("SAIR", "VER LOG")
    return ("SAIR", "VER LOG")


def filtered_log(s: UIState) -> tuple:
    kind = LOG_FILTERS[s.log_filter]
    if kind == "TUDO":
        return s.log
    return tuple(r for r in s.log if r.kind == kind)


def apply(s: UIState, ev) -> UIState:
    if isinstance(ev, Tick):
        return _tick(s, ev)
    if isinstance(ev, Key):
        return _key(s, ev.name)
    if isinstance(ev, Finished):
        return _finished(s, ev.exit_code)
    return _engine(s, ev)


def _log(s: UIState, kind: str, text: str) -> UIState:
    rows = (s.log + (LogRow(kind, text),))[-LOG_CAP:]
    return replace(s, log=rows, warnings=s.warnings + (1 if kind == "WARNING" else 0))


def _with_track(s: UIState, track: PassTrack) -> UIState:
    others = tuple(t for t in s.passes if t.index != track.index)
    return replace(s, passes=tuple(sorted(others + (track,), key=lambda t: t.index)))


def _engine(s: UIState, ev) -> UIState:
    if s.cancel_phase is not None and isinstance(ev, (R.Stage, R.Pass, R.Progress)):
        return s
    if isinstance(ev, R.Stage):
        done = s.stages_done
        if s.stage is not None and s.stage != ev.name and s.stage not in done:
            done = done + (s.stage,)
        started = s.job_started if s.job_started is not None else ev.ts
        s = replace(s, stage=ev.name, substep=ev.substep, stages_done=done, job_started=started)
        s = _log(s, "SYSTEM", ev.name + (f" · {ev.substep}" if ev.substep else ""))
        if ev.name == R.QC:
            if s.screen == ENCODING:
                s = replace(s, screen=QC, modal=None)
            elif s.screen in OVERLAYS:
                s = replace(s, back=QC, modal=None)
        return s
    if isinstance(ev, R.Hardware):
        return replace(s, hardware=dict(ev.fields))
    if isinstance(ev, R.Probe):
        return replace(s, probe=ev)
    if isinstance(ev, R.EncodeParams):
        return replace(s, encode_params=ev)
    if isinstance(ev, R.Pass):
        if ev.phase == "start":
            return _with_track(s, PassTrack(ev.index, ev.total, ev.label, started=ev.ts))
        cur = next((t for t in s.passes if t.index == ev.index), PassTrack(ev.index, ev.total, ev.label))
        secs = ev.ts - cur.started if cur.started is not None else None
        return _with_track(s, replace(cur, pct=100.0, done=True, seconds=secs, eta=None))
    if isinstance(ev, R.Progress):
        track = active_pass(s)
        s = replace(s, progress=ev)
        if track is None:
            return s
        pct = (100.0 * ev.frame / ev.total) if ev.total else track.pct
        return _with_track(s, replace(track, pct=min(pct, 100.0), eta=ev.eta))
    if isinstance(ev, R.FfmpegLine):
        parts = [p for p in ev.line.split("\r") if p.strip()]
        return _log(s, "FFMPEG", parts[-1].strip() if parts else "")
    if isinstance(ev, R.Info):
        return _log(s, "WARNING" if _WARNING_RE.search(ev.text) else "INFO", ev.text)
    if isinstance(ev, R.Qc):
        return replace(s, qc=ev.payload)
    if isinstance(ev, R.Done):
        return replace(s, done=ev)
    if isinstance(ev, R.Error):
        return _log(replace(s, error=ev), "WARNING", f"{ev.kind}: {ev.message}")
    if isinstance(ev, R.Cancel):
        s = replace(s, cancel_phase=ev.phase, modal=None)
        if ev.partial_removed is not None:
            s = replace(s, partial_removed=ev.partial_removed)
        return _log(s, "SYSTEM", f"CANCEL · {ev.phase}")
    return s


def _tick(s: UIState, ev: Tick) -> UIState:
    s = replace(s, now=ev.ts, size=tuple(ev.size), cpu=ev.cpu, ram=ev.ram, ram_used_gb=ev.ram_used_gb)
    if s.screen == QC and s.qc is not None and s.seal_reveal_start is None:
        s = replace(s, seal_reveal_start=ev.ts)
    if s.exit_code == 0 and s.screen == QC and s.back != COMPLETED:
        revealed = s.qc is None or (
            s.seal_reveal_start is not None and ev.ts - s.seal_reveal_start >= SEAL_REVEAL_S
        )
        if revealed:
            s = replace(s, screen=COMPLETED, action_focus=0)
    return s


def _finished(s: UIState, code: int) -> UIState:
    s = replace(s, exit_code=code, modal=None, action_focus=0)
    if s.screen in OVERLAYS:
        s = replace(s, screen=s.back)
    if code == 0:
        return replace(s, screen=QC if s.qc is not None else COMPLETED)
    return replace(s, screen=CANCELLED if code == 130 else ERROR)


def _key(s: UIState, k: str) -> UIState:
    if s.screen == READY:
        if k == "ENTER":
            return replace(s, screen=ENCODING, action="start")
        if k == "ESC":
            return replace(s, action="exit", exit_code=0)
        return s
    if s.modal == "CANCEL":
        if k in ("LEFT", "RIGHT"):
            return replace(s, modal_focus=1 - s.modal_focus)
        if k == "ESC":
            return replace(s, modal=None, modal_focus=0)
        if k == "ENTER":
            return replace(s, modal=None, modal_focus=0, action="cancel" if s.modal_focus == 1 else s.action)
        return s
    if s.screen in FINAL_SCREENS:
        actions = final_actions(s)
        if k == "LEFT":
            return replace(s, action_focus=max(0, s.action_focus - 1))
        if k == "RIGHT":
            return replace(s, action_focus=min(len(actions) - 1, s.action_focus + 1))
        if s.screen == ERROR and k in ("UP", "DOWN"):
            return replace(s, error_scroll=max(0, s.error_scroll + (1 if k == "DOWN" else -1)))
        if k == "ESC":
            return replace(s, action="exit")
        if k == "ENTER":
            chosen = actions[s.action_focus]
            if chosen == "SAIR":
                return replace(s, action="exit")
            return replace(s, screen=QC if chosen == "VER QC" else LOG, back=s.screen)
        return s
    if s.screen in OVERLAYS:
        if k == "ESC" or (k == "D" and s.screen == DETAILS) or (k == "L" and s.screen == LOG):
            return replace(s, screen=s.back)
        if k == "D":
            return replace(s, screen=DETAILS)
        if k == "L":
            return replace(s, screen=LOG)
        if s.screen == LOG and k in ("LEFT", "RIGHT"):
            step = 1 if k == "RIGHT" else -1
            return replace(s, log_filter=(s.log_filter + step) % len(LOG_FILTERS))
        return s
    if s.screen == QC and s.back in FINAL_SCREENS:
        return replace(s, screen=s.back) if k == "ESC" else s
    if s.screen in (ENCODING, QC):
        if k == "D":
            return replace(s, screen=DETAILS, back=s.screen)
        if k == "L":
            return replace(s, screen=LOG, back=s.screen)
        if k == "C" and s.screen == ENCODING and s.cancel_phase is None and not cancel_blocked(s):
            return replace(s, modal="CANCEL", modal_focus=0)
    return s
```

Nota para quem implementa: um `LOG` aberto a partir de uma tela final (`back` ∈ `FINAL_SCREENS`) usa o ramo `OVERLAYS` — ESC volta para a tela final. O `App` zera `action` depois de executá-la; por isso `test_double_enter_in_modal_single_cancel` só verifica que o segundo ENTER (com o modal já fechado, tela ENCODING) não reabre nem produz outro cancelamento além do pendente.

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_state.py -v` → todos verdes; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/__init__.py ui/tui/state.py ui/tui/test_state.py
git commit -m "feat(tui): estado imutável e reducer puro da casca (P3B)"
```

---

### Task 2: `keys.py` — leitor de teclado

**Files:**
- Create: `ui/tui/keys.py`
- Test: `ui/tui/test_keys.py`

**Interfaces:**
- Consumes: `ui.tui.state.Key`.
- Produces: `decode_windows(ch: str, nxt: str | None = None) -> str | None`; `decode_posix(seq: str) -> str | None`; `class KeyReader(emit: Callable[[Key], None])` com `start()`, `stop()` (encerra a thread) e `restore()` (restaura o terminal no POSIX; no Windows não faz nada). Nomes de tecla: `ENTER, ESC, LEFT, RIGHT, UP, DOWN, D, L, C`.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_keys.py`

```python
import pytest

from ui.tui import keys as K


@pytest.mark.parametrize("ch,nxt,want", [
    ("\r", None, "ENTER"), ("\x1b", None, "ESC"), ("d", None, "D"), ("D", None, "D"),
    ("l", None, "L"), ("c", None, "C"), ("C", None, "C"),
    ("\xe0", "K", "LEFT"), ("\xe0", "M", "RIGHT"), ("\x00", "H", "UP"), ("\x00", "P", "DOWN"),
    ("x", None, None), ("\x03", None, None), ("\xe0", "Z", None),
])
def test_decode_windows(ch, nxt, want):
    assert K.decode_windows(ch, nxt) == want


@pytest.mark.parametrize("seq,want", [
    ("\n", "ENTER"), ("\r", "ENTER"), ("\x1b", "ESC"), ("\x1b[D", "LEFT"), ("\x1b[C", "RIGHT"),
    ("\x1b[A", "UP"), ("\x1b[B", "DOWN"), ("l", "L"), ("q", None), ("\x03", None),
])
def test_decode_posix(seq, want):
    assert K.decode_posix(seq) == want


def test_reader_start_stop_without_console(monkeypatch):
    got = []
    r = K.KeyReader(got.append)
    monkeypatch.setattr(K, "_reader_loop", lambda self: self._stop.wait(5))
    r.start()
    r.stop()
    r.restore()
    assert not r._thread.is_alive()
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_keys.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** — `ui/tui/keys.py`

```python
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable

from ui.tui.state import Key

_CHARS = {"\r": "ENTER", "\n": "ENTER", "\x1b": "ESC", "d": "D", "l": "L", "c": "C"}
_WIN_EXT = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
_ANSI = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}


def decode_windows(ch: str, nxt: str | None = None) -> str | None:
    if ch in ("\x00", "\xe0"):
        return _WIN_EXT.get(nxt or "")
    return _CHARS.get(ch.lower())


def decode_posix(seq: str) -> str | None:
    if seq.startswith("\x1b") and len(seq) > 1:
        return _ANSI.get(seq[1:3])
    return _CHARS.get(seq.lower())


class KeyReader:
    def __init__(self, emit: Callable[[Key], None]):
        self._emit = emit
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._restore: Callable[[], None] | None = None

    def start(self) -> None:
        if os.name != "nt" and sys.stdin.isatty():
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            self._restore = lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old)
        self._thread = threading.Thread(target=_reader_loop, args=(self,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def restore(self) -> None:
        if self._restore is not None:
            self._restore()
            self._restore = None

    def _put(self, name: str | None) -> None:
        if name is not None:
            self._emit(Key(name))


def _reader_loop(reader: KeyReader) -> None:
    try:
        if os.name == "nt":
            _windows_loop(reader)
        else:
            _posix_loop(reader)
    except Exception:
        return


def _windows_loop(reader: KeyReader) -> None:
    import msvcrt

    while not reader._stop.is_set():
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            nxt = msvcrt.getwch() if ch in ("\x00", "\xe0") else None
            reader._put(decode_windows(ch, nxt))
        else:
            time.sleep(0.05)


def _posix_loop(reader: KeyReader) -> None:
    import select

    fd = sys.stdin.fileno()
    while not reader._stop.is_set():
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            continue
        seq = os.read(fd, 1).decode("utf-8", "ignore")
        if seq == "\x1b":
            more, _, _ = select.select([fd], [], [], 0.03)
            if more:
                seq += os.read(fd, 2).decode("utf-8", "ignore")
        reader._put(decode_posix(seq))
```

`tty.setcbreak` desliga ECHO e ICANON e mantém ISIG: Ctrl+C continua gerando `SIGINT` e nunca chega como byte. No Windows, `getwch` não recebe Ctrl+C (validado no B-3).

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_keys.py -v` → verdes; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/keys.py ui/tui/test_keys.py
git commit -m "feat(tui): leitor de teclado sem consumir Ctrl+C (P3B)"
```

---

### Task 3: `screens.py` (1/3) — moldura, READY e aviso de terminal pequeno

**Files:**
- Create: `ui/tui/screens.py`
- Test: `ui/tui/test_screens.py`

**Interfaces:**
- Consumes: `ui.tui.state` (Task 1); `ui.components` (`tab_bar` não é usado — o trilho é próprio, ver abaixo); `ui.theme` (`glyphs`, `get_console`, `PANEL_BOX`, `HEAVY_BOX`); `version.__version__`.
- Produces: `render(s: UIState) -> RenderableType`; helpers `header(s)`, `footer(s)`, `kv_table(rows)`, `panel(body, title, height)`, `hero(lines, height)`, `bar(pct, width)`, `fmt_secs(seconds)`, `basename(path)`, `pipeline_label(config)`; tabelas `SCREEN_RENDERERS: dict[str, Callable[[UIState], RenderableType]]` (Tasks 4–5 acrescentam entradas) e `STATUS: dict[str, str]`.

Regras de desenho (spec P3B §5 + Phase 2 §M, §X, §AE):

- Raiz: `Layout` com `split_column(Layout(name="header", size=3), Layout(name="body", size=34), Layout(name="footer", size=3))`.
- Cabeçalho: linha 1 `" REELS ENCODER  v{__version__}"` (estilo `title`) à esquerda e status à direita (`STATUS[screen]`, com spinner `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` indexado por `int(s.now * 10) % 10` no ENCODING/QC); linha 2 trilho `HOME SOURCE CONFIG PREVIEW READY ENCODE QC DELIVERY` (os quatro primeiros sempre `✓`; o ativo marcado com o glifo `tab_l` e estilo `tab.active`; concluídos com `ok`); linha 3 regra `─` de 120.
- Rodapé: regra `─` + teclas da tela atual (`FOOTER_KEYS[screen]`), com `░[C]` quando `cancel_blocked(s)`.
- `s.size` menor que `MIN_SIZE` em qualquer dimensão → `render` devolve só um `Panel` com "terminal pequeno — amplie para 120×40" e o tamanho atual (sem cabeçalho/rodapé).

- [ ] **Step 1: Write the failing test** — `ui/tui/test_screens.py`

```python
import re
import unicodedata

from ui.theme import get_console
from ui.tui import screens as V
from ui.tui import state as S

CFG = {"input": "C:/v/clip_final.mov", "mode": "crf", "cineon_pipeline": "off", "fps": 30, "fit": "contain",
       "scale": "auto", "lut": "on", "hdr": "auto", "tonemap": "mobius", "loudnorm": "on", "enhance": "on",
       "enhance_ai": "off", "mctf": "off", "dither": "auto", "performance": "balanced", "threads": 0,
       "report": "on", "ebu_meter": "on"}


def text_of(state, width=120, height=40):
    con = get_console(record=True, width=width, height=height, force_terminal=True, color_system="truecolor")
    con.print(V.render(state))
    return con.export_text()


def assert_fits(out):
    for line in out.splitlines():
        assert len(line.rstrip()) <= 120, line


def assert_no_emoji(out):
    allowed = set("✓⚠✗●▸★█░▎▓○⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏─│╭╮╰╯═║╔╗╚╝┌┐└┘├┤┬┴┼━┃")
    for ch in out:
        if unicodedata.category(ch) == "So" and ch not in allowed:
            raise AssertionError(f"símbolo não permitido: {ch!r}")


def st(**kw):
    return S.UIState(config=dict(CFG), output_path="C:/v/clip_final_Hollywood_CRF18.mp4", **kw)


def test_ready_screen():
    out = text_of(st())
    assert "REELS ENCODER" in out and "READY TO ENCODE" in out
    assert "clip_final.mov" in out and "clip_final_Hollywood_CRF18.mp4" in out
    for region in ("KEY SETTINGS", "PIPELINE PLAN", "QC / DELIVERY", "START ENCODE"):
        assert region in out
    assert "passe único CRF" in out and "loudness" in out
    assert re.search(r"\[ENTER\].*\[ESC\]", out)
    assert_fits(out)
    assert_no_emoji(out)


def test_ready_plan_two_pass_and_cineon():
    two = text_of(S.UIState(config={**CFG, "mode": "2pass"}, output_path="o.mp4"))
    assert "PASS 1 / 2 + PASS 2 / 2" in two
    cin = text_of(S.UIState(config={**CFG, "cineon_pipeline": "on"}, output_path="o.mp4"))
    assert "FILM RENDER" in cin and "Cineon Film" in cin


def test_ready_report_off_says_certificate_disabled():
    out = text_of(S.UIState(config={**CFG, "report": "off"}, output_path="o.mp4"))
    assert "certificado desativado" in out


def test_small_terminal_notice():
    out = text_of(st(size=(100, 30)), width=100, height=30)
    assert "terminal pequeno" in out and "120×40" in out and "100×30" in out
    assert "READY TO ENCODE" not in out
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_screens.py -v` → FAIL (`ModuleNotFoundError: ui.tui.screens`).

- [ ] **Step 3: Implement** — `ui/tui/screens.py` (base; Tasks 4–5 acrescentam telas no mesmo arquivo)

```python
from __future__ import annotations

import os
from typing import Callable

from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ui.theme import HEAVY_BOX, PANEL_BOX, glyphs
from ui.tui import state as S

try:
    from version import __version__
except Exception:
    __version__ = "2.1.0"

WIDTH = 120
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "ENCODE", "QC", "DELIVERY")
STATUS = {
    S.READY: "● READY", S.ENCODING: "ENCODING", S.DETAILS: "DETAILS", S.LOG: "LOG", S.QC: "QC",
    S.COMPLETED: "✓ COMPLETED", S.ERROR: "✗ ERROR", S.CANCELLED: "⚠ CANCELLED",
}
FOOTER_KEYS = {
    S.READY: "[←→] Choose   [ENTER] Start encode   [ESC] Sair",
    S.ENCODING: "[D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt",
    S.DETAILS: "[D] Voltar   [L] Log   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.LOG: "[←→] Filtro   [D] Details   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.QC: "[D] Details   [L] Log   ░[C] Cancel   [Ctrl+C] Interrupt",
    S.COMPLETED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.ERROR: "[↑↓] Rolar   [←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.CANCELLED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
}
SCREEN_RENDERERS: dict[str, Callable[[S.UIState], RenderableType]] = {}


def basename(path: str | None) -> str:
    return os.path.basename(path) if path else "—"


def fmt_secs(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def pipeline_label(cfg: dict) -> str:
    pipe = "Cineon Film" if cfg.get("cineon_pipeline") == "on" else "FFmpeg native"
    return f"{pipe} · {cfg.get('mode', '—')}"


def bar(pct: float, width: int = 48) -> Text:
    g = glyphs()
    filled = int(round(width * max(0.0, min(pct, 100.0)) / 100.0))
    out = Text()
    out.append(g["block_full"] * filled, style="bar.complete")
    out.append(g["block_empty"] * (width - filled), style="bar.back")
    return out


def kv_table(rows) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(style="label", no_wrap=True)
    t.add_column(style="value", overflow="ellipsis", no_wrap=True)
    for label, value in rows:
        t.add_row(label, value if isinstance(value, Text) else Text(str(value)))
    return t


def panel(body: RenderableType, title: str, height: int | None = None, style: str = "panel.border") -> Panel:
    return Panel(body, title=f"[panel.title]{title}[/]", title_align="left", box=PANEL_BOX,
                 border_style=style, height=height)


def hero(lines, height: int, style: str = "panel.border") -> Panel:
    return Panel(Group(*lines), box=HEAVY_BOX, border_style=style, height=height)


def _status(s: S.UIState) -> str:
    base = STATUS.get(s.screen, s.screen)
    if s.modal == "CANCEL":
        return "⚠ CANCEL?"
    if s.screen in (S.ENCODING, S.QC) and s.exit_code is None:
        spin = SPINNER[int(s.now * 10) % len(SPINNER)]
        track = S.active_pass(s)
        suffix = f" · PASS {track.index}/{track.total}" if s.screen == S.ENCODING and track else ""
        return f"{spin} {base}{suffix}"
    return base


def _rail_active(s: S.UIState) -> str:
    if s.screen == S.READY:
        return "READY"
    if s.screen in (S.COMPLETED,):
        return "DELIVERY"
    if s.screen == S.QC:
        return "QC"
    return "ENCODE"


def header(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = Table.grid(expand=True)
    top.add_column(justify="left")
    top.add_column(justify="right")
    top.add_row(Text(f" REELS ENCODER  v{__version__}", style="title"), Text(_status(s) + " ", style="accent"))
    active = _rail_active(s)
    idx = RAIL.index(active)
    rail = Text(" ")
    for i, name in enumerate(RAIL):
        if i < 4 or i < idx or (s.screen == S.COMPLETED and name != "DELIVERY"):
            rail.append(f"{g['ok']} {name}   ", style="ok")
        elif name == active:
            rail.append(f"{g['tab_l']}{name}   ", style="tab.active")
        else:
            rail.append(f"  {name}   ", style="tab.inactive")
    return Group(top, rail, Text("─" * WIDTH, style="muted"))


def footer(s: S.UIState) -> RenderableType:
    keys = FOOTER_KEYS.get(s.screen, "")
    if s.screen == S.ENCODING and S.cancel_blocked(s):
        keys = keys.replace("[C] Cancel", "░[C] Cancel")
    return Group(Text("─" * WIDTH, style="muted"), Text(" " + keys, style="muted"))


def _ready(s: S.UIState) -> RenderableType:
    cfg = s.config
    g = glyphs()
    top = hero([
        Text(""),
        Text("   READY TO ENCODE", style="title"),
        Text(""),
        Text(f"   {basename(cfg.get('input'))}   {g['arrow']}   {basename(s.output_path)}"),
        Text(f"   {pipeline_label(cfg)}", style="muted"),
    ], height=7)
    two = cfg.get("mode") == "2pass"
    cineon = cfg.get("cineon_pipeline") == "on"
    key = panel(kv_table([
        ("SOURCE", basename(cfg.get("input"))),
        ("OUTPUT", basename(s.output_path)),
        ("PIPELINE", pipeline_label(cfg)),
        ("", ""),
        ("MODO", f"{cfg.get('mode')} · {'2 passes' if two else '1 passe'}"),
        ("FPS", f"{cfg.get('fps')} · {cfg.get('fit')} · scale {cfg.get('scale')}"),
        ("COR", f"LUT {cfg.get('lut')} · HDR {cfg.get('hdr')} · {cfg.get('tonemap')}"),
        ("ÁUDIO", f"loudnorm {cfg.get('loudnorm')} · alvo instagram"),
        ("ENHANCE", f"{cfg.get('enhance')} · AI {cfg.get('enhance_ai')} · MCTF {cfg.get('mctf')} · dither {cfg.get('dither')}"),
        ("PERF", f"{cfg.get('performance')} · threads {cfg.get('threads')}"),
    ]), "KEY SETTINGS", height=15)
    analyzing = [n for n, on in (("enhance", cfg.get("enhance") == "on"),
                                 ("MCTF máscara", cfg.get("mctf") == "on" and cfg.get("enhance_ai") == "on"),
                                 ("loudness da fonte", cfg.get("loudnorm") == "on")) if on]
    if cineon:
        encoding = f"FILM RENDER · {'PASS 1 / 2 + PASS 2 / 2' if two else 'passe único'}"
    else:
        encoding = "PASS 1 / 2 + PASS 2 / 2" if two else "passe único CRF"
    report_on = cfg.get("report", "on") == "on"
    plan = panel(kv_table([
        ("○ PREPARING", "hardware · validação"),
        ("○ PROBING", "duração · frames · fps · HDR"),
        ("○ ANALYZING", " · ".join(analyzing) if analyzing else "—"),
        ("○ ENCODING", encoding),
        ("○ QC", "EBU R128 · checks do master"),
        ("○ COMPLETED", "MASTER QC · certificado" if report_on else "MASTER QC · certificado desativado"),
    ]), "PIPELINE PLAN", height=15)
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(key, plan)
    base = os.path.splitext(basename(s.output_path))[0]
    cert = f"{base}.qc.html · .qc.json" if report_on else "certificado desativado (--report off)"
    meter = "FFplay ANTES / DEPOIS" if cfg.get("ebu_meter", "on") == "on" else "desligado"
    qc = panel(kv_table([
        ("10 checks no master", "Container · Video · Resolution · Bit Depth · Color · FPS"),
        ("", "Loudness · True Peak · Codec · Sample Rate"),
        ("certificado", cert),
        ("monitor EBU", meter),
    ]), "QC / DELIVERY", height=6)
    actions = Table.grid(expand=True)
    actions.add_column(justify="left")
    actions.add_column(justify="right")
    actions.add_row(Text("   [ ESC  Sair ]", style="muted"), Text(f"{g['tab_l']}{g['arrow']}   START ENCODE   ", style="tab.active"))
    return Group(top, mid, qc, actions)


SCREEN_RENDERERS[S.READY] = _ready


def _small(s: S.UIState) -> RenderableType:
    w, h = s.size
    return Panel(Text(f"terminal pequeno — amplie para 120×40 (atual {w}×{h})\n"
                      "o encode continua rodando", style="warn"), box=PANEL_BOX, border_style="warn")


def render(s: S.UIState) -> RenderableType:
    w, h = s.size
    if w < S.MIN_SIZE[0] or h < S.MIN_SIZE[1]:
        return _small(s)
    body_fn = SCREEN_RENDERERS.get(s.screen)
    body = body_fn(s) if body_fn else Text(s.screen)
    root = Layout()
    root.split_column(Layout(header(s), name="header", size=3), Layout(body, name="body", size=34),
                      Layout(footer(s), name="footer", size=3))
    return root
```

O layout do READY segue o wireframe de §M; ajustes de espaçamento para casar com ele são permitidos desde que os testes sigam verdes (textos-chave, ≤ 120 colunas, sem emoji).

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_screens.py -v` → verdes; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens.py
git commit -m "feat(tui): moldura, tela READY e aviso de terminal pequeno (P3B)"
```

---

### Task 4: `screens.py` (2/3) — ENCODING, modal CANCEL, DETAILS e LOG

**Files:**
- Modify: `ui/tui/screens.py` (acrescentar ao fim, antes de `_small`)
- Test: `ui/tui/test_screens.py` (acrescentar)

**Interfaces:**
- Consumes: helpers da Task 3; `ui.components.job_strip(source, output=None, src_dims=None, console=None)`, `ui.components.viewer_frame(fit="contain", src_dims=None, title="PROGRAM", console=None)`, `ui.components.gauge_bar(pct, width=12, console=None)`.
- Produces: `SCREEN_RENDERERS[S.ENCODING]`, `[S.DETAILS]`, `[S.LOG]`; helpers `stage_rail(s) -> Text`, `pass_lines(s) -> list[Text]`, `pass_label(track, cfg) -> str`, `log_rows(rows, limit) -> Table`, `dashboard(s, middle)` (job strip + header de progresso + `middle` + LOG; usado pelo modal); `cancel_modal(s) -> Panel`.

Regras (Phase 2 §N, §O, §P, §Q, §R, §S):

- `pass_label`: `"Pass 1"` → `"ANÁLISE"`; `"Pass 2"` → `"ENCODE FINAL"`; `"Encode"` → `"FILM RENDER"` se Cineon, senão `"ENCODE"`.
- Trilho de etapas: `PREPARING PROBING ANALYZING PASS 1 [PASS 2] QC COMPLETED` (PASS 2 só no 2-pass); concluída `✓`, ativa `▎●`, pendente `○`. "PASS n" concluído quando a faixa n tem `done`.
- Faixa por passe: `PASS i / n   <label 14>` + `bar(pct, 48)` + `{pct:6.1f}%` + (`✓ hh:mm:ss` se `done`, senão `ETA {eta}`). Antes do primeiro `Pass`, mostra uma linha muted "aguardando o primeiro passe…".
- Meio do dashboard (13 linhas): PROGRAM (30) | TIMELINE (43) | PERFORMANCE (43). Quando `s.modal == "CANCEL"`, o meio é substituído pelo modal centralizado (64 × 12, borda `warn`) — o resto do dashboard continua atualizando (aproximação Rich da sobreposição de §S).
- Modal: título `CANCELAR ENCODE?`; linhas: etapa ativa + `%`, "usa o caminho de interrupção existente (o mesmo do Ctrl+C)", "parcial: <output>"; botões `[ CONTINUAR ENCODE ]   [ CANCELAR ENCODE ]`, o focado (`modal_focus`) com `tab.active` e prefixo do glifo `arrow`.
- LOG (painel de 11 linhas, 9 linhas úteis): título `LOG` + ` ⚠ N` em `warn` quando `warnings > 0`; linhas `KIND    texto` com estilo por tipo (SYSTEM `info`, INFO `value`, WARNING `warn`, FFMPEG `muted`).
- PERFORMANCE: `cpu` e `ram` com `gauge_bar` (`—` se `None`), `ram used`, `threads` e `performance` do config, `tier` do `hardware` (`—` sem evento).
- TIMELINE: `pass`, `frame` (`frame / total`), `fps`, `speed` (`{:.2f}x`), `eta`, `elapsed` (do `Progress`), `job elapsed` (`now - job_started`), tudo `—` sem dado.
- DETAILS (§Q): faixa mini de 1 linha (stage + pass ativo) e 6 painéis 38 × 15 em 2 linhas de 3: `SOURCE` (DET: resolução, duração, frames, fps, HDR), `HARDWARE` (DET/DER: cpu, cores/threads, ram, tier, preset recomendado), `ENCODING` (CFG modo; LIVE pass; CALC VBV `vbv_key`, target, maxrate, bufsize, vbv_init, x264 preset), `CONFIG` (CFG pipeline, LUT, loudnorm, enhance, AI, MCTF, dither), `OUTPUT` (CFG output, report, ebu_meter), `PROGRESS` (LIVE frame, fps, speed, eta, elapsed). Cada linha mostra o rótulo de proveniência em `muted` à direita.
- LOG em tela cheia (§R): faixa mini, abas `TUDO SYSTEM INFO WARNING FFMPEG` com a ativa em `tab.active`, regra, as últimas 28 linhas de `filtered_log(s)`, regra, status `N linhas · filtro X`.

- [ ] **Step 1: Write the failing test** — acrescentar a `ui/tui/test_screens.py`:

```python
import reporter as R


def encoding_state():
    s = S.UIState(config={**CFG, "mode": "2pass"}, output_path="C:/v/clip_final_Hollywood_2Pass.mp4",
                  screen=S.ENCODING, now=200.0)
    for ev in (R.Stage(R.PREPARING, ts=100.0), R.Hardware({"tier": "high", "cpu_threads": 16}, ts=100.1),
               R.Stage(R.PROBING, ts=100.2), R.Probe(60.0, 1800, 30, 1080, 1920, False, ts=100.3),
               R.EncodeParams("long", 7500, 8500, 11475, 0.9, "slow", "2pass", ts=100.4),
               R.Stage(R.PASS, "1", ts=101.0), R.Pass(1, 2, "Pass 1", "start", ts=101.0),
               R.Pass(1, 2, "Pass 1", "end", ts=173.0), R.Stage(R.PASS, "2", ts=173.5),
               R.Pass(2, 2, "Pass 2", "start", ts=173.5),
               R.Progress(1152, 1800, 28.4, 0.95, "00:00:41", 125.0, ts=199.0),
               R.Info("Aviso: ffprobe falhou, usando duração padrão 30s", ts=199.1),
               R.FfmpegLine("frame= 1152 fps= 28 q=24.0", ts=199.2)):
        s = S.apply(s, ev)
    return S.apply(s, S.Tick(200.0, (120, 40), cpu=71.0, ram=48.0, ram_used_gb=7.8))


def test_encoding_dashboard():
    out = text_of(encoding_state())
    for txt in ("ENCODING", "PASS 1 / 2", "ANÁLISE", "PASS 2 / 2", "ENCODE FINAL", "100.0%", "ETA 00:00:41",
                "PROGRAM", "TIMELINE", "PERFORMANCE", "LOG", "1152 / 1800", "0.95x", "tier", "high",
                "⚠ 1", "[D] Details", "[C] Cancel"):
        assert txt in out, txt
    assert "✓ 00:01:12" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_encoding_blocked_c_shows_disabled():
    s = S.apply(encoding_state(), R.Stage(R.ANALYZING, "mctf_mask", ts=201.0))
    assert "░[C]" in text_of(s)


def test_cancel_modal_over_dashboard():
    s = S.apply(encoding_state(), S.Key("C"))
    out = text_of(s)
    assert "CANCELAR ENCODE?" in out and "CONTINUAR ENCODE" in out and "CANCELAR ENCODE ]" in out
    assert "⚠ CANCEL?" in out and "PASS 2 / 2" in out and "LOG" in out
    assert_fits(out)


def test_details_screen():
    out = text_of(S.apply(encoding_state(), S.Key("D")))
    for txt in ("SOURCE", "HARDWARE", "ENCODING", "CONFIG", "OUTPUT", "PROGRESS",
                "1080", "1920", "long", "7500", "8500", "11475", "DET", "CALC", "CFG", "LIVE"):
        assert txt in out, txt
    assert_fits(out)


def test_details_without_events_shows_dash():
    s = S.UIState(config=dict(CFG), output_path="o.mp4", screen=S.DETAILS)
    out = text_of(s)
    assert "—" in out


def test_log_screen_filters():
    s = S.apply(encoding_state(), S.Key("L"))
    out = text_of(s)
    for tab in S.LOG_FILTERS:
        assert tab in out
    assert "ffprobe falhou" in out and "frame= 1152" in out
    s = S.apply(s, S.Key("RIGHT"))
    s = S.apply(s, S.Key("RIGHT"))
    s = S.apply(s, S.Key("RIGHT"))
    out = text_of(s)
    assert "ffprobe falhou" in out and "frame= 1152" not in out
    assert_fits(out)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_screens.py -v` → os novos falham (`KeyError`/texto ausente: telas ainda não registradas).

- [ ] **Step 3: Implement** — acrescentar a `ui/tui/screens.py`:

```python
import reporter as R
from ui import components as C

STAGE_ORDER = (R.PREPARING, R.PROBING, R.ANALYZING)
KIND_STYLE = {"SYSTEM": "info", "INFO": "value", "WARNING": "warn", "FFMPEG": "muted"}


def pass_label(track: S.PassTrack, cfg: dict) -> str:
    if track.label == "Pass 1":
        return "ANÁLISE"
    if track.label == "Pass 2":
        return "ENCODE FINAL"
    return "FILM RENDER" if cfg.get("cineon_pipeline") == "on" else "ENCODE"


def stage_rail(s: S.UIState) -> Text:
    g = glyphs()
    total = 2 if s.config.get("mode") == "2pass" else 1
    names = list(STAGE_ORDER) + [f"PASS {i}" for i in range(1, total + 1)] + [R.QC, "COMPLETED"]
    done_tracks = {f"PASS {t.index}" for t in s.passes if t.done}
    current = f"PASS {s.substep}" if s.stage == R.PASS else s.stage
    finished = s.exit_code == 0 and s.screen in (S.COMPLETED,)
    out = Text(" ")
    for name in names:
        is_done = finished or name in s.stages_done or name in done_tracks or (
            name in STAGE_ORDER and current not in STAGE_ORDER and current is not None)
        if name == current and not finished:
            out.append(f"{g['tab_l']}{g['bullet']} {name}    ", style="tab.active")
        elif is_done:
            out.append(f"{g['ok']} {name}    ", style="ok")
        else:
            out.append(f"○ {name}    ", style="muted")
    return out


def pass_lines(s: S.UIState) -> list:
    if not s.passes:
        return [Text(" aguardando o primeiro passe…", style="muted")]
    lines = []
    for t in s.passes:
        line = Text(f" PASS {t.index} / {t.total}   {pass_label(t, s.config):<14}")
        line.append_text(bar(t.pct))
        tail = f"   {t.pct:6.1f}%   "
        tail += f"{glyphs()['ok']} {fmt_secs(t.seconds)}" if t.done else f"ETA {t.eta or '—'}"
        line.append(tail, style="ok" if t.done else "value")
        lines.append(line)
    return lines


def log_rows(rows, limit: int) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(no_wrap=True, width=8)
    t.add_column(overflow="ellipsis", no_wrap=True, max_width=104)
    for r in rows[-limit:]:
        t.add_row(Text(r.kind, style=KIND_STYLE.get(r.kind, "value")), Text(r.text))
    return t


def _log_panel(s: S.UIState) -> Panel:
    title = "LOG" + (f" [warn]⚠ {s.warnings}[/]" if s.warnings else "")
    return panel(log_rows(s.log, 9), title, height=11)


def _src_dims(s: S.UIState):
    return (s.probe.width, s.probe.height) if s.probe else None


def _job_strip(s: S.UIState) -> RenderableType:
    return C.job_strip(s.config.get("input"), s.output_path, src_dims=_src_dims(s))


def _progress_header(s: S.UIState) -> Panel:
    track = S.active_pass(s)
    title = f"ENCODING · PASS {track.index} / {track.total}" if track else "ENCODING"
    return panel(Group(stage_rail(s), Text(""), *pass_lines(s)), title, height=7)


def _timeline(s: S.UIState) -> Panel:
    p = s.progress
    track = S.active_pass(s)
    job = (s.now - s.job_started) if s.job_started is not None else None
    return panel(kv_table([
        ("pass", f"{track.index} / {track.total} · {pass_label(track, s.config)}" if track else "—"),
        ("frame", f"{p.frame} / {p.total}" if p else "—"),
        ("fps", f"{p.fps:.1f}" if p else "—"),
        ("speed", f"{p.speed:.2f}x" if p else "—"),
        ("eta", p.eta if p else "—"),
        ("elapsed", fmt_secs(p.elapsed) if p else "—"),
        ("job elapsed", fmt_secs(job)),
    ]), "TIMELINE", height=13)


def _gauge(pct):
    return C.gauge_bar(pct) if pct is not None else Text("—")


def _performance(s: S.UIState) -> Panel:
    hw = s.hardware or {}
    threads = s.config.get("threads")
    return panel(kv_table([
        ("cpu", _gauge(s.cpu)),
        ("ram", _gauge(s.ram)),
        ("ram used", f"{s.ram_used_gb:.1f} GB" if s.ram_used_gb is not None else "—"),
        ("", ""),
        ("threads", f"{threads} (auto)" if threads in (0, None) else str(threads)),
        ("performance", s.config.get("performance", "—")),
        ("tier", hw.get("tier", "—")),
    ]), "PERFORMANCE", height=13)


def _middle(s: S.UIState) -> RenderableType:
    row = Table.grid(expand=True)
    row.add_column(width=30)
    row.add_column(ratio=1)
    row.add_column(ratio=1)
    viewer = C.viewer_frame(fit=s.config.get("fit", "contain"), src_dims=_src_dims(s), title="PROGRAM")
    row.add_row(Panel(viewer, height=13, box=PANEL_BOX, border_style="panel.border"), _timeline(s), _performance(s))
    return row


def cancel_modal(s: S.UIState) -> RenderableType:
    g = glyphs()
    track = S.active_pass(s)
    where = f"{s.stage or '—'}{' · ' + s.substep if s.substep else ''}"
    pct = f" · {track.pct:.0f}%" if track else ""
    buttons = Text("   ")
    for i, label in enumerate(("CONTINUAR ENCODE", "CANCELAR ENCODE")):
        focused = s.modal_focus == i
        buttons.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    body = Group(
        Text(""),
        Text(f"  etapa ativa: {where}{pct}"),
        Text("  usa o caminho de interrupção existente (o mesmo do Ctrl+C)", style="muted"),
        Text(f"  parcial: {basename(s.output_path)}", style="muted"),
        Text(""),
        buttons,
    )
    box = Panel(body, title="[warn]CANCELAR ENCODE?[/]", box=PANEL_BOX, border_style="warn", width=64, height=12)
    return Align.center(box, vertical="middle", height=13)


def dashboard(s: S.UIState, middle: RenderableType) -> RenderableType:
    return Group(_job_strip(s), _progress_header(s), Text(""), middle, Text(""), _log_panel(s))


def _encoding(s: S.UIState) -> RenderableType:
    return dashboard(s, cancel_modal(s) if s.modal == "CANCEL" else _middle(s))


def _prov(value, tag: str) -> Text:
    out = Text(str(value) if value not in (None, "") else "—")
    out.append(f"  {tag}", style="muted")
    return out


def _mini(s: S.UIState) -> Text:
    track = S.active_pass(s)
    return Text(f" {s.stage or '—'}{' · ' + s.substep if s.substep else ''}"
                f"{f'   PASS {track.index}/{track.total} {track.pct:.1f}%' if track else ''}", style="muted")


def _details(s: S.UIState) -> RenderableType:
    p, hw, ep, pr, cfg = s.probe, s.hardware or {}, s.encode_params, s.progress, s.config
    track = S.active_pass(s)
    src = panel(kv_table([
        ("resolução", _prov(f"{p.width} × {p.height}" if p else None, "DET")),
        ("duração", _prov(fmt_secs(p.duration) if p else None, "DET")),
        ("frames", _prov(p.total_frames if p else None, "DET")),
        ("fps", _prov(p.fps if p else None, "DET")),
        ("HDR", _prov(("sim" if p.is_hdr else "não") if p else None, "DET")),
    ]), "SOURCE", height=15)
    hwp = panel(kv_table([
        ("cpu", _prov(hw.get("cpu_name"), "DET")),
        ("cores/threads", _prov(f"{hw['cpu_cores']} / {hw['cpu_threads']}" if "cpu_cores" in hw and "cpu_threads" in hw else None, "DET")),
        ("ram", _prov(f"{hw['ram_total_gb']:.1f} GB" if "ram_total_gb" in hw else None, "DET")),
        ("tier", _prov(hw.get("tier"), "DER")),
        ("preset rec.", _prov(hw.get("recommended_preset"), "DER")),
    ]), "HARDWARE", height=15)
    enc = panel(kv_table([
        ("modo", _prov(cfg.get("mode"), "CFG")),
        ("pass", _prov(f"{track.index} / {track.total}" if track else None, "LIVE")),
        ("VBV", _prov(ep.vbv_key if ep else None, "CALC")),
        ("target", _prov(ep.target if ep else None, "CALC")),
        ("maxrate", _prov(ep.maxrate if ep else None, "CALC")),
        ("bufsize", _prov(ep.bufsize if ep else None, "CALC")),
        ("vbv_init", _prov(ep.vbv_init if ep else None, "CALC")),
        ("x264 preset", _prov(ep.x264_preset if ep else None, "CALC")),
    ]), "ENCODING", height=15)
    con = panel(kv_table([
        ("pipeline", _prov(pipeline_label(cfg), "CFG")),
        ("LUT", _prov(cfg.get("lut"), "CFG")),
        ("loudnorm", _prov(cfg.get("loudnorm"), "CFG")),
        ("enhance", _prov(cfg.get("enhance"), "CFG")),
        ("AI", _prov(cfg.get("enhance_ai"), "CFG")),
        ("MCTF", _prov(cfg.get("mctf"), "CFG")),
        ("dither", _prov(cfg.get("dither"), "CFG")),
    ]), "CONFIG", height=15)
    out = panel(kv_table([
        ("output", _prov(basename(s.output_path), "CFG")),
        ("report", _prov(cfg.get("report"), "CFG")),
        ("ebu meter", _prov(cfg.get("ebu_meter"), "CFG")),
    ]), "OUTPUT", height=15)
    prog = panel(kv_table([
        ("frame", _prov(f"{pr.frame} / {pr.total}" if pr else None, "LIVE")),
        ("fps", _prov(f"{pr.fps:.1f}" if pr else None, "LIVE")),
        ("speed", _prov(f"{pr.speed:.2f}x" if pr else None, "LIVE")),
        ("eta", _prov(pr.eta if pr else None, "LIVE")),
        ("elapsed", _prov(fmt_secs(pr.elapsed) if pr else None, "LIVE")),
    ]), "PROGRESS", height=15)
    grid = Table.grid(expand=True)
    for _ in range(3):
        grid.add_column(ratio=1)
    grid.add_row(src, hwp, enc)
    grid.add_row(con, out, prog)
    return Group(_mini(s), grid)


def _log_screen(s: S.UIState) -> RenderableType:
    tabs = Text(" ")
    for i, name in enumerate(S.LOG_FILTERS):
        tabs.append(f" {name} ", style="tab.active" if i == s.log_filter else "tab.inactive")
        tabs.append("  ")
    rows = S.filtered_log(s)
    status = Text(f" {len(rows)} linhas · filtro {S.LOG_FILTERS[s.log_filter]}", style="muted")
    return Group(_mini(s), tabs, Text("─" * WIDTH, style="muted"), log_rows(rows, 28),
                 Text("─" * WIDTH, style="muted"), status)


SCREEN_RENDERERS[S.ENCODING] = _encoding
SCREEN_RENDERERS[S.DETAILS] = _details
SCREEN_RENDERERS[S.LOG] = _log_screen
```

Os imports `reporter`, `ui.components` e `from rich.align import Align` vão para o topo do arquivo junto com os demais (ruff `I`).

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_screens.py -v` → verdes; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens.py
git commit -m "feat(tui): dashboard de encode, modal de cancelamento, DETAILS e LOG (P3B)"
```

---

### Task 5: `screens.py` (3/3) — QC/DELIVERY, COMPLETED, ERROR, CANCELLED

**Files:**
- Modify: `ui/tui/screens.py`
- Test: `ui/tui/test_screens.py` (acrescentar)

**Interfaces:**
- Consumes: helpers das Tasks 3–4; `ui.components.delivery_seal(checks, *, ready=None, console=None)`, `ui.components.error_card(message, hints=None, title=None, console=None)`, `ui.components.quality_chip(label, status, console=None)`; payload do QC (`ebu_meter.build_report_payload`: `checks: [{"label","value","passed"}]`, `summary: {"passed","warnings","failed","ready"}`, `audio: {"before": {...}, "after": {...}}` com `I`, `TP`, `LRA`, `targets: {"I","TP","LRA"}`, `output: {"size_human"}`, `encode: {"duration_human"}`, `video: {"codec","width","height","fps"}`).
- Produces: `SCREEN_RENDERERS[S.QC]`, `[S.COMPLETED]`, `[S.ERROR]`, `[S.CANCELLED]`; helper `stderr_lines(err: reporter.Error | None, log) -> list[str]`; `action_row(s) -> Text`.

`delivery_seal(checks, *, ready=None)` (`ui/components.py:489`) espera `checks` como sequência de `(label, value, passed)`, devolve um `Panel` já titulado "MASTER QC" (DOUBLE, borda `seal`/`warn`) e escreve o selo espaçado: `★  D E L I V E R Y   R E A D Y  ★` / `⚠  R E V I S A R   E N T R E G A  ⚠`. Não embrulhar esse painel em outro.

Regras (Phase 2 §U, §V, §W):

- QC: job strip · cabeçalho QC 118 × 5 (trilho de etapas + "medindo loudness · checks do master" com spinner enquanto `qc is None`) · `EBU R128 — AUDITORIA PÓS-ENCODE` 118 × 9 (tabela I/TP/LRA × ANTES/DEPOIS/Alvo, `—` sem dado) · `MASTER QC` 118 × 14: enquanto `seal_reveal_start is None` ou `now - seal_reveal_start < SEAL_REVEAL_S`, mostra os checks com `quality_chip` e "verificando…"; depois, `delivery_seal(...)` · `DELIVERY` 118 × 5 (certificado `<base>.qc.html · .qc.json` ou "certificado desativado (--report off)"; monitor EBU on/off).
- COMPLETED: hero DOUBLE 8 linhas `✓ ENCODE COMPLETE` + veredito (`★ DELIVERY READY ★` em `seal` se `summary.ready`, `⚠ REVISAR ENTREGA ⚠` em `warn` se False, "QC indisponível" se `qc is None`) · `OUTPUT` (caminho, tamanho, duração, vídeo) | `MASTER QC · RESUMO` (passed/warnings/failed, I/TP/LRA depois) · `DELIVERY` · linha de ações.
- ERROR: `error_card` 118 × 8 com a mensagem do `Error` (ou "Encode terminou com erro (código N)") · `FFMPEG STDERR` 118 × 19 rolável (`error_scroll`) · `ESTADO` 118 × 4 (etapa, último frame, "o output parcial pode existir: <output>") · ações.
- CANCELLED: card âmbar "⚠ Encode interrompido pelo usuário" + resultado do parcial (`partial_removed` True → "output parcial removido"; False → "NÃO foi possível remover … apague à mão"; None → "nenhum output parcial") + LOG resumido + ações.
- `action_row`: `final_actions(s)` com o focado em `tab.active` e prefixo `arrow`.
- `stderr_lines`: `err.stderr_tail` `bytes` → `decode("utf-8", "replace")`; `str` → como está; `None` → últimas 40 linhas FFMPEG do log; dividir em linhas, trocar `\r` por quebra.

- [ ] **Step 1: Write the failing test** — acrescentar:

```python
PAYLOAD = {
    "checks": [{"label": "Container", "value": "mp4", "passed": True},
               {"label": "Loudness", "value": "-14.0 LUFS", "passed": True},
               {"label": "Resolution", "value": "1080x1920", "passed": None}],
    "summary": {"passed": 2, "warnings": 1, "failed": 0, "ready": True},
    "audio": {"before": {"I": -20.1, "TP": -3.0, "LRA": 7.0}, "after": {"I": -14.0, "TP": -1.6, "LRA": 6.0}},
    "targets": {"I": -14.0, "TP": -1.5, "LRA": None},
    "output": {"size_human": "38.2 MB"}, "encode": {"duration_human": "00:03:17"},
    "video": {"codec": "h264", "width": 1080, "height": 1920, "fps": 30.0},
}


def qc_state(reveal_done: bool, ready=True):
    payload = {**PAYLOAD, "summary": {**PAYLOAD["summary"], "ready": ready}}
    s = encoding_state()
    s = S.apply(s, R.Stage(R.QC, ts=300.0))
    s = S.apply(s, R.Qc(payload, ts=301.0))
    s = S.apply(s, S.Tick(301.0, (120, 40)))
    if reveal_done:
        s = S.apply(s, S.Tick(301.0 + S.SEAL_REVEAL_S, (120, 40)))
    return s


def test_qc_before_and_after_reveal():
    before = text_of(qc_state(False))
    assert "EBU R128" in before and "MASTER QC" in before and "verificando" in before
    assert "-14.0" in before and "-20.1" in before
    after = text_of(qc_state(True))
    assert "D E L I V E R Y   R E A D Y" in after
    assert "░[C]" in after
    assert_fits(after)
    assert_no_emoji(after)


def test_qc_review_seal():
    assert "R E V I S A R   E N T R E G A" in text_of(qc_state(True, ready=False))


def test_completed_screen():
    s = S.apply(qc_state(True), S.Finished(0))
    s = S.apply(s, S.Tick(400.0, (120, 40)))
    assert s.screen == S.COMPLETED
    out = text_of(s)
    for txt in ("ENCODE COMPLETE", "DELIVERY READY", "OUTPUT", "38.2 MB", "00:03:17", "SAIR", "VER QC", "VER LOG"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_completed_report_off():
    s = S.UIState(config={**CFG, "report": "off"}, output_path="o.mp4", screen=S.COMPLETED, exit_code=0, qc=PAYLOAD)
    assert "certificado desativado" in text_of(s)


def test_error_screen_handles_bytes_and_none_stderr():
    base = S.apply(encoding_state(), R.Error("CalledProcessError", "ffmpeg saiu com 1",
                                             b"linha a\r\nlinha b\xff\n", 1, None, ts=250.0))
    out = text_of(S.apply(base, S.Finished(1)))
    assert "ffmpeg saiu com 1" in out and "linha a" in out and "linha b" in out
    assert "FFMPEG STDERR" in out and "ESTADO" in out and "SAIR" in out
    none_err = S.apply(encoding_state(), R.Error("RuntimeError", "x", None, None, "tb", ts=250.0))
    out = text_of(S.apply(none_err, S.Finished(1)))
    assert "frame= 1152" in out
    assert_fits(out)


def test_error_without_error_event_uses_exit_code():
    out = text_of(S.apply(encoding_state(), S.Finished(2)))
    assert "código 2" in out


def test_cancelled_screen_partial_results():
    base = S.apply(encoding_state(), R.Cancel("requested", ts=250.0))
    removed = S.apply(S.apply(base, R.Cancel("cleaned", True, ts=251.0)), S.Finished(130))
    assert "Encode interrompido pelo usuário" in text_of(removed)
    assert "output parcial removido" in text_of(removed)
    kept = S.apply(S.apply(base, R.Cancel("cleaned", False, ts=251.0)), S.Finished(130))
    assert "NÃO foi possível remover" in text_of(kept)
    none = S.apply(base, S.Finished(130))
    out = text_of(none)
    assert "nenhum output parcial" in out
    assert_fits(out)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_screens.py -v` → os novos falham.

- [ ] **Step 3: Implement** — acrescentar a `ui/tui/screens.py`:

```python
def stderr_lines(err, log) -> list:
    raw = getattr(err, "stderr_tail", None) if err is not None else None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if raw:
        return [ln for ln in raw.replace("\r", "\n").split("\n") if ln.strip()]
    return [r.text for r in log if r.kind == "FFMPEG"][-40:]


def action_row(s: S.UIState) -> Text:
    g = glyphs()
    out = Text("   ")
    for i, name in enumerate(S.final_actions(s)):
        focused = i == s.action_focus
        out.append(f"{g['arrow'] if focused else ' '}[ {name} ]   ", style="tab.active" if focused else "muted")
    return out


def _fmt(v, unit=""):
    return f"{v:.1f}{unit}" if isinstance(v, (int, float)) else "—"


def _ebu_table(qc) -> Table:
    audio = (qc or {}).get("audio", {})
    before, after = audio.get("before") or {}, audio.get("after") or {}
    targets = (qc or {}).get("targets") or {}
    t = Table(box=None, expand=True, padding=(0, 2))
    for col in ("", "ANTES", "DEPOIS", "Alvo"):
        t.add_column(col, style="label" if not col else "value")
    for key, unit in (("I", " LUFS"), ("TP", " dBTP"), ("LRA", " LU")):
        t.add_row(key, _fmt(before.get(key), unit), _fmt(after.get(key), unit), _fmt(targets.get(key), unit))
    return t


def _seal_checks(qc: dict) -> list:
    return [(c.get("label", ""), c.get("value", ""), c.get("passed")) for c in qc.get("checks", [])]


def _seal(s: S.UIState) -> RenderableType:
    qc = s.qc or {}
    revealed = s.seal_reveal_start is not None and s.now - s.seal_reveal_start >= S.SEAL_REVEAL_S
    if not revealed:
        chips = [C.quality_chip(c.get("label", ""), c.get("passed")) for c in qc.get("checks", [])]
        return Panel(Group(Text(" verificando…", style="muted"), *chips), title="[panel.title]MASTER QC[/]",
                     title_align="left", box=HEAVY_BOX, border_style="panel.border", height=14)
    return C.delivery_seal(_seal_checks(qc), ready=qc.get("summary", {}).get("ready"))


def _delivery(s: S.UIState) -> Panel:
    cfg = s.config
    base = os.path.splitext(basename(s.output_path))[0]
    cert = f"{base}.qc.html · .qc.json" if cfg.get("report", "on") == "on" else "certificado desativado (--report off)"
    meter = "FFplay ANTES / DEPOIS" if cfg.get("ebu_meter", "on") == "on" else "desligado"
    return panel(kv_table([("certificado", cert), ("monitor EBU", meter)]), "DELIVERY", height=5)


def _qc(s: S.UIState) -> RenderableType:
    spin = SPINNER[int(s.now * 10) % len(SPINNER)]
    sub = Text(f" {spin} medindo loudness · checks do master" if s.qc is None else " checks concluídos",
               style="muted")
    return Group(_job_strip(s), panel(Group(stage_rail(s), sub), "QC", height=5),
                 panel(_ebu_table(s.qc), "EBU R128 — AUDITORIA PÓS-ENCODE", height=9),
                 _seal(s),
                 _delivery(s))


def _verdict(qc) -> Text:
    if qc is None:
        return Text("   QC indisponível", style="muted")
    ready = qc.get("summary", {}).get("ready")
    if ready:
        return Text("   ★ DELIVERY READY ★", style="seal")
    return Text("   ⚠ REVISAR ENTREGA ⚠", style="warn")


def _completed(s: S.UIState) -> RenderableType:
    g = glyphs()
    qc = s.qc or {}
    out_info, enc, video = qc.get("output", {}), qc.get("encode", {}), qc.get("video", {})
    summary, after = qc.get("summary", {}), (qc.get("audio", {}) or {}).get("after") or {}
    top = hero([Text(""), Text(f"   {g['ok']} ENCODE COMPLETE", style="ok"), Text(""), _verdict(s.qc),
                Text(f"   {basename(s.output_path)}", style="muted")], height=8)
    res = f"{video.get('width')} × {video.get('height')}" if video.get("width") else "—"
    left = panel(kv_table([
        ("arquivo", basename(s.output_path)),
        ("tamanho", out_info.get("size_human") or "—"),
        ("duração", enc.get("duration_human") or fmt_secs(s.done.seconds if s.done else None)),
        ("vídeo", f"{video.get('codec') or '—'} · {res} · {_fmt(video.get('fps'))} fps"),
    ]), "OUTPUT", height=14)
    right = panel(kv_table([
        ("passed", summary.get("passed", "—")),
        ("warnings", summary.get("warnings", "—")),
        ("failed", summary.get("failed", "—")),
        ("I depois", _fmt(after.get("I"), " LUFS")),
        ("TP depois", _fmt(after.get("TP"), " dBTP")),
        ("LRA depois", _fmt(after.get("LRA"), " LU")),
    ]), "MASTER QC · RESUMO", height=14)
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(left, right)
    return Group(top, mid, _delivery(s), action_row(s))


def _error(s: S.UIState) -> RenderableType:
    err = s.error
    msg = f"{err.kind}: {err.message}" if err is not None else f"Encode terminou com erro (código {s.exit_code})"
    card = C.error_card(msg)
    lines = stderr_lines(err, s.log)
    start = min(s.error_scroll, max(0, len(lines) - 17))
    body = Group(*[Text(ln, overflow="ellipsis", no_wrap=True) for ln in lines[start:start + 17]]) if lines \
        else Text("—", style="muted")
    p = s.progress
    state = panel(kv_table([
        ("etapa", f"{s.stage or '—'}{' · ' + s.substep if s.substep else ''}"),
        ("último frame", f"{p.frame} / {p.total}" if p else "—"),
        ("output", f"o output parcial pode existir: {basename(s.output_path)}"),
    ]), "ESTADO", height=5)
    return Group(card, panel(body, "FFMPEG STDERR", height=19), state, action_row(s))


def _cancelled(s: S.UIState) -> RenderableType:
    if s.partial_removed is True:
        partial = f"output parcial removido: {basename(s.output_path)}"
    elif s.partial_removed is False:
        partial = f"NÃO foi possível remover {basename(s.output_path)} — apague à mão antes de rodar de novo"
    else:
        partial = "nenhum output parcial"
    card = Panel(Group(Text(""), Text("   ⚠ Encode interrompido pelo usuário", style="warn"), Text(""),
                       Text(f"   {partial}")), box=HEAVY_BOX, border_style="warn", height=8)
    return Group(card, _log_panel(s), action_row(s))


SCREEN_RENDERERS[S.QC] = _qc
SCREEN_RENDERERS[S.COMPLETED] = _completed
SCREEN_RENDERERS[S.ERROR] = _error
SCREEN_RENDERERS[S.CANCELLED] = _cancelled
```

`ESTADO` usa altura 5 (3 linhas + borda) em vez dos 4 do wireframe de §W, para caber sem truncar; a diferença de 1 linha sai da área do stderr se o corpo exceder 34 linhas.

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_screens.py -v` → verdes; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens.py
git commit -m "feat(tui): telas de QC, COMPLETED, ERROR e CANCELLED (P3B)"
```

---

### Task 6: `app.py` — ciclo de vida

**Files:**
- Create: `ui/tui/app.py`
- Test: `ui/tui/test_app.py`

**Interfaces:**
- Consumes: `state` (Task 1), `keys.KeyReader` (Task 2), `screens.render` (Tasks 3–5), `ui.tui_driver.run_single(ns, events, control, on_tick) -> int` e `ui.tui_driver._single_output_path(ns) -> str`, `ui.tui_capture.ConsoleCapture(console, emit)` e `ui.tui_capture._Sink(emit)` (objeto com `write/flush/isatty`), `reporter.CancelControl(terminate)`, `Reels_Encoder_v2_FINAL.console` e `.terminate_active_ffmpeg`.
- Produces: `class App(ns, *, console=None, run_single=None, reader_factory=None, live_factory=None, clock=time.monotonic, sleep=time.sleep, perf=None)` com `run() -> int`; atributo `state` (último `UIState`) para testes.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_app.py`

```python
import argparse
import sys

import pytest

import reporter as R
import Reels_Encoder_v2_FINAL as RE
from ui.tui import app as A
from ui.tui import state as S


class FakeLive:
    def __init__(self):
        self.frames = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def update(self, renderable, refresh=True):
        self.frames.append(renderable)


class FakeReader:
    def __init__(self, keys):
        self.keys = list(keys)
        self.stopped = self.restored = False

    def __call__(self, emit):
        self.emit = emit
        return self

    def start(self):
        for k in self.keys:
            self.emit(S.Key(k))

    def stop(self):
        self.stopped = True

    def restore(self):
        self.restored = True


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        self.t += 0.5
        return self.t


def ns(tmp_path):
    src = tmp_path / "in.mov"
    src.write_bytes(b"x")
    return argparse.Namespace(input=str(src), mode="crf", cineon_pipeline="off", output_dir=None,
                              report="on", ebu_meter="off", fit="contain", threads=0, performance="balanced")


def make(tmp_path, keys, run_single, **kw):
    live = FakeLive()
    reader = FakeReader(keys)
    app = A.App(ns(tmp_path), run_single=run_single, reader_factory=reader, live_factory=lambda c: live,
                clock=Clock(), sleep=lambda s: None, perf=lambda: (10.0, 20.0, 1.0),
                size=lambda: (120, 40), output_path=str(tmp_path / "out.mp4"), **kw)
    return app, live, reader


def fake_success(events_to_emit, code=0):
    def run(ns_, q, control, on_tick):
        for ev in events_to_emit:
            q.put(ev)
            on_tick()
        q.put(S.Key("ENTER"))
        return code
    return run


def test_ready_esc_returns_zero_without_encoding(tmp_path):
    called = []
    app, live, reader = make(tmp_path, ["ESC"], lambda *a: called.append(1) or 0)
    assert app.run() == 0
    assert called == [] and reader.stopped and reader.restored


def test_ready_keys_after_enter_stay_queued(tmp_path):
    seen = []

    def run(ns_, q, control, on_tick):
        seen.append(q.qsize())
        q.put(S.Key("ENTER"))
        return 0

    app, _, _ = make(tmp_path, ["ENTER", "D"], run)
    assert app.run() == 0
    assert seen == [1]


def test_success_flow_reaches_completed_then_exit(tmp_path):
    evs = [R.Stage(R.PREPARING, ts=1.0), R.Stage(R.PASS, "1", ts=2.0), R.Pass(1, 1, "Encode", "start", ts=2.0),
           R.Pass(1, 1, "Encode", "end", ts=3.0), R.Stage(R.DONE, ts=4.0), R.Done("out.mp4", 3.0, ts=4.0)]
    app, live, _ = make(tmp_path, ["ENTER"], fake_success(evs))
    assert app.run() == 0
    assert app.state.screen == S.COMPLETED and live.frames


def test_error_flow_returns_1(tmp_path):
    app, _, _ = make(tmp_path, ["ENTER"],
                     fake_success([R.Error("RuntimeError", "boom", None, None, "tb", ts=1.0)], code=1))
    assert app.run() == 1
    assert app.state.screen == S.ERROR


def test_c_confirm_calls_request_cancel(tmp_path):
    calls = []

    def run(ns_, q, control, on_tick):
        q.put(R.Stage(R.PASS, "1", ts=1.0))
        on_tick()
        q.put(S.Key("C"))
        q.put(S.Key("RIGHT"))
        q.put(S.Key("ENTER"))
        on_tick()
        calls.append(control.cancelled)
        q.put(S.Key("ENTER"))
        return 130

    app, _, _ = make(tmp_path, ["ENTER"], run, terminate=lambda: True)
    assert app.run() == 130
    assert calls == [True] and app.state.screen == S.CANCELLED


def test_ctrl_c_in_ready_returns_130_and_restores(tmp_path, monkeypatch):
    orig = sys.stderr
    app, _, reader = make(tmp_path, [], lambda *a: 0)
    monkeypatch.setattr(app, "_tick", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert app.run() == 130
    assert sys.stderr is orig and reader.restored
    assert RE.console.file is not None


def test_stderr_and_console_restored_on_unexpected_exception(tmp_path):
    orig_err, orig_file = sys.stderr, RE.console.file

    def boom(*a):
        raise ValueError("bug")

    app, _, reader = make(tmp_path, ["ENTER"], boom)
    with pytest.raises(ValueError):
        app.run()
    assert sys.stderr is orig_err and RE.console.file is orig_file and reader.restored


def test_render_exception_does_not_escape_on_tick(tmp_path, monkeypatch):
    seen = []

    def run(ns_, q, control, on_tick):
        on_tick()
        seen.append("still-running")
        q.put(S.Key("ENTER"))
        return 0

    app, live, _ = make(tmp_path, ["ENTER"], run)
    monkeypatch.setattr(A, "render", lambda s: (_ for _ in ()).throw(RuntimeError("render bug")))
    assert app.run() == 0
    assert seen == ["still-running"]


def test_resize_mid_encode_keeps_running(tmp_path):
    sizes = iter([(120, 40), (90, 30), (90, 30), (120, 40)] + [(120, 40)] * 50)
    evs = [R.Stage(R.PASS, "1", ts=1.0), R.Stage(R.DONE, ts=2.0)]
    app, live, _ = make(tmp_path, ["ENTER"], fake_success(evs))
    app._size = lambda: next(sizes)
    assert app.run() == 0


def test_stderr_writes_become_log_rows(tmp_path):
    def run(ns_, q, control, on_tick):
        sys.stderr.write("Traceback (most recent call last):\n  oops\n")
        on_tick()
        q.put(S.Key("ENTER"))
        return 1

    app, _, _ = make(tmp_path, ["ENTER"], run)
    app.run()
    assert any("Traceback" in r.text for r in app.state.log)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_app.py -v` → FAIL (`ModuleNotFoundError: ui.tui.app`).

- [ ] **Step 3: Implement** — `ui/tui/app.py`

```python
from __future__ import annotations

import queue
import sys
import time
from dataclasses import replace
from typing import Callable

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

import reporter as R
import Reels_Encoder_v2_FINAL as RE
from ui import tui_driver as D
from ui.theme import get_console
from ui.tui import state as S
from ui.tui.keys import KeyReader
from ui.tui.screens import render
from ui.tui_capture import ConsoleCapture, _Sink

TICK_S = 0.1


def _default_perf():
    try:
        import psutil

        vm = psutil.virtual_memory()
        return psutil.cpu_percent(interval=None), vm.percent, vm.used / 1e9
    except Exception:
        return None, None, None


class App:
    def __init__(self, ns, *, console=None, run_single=None, reader_factory=None, live_factory=None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 perf=None, size=None, output_path: str | None = None, terminate=None):
        self._ns = ns
        self._console = console or get_console()
        self._run_single = run_single or D.run_single
        self._reader_factory = reader_factory or KeyReader
        self._live_factory = live_factory or (lambda c: Live(console=c, screen=True, auto_refresh=False))
        self._clock = clock
        self._sleep = sleep
        self._perf = perf or _default_perf
        self._size = size or (lambda: (self._console.size.width, self._console.size.height))
        self._terminate = terminate or RE.terminate_active_ffmpeg
        out = output_path if output_path is not None else D._single_output_path(ns)
        self.state = S.UIState(config=dict(vars(ns)), output_path=out)
        self._queue: queue.Queue = queue.Queue()
        self._control = R.CancelControl(terminate=self._terminate)
        self._live = None

    def run(self) -> int:
        reader = self._reader_factory(self._queue.put)
        orig_stderr = sys.stderr
        code = 1
        try:
            with self._live_factory(self._console) as live, ConsoleCapture(RE.console, self._queue.put):
                self._live = live
                sys.stderr = _Sink(self._queue.put)
                try:
                    reader.start()
                    code = self._session()
                except KeyboardInterrupt:
                    code = 130
                finally:
                    reader.stop()
                    sys.stderr = orig_stderr
        finally:
            sys.stderr = orig_stderr
            reader.restore()
        return code

    def _session(self) -> int:
        self._until(lambda s: s.action in ("start", "exit"))
        if self.state.action == "exit":
            return 0
        self.state = replace(self.state, action=None)
        code = self._run_single(self._ns, self._queue, self._control, self._tick)
        self.state = S.apply(self.state, S.Finished(code))
        self._until(lambda s: s.action == "exit")
        return code

    def _until(self, done: Callable[[S.UIState], bool]) -> None:
        while not done(self.state):
            self._tick()
            if not done(self.state):
                self._sleep(TICK_S)

    def _tick(self) -> None:
        while True:
            try:
                ev = self._queue.get_nowait()
            except queue.Empty:
                break
            self.state = S.apply(self.state, ev)
            if self.state.action == "cancel":
                self.state = replace(self.state, action=None)
                self._control.request_cancel()
            elif self.state.action in ("start", "exit"):
                break
        cpu, ram, used = self._perf()
        self.state = S.apply(self.state, S.Tick(self._clock(), tuple(self._size()), cpu, ram, used))
        try:
            frame = render(self.state)
        except Exception as exc:
            frame = Panel(Text(f"erro ao desenhar a tela: {exc!r}\no encode continua", style="err"))
        self._live.update(frame, refresh=True)
```

Notas para quem implementa: (a) a ordem do `finally` segue a spec §7 — para a thread de teclado, restaura `sys.stderr`, sai da captura (fim do `with`), fecha o `Live`, restaura o terminal (`reader.restore()`); (b) um `KeyboardInterrupt` durante `run_single` é tratado pelo condutor, que devolve 130 — o `except KeyboardInterrupt` aqui só cobre READY e a tela final; (c) `run_single` nunca vê exceção de render porque `_tick` a captura (Review Focus 1); (d) `_Sink` é privado de `ui/tui_capture.py`; importá-lo é permitido aqui (mesmo pacote `ui`), sem alterar aquele módulo.

- [ ] **Step 4: Run** — `python -m pytest ui/tui/test_app.py -v` (3× para flake) → verdes; `python -m pytest ui/ test_render_queue.py -q --timeout=120`; `ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/app.py ui/tui/test_app.py
git commit -m "feat(tui): ciclo de vida com Live único, captura e teclado (P3B)"
```

---

### Task 7: `__main__.py` — entrada `python -m ui.tui`

**Files:**
- Create: `ui/tui/__main__.py`
- Test: `ui/tui/test_main.py`

**Interfaces:**
- Consumes: `App` (Task 6); `ui.launcher.run_launcher(console=None) -> Namespace | None`; o preflight de binários e `RE._validate_args_consistency(ns) -> str | None` exatamente como `RE.main()` os chama (ler o bloco de `main()` entre a decisão de modo UI e o despacho; usar as mesmas funções e mensagens/códigos: binários ausentes → 1 com o card de dependência; validação → 2).
- Produces: `main() -> int`; `terminal_ok(console, stdin=sys.stdin, stdout=sys.stdout) -> bool`.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_main.py`

```python
import argparse
import types

import Reels_Encoder_v2_FINAL as RE
from ui.tui import __main__ as M


class Tty:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


def console(w=120, h=40, terminal=True, legacy=False):
    return types.SimpleNamespace(is_terminal=terminal, legacy_windows=legacy,
                                 size=types.SimpleNamespace(width=w, height=h), print=lambda *a, **k: None)


def test_terminal_ok_rules():
    assert M.terminal_ok(console(), Tty(True), Tty(True))
    assert not M.terminal_ok(console(), Tty(False), Tty(True))
    assert not M.terminal_ok(console(119, 40), Tty(True), Tty(True))
    assert not M.terminal_ok(console(120, 39), Tty(True), Tty(True))
    assert not M.terminal_ok(console(legacy=True), Tty(True), Tty(True))
    assert not M.terminal_ok(console(terminal=False), Tty(True), Tty(True))


def test_fallback_runs_classic_main(monkeypatch):
    called = []
    monkeypatch.setattr(M, "get_console", lambda: console(80, 24))
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)
    monkeypatch.setattr(RE, "main", lambda: called.append(1))
    assert M.main() == 0 and called == [1]


def test_fallback_propagates_classic_exit_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)

    def boom():
        raise SystemExit(2)

    monkeypatch.setattr(RE, "main", boom)
    assert M.main() == 2


def test_launcher_cancel_returns_zero(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: None)
    assert M.main() == 0


def test_validation_error_returns_2(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda ns: "inválido")
    assert M.main() == 2


def test_missing_binaries_returns_1(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: ["ffmpeg"])
    assert M.main() == 1


def test_runs_app_and_returns_its_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda ns: None)
    monkeypatch.setattr(M, "App", lambda ns, console=None: types.SimpleNamespace(run=lambda: 130))
    assert M.main() == 130
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/tui/test_main.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** — `ui/tui/__main__.py`

```python
from __future__ import annotations

import sys

import Reels_Encoder_v2_FINAL as RE
from ui import components as C
from ui.launcher import run_launcher
from ui.theme import get_console
from ui.tui.app import App
from ui.tui.state import MIN_SIZE


def terminal_ok(console, stdin=None, stdout=None) -> bool:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    return (stdin.isatty() and stdout.isatty() and console.is_terminal and not console.legacy_windows
            and console.size.width >= MIN_SIZE[0] and console.size.height >= MIN_SIZE[1])


def _missing_binaries() -> list:
    from ui.preflight import missing_ffmpeg_binaries

    return list(missing_ffmpeg_binaries() or [])


def _exit_code(exc: SystemExit) -> int:
    if exc.code is None:
        return 0
    return exc.code if isinstance(exc.code, int) else 1


def main() -> int:
    console = get_console()
    if not terminal_ok(console):
        console.print("[warn]A TUI precisa de um terminal interativo com VT e pelo menos 120×40 — "
                      "abrindo o modo clássico.[/warn]")
        try:
            RE.main()
        except SystemExit as exc:
            return _exit_code(exc)
        return 0
    ns = run_launcher(console)
    if ns is None:
        return 0
    missing = _missing_binaries()
    if missing:
        console.print(C.dependency_error_card(missing))
        return 1
    err = RE._validate_args_consistency(ns)
    if err:
        console.print(C.error_card(err))
        return 2
    return App(ns, console=console).run()


if __name__ == "__main__":
    sys.exit(main())
```

Antes de finalizar `_missing_binaries`, conferir em `RE.main()` como `missing_ffmpeg_binaries` é chamado (argumentos e formato de retorno) e espelhar exatamente; idem a mensagem de validação (se `main()` imprime de outro jeito, usar o mesmo texto via `C.error_card`).

- [ ] **Step 4: Run** — `python -m pytest ui/tui/ -v`; suíte canônica completa uma vez; `ruff check .`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/__main__.py ui/tui/test_main.py
git commit -m "feat(tui): entrada python -m ui.tui com guarda do terminal (P3B)"
```

---

### Task 8: Verificação manual no Windows Terminal (usuário)

**Files:**
- Create (scratchpad, fora do repo): `<SCRATCH>\p3b\P3B_ROTEIRO.md`, onde `<SCRATCH>` = scratchpad da sessão do Orquestrador. Sem script novo: o roteiro roda `python -m ui.tui` com o venv do projeto.

- [ ] **Step 1:** Roteiro (≤ 1 página, PowerShell copiável, cópia do vídeo em pasta isolada como no B-4) com: T1 native 2-pass até COMPLETED (selo, VER QC, VER LOG, SAIR); T2 Cineon CRF até COMPLETED; T3 D/L/ESC e filtros do LOG durante o encode; T4 `C` → CONTINUAR (segue) e `C` → CANCELAR (CANCELLED, parcial removido, exit 130); T5 MCTF on: `░[C]` na máscara; T6 Ctrl+C no PASS 1 (exit 130); T7 reduzir a janela abaixo de 120×40 durante o encode e voltar; T8 abrir em janela pequena → modo clássico. Após cada: `$LASTEXITCODE`, `Get-Process ffmpeg`, arquivos restantes, terminal utilizável.
- [ ] **Step 2:** Usuário roda e devolve; Orquestrador registra em VALIDATION.md.

---

### Task 9: Fechamento (Orquestrador)

- [ ] Suíte canônica + `ruff check .`; comparar com o baseline da Task 1 Step 0.
- [ ] STATE.md / FINDINGS.md / VALIDATION.md; push e PR só com pedido do usuário.
