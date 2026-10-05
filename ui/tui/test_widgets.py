from dataclasses import dataclass

import pytest

from ui.tui import widgets as W


@dataclass(frozen=True)
class F:
    kind: str
    options: tuple = ()
    lo: float | None = None
    hi: float | None = None
    step: float = 1.0
    integer: bool = False


def typed(text):
    buf = W.TextBuf()
    for ch in text:
        name = "SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR")
        buf = W.edit_text(buf, name, ch)
    return buf


def test_typing_inserts_including_hotkey_letters():
    assert typed("C:\\dl clip.mov").text == "C:\\dl clip.mov"


def test_cursor_backspace_delete():
    buf = typed("abcd")
    buf = W.edit_text(buf, "LEFT", None)
    buf = W.edit_text(buf, "LEFT", None)
    assert buf.cursor == 2
    buf = W.edit_text(buf, "BACKSPACE", None)
    assert (buf.text, buf.cursor) == ("acd", 1)
    buf = W.edit_text(buf, "DELETE", None)
    assert (buf.text, buf.cursor) == ("ad", 1)
    for _ in range(5):
        buf = W.edit_text(buf, "RIGHT", None)
    assert buf.cursor == 2
    assert W.edit_text(buf, "ENTER", None) is buf


def test_clean_path_strips_quotes_and_spaces():
    assert W.clean_path('  "C:\\Meus Vídeos\\clip.mov"  ') == "C:\\Meus Vídeos\\clip.mov"
    assert W.clean_path("") == ""


@pytest.mark.parametrize("text,lo,hi,integer,want", [
    ("-0.5", -2, 2, False, (-0.5, None)),
    ("1,2", 0, 2, False, (1.2, None)),
    ("4", 0, None, True, (4, None)),
    ("abc", 0, 2, False, (None, "Número inválido: abc")),
    ("5", -2, 2, False, (None, "Máximo é 2.")),
    ("-3", -2, 2, False, (None, "Mínimo é -2.")),
    ("1.5", 0, None, True, (None, "Número inválido: 1.5")),
])
def test_parse_number(text, lo, hi, integer, want):
    assert W.parse_number(text, lo, hi, integer) == want


def test_change_choice_toggle_number():
    choice = F("choice", ("auto", "24", "25", "30", "60"))
    assert W.change(choice, "30", "RIGHT") == "60"
    assert W.change(choice, "60", "RIGHT") == "auto"
    assert W.change(choice, "auto", "LEFT") == "60"
    toggle = F("toggle")
    assert W.change(toggle, "on", "SPACE") == "off"
    assert W.change(toggle, "off", "RIGHT") == "on"
    num = F("number", lo=-2, hi=2, step=0.1)
    assert W.change(num, 0.0, "RIGHT") == 0.1
    assert W.change(num, 2.0, "RIGHT") == 2.0
    assert W.change(num, -1.95, "LEFT") == -2.0
    threads = F("number", lo=0, step=1, integer=True)
    assert W.change(threads, 0, "LEFT") == 0
    assert W.change(threads, 3, "RIGHT") == 4
    assert W.change(choice, "30", "ENTER") is None
