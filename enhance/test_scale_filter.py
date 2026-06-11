"""Testes para build_scale_filter: modos de enquadramento contain (default) e cover.

contain (aspect-fit): frame inteiro cabe no alvo, pode sair menor que o alvo.
cover  (aspect-fill): escala pra cobrir os dois eixos e croppa o excesso no centro,
                      produzindo SEMPRE exatamente as dimensões-alvo.
"""
import importlib

import pytest

R = importlib.import_module("Reels_Encoder_v2_FINAL")


@pytest.fixture(autouse=True)
def _silence_console(monkeypatch):
    # build_scale_filter imprime via rich; no terminal cp1252 do Windows os emojis
    # quebram. Silencia o console durante os testes.
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)


# ── contain (comportamento atual, default) ──────────────────────────────────
def test_contain_downscale_landscape():
    # 4K 16:9 → 1920x1080 exato
    assert R.build_scale_filter(3840, 2160, 1920, 1080) == "zscale=w=1920:h=1080:filter=lanczos"


def test_contain_portrait_3x4_returns_none():
    # 1080x1440 (3:4) com alvo 9:16: contain não faz upscale → None (sai 1080x1440)
    assert R.build_scale_filter(1080, 1440, 1080, 1920) is None


def test_contain_already_at_target_returns_none():
    assert R.build_scale_filter(1080, 1920, 1080, 1920) is None


# ── cover (novo: aspect-fill) ───────────────────────────────────────────────
def test_cover_portrait_3x4_scales_and_crops():
    # 1080x1440 (3:4) → cover: escala pra 1440x1920 (max factor) e croppa centro 1080x1920
    result = R.build_scale_filter(1080, 1440, 1080, 1920, fit="cover")
    assert result == "zscale=w=1440:h=1920:filter=lanczos,crop=1080:1920"


def test_cover_larger_portrait_crop_only_when_no_scale_needed():
    # 1440x1920 já cobre o alvo sem escalar → só crop centralizado
    result = R.build_scale_filter(1440, 1920, 1080, 1920, fit="cover")
    assert result == "crop=1080:1920"


def test_cover_exact_target_returns_none():
    # já é exatamente o alvo: nada a fazer
    assert R.build_scale_filter(1080, 1920, 1080, 1920, fit="cover") is None


def test_cover_matching_aspect_no_crop():
    # 9:16 perfeito em alta res → escala exato, sem crop necessário
    result = R.build_scale_filter(1620, 2880, 1080, 1920, fit="cover")
    assert result == "zscale=w=1080:h=1920:filter=lanczos"


def test_cover_output_always_at_least_target():
    # cobertura mínima garantida mesmo com arredondamento par
    for iw, ih in [(1079, 1439), (1234, 1601), (1080, 1441)]:
        result = R.build_scale_filter(iw, ih, 1080, 1920, fit="cover")
        assert result is not None
        assert "crop=1080:1920" in result
