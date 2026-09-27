"""Conversão CFR do Cineon (BDF3): `_cfr_resample` com a semântica do filtro
`fps` do FFmpeg (`round=near`). Frames falsos, sem FFmpeg nem PyAV."""
import importlib
from fractions import Fraction

R = importlib.import_module("Reels_Encoder_v2_FINAL")


class FakeFrame:
    def __init__(self, idx, pts, time_base, duration):
        self.idx = idx
        self.pts = pts
        self.time_base = time_base
        self.duration = duration


def _frames(n, fps, time_base=Fraction(1, 90000), jitter=None):
    fps = Fraction(fps)
    dur = int(round(1 / fps / time_base))
    out = []
    for k in range(n):
        t = Fraction(k) / fps
        if jitter is not None:
            t += jitter(k)
        out.append(FakeFrame(k, int(round(t / time_base)), time_base, dur))
    return out


def _resample(frames, out_fps, in_fps):
    return [(f.idx, rep) for f, rep in R._cfr_resample(frames, out_fps, Fraction(in_fps))]


def test_60_to_30_picks_even_frames():
    out = _resample(_frames(120, 60), 30, 60)
    assert len(out) == 60
    assert [idx for idx, _ in out] == list(range(0, 120, 2))
    assert not any(rep for _, rep in out)


def test_24_to_30_repeats_twelve_frames_spread_out():
    out = _resample(_frames(48, 24), 30, 24)
    assert len(out) == 60
    repeats = [i for i, (_, rep) in enumerate(out) if rep]
    assert len(repeats) == 12
    assert sorted({idx for idx, _ in out}) == list(range(48))
    for i in repeats:
        assert out[i][0] == out[i - 1][0]
    gaps = [b - a for a, b in zip(repeats, repeats[1:])]
    assert min(gaps) >= 4 and max(gaps) <= 6


def test_30_to_30_identity():
    out = _resample(_frames(60, 30), 30, 30)
    assert out == [(k, False) for k in range(60)]


def test_ntsc_to_30_repeats_about_once_per_thousand():
    n = 3000
    out = _resample(_frames(n, Fraction(30000, 1001), time_base=Fraction(1, 30000)), 30, Fraction(30000, 1001))
    repeats = [i for i, (_, rep) in enumerate(out) if rep]
    assert len(out) == round(n * Fraction(1001, 30000) * 30)
    assert len(repeats) == 3
    assert sorted({idx for idx, _ in out}) == list(range(n))


def test_vfr_jitter_does_not_drop_or_duplicate():
    jitter = lambda k: Fraction((-1) ** k * 2, 1000)  # noqa: E731
    frames = _frames(60, 30, jitter=jitter)
    out = _resample(frames, 30, 30)
    assert out == [(k, False) for k in range(60)]


def test_total_slots_equal_duration_times_fps():
    for fps_in, n, fps_out in ((60, 150, 30), (24, 60, 30), (25, 100, 30), (50, 100, 24)):
        out = _resample(_frames(n, fps_in), fps_out, fps_in)
        assert len(out) == round(Fraction(n, fps_in) * fps_out), (fps_in, fps_out)


def test_missing_pts_and_duration_fall_back_to_input_fps():
    frames = _frames(60, 60)
    for f in frames:
        f.pts = None
        f.duration = 0
    out = _resample(frames, 30, 60)
    assert [idx for idx, _ in out] == list(range(0, 60, 2))


def test_streaming_consumes_lazily():
    consumed = []

    def gen():
        for f in _frames(120, 60):
            consumed.append(f.idx)
            yield f

    it = R._cfr_resample(gen(), 30, Fraction(60))
    first, rep = next(it)
    assert first.idx == 0 and rep is False
    assert consumed == [0, 1]
