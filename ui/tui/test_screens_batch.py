import re
from dataclasses import replace

import reporter as R
from ui.config import EncodeConfig
from ui.theme import get_console
from ui.tui import forms as F
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of
from ui.tui.test_screens_config import folder_state


def batch_cfg(**kw):
    return {**vars(EncodeConfig.preset_batch("C:/v/lote").to_namespace()), **kw}


def queue_state(n=3, active=1):
    jobs = tuple((f"C:/v/lote/clip_{i:02d}.mov", f"C:/v/lote/clip_{i:02d}_Hollywood_CRF18.mp4") for i in range(n))
    s = S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3, now=100.0, source_count=n)
    t = 100.0
    evs = [R.QueueInit(jobs, ts=t)]
    for i in range(active):
        evs += [R.JobStart(i, job_id=i, ts=t), R.JobDone(i, "ok", None, job_id=i, ts=t + 60)]
        t += 60
    evs += [R.JobStart(active, job_id=active, ts=t), R.Stage(R.PASS, "1", job_id=active, ts=t + 1),
            R.Pass(1, 1, "Encode", "start", job_id=active, ts=t + 1),
            R.Progress(300, 900, 30.0, 1.2, "00:00:20", 10.0, job_id=active, ts=t + 11),
            R.FfmpegLine("frame=  300 fps= 30", job_id=active, ts=t + 11)]
    for ev in evs:
        s = S.apply(s, ev)
    return replace(s, now=t + 20)


def report_state(cancel=False):
    jobs = tuple((f"C:/v/lote/clip_{i}.mov", f"C:/v/lote/clip_{i}_Hollywood_CRF18.mp4") for i in range(4))
    msg = "Command '[ffmpeg]' returned non-zero exit status 1."
    evs = [R.QueueInit(jobs, ts=100.0), R.JobStart(0, ts=100.0), R.JobDone(0, "ok", None, ts=160.0),
           R.JobSkip(1, "output existe"), R.JobStart(2, ts=160.0),
           R.Error("CalledProcessError", msg, None, 1, "tb", job_id=2, ts=200.0),
           R.JobDone(2, "falha", msg + "\nTraceback (most recent call last)", ts=200.0), R.JobStart(3, ts=200.0)]
    if cancel:
        evs += [R.Cancel("requested", ts=210.0), R.JobDone(3, "falha", "cancelado pelo usuário", ts=211.0),
                R.Info("NÃO foi possível remover clip_3_Hollywood_CRF18.mp4", job_id=3, ts=212.0),
                R.QueueDone(130, ts=212.0)]
    else:
        evs += [R.JobDone(3, "ok", None, ts=260.0), R.QueueDone(1, ts=260.0)]
    s = S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3, now=100.0)
    for ev in evs:
        s = S.apply(s, ev)
    return s


def test_queue_screen_three_jobs():
    out = text_of(queue_state())
    for txt in ("BATCH", "C:/v/lote", "3 arquivos", "saída: mesma pasta", "RENDER QUEUE", "Job 2 de 3",
                "ETA 01:40", "JOB", "ARQUIVO", "STATUS", "ETA/DURAÇÃO", "RESULTADO", "clip_00.mov",
                "✓ COMPLETED", "01:00", "ENCODING", "· QUEUED", "…", "PASS 1 / 1", "frame=  300", "LOG",
                "QUEUE · JOB 2/3", "[C] Cancelar fila", "[D] Details"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_queue_screen_twenty_jobs_scrolls_to_active():
    out = text_of(queue_state(n=20, active=15))
    assert "clip_15.mov" in out and "clip_19.mov" in out and "clip_00.mov" not in out
    assert "Job 16 de 20" in out and "ETA 04:40" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_queue_eta_dash_before_first_done():
    out = text_of(queue_state(active=0))
    assert "ETA —" in out and "Job 1 de 3" in out


def test_queue_cancel_modal_and_blocked_footer():
    out = text_of(S.apply(queue_state(), S.Key("C")))
    assert "CANCELAR FILA?" in out and "CONTINUAR FILA" in out and "CANCELAR FILA ]" in out
    assert "RENDER QUEUE" in out
    assert_fits(out)
    blocked = S.apply(queue_state(), R.Stage(R.ANALYZING, "mctf_mask", ts=500.0))
    assert "░[C] Cancelar fila" in text_of(blocked)


def test_batch_rail_on_queue_and_folder_source():
    rail = text_of(queue_state()).splitlines()[1]
    assert "QUEUE" in rail and "REPORT" in rail and "DELIVERY" not in rail and "✓ READY" in rail
    rail = text_of(folder_state()).splitlines()[1]
    assert "REPORT" in rail and "DELIVERY" not in rail
    rail = text_of(S.UIState(config={}, screen=S.SOURCE, preset=1)).splitlines()[1]
    assert "DELIVERY" in rail and "REPORT" not in rail


def test_report_with_failure():
    out = text_of(report_state())
    for txt in ("✗ FILA CONCLUÍDA COM FALHAS", "Sucesso 2/4", "Pulados 1", "Falhas 1", "Interrompidos 0",
                "Tempo total 00:02:40", "Código de saída 1", "saída já existe", "Command '[ffmpeg]' returned",
                "✓ COMPLETED", "○ SKIPPED", "✗ FAILED", "SAIR", "[ENTER] Sair"):
        assert txt in out, txt
    assert "Traceback" not in out and "NÃO foi possível remover" not in out
    assert_fits(out)
    assert_no_emoji(out)


def test_report_with_interrupted():
    out = text_of(report_state(cancel=True))
    for txt in ("⚠ FILA INTERROMPIDA", "Sucesso 1/4", "Interrompidos 1", "Código de saída 130",
                "⚠ CANCELLED", "interrompido"):
        assert txt in out, txt
    assert "⚡" not in out
    assert_fits(out)
    assert_no_emoji(out)


def test_report_warns_unremovable_partial():
    out = text_of(report_state(cancel=True))
    assert "NÃO foi possível remover clip_3_Hollywood_CRF18.mp4" in out and "rodar a fila de novo" in out


def test_report_scrolls_long_queue():
    jobs = tuple((f"C:/v/lote/clip_{i:02d}.mov", f"C:/v/lote/clip_{i:02d}_o.mp4") for i in range(30))
    s = S.apply(S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3), R.QueueInit(jobs))
    s = S.apply(s, R.QueueDone(0))
    out = text_of(s)
    assert "clip_00.mov" in out and "clip_20.mov" in out and "clip_21.mov" not in out
    for _ in range(5):
        s = S.apply(s, S.Key("DOWN"))
    out = text_of(s)
    assert "clip_05.mov" in out and "clip_25.mov" in out and "clip_04.mov" not in out
    assert_fits(out)


def test_long_and_bracketed_names_fit():
    folder = "C:/v/[lote] " + "p" * 200
    name = "clip [b] " + "n" * 150
    jobs = ((f"{folder}/{name}.mov", f"{folder}/{name}_Hollywood_CRF18.mp4"),
            (f"{folder}/clip [b].mov", f"{folder}/clip [b]_o.mp4"))
    cfg = batch_cfg(batch=folder, output_dir="D:/" + "o" * 200)
    s = S.UIState(config=cfg, screen=S.QUEUE, is_batch=True, preset=3, now=100.0)
    s = S.apply(S.apply(s, R.QueueInit(jobs, ts=100.0)), R.JobStart(0, ts=100.0))
    out = text_of(s)
    assert "erro ao desenhar" not in out and "nnnn" in out and "clip [b].mov" in out
    assert_fits(out)
    s = S.apply(S.apply(s, R.JobDone(0, "falha", "[x] " + "e" * 300, ts=150.0)), R.QueueDone(1, ts=150.0))
    out = text_of(s)
    assert "erro ao desenhar" not in out and "[x] eee" in out
    assert_fits(out)
    ready = S.UIState(config=cfg, screen=S.READY, is_batch=True, preset=3, source_count=1)
    assert_fits(text_of(ready))


def test_queue_summary_lines():
    assert V.queue_summary(report_state(), 1).plain == "✗ fila: 2 ok · 1 pulado · 1 falha (código 1)"
    assert V.queue_summary(report_state(cancel=True), 130).plain == \
        "⚠ fila interrompida: 1 ok · 1 pulado · 1 falha · 1 interrompido (código 130)"
    ok = S.UIState(config={}, queue=(S.Job("a", "b", "ok"), S.Job("c", "d", "ok")))
    assert V.queue_summary(ok, 0).plain == "✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)"


def test_queue_one_job_pluralizes():
    out = text_of(queue_state(n=1, active=0))
    assert "1 arquivo" in out and "1 arquivos" not in out
    done = S.apply(queue_state(n=1, active=0), R.QueueDone(0, ts=130.0))
    out = text_of(done)
    assert "FILA · 1 arquivo" in out and "1 arquivos" not in out


def _labels_intact(out, labels):
    lines = out.splitlines()
    for lbl in labels:
        assert any(lbl in ln.split()[:2] for ln in lines), lbl
    assert not re.search(r"\s[A-ZÁÍ]{1,3}…\s", out)


def test_long_names_keep_labels_in_ready_and_configuration():
    folder = "C:/v/" + "lote_muito_longo_" * 6
    outdir = "D:/" + "saida_longa_" * 8
    ready = S.UIState(config=batch_cfg(batch=folder, output_dir=outdir), screen=S.READY, is_batch=True, preset=3,
                      source_count=12)
    out = text_of(ready)
    _labels_intact(out, ("SOURCE", "OUTPUT", "PIPELINE", "MODO", "FPS", "COR", "ÁUDIO", "ENHANCE", "PERF"))
    assert "12 vídeos" in out and "saída: …" in out
    assert_fits(out)
    d = {**F.new_draft(3), "batch": folder, F.OUTDIR_ON: "on", "output_dir": outdir}
    out = text_of(S.UIState(config={}, screen=S.CONFIGURATION, preset=3, drafts=((3, d),), source_count=12))
    _labels_intact(out, ("PIPELINE", "PASTA"))
    assert "12 vídeos" in out and "saída: …" in out
    assert_fits(out)


def test_preview_batch_ebu_meter_chip_off():
    chips = dict(V.preview_chips({**F.new_draft(3), "ebu_meter": "on"}))
    assert chips["EBU Meter"] is False
    assert dict(V.preview_chips({**F.new_draft(1), "ebu_meter": "on"}))["EBU Meter"] is True
    s = S.UIState(config={}, screen=S.PREVIEW, preset=3, source_count=2,
                  drafts=((3, {**F.new_draft(3), "batch": "C:/v/lote", "ebu_meter": "on"}),))
    out = text_of(s)
    assert "EBU Meter" in out and "✓ EBU Meter" not in out


def _footer(out):
    return "\n".join(out.splitlines()[-2:])


def test_batch_footers_say_queue():
    ready = S.UIState(config=batch_cfg(), screen=S.READY, is_batch=True, preset=3, source_count=3)
    foot = _footer(text_of(ready))
    assert "[ENTER] Start queue" in foot and "Start encode" not in foot
    foot = _footer(text_of(S.apply(queue_state(), S.Key("C"))))
    assert "[ESC] Keep queue" in foot and "Keep encoding" not in foot


def _has_reverse(state):
    con = get_console(record=True, width=120, height=40, force_terminal=True, color_system="truecolor")
    return any(seg.style is not None and seg.style.reverse for seg in con.render(V.render(state)))


def test_source_path_cursor_hidden_while_tipo_focused():
    s = folder_state(preset=5)
    assert _has_reverse(s)
    assert not _has_reverse(replace(s, tab_focus=True))


def test_report_empty_queue_explains():
    empty = S.apply(S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3), R.QueueDone(0))
    assert empty.screen == S.REPORT and "nenhum vídeo encontrado na pasta" in text_of(empty)
    assert "nenhum vídeo encontrado na pasta" not in text_of(report_state())
    stopped = S.apply(S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3), S.Finished(130))
    assert stopped.screen == S.REPORT and "nenhum vídeo encontrado na pasta" not in text_of(stopped)


def test_queue_start_window_edges():
    assert V.queue_start(5, 4, 8) == 0
    assert V.queue_start(20, 0, 8) == 0
    assert V.queue_start(20, 19, 8) == 12
    assert V.queue_start(20, 10, 8) == 6
    assert V.queue_start(20, None, 8) == 0
    assert V.queue_start(20, 10, 8, scroll=-3) == 0
    assert V.queue_start(20, 10, 8, scroll=99) == 12
    assert V.queue_start(20, 10, 8, scroll=5) == 5
