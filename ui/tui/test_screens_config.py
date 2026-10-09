from ui.config import EncodeConfig
from ui.tui import forms as F
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of


def home(**kw):
    return S.UIState(config={}, screen=S.HOME,
                     system=(("FFmpeg", "ffmpeg.exe"), ("ffprobe", "ffprobe.exe"), ("ffplay", "ok"),
                             ("hardware", "detectado no início do encode")), **kw)


def test_home_screen():
    out = text_of(home())
    for txt in ("REELS ENCODER", "Encode rápido (FFmpeg)", "Film look (Cineon)", "Batch de pasta",
                "Tools", "Configurar avançado", "O QUE FAZ", "SYSTEM", "ffprobe.exe",
                "detectado no início do encode", "[1-5] Abrir"):
        assert txt in out, txt
    assert "chega no P3D" not in out and "[1 2 4 5]" not in out
    assert "▸" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_home_rail_has_no_checks_before_home():
    out = text_of(home())
    assert "✓ HOME" not in out and "✓ SOURCE" not in out


def test_source_screen_states():
    base = S.UIState(config={}, screen=S.SOURCE, preset=1, drafts=((1, {**S.draft(S.UIState(config={}, preset=1))}),),
                     source=W.TextBuf("C:/v/clip.mov", 13))
    for status, txt in (("VALID", "arquivo encontrado"), ("NOT_FOUND", "não encontrado"),
                        ("INVALID", "informe um arquivo"), ("CHECKING", "verificando")):
        out = text_of(S.UIState(**{**base.__dict__, "source_status": status}))
        assert txt in out, status
        assert "clip.mov" in out and "PROGRAM" in out and "ENTER → CONFIGURATION" in out
        assert_fits(out)
        assert_no_emoji(out)
    out = text_of(S.UIState(**{**base.__dict__, "source_status": "VALID", "source_dims": (1080, 1920)}))
    assert "1080 × 1920" in out and "clip_Hollywood" in out


def test_path_field_long_path_keeps_cursor_visible():
    buf = W.TextBuf("C:/" + "a" * 200 + "/z.mov", 206)
    txt = __import__("ui.tui.screens", fromlist=["path_field"]).path_field(buf, 60)
    assert len(txt.plain) <= 61 and "z.mov" in txt.plain


def cfg_state(preset=1, **kw):
    d = {**F.new_draft(preset), "input": "C:/v/clip.mov"}
    return S.UIState(config={}, screen=kw.pop("screen", S.CONFIGURATION), preset=preset, drafts=((preset, d),), **kw)


def test_configuration_quick():
    out = text_of(cfg_state(1))
    for txt in ("Enquadramento", "FPS", "Modo", "◂ contain ▸", "CONTINUAR", "PADRÕES", "loudnorm"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_configuration_cineon_numbers_and_error():
    s = cfg_state(2, field_error="Máximo é 2.")
    out = text_of(s)
    assert "Máximo é 2." in out


def test_configuration_numbers_shown_as_stored():
    s = cfg_state(2)
    s = S.UIState(**{**s.__dict__, "drafts": ((2, {**S.draft(s), "exposure_offset": 0.05, "saturation": 1.234}),)})
    out = text_of(s)
    assert "0.05" in out and "1.234" in out
    assert "+0.1" not in out and "1.23 " not in out


def test_configuration_footer_lists_digit_typing_not_space():
    lines = text_of(cfg_state(1)).splitlines()
    foot = "\n".join(lines[-2:])
    assert "[0-9] Digitar" in foot and "SPACE" not in foot
    assert "[↑↓] Campo" in foot and "[ENTER] Próximo" in foot and "[ESC] Voltar" in foot


def test_ready_esc_label_is_voltar_in_tui_flow_and_sair_without_preset():
    base = {"input": "C:/v/clip.mov", "mode": "crf", "cineon_pipeline": "off"}
    out = text_of(S.UIState(config=base, screen=S.READY, preset=1, output_path="C:/v/o.mp4"))
    foot = "\n".join(out.splitlines()[-2:])
    assert "[ESC] Voltar" in foot and "Sair" not in foot
    assert "[ ESC  Voltar ]" in out and "[ ESC  Sair ]" not in out
    out = text_of(S.UIState(config=base, screen=S.READY, output_path="C:/v/o.mp4"))
    assert "[ESC] Sair" in "\n".join(out.splitlines()[-2:]) and "[ ESC  Sair ]" in out


def test_configuration_number_edit_shows_buffer():
    s = cfg_state(2, edit=W.TextBuf("-0.7", 4))
    assert "-0.7" in text_of(s)


def test_advanced_each_tab():
    for i, tab in enumerate(F.TABS):
        s = cfg_state(5, screen=S.ADVANCED, tab=i)
        out = text_of(s)
        for t in F.TABS:
            assert t in out
        for f in F.visible(F.ADVANCED[tab], S.draft(s)):
            assert f.label.split(" (")[0] in out, f.label
        assert "SETTINGS" in out and "Pipeline" in out
        assert_fits(out)
        assert_no_emoji(out)
    focused_bar = text_of(cfg_state(5, screen=S.ADVANCED, tab_focus=True))
    assert "▎▸Source" in focused_bar


def test_preview_rows_and_chips():
    d = {**F.new_draft(5), "cineon_pipeline": "on", "exposure_offset": 0.5, "saturation": 0.8}
    rows = dict(__import__("ui.tui.screens", fromlist=["preview_rows"]).preview_rows(d))
    assert list(rows)[:9] == ["Pipeline", "Mode", "FPS", "Scale / Fit", "LUT", "HDR", "Tonemap", "Audio", "Performance"]
    assert rows["Exposure / Sat"] == "+0.5 EV · 0.8"
    chips = dict(__import__("ui.tui.screens", fromlist=["preview_chips"]).preview_chips(d))
    assert list(chips) == ["LUT", "Loudnorm", "Enhance", "AI", "MCTF", "Dither", "EBU Meter"]


def test_preview_screen_and_error():
    s = cfg_state(1, screen=S.PREVIEW, field_error="combinação inválida")
    out = text_of(s)
    for txt in ("PREVIEW", "EXPORT SETTINGS", "CONTINUAR", "REVISAR", "combinação inválida", "LUT", "EBU Meter"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def _program_rows(out):
    lines = out.splitlines()
    # Find top line containing either "┌─ PROGRAM" (Windows) or "╭─ PROGRAM" (Linux)
    top = next(i for i, ln in enumerate(lines) if "┌─ PROGRAM" in ln or "╭─ PROGRAM" in ln)
    line_top = lines[top]
    # Find the opening corner position
    if "┌─ PROGRAM" in line_top:
        c0 = line_top.index("┌─ PROGRAM")
    else:
        c0 = line_top.index("╭─ PROGRAM")
    # Find the closing corner as first of "┐" (Windows) or "╮" (Linux) after c0
    closing_idx = next(idx for idx in range(c0 + 1, len(line_top)) if line_top[idx] in ("┐", "╮"))
    width = closing_idx - c0 + 1
    rows = []
    for ln in lines[top + 1:]:
        cell = ln[c0:c0 + width]
        if not cell.startswith("│"):
            break
        if cell[1:-1].strip():
            rows.append(cell)
    return width, rows


def test_program_frame_cover_portrait_keeps_bars_aligned():
    from dataclasses import replace

    from ui.tui.test_screens import CFG, encoding_state
    d = {**F.new_draft(1), "input": "C:/v/clip.mov", "fit": "cover"}
    states = {
        "PREVIEW": cfg_state(1, screen=S.PREVIEW, source_dims=(1080, 1920)),
        "SOURCE": cfg_state(1, screen=S.SOURCE, source=W.TextBuf("C:/v/clip.mov", 13), source_status="VALID",
                            source_dims=(1080, 1920)),
        "ENCODING": replace(encoding_state(), config={**CFG, "mode": "2pass", "fit": "cover"}),
    }
    states["PREVIEW"] = S.UIState(**{**states["PREVIEW"].__dict__, "drafts": ((1, d),)})
    states["SOURCE"] = S.UIState(**{**states["SOURCE"].__dict__, "drafts": ((1, d),)})
    for name, s in states.items():
        out = text_of(s)
        for ln in out.splitlines():
            assert "preenche" not in ln or "crop" in ln, (name, ln)
        width, rows = _program_rows(out)
        assert len(rows) >= 9, (name, rows)
        for cell in rows:
            assert len(cell) == width and cell.endswith("│"), (name, cell)
            assert cell[2] == "█" and cell[-3] == "█", (name, cell)
        assert any("crop" in cell for cell in rows), name
        assert_fits(out)


def test_ready_shows_ready_error():
    s = S.UIState(config={"input": "C:/v/clip.mov", "mode": "crf", "cineon_pipeline": "off"}, screen=S.READY,
                  preset=1, output_path="C:/v/o.mp4", ready_error="arquivo de entrada não encontrado: C:/v/clip.mov")
    assert "arquivo de entrada não encontrado" in text_of(s)


def folder_state(status="VALID", count=3, preset=3, path="C:/v/lote", **kw):
    d = {**F.new_draft(preset), F.SOURCE_KIND: F.FOLDER}
    return S.UIState(config={}, screen=S.SOURCE, preset=preset, drafts=((preset, d),),
                     source=W.TextBuf(path, len(path)), source_status=status,
                     source_count=count if status in ("VALID", "EMPTY") else None, **kw)


def test_source_folder_states():
    cases = (("VALID", 3, "✓ pasta encontrada · 3 vídeos"), ("VALID", 1, "✓ pasta encontrada · 1 vídeo"),
             ("EMPTY", 0, "⚠ nenhum vídeo encontrado"), ("NOT_FOUND", None, "✗ pasta não encontrada"),
             ("INVALID", None, "informe uma pasta"), ("CHECKING", None, "verificando"))
    for status, count, txt in cases:
        out = text_of(folder_state(status, count))
        assert txt in out, status
        assert "PASTA" in out and "PROGRAM" in out and "ENTER → CONFIGURATION" in out
        assert "DIMENSÕES" not in out and "ARQUIVO" not in out
        assert_fits(out)
        assert_no_emoji(out)
    out = text_of(folder_state())
    assert "pasta · 3 vídeos" in out and "mesma pasta" in out
    assert "1 vídeos" not in text_of(folder_state("VALID", 1))


def test_source_preset5_tipo_row_and_footer():
    from dataclasses import replace
    s = S.UIState(config={}, screen=S.SOURCE, preset=5, drafts=((5, F.new_draft(5)),))
    out = text_of(s)
    assert "● Arquivo único" in out and "○ Pasta (batch)" in out and "ENTER → ADVANCED" in out
    assert "chega no P3D" not in out and "▎▸ ●" not in out
    assert "[↑] Tipo" in "\n".join(out.splitlines()[-2:])
    out = text_of(replace(s, tab_focus=True))
    assert "▎▸ ● Arquivo único" in out
    foot = "\n".join(out.splitlines()[-2:])
    assert "[←→] Tipo" in foot and "[↓] Caminho" in foot
    out = text_of(folder_state(preset=5))
    assert "○ Arquivo único" in out and "● Pasta (batch)" in out and "PASTA" in out
    assert_fits(out)
    assert_no_emoji(out)


def batch_cfg_state(**kw):
    d = {**F.new_draft(3), "batch": "C:/v/lote", **kw.pop("draft", {})}
    return S.UIState(config={}, screen=kw.pop("screen", S.CONFIGURATION), preset=3, drafts=((3, d),),
                     source_count=3, **kw)


def test_configuration_batch_form():
    out = text_of(batch_cfg_state())
    for txt in ("Definir pasta de saída separada", "Usar film look (Cineon)", "CONTINUAR", "PADRÕES",
                "C:/v/lote", "3 vídeos", "mesma pasta"):
        assert txt in out, txt
    assert "Pasta de saída" not in out
    foot = "\n".join(out.splitlines()[-2:])
    assert "[digite] Pasta" in foot and "[0-9]" not in foot
    assert_fits(out)
    assert_no_emoji(out)
    on = batch_cfg_state(draft={F.OUTDIR_ON: "on", "output_dir": "D:/saida"})
    out = text_of(on)
    assert "Pasta de saída" in out and "D:/saida" in out
    editing = batch_cfg_state(draft={F.OUTDIR_ON: "on"}, focus=((S.CONFIGURATION, 1),), edit=W.TextBuf("D:/sa", 5))
    assert "D:/sa" in text_of(editing)
    err = batch_cfg_state(draft={F.OUTDIR_ON: "on"}, focus=((S.CONFIGURATION, 1),), field_error=F.OUTDIR_EMPTY)
    assert "Informe a pasta de saída." in text_of(err)


def test_preview_folder_text():
    out = text_of(batch_cfg_state(screen=S.PREVIEW))
    for txt in ("PREVIEW", "pasta lote · 3 vídeos", "saída: mesma pasta", "PROGRAM", "EXPORT SETTINGS"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_preview_folder_with_brackets():
    s = batch_cfg_state(screen=S.PREVIEW, draft={"batch": "C:/v/[lote] final"})
    out = text_of(s)
    assert "[lote] final" in out and "erro ao desenhar" not in out
    assert_fits(out)


def test_preview_file_with_brackets():
    s = cfg_state(1, screen=S.PREVIEW)
    s = S.UIState(**{**s.__dict__, "drafts": ((1, {**S.draft(s), "input": "C:/v/clip [b].mov"}),)})
    out = text_of(s)
    assert "clip [b].mov" in out and "erro ao desenhar" not in out
    assert_fits(out)


def test_ready_folder_text():
    cfg = {**vars(EncodeConfig.preset_batch("C:/v/lote").to_namespace()), "output_dir": "D:/saida"}
    out = text_of(S.UIState(config=cfg, screen=S.READY, preset=3, is_batch=True, source_count=12))
    for txt in ("READY TO ENCODE", "pasta lote · 12 vídeos", "saída: D:/saida", "START QUEUE", "por vídeo",
                "suprimido em batch"):
        assert txt in out, txt
    assert "START ENCODE" not in out
    assert_fits(out)
    assert_no_emoji(out)


def test_ready_folder_long_names_keep_pipeline_label():
    from ui.tui.screens import pipeline_label
    cfg = {**vars(EncodeConfig.preset_batch("C:/v/" + "x" * 90 + " [lote] final").to_namespace()),
           "output_dir": "D:/" + "y" * 120}
    out = text_of(S.UIState(config=cfg, screen=S.READY, preset=3, is_batch=True, source_count=12))
    assert out.count(pipeline_label(cfg)) >= 2
    assert "KEY SETTINGS" in out and "START QUEUE" in out and "erro ao desenhar" not in out
    assert_fits(out)


def test_helpers():
    from ui.tui.screens import elide, folder_name, output_dir_text, source_text, videos
    assert elide(None, 5) == "—" and elide("abcdefgh", 5) == "…efgh" and elide("abc", 5) == "abc"
    assert folder_name("C:/v/lote/") == "lote" and folder_name(None) == "—"
    assert videos(1) == "1 vídeo" and videos(3) == "3 vídeos" and videos(None) == "— vídeos"
    assert output_dir_text({}) == "mesma pasta" and output_dir_text({"output_dir": "D:/s"}) == "D:/s"
    assert source_text({"batch": "C:/v/lote"}, 2) == "pasta lote · 2 vídeos"
    assert source_text({"input": "C:/v/a.mov"}, None) == "a.mov"


def _ansi_before(state, needle):
    from ui.theme import get_console
    con = get_console(record=True, width=120, height=40, force_terminal=True, color_system="truecolor")
    con.print(__import__("ui.tui.screens", fromlist=["render"]).render(state))
    line = next(ln for ln in con.export_text(styles=True).splitlines() if needle in ln)
    head = line.split(needle)[0]
    start = head.rfind("\x1b[")
    return head[start:head.index("m", start) + 1]


def test_source_next_hint_dims_unless_valid():
    base = S.UIState(config={}, screen=S.SOURCE, preset=1, drafts=((1, {**S.draft(S.UIState(config={}, preset=1))}),),
                     source=W.TextBuf("C:/v/clip.mov", 13))
    valid = _ansi_before(S.UIState(**{**base.__dict__, "source_status": "VALID"}), "ENTER → CONFIGURATION")
    muted = _ansi_before(base, "[ENTER] Continuar")
    for status in ("NOT_FOUND", "INVALID", "CHECKING"):
        dim = _ansi_before(S.UIState(**{**base.__dict__, "source_status": status}), "ENTER → CONFIGURATION")
        assert dim == muted and dim != valid, status


def test_choice_with_single_option_has_no_arrows():
    sc = __import__("ui.tui.screens", fromlist=["_value_text"])
    one = F.Field("x", "choice", "X", ("only",))
    two = F.Field("x", "choice", "X", ("a", "b"))
    assert sc._value_text(S.UIState(config={}), one, {"x": "only"}, False).plain == "only"
    assert sc._value_text(S.UIState(config={}), two, {"x": "a"}, False).plain == "◂ a ▸"


def test_preview_rows_show_exact_exposure_and_saturation():
    sc = __import__("ui.tui.screens", fromlist=["preview_rows"])
    d = {**F.new_draft(5), "cineon_pipeline": "on", "exposure_offset": 0.05, "saturation": 1.234}
    assert dict(sc.preview_rows(d))["Exposure / Sat"] == "+0.05 EV · 1.234"
    d = {**d, "exposure_offset": -0.7, "saturation": 1.0}
    assert dict(sc.preview_rows(d))["Exposure / Sat"] == "-0.7 EV · 1"
