import pytest

from ui.tui import keys as K


@pytest.mark.parametrize("ch,nxt,want", [
    ("\r", None, "ENTER"), ("\x1b", None, "ESC"), ("d", None, "D"), ("D", None, "D"),
    ("l", None, "L"), ("c", None, "C"), ("C", None, "C"),
    ("\xe0", "K", "LEFT"), ("\xe0", "M", "RIGHT"), ("\x00", "H", "UP"), ("\x00", "P", "DOWN"),
    ("x", None, None), ("\x03", None, None), ("\xe0", "Z", None),
])
def test_decode_windows(ch, nxt, want):
    assert K.decode_windows(ch, nxt) == want


@pytest.mark.parametrize("seq,want", [
    ("\n", "ENTER"), ("\r", "ENTER"), ("\x1b", "ESC"), ("\x1b[D", "LEFT"), ("\x1b[C", "RIGHT"),
    ("\x1b[A", "UP"), ("\x1b[B", "DOWN"), ("l", "L"), ("q", None), ("\x03", None),
])
def test_decode_posix(seq, want):
    assert K.decode_posix(seq) == want


def test_reader_start_stop_without_console(monkeypatch):
    got = []
    r = K.KeyReader(got.append)
    monkeypatch.setattr(K, "_reader_loop", lambda self: self._stop.wait(5))
    r.start()
    r.stop()
    r.restore()
    assert not r._thread.is_alive()
