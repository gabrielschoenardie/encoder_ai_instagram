from dataclasses import replace

import pytest
from rich.cells import cell_len
from rich.segment import Segment

import reporter as R
from ui.theme import get_console
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import CFG, encoding_state, text_of
from ui.tui.test_screens_batch import batch_cfg, queue_state, report_state
from ui.tui.test_screens_config import cfg_state, folder_state, home

SIZES = [(w, h) for w in (80, 100, 119) for h in (24, 30, 39)] + [(130, 30), (80, 45)]
LONG = "C:/Users/editor/Videos/projetos/cliente_muito_importante/2026/novembro/" + "a" * 120 + "/clip.mov"
CHECKS = [{"label": n, "value": v, "passed": p} for n, v, p in (
    ("Container", "mp4", True), ("Video", "h264", True), ("Resolution", "1080x1920", True),
    ("Bit Depth", "8-bit", True), ("Color", "bt709", True), ("FPS", "30", True),
    ("Loudness", "-14.0 LUFS", True), ("True Peak", "-1.6 dBTP", True), ("Codec", "aac", None),
    ("Sample Rate", "48000", False))]
PAYLOAD = {
    "checks": CHECKS,
    "summary": {"passed": 8, "warnings": 1, "failed": 1, "ready": True},
    "audio": {"before": {"I": -20.1, "TP": -3.0, "LRA": 7.0}, "after": {"I": -14.0, "TP": -1.6, "LRA": 6.0}},
    "targets": {"I": -14.0, "TP": -1.5, "LRA": None},
    "output": {"size_human": "38.2 MB"}, "encode": {"duration_human": "00:03:17"},
    "video": {"codec": "h264", "width": 1080, "height": 1920, "fps": 30.0},
}


def busy(s, n=60):
    for i in range(n):
        s = S.apply(s, R.FfmpegLine(f"frame= {i:4d} fps= 28 q=24.0 linha {i}", ts=199.0))
    return s


def qc(reveal):
    s = busy(encoding_state())
    s = S.apply(s, R.Stage(R.QC, ts=300.0))
    s = S.apply(s, R.Qc(PAYLOAD, ts=301.0))
    s = S.apply(s, S.Tick(301.0, (120, 40)))
    if reveal:
        s = S.apply(s, S.Tick(301.0 + S.SEAL_REVEAL_S, (120, 40)))
    return s


def completed():
    s = S.apply(S.apply(qc(True), S.Finished(0)), S.Tick(400.0, (120, 40)))
    return replace(s, preset=1)


def error_state():
    tb = "".join(f"  File \"x{i}.py\", line {i}, in f{i}\n" for i in range(60)) + "ULTIMA LINHA DO STDERR\n"
    msg = "Command '['ffmpeg', '-y', '-i', 'C:/v/clip_final.mov', " + "'-x264-params', 'a=b:c=d', " * 30
    s = S.apply(busy(encoding_state()), R.Error("CalledProcessError", msg, tb.encode(), 1, None, ts=250.0))
    return replace(S.apply(s, S.Finished(1)), preset=1)


def cancelled_state():
    s = S.apply(busy(encoding_state()), R.Cancel("requested", ts=250.0))
    s = replace(s, output_preexisted=True, output_path="C:/v/" + "nome_bem_comprido_" * 4 + ".mp4", preset=1)
    return S.apply(S.apply(s, R.Cancel("terminated", ts=251.0)), S.Finished(130))


def report_long():
    jobs = tuple((f"C:/v/lote/clip_com_nome_comprido_{i:02d}.mov", f"C:/v/lote/out_{i:02d}.mp4") for i in range(14))
    s = S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3, now=100.0)
    evs = [R.QueueInit(jobs, ts=100.0)]
    for i in range(14):
        evs += [R.JobStart(i, ts=100.0 + i), R.JobDone(i, "ok" if i % 3 else "falha", "erro longo " * 20, ts=101.0 + i)]
    evs += [R.Info("NÃO foi possível remover out_13.mp4", ts=120.0), R.QueueDone(1, ts=120.0)]
    for ev in evs:
        s = S.apply(s, ev)
    return replace(s, removal_failed=True)


def adv_state(tab):
    s = cfg_state(5, screen=S.ADVANCED, tab=tab, field_error="Máximo é 2." if tab == 1 else None)
    d = {**S.draft(s), "source_kind": "folder", "output_dir_on": "on", "output_dir": LONG, "batch": LONG,
         "cineon_pipeline": "on", "enhance_ai": "on"}
    return replace(s, drafts=((5, d),))


def batch_form(screen, **kw):
    s = folder_state(path=LONG, count=12)
    d = {**S.draft(s), "output_dir_on": "on", "output_dir": LONG, "batch": LONG}
    return replace(s, screen=screen, drafts=((3, d),), **kw)


STATES = {
    "home": lambda: home(home_focus=4),
    "source_file": lambda: replace(cfg_state(1, screen=S.SOURCE), source=W.TextBuf(LONG, len(LONG)),
                                   source_status="VALID", source_dims=(1080, 1920)),
    "source_p5_tipo": lambda: replace(cfg_state(5, screen=S.SOURCE), source=W.TextBuf(LONG, 3), tab_focus=True),
    "source_p5_path": lambda: replace(cfg_state(5, screen=S.SOURCE), source=W.TextBuf(LONG, 3)),
    "source_folder": lambda: folder_state(path=LONG, count=12),
    "config_quick": lambda: cfg_state(1, focus=((S.CONFIGURATION, 2),), field_error="Mínimo é 1."),
    "config_cineon": lambda: cfg_state(2, field_error="Máximo é 2."),
    "config_batch": lambda: batch_form(S.CONFIGURATION, focus=((S.CONFIGURATION, 1),),
                                       field_error="Informe a pasta de saída."),
    **{f"advanced_{i}": (lambda i=i: adv_state(i)) for i in range(5)},
    "advanced_tabfocus": lambda: replace(adv_state(0), tab_focus=True),
    "preview_file": lambda: cfg_state(1, screen=S.PREVIEW, field_error="Informe a pasta de saída."),
    "preview_folder": lambda: batch_form(S.PREVIEW),
    "ready": lambda: S.UIState(config={**CFG, "mode": "2pass", "cineon_pipeline": "on", "input": LONG},
                               output_path="C:/v/" + "x" * 90 + ".mp4", preset=1, ready_error="pasta sem permissão"),
    "ready_batch": lambda: S.UIState(config=batch_cfg(batch=LONG, output_dir=LONG), screen=S.READY, is_batch=True,
                                     preset=3, source_count=12, ready_error="erro"),
    "encoding": lambda: busy(encoding_state()),
    "encoding_cancel": lambda: S.apply(busy(encoding_state()), R.Cancel("requested", ts=250.0)),
    "details": lambda: S.apply(busy(encoding_state()), S.Key("D")),
    "log": lambda: S.apply(busy(encoding_state()), S.Key("L")),
    "qc_before": lambda: qc(False),
    "qc_after": lambda: qc(True),
    "completed": completed,
    "error": error_state,
    "cancelled": cancelled_state,
    "queue": lambda: busy(queue_state(n=14, active=8)),
    "report": report_long,
    "report_cancel": lambda: report_state(cancel=True),
    "overlay_log_final": lambda: S.apply(S.apply(S.apply(completed(), S.Key("RIGHT")), S.Key("RIGHT")),
                                         S.Key("ENTER")),
    "overlay_qc_final": lambda: S.apply(S.apply(completed(), S.Key("RIGHT")), S.Key("ENTER")),
}


def natural(renderable, width):
    con = get_console(width=width, height=24, force_terminal=True, color_system="truecolor")
    lines = con.render_lines(renderable, con.options.update(width=width, height=None), pad=False)
    return lines, [Segment.get_line_length(ln) for ln in lines]


@pytest.mark.parametrize("name", sorted(STATES))
@pytest.mark.parametrize("size", SIZES, ids=lambda z: f"{z[0]}x{z[1]}")
def test_compact_body_and_footer_fit(name, size):
    s = replace(STATES[name](), size=size)
    assert S.compact(s) and not S.too_small(s)
    w, h = size
    head, head_w = natural(V.header(s), w)
    foot, foot_w = natural(V.footer(s), w)
    body, body_w = natural(V.SCREEN_RENDERERS[s.screen](s), w)
    assert len(head) == 1 and len(foot) == 1
    assert len(body) <= h - 2, f"corpo {len(body)} > {h - 2}"
    assert max(head_w + foot_w + body_w) <= w
    assert "…" not in "".join(seg.text for seg in foot[0])


def plain(name, size=(80, 24)):
    return text_of(replace(STATES[name](), size=size), width=size[0], height=size[1])


CONTENT = {
    "home": ("Encode rápido", "Film look", "Batch de pasta", "Tools", "Configurar avançado", "▸ 5", "O QUE FAZ",
             "5 abas", "ffprobe.exe", "[ESC] Sair"),
    "source_file": ("ARQUIVO", "STATUS", "arquivo encontrado", "1080 × 1920", "SAÍDA", "clip.mov", "ENTER →"),
    "source_p5_tipo": ("TIPO", "▸ ● Arquivo único", "Pasta (batch)", "[←→] Tipo"),
    "source_folder": ("PASTA", "pasta encontrada · 12 vídeos", "VÍDEOS", "SAÍDA"),
    "config_quick": ("Enquadramento", "FPS", "▸  Modo", "CONTINUAR", "Mínimo é 1.", "PADRÕES", "performance",
                     "[^C] Sair"),
    "config_cineon": ("Exposure offset", "Saturação", "Enquadramento", "CONTINUAR", "Máximo é 2."),
    "config_batch": ("Definir pasta de saída separada", "Pasta de saída", "Usar film look", "CONTINUAR",
                     "Informe a pasta de saída.", "[digite] Pasta", "[^C] Sair"),
    "advanced_0": ("Source", "Export", "Pasta de saída separada", "Performance", "CONTINUAR", "SETTINGS"),
    "advanced_1": ("Exposure offset", "Saturação", "Tonemap", "Máximo é 2.", "CONTINUAR"),
    "advanced_3": ("Enhancement engine", "MCTF", "Dither", "CONTINUAR"),
    "advanced_4": ("Exibir perfil de hardware", "Threads", "CONTINUAR", "[^C] Sair"),
    "preview_file": ("PREVIEW", "Pipeline", "Performance", "LUT", "Loudnorm", "EBU Meter", "CONTINUAR ▸ READY",
                     "REVISAR", "Informe a pasta de saída."),
    "ready": ("SOURCE", "OUTPUT", "2 passes", "PERF", "PREPARING", "COMPLETED", "certificado", "pasta sem permissão",
              "START ENCODE", "[ESC] Voltar"),
    "ready_batch": ("START QUEUE", "suprimido em batch", "Start queue", "erro"),
    "encoding": ("PASS 1 / 2", "PASS 2 / 2", "ETA 00:00:41", "TIMELINE", "PERFORMANCE", "linha 59", "[^C] Interrupt"),
    "encoding_cancel": ("CANCELAMENTO SOLICITADO", "PASS 2 / 2", "linha 59"),
    "details": ("SOURCE", "HARDWARE", "ENCODING", "CONFIG", "OUTPUT", "PROGRESS", "11475", "bufsize", "ebu meter",
                "elapsed", "DET", "CALC", "LIVE"),
    "log": ("TUDO", "FFMPEG", "linha 59", "linhas · filtro TUDO"),
    "qc_before": ("EBU R128", "ANTES", "DEPOIS", "LUFS", "dBTP", "LRA", "verificando", "Container", "Sample Rate"),
    "qc_after": ("EBU R128", "LRA", "D E L I V E R Y   R E A D Y", "Sample Rate", "certificado", "monitor EBU"),
    "completed": ("ENCODE COMPLETE", "DELIVERY READY", "38.2 MB", "LRA depois", "monitor EBU", "[ SAIR ]",
                  "[ VER QC ]", "[ VER LOG ]", "[ NOVO ENCODE ]", "[N] Novo encode"),
    "error": ("ffmpeg saiu com código 1", "FFMPEG STDERR", "ESTADO", "último frame", "[ SAIR ]", "[ NOVO ENCODE ]",
              "[↑↓] Rolar"),
    "cancelled": ("Encode interrompido", "o arquivo existente foi mantido", "linha 59", "[ SAIR ]",
                  "[ NOVO ENCODE ]"),
    "queue": ("RENDER QUEUE", "Job 9 de 14", "ENCODING", "PASS 1 / 1", "frame=", "[^C] Interrupt"),
    "report": ("FILA CONCLUÍDA COM FALHAS", "Sucesso", "Interrompidos", "Tempo total", "nome_comprido_00",
               "NÃO foi possível remover", "apague à mão", "[ SAIR ]"),
    "report_cancel": ("FILA INTERROMPIDA", "clip_3.mov", "apague à mão", "[ SAIR ]"),
    "overlay_log_final": ("TUDO", "[←→] Filtro", "[ESC] Voltar"),
    "overlay_qc_final": ("EBU R128", "[ESC] Voltar"),
}


@pytest.mark.parametrize("name", sorted(CONTENT))
def test_compact_80x24_keeps_functional_content(name):
    out = plain(name)
    for txt in CONTENT[name]:
        assert txt in out, (name, txt)
    assert len(out.splitlines()) == 24


def test_min_size_gate():
    s = home()
    assert not S.too_small(replace(s, size=(80, 24)))
    assert S.too_small(replace(s, size=(79, 24)))
    assert S.too_small(replace(s, size=(80, 23)))
    assert S.compact(replace(s, size=(119, 40))) and S.compact(replace(s, size=(120, 39)))
    assert not S.compact(replace(s, size=(120, 40)))
    assert S.UIState(config={}).size == S.FULL_SIZE


def test_home_navigates_at_80x24():
    s = home(size=(80, 24))
    assert S.apply(s, S.Key("DOWN")).home_focus == 1
    assert S.apply(s, S.Key("ENTER")).screen == S.SOURCE


def test_small_message_cites_min_size_and_ctrl_c_path():
    out = text_of(home(size=(79, 24)), width=79, height=24)
    assert "80×24" in out and "79×24" in out and "encode continua" not in out
    out = text_of(replace(busy(encoding_state()), size=(70, 20)), width=70, height=20)
    assert "o encode continua rodando" in out


def _down(s, n):
    for _ in range(n):
        s = S.apply(s, S.Key("DOWN"))
    return s


def test_report_scroll_reaches_last_job_at_80x24():
    s = replace(report_long(), size=(80, 24))
    assert "nome_comprido_13" not in text_of(s, width=80, height=24)
    s = _down(s, 50)
    assert s.queue_scroll == 14 - S.report_rows(s)
    out = text_of(s, width=80, height=24)
    assert "nome_comprido_13" in out and "[ SAIR ]" in out


def test_error_scroll_reaches_last_line_at_80x24():
    s = replace(error_state(), size=(80, 24))
    assert "ULTIMA LINHA DO STDERR" not in text_of(s, width=80, height=24)
    s = _down(s, 100)
    assert s.error_scroll == len(S.stderr_lines(s.error, s.log)) - S.error_rows(s)
    out = text_of(s, width=80, height=24)
    assert "ULTIMA LINHA DO STDERR" in out and "[ SAIR ]" in out


def test_scroll_windows_keep_full_size_values():
    s = S.UIState(config={})
    assert S.report_rows(s) == S.REPORT_ROWS == 21 and S.error_rows(s) == S.ERROR_ROWS == 17


def test_compact_layout_regions():
    lines = plain("encoding").splitlines()
    assert "REELS ENCODER" in lines[0] and "ENCODING" in lines[0]
    assert "[D] Details" in lines[-1] and "[^C] Interrupt" in lines[-1]


def test_compact_footer_strings_fit_80_columns():
    for name in STATES:
        s = replace(STATES[name](), size=(80, 24))
        text = "".join(seg.text for seg in natural(V.footer(s), 80)[0][0]).rstrip()
        assert cell_len(text) <= 80 and "…" not in text, (name, text)


def _body_height(s):
    return len(natural(V.SCREEN_RENDERERS[s.screen](s), s.size[0])[0])


def _squash(text):
    return "".join("".join(ln.strip(" │║") for ln in text.splitlines()).split())


LONG_READY_ERROR = ("Sem permissão de escrita na pasta de saída C:/Users/editor/Videos/projetos/cliente/2026/"
                    "novembro/entregas_finais/reels — escolha outra pasta de saída ou ajuste as permissões do Windows e tente de novo")


@pytest.mark.parametrize("size", [(80, 24), (100, 30), (119, 39)], ids=lambda z: f"{z[0]}x{z[1]}")
def test_ready_compact_shows_whole_long_error(size):
    assert len(LONG_READY_ERROR) >= 190
    s = replace(STATES["ready"](), ready_error=LONG_READY_ERROR, size=size)
    assert _body_height(s) <= size[1] - 2
    out = text_of(s, width=size[0], height=size[1])
    assert _squash(LONG_READY_ERROR) in _squash(out)
    assert "START ENCODE" in out and "KEY SETTINGS" in out


def long_error_state():
    msg = ("Falha ao abrir o arquivo de entrada C:/Users/editor/Videos/projetos/cliente/2026/novembro/"
           "brutos/clip_final_versao_aprovada.mov: o FFmpeg não reconheceu o container e o encoder abortou "
           "antes do primeiro frame; verifique o arquivo")
    s = replace(error_state(), error=R.Error("RuntimeError", msg, error_state().error.stderr_tail, None, None))
    return s, msg


@pytest.mark.parametrize("size", [(80, 24), (100, 30), (119, 39)], ids=lambda z: f"{z[0]}x{z[1]}")
def test_error_compact_card_shows_whole_message(size):
    s, msg = long_error_state()
    s = replace(s, size=size)
    assert len(msg) >= 200
    assert _body_height(s) <= size[1] - 2
    out = text_of(s, width=size[0], height=size[1])
    assert _squash(V.error_message(s)) in _squash(out)
    s = _down(s, 100)
    assert s.error_scroll == len(S.stderr_lines(s.error, s.log)) - S.error_rows(s)
    out = text_of(s, width=size[0], height=size[1])
    assert "ULTIMA LINHA DO STDERR" in out and "[ SAIR ]" in out


def _worst_draft(preset):
    d = {**S.draft(S.UIState(config={}, preset=preset)), "input": "C:/v/clip.mov", "batch": LONG,
         "source_kind": "folder", "output_dir_on": "on", "output_dir": LONG, "cineon_pipeline": "on",
         "enhance": "on", "enhance_ai": "on"}
    return d


WORST_FORMS = [(S.CONFIGURATION, p, 0) for p in (1, 2, 3, 5)] + [(S.ADVANCED, 5, t) for t in range(5)]


@pytest.mark.parametrize("screen,preset,tab", WORST_FORMS)
def test_worst_case_form_keeps_continue_inside_80x24(screen, preset, tab):
    s = S.UIState(config={}, screen=screen, preset=preset, tab=tab, drafts=((preset, _worst_draft(preset)),),
                  field_error="Informe a pasta de saída.", size=(80, 24), source_count=12)
    assert _body_height(s) <= 22
    out = text_of(s, width=80, height=24)
    assert "CONTINUAR" in out and "Informe a pasta de saída." in out


def _tick(s, size):
    return S.apply(s, S.Tick(s.now, size))


def test_report_resize_with_scroll_keeps_window_valid():
    jobs = tuple(S.Job(f"C:/v/lote/job_{i:02d}.mov", f"o_{i:02d}.mp4", status="ok") for i in range(30))
    s = replace(report_long(), size=(120, 40), queue=jobs, queue_scroll=0)
    s = _down(s, 50)
    assert s.queue_scroll == 30 - S.REPORT_ROWS
    small = _tick(s, (80, 24))
    out = text_of(small, width=80, height=24)
    assert f"job_{s.queue_scroll:02d}" in out
    small = _down(small, 50)
    assert small.queue_scroll == 30 - S.report_rows(small)
    assert "job_29" in text_of(small, width=80, height=24)
    full = _tick(small, (120, 40))
    assert "job_29" in text_of(full, width=120, height=40)


def test_error_resize_with_scroll_keeps_window_valid():
    s = replace(error_state(), size=(120, 40))
    s = _down(s, 100)
    total = len(S.stderr_lines(s.error, s.log))
    assert s.error_scroll == total - S.ERROR_ROWS
    small = _tick(s, (80, 24))
    assert "[ SAIR ]" in text_of(small, width=80, height=24)
    small = _down(small, 100)
    assert small.error_scroll == total - S.error_rows(small)
    assert "ULTIMA LINHA DO STDERR" in text_of(small, width=80, height=24)
    full = _tick(small, (120, 40))
    assert "ULTIMA LINHA DO STDERR" in text_of(full, width=120, height=40)


@pytest.mark.parametrize("kind", ["SYSTEM", "INFO", "WARNING", "FFMPEG"])
def test_log_compact_keeps_level_name_whole_with_long_text(kind):
    s = S.apply(busy(encoding_state()), S.Key("L"))
    rows = tuple(S.LogRow(k, f"{k} " + "x" * 200) for k in ("SYSTEM", "INFO", "WARNING", "FFMPEG"))
    s = replace(s, log=rows, size=(80, 24))
    lines = text_of(s, width=80, height=24).splitlines()
    assert any(ln.strip(" │║").startswith(f"{kind} ") for ln in lines), kind


def test_details_compact_pairs_section_titles_per_row():
    s = replace(STATES["details"](), size=(80, 24))
    lines = text_of(s, width=80, height=24).splitlines()
    for left, right in (("SOURCE", "HARDWARE"), ("ENCODING", "CONFIG"), ("OUTPUT", "PROGRESS")):
        assert any(left in ln and right in ln for ln in lines), (left, right)
    assert _body_height(s) <= 24 - 2
