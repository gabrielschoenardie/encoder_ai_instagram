# -*- coding: utf-8 -*-
"""Gera HollywoodCinema_Ultimate_v6.8_3.1-96IRE_...cube: a v6.7B com o teto
expandido para 96 IRE e o eixo warm-cool atenuado em 20%.

Duas etapas, nesta ordem. Expandir depois de atenuar reaqueceria as altas.

    # etapa 1 -- expansao de teto, lift ADITIVO guiado pela luma
    k  = (HIo - P) / (HIn - P)
    L  = 0.2126*R + 0.7152*G + 0.0722*B
    t  = clip((L - P) / (HIo - P), 0, None)
    L' = P + (HIn - P)*(k*t + (1-k)*t*t)   se L > P;   L' = L caso contrario
    E  = v + (L' - L)                      somado IGUALMENTE aos 3 canais

    # etapa 2 -- atenuacao warm 20%, um lado so
    F  = clip(E - FATOR*max((E - i).w, 0)*w, LO, HIn)

O lift e aditivo e igual nos tres canais -- nao e curva por canal. Uma curva
por canal expandiria croma junto com luma e deixaria nos mais quentes que a
propria v6.7B. Somando o mesmo escalar aos tres canais, toda diferenca de croma
(warm-cool e green-magenta) passa exata, e a etapa 2 recebe o mesmo `dw` que
receberia da v6.7B crua -- o lift tem projecao zero no eixo warm-cool.

A quadratica tem g(0)=0, g(1)=1, g'(0)=k: derivada continua no pivo e
monotonica. O pivo 0.75 e o mais baixo com efeito exatamente zero abaixo dele e
espalha os +3.84 IRE por ~17 IRE de range; pivo alto concentra o ganho numa
rampa ingreme e banda em 8-bit.

O piso NAO muda: 0.031373, o mesmo da v6.7B.

A v6.7B nao tem desvio de white balance -- no eixo neutro (R=G=B) ela e
identidade em croma. O calor dela vem de assimetria por matiz: ela comprime o
azul saturado (ganho warm-cool medido 0.768) e empurra laranja/pele ~1%. Por
isso `colortemperature`/`colorbalance`/ganho por canal depois do `lut3d` estao
descartados: todos deslocam o cinza, e o requisito e justamente nao mexer na
temperatura do material sem LUT.

A correcao vive dentro do cube. Base ortonormal de oponentes de cor em RGB:

    acromatico   (1,1,1)/sqrt(3)   intacto
    warm-cool    (1,0,-1)/sqrt(2)  x (1 - FATOR) no lado quente
    green-magenta (-1,2,-1)/sqrt(6) intacto

Para cada no, com entrada `i` (a grade) e saida `o` (o cube ja expandido):

    delta = o - i
    dw    = delta . w
    out'  = o - FATOR * max(dw, 0) * w
    out'  = clip(out', LO, HI)

A atenuacao e unilateral. Em 17.831 dos 35.937 nos a v6.7B ja esfria (`dw <=
0`); atenuar tambem esse lado devolveria calor -- branco quente, vermelho e
azul de ceu sairiam mais quentes que a v6.7B, o oposto do pedido. Com
`max(dw, 0)` esses nos passam intactos, e a funcao e continua em `dw = 0`,
sem descontinuidade na LUT.

Os tres eixos sao mutuamente ortogonais: atenuar um nao vaza nos outros. Em
todo neutro `delta = 0`, logo `out' = o` -- e isso que preserva o requisito.

O clamp e para o envelope de saida (LO do cube FONTE, HI = TETO_NOVO), nao para
[0,1]. Reduzir o delta empurra a saida na direcao da entrada, e a entrada vai
ate 1.0; sem esse clamp um no claro e saturado estoura o teto e quebra a
conformidade Instagram8bit_TVRange. Com o teto em 0.96 nenhum no chega a ser
truncado -- o envelope sai da transformacao, nao do clip.

Validacao: tools/test_generate_hollywood_lut_cooler.py
"""

import argparse
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube"
OUT_PATH = REPO_ROOT / "HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube"

LUT_SIZE = 33
FATOR = 0.20
PIVO = 0.75
TETO_NOVO = 0.96
ENVELOPE_LO = 0.031373
ENVELOPE_HI = 0.921569
WARM_COOL = np.array([1.0, 0.0, -1.0]) / np.sqrt(2.0)
LUMA_BT709 = np.array([0.2126, 0.7152, 0.0722])

HEADER = """\
TITLE "Hollywood Cinema Ultimate v6.8 3.1-96IRE_Instagram8bit_TVRange - Neutral Shadows - Warm 80%"
LUT_3D_SIZE {size}"""


def read_cube(path: Path, size: int) -> np.ndarray:
    """Le a tabela do .cube na ordem do arquivo (red-fastest, k = r + g*N + b*N^2)."""
    rows = []
    declared = None
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("TITLE"):
            continue
        if line.startswith("LUT_3D_SIZE"):
            declared = int(line.split()[1])
            continue
        if line.startswith("LUT_3D"):
            continue
        rows.append([float(v) for v in line.split()])
    if declared != size:
        raise ValueError(f"{path.name}: LUT_3D_SIZE {declared}, esperado {size}")
    if len(rows) != size**3:
        raise ValueError(f"{path.name}: {len(rows)} linhas de dados, esperado {size**3}")
    return np.array(rows, dtype=np.float64)


def identity_grid(size: int) -> np.ndarray:
    """Grade de entrada na mesma ordem red-fastest da tabela lida."""
    steps = np.linspace(0.0, 1.0, size)
    grid = np.empty((size**3, 3), dtype=np.float64)
    for b in range(size):
        for g in range(size):
            for r in range(size):
                grid[r + g * size + b * size**2] = (steps[r], steps[g], steps[b])
    return grid


def expand_highlights(out: np.ndarray, pivo: float, hi_old: float, hi_new: float) -> np.ndarray:
    """Etapa 1: lift aditivo guiado pela luma, igual nos tres canais, acima do pivo."""
    luma = out @ LUMA_BT709
    k = (hi_old - pivo) / (hi_new - pivo)
    t = np.clip((luma - pivo) / (hi_old - pivo), 0.0, None)
    curva = pivo + (hi_new - pivo) * (k * t + (1.0 - k) * t * t)
    alvo = np.where(luma > pivo, curva, luma)
    return out + (alvo - luma)[:, None]


def cool_warm_axis(out: np.ndarray, grid: np.ndarray, fator: float, lo: float, hi: float):
    """Atenua a projecao quente de (out - grid) no eixo warm-cool e clampa no envelope."""
    delta = out - grid
    projection = np.maximum(delta @ WARM_COOL, 0.0)
    cooled = out - fator * projection[:, None] * WARM_COOL[None, :]
    clamped = np.clip(cooled, lo, hi)
    touched = int(np.any(cooled != clamped, axis=1).sum())
    return clamped, touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fator", type=float, default=FATOR)
    parser.add_argument("--pivo", type=float, default=PIVO)
    parser.add_argument("--teto", type=float, default=TETO_NOVO)
    args = parser.parse_args()

    src = read_cube(SRC_PATH, LUT_SIZE)
    lo, hi = float(src.min()), float(src.max())
    assert lo == ENVELOPE_LO, f"envelope LO {lo!r} != {ENVELOPE_LO!r}"
    assert hi == ENVELOPE_HI, f"envelope HI {hi!r} != {ENVELOPE_HI!r}"

    grid = identity_grid(LUT_SIZE)
    expanded = expand_highlights(src, args.pivo, hi, args.teto)
    cooled, touched = cool_warm_axis(expanded, grid, args.fator, lo, args.teto)

    lines = [HEADER.format(size=LUT_SIZE)]
    for r, g, b in cooled:
        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\r\n")

    print(
        f"OK: {OUT_PATH.name} ({LUT_SIZE}^3 = {LUT_SIZE**3} pontos, "
        f"fator={args.fator}, pivo={args.pivo}, teto={args.teto})"
    )
    print(
        f"    envelope: LO={cooled.min():.6f} HI={cooled.max():.6f} | nos no clamp: {touched}"
    )


if __name__ == "__main__":
    main()
