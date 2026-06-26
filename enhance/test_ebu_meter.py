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


def test_parse_summary_ignores_per_frame_progress_lines():
    # Regression: ebur128 prints per-frame progress lines that -nostats does NOT
    # suppress. At t~0 (silent intro) they read 'I: -70.0 LUFS ... LRA: 0.0 LU'.
    # The parser must read the final Summary block, not the first progress line.
    stderr_with_progress = (
        "[Parsed_ebur128_0 @ 0x1] t: 0.1  TARGET:-23 LUFS  M:-120.7 S:-120.7     "
        "I: -70.0 LUFS     LRA:  0.0 LU  FTPK: -25.4 -26.0 dBFS  TPK: -25.4 -26.0 dBFS\n"
        "[Parsed_ebur128_0 @ 0x1] t: 0.2  TARGET:-23 LUFS  M:-120.7 S:-120.7     "
        "I: -70.0 LUFS     LRA:  0.0 LU  FTPK: -12.4 -13.0 dBFS  TPK: -12.4 -13.0 dBFS\n"
        + _SUMMARY_OK
    )
    stats = E.parse_ebur128_summary(stderr_with_progress)
    assert stats is not None
    assert stats["I"] == -14.0   # from Summary, NOT the -70.0 progress lines
    assert stats["LRA"] == 7.5   # from Summary, NOT the 0.0 progress lines
    assert stats["TP"] == -1.5


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


# ══════════════════════════════════════════════════════════════════════════════
# window geometry (side-by-side layout)
# ══════════════════════════════════════════════════════════════════════════════

def test_ffplay_args_geometry_flags():
    geom = {"width": 700, "height": 525, "left": 100, "top": 50}
    args = E.build_ffplay_meter_args("a.mp4", target_i=-14, title="t", geometry=geom)
    # geometry flags appear before -i, with the right values
    assert args[args.index("-x") + 1] == "700"
    assert args[args.index("-y") + 1] == "525"
    assert args[args.index("-left") + 1] == "100"
    assert args[args.index("-top") + 1] == "50"
    assert args.index("-x") < args.index("-i")
    # graph still immediately follows -i
    assert "ebur128=video=1" in args[args.index("-i") + 1]


def test_ffplay_args_no_geometry_is_unchanged():
    base = E.build_ffplay_meter_args("a.mp4", target_i=-14, title="t")
    assert "-x" not in base and "-left" not in base


def test_layout_two_windows_side_by_side_no_overlap():
    layout = E.compute_side_by_side_layout(n=2, screen=(1920, 1080))
    assert len(layout) == 2
    left, right = layout
    # second window starts to the right of the first (no overlap)
    assert right["left"] >= left["left"] + left["width"]
    # same size and same vertical position (true side-by-side)
    assert left["width"] == right["width"]
    assert left["top"] == right["top"]
    # both fit on screen
    assert left["left"] >= 0
    assert right["left"] + right["width"] <= 1920


def test_layout_centered_horizontally():
    layout = E.compute_side_by_side_layout(n=2, screen=(1920, 1080))
    left, right = layout
    total_w = (right["left"] + right["width"]) - left["left"]
    margin_l = left["left"]
    margin_r = 1920 - (right["left"] + right["width"])
    # left/right margins within 1px of each other → centered
    assert abs(margin_l - margin_r) <= 1


def test_layout_single_window():
    layout = E.compute_side_by_side_layout(n=1, screen=(1920, 1080))
    assert len(layout) == 1
    assert layout[0]["left"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# build_delivery_checks (pure, rich-free)
# ══════════════════════════════════════════════════════════════════════════════

def test_build_delivery_checks_conforming_all_pass():
    checks = E.build_delivery_checks(
        aI=-14.0, aTP=-1.5, a_codec="aac", a_rate="48000",
        tgt_i=-14, tgt_tp=-1.5,
    )
    labels = [c[0] for c in checks]
    assert labels == ["Loudness", "True Peak", "Codec", "Sample Rate"]
    assert all(passed is True for (_, _, passed) in checks)
    # value strings carry units / raw values
    by_label = {c[0]: c for c in checks}
    assert by_label["Loudness"][1] == "-14.0 LUFS"
    assert by_label["True Peak"][1] == "-1.5 dBTP"
    assert by_label["Codec"][1] == "aac"
    assert by_label["Sample Rate"][1] == "48000"


def test_build_delivery_checks_off_target_loudness_fails():
    checks = E.build_delivery_checks(
        aI=-9.0, aTP=-1.5, a_codec="aac", a_rate="48000",
        tgt_i=-14, tgt_tp=-1.5,
    )
    by_label = {c[0]: c for c in checks}
    assert by_label["Loudness"][2] is False
    assert by_label["True Peak"][2] is True


def test_build_delivery_checks_hot_true_peak_fails():
    checks = E.build_delivery_checks(
        aI=-14.0, aTP=-0.5, a_codec="aac", a_rate="48000",
        tgt_i=-14, tgt_tp=-1.5,
    )
    by_label = {c[0]: c for c in checks}
    assert by_label["True Peak"][2] is False
    assert by_label["Loudness"][2] is True


def test_build_delivery_checks_all_none():
    checks = E.build_delivery_checks(
        aI=None, aTP=None, a_codec=None, a_rate=None,
        tgt_i=-14, tgt_tp=-1.5,
    )
    assert all(passed is None for (_, _, passed) in checks)
    # None metrics show '—' without a stray unit
    by_label = {c[0]: c for c in checks}
    assert by_label["Loudness"][1] == "—"
    assert by_label["True Peak"][1] == "—"
    assert by_label["Codec"][1] == "—"
    assert by_label["Sample Rate"][1] == "—"
