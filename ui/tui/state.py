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
    removal_failed: bool = False
    output_preexisted: bool = False
    exit_code: int | None = None
    seal_reveal_start: float | None = None
    action: str | None = None


def cancel_blocked(s: UIState) -> bool:
    return (s.stage, s.substep) in R.CANCEL_BLOCKED


def seal_revealed(s: UIState) -> bool:
    return s.seal_reveal_start is not None and s.now - s.seal_reveal_start >= SEAL_REVEAL_S - 1e-6


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
        if "NÃO foi possível remover" in ev.text:
            s = replace(s, removal_failed=True)
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
        if s.qc is None or seal_revealed(s):
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
