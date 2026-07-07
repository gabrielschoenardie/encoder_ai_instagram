# -*- coding: utf-8 -*-
"""Exposure em stops (Node 2) deve corresponder a stops fotograficos reais.

Regressao coberta: node2_primary aplicava `exposure_offset * 0.301` (log10(2))
diretamente no espaco DaVinci Intermediate (log). 0.301 so vale para log10
puro sem offset aditivo -- a curva DI real tem offset (`log(L*a+b)`), entao a
inclinacao log-por-stop varia com o nivel de luminancia (~0.071-0.073 no
range util, medido via colour-science). Usar 0.301 fazia `--exposure 1.0`
aplicar ~4.1 stops reais em vez de 1.
"""

import numpy as np
import pytest

colour = pytest.importorskip("colour")

from cineon_pipeline import (  # noqa: E402
    eotf_davinci_intermediate,
    node2_primary,
    oetf_davinci_intermediate,
)

REF_GREY = 0.18  # 18% grey -- ancora fotografica padrao para "stops"


def _dwg_frame(linear_value):
    return oetf_davinci_intermediate(
        np.full((1, 1, 3), linear_value, dtype=np.float32)
    )


def test_zero_exposure_is_noop():
    frame_dwg = _dwg_frame(REF_GREY)
    out = node2_primary(frame_dwg, exposure_offset=0.0)
    assert np.allclose(out, frame_dwg)


def test_one_stop_exposure_doubles_reference_grey_linear():
    frame_dwg = _dwg_frame(REF_GREY)
    out = node2_primary(frame_dwg, exposure_offset=1.0)
    recovered_linear = eotf_davinci_intermediate(out)
    assert recovered_linear[0, 0, 0] == pytest.approx(REF_GREY * 2.0, rel=1e-3)


def test_negative_one_stop_halves_reference_grey_linear():
    frame_dwg = _dwg_frame(REF_GREY)
    out = node2_primary(frame_dwg, exposure_offset=-1.0)
    recovered_linear = eotf_davinci_intermediate(out)
    assert recovered_linear[0, 0, 0] == pytest.approx(REF_GREY * 0.5, rel=1e-3)


def test_two_stops_quadruples_reference_grey_linear():
    frame_dwg = _dwg_frame(REF_GREY)
    out = node2_primary(frame_dwg, exposure_offset=2.0)
    recovered_linear = eotf_davinci_intermediate(out)
    assert recovered_linear[0, 0, 0] == pytest.approx(REF_GREY * 4.0, rel=1e-3)
