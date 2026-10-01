from __future__ import annotations

import os
import queue
import threading
import traceback
from typing import Callable

import Reels_Encoder_v2_FINAL as RE
import render_queue
import reporter as R

WORKER_WAIT_S = 30.0


def _single_output_path(ns) -> str:
    base, _ = os.path.splitext(ns.input)
    if ns.cineon_pipeline == "on":
        output_file = f"{base}_Cineon_Film.mp4"
    elif ns.mode == "crf":
        output_file = f"{base}_Hollywood_CRF18.mp4"
    else:
        output_file = f"{base}_Hollywood_2Pass.mp4"
    return output_file


def _run_one(job, ns, events, control, on_tick, job_id, is_batch) -> str:
    worker_done = threading.Event()
    state: dict = {}
    rep = R.QueueReporter(events, job_id=job_id, control=control)

    def encode_fn() -> None:
        try:
            RE._encode_single_file(job.input_path, job.output_path, ns,
                                   is_batch=is_batch, reporter=rep)
        except R.CancelRequested:
            raise RuntimeError("cancelado pelo usuário") from None
        except Exception as exc:
            state["exc"] = exc
            state["tb"] = traceback.format_exc()
            raise
        finally:
            worker_done.set()

    try:
        render_queue.run_job(job, encode_fn, RE.console, on_tick=on_tick)
    except KeyboardInterrupt:
        control.force_cancel()
        RE.terminate_active_ffmpeg()
        worker_done.wait(WORKER_WAIT_S)
        raise
    worker_done.wait(WORKER_WAIT_S)
    if control.cancelled:
        return "cancelado"
    if job.status == "falha":
        exc = state.get("exc")
        events.put(R.Error(
            type(exc).__name__ if exc else "Exception",
            str(exc) if exc else (job.error or ""),
            getattr(exc, "stderr", None), getattr(exc, "returncode", None),
            state.get("tb"), job_id=job_id))
        return "falha"
    return "ok"


def _cancel_cleanup(job, events, remove_partial: bool, job_id: int) -> None:
    events.put(R.Cancel("terminated", job_id=job_id))
    if remove_partial:
        removed = render_queue.discard_partial_output(job)
        events.put(R.Cancel("cleaned", removed, job_id=job_id))


def run_single(ns, events: queue.Queue, control: R.CancelControl,
               on_tick: Callable[[], None]) -> int:
    err = RE._validate_args_consistency(ns)
    if err:
        events.put(R.Error("validation", err, None, None, None))
        return 2
    out = _single_output_path(ns)
    job = render_queue.QueueJob(input_path=ns.input, output_path=out)
    output_preexisted = os.path.exists(out)
    try:
        result = _run_one(job, ns, events, control, on_tick, 0, is_batch=False)
    except KeyboardInterrupt:
        result = "cancelado"
    if result == "ok":
        return 0
    if result == "falha":
        return 1
    _cancel_cleanup(job, events, remove_partial=not output_preexisted, job_id=0)
    return 130
