"""BFF3: o certificado de entrega deve gravar enhance_ai/mctf efetivos, não os
crus de `args` — sem listar como "on" o que o motor descartou."""
import argparse
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import Reels_Encoder_v2_FINAL as R  # noqa: E402


def test_enhance_off_zeroes_enhance_ai_and_mctf():
    args = argparse.Namespace(enhance="off", enhance_ai="on", mctf="on")
    settings = R._report_settings(args)
    assert settings["enhance_ai"] == "off"
    assert settings["mctf"] == "off"


def test_enhance_ai_off_zeroes_mctf_only():
    args = argparse.Namespace(enhance="on", enhance_ai="off", mctf="on")
    settings = R._report_settings(args)
    assert settings["enhance_ai"] == "off"
    assert settings["mctf"] == "off"


def test_all_on_stays_unchanged():
    args = argparse.Namespace(enhance="on", enhance_ai="on", mctf="on")
    settings = R._report_settings(args)
    assert settings["enhance_ai"] == "on"
    assert settings["mctf"] == "on"


def test_missing_keys_stay_absent():
    args = argparse.Namespace(enhance="off")
    settings = R._report_settings(args)
    assert "enhance_ai" not in settings
    assert "mctf" not in settings
