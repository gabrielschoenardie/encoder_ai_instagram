# -*- coding: utf-8 -*-
"""Gera FilmLook_Portra400_SkinPriority_D65.cube (identity baseline, 33^3).

Curva baked (separavel por canal):
    f(x) = oetf_BT709_estendida(log_decoding_Cineon(x))   -- SEM clamp

Por que sem clamp: o white reference Cineon (x = 0.6696) nao cai em ponto da
grade 33 (0.6696 * 32 = 21.43). Bakear com `clip(decode(x), 0, 1)` cria um knee
duro entre os pontos 21 e 22, e a corda da interpolacao trilinear subestima a
curva concava em ate -2.93% (-7.5 codes 8-bit no pico) -> highlights abafados.
Sem o clamp, o shoulder continua suave acima de 1.0 (ate ~3.45 em x=1.0) e a
interpolacao cruza 1.0 exatamente no white reference; o clip final acontece
depois da LUT, na conversao uint8 do encoder (np.clip(frame*255, 0, 255)).

O mesmo vale para o toe: a OETF estendida e linear (4.5*L) tambem para L < 0,
entao o segmento abaixo do black code Cineon (x = 0.0928) interpola limpo.

Inputs acima de 0.6696 nunca ocorrem no pipeline (Node 3 tone-mapping garante
linear <= 1.0), mas os valores > 1.0 baked ali sao necessarios para o ponto de
grade adjacente ao white reference interpolar certo.

Validacao: enhance/test_cineon_lut.py (round-trip Node 3 -> LUT sub-code 8-bit).
"""

from pathlib import Path

import colour
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "FilmLook_Portra400_SkinPriority_D65.cube"
LUT_SIZE = 33

HEADER = """\
TITLE "Portra400_Identity_Baseline"
LUT_3D_SIZE {size}
LUT_3D_INPUT_RANGE 0.0 1.0

# Portra 400 Film Emulation - IDENTITY (Rec.709 OETF)
# Input:  Cineon Film Log (0.0-1.0)
# Output: Rec.709 OETF / D65 - UNCLIPPED (shoulder > 1.0, toe < 0.0)
# Identity baseline: output = input (transparent) no range util lin 0.0-1.0
#
# Bake sem clamp: o clip [0,1] acontece DEPOIS da interpolacao, na conversao
# uint8 do encoder. Bakear com clamp cria knee duro no white reference Cineon
# (x=0.6696, off-grid) e a interpolacao trilinear abafa highlights em -7.5
# codes 8-bit no pico.
# Gerado por: tools/generate_portra400_baseline_lut.py
"""


def oetf_bt709_extended(linear: np.ndarray) -> np.ndarray:
    """OETF Rec.709 estendida: linear (4.5*L) abaixo de 0.018 inclusive para
    L < 0, e power segment acima — sem clamp em 1.0."""
    L = np.asarray(linear, dtype=np.float64)
    return np.where(L < 0.018, 4.5 * L, 1.099 * np.power(np.maximum(L, 0.018), 0.45) - 0.099)


def bake_curve(size: int) -> np.ndarray:
    xs = np.linspace(0.0, 1.0, size)
    lin = colour.models.log_decoding_Cineon(xs)  # sem clip: <0 no toe, >1 no shoulder
    return oetf_bt709_extended(lin)


def main() -> None:
    f = bake_curve(LUT_SIZE)
    lines = [HEADER.format(size=LUT_SIZE)]
    # Ordem Adobe .cube: R varia mais rapido, depois G, depois B.
    for b in range(LUT_SIZE):
        for g in range(LUT_SIZE):
            for r in range(LUT_SIZE):
                lines.append(f"{f[r]:.6f} {f[g]:.6f} {f[b]:.6f}")
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    print(f"OK: {OUT_PATH.name} ({LUT_SIZE}^3 = {LUT_SIZE**3} pontos)")
    print(f"    range: min={f.min():.6f} (toe) max={f.max():.6f} (shoulder x=1.0)")


if __name__ == "__main__":
    main()
