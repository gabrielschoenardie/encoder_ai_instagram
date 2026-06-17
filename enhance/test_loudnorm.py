"""
test_loudnorm.py
================
Tests for the EBU R128 two-pass loudnorm audio pipeline in
Reels_Encoder_v2_FINAL.py.

Covers the audit fixes:
  - offset (target_offset) passed back into Pass 2
  - True Peak target hardened to -1.5 dBTP for Instagram/YouTube
  - dual_mono correction for mono sources
  - multichannel (>2) downmix to stereo INSIDE the filter chain, so
    measurement (Pass 1) and normalization (Pass 2) act on the same
    layout that is actually delivered.

All tests exercise pure string builders — no ffmpeg subprocess required.

Run:
    python -m pytest enhance/test_loudnorm.py -v
"""

from __future__ import annotations

import os
import sys

# ── Path setup: import the root encoder module ────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() == "enhance" else _HERE
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import Reels_Encoder_v2_FINAL as R  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _stats(**overrides) -> dict:
    base = {
        "input_i": "-27.61",
        "input_tp": "-9.05",
        "input_lra": "8.40",
        "input_thresh": "-38.10",
        "target_offset": "0.49",
    }
    base.update(overrides)
    return base


def _assert_no_malformed_af(af: str) -> None:
    assert af, "filter string must be non-empty"
    assert "::" not in af, f"double colon in: {af!r}"
    assert " " not in af, f"unquoted space in: {af!r}"
    assert not af.endswith(":"), f"trailing colon in: {af!r}"
    assert not af.endswith(","), f"trailing comma in: {af!r}"


# ══════════════════════════════════════════════════════════════════════════════
# TARGET CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLoudnormTargets:

    def test_instagram_true_peak_is_minus_1_5(self):
        """Instagram TP hardened to -1.5 dBTP (headroom for IG's AAC transcode)."""
        assert R.LOUDNORM_TARGETS["instagram"]["TP"] == -1.5

    def test_youtube_true_peak_is_minus_1_5(self):
        assert R.LOUDNORM_TARGETS["youtube"]["TP"] == -1.5

    def test_instagram_integrated_stays_minus_14(self):
        """-14 LUFS must NOT change — it's what stops IG re-normalizing."""
        assert R.LOUDNORM_TARGETS["instagram"]["I"] == -14

    def test_broadcast_true_peak_unchanged(self):
        """Broadcast stays at the EBU R128 -1 dBTP ceiling."""
        assert R.LOUDNORM_TARGETS["broadcast"]["TP"] == -1


# ══════════════════════════════════════════════════════════════════════════════
# PASS 2 — build_loudnorm_filter
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildLoudnormFilter:

    def test_emits_target_values(self):
        af = R.build_loudnorm_filter(_stats(), target="instagram", channels=2)
        assert "I=-14" in af and "TP=-1.5" in af and "LRA=11" in af

    def test_emits_measured_values(self):
        af = R.build_loudnorm_filter(_stats(), channels=2)
        assert "measured_I=-27.61" in af
        assert "measured_TP=-9.05" in af
        assert "measured_LRA=8.40" in af
        assert "measured_thresh=-38.10" in af

    def test_linear_mode(self):
        af = R.build_loudnorm_filter(_stats(), channels=2)
        assert "linear=true" in af

    def test_emits_offset_when_target_offset_present(self):
        """target_offset from Pass 1 must be fed back as offset= (precision)."""
        af = R.build_loudnorm_filter(_stats(target_offset="0.49"), channels=2)
        assert ":offset=0.49" in af, f"expected offset passback: {af}"

    def test_omits_offset_when_target_offset_absent(self):
        stats = _stats()
        del stats["target_offset"]
        af = R.build_loudnorm_filter(stats, channels=2)
        assert "offset=" not in af, f"offset must be omitted when absent: {af}"

    def test_dual_mono_for_mono_source(self):
        af = R.build_loudnorm_filter(_stats(), channels=1)
        assert "dual_mono=true" in af, f"mono needs dual_mono: {af}"

    def test_no_dual_mono_for_stereo(self):
        af = R.build_loudnorm_filter(_stats(), channels=2)
        assert "dual_mono" not in af, f"stereo must not set dual_mono: {af}"

    def test_downmix_prefix_for_multichannel(self):
        """5.1+ must downmix to stereo BEFORE loudnorm, in the filter chain."""
        af = R.build_loudnorm_filter(_stats(), channels=6)
        assert af.startswith("aformat=channel_layouts=stereo,"), af
        assert "loudnorm=" in af

    def test_no_prefix_for_stereo(self):
        af = R.build_loudnorm_filter(_stats(), channels=2)
        assert not af.startswith("aformat"), af
        assert af.startswith("loudnorm="), af

    def test_channels_read_from_stats_when_param_none(self):
        """When channels not passed, fall back to stats['_channels']."""
        af = R.build_loudnorm_filter(_stats(_channels=1), channels=None)
        assert "dual_mono=true" in af

    def test_defaults_to_stereo_when_no_channel_info(self):
        af = R.build_loudnorm_filter(_stats(), channels=None)
        assert "dual_mono" not in af
        assert not af.startswith("aformat")

    def test_no_malformed_syntax(self):
        for ch in (1, 2, 6):
            _assert_no_malformed_af(R.build_loudnorm_filter(_stats(), channels=ch))


# ══════════════════════════════════════════════════════════════════════════════
# PASS 1 — build_loudnorm_measure_filter
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildLoudnormMeasureFilter:

    def test_uses_json_print_format(self):
        af = R.build_loudnorm_measure_filter(target="instagram", channels=2)
        assert "print_format=json" in af

    def test_emits_target_values(self):
        af = R.build_loudnorm_measure_filter(channels=2)
        assert "I=-14" in af and "TP=-1.5" in af and "LRA=11" in af

    def test_no_measured_values(self):
        """Pass 1 measures — it must NOT carry measured_* values."""
        af = R.build_loudnorm_measure_filter(channels=2)
        assert "measured_" not in af

    def test_dual_mono_for_mono(self):
        af = R.build_loudnorm_measure_filter(channels=1)
        assert "dual_mono=true" in af

    def test_downmix_prefix_for_multichannel(self):
        """Measurement must act on the SAME stereo downmix Pass 2 delivers."""
        af = R.build_loudnorm_measure_filter(channels=6)
        assert af.startswith("aformat=channel_layouts=stereo,"), af
        assert "loudnorm=" in af

    def test_stereo_is_plain(self):
        af = R.build_loudnorm_measure_filter(channels=2)
        assert af.startswith("loudnorm=")
        assert "dual_mono" not in af

    def test_no_malformed_syntax(self):
        for ch in (1, 2, 6):
            _assert_no_malformed_af(R.build_loudnorm_measure_filter(channels=ch))


# ══════════════════════════════════════════════════════════════════════════════
# probe_audio_channels (I/O — graceful failure path only)
# ══════════════════════════════════════════════════════════════════════════════

class TestProbeAudioChannels:

    def test_nonexistent_file_returns_stereo_default(self):
        """A missing/unprobeable file must degrade to safe stereo (2)."""
        assert R.probe_audio_channels("does_not_exist_xyz.mp4") == 2


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO OUTPUT ARGS — _audio_output_args (stereo-output regression guard)
# ══════════════════════════════════════════════════════════════════════════════

def _adjacent(args: list, flag: str, value: str) -> bool:
    """True if `flag` is immediately followed by `value` in the arg list."""
    return any(args[i] == flag and args[i + 1] == value for i in range(len(args) - 1))


class TestAudioOutputArgs:
    """Final output MUST always be stereo — Instagram rejects 5.1.

    The stereo guarantee lives in the encode command assembly (`-ac 2`); this
    pins it so a future edit can't silently drop it from any pipeline.
    """

    def test_returns_list(self):
        assert isinstance(R._audio_output_args(), list)

    def test_always_forces_stereo(self):
        """`-ac 2` must be present (and adjacent) with or without a filter."""
        assert _adjacent(R._audio_output_args(), "-ac", "2")
        assert _adjacent(R._audio_output_args("loudnorm=I=-14"), "-ac", "2")

    def test_aac_lc_48k_192k(self):
        args = R._audio_output_args()
        assert _adjacent(args, "-c:a", "aac")
        assert _adjacent(args, "-b:a", "192k")
        assert _adjacent(args, "-ar", "48000")
        assert _adjacent(args, "-profile:a", "aac_low")

    def test_audio_filter_prepended_as_af(self):
        args = R._audio_output_args("loudnorm=I=-14:TP=-1.5")
        assert _adjacent(args, "-af", "loudnorm=I=-14:TP=-1.5")
        # -af must come before the codec args
        assert args.index("-af") < args.index("-c:a")

    def test_no_af_when_no_filter(self):
        assert "-af" not in R._audio_output_args()
        assert "-af" not in R._audio_output_args(None)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
