from ui.config import EncodeConfig
from ui.tui import forms as F


def all_fields():
    return F.QUICK + F.CINEON + tuple(f for tab in F.TABS for f in F.ADVANCED[tab])


def test_every_field_is_an_encodeconfig_field_and_options_validate():
    names = set(EncodeConfig.model_fields)
    for f in all_fields():
        assert f.name in names, f.name
        for opt in f.options:
            EncodeConfig.model_validate({**EncodeConfig().model_dump(), f.name: opt})


def test_hidden_fields_never_exposed():
    exposed = {f.name for f in all_fields()}
    assert exposed.isdisjoint({"report", "cineon_lut", "debug", "hardware_info", "ui", "batch", "output_dir", "input"})


def test_preset_labels_are_the_wizard_labels():
    from ui.launcher import PRESETS
    assert F.PRESET_LABELS == tuple(PRESETS)
    assert F.ENABLED_PRESETS == (1, 2, 4, 5)


def test_new_draft_matches_factories():
    assert F.new_draft(1) == EncodeConfig.preset_quick_ffmpeg().model_dump()
    assert F.new_draft(2) == EncodeConfig.preset_film_cineon().model_dump()
    assert F.new_draft(5) == EncodeConfig().model_dump()


def test_quick_and_cineon_field_order():
    assert [f.name for f in F.QUICK] == ["fit", "fps", "mode"]
    assert [f.name for f in F.CINEON] == ["exposure_offset", "saturation", "fit"]


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
