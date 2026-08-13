"""Gera capturas REAIS da UI do Reels Encoder como SVG para o README.

Headless e re-executável: renderiza os componentes Rich num Console gravador e
salva SVGs em docs/assets/. Rode: python tools/gen_readme_assets.py
"""

from __future__ import annotations

import glob
import os
import sys
import time
from collections import deque

# Permite rodar como `python tools/gen_readme_assets.py` (repo root no sys.path).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import version
from ebu_meter import (
    _human_size,
    build_delivery_checks,
    build_report_payload,
    build_video_checks,
)
from ui import components as C
from ui.config import EncodeConfig
from ui.dashboard import make_dashboard
from ui.report import render_html
from ui.theme import get_console

_TITLE = "Reels Encoder"

# Timestamp fixo: mantém o certificado gerado byte-a-byte igual entre execuções
# (senão cada regeneração sujaria o diff do asset).
_CERT_GENERATED_AT = "2026-08-13T14:10:55"
# Não há mídia real no repositório, então os.path.getsize() falha e o tamanho sai
# None; fixamos um valor plausível para a seção ARQUIVO ficar completa.
_CERT_SIZE_BYTES = 19293798
# Chromium do Playwright (opcional): usado só para a captura PNG do certificado.
_PW_BROWSERS = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "/opt/pw-browsers"


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


def _certificate_payload():
    """Payload de exemplo realista do certificado de entrega (puro, offline)."""
    video_info = {
        "container": "mov,mp4,m4a",
        "codec": "h264",
        "profile": "High",
        "level": 40,
        "width": 1080,
        "height": 1920,
        "pix_fmt": "yuv420p",
        "color_primaries": "bt709",
        "color_transfer": "bt709",
        "color_space": "bt709",
        "fps": 30.0,
    }
    checks = build_video_checks(video_info) + build_delivery_checks(
        -14.1, -1.8, "aac", "48000", -14.0, -1.5
    )
    payload = build_report_payload(
        source_file="/Volumes/Media/Ensaio_Praia_4K_iPhone.MOV",
        output_file="/Volumes/Media/Ensaio_Praia_4K_iPhone_Hollywood_CRF18.mp4",
        checks=checks,
        before={"I": -9.7, "TP": 0.8, "LRA": 6.2},
        after={"I": -14.1, "TP": -1.8, "LRA": 7.1},
        b_codec="aac",
        b_rate="44100",
        a_codec="aac",
        a_rate="48000",
        targets={"I": -14, "TP": -1.5, "LRA": 11},
        app_version=version.__version__,
        video_info=video_info,
        settings={
            "mode": "crf",
            "fit": "contain",
            "fps": "30",
            "scale": "auto",
            "lut": "on",
            "loudnorm": "on",
            "hdr": "auto",
            "tonemap": "mobius",
            "cineon_pipeline": "off",
            "enhance": "on",
            "enhance_ai": "on",
            "mctf": "on",
            "dither": "auto",
            "performance": "balanced",
        },
        encode_seconds=252.3,
        generated_at=_CERT_GENERATED_AT,
    )
    # O output de exemplo não existe em disco: build_report_payload devolve
    # size_bytes/size_human None e a seção ARQUIVO perderia o tamanho.
    payload["output"]["size_bytes"] = _CERT_SIZE_BYTES
    payload["output"]["size_human"] = _human_size(_CERT_SIZE_BYTES)
    return payload


def _chromium_executable():
    """Caminho do chromium do Playwright, se houver um instalado; senão None."""
    matches = sorted(glob.glob(os.path.join(_PW_BROWSERS, "chromium-*", "chrome-linux", "chrome")))
    return matches[-1] if matches else None


def _shot_certificate(html_path, png_path):
    """Captura opcional do certificado em PNG; nunca derruba o gerador."""
    try:
        from playwright.sync_api import sync_playwright

        exe = _chromium_executable()
        if not exe:
            raise RuntimeError("chromium não encontrado")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=exe, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1000, "height": 1400},
                                    device_scale_factor=2)
            page.goto("file://" + os.path.abspath(html_path))
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        return True
    except Exception as exc:
        print(f"[gen_readme_assets] certificado.png: pulado "
              f"(playwright/chromium indisponível: {exc}) — HTML gerado")
        return False


def _gen_certificate(outdir):
    html_path = os.path.join(outdir, "certificado.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(render_html(_certificate_payload()))
    _shot_certificate(html_path, os.path.join(outdir, "certificado.png"))


def main(outdir="docs/assets"):
    os.makedirs(outdir, exist_ok=True)
    dash_stats = None
    for label, fn in (
        ("banner", _gen_banner),
        ("preview", _gen_preview),
        ("dashboard", _gen_dashboard),
        ("seal", _gen_seal),
        ("certificado", _gen_certificate),
    ):
        try:
            result = fn(outdir)
            if label == "dashboard":
                dash_stats = result
        except Exception as exc:  # best-effort: um asset falho não derruba os outros
            print(f"[gen_readme_assets] ERRO ao gerar {label}: {exc}",
                  file=sys.stderr)
    if dash_stats:
        print(f"[gen_readme_assets] dashboard: fps={dash_stats[0]:.1f} "
              f"speed={dash_stats[1]:.2f}x")
    print(f"[gen_readme_assets] SVGs em {outdir}/")


if __name__ == "__main__":
    main()
