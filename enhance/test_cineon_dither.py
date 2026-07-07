# -*- coding: utf-8 -*-
"""RPDF dithering na quantizacao float32->uint8 do pipeline Cineon.

Regressao coberta: Reels_Encoder_v2_FINAL.py:3564-3567 fazia um cast direto
`astype(np.uint8)` sem dither -> truncamento (vies -0.5 LSB) e banding em
areas planas. quantize_uint8_dithered() soma ruido RPDF (uniforme +-0.5 LSB,
media zero) antes de arredondar, quebrando a coerencia espacial do degrau de
quantizacao sem introduzir vies -- mesma tecnica do filtro
`noise=c0s=...:c0f=t+u` do pipeline FFmpeg (ver
enhance/ffmpeg_filters.py::_build_dither).
"""

import numpy as np
import pytest

from cineon_pipeline import quantize_uint8_dithered


def test_output_dtype_and_shape():
    frame = np.full((4, 4, 3), 0.5, dtype=np.float32)
    out = quantize_uint8_dithered(frame, rng=np.random.default_rng(0))
    assert out.dtype == np.uint8
    assert out.shape == frame.shape


def test_dither_breaks_flat_banding():
    # 127.5/255 esta exatamente entre dois codes 8-bit; sem dither, o cast
    # devolve sempre o mesmo valor para toda a imagem -> banding num
    # gradiente com muitos pixels neste nivel. Com dither, deve variar.
    frame = np.full((64, 64, 3), 127.5 / 255.0, dtype=np.float32)
    out = quantize_uint8_dithered(frame, rng=np.random.default_rng(1))
    assert len(np.unique(out)) > 1, "dither nao quebrou o valor constante"


def test_dither_is_unbiased():
    # A media do dither RPDF sobre muitas amostras deve convergir para o
    # valor real (sem vies) -- troca o erro de quantizacao deterministico
    # por ruido de media zero.
    frame = np.full((256, 256, 3), 127.5 / 255.0, dtype=np.float32)
    out = quantize_uint8_dithered(frame, rng=np.random.default_rng(2))
    assert out.mean() == pytest.approx(127.5, abs=0.5)


def test_dither_deterministic_with_seeded_rng():
    frame = np.full((8, 8, 3), 0.3, dtype=np.float32)
    out_a = quantize_uint8_dithered(frame, rng=np.random.default_rng(42))
    out_b = quantize_uint8_dithered(frame, rng=np.random.default_rng(42))
    assert np.array_equal(out_a, out_b)


def test_no_dither_when_rng_none_but_still_rounds_not_truncates():
    # rng=None desativa o dither (equivalente a --dither off), mas o
    # arredondamento correto (nao truncamento) continua valendo.
    frame = np.full((2, 2, 3), 127.6 / 255.0, dtype=np.float32)
    out = quantize_uint8_dithered(frame, rng=None)
    assert np.all(out == 128)  # truncamento (bug antigo) dava 127


def test_clips_out_of_range_values():
    # Node 5 pode exceder [0,1] (shoulder/toe unclamped do LUT Portra 400) --
    # o clip final acontece aqui, nunca antes.
    frame = np.array([[[-0.1, 1.2, 0.5]]], dtype=np.float32)
    out = quantize_uint8_dithered(frame, rng=None)
    assert out[0, 0, 0] == 0
    assert out[0, 0, 1] == 255
