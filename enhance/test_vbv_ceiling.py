"""BDF9 — teto de ingestão do Instagram (Regra de Ouro 6) no VBV e no 2-pass.

Média ≤ 12000 kbps e maxrate ≤ 15000 kbps. Testes puros, sem FFmpeg.
"""
from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() == "enhance" else _HERE
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import Reels_Encoder_v2_FINAL as R  # noqa: E402

MAX_AVG = 12000
MAX_PEAK = 15000

TIER_DURATIONS = [10.0, 15.0, 25.0, 40.0, 55.0, 80.0, 120.0]


def test_ultra_short_tier_at_15s_uses_skill_profile():
    p = R.get_vbv_preset(15.0)
    assert (p["target"], p["maxrate"], p["bufsize"]) == (10000, 11200, 15000)


def test_short_tier_just_above_15s_untouched():
    p = R.get_vbv_preset(15.1)
    assert (p["target"], p["maxrate"], p["bufsize"]) == (9800, 11000, 14850)


@pytest.mark.parametrize("duration", TIER_DURATIONS)
@pytest.mark.parametrize("mean_q", [10.0, 17.0, 19.0, 22.0, 30.0])
@pytest.mark.parametrize("log_found", [True, False])
def test_2pass_respects_ingest_ceiling(duration, mean_q, log_found):
    base = R.get_vbv_preset(duration)["target"]
    stats = {"mean_q": mean_q, "log_found": log_found}
    _, avg, maxrate, _ = R._adaptive_2pass_x264_params(base, 30, stats, duration, 4, 40)
    assert avg <= MAX_AVG
    assert maxrate <= MAX_PEAK


def test_2pass_clamps_average_even_when_base_is_at_ceiling():
    stats = {"mean_q": 10.0, "log_found": True}
    params, avg, maxrate, bufsize = R._adaptive_2pass_x264_params(12000, 30, stats, 10.0, 4, 40)
    assert avg == 12000
    assert maxrate == 13200
    assert bufsize == int(13200 * 1.35)
    assert f"vbv-maxrate={maxrate}" in params
    assert f"vbv-bufsize={bufsize}" in params


def test_2pass_clamps_maxrate_to_peak_ceiling():
    stats = {"mean_q": 30.0, "log_found": False}
    _, avg, maxrate, bufsize = R._adaptive_2pass_x264_params(20000, 30, stats, 10.0, 4, 40)
    assert avg == MAX_AVG
    assert maxrate == 13200
    assert maxrate <= MAX_PEAK
    assert bufsize == int(maxrate * 1.35)
