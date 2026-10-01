from __future__ import annotations

import io
import os
import queue
import threading
import time
import traceback
from typing import Callable

from rich.console import Console

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
        render_queue.run_job(job, encode_fn, Console(file=io.StringIO()), on_tick=on_tick)
    except KeyboardInterrupt:
        events.put(R.Cancel("requested", job_id=job_id))
        control.force_cancel()
        RE.terminate_active_ffmpeg()
        deadline = time.monotonic() + WORKER_WAIT_S
        while not worker_done.wait(0.25) and time.monotonic() < deadline:
            try:
                on_tick()
            except KeyboardInterrupt:
                pass
        raise
    worker_done.wait(WORKER_WAIT_S)
    if control.cancelled and job.status == "falha":
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


def _qc_report_paths(output_path: str) -> tuple[str, str]:
    base = os.path.splitext(output_path)[0]
    return base + ".qc.html", base + ".qc.json"


def _existing_qc_reports(output_path: str) -> frozenset:
    return frozenset(p for p in _qc_report_paths(output_path) if os.path.exists(p))


def _cancel_cleanup(job, events, remove_partial: bool, job_id: int,
                    batch: bool = False, reports_preexisted: frozenset = frozenset()) -> None:
    events.put(R.Cancel("terminated", job_id=job_id))
    if remove_partial:
        removed = render_queue.discard_partial_output(job)
        if removed:
            for path in _qc_report_paths(job.output_path):
                if path not in reports_preexisted:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        events.put(R.Cancel("cleaned", removed, job_id=job_id))
        if not removed and os.path.exists(job.output_path):
            rerun = "rodar a fila de novo" if batch else "rodar o encode de novo"
            events.put(R.Info(
                f"NÃO foi possível remover {os.path.basename(job.output_path)}",
                job_id=job_id))
            events.put(R.Info(
                "Este arquivo está incompleto e NÃO passou pelo controle de qualidade. "
                f"Apague-o à mão antes de {rerun}, ou ele será tratado "
                "como pronto.", job_id=job_id))


def run_single(ns, events: queue.Queue, control: R.CancelControl,
               on_tick: Callable[[], None]) -> int:
    err = RE._validate_args_consistency(ns)
    if err:
        events.put(R.Error("validation", err, None, None, None))
        return 2
    out = _single_output_path(ns)
    job = render_queue.QueueJob(input_path=ns.input, output_path=out)
    output_preexisted = os.path.exists(out)
    reports_preexisted = _existing_qc_reports(out)
    try:
        result = _run_one(job, ns, events, control, on_tick, 0, is_batch=False)
    except KeyboardInterrupt:
        result = "cancelado"
    if result == "ok":
        return 0
    if result == "falha":
        return 1
    _cancel_cleanup(job, events, remove_partial=not output_preexisted, job_id=0,
                    reports_preexisted=reports_preexisted)
    return 130


def _batch_jobs(ns) -> tuple[str, list]:
    args = ns
    batch_folder = os.path.abspath(args.batch)
    video_files = RE.find_video_files(batch_folder)
    output_folder = (
        os.path.abspath(args.output_dir)
        if args.output_dir
        else batch_folder
    )
    if args.output_dir:
        os.makedirs(output_folder, exist_ok=True)

    jobs: list[render_queue.QueueJob] = []
    for input_file in video_files:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        if args.cineon_pipeline == "on":
            out_name = f"{base_name}_Cineon_Film.mp4"
        elif args.mode == "crf":
            out_name = f"{base_name}_Hollywood_CRF18.mp4"
        else:
            out_name = f"{base_name}_Hollywood_2Pass.mp4"
        output_file = os.path.join(output_folder, out_name)
        jobs.append(render_queue.QueueJob(input_path=input_file, output_path=output_file))
    return output_folder, jobs


def run_batch(ns, events: queue.Queue, control: R.CancelControl,
              on_tick: Callable[[], None]) -> int:
    err = RE._validate_args_consistency(ns)
    if err:
        events.put(R.Error("validation", err, None, None, None))
        return 2
    folder = os.path.abspath(ns.batch)
    if not os.path.isdir(folder):
        events.put(R.Error("batch_folder", f"Pasta não encontrada: {folder}", None, None, None))
        return 1
    if not RE.find_video_files(folder):
        events.put(R.Info(f"Nenhum vídeo encontrado em: {folder}"))
        events.put(R.QueueDone(0))
        return 0
    _, jobs = _batch_jobs(ns)
    events.put(R.QueueInit(tuple((j.input_path, j.output_path) for j in jobs)))
    for i, job in enumerate(jobs):
        if os.path.exists(job.output_path):
            job.status = "pulado"
            events.put(R.JobSkip(i, "output existe", job_id=i))
            continue
        events.put(R.JobStart(i, job_id=i))
        reports_preexisted = _existing_qc_reports(job.output_path)
        try:
            result = _run_one(job, ns, events, control, on_tick, job_id=i, is_batch=True)
        except KeyboardInterrupt:
            _cancel_cleanup(job, events, True, i, batch=True,
                            reports_preexisted=reports_preexisted)
            events.put(R.QueueDone(130))
            return 130
        events.put(R.JobDone(i, job.status, job.error, job_id=i))
        if result == "cancelado":
            _cancel_cleanup(job, events, True, i, batch=True,
                            reports_preexisted=reports_preexisted)
            events.put(R.QueueDone(130))
            return 130
    code = 1 if any(j.status == "falha" for j in jobs) else 0
    events.put(R.QueueDone(code))
    return code
