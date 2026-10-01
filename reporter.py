from __future__ import annotations

import dataclasses
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

PREPARING = "PREPARING"
PROBING = "PROBING"
ANALYZING = "ANALYZING"
PASS = "PASS"
BETWEEN_PASSES = "BETWEEN_PASSES"
FINALIZING = "FINALIZING"
QC = "QC"
DONE = "DONE"

CANCEL_BLOCKED = {(ANALYZING, "mctf_mask"), (QC, None)}


class CancelRequested(Exception):
    pass


@dataclass(frozen=True)
class Stage:
    name: str
    substep: str | None = None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Hardware:
    fields: dict
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Probe:
    duration: float
    total_frames: int
    fps: int
    width: int
    height: int
    is_hdr: bool
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class EncodeParams:
    vbv_key: str
    target: int
    maxrate: int
    bufsize: int
    vbv_init: float
    x264_preset: str
    mode: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Pass:
    index: int
    total: int
    label: str
    phase: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Progress:
    frame: int
    total: int
    fps: float
    speed: float
    eta: str
    elapsed: float
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class FfmpegLine:
    line: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Info:
    text: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Qc:
    payload: Any
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Done:
    output_path: str
    seconds: float
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Error:
    kind: str
    message: str
    stderr_tail: str | None
    returncode: int | None
    traceback: str | None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Cancel:
    phase: str
    partial_removed: bool | None = None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class QueueInit:
    jobs: tuple
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobStart:
    index: int
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobSkip:
    index: int
    reason: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobDone:
    index: int
    status: str
    error: str | None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class QueueDone:
    exit_code: int
    job_id: int = 0
    ts: float = 0.0


class CancelControl:
    def __init__(self, terminate: Callable[[], bool]):
        self._terminate = terminate
        self._flag = threading.Event()
        self._lock = threading.Lock()
        self.stage: tuple[str, str | None] | None = None

    @property
    def cancelled(self) -> bool:
        return self._flag.is_set()

    def request_cancel(self) -> bool:
        with self._lock:
            if self.stage in CANCEL_BLOCKED:
                return False
            self._flag.set()
        self._terminate()
        return True

    def force_cancel(self) -> None:
        self._flag.set()


_CHECKPOINTS = (Stage, Pass, Progress)


class QueueReporter:
    def __init__(
        self,
        events: queue.Queue,
        job_id: int = 0,
        control: CancelControl | None = None,
        progress_interval: float = 0.1,
    ):
        self._events = events
        self._job_id = job_id
        self._control = control
        self._interval = progress_interval
        self._last_progress: float | None = None

    def emit(self, event) -> None:
        now = time.monotonic()
        if isinstance(event, Progress):
            last = self._last_progress
            if last is not None and now - last < self._interval and event.frame < event.total:
                return
            self._last_progress = now
        if isinstance(event, Stage) and self._control is not None:
            with self._control._lock:
                self._control.stage = (event.name, event.substep)
        self._events.put(dataclasses.replace(event, job_id=self._job_id, ts=now))
        if (
            self._control is not None
            and self._control.cancelled
            and isinstance(event, _CHECKPOINTS)
        ):
            raise CancelRequested()
