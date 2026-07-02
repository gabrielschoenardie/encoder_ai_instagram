import os

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    tomllib = None

import version

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")


def _pyproject():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)


def test_name_and_dynamic_version():
    data = _pyproject()
    proj = data["project"]
    assert proj["name"] == "reels-encoder-ai"
    assert "version" in proj.get("dynamic", [])
    assert data["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "version.__version__"


def test_entry_point_target_importable():
    data = _pyproject()
    assert data["project"]["scripts"]["reels-encoder"] == "Reels_Encoder_v2_FINAL:main"
    import importlib

    mod = importlib.import_module("Reels_Encoder_v2_FINAL")
    assert callable(getattr(mod, "main"))


def test_scipy_declared():
    deps = _pyproject()["project"]["dependencies"]
    assert any(d.replace(" ", "").lower().startswith("scipy") for d in deps)


def test_data_files_include_luts():
    df = _pyproject()["tool"]["setuptools"]["data-files"]["share/reels-encoder"]
    assert any(f.endswith(".cube") for f in df)


def test_find_data_file_resolves_lut():
    import Reels_Encoder_v2_FINAL as E

    p = E._find_data_file("FilmLook_Portra400_SkinPriority_D65.cube")
    assert p.endswith(".cube")
    assert os.path.isfile(p)
