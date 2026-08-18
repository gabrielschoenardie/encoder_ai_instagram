"""Fila de render para o modo --batch: estado por job, tabela ao vivo, ETA e relatório final."""

from __future__ import annotations

import os
import statistics
import threading
import time
from dataclasses import dataclass
from typing import Callable

from rich import box
from rich.console import Console
from rich.table import Table

STATUS_SYMBOLS = {
    "aguardando": "·",
    "processando": "⏳",
    "ok": "✓",
    "falha": "✗",
    "pulado": "○",
    "interrompido": "⚡",
}

MAX_LOG_CHARS = 4000


@dataclass
class QueueJob:
    input_path: str
    output_path: str
    status: str = "aguardando"
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    log: str = ""


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_eta(eta_seconds: float | None) -> str:
    if eta_seconds is None:
        return "--:--"
    return format_duration(eta_seconds)


def discard_partial_output(job: QueueJob) -> bool:
    """Remove o output parcial de um job interrompido.

    Retorna True se removeu de fato. Nunca levanta: um arquivo travado pelo
    processo do ffmpeg ainda encerrando (comum no Windows) devolve False.
    """
    path = job.output_path
    if not path or not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def estimate_eta(
    jobs: list[QueueJob],
    remaining: int,
    in_flight_elapsed: float | None = None,
) -> float | None:
    """Estima o tempo restante da fila, em segundos.

    `remaining` conta os jobs que ainda nao comecaram. `in_flight_elapsed`, quando
    informado, e o tempo ja decorrido do job em execucao: o que falta dele entra na
    estimativa, descontado do que ja passou. Sem amostras concluidas, retorna None.
    """
    durations = [
        job.finished_at - job.started_at
        for job in jobs
        if job.status in ("ok", "falha")
        and job.started_at is not None
        and job.finished_at is not None
    ]
    if not durations:
        return None
    mean = statistics.mean(durations)
    eta = mean * remaining
    if in_flight_elapsed is not None:
        eta += max(0.0, mean - in_flight_elapsed)
    return eta


def build_table(
    jobs: list[QueueJob],
    eta_seconds: float | None = None,
    title: str | None = None,
) -> Table:
    total = len(jobs)
    current = sum(1 for job in jobs if job.status != "aguardando")
    if title is None:
        title = f"Job {current} de {total}  ·  ETA: {format_eta(eta_seconds)}"

    table = Table(title=title, box=box.SIMPLE_HEAD)
    table.add_column("#", justify="right")
    table.add_column("Arquivo")
    table.add_column("Status", justify="center")
    table.add_column("Duração", justify="right")

    for idx, job in enumerate(jobs, start=1):
        symbol = STATUS_SYMBOLS[job.status]
        if (
            job.status in ("ok", "falha")
            and job.started_at is not None
            and job.finished_at is not None
        ):
            duration = format_duration(job.finished_at - job.started_at)
        elif job.status == "processando" and job.started_at is not None:
            duration = format_duration(time.time() - job.started_at)
        else:
            duration = "—"
        table.add_row(str(idx), job.input_path, symbol, duration)

    return table


def run_job(
    job: QueueJob,
    encode_fn: Callable[[], None],
    console: Console,
    on_tick: Callable[[], None] | None = None,
    tick_interval: float = 0.25,
) -> None:
    job.status = "processando"
    job.started_at = time.time()
    failure: Exception | None = None
    log_text = ""

    def _target() -> None:
        nonlocal failure, log_text
        with console.capture() as capture:
            try:
                encode_fn()
            except Exception as exc:  # noqa: BLE001 - repassado via job.error, nao propagado
                failure = exc
        log_text = capture.get()

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    try:
        while worker.is_alive():
            if on_tick is not None:
                on_tick()
            worker.join(timeout=tick_interval)
    except KeyboardInterrupt:
        # O KeyboardInterrupt chega na main thread (aqui), nunca no worker: o
        # `except Exception` de _target nao ve BaseException. Sem isto o job
        # ficaria preso em "processando" com finished_at=None.
        # `log_text` so e atribuido depois que o `with console.capture()`
        # sai normalmente dentro de `_target`, o que uma interrupcao no
        # meio do encode impede: aqui ele ainda esta no valor inicial ""
        # (a worker thread nunca chega a fechar o context manager). Ou
        # seja, job.log fica vazio para um job interrompido durante o
        # encode, nao o log parcial capturado ate aquele ponto.
        job.finished_at = time.time()
        job.log = log_text
        job.status = "interrompido"
        raise

    job.finished_at = time.time()
    job.log = log_text
    if failure is not None:
        job.status = "falha"
        job.error = str(failure)
    else:
        job.status = "ok"


def render_final_report(jobs: list[QueueJob], console: Console) -> None:
    total = len(jobs)
    ok = sum(1 for job in jobs if job.status == "ok")
    failed = [job for job in jobs if job.status == "falha"]
    skipped = [job for job in jobs if job.status == "pulado"]
    interrupted = [job for job in jobs if job.status == "interrompido"]
    total_seconds = sum(
        (job.finished_at - job.started_at)
        for job in jobs
        if job.status in ("ok", "falha")
        and job.started_at is not None
        and job.finished_at is not None
    )

    console.print()
    console.rule("[bold magenta]\U0001F4CA Fila — Relatório Final")
    console.print(build_table(jobs, title="Resumo da fila"))
    console.print(f"[green]✓ Sucesso:  {ok}/{total}[/green]")
    if skipped:
        console.print(f"[yellow]○ Pulados:  {len(skipped)}/{total}[/yellow]")
    if interrupted:
        console.print(f"[yellow]⚡ Interrompidos: {len(interrupted)}/{total}[/yellow]")
    if failed:
        console.print(f"[red]✗ Falhas:   {len(failed)}/{total}[/red]")
        for job in failed:
            console.print(f"[red]  • {job.input_path} → {job.error}[/red]")
            log_text = job.log if len(job.log) <= MAX_LOG_CHARS else job.log[-MAX_LOG_CHARS:]
            if log_text.strip():
                console.print(log_text, style="dim", markup=False, soft_wrap=True)
    console.print(f"[dim]Tempo total da fila: {format_duration(total_seconds)}[/dim]")
    console.print()
