# -*- coding: utf-8 -*-
"""Round-trip Node 3 (Cineon log) -> Node 5 (LUT baseline) deve ser transparente.

A LUT FilmLook_Portra400_SkinPriority_D65.cube e um identity baseline:
para todo o range util (linear 0.0-1.0), LUT(log_encoding_cineon(lin)) deve
devolver oetf_BT709(lin) dentro de sub-code 8-bit apos o clip final do encoder.

Regressao coberta: bake com clamp `clip(decode(x), 0, 1)` cria um knee duro no
white reference Cineon (x=0.6696), que cai entre os pontos 21 e 22 da grade
33x33x33. A corda da interpolacao trilinear subestima a curva concava em ate
-2.93% (-7.5 codes 8-bit no pico) -> highlights abafados no Cineon Mode.
"""

from pathlib import Path

import numpy as np
import pytest

colour = pytest.importorskip("colour")

from cineon_pipeline import LUT3D, log_encoding_cineon  # noqa: E402

LUT_PATH = Path(__file__).resolve().parents[1] / "FilmLook_Portra400_SkinPriority_D65.cube"

# Tolerancia: meio code 8-bit de folga sobre 1 code (erro de interpolacao
# residual de grade 33 em curva suave fica bem abaixo disso).
MAX_ERR = 2.0 / 255.0


@pytest.fixture(scope="module")
def lut():
    return LUT3D(str(LUT_PATH))


def _roundtrip(lut, lin):
    """Node 3 encode -> LUT -> clip [0,1] (como o encoder faz no uint8)."""
    enc = log_encoding_cineon(lin.astype(np.float32))
    neutral = np.stack([enc] * 3, axis=-1).reshape(1, -1, 3).astype(np.float32)
    out = lut.apply(neutral).reshape(-1, 3)[:, 0]
    return np.clip(out, 0.0, 1.0)


def test_roundtrip_neutral_ramp_transparente(lut):
    lin = np.linspace(0.0, 1.0, 1025, dtype=np.float32)
    out = _roundtrip(lut, lin)
    expected = colour.models.oetf_BT709(lin)
    err = np.abs(out - expected)
    worst = int(np.argmax(err))
    assert err.max() <= MAX_ERR, (
        f"round-trip fora de sub-code: |err|max={err.max():.5f} "
        f"({err.max() * 255:.1f} codes) em lin={lin[worst]:.4f}"
    )


def test_roundtrip_white_atinge_pico(lut):
    out = _roundtrip(lut, np.array([1.0], dtype=np.float32))
    assert out[0] == pytest.approx(1.0, abs=1e-6), (
        f"branco lin=1.0 deve mapear para 1.0 apos clip; obtido {out[0]:.5f} "
        f"({(out[0] - 1.0) * 255:+.1f} codes)"
    )


_CUBE_DATA_2 = (
    "0.0 0.0 0.0\n"
    "1.0 0.0 0.0\n"
    "0.0 1.0 0.0\n"
    "1.0 1.0 0.0\n"
    "0.0 0.0 1.0\n"
    "1.0 0.0 1.0\n"
    "0.0 1.0 1.0\n"
    "1.0 1.0 1.0\n"
)

_CUBE_CASES = {
    "bom_lut_size_primeira_linha": (
        "utf-8-sig",
        "LUT_3D_SIZE 2\n" + _CUBE_DATA_2,
    ),
    "utf8_title_acentuado_maiusculo": (
        "utf-8",
        'TITLE "ÁGUA Film Look"\nLUT_3D_SIZE 2\n' + _CUBE_DATA_2,
    ),
    "cp1252_title_acentuado_maiusculo": (
        "cp1252",
        'TITLE "ÁGUA Film Look"\nLUT_3D_SIZE 2\n' + _CUBE_DATA_2,
    ),
    "ascii_puro": (
        "ascii",
        'TITLE "Film Look"\nLUT_3D_SIZE 2\n' + _CUBE_DATA_2,
    ),
}


@pytest.mark.parametrize("caso", sorted(_CUBE_CASES))
def test_load_cube_file_independente_de_encoding(tmp_path, caso):
    encoding, content = _CUBE_CASES[caso]
    p = tmp_path / f"{caso}.cube"
    with open(p, "w", encoding=encoding, newline="") as f:
        f.write(content)

    loaded = LUT3D(str(p))

    assert loaded.lut_size == 2
