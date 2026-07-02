"""Gera capturas REAIS da UI do Reels Encoder como SVG para o README.

Headless e re-executável: renderiza os componentes Rich num Console gravador e
salva SVGs em docs/assets/. Rode: python tools/gen_readme_assets.py
"""

from __future__ import annotations

import os
import sys
import time
from collections import deque

# Permite rodar como `python tools/gen_readme_assets.py` (repo root no sys.path).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import version
from ui import components as C
from ui.config import EncodeConfig
from ui.dashboard import make_dashboard
from ui.theme import get_console
from ebu_meter import build_delivery_checks

_TITLE = "Reels Encoder"


def _save(console, outdir, name):
    console.save_svg(os.path.join(outdir, name), title=_TITLE)


def _gen_banner(outdir):
    con = get_console(record=True, width=100)
    con.print(
        C.banner(
            "REELS ENCODER",
            f"Premiere Workspace · UI interativa · v{version.__version__}",
        )
    )
    _save(con, outdir, "banner.svg")


def _gen_preview(outdir):
    con = get_console(record=True, width=100)
    con.print(
        C.settings_preview(
            EncodeConfig(input="ferias_praia.mp4"), src_dims=(1080, 1920)
        )
    )
    _save(con, outdir, "preview.svg")


def _gen_dashboard(outdir):
    con = get_console(record=True, width=100)
    log = deque(
        [
            "[libx264 @ 0x5583a0] frame I:36   Avg QP:18.42  size: 89123",
            "[libx264 @ 0x5583a0] frame P:1740 Avg QP:21.07  size: 24518",
            "[libx264 @ 0x5583a0] frame B:2544 Avg QP:23.91  size:  8102",
            "frame= 4320 fps= 72 q=23.0 size=   18432kB time=00:00:60.00 "
            "bitrate=2516.6kbits/s speed=1.2x",
            "[mux] writing trailer · vbv-maxrate=6000 buffer OK",
        ],
        maxlen=8,
    )
    d = make_dashboard(
        total_frames=7200,
        fps=60,
        source="ferias_praia.mp4",
        output="ferias_praia_Hollywood_CRF18.mp4",
        fit="contain",
        src_dims=(1080, 1920),
        log_sink=log,
        console=con,
    )
    # Retrocede o relógio interno ~60s para que fps/velocidade/elapsed saiam
    # plausíveis: df=4320 em dt=60s -> fps≈72, speed=72/60=1.2x, elapsed≈60s.
    now = time.time()
    d.start_time = now - 60.0
    d.last_time = now - 60.0
    d.last_frame = 0
    d.update_frame(4320)
    con.print(d.render())
    _save(con, outdir, "dashboard.svg")
    return d.fps, d.speed


def _gen_seal(outdir):
    con = get_console(record=True, width=100)
    checks = build_delivery_checks(-14.1, -1.8, "aac", 48000, -14.0, -1.5)
    con.print(C.delivery_seal(checks, ready=True))
    _save(con, outdir, "seal.svg")


def main(outdir="docs/assets"):
    os.makedirs(outdir, exist_ok=True)
    dash_stats = None
    for label, fn in (
        ("banner", _gen_banner),
        ("preview", _gen_preview),
        ("dashboard", _gen_dashboard),
        ("seal", _gen_seal),
    ):
        try:
            result = fn(outdir)
            if label == "dashboard":
                dash_stats = result
        except Exception as exc:  # best-effort: um asset falho não derruba os outros
            print(f"[gen_readme_assets] ERRO ao gerar {label}.svg: {exc}",
                  file=sys.stderr)
    if dash_stats:
        print(f"[gen_readme_assets] dashboard: fps={dash_stats[0]:.1f} "
              f"speed={dash_stats[1]:.2f}x")
    print(f"[gen_readme_assets] SVGs em {outdir}/")


if __name__ == "__main__":
    main()
