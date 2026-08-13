"""Delivery certificate — renders the post-encode QC payload as HTML + JSON.

Pure: takes the payload dict from ``ebu_meter.build_report_payload`` and produces
a self-contained dark-theme HTML document (reusing the Premiere palette from
``ui.theme``) plus a machine-readable JSON sidecar. No network, no templating
dependency, never raises into the encode path.
"""

from __future__ import annotations

import html
import json
import os

from ui.theme import PALETTE

__all__ = ["render_seal_fragment", "render_html", "render_json", "write_report"]

# PT-BR labels for the settings block; unknown keys fall back to a prettified key.
_SETTING_LABELS = {
    "mode": "Modo",
    "fit": "Enquadramento",
    "fps": "FPS",
    "scale": "Escala",
    "lut": "LUT",
    "loudnorm": "Loudnorm",
    "hdr": "HDR",
    "tonemap": "Tone Mapping",
    "cineon_pipeline": "Cineon",
    "enhance": "Enhance",
    "enhance_ai": "IA",
    "mctf": "MCTF",
    "dither": "Dither",
    "performance": "Performance",
}


# ──────────────────────────────────────────────────────────────────────────────
# Small pure formatters
# ──────────────────────────────────────────────────────────────────────────────
def _e(value) -> str:
    """HTML-escaped string form of any value ("—" when empty/None)."""
    if value is None or value == "":
        return "—"
    return html.escape(str(value))


def _num(value, suffix: str = "") -> str:
    """One-decimal number, escaped, with optional suffix ("—" when unavailable)."""
    try:
        return html.escape(f"{float(value):.1f}{suffix}")
    except (TypeError, ValueError):
        return "—"


def _as_tuples(checks) -> list:
    """Accept both the tuple shape and the payload dict shape for checks."""
    out = []
    for c in list(checks or []):
        if isinstance(c, dict):
            out.append((c.get("label"), c.get("value"), c.get("passed")))
        else:
            try:
                out.append((c[0], c[1], c[2]))
            except Exception:
                continue
    return out


_COLOR_LABELS = {
    "bt709": "BT.709",
    "bt2020": "BT.2020",
    "bt2020nc": "BT.2020",
    "smpte2084": "SMPTE ST 2084 (PQ)",
    "arib-std-b67": "HLG",
    "bt470bg": "BT.470BG",
    "smpte170m": "SMPTE 170M",
}


def _fmt_color(value) -> str:
    """Probe colour tag in display form ("bt709" → "BT.709"); "—" when empty."""
    if value is None or value == "":
        return "—"
    key = str(value).strip().lower()
    return _COLOR_LABELS.get(key, str(value).upper())


def _bit_depth(pix_fmt) -> str:
    """Bit depth inferred from pix_fmt, as a display string."""
    if not pix_fmt:
        return "—"
    p = str(pix_fmt).lower()
    return "10-bit" if "10" in p else "12-bit" if "12" in p else "8-bit"


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def render_seal_fragment(checks, ready=None) -> str:
    """Render the REAL delivery seal card as an embeddable HTML fragment.

    Uses a recording Rich console writing to an in-memory buffer (so nothing is
    echoed to the terminal) — the certificate carries the exact same card the
    terminal shows. Returns "" if rich/ui is unavailable.
    """
    try:
        import io

        from ui.components import delivery_seal
        from ui.theme import get_console

        console = get_console(record=True, width=100, file=io.StringIO())
        console.print(delivery_seal(_as_tuples(checks), ready=ready, console=console))
        return console.export_html(clear=False, inline_styles=True, code_format="{code}")
    except Exception:
        return ""


def render_json(payload: dict) -> str:
    """The payload as a pretty, UTF-8-friendly JSON document."""
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _css() -> str:
    """Compact self-contained stylesheet built from the Premiere palette."""
    p = PALETTE
    return f"""
:root {{
  --ink:{p['ink']}; --text:{p['text']}; --muted:{p['muted']}; --indigo:{p['indigo']};
  --violet:{p['violet']}; --gold:{p['gold']}; --green:{p['green']}; --red:{p['red']};
  --amber:{p['amber']}; --cyan:{p['cyan']};
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:40px 20px; background:var(--ink); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:14px; line-height:1.6; }}
.wrap {{ max-width:860px; margin:0 auto; }}
.card {{ background:#191b23; border:1px solid #262936; border-radius:14px;
  padding:26px 30px; margin-bottom:22px; }}
.brand {{ font-size:13px; letter-spacing:.18em; text-transform:uppercase; font-weight:700;
  background:linear-gradient(90deg,var(--indigo),var(--violet));
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
h1 {{ font-size:30px; margin:10px 0 6px; letter-spacing:.06em; font-weight:700; }}
.stamp {{ color:var(--muted); font-size:12px; letter-spacing:.05em; }}
h2 {{ font-size:12px; letter-spacing:.2em; text-transform:uppercase; color:var(--cyan);
  margin:0 0 14px; font-weight:700; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); font-weight:600; padding:0 10px 8px 0; border-bottom:1px solid #262936; }}
td {{ padding:9px 10px 9px 0; border-bottom:1px solid #1f222c; }}
td.n, th.n {{ text-align:right; font-variant-numeric:tabular-nums;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
td.tgt {{ color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 26px; }}
.row {{ display:flex; justify-content:space-between; gap:14px; padding:7px 0;
  border-bottom:1px solid #1f222c; }}
.row .k {{ color:var(--muted); }}
.row .v {{ font-weight:600; text-align:right; }}
.ok {{ color:var(--green); }} .warn {{ color:var(--amber); }} .fail {{ color:var(--red); }}
.tally {{ margin-top:16px; font-size:12px; color:var(--muted); letter-spacing:.04em; }}
.tally b {{ font-weight:700; }}
pre.seal {{ margin:0; overflow-x:auto; line-height:1.15; font-size:13px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace; }}
.verdict {{ text-align:center; padding:20px; border-radius:14px; margin-bottom:14px;
  font-size:19px; font-weight:700; letter-spacing:.22em; }}
.verdict.ready {{ color:var(--gold); border:1px solid var(--gold); background:#201d10; }}
.verdict.review {{ color:var(--amber); border:1px solid var(--amber); background:#211a10; }}
footer {{ text-align:center; color:var(--muted); font-size:11px; letter-spacing:.08em; }}
""".strip()


def _audio_table(payload: dict) -> str:
    """The 'AUDITORIA EBU R128' before/after/target table."""
    audio = payload.get("audio") or {}
    b = audio.get("before") or {}
    a = audio.get("after") or {}
    t = payload.get("targets") or {}
    rows = [
        ("Integrated (LUFS-I)", _num(b.get("I")), _num(a.get("I")), _num(t.get("I"))),
        ("True Peak (dBTP)", _num(b.get("TP")), _num(a.get("TP")),
         "—" if t.get("TP") is None else "≤ " + _num(t.get("TP"))),
        ("Loudness Range (LU)", _num(b.get("LRA")), _num(a.get("LRA")),
         "—" if t.get("LRA") is None else "~" + _num(t.get("LRA"))),
        ("Codec", _e(b.get("codec")), _e(a.get("codec")), "AAC-LC"),
        ("Sample Rate", _e(b.get("sample_rate")), _e(a.get("sample_rate")), "48000"),
    ]
    body = "".join(
        f'<tr><td>{m}</td><td class="n">{bv}</td>'
        f'<td class="n">{av}</td><td class="n tgt">{tv}</td></tr>'
        for (m, bv, av, tv) in rows
    )
    return (
        '<section class="card"><h2>AUDITORIA EBU R128</h2><table>'
        '<tr><th>Métrica</th><th class="n">Antes</th>'
        '<th class="n">Depois</th><th class="n">Alvo</th></tr>'
        f"{body}</table></section>"
    )


def _checks_section(payload: dict) -> str:
    """The 'CONFORMIDADE' grid plus the pass/warn/fail tally."""
    cells = []
    for label, value, passed in _as_tuples(payload.get("checks")):
        cls, glyph = ("ok", "✓") if passed is True else \
            ("fail", "✗") if passed is False else ("warn", "⚠")
        cells.append(
            f'<div class="row"><span class="k">'
            f'<span class="{cls}">{glyph}</span> {_e(label)}</span>'
            f'<span class="v">{_e(value)}</span></div>'
        )
    s = payload.get("summary") or {}
    tally = (
        f'<div class="tally"><b class="ok">{s.get("passed", 0)} aprovados</b> · '
        f'<b class="warn">{s.get("warnings", 0)} avisos</b> · '
        f'<b class="fail">{s.get("failed", 0)} reprovados</b></div>'
    )
    return (
        '<section class="card"><h2>CONFORMIDADE</h2>'
        f'<div class="grid">{"".join(cells)}</div>{tally}</section>'
    )


def _kv_section(title: str, pairs) -> str:
    """A two-column label/value card; returns "" when there is nothing to show."""
    rows = "".join(
        f'<div class="row"><span class="k">{_e(k)}</span>'
        f'<span class="v">{v}</span></div>'
        for k, v in pairs
    )
    if not rows:
        return ""
    return f'<section class="card"><h2>{_e(title)}</h2><div class="grid">{rows}</div></section>'


def render_html(payload: dict) -> str:
    """A complete, self-contained HTML5 delivery certificate."""
    payload = payload or {}
    app = payload.get("app") or {}
    out = payload.get("output") or {}
    video = payload.get("video") or {}
    summary = payload.get("summary") or {}
    encode = payload.get("encode") or {}

    name = _e(app.get("name") or "Instagram Reels Encoder")
    version = str(app.get("version") or "")
    header_version = f" v{_e(version)}" if version else ""

    src = payload.get("source") or {}
    w, h = video.get("width"), video.get("height")
    fps = video.get("fps")
    file_pairs = [
        ("Origem", _e(src.get("filename"))),
        ("Master", _e(out.get("filename"))),
        ("Tamanho", _e(out.get("size_human"))),
        ("Resolução", f"{int(w)}x{int(h)}" if w and h else "—"),
        ("FPS", _num(fps) if fps is not None else "—"),
        ("Profundidade", _e(_bit_depth(video.get("pix_fmt")))),
        ("Cor", _e(_fmt_color(video.get("color_primaries")))),
    ]
    settings = payload.get("settings") or {}
    setting_pairs = [
        (_SETTING_LABELS.get(k, str(k).replace("_", " ").title()), _e(v))
        for k, v in settings.items()
    ]
    mode = settings.get("mode")
    encode_pairs = [
        ("Duração", _e(encode.get("duration_human"))),
        ("Modo", _e(str(mode).upper()) if mode else "—"),
        ("Concluído em", _e(payload.get("generated_at"))),
        ("Encoder", f"{name}{header_version}"),
    ]

    ready = bool(summary.get("ready"))
    verdict = (
        '<div class="verdict ready">★ DELIVERY READY ★</div>' if ready
        else '<div class="verdict review">⚠ REVISAR ENTREGA</div>'
    )
    seal = render_seal_fragment(payload.get("checks"), ready=summary.get("ready"))
    seal_block = f'<section class="card"><pre class="seal">{seal}</pre></section>' if seal else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Certificado de Entrega — {_e(out.get('filename'))}</title>
<style>{_css()}</style></head>
<body><div class="wrap">
<header class="card">
  <div class="brand">{name}{header_version}</div>
  <h1>CERTIFICADO DE ENTREGA</h1>
  <div class="stamp">{_e(payload.get('generated_at'))} · {_e(out.get('filename'))}</div>
</header>
{seal_block}
{_audio_table(payload)}
{_checks_section(payload)}
{_kv_section('ARQUIVO', file_pairs)}
{_kv_section('CONFIGURAÇÃO', setting_pairs)}
{_kv_section('ENCODE', encode_pairs)}
{verdict}
<footer>Gerado por {name}{header_version}</footer>
</div></body></html>
"""


def write_report(payload: dict, output_file: str, outdir=None) -> list:
    """Write ``<base>.qc.html`` + ``<base>.qc.json``; returns the paths written.

    HTML first. Never raises: any failure yields an empty list so the encode path
    is untouched.
    """
    try:
        base = os.path.splitext(output_file)[0]
        if outdir:
            base = os.path.join(outdir, os.path.basename(base))
        html_path, json_path = base + ".qc.html", base + ".qc.json"
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(render_html(payload))
        with open(json_path, "w", encoding="utf-8") as fh:
            fh.write(render_json(payload))
        return [html_path, json_path]
    except Exception:
        return []
