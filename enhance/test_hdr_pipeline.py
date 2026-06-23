"""Testes para o pipeline HDR (build_scene_referred_hdr_pipeline / build_video_filter_auto).

Foco: a correção do "no path between colorspaces" (code 3074).

Quando enhance-ai está ON, fontes HDR passam pelo filter_complex seletivo, cujos
filtros (format=yuva420p, alphamerge, overlay) descartam os metadados de cor do
frame. O pipeline HDR começa com `zscale=t=linear`, que aborta se não souber o
transfer de origem. A correção re-carimba os tags com `setparams` ANTES do zscale.
"""
import importlib

import pytest

R = importlib.import_module("Reels_Encoder_v2_FINAL")


@pytest.fixture(autouse=True)
def _silence_console(monkeypatch):
    # rich + cp1252 do Windows quebra com emoji; silencia durante os testes.
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)


# ── setparams re-stamp (a correção) ──────────────────────────────────────────

def test_hdr_setparams_precedes_zscale_linear():
    """setparams (re-carimbo dos tags) deve vir ANTES do zscale=t=linear."""
    vf = R.build_scene_referred_hdr_pipeline(
        scale_filter=None,
        target_resolution=(1080, 1920),
        tonemap_algorithm="mobius",
        input_color=("bt2020", "arib-std-b67", "bt2020nc"),
    )
    assert "setparams=" in vf
    assert "color_trc=arib-std-b67" in vf
    assert "color_primaries=bt2020" in vf
    assert "colorspace=bt2020nc" in vf
    # ordem: setparams antes da linearização (senão o zscale ainda quebra)
    assert vf.index("setparams=") < vf.index("zscale=t=linear")


def test_hdr_setparams_omits_unknown_keys():
    """Valores 'unknown' não devem virar tags inválidas no setparams."""
    vf = R.build_scene_referred_hdr_pipeline(
        scale_filter=None,
        target_resolution=(1080, 1920),
        input_color=("bt2020", "smpte2084", "unknown"),
    )
    assert "color_primaries=bt2020" in vf
    assert "color_trc=smpte2084" in vf
    assert "colorspace=" not in vf  # space era 'unknown' → omitido


def test_hdr_no_input_color_emits_no_setparams():
    """Sem input_color (compat retro), nenhum setparams é emitido."""
    vf = R.build_scene_referred_hdr_pipeline(
        scale_filter=None,
        target_resolution=(1080, 1920),
        input_color=None,
    )
    assert "setparams=" not in vf
    # pipeline HDR base permanece intacto
    assert "zscale=t=linear" in vf
    assert "tonemap=mobius" in vf


def test_hdr_setparams_comes_before_scale():
    """O re-carimbo deve preceder até o scale (que também propaga/altera tags)."""
    vf = R.build_scene_referred_hdr_pipeline(
        scale_filter="zscale=w=1080:h=1920:filter=lanczos",
        target_resolution=(1080, 1920),
        input_color=("bt2020", "arib-std-b67", "bt2020nc"),
    )
    assert vf.index("setparams=") < vf.index("zscale=w=1080")


def test_build_video_filter_auto_threads_input_color_for_hdr():
    """build_video_filter_auto deve repassar input_color ao pipeline HDR."""
    vf = R.build_video_filter_auto(
        is_hdr=True,
        scale_filter=None,
        target_resolution=(1080, 1920),
        tonemap_algorithm="mobius",
        input_color=("bt2020", "arib-std-b67", "bt2020nc"),
    )
    assert "setparams=" in vf and "color_trc=arib-std-b67" in vf


def test_build_video_filter_auto_sdr_ignores_input_color():
    """Fonte SDR usa o float pipeline e não emite setparams HDR."""
    vf = R.build_video_filter_auto(
        is_hdr=False,
        scale_filter=None,
        target_resolution=(1080, 1920),
        input_color=("bt709", "bt709", "bt709"),
    )
    assert "setparams=" not in vf
