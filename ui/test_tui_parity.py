import hashlib
import queue
import subprocess

import pytest

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from enhance.test_classic_golden import SCENARIOS, run_classic


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _streamhash(path):
    r = subprocess.run(
        [RE.FFMPEG, "-v", "error", "-i", str(path), "-map", "0", "-c", "copy",
         "-f", "streamhash", "-"],
        capture_output=True, text=True, check=True,
    )
    return r.stdout


def _same_output(a, b):
    if _sha(a) == _sha(b):
        print("PARITY-DECIDED-BY: sha")
        return True
    print("PARITY-DECIDED-BY: streamhash")
    return _streamhash(a) == _streamhash(b)


@pytest.mark.timeout(600)
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_reporter_path_matches_classic_argv_and_output(tmp_path, monkeypatch, scenario):
    (tmp_path / "c").mkdir()
    (tmp_path / "t").mkdir()
    classic = run_classic(tmp_path / "c", monkeypatch, scenario)
    tui = run_classic(tmp_path / "t", monkeypatch, scenario,
                      reporter=R.QueueReporter(queue.Queue()))
    assert tui["argv"] == classic["argv"]
    assert _same_output(tui["output"], classic["output"])
