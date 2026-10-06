from __future__ import annotations

import re
from dataclasses import dataclass, replace

import reporter as R
from ui.tui import forms as F
from ui.tui import widgets as W

READY = "READY"
ENCODING = "ENCODING"
DETAILS = "DETAILS"
LOG = "LOG"
QC = "QC"
COMPLETED = "COMPLETED"
ERROR = "ERROR"
CANCELLED = "CANCELLED"
HOME = "HOME"
SOURCE = "SOURCE"
CONFIGURATION = "CONFIGURATION"
ADVANCED = "ADVANCED"
PREVIEW = "PREVIEW"
QUEUE = "QUEUE"
REPORT = "REPORT"
CONFIG_SCREENS = frozenset({HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW})
ACTIONS = ("start", "exit", "tools", "arm", "check_source")
FINAL_SCREENS = frozenset({COMPLETED, ERROR, CANCELLED, REPORT})
OVERLAYS = frozenset({DETAILS, LOG})
SEAL_REVEAL_S = 1.2
MIN_SIZE = (120, 40)
LOG_CAP = 500
REPORT_ROWS = 21
LOG_FILTERS = ("TUDO", "SYSTEM", "INFO", "WARNING", "FFMPEG")
_WARNING_RE = re.compile(r"^aviso\b|\bfalhou\b|n[ãa]o foi poss[ií]vel", re.IGNORECASE)


@dataclass(frozen=True)
class Key:
    name: str
    char: str | None = None


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
class SourceChecked:
    path: str
    status: str
    dims: tuple | None = None
    count: int | None = None


@dataclass(frozen=True)
class Armed:
    config: dict
    output_path: str
    output_preexisted: bool
    error: str | None = None


@dataclass(frozen=True)
class ReadyBlocked:
    message: str


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
class Job:
    input: str
    output: str
    status: str = "aguardando"
    started: float | None = None
    finished: float | None = None
    reason: str | None = None


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
    preset: int = 0
    drafts: tuple = ()
    focus: tuple = ()
    home_focus: int = 0
    tab: int = 0
    tab_focus: bool = False
    edit: W.TextBuf | None = None
    field_error: str | None = None
    source: W.TextBuf = W.TextBuf()
    source_status: str = "INVALID"
    source_dims: tuple | None = None
    came_from: str = CONFIGURATION
    adv_back: str = SOURCE
    ready_error: str | None = None
    system: tuple = ()
    source_count: int | None = None
    queue: tuple = ()
    active_job: int | None = None
    queue_started: float | None = None
    queue_finished: float | None = None
    is_batch: bool = False
    queue_scroll: int = 0


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


def queue_counts(queue: tuple) -> dict:
    out = dict.fromkeys(("aguardando", "processando", "ok", "pulado", "falha", "interrompido"), 0)
    for job in queue:
        out[job.status] = out.get(job.status, 0) + 1
    out["total"] = len(queue)
    return out


def queue_eta(s: UIState) -> float | None:
    durations = [j.finished - j.started for j in s.queue
                 if j.status in ("ok", "falha") and j.started is not None and j.finished is not None]
    if not durations:
        return None
    mean = sum(durations) / len(durations)
    eta = mean * sum(1 for j in s.queue if j.status == "aguardando")
    active = s.queue[s.active_job] if s.active_job is not None and s.active_job < len(s.queue) else None
    if active is not None and active.status == "processando" and active.started is not None:
        eta += max(0.0, mean - (s.now - active.started))
    return eta


def draft(s: UIState) -> dict:
    found = dict(s.drafts).get(s.preset)
    return dict(found) if found is not None else F.new_draft(s.preset)


def _with_draft(s: UIState, d: dict) -> UIState:
    others = tuple((p, x) for p, x in s.drafts if p != s.preset)
    return replace(s, drafts=others + ((s.preset, d),))


def focus_key(s: UIState) -> str:
    return f"{ADVANCED}:{s.tab}" if s.screen == ADVANCED else s.screen


def focus_of(s: UIState, key: str) -> int:
    return dict(s.focus).get(key, 0)


def _set_focus(s: UIState, key: str, index: int) -> UIState:
    others = tuple((k, v) for k, v in s.focus if k != key)
    return replace(s, focus=others + ((key, index),))


def form_items(s: UIState) -> tuple:
    d = draft(s)
    if s.screen == ADVANCED:
        return F.visible(F.ADVANCED[F.TABS[s.tab]], d) + (F.CONTINUE,)
    if s.screen == CONFIGURATION:
        return F.visible(F.form_for(s.preset), d) + (F.CONTINUE,)
    return ()


def apply(s: UIState, ev) -> UIState:
    if isinstance(ev, Tick):
        return _tick(s, ev)
    if isinstance(ev, Key):
        return _key(s, ev.name, ev.char)
    if isinstance(ev, Finished):
        return _finished(s, ev.exit_code)
    if isinstance(ev, SourceChecked):
        if ev.path != W.clean_path(s.source.text):
            return s
        return replace(s, source_status=ev.status, source_dims=ev.dims, source_count=ev.count)
    if isinstance(ev, Armed):
        if ev.error:
            return replace(s, field_error=ev.error)
        return replace(
            s,
            screen=READY,
            config=dict(ev.config),
            output_path=ev.output_path,
            output_preexisted=ev.output_preexisted,
            ready_error=None,
            field_error=None,
            is_batch=bool(ev.config.get("batch")),
        )
    if isinstance(ev, ReadyBlocked):
        return replace(s, screen=READY, ready_error=ev.message, action=None)
    return _engine(s, ev)


def _log(s: UIState, kind: str, text: str) -> UIState:
    rows = (s.log + (LogRow(kind, text),))[-LOG_CAP:]
    return replace(s, log=rows, warnings=s.warnings + (1 if kind == "WARNING" else 0))


def _with_track(s: UIState, track: PassTrack) -> UIState:
    others = tuple(t for t in s.passes if t.index != track.index)
    return replace(s, passes=tuple(sorted(others + (track,), key=lambda t: t.index)))


_QUEUE_EVENTS = (R.QueueInit, R.JobStart, R.JobSkip, R.JobDone, R.QueueDone)
_JOB_RESET = {
    "stage": None, "substep": None, "stages_done": (), "passes": (), "progress": None, "job_started": None,
    "probe": None, "encode_params": None, "log": (), "warnings": 0, "qc": None, "done": None, "error": None,
    "seal_reveal_start": None,
}


def _at(s: UIState, ev) -> float:
    return ev.ts if ev.ts else s.now


def _first_line(text) -> str:
    return next((ln.strip() for ln in str(text or "").splitlines() if ln.strip()), "")


def _with_job(s: UIState, index: int, **changes) -> UIState:
    if not 0 <= index < len(s.queue):
        return s
    jobs = list(s.queue)
    jobs[index] = replace(jobs[index], **changes)
    return replace(s, queue=tuple(jobs))


def _interrupt_active(s: UIState, at: float) -> UIState:
    i = s.active_job
    if i is None or not 0 <= i < len(s.queue) or s.queue[i].status != "processando":
        return s
    return _with_job(s, i, status="interrompido", finished=at, reason="interrompido")


def _to_report(s: UIState) -> UIState:
    return replace(s, screen=REPORT, modal=None, modal_focus=0, action_focus=0, queue_scroll=0)


def _queue_event(s: UIState, ev) -> UIState:
    at = _at(s, ev)
    if isinstance(ev, R.QueueInit):
        jobs = tuple(Job(str(i), str(o)) for i, o in ev.jobs)
        screen = QUEUE if s.screen in (READY, ENCODING) else s.screen
        return replace(s, queue=jobs, is_batch=True, active_job=None, queue_started=at, screen=screen)
    if isinstance(ev, R.JobStart):
        if not 0 <= ev.index < len(s.queue):
            return s
        s = replace(s, active_job=ev.index, output_path=s.queue[ev.index].output, **_JOB_RESET)
        return _with_job(s, ev.index, status="processando", started=at, finished=None, reason=None)
    if isinstance(ev, R.JobSkip):
        return _with_job(s, ev.index, status="pulado", reason="saída já existe")
    if isinstance(ev, R.JobDone):
        status = "interrompido" if s.cancel_phase is not None and ev.status != "ok" else ev.status
        if status in ("ok", "interrompido"):
            reason = status
        else:
            reason = _first_line(ev.error) or status
        return _with_job(s, ev.index, status=status, finished=at, reason=reason)
    s = replace(s, exit_code=ev.exit_code, queue_finished=at)
    if ev.exit_code == 130:
        s = _interrupt_active(s, at)
    return _to_report(s)


def _engine(s: UIState, ev) -> UIState:
    if isinstance(ev, _QUEUE_EVENTS):
        return _queue_event(s, ev)
    if s.cancel_phase is not None and isinstance(ev, (R.Stage, R.Pass, R.Progress)):
        return s
    if isinstance(ev, R.Stage):
        done = s.stages_done
        if s.stage is not None and s.stage != ev.name and s.stage not in done:
            done = done + (s.stage,)
        started = s.job_started if s.job_started is not None else ev.ts
        s = replace(s, stage=ev.name, substep=ev.substep, stages_done=done, job_started=started)
        s = _log(s, "SYSTEM", ev.name + (f" · {ev.substep}" if ev.substep else ""))
        if ev.name == R.QC and not s.is_batch:
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
        if s.is_batch and s.queue:
            return _log(s, "WARNING", f"{ev.kind}: {ev.message}")
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
    if s.is_batch and (s.queue or code in (0, 130)):
        s = replace(s, exit_code=code)
        if s.screen == REPORT:
            return s
        if code == 130:
            s = _interrupt_active(s, s.now)
        finished = s.queue_finished if s.queue_finished is not None else s.now
        return _to_report(replace(s, queue_finished=finished))
    s = replace(s, exit_code=code, modal=None, action_focus=0)
    if s.screen in OVERLAYS:
        s = replace(s, screen=s.back)
    if code == 0:
        return replace(s, screen=QC if s.qc is not None else COMPLETED)
    return replace(s, screen=CANCELLED if code == 130 else ERROR)


_EDIT_KEYS = frozenset({"CHAR", "SPACE", "BACKSPACE", "DELETE", "LEFT", "RIGHT", "D", "L", "C"})


def _config_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.screen == HOME:
        return _home_key(s, k, ch)
    if s.screen == SOURCE:
        return _source_key(s, k, ch)
    if s.screen == PREVIEW:
        return _preview_key(s, k)
    return _form_key(s, k, ch)


def form_back(s: UIState) -> UIState:
    target = SOURCE if s.screen == CONFIGURATION else s.adv_back
    return replace(s, screen=target, edit=None, field_error=None, tab_focus=False)


def _set_value(s: UIState, name: str, value) -> UIState:
    new, err = F.apply_change(draft(s), name, value)
    if err:
        return replace(s, field_error=err, edit=None)
    s = replace(_with_draft(s, new), field_error=None, edit=None)
    key = focus_key(s)
    return _set_focus(s, key, min(focus_of(s, key), len(form_items(s)) - 1))


def _commit(s: UIState, field) -> UIState:
    if field.kind == "path":
        value = W.clean_path(s.edit.text)
        s = _set_value(s, field.name, value or None)
        return s if value else replace(s, field_error=F.OUTDIR_EMPTY)
    value, err = W.parse_number(s.edit.text, field.lo, field.hi, field.integer)
    if err:
        return replace(s, field_error=err, edit=None)
    return _set_value(s, field.name, value)


def _to_preview(s: UIState) -> UIState:
    if F.outdir_missing(draft(s)):
        if s.screen == ADVANCED:
            s = replace(s, tab=0, tab_focus=False)
        names = [f.name for f in form_items(s)]
        s = _set_focus(s, focus_key(s), names.index("output_dir"))
        return replace(s, field_error=F.OUTDIR_EMPTY, edit=None)
    origin = s.came_from if s.screen == ADVANCED and s.adv_back == PREVIEW else s.screen
    return replace(s, screen=PREVIEW, came_from=origin, action_focus=0, field_error=None)


def _enter_next(s: UIState, key: str, items: tuple, i: int) -> UIState:
    nxt = min(i + 1, len(items) - 1)
    if items[nxt] is not F.CONTINUE:
        return _set_focus(s, key, nxt)
    if s.screen == ADVANCED and s.tab < len(F.TABS) - 1:
        s = replace(s, tab=s.tab + 1, tab_focus=False)
        return _set_focus(s, focus_key(s), 0)
    return _to_preview(s)


def _form_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.screen == ADVANCED and s.tab_focus:
        if k in ("LEFT", "RIGHT"):
            return replace(s, tab=(s.tab + (1 if k == "RIGHT" else -1)) % len(F.TABS))
        if k == "DOWN":
            return _set_focus(replace(s, tab_focus=False), focus_key(s), 0)
        if k == "ESC":
            return form_back(s)
        return s
    items = form_items(s)
    key = focus_key(s)
    i = min(focus_of(s, key), len(items) - 1)
    item = items[i]
    if s.edit is not None:
        if k == "ESC":
            return replace(s, edit=None, field_error=None)
        if k in _EDIT_KEYS:
            return replace(s, edit=W.edit_text(s.edit, k, ch))
        s = _commit(s, item)
        if s.field_error:
            return s
        items = form_items(s)
        i = min(focus_of(s, key), len(items) - 1)
        if k == "ENTER":
            return _enter_next(s, key, items, i)
    if k == "ESC":
        return form_back(s)
    if k == "UP":
        if i == 0 and s.screen == ADVANCED:
            return replace(s, tab_focus=True, field_error=None)
        return _set_focus(replace(s, field_error=None), key, max(0, i - 1))
    if k == "DOWN":
        return _set_focus(replace(s, field_error=None), key, min(len(items) - 1, i + 1))
    if item is F.CONTINUE:
        if k == "ENTER":
            return _to_preview(s)
        return s
    if item.kind == "path":
        if k in _EDIT_KEYS:
            cur = draft(s).get(item.name) or ""
            return replace(s, edit=W.edit_text(W.TextBuf(cur, len(cur)), k, ch), field_error=None)
        if k == "ENTER" and not str(draft(s).get(item.name) or "").strip():
            return replace(s, field_error=F.OUTDIR_EMPTY)
    if k == "ENTER":
        return _enter_next(s, key, items, i)
    if item.kind == "number" and k == "CHAR" and ch and (ch.isdigit() or ch in ".,-"):
        return replace(s, edit=W.TextBuf(ch, 1), field_error=None)
    value = W.change(item, draft(s)[item.name], k)
    if value is None:
        return s
    return _set_value(s, item.name, value)


def _preview_key(s: UIState, k: str) -> UIState:
    if k in ("LEFT", "RIGHT"):
        return replace(s, action_focus=1 - s.action_focus)
    if k == "ESC":
        back = SOURCE if s.came_from == ADVANCED else s.adv_back
        return replace(s, screen=s.came_from, adv_back=back, field_error=None)
    if k == "ENTER":
        if s.action_focus == 0:
            return replace(s, action="arm")
        return replace(s, screen=ADVANCED, adv_back=PREVIEW, tab=0, tab_focus=False, edit=None, field_error=None)
    return s


def _home_key(s: UIState, k: str, ch: str | None) -> UIState:
    if k in ("UP", "DOWN"):
        i = s.home_focus
        step = 1 if k == "DOWN" else -1
        while True:
            i = (i + step) % len(F.PRESET_LABELS)
            if i + 1 in F.ENABLED_PRESETS:
                return replace(s, home_focus=i)
    if k == "ESC":
        return replace(s, action="exit", exit_code=0)
    if k == "ENTER":
        choice = s.home_focus + 1
    elif ch and ch in "12345":
        choice = int(ch)
    else:
        return s
    if choice not in F.ENABLED_PRESETS:
        return s
    s = replace(s, home_focus=choice - 1)
    if choice == 4:
        return replace(s, action="tools")
    s = replace(s, preset=choice, field_error=None, edit=None)
    d = draft(s)
    s = _with_draft(s, d)
    text = d.get("batch" if F.is_folder(d) else "input") or ""
    s = replace(s, screen=SOURCE, source=W.TextBuf(text, len(text)), source_status="INVALID", source_dims=None,
                source_count=None, tab_focus=False)
    return replace(s, source_status="CHECKING", action="check_source") if text else s


def _toggle_kind(s: UIState) -> UIState:
    d = draft(s)
    folder = not F.is_folder(d)
    path = W.clean_path(s.source.text) or None
    d = {**d, F.SOURCE_KIND: F.FOLDER if folder else F.FILE,
         "batch": path if folder else None, "input": None if folder else path}
    s = replace(_with_draft(s, d), source_dims=None, source_count=None, field_error=None)
    if path is None:
        return replace(s, source_status="INVALID")
    return replace(s, source_status="CHECKING", action="check_source")


def _source_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.preset == 5:
        if s.tab_focus:
            if k in ("LEFT", "RIGHT", "SPACE"):
                return _toggle_kind(s)
            if k == "DOWN":
                return replace(s, tab_focus=False)
            if k not in ("ENTER", "ESC"):
                return s
        elif k == "UP":
            return replace(s, tab_focus=True)
    field = "batch" if F.is_folder(draft(s)) else "input"
    if k == "ESC":
        s = _with_draft(s, {**draft(s), field: W.clean_path(s.source.text) or None})
        return replace(s, screen=HOME, tab_focus=False)
    if k == "ENTER":
        if s.source_status != "VALID":
            return s
        s = _with_draft(s, {**draft(s), field: W.clean_path(s.source.text)})
        if s.preset == 5:
            return replace(s, screen=ADVANCED, adv_back=SOURCE, tab_focus=False, edit=None, field_error=None)
        return replace(s, screen=CONFIGURATION, edit=None, field_error=None)
    buf = W.edit_text(s.source, k, ch)
    if buf == s.source:
        return s
    if buf.text == s.source.text:
        return replace(s, source=buf)
    return replace(s, source=buf, source_status="CHECKING", source_dims=None, source_count=None,
                   action="check_source")


def _key(s: UIState, k: str, ch: str | None = None) -> UIState:
    if s.screen in CONFIG_SCREENS:
        return _config_key(s, k, ch)
    if s.screen == READY:
        if k == "ENTER":
            return replace(s, screen=QUEUE if s.is_batch else ENCODING, action="start", ready_error=None)
        if k == "ESC":
            if s.preset:
                return replace(s, screen=PREVIEW, ready_error=None)
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
    if s.screen == REPORT:
        if k in ("UP", "DOWN"):
            top = max(0, len(s.queue) - REPORT_ROWS)
            return replace(s, queue_scroll=max(0, min(top, s.queue_scroll + (1 if k == "DOWN" else -1))))
        if k in ("ENTER", "ESC"):
            return replace(s, action="exit")
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
    if s.screen in (ENCODING, QC, QUEUE):
        if k == "D":
            return replace(s, screen=DETAILS, back=s.screen)
        if k == "L":
            return replace(s, screen=LOG, back=s.screen)
        if k == "C" and s.screen in (ENCODING, QUEUE) and s.cancel_phase is None and not cancel_blocked(s):
            return replace(s, modal="CANCEL", modal_focus=0)
    return s
