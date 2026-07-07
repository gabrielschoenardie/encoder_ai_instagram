# -*- coding: utf-8 -*-
"""log_encoding_cineon / log_decoding_cineon exigem colour-science.

Regressao coberta: o fallback manual (usado quando colour-science nao esta
instalada) tinha a formula errada -- `log10(1.0*0.9+0.1)*0.2932+0.0928`
mapeava branco linear (1.0) para o proprio black_code (0.0928), ou seja,
branco virava preto. O decode inverso correspondente tambem nao era o
inverso correto (gamma=0.6 sem subtrair offset/dividir por gain). Como
colour-science e dependencia obrigatoria do pipeline Cineon (requirements.txt,
secao "DEPENDENCIAS DO PIPELINE CINEON"), o fallback quebrado foi removido:
sem colour-science, as funcoes falham alto (RuntimeError) em vez de
silenciosamente produzir cor errada.
"""

import numpy as np
import pytest

colour = pytest.importorskip("colour")

import cineon_pipeline as cp


def test_log_encoding_cineon_matches_colour_science_reference():
    lin = np.linspace(0.0, 2.0, 50, dtype=np.float32)
    result = cp.log_encoding_cineon(lin)
    expected = np.clip(
        colour.models.log_encoding_Cineon(np.clip(lin, 0.0, None)), 0.0, 1.0
    ).astype(np.float32)
    assert np.allclose(result, expected, atol=1e-6)


def test_log_decoding_cineon_is_true_inverse_of_encoding():
    lin = np.linspace(0.01, 1.0, 50, dtype=np.float32)
    encoded = cp.log_encoding_cineon(lin)
    decoded = cp.log_decoding_cineon(encoded)
    assert np.allclose(decoded, lin, atol=1e-4)


def test_white_encodes_near_cineon_white_reference_not_black():
    # Regressao direta do bug: branco linear (1.0) NAO pode virar black_code.
    encoded = cp.log_encoding_cineon(np.array([1.0], dtype=np.float32))[0]
    assert encoded == pytest.approx(0.6697, abs=1e-3)


def test_log_encoding_cineon_raises_without_colour_science(monkeypatch):
    monkeypatch.setattr(cp, "COLOUR_AVAILABLE", False)
    with pytest.raises(RuntimeError):
        cp.log_encoding_cineon(np.array([1.0], dtype=np.float32))


def test_log_decoding_cineon_raises_without_colour_science(monkeypatch):
    monkeypatch.setattr(cp, "COLOUR_AVAILABLE", False)
    with pytest.raises(RuntimeError):
        cp.log_decoding_cineon(np.array([0.6697], dtype=np.float32))
