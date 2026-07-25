# -*- coding: utf-8 -*-
"""_validate_cineon_constants() guarda os valores canonicos da formula
Cineon Log contra regressao silenciosa (ver
.claude/skills/instagram-reels-encoder/references/cineon-pipeline.md,
secao "Formula Cineon Log").

Cada teste adultera uma constante por vez (via monkeypatch) e afirma que a
funcao levanta RuntimeError. Um caso feliz confirma que os valores reais nao
disparam a excecao.
"""

import pytest

colour = pytest.importorskip("colour")

import cineon_pipeline as cp  # noqa: E402


def test_validate_cineon_constants_passes_with_real_values():
    cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_without_colour_science(monkeypatch):
    monkeypatch.setattr(cp, "COLOUR_AVAILABLE", False)
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_on_ref_black_tampering(monkeypatch):
    monkeypatch.setattr(cp, "CINEON_REF_BLACK", 100)
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_on_ref_white_tampering(monkeypatch):
    monkeypatch.setattr(cp, "CINEON_REF_WHITE", 700)
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_on_gain_tampering(monkeypatch):
    monkeypatch.setattr(cp, "CINEON_GAIN", 310)
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_on_expected_black_offset_tampering(
    monkeypatch,
):
    monkeypatch.setattr(cp, "CINEON_EXPECTED_BLACK_OFFSET", 0.5)
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_validate_cineon_constants_raises_on_reference_points_tampering(monkeypatch):
    monkeypatch.setattr(
        cp,
        "CINEON_REFERENCE_POINTS",
        (
            ("black (lin=0.0)", 0.0, 0.9928),
            ("18% grey (lin=0.18)", 0.18, 0.457),
            ("white (lin=1.0)", 1.0, 0.6697),
        ),
    )
    with pytest.raises(RuntimeError):
        cp._validate_cineon_constants()


def test_run_ffmpeg_with_cineon_calls_guard_before_touching_disk_or_ffmpeg(
    monkeypatch,
):
    """O call site em run_ffmpeg_with_cineon deve disparar o guard antes de
    qualquer I/O (probe_video, LUT3D, subprocess do FFmpeg)."""
    import Reels_Encoder_v2_FINAL as R  # noqa: E402

    def _boom():
        raise RuntimeError("adulterado para o teste")

    monkeypatch.setattr(cp, "_validate_cineon_constants", _boom)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "probe_video foi chamado antes do guard de constantes Cineon"
        )

    monkeypatch.setattr(R, "probe_video", _fail_if_called)

    with pytest.raises(RuntimeError, match="adulterado para o teste"):
        R.run_ffmpeg_with_cineon(
            input_file="nonexistent-input-does-not-exist.mp4",
            output_file="nonexistent-output-does-not-exist.mp4",
        )
