# -*- coding: utf-8 -*-
"""Propriedades do cube derivado HollywoodCinema v6.8 (teto 96 IRE + warm 80%).

Testes sobre o arquivo .cube gerado por tools/generate_hollywood_lut_cooler.py,
nao sobre pixels de video. O que precisa ficar provado:

- o eixo neutro continua neutro (R=G=B em todo degrau) e chega a 96.00 IRE;
- o piso da v6.7B nao se move: 0.031373, tolerancia zero;
- a expansao de teto e um lift ADITIVO igual nos tres canais: green-magenta e
  toda diferenca de croma passam intactos, so a luma sobe;
- abaixo do pivo 0.75 a etapa 1 tem efeito exatamente zero (INV 9);
- a curva de expansao e estritamente monotonica no eixo neutro (INV 10);
- nenhum no fica mais quente que a v6.7B (INV 11).
"""

import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube"
OUT_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube"
GENERATOR = Path(__file__).resolve().parent / "generate_hollywood_lut_cooler.py"

sys.path.insert(0, str(GENERATOR.parent))
from generate_hollywood_lut_cooler import (  # noqa: E402
    cool_warm_axis,
    expand_highlights,
)

LUT_SIZE = 33
DATA_LINES = LUT_SIZE**3
LO = 0.031373
HI = 0.96
HI_V67B = 0.921569
PIVO = 0.75
FATOR = 0.20
TITLE = (
    'TITLE "Hollywood Cinema Ultimate v6.8 3.1-96IRE_Instagram8bit_TVRange'
    ' - Neutral Shadows - Warm 80%"'
)
# meio-ulp de %.6f em dois canais: uma diferenca de croma so e real acima disso
ROUND_EPS = 2e-6


def _data_lines(path):
    lines = []
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("TITLE") or line.startswith("LUT_3D"):
            continue
        lines.append(line)
    return lines


def _table(path):
    return np.array([[float(v) for v in line.split()] for line in _data_lines(path)])


def _grid():
    steps = np.arange(LUT_SIZE) / (LUT_SIZE - 1)
    grid = np.empty((DATA_LINES, 3))
    for bi in range(LUT_SIZE):
        for gi in range(LUT_SIZE):
            for ri in range(LUT_SIZE):
                grid[ri + gi * LUT_SIZE + bi * LUT_SIZE**2] = (steps[ri], steps[gi], steps[bi])
    return grid


def _neutral_indices():
    return [k + k * LUT_SIZE + k * LUT_SIZE**2 for k in range(LUT_SIZE)]


def _fmt(triplet):
    return "%.6f %.6f %.6f" % tuple(triplet)


def _gain(x, y):
    """Ajuste linear pela origem: coeficiente de y sobre x."""
    return float(np.dot(x, y) / np.dot(x, x))


def _warm_cool(t):
    return t[:, 0] - t[:, 2]


def _green_magenta(t):
    return 2.0 * t[:, 1] - t[:, 0] - t[:, 2]


def _luma(t):
    return 0.2126 * t[:, 0] + 0.7152 * t[:, 1] + 0.0722 * t[:, 2]


def _saturated_mask(grid):
    return (grid.max(axis=1) - grid.min(axis=1)) > 0.05


def _warm_projection(src, grid):
    """dw = (src - grid) . w, com w = (1,0,-1)/sqrt(2)."""
    delta = src - grid
    return (delta[:, 0] - delta[:, 2]) / np.sqrt(2.0)


def test_neutral_axis_stays_neutral_and_reaches_ceiling():
    out = _table(OUT_PATH)
    for idx in _neutral_indices():
        r, g, b = out[idx]
        assert "%.6f" % r == "%.6f" % g == "%.6f" % b
    assert "%.6f" % out[_neutral_indices()[-1]][0] == "%.6f" % HI


def test_envelope_preserved():
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    assert out.min() == src.min() == LO
    assert out.max() == HI

    # nenhum no e truncado pelo clamp: o envelope sai da transformacao, nao do clip
    expandido = expand_highlights(src, PIVO, HI_V67B, HI)
    _, touched = cool_warm_axis(expandido, _grid(), FATOR, LO, HI)
    assert touched == 0


def test_warm_cool_gain_attenuated():
    grid = _grid()
    out = _table(OUT_PATH)
    mask = _saturated_mask(grid)
    gain = _gain(_warm_cool(grid)[mask], _warm_cool(out)[mask])
    assert abs(gain - 0.790686) <= 1e-5


def test_green_magenta_preserved_and_luma_expanded():
    grid = _grid()
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    mask = _saturated_mask(grid)

    # lift aditivo: green-magenta passa intacto no ganho e no e a no
    gm = _gain(_green_magenta(grid)[mask], _green_magenta(out)[mask])
    assert abs(gm - 0.714632) <= 1e-6
    assert np.abs(_green_magenta(out) - _green_magenta(src)).max() <= ROUND_EPS

    luma_src = _gain(_luma(grid)[mask], _luma(src)[mask])
    luma_out = _gain(_luma(grid)[mask], _luma(out)[mask])
    assert luma_out > luma_src


def test_structure():
    raw = OUT_PATH.read_bytes()
    text = OUT_PATH.read_text(encoding="ascii")
    assert TITLE in text.splitlines()
    assert "LUT_3D_SIZE 33" in text.splitlines()
    assert raw.count(b"\r\n") == DATA_LINES + 2
    assert raw.count(b"\n") == raw.count(b"\r\n")

    lines = _data_lines(OUT_PATH)
    assert len(lines) == DATA_LINES
    for line in lines:
        values = line.split()
        assert len(values) == 3
        for value in values:
            float(value)


def test_generator_is_deterministic():
    first = subprocess.run(
        [sys.executable, str(GENERATOR)], cwd=str(REPO_ROOT), capture_output=True
    )
    assert first.returncode == 0, first.stderr.decode(errors="replace")
    first_bytes = OUT_PATH.read_bytes()

    second = subprocess.run(
        [sys.executable, str(GENERATOR)], cwd=str(REPO_ROOT), capture_output=True
    )
    assert second.returncode == 0, second.stderr.decode(errors="replace")
    assert OUT_PATH.read_bytes() == first_bytes


def test_no_node_warmer_than_source():
    """INV 11: nenhum no mais quente que a v6.7B -- 0, nao relativo a base expandida."""
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    violations = int((_warm_cool(out) > _warm_cool(src) + ROUND_EPS).sum())
    assert violations == 0


def test_cooling_nodes_receive_only_the_additive_lift():
    grid = _grid()
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    mask = _warm_projection(src, grid) <= 0.0
    assert mask.sum() > 0

    delta = out[mask] - src[mask]
    assert np.abs(delta[:, 0] - delta[:, 1]).max() <= ROUND_EPS
    assert np.abs(delta[:, 1] - delta[:, 2]).max() <= ROUND_EPS
    assert delta.min() >= -ROUND_EPS

    below = _luma(src[mask]) <= PIVO
    assert below.sum() > 0
    assert np.abs(delta[below]).max() == 0.0

    # logo acima do pivo o lift e menor que meio-ulp de %.6f e nao aparece no
    # arquivo; o que precisa aparecer e o topo, que sobe o teto inteiro
    above = ~below
    assert above.sum() > 0
    assert delta[above].min() >= 0.0
    assert abs(delta[above].max() - (HI - HI_V67B)) <= 5e-7


def test_nodes_below_pivot_untouched_by_expansion():
    """INV 9: com L <= 0.75 a etapa 1 nao move nada -- so a etapa 2 age."""
    grid = _grid()
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    somente_etapa2, _ = cool_warm_axis(src, grid, FATOR, LO, HI)

    below = _luma(src) <= PIVO
    assert below.sum() > 0
    for idx in np.nonzero(below)[0]:
        assert _fmt(out[idx]) == _fmt(somente_etapa2[idx])

    above = ~below
    assert above.sum() > 0
    lift = out[above] - somente_etapa2[above]
    assert lift.min() >= -5e-7
    assert abs(lift.max() - (HI - HI_V67B)) <= 5e-7


def test_expansion_curve_strictly_monotonic_on_neutral_axis():
    """INV 10."""
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    idx = _neutral_indices()
    neutro_src = src[idx][:, 0]
    neutro_out = out[idx][:, 0]

    assert np.all(np.diff(neutro_out) > 0.0)

    lift = neutro_out - neutro_src
    abaixo = neutro_src <= PIVO
    assert np.abs(lift[abaixo]).max() == 0.0
    acima = ~abaixo
    assert acima.sum() >= 2
    assert np.all(np.diff(lift[acima]) > 0.0)
    assert lift[acima].min() > 0.0
