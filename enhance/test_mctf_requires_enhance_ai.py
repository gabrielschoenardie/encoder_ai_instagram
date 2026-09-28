"""BDF15: --mctf on sem --enhance-ai on deve avisar em vez de ser ignorado em silêncio."""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import Reels_Encoder_v2_FINAL as R  # noqa: E402


def test_mctf_on_without_enhance_ai_warns():
    msg = R._mctf_ignored_reason("on", False)
    assert isinstance(msg, str)
    assert "--mctf" in msg
    assert "--enhance-ai" in msg


def test_no_warning_in_other_combinations():
    assert R._mctf_ignored_reason("on", True) is None
    assert R._mctf_ignored_reason("off", False) is None
    assert R._mctf_ignored_reason("off", True) is None
