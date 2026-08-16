import io

import pytest
from render_queue import (
    QueueJob,
    build_table,
    estimate_eta,
    format_duration,
    format_eta,
    render_final_report,
    run_job,
)
from rich.console import Console


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


def test_run_job_marks_success_and_leaves_log_empty():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())

    def encode_fn():
        console.print("trabalhando...")

    run_job(job, encode_fn, console)

    assert job.status == "ok"
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.finished_at >= job.started_at
    assert job.log == ""
    assert job.error is None


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
