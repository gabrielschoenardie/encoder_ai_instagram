import sys

import pytest

from ui.tui import keys as K


@pytest.mark.parametrize("ch,nxt,want", [
    ("\r", None, "ENTER"), ("\x1b", None, "ESC"), ("d", None, "D"), ("D", None, "D"),
    ("l", None, "L"), ("c", None, "C"), ("C", None, "C"),
    ("\xe0", "K", "LEFT"), ("\xe0", "M", "RIGHT"), ("\x00", "H", "UP"), ("\x00", "P", "DOWN"),
    ("x", None, "CHAR"), ("\x03", None, None), ("\xe0", "Z", None),
])
def test_decode_windows(ch, nxt, want):
    assert K.decode_windows(ch, nxt) == want


@pytest.mark.parametrize("seq,want", [
    ("\n", "ENTER"), ("\r", "ENTER"), ("\x1b", "ESC"), ("\x1b[D", "LEFT"), ("\x1b[C", "RIGHT"),
    ("\x1b[A", "UP"), ("\x1b[B", "DOWN"), ("l", "L"), ("q", "CHAR"), ("\x03", None),
])
def test_decode_posix(seq, want):
    assert K.decode_posix(seq) == want


class FakeMsvcrt:
    def __init__(self, pending):
        self.pending = list(pending)

    def kbhit(self):
        return bool(self.pending)

    def getwch(self):
        return self.pending.pop(0)


def test_reader_start_stop_without_console(monkeypatch):
    monkeypatch.setitem(sys.modules, "msvcrt", FakeMsvcrt([]))
    got = []
    r = K.KeyReader(got.append)
    monkeypatch.setattr(K, "_reader_loop", lambda self: self._stop.wait(5))
    r.start()
    r.stop()
    r.restore()
    assert not r._thread.is_alive()


def test_start_flushes_pending_console_input(monkeypatch):
    fake = FakeMsvcrt(["\r", "x"])
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    got = []
    r = K.KeyReader(got.append)
    monkeypatch.setattr(K, "_reader_loop", lambda self: self._stop.wait(5))
    r.start()
    r.stop()
    assert fake.pending == [] and got == []


@pytest.mark.parametrize("ch,nxt,want", [
    (" ", None, "SPACE"), ("\x08", None, "BACKSPACE"), ("\xe0", "S", "DELETE"),
    ("1", None, "CHAR"), (":", None, "CHAR"), ("\\", None, "CHAR"), ("ã", None, "CHAR"),
    ("\x03", None, None), ("\x01", None, None),
])
def test_decode_windows_text_keys(ch, nxt, want):
    assert K.decode_windows(ch, nxt) == want


@pytest.mark.parametrize("seq,want", [
    (" ", "SPACE"), ("\x7f", "BACKSPACE"), ("\x08", "BACKSPACE"), ("5", "CHAR"), ("", None),
])
def test_decode_posix_text_keys(seq, want):
    assert K.decode_posix(seq) == want


def test_put_attaches_char_for_text_keys():
    got = []
    r = K.KeyReader(got.append)
    r._put("CHAR", "x")
    r._put("C", "c")
    r._put("SPACE", " ")
    r._put("ENTER", "\r")
    r._put(None, "\x03")
    assert [(k.name, k.char) for k in got] == [("CHAR", "x"), ("C", "c"), ("SPACE", " "), ("ENTER", None)]
