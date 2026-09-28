"""BFF1: resolver o --cineon-lut no ponto de uso, com fallback pela busca do
_find_data_file quando o valor for None ou um nome nu inexistente no CWD."""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import Reels_Encoder_v2_FINAL as R  # noqa: E402

_DEFAULT_LUT_NAME = "FilmLook_Portra400_SkinPriority_D65.cube"
_MODULE_DIR = os.path.dirname(os.path.abspath(R.__file__))


def test_none_resolves_via_find_data_file():
    resolved = R._resolve_cineon_lut(None)
    assert resolved == R._find_data_file(_DEFAULT_LUT_NAME)


def test_bare_name_existing_only_beside_module_from_other_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    resolved = R._resolve_cineon_lut(_DEFAULT_LUT_NAME)
    assert resolved == os.path.join(_MODULE_DIR, _DEFAULT_LUT_NAME)
    assert os.path.exists(resolved)


def test_absolute_existing_path_returned_unchanged(monkeypatch, tmp_path):
    lut_file = tmp_path / "custom.cube"
    lut_file.write_text("dummy")
    monkeypatch.chdir(tmp_path)
    resolved = R._resolve_cineon_lut(str(lut_file))
    assert resolved == str(lut_file)


def test_bare_name_only_in_cwd_without_module_homonym(monkeypatch, tmp_path):
    name = "bg1_only_cwd.cube"
    assert not os.path.exists(os.path.join(_MODULE_DIR, name))
    lut_file = tmp_path / name
    lut_file.write_text("dummy")
    monkeypatch.chdir(tmp_path)
    resolved = R._resolve_cineon_lut(name)
    assert resolved == name
    assert os.path.exists(resolved)


def test_path_with_missing_directory_left_unchanged(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    missing = os.path.join("no_such_dir", "whatever.cube")
    resolved = R._resolve_cineon_lut(missing)
    assert resolved == missing
