import io
import time

import pytest
from rich.console import Console

from render_queue import (
    QueueJob,
    build_table,
    discard_partial_output,
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
    console = Console(file=output, width=120, force_terminal=False)
    console.print(table)
    text = output.getvalue()

    for job in jobs:
        assert job.input_path in text
    for symbol in ["·", "⏳", "✓", "✗", "○"]:
        assert symbol in text


def test_run_job_marks_success_and_keeps_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    output = io.StringIO()
    console = Console(file=output, width=120, force_terminal=False)

    def encode_fn():
        console.print("trabalhando...")

    run_job(job, encode_fn, console)

    assert job.status == "ok"
    assert job.error is None
    assert "trabalhando..." in job.log


def test_run_job_marks_failure_and_captures_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO(), force_terminal=False)

    def encode_fn():
        console.print("preparando encode...")
        raise RuntimeError("ffmpeg explodiu")

    run_job(job, encode_fn, console)

    assert job.status == "falha"
    assert job.error == "ffmpeg explodiu"
    assert "preparando encode..." in job.log


def test_render_final_report_lists_failure_with_captured_log():
    output = io.StringIO()
    console = Console(file=output, width=100, force_terminal=False)

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
    console = Console(file=output, width=200, force_terminal=False)

    failed_job = _finished_job(1.0, input_path="falhou.mp4", status="falha")
    failed_job.error = "erro"
    failed_job.log = "HEAD-MARKER" + ("y" * 4990) + "TAIL-MARKER"

    render_final_report([failed_job], console)

    text = output.getvalue()
    assert "TAIL-MARKER" in text
    assert "HEAD-MARKER" not in text


def test_run_job_calls_on_tick_while_encode_runs():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO(), force_terminal=False)
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
    console = Console(file=output, width=120, force_terminal=False)
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


def test_discard_partial_output_removes_existing_file(tmp_path):
    partial = tmp_path / "clip_Hollywood_CRF18.mp4"
    partial.write_bytes(b"\x00" * 128)
    job = QueueJob(input_path="clip.mp4", output_path=str(partial))

    assert discard_partial_output(job) is True
    assert not partial.exists()


def test_discard_partial_output_returns_false_when_absent(tmp_path):
    job = QueueJob(
        input_path="clip.mp4",
        output_path=str(tmp_path / "nao_existe.mp4"),
    )
    assert discard_partial_output(job) is False


def test_discard_partial_output_retries_until_handle_is_released():
    # Simula o ffmpeg do Windows soltando o arquivo so na terceira tentativa.
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    calls = {"remove": 0, "sleep": 0}

    def fake_remove(path):
        calls["remove"] += 1
        if calls["remove"] < 3:
            raise OSError(13, "Permission denied")

    def fake_sleep(seconds):
        calls["sleep"] += 1

    ok = discard_partial_output(
        job,
        remove=fake_remove,
        exists=lambda path: True,
        sleep=fake_sleep,
        attempts=3,
        delay=0.0,
    )

    assert ok is True
    assert calls["remove"] == 3
    assert calls["sleep"] == 2


def test_discard_partial_output_gives_up_after_attempts():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    calls = {"remove": 0}

    def always_locked(path):
        calls["remove"] += 1
        raise OSError(13, "Permission denied")

    ok = discard_partial_output(
        job,
        remove=always_locked,
        exists=lambda path: True,
        sleep=lambda seconds: None,
        attempts=3,
        delay=0.0,
    )

    assert ok is False
    assert calls["remove"] == 3


def test_discard_partial_output_does_not_sleep_when_first_try_wins():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    slept = []

    ok = discard_partial_output(
        job,
        remove=lambda path: None,
        exists=lambda path: True,
        sleep=lambda seconds: slept.append(seconds),
        delay=0.0,
    )

    assert ok is True
    assert slept == []


def test_run_job_marks_interrupted_and_reraises():
    # O KeyboardInterrupt precisa vir do on_tick: ele roda na main thread dentro
    # do laco do run_job. Levantado de dentro do encode_fn morreria no worker.
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO(), width=120, force_terminal=False)

    def encode_fn():
        time.sleep(1.0)

    def on_tick():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_job(job, encode_fn, console, on_tick=on_tick, tick_interval=0.01)

    assert job.status == "interrompido"
    assert job.finished_at is not None


def test_build_table_renders_interrupted_symbol():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    job.status = "interrompido"
    job.started_at = 100.0
    job.finished_at = 105.0

    output = io.StringIO()
    console = Console(file=output, width=120, force_terminal=False)
    console.print(build_table([job]))
    text = output.getvalue()

    assert "⚡" in text


def test_render_final_report_counts_interrupted():
    done = _finished_job(10.0)
    stopped = QueueJob(input_path="b.mp4", output_path="b_out.mp4")
    stopped.status = "interrompido"
    stopped.started_at = 100.0
    stopped.finished_at = 104.0

    output = io.StringIO()
    console = Console(file=output, width=120, force_terminal=False)
    render_final_report([done, stopped], console)
    text = output.getvalue()

    assert "Interrompidos: 1/2" in text
