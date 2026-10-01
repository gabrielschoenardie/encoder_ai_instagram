import queue

import pytest

import reporter as R
from enhance.test_classic_golden import run_classic


def _events(tmp_path, monkeypatch, scenario):
    q = queue.Queue()
    run_classic(tmp_path, monkeypatch, scenario, reporter=R.QueueReporter(q))
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _stages(events):
    return [(e.name, e.substep) for e in events if isinstance(e, R.Stage)]


EXPECTED = {
    "native_crf": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.QC, None), (R.DONE, None)],
    "native_2pass": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.BETWEEN_PASSES, "pass1_log"), (R.PASS, "2"),
        (R.QC, None), (R.DONE, None)],
}


@pytest.mark.timeout(300)
@pytest.mark.parametrize("scenario", ["native_crf", "native_2pass"])
def test_native_stage_order(tmp_path, monkeypatch, scenario):
    assert _stages(_events(tmp_path, monkeypatch, scenario)) == EXPECTED[scenario]


@pytest.mark.timeout(300)
def test_native_2pass_payload_events(tmp_path, monkeypatch):
    ev = _events(tmp_path, monkeypatch, "native_2pass")
    kinds = [type(e).__name__ for e in ev]
    assert kinds.index("Hardware") < kinds.index("Probe") < kinds.index("EncodeParams")
    passes = [(e.index, e.total, e.label, e.phase) for e in ev if isinstance(e, R.Pass)]
    assert passes == [(1, 2, "Pass 1", "start"), (1, 2, "Pass 1", "end"),
                      (2, 2, "Pass 2", "start"), (2, 2, "Pass 2", "end")]
    probe = next(e for e in ev if isinstance(e, R.Probe))
    assert (probe.width, probe.height, probe.fps) == (90, 160, 30)
    params = next(e for e in ev if isinstance(e, R.EncodeParams))
    assert params.vbv_key == "ultra_short" and params.mode == "2pass"
    assert any(isinstance(e, R.Progress) for e in ev)
    assert any(isinstance(e, R.FfmpegLine) for e in ev)
    assert isinstance(ev[-1], R.Done)


@pytest.mark.timeout(300)
def test_native_reporter_mode_prints_no_hud(tmp_path, monkeypatch):
    q = queue.Queue()
    got = run_classic(tmp_path, monkeypatch, "native_crf", reporter=R.QueueReporter(q))
    assert not any("ENCODING" in line for line in got["console"])


EXPECTED.update({
    "cineon_crf": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.FINALIZING, "remux"), (R.QC, None), (R.DONE, None)],
    "cineon_2pass": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.BETWEEN_PASSES, "pass1_log"), (R.PASS, "2"),
        (R.FINALIZING, "remux"), (R.QC, None), (R.DONE, None)],
})


@pytest.mark.timeout(300)
@pytest.mark.parametrize("scenario", ["cineon_crf", "cineon_2pass"])
def test_cineon_stage_order(tmp_path, monkeypatch, scenario):
    assert _stages(_events(tmp_path, monkeypatch, scenario)) == EXPECTED[scenario]


@pytest.mark.timeout(300)
def test_cineon_2pass_payload_events(tmp_path, monkeypatch):
    ev = _events(tmp_path, monkeypatch, "cineon_2pass")
    kinds = [type(e).__name__ for e in ev]
    assert kinds.index("Probe") < kinds.index("Hardware") < kinds.index("EncodeParams")
    passes = [(e.index, e.total, e.label, e.phase) for e in ev if isinstance(e, R.Pass)]
    assert passes == [(1, 2, "Pass 1", "start"), (1, 2, "Pass 1", "end"),
                      (2, 2, "Pass 2", "start"), (2, 2, "Pass 2", "end")]
    assert any(isinstance(e, R.Progress) for e in ev)
    assert isinstance(ev[-1], R.Done)
