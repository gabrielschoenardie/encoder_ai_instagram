# -*- coding: utf-8 -*-
"""Propriedades do cube derivado HollywoodCinema ...-W80 (eixo warm-cool a 80%).

Testes sobre o arquivo .cube gerado por tools/generate_hollywood_lut_cooler.py,
nao sobre pixels de video. O que precisa ficar provado:

- o eixo neutro nao se move (delta cromatico zero -> saida identica ao fonte),
  que e o requisito de nao mudar a temperatura do material sem LUT;
- a atenuacao vive so no eixo warm-cool: green-magenta e luma nao vazam;
- o envelope 1.5 IRE / TV range do fonte continua intacto apos o clamp;
- a atenuacao e unilateral: nenhum no fica mais quente que a v6.7B, e onde a
  v6.7B ja esfriava (dw <= 0) a saida e byte a byte a do fonte.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube"
OUT_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube"
GENERATOR = Path(__file__).resolve().parent / "generate_hollywood_lut_cooler.py"

LUT_SIZE = 33
DATA_LINES = LUT_SIZE**3
LO = 0.031373
HI = 0.921569


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


def test_neutral_axis_identical_to_source():
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    for k in range(LUT_SIZE):
        idx = k + k * LUT_SIZE + k * LUT_SIZE**2
        assert _fmt(out[idx]) == _fmt(src[idx])


def test_envelope_preserved():
    out = _table(OUT_PATH)
    assert out.min() == LO
    assert out.max() == HI


def test_warm_cool_gain_attenuated():
    grid = _grid()
    out = _table(OUT_PATH)
    mask = _saturated_mask(grid)
    gain = _gain(_warm_cool(grid)[mask], _warm_cool(out)[mask])
    assert abs(gain - 0.790588) <= 0.002


def test_green_magenta_and_luma_unchanged():
    grid = _grid()
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    mask = _saturated_mask(grid)

    gm = _gain(_green_magenta(grid)[mask], _green_magenta(out)[mask])
    assert abs(gm - 0.7146) <= 0.001

    luma_src = _gain(_luma(grid)[mask], _luma(src)[mask])
    luma_out = _gain(_luma(grid)[mask], _luma(out)[mask])
    assert abs(luma_out - luma_src) <= 0.001


def test_structure():
    text = OUT_PATH.read_text(encoding="ascii")
    assert "LUT_3D_SIZE 33" in text.splitlines()

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
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    violations = int((_warm_cool(out) > _warm_cool(src) + 1e-9).sum())
    assert violations == 0


def test_cooling_nodes_identical_to_source():
    grid = _grid()
    src = _table(SRC_PATH)
    out = _table(OUT_PATH)
    mask = _warm_projection(src, grid) <= 0.0
    assert mask.sum() > 0
    assert np.abs(out[mask] - src[mask]).max() <= 1e-9
