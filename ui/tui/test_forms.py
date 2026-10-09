from ui.config import EncodeConfig
from ui.tui import forms as F


def all_fields():
    return F.QUICK + F.CINEON + F.BATCH + tuple(f for tab in F.TABS for f in F.ADVANCED[tab])


def test_every_field_is_an_encodeconfig_field_or_form_state_and_options_validate():
    names = set(EncodeConfig.model_fields) | F.FORM_ONLY
    for f in all_fields():
        assert f.name in names, f.name
        for opt in f.options:
            EncodeConfig.model_validate({**EncodeConfig().model_dump(), f.name: opt})


def test_hidden_fields_never_exposed():
    exposed = {f.name for f in all_fields()}
    assert exposed.isdisjoint({"report", "cineon_lut", "debug", "hardware_info", "ui", "batch", "input"})


def test_preset_labels_are_the_wizard_labels():
    from ui.launcher import PRESETS
    assert F.PRESET_LABELS == tuple(PRESETS)
    assert F.ENABLED_PRESETS == (1, 2, 3, 4, 5)
    assert "P3D" not in F.PRESET_HELP[3]


def test_new_draft_matches_factories():
    assert F.new_draft(1) == EncodeConfig.preset_quick_ffmpeg().model_dump()
    assert F.new_draft(2) == EncodeConfig.preset_film_cineon().model_dump()
    assert F.new_draft(3) == {**EncodeConfig.preset_batch().model_dump(), F.SOURCE_KIND: F.FOLDER, F.OUTDIR_ON: "off"}
    assert F.new_draft(5) == {**EncodeConfig().model_dump(), F.SOURCE_KIND: F.FILE, F.OUTDIR_ON: "off"}
    assert F.is_folder(F.new_draft(3)) and not F.is_folder(F.new_draft(5)) and not F.is_folder(F.new_draft(1))


def test_batch_form_order_labels_and_visibility():
    d = F.new_draft(3)
    assert F.form_for(3) is F.BATCH
    assert [f.label for f in F.BATCH] == ["Definir pasta de saída separada", "Pasta de saída", "Usar film look (Cineon)"]
    assert [f.name for f in F.visible(F.BATCH, d)] == [F.OUTDIR_ON, "cineon_pipeline"]
    assert [f.name for f in F.visible(F.BATCH, {**d, F.OUTDIR_ON: "on"})] == [F.OUTDIR_ON, "output_dir", "cineon_pipeline"]
    assert next(f for f in F.BATCH if f.name == "output_dir").kind == "path"


def test_advanced_source_tab_outdir_fields_only_for_folder():
    d = F.new_draft(5)

    def names(dd):
        return [f.name for f in F.visible(F.ADVANCED["Source"], dd)]

    base = ["cineon_pipeline", "fit", "fps", "scale", "mode", "performance"]
    assert names(d) == base
    folder = {**d, F.SOURCE_KIND: F.FOLDER}
    assert names(folder) == [F.OUTDIR_ON] + base
    assert names({**folder, F.OUTDIR_ON: "on"}) == [F.OUTDIR_ON, "output_dir"] + base
    assert F.ADVANCED["Source"][0].label == "Pasta de saída separada"


def test_to_config_strips_form_state_and_applies_output_dir_rules():
    d = {**F.new_draft(3), "batch": "C:/v/lote", "output_dir": "D:/saida"}
    cfg = F.to_config(d)
    assert F.OUTDIR_ON not in cfg and F.SOURCE_KIND not in cfg and cfg["output_dir"] is None
    assert F.to_config({**d, F.OUTDIR_ON: "on"})["output_dir"] == "D:/saida"
    file5 = {**F.new_draft(5), "input": "C:/v/a.mov", F.OUTDIR_ON: "on", "output_dir": "D:/saida"}
    assert F.to_config(file5)["output_dir"] is None
    EncodeConfig.model_validate(F.to_config({**d, F.OUTDIR_ON: "on"}))


def test_outdir_missing():
    d = {**F.new_draft(3), "batch": "C:/v/lote", F.OUTDIR_ON: "on"}
    assert F.outdir_missing(d)
    assert F.outdir_missing({**d, "output_dir": "  "})
    assert not F.outdir_missing({**d, "output_dir": "D:/saida"})
    assert not F.outdir_missing({**d, F.OUTDIR_ON: "off"})
    assert not F.outdir_missing({**F.new_draft(5), F.OUTDIR_ON: "on"})


def test_apply_change_accepts_form_state_keys():
    nd, err = F.apply_change(F.new_draft(3), F.OUTDIR_ON, "on")
    assert err is None and nd[F.OUTDIR_ON] == "on"
    nd, err = F.apply_change(nd, "output_dir", "D:/saida")
    assert err is None and nd["output_dir"] == "D:/saida"


def test_quick_and_cineon_field_order():
    assert [f.name for f in F.QUICK] == ["fit", "fps", "mode"]
    assert [f.name for f in F.CINEON] == ["exposure_offset", "saturation", "fit"]


def test_cineon_form_hides_exposure_and_saturation_when_cineon_off():
    d = F.new_draft(2)
    assert [f.name for f in F.visible(F.CINEON, d)] == ["exposure_offset", "saturation", "fit"]
    assert [f.name for f in F.visible(F.CINEON, {**d, "cineon_pipeline": "off"})] == ["fit"]


def test_advanced_tabs_and_conditions():
    d = F.new_draft(5)

    def names(tab, dd):
        return [f.name for f in F.visible(F.ADVANCED[tab], dd)]

    assert names("Source", d) == ["cineon_pipeline", "fit", "fps", "scale", "mode", "performance"]
    assert names("Color/LUT", d) == ["lut", "hdr", "tonemap"]
    assert names("Color/LUT", {**d, "cineon_pipeline": "on"}) == ["exposure_offset", "saturation", "hdr", "tonemap"]
    assert names("Audio", d) == ["loudnorm", "ebu_meter"]
    assert names("Enhance", d) == ["enhance", "enhance_ai", "dither"]
    assert names("Enhance", {**d, "enhance_ai": "on"}) == ["enhance", "enhance_ai", "mctf", "dither"]
    assert names("Enhance", {**d, "enhance": "off", "enhance_ai": "on"}) == ["enhance", "dither"]
    assert names("Export", d) == ["show_hardware", "threads"]


def test_derive_mctf_follows_wizard_rule():
    d = {**F.new_draft(5), "enhance": "on", "enhance_ai": "off", "mctf": "on"}
    assert F.derive(d)["mctf"] == "off"
    d2 = {**F.new_draft(5), "enhance": "off", "enhance_ai": "on", "mctf": "on"}
    assert F.derive(d2)["mctf"] == "on"


def test_apply_change_validates_and_derives():
    d = {**F.new_draft(5), "enhance_ai": "on", "mctf": "on"}
    nd, err = F.apply_change(d, "enhance_ai", "off")
    assert err is None and nd["mctf"] == "off"
    same, err = F.apply_change(d, "exposure_offset", 5.0)
    assert same == d and err


def test_output_name():
    d = {**F.new_draft(1), "input": "C:/v/clip.mov"}
    assert F.output_name(d).endswith(".mp4")
    assert F.output_name(F.new_draft(1)) == "—"


def test_new_draft_preset4_has_form_keys():
    d = F.new_draft(4)
    assert d[F.SOURCE_KIND] == F.FILE and d[F.OUTDIR_ON] == "off"
