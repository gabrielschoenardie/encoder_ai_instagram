import reporter as R
from ui.tui import state as S

JOBS = tuple((f"C:/v/lote/{n}.mov", f"C:/v/lote/{n}_Hollywood_CRF18.mp4") for n in ("a", "b", "c"))
CFG = {"batch": "C:/v/lote", "input": None, "output_dir": None, "mode": "crf", "cineon_pipeline": "off"}


def run(s, *evs):
    for ev in evs:
        s = S.apply(s, ev)
    return s


def tick(s, t):
    return S.apply(s, S.Tick(t, (120, 40)))


def armed():
    s = S.UIState(config={}, screen=S.PREVIEW, preset=3)
    return S.apply(s, S.Armed(dict(CFG), "", False))


def in_queue(now=10.0):
    s = S.apply(tick(armed(), now), S.Key("ENTER"))
    return S.apply(s, R.QueueInit(JOBS))


def test_armed_batch_and_ready_enter_opens_queue():
    s = armed()
    assert s.screen == S.READY and s.is_batch and s.output_path == ""
    s = S.apply(s, S.Key("ENTER"))
    assert s.screen == S.QUEUE and s.action == "start"
    assert S.apply(armed(), S.Key("ESC")).screen == S.PREVIEW
    single = S.apply(S.UIState(config={}, screen=S.PREVIEW, preset=1), S.Armed({"input": "a.mov"}, "o.mp4", False))
    assert not single.is_batch and S.apply(single, S.Key("ENTER")).screen == S.ENCODING


def test_queue_init_builds_waiting_table():
    s = in_queue(now=10.0)
    assert s.screen == S.QUEUE and len(s.queue) == 3 and s.is_batch
    assert all(j.status == "aguardando" and j.reason is None for j in s.queue)
    assert (s.queue[0].input, s.queue[0].output) == JOBS[0]
    assert s.queue_started == 10.0 and s.active_job is None


def test_events_without_timestamp_use_tick_clock():
    s = S.apply(in_queue(now=50.0), R.JobStart(0))
    s = S.apply(tick(s, 80.0), R.JobDone(0, "ok", None))
    job = s.queue[0]
    assert (job.started, job.finished, job.status, job.reason) == (50.0, 80.0, "ok", "ok")
    s = S.apply(tick(s, 95.0), R.QueueDone(0))
    assert s.queue_finished == 95.0 and s.queue_finished - s.queue_started == 45.0


def test_job_start_resets_active_job_panel():
    s = run(in_queue(), R.JobStart(0, job_id=0, ts=10.0), R.Stage(R.PASS, "1", job_id=0, ts=11.0),
            R.Pass(1, 1, "Encode", "start", job_id=0, ts=11.0),
            R.Progress(10, 100, 30.0, 1.0, "00:00:03", 1.0, job_id=0, ts=12.0),
            R.Info("Aviso: ffprobe falhou", job_id=0, ts=12.0), R.Qc({"checks": []}, job_id=0, ts=13.0),
            R.JobDone(0, "ok", None, job_id=0, ts=20.0), R.JobStart(1, job_id=1, ts=20.0))
    assert s.active_job == 1 and s.queue[1].status == "processando" and s.queue[0].status == "ok"
    assert s.stage is None and s.passes == () and s.progress is None and s.log == ()
    assert s.qc is None and s.error is None and s.warnings == 0 and s.job_started is None
    assert s.output_path == JOBS[1][1] and s.screen == S.QUEUE


def test_skip_and_failure_reasons_do_not_go_to_error():
    s = run(in_queue(), R.JobSkip(0, "output existe", job_id=0),
            R.JobStart(1, job_id=1, ts=10.0),
            R.Error("CalledProcessError", "ffmpeg saiu com 1\nstderr...", "tail", 1, "tb", job_id=1, ts=15.0),
            R.JobDone(1, "falha", "ffmpeg saiu com 1\nstderr...", job_id=1, ts=15.0))
    assert (s.queue[0].status, s.queue[0].reason) == ("pulado", "saída já existe")
    assert (s.queue[1].status, s.queue[1].reason) == ("falha", "ffmpeg saiu com 1")
    assert s.screen == S.QUEUE and s.error is None
    assert any("ffmpeg saiu com 1" in r.text for r in s.log)


def test_error_before_queue_goes_to_error_screen():
    s = run(S.apply(armed(), S.Key("ENTER")),
            R.Error("validation", "--output-dir só se aplica a --batch", None, None, None), S.Finished(2))
    assert s.screen == S.ERROR and s.error.kind == "validation" and s.exit_code == 2
    s = run(S.apply(armed(), S.Key("ENTER")),
            R.Error("batch_folder", "Pasta não encontrada: C:/v/lote", None, None, None), S.Finished(1))
    assert s.screen == S.ERROR and s.exit_code == 1


def test_queue_done_goes_to_report_and_finished_is_idempotent():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.JobDone(0, "ok", None, ts=70.0), R.JobSkip(1, "output existe"),
            R.JobStart(2, ts=70.0), R.JobDone(2, "falha", "boom", ts=80.0), R.QueueDone(1, ts=80.0))
    assert s.screen == S.REPORT and s.exit_code == 1 and s.queue_finished == 80.0
    assert S.apply(s, S.Finished(1)) == s
    c = S.queue_counts(s.queue)
    assert (c["ok"], c["pulado"], c["falha"], c["interrompido"], c["total"]) == (1, 1, 1, 0, 3)


def test_empty_queue_done_zero_goes_to_report():
    s = run(S.apply(armed(), S.Key("ENTER")), R.Info("Nenhum vídeo encontrado em: C:/v/lote"), R.QueueDone(0),
            S.Finished(0))
    assert s.screen == S.REPORT and s.queue == () and s.exit_code == 0


def test_cancel_marks_active_job_interrupted_and_keeps_waiting_jobs():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Cancel("requested", ts=12.0),
            R.JobDone(0, "falha", "cancelado pelo usuário", ts=13.0), R.Cancel("terminated", ts=13.0),
            R.Cancel("cleaned", True, ts=14.0), R.QueueDone(130, ts=14.0))
    assert s.screen == S.REPORT and s.exit_code == 130 and s.modal is None
    assert (s.queue[0].status, s.queue[0].reason) == ("interrompido", "interrompido")
    assert [j.status for j in s.queue[1:]] == ["aguardando", "aguardando"]


def test_ctrl_c_without_job_done_marks_active_interrupted():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Cancel("requested", ts=12.0), R.QueueDone(130, ts=14.0))
    assert s.queue[0].status == "interrompido" and s.queue[0].finished == 14.0
    s = run(in_queue(), R.JobStart(0, ts=10.0), S.Finished(130))
    assert s.screen == S.REPORT and s.queue[0].status == "interrompido" and s.exit_code == 130


def test_queue_keys_overlays_and_cancel_modal():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Stage(R.PASS, "1", ts=11.0))
    d = S.apply(s, S.Key("D"))
    assert d.screen == S.DETAILS and d.back == S.QUEUE
    assert S.apply(d, S.Key("ESC")).screen == S.QUEUE
    assert S.apply(s, S.Key("L")).screen == S.LOG
    m = S.apply(s, S.Key("C"))
    assert m.modal == "CANCEL"
    m = S.apply(S.apply(m, S.Key("RIGHT")), S.Key("ENTER"))
    assert m.action == "cancel" and m.modal is None
    blocked = S.apply(s, R.Stage(R.ANALYZING, "mctf_mask", ts=12.0))
    assert S.apply(blocked, S.Key("C")).modal is None


def test_qc_stage_in_batch_never_opens_qc_screen():
    s = run(in_queue(), R.JobStart(0, ts=10.0))
    assert S.apply(s, R.Stage(R.QC, ts=11.0)).screen == S.QUEUE
    d = run(S.apply(s, S.Key("D")), R.Stage(R.QC, ts=11.0))
    assert d.screen == S.DETAILS and d.back == S.QUEUE
    d = run(d, R.JobDone(0, "ok", None, ts=20.0), R.QueueDone(0, ts=30.0))
    assert d.screen == S.REPORT


def test_report_keys_scroll_and_exit():
    jobs = tuple((f"C:/v/{i}.mov", f"C:/v/{i}_o.mp4") for i in range(30))
    s = run(S.apply(armed(), S.Key("ENTER")), R.QueueInit(jobs), R.QueueDone(0))
    assert S.apply(s, S.Key("UP")).queue_scroll == 0
    for _ in range(20):
        s = S.apply(s, S.Key("DOWN"))
    assert s.queue_scroll == 30 - S.REPORT_ROWS
    assert S.apply(s, S.Key("ENTER")).action == "exit"
    assert S.apply(s, S.Key("ESC")).action == "exit"


def test_queue_eta_mean_times_remaining_plus_in_flight():
    assert S.queue_eta(run(in_queue(), R.JobStart(0, ts=10.0))) is None
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.JobDone(0, "ok", None, ts=70.0), R.JobStart(1, ts=70.0))
    assert S.queue_eta(tick(s, 90.0)) == 100.0


def test_finished_error_with_queue_fails_active_job():
    err = R.Error("OSError", "sem permissão\ndetalhe", None, None, "tb", ts=12.0)
    s = run(in_queue(), R.JobStart(0, ts=10.0), err, S.Finished(1))
    assert s.screen == S.REPORT and s.exit_code == 1
    assert (s.queue[0].status, s.queue[0].reason) == ("falha", "OSError: sem permissão")
    assert [j.status for j in s.queue[1:]] == ["aguardando", "aguardando"]
    s = run(in_queue(), R.JobStart(0, ts=10.0), S.Finished(1))
    assert (s.queue[0].status, s.queue[0].reason) == ("falha", "erro")
    s = run(in_queue(), R.JobStart(0, ts=10.0), S.Finished(0))
    assert s.queue[0].status == "processando"


def test_cancel_unavailable_logs_warning_and_closes_modal():
    s = S.apply(run(in_queue(), R.JobStart(0, ts=10.0)), S.Key("C"))
    assert s.modal == "CANCEL"
    s = S.cancel_unavailable(s)
    assert s.modal is None and s.warnings == 1
    assert s.log[-1] == S.LogRow("WARNING", "cancelamento indisponível neste estágio — tente de novo em instantes")


def test_queue_eta_active_job_past_mean_adds_nothing():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.JobDone(0, "ok", None, ts=70.0), R.JobStart(1, ts=70.0))
    assert S.queue_eta(tick(s, 200.0)) == 60.0


def test_d_and_l_from_queue_open_overlays_and_return():
    s = run(in_queue(), R.JobStart(0, ts=10.0))
    assert s.screen == S.QUEUE
    d = S.apply(s, S.Key("D"))
    assert d.screen == S.DETAILS and d.back == S.QUEUE
    assert S.apply(d, S.Key("D")).screen == S.QUEUE
    lg = S.apply(s, S.Key("L"))
    assert lg.screen == S.LOG and lg.back == S.QUEUE
    assert S.apply(lg, S.Key("ESC")).screen == S.QUEUE
    assert S.apply(S.apply(s, S.Key("D")), S.Key("L")).screen == S.LOG
