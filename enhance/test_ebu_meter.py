"""
test_ebu_meter.py
=================
Tests for the post-encode EBU R128 QC module (ebu_meter.py).

Exercises only the PURE builders/parsers — no ffmpeg/ffplay subprocess required,
matching the style of test_loudnorm.py.

Covers:
  - build_ebur128_measure_cmd: ffmpeg measure command shape
  - parse_ebur128_summary: parsing the ebur128 'Summary:' block, incl. malformed
    / silent (-inf) / partial inputs degrading to None
  - build_ffplay_meter_args: the ffplay lavfi filtergraph (ebur128=video=1) and
    path escaping (\\ and :)

Run:
    python -m pytest enhance/test_ebu_meter.py -v
"""

from __future__ import annotations

import os
import sys

# ── Path setup: import the root module ────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() == "enhance" else _HERE
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ebu_meter as E  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

_SUMMARY_OK = """\
[Parsed_ebur128_0 @ 0000020a] Summary:

  Integrated loudness:
    I:         -14.0 LUFS
    Threshold: -24.7 LUFS

  Loudness range:
    LRA:         7.5 LU
    Threshold: -34.6 LUFS
    LRA low:   -18.2 LUFS
    LRA high:  -10.7 LUFS

  True peak:
    Peak:       -1.5 dBFS
"""

_SUMMARY_SILENT = """\
[Parsed_ebur128_0 @ 0000020a] Summary:

  Integrated loudness:
    I:         -inf LUFS
    Threshold: -inf LUFS

  Loudness range:
    LRA:         0.0 LU

  True peak:
    Peak:       -inf dBFS
"""


# ══════════════════════════════════════════════════════════════════════════════
# build_ebur128_measure_cmd
# ══════════════════════════════════════════════════════════════════════════════

def test_measure_cmd_basic_shape():
    cmd = E.build_ebur128_measure_cmd("clip.mp4")
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd and "clip.mp4" in cmd
    # ebur128 with peak=true so True Peak appears in the summary
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "ebur128=peak=true"
    # null muxer, no encode
    assert cmd[-2:] == ["-f", "null"] or cmd[-3:] == ["-f", "null", "-"]


def test_measure_cmd_returns_list_of_str():
    cmd = E.build_ebur128_measure_cmd("a b/with space.mov")
    assert isinstance(cmd, list)
    assert all(isinstance(tok, str) for tok in cmd)
    assert "a b/with space.mov" in cmd  # path passed as a single argv token


# ══════════════════════════════════════════════════════════════════════════════
# parse_ebur128_summary
# ══════════════════════════════════════════════════════════════════════════════

def test_parse_summary_ok():
    stats = E.parse_ebur128_summary(_SUMMARY_OK)
    assert stats is not None
    assert stats["I"] == -14.0
    assert stats["LRA"] == 7.5
    assert stats["TP"] == -1.5


def test_parse_summary_picks_true_peak_not_threshold():
    # The 'Peak:' under 'True peak:' must be chosen, not a stray number.
    stats = E.parse_ebur128_summary(_SUMMARY_OK)
    assert stats["TP"] == -1.5


def test_parse_summary_silent_is_none():
    # -inf integrated → unusable measurement → None (graceful).
    assert E.parse_ebur128_summary(_SUMMARY_SILENT) is None


def test_parse_summary_garbage_is_none():
    assert E.parse_ebur128_summary("no summary here") is None
    assert E.parse_ebur128_summary("") is None


def test_parse_summary_missing_field_is_none():
    partial = "Summary:\n  Integrated loudness:\n    I:  -14.0 LUFS\n"
    # Missing LRA and True peak → cannot build a complete record → None.
    assert E.parse_ebur128_summary(partial) is None


# ══════════════════════════════════════════════════════════════════════════════
# build_ffplay_meter_args
# ══════════════════════════════════════════════════════════════════════════════

def test_ffplay_args_basic():
    args = E.build_ffplay_meter_args("clip.mp4", target_i=-14, title="DEPOIS")
    assert args[0] == "ffplay"
    assert "-f" in args and "lavfi" in args
    # window title threaded through
    wt = args.index("-window_title")
    assert args[wt + 1] == "DEPOIS"
    # the lavfi graph is the last argument after -i
    i_idx = args.index("-i")
    graph = args[i_idx + 1]
    assert "ebur128=video=1" in graph
    assert "meter=18" in graph
    assert "target=-14" in graph
    assert "amovie=" in graph
    assert graph.endswith("[out0][out1]")


def test_ffplay_args_path_escaping():
    # Windows-style path: backslashes doubled, colon escaped.
    args = E.build_ffplay_meter_args(r"C:\videos\my clip.mp4", target_i=-14, title="X")
    graph = args[args.index("-i") + 1]
    assert r"C\:\\videos\\my clip.mp4" in graph


def test_ffplay_args_target_float_formatting():
    args = E.build_ffplay_meter_args("a.mp4", target_i=-14.0, title="t")
    graph = args[args.index("-i") + 1]
    # -14.0 should render as target=-14 (no trailing .0 noise) or target=-14.0;
    # accept either but it must be present and parseable.
    assert "target=-14" in graph
