"""Testes de guarda: README e --help não citam versões/algoritmo removidos (BD8)."""
import importlib
import os
import re

_FORBIDDEN = re.compile(r"v6\.6|v6\.7|bt2390|[Bb]lue-noise")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name: str) -> str:
    with open(os.path.join(_ROOT, name), encoding="utf-8") as f:
        return f.read()


def test_readme_has_no_forbidden_strings():
    text = _read("README.md")
    assert not _FORBIDDEN.search(text)


def test_cli_help_has_no_forbidden_strings():
    engine = importlib.import_module("Reels_Encoder_v2_FINAL")
    help_text = engine.build_parser().format_help()
    assert not _FORBIDDEN.search(help_text)


def test_readme_contains_current_lut_version():
    engine = importlib.import_module("Reels_Encoder_v2_FINAL")
    text = _read("README.md")
    assert engine._HOLLYWOOD_LUT_VERSION in text
