# -*- coding: utf-8 -*-
"""Soft-knee do tone mapping DaVinci (Node 3) precisa realmente comprimir.

Regressao coberta: apply_tone_mapping_davinci tinha `knee = 1.0` hardcoded,
zerando o termo `(1.0 - knee)` da compressao exponencial -- a curva
colapsava para um hard clip `min(x, 1.0)` independente do parametro
`adaptation`. Um soft-knee de verdade precisa de uma faixa de compressao
(knee < teto) onde `adaptation` de fato controla a suavidade -- exatamente
como apply_gamut_mapping_saturation_compression (aprovada na auditoria) ja
faz com `knee=0.9 < max_saturation=1.0`.
"""

import numpy as np
import pytest

from cineon_pipeline import apply_tone_mapping_davinci


def test_below_knee_is_linear_passthrough():
    linear = np.array([[[0.1, 0.3, 0.5]]], dtype=np.float32)
    out = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=9.0)
    assert np.allclose(out, linear, atol=1e-6)


def test_highlights_above_knee_are_not_hard_clipped_to_knee_value():
    # Bug antigo: qualquer valor > 1.0 virava exatamente `knee` (=1.0) na
    # pratica -- ou seja, hard clip. Com soft-knee real, valores diferentes
    # acima do knee devem produzir saidas diferentes (curva, nao platô).
    linear = np.array([[[1.2, 2.0, 4.0]]], dtype=np.float32)
    out = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=9.0)
    assert len(np.unique(out)) == 3, "highlights diferentes colapsaram no mesmo valor (hard clip)"


def test_adaptation_parameter_actually_changes_output():
    # Bug antigo: `adaptation` so multiplicava um termo zerado por
    # (1.0 - knee) == 0 -- mudar adaptation nao alterava o resultado.
    linear = np.array([[[2.0, 2.0, 2.0]]], dtype=np.float32)
    out_soft = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=1.0)
    out_hard = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=20.0)
    assert not np.allclose(out_soft, out_hard)


def test_output_stays_within_display_range():
    linear = np.array([[[0.0, 1.0, 50.0]]], dtype=np.float32)
    out = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=9.0)
    assert np.all(out >= 0.0) and np.all(out <= 1.0)


def test_extreme_highlights_asymptote_to_ceiling_not_hard_clip():
    # Valores bem acima do knee devem se aproximar assintoticamente de 1.0,
    # nunca serem clipados abruptamente nele.
    linear = np.array([[[100.0, 100.0, 100.0]]], dtype=np.float32)
    out = apply_tone_mapping_davinci(linear, max_output_nits=100.0, adaptation=9.0)
    assert out[0, 0, 0] < 1.0
    assert out[0, 0, 0] == pytest.approx(1.0, abs=0.05)
