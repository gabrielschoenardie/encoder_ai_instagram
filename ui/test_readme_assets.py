"""Testes do gerador de capturas do README (tools/gen_readme_assets.py).

``tools/`` não é um pacote (sem __init__.py), então o gerador é carregado por
caminho via importlib para não mexer no empacotamento.
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_GEN_PATH = os.path.join(_ROOT, "tools", "gen_readme_assets.py")


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_readme_assets", _GEN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generates_four_svgs(tmp_path):
    gen = _load_generator()
    gen.main(outdir=str(tmp_path))
    svgs = sorted(p for p in os.listdir(tmp_path) if p.endswith(".svg"))
    assert svgs == ["banner.svg", "dashboard.svg", "preview.svg", "seal.svg"]
    for name in svgs:
        assert (tmp_path / name).stat().st_size > 1024


def test_anchor_strings_present(tmp_path):
    gen = _load_generator()
    gen.main(outdir=str(tmp_path))
    banner = (tmp_path / "banner.svg").read_text()
    seal = (tmp_path / "seal.svg").read_text()
    # O banner tem o título com letter-spacing (cada char num span próprio), então
    # a âncora confiável é o subtítulo real; o selo mantém o título "MASTER QC".
    assert "interativa" in banner or "ENCODER" in banner
    assert "MASTER" in seal or "QC" in seal
