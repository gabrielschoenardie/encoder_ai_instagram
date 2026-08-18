import io
import time

import pytest
from rich.console import Console

from render_queue import (
    QueueJob,
    build_table,
    estimate_eta,
    format_duration,
    format_eta,
    render_final_report,
    run_job,
)


def _finished_job(duration_seconds, status="ok", input_path="job.mp4"):
    job = QueueJob(input_path=input_path, output_path=input_path + ".out")
    job.status = status
    job.started_at = 100.0
    job.finished_at = 100.0 + duration_seconds
    return job


def test_estimate_eta_returns_none_with_no_finished_jobs():
    jobs = [QueueJob(input_path="a.mp4", output_path="a_out.mp4")]
    assert estimate_eta(jobs, remaining=3) is None


def test_estimate_eta_uses_mean_of_finished_durations():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    assert estimate_eta(jobs, remaining=2) == pytest.approx(30.0)


def test_estimate_eta_ignores_skipped_and_pending_jobs():
    jobs = [
        _finished_job(10.0),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4", status="pulado"),
        QueueJob(input_path="c.mp4", output_path="c_out.mp4"),
    ]
    assert estimate_eta(jobs, remaining=1) == pytest.approx(10.0)


def test_format_duration_formats_minutes_and_seconds():
    assert format_duration(75) == "01:15"


def test_format_eta_none_is_placeholder():
    assert format_eta(None) == "--:--"


def test_format_eta_formats_seconds():
    assert format_eta(65) == "01:05"


def test_build_table_title_shows_job_count_and_eta():
    jobs = [
        _finished_job(12.0, input_path="a.mp4"),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4"),
    ]
    table = build_table(jobs, eta_seconds=30.0)
    assert "Job 1 de 2" in table.title
    assert "00:30" in table.title


def test_build_table_lists_every_job_with_its_status_symbol():
    jobs = [
        QueueJob(input_path="a.mp4", output_path="a_out.mp4", status="aguardando"),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4", status="processando"),
        _finished_job(12.0, input_path="c.mp4", status="ok"),
        _finished_job(5.0, input_path="d.mp4", status="falha"),
        QueueJob(input_path="e.mp4", output_path="e_out.mp4", status="pulado"),
    ]
    table = build_table(jobs, eta_seconds=None)

    output = io.StringIO()
    console = Console(file=output, width=120)
    console.print(table)
    text = output.getvalue()

    for job in jobs:
        assert job.input_path in text
    for symbol in ["·", "⏳", "✓", "✗", "○"]:
        assert symbol in text


def test_run_job_marks_success_and_keeps_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    output = io.StringIO()
    console = Console(file=output, width=120)

    def encode_fn():
        console.print("trabalhando...")

    run_job(job, encode_fn, console)

    assert job.status == "ok"
    assert job.error is None
    assert "trabalhando..." in job.log


def test_run_job_marks_failure_and_captures_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())

    def encode_fn():
        console.print("preparando encode...")
        raise RuntimeError("ffmpeg explodiu")

    run_job(job, encode_fn, console)

    assert job.status == "falha"
    assert job.error == "ffmpeg explodiu"
    assert "preparando encode..." in job.log


def test_render_final_report_lists_failure_with_captured_log():
    output = io.StringIO()
    console = Console(file=output, width=100)

    ok_job = _finished_job(3.0, input_path="ok.mp4", status="ok")
    failed_job = _finished_job(1.0, input_path="falhou.mp4", status="falha")
    failed_job.error = "ffmpeg explodiu"
    failed_job.log = "preparando encode...\nffmpeg explodiu"

    render_final_report([ok_job, failed_job], console)

    text = output.getvalue()
    assert "1/2" in text
    assert "ffmpeg explodiu" in text
    assert "preparando encode..." in text


def test_render_final_report_truncates_long_logs_keeping_the_tail():
    output = io.StringIO()
    console = Console(file=output, width=200)

    failed_job = _finished_job(1.0, input_path="falhou.mp4", status="falha")
    failed_job.error = "erro"
    failed_job.log = "HEAD-MARKER" + ("y" * 4990) + "TAIL-MARKER"

    render_final_report([failed_job], console)

    text = output.getvalue()
    assert "TAIL-MARKER" in text
    assert "HEAD-MARKER" not in text


def test_run_job_calls_on_tick_while_encode_runs():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())
    tick_count = {"n": 0}

    def encode_fn():
        time.sleep(0.2)

    def on_tick():
        tick_count["n"] += 1

    run_job(job, encode_fn, console, on_tick=on_tick, tick_interval=0.05)

    assert job.status == "ok"
    assert tick_count["n"] >= 2


def test_build_table_shows_ticking_duration_for_running_job():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4", status="processando")
    job.started_at = time.time() - 5.0

    table = build_table([job], eta_seconds=None)

    output = io.StringIO()
    console = Console(file=output, width=120)
    console.print(table)
    text = output.getvalue()

    assert "—" not in text.split("a.mp4", 1)[1].split("\n", 1)[0]
    assert any(f"00:0{n}" in text for n in (3, 4, 5, 6, 7))


def test_estimate_eta_accounts_for_in_flight_job():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    # media = 15s. 1 job na fila + 5s ja decorridos do job em execucao.
    eta = estimate_eta(jobs, remaining=1, in_flight_elapsed=5.0)
    assert eta == pytest.approx(15.0 + 10.0)


def test_estimate_eta_in_flight_longer_than_average_never_goes_negative():
    jobs = [_finished_job(10.0)]
    eta = estimate_eta(jobs, remaining=0, in_flight_elapsed=999.0)
    assert eta == pytest.approx(0.0)


def test_estimate_eta_without_in_flight_is_unchanged():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    assert estimate_eta(jobs, remaining=2) == pytest.approx(30.0)


def test_estimate_eta_still_none_without_samples():
    jobs = [QueueJob(input_path="a.mp4", output_path="b.mp4")]
    assert estimate_eta(jobs, remaining=1, in_flight_elapsed=3.0) is None
