"""Testes do certificado de entrega (ui/report.py).

Puros e offline: o payload vem de ``ebu_meter.build_report_payload`` (sem ffmpeg)
e a renderização é HTML/JSON em memória ou em ``tmp_path``.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import ebu_meter as E  # noqa: E402
from ui.report import (  # noqa: E402
    render_html,
    render_json,
    render_seal_fragment,
    write_report,
)

_CHECKS = [
    ("Container", "MP4", True),
    ("Video", "H.264 High@4.0", True),
    ("Resolution", "1080x1920", True),
    ("Color", "bt2020", False),
    ("FPS", "—", None),
    ("Loudness", "-14.1 LUFS", True),
]


def _payload(**over):
    kw = dict(
        source_file="/in/férias & cia.mp4",
        output_file="/out/ferias_Hollywood_CRF18.mp4",
        checks=_CHECKS,
        before={"I": -9.7, "TP": 0.8, "LRA": 6.2},
        after={"I": -14.1, "TP": -1.8, "LRA": 7.1},
        b_codec="aac", b_rate="44100", a_codec="aac", a_rate="48000",
        targets={"I": -14, "TP": -1.5, "LRA": 11},
        app_version="2.1.0",
        video_info={
            "container": "mov,mp4,m4a", "codec": "h264", "profile": "High",
            "width": 1080, "height": 1920, "pix_fmt": "yuv420p",
            "color_primaries": "bt709", "fps": 30.0,
        },
        settings={"mode": "crf", "fit": "contain", "enhance_ai": "on"},
        encode_seconds=252.3,
    )
    kw.update(over)
    return E.build_report_payload(**kw)


def test_payload_schema():
    p = _payload()
    for key in ("app", "generated_at", "source", "output", "video", "audio",
                "targets", "checks", "summary", "settings", "encode"):
        assert key in p, f"payload missing key: {key}"
    # 4 True / 1 None / 1 False → not ready
    assert p["summary"] == {"passed": 4, "warnings": 1, "failed": 1, "ready": False}
    assert p["output"]["filename"] == "ferias_Hollywood_CRF18.mp4"
    assert p["encode"]["duration_human"] == "4m 12s"


def test_render_json_roundtrips():
    p = _payload()
    assert json.loads(render_json(p)) == p


def test_render_html_contains_key_facts():
    p = _payload()
    doc = render_html(p)
    assert doc.startswith("<!DOCTYPE html>")
    assert "CERTIFICADO DE ENTREGA" in doc
    assert "2.1.0" in doc
    assert "ferias_Hollywood_CRF18.mp4" in doc
    assert "#d4af37" in doc                     # gold, from ui.theme.PALETTE
    assert "AUDITORIA EBU R128" in doc
    assert "CONFORMIDADE" in doc
    assert "REVISAR ENTREGA" in doc             # one check failed
    assert "-14.1" in doc                       # measured loudness


def test_render_html_ready_verdict():
    p = _payload(checks=[("Codec", "aac", True), ("FPS", "30 fps", True)])
    doc = render_html(p)
    assert "DELIVERY READY" in doc
    assert "REVISAR ENTREGA" not in doc


def test_render_html_escapes_values():
    p = _payload(source_file="/in/a&b.mp4", output_file="/out/a&b<x>.mp4")
    doc = render_html(p)
    assert "a&amp;b&lt;x&gt;.mp4" in doc
    assert "a&b<x>.mp4" not in doc


def test_write_report_creates_both_files(tmp_path):
    p = _payload()
    written = write_report(p, str(tmp_path / "video.mp4"))
    assert len(written) == 2
    assert written[0].endswith(".qc.html")
    assert written[1].endswith(".qc.json")
    html_path = tmp_path / "video.qc.html"
    json_path = tmp_path / "video.qc.json"
    assert html_path.exists() and json_path.exists()
    assert html_path.stat().st_size > 512
    assert json.loads(json_path.read_text(encoding="utf-8")) == p


def test_write_report_outdir(tmp_path):
    p = _payload()
    written = write_report(p, "/somewhere/else/video.mp4", outdir=str(tmp_path))
    assert written == [str(tmp_path / "video.qc.html"), str(tmp_path / "video.qc.json")]


def test_write_report_never_raises():
    assert write_report(_payload(), "/nonexistent-dir-xyz/out.mp4") == []
    assert write_report(None, "/nonexistent-dir-xyz/out.mp4") == []


def test_seal_fragment_renders():
    frag = render_seal_fragment([("Loudness", "-14.1 LUFS", True), ("Codec", "aac", True)])
    assert isinstance(frag, str)
    assert frag                       # ui.components is importable in this repo
    assert "#" in frag                # carries the palette hexes from the export


def test_seal_fragment_accepts_payload_dicts():
    frag = render_seal_fragment(_payload()["checks"])
    assert isinstance(frag, str) and frag


def test_seal_fragment_does_not_write_to_stdout(capsys):
    """O card do selo é gravado em buffer — nada vaza para o terminal do encode."""
    render_seal_fragment(_CHECKS)
    assert capsys.readouterr().out == ""
