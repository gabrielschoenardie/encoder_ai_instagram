import io

import pytest
from rich.console import Console

import reporter as R
from ui.tui_capture import ConsoleCapture, strip_symbols


def test_strip_symbols_removes_emoji_and_graphics():
    assert strip_symbols("📊 Pass 1: Analisando complexidade...") == "Pass 1: Analisando complexidade..."
    assert strip_symbols("✓ LUT Portra 400 carregada") == "LUT Portra 400 carregada"
    assert strip_symbols("⚠️  MCTF falhou") == "MCTF falhou"
    assert strip_symbols("────────") == ""
    assert strip_symbols("x264 ▶ ref frames: 4 · keyint") == "x264 ref frames: 4 · keyint"


def _console():
    return Console(file=io.StringIO(), width=80, force_terminal=True)


def test_capture_emits_clean_info_lines():
    cons, got = _console(), []
    with ConsoleCapture(cons, got.append):
        cons.print("[yellow]Aviso: ffprobe falhou, usando duração padrão 30s[/yellow]")
        cons.rule()
        cons.print("🎬 Pass 2: Encoding final...")
    assert [e.text for e in got] == [
        "Aviso: ffprobe falhou, usando duração padrão 30s",
        "Pass 2: Encoding final...",
    ]
    assert all(isinstance(e, R.Info) for e in got)


def test_capture_restores_on_exception():
    cons = _console()
    orig_file, orig_width = cons.file, cons.width
    with pytest.raises(RuntimeError):
        with ConsoleCapture(cons, lambda e: None):
            raise RuntimeError("boom")
    assert cons.file is orig_file and cons.width == orig_width


def test_capture_does_not_write_to_original_file():
    cons = _console()
    with ConsoleCapture(cons, lambda e: None):
        cons.print("nada na tela")
    assert cons.file.getvalue() == ""
