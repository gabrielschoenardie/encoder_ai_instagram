import re
from dataclasses import replace

import pytest
from rich.cells import cell_len

import reporter as R
from ui.theme import get_console
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui.test_screens import assert_fits, encoding_state
from ui.tui.test_screens_compact import _down, busy

SIZES = [(80, 24), (120, 40)]
LONG = ("[out#0/mp4 @ 000001] Error opening output file C:/Users/Editor Pro/Meus Videos/projeto final 2026/"
        "saida versao 3/clip final.mp4: Permission denied")


def text_of(state, width=120, height=40):
    con = get_console(record=True, width=width, height=height, force_terminal=True, color_system="truecolor",
                      legacy_windows=False)
    con.print(V.render(state))
    return con.export_text()


def err_state(stderr, size):
    s = S.apply(busy(encoding_state()), R.Error("RuntimeError", "falha", stderr, 1, None, ts=250.0))
    return replace(S.apply(s, S.Finished(1)), preset=1, size=size)


def visual(s):
    return S.stderr_visual_lines(s)


@pytest.mark.parametrize("size", SIZES)
def test_long_line_shown_complete(size):
    s = err_state((LONG + "\n").encode(), size)
    out = text_of(replace(s, error_scroll=max(0, len(visual(s)) - S.error_rows(s))), width=size[0], height=size[1])
    assert "…" not in out
    flat = re.sub(r"[│┃║╭╮╰╯─━═]", "", out)
    squashed = re.sub(r"\s+", "", flat)
    assert re.sub(r"\s+", "", LONG) in squashed
    assert "Permission denied" in out


@pytest.mark.parametrize("size", SIZES)
def test_literal_markup_and_wide_chars(size):
    raw = "[red]x[/red] [bold] 映像映像映像 áé" + "e\u0301" * 3 + " " + "映像 ação " * 25
    s = err_state(raw.encode("utf-8"), size)
    vis = visual(s)
    assert "".join(vis) == raw
    width = S.stderr_width(s)
    assert all(cell_len(ln) <= width for ln in vis)
    out = text_of(replace(s, error_scroll=0), width=size[0], height=size[1])
    assert "[red]x[/red] [bold]" in out


@pytest.mark.parametrize("size", SIZES)
def test_short_lines_unchanged(size):
    lines = ["primeira", "  indentada", "terceira"]
    s = err_state("\n".join(lines).encode(), size)
    assert visual(s) == lines


@pytest.mark.parametrize("size", SIZES)
def test_assert_fits_rendered(size):
    s = err_state((LONG * 3 + "\n").encode(), size)
    assert_fits(text_of(s, width=size[0], height=size[1]))


@pytest.mark.parametrize("size", SIZES)
def test_scroll_bounds(size):
    s = err_state(("\n".join(LONG + str(i) for i in range(30))).encode(), size)
    top = len(visual(s)) - S.error_rows(s)
    assert top > 0
    s = _down(s, top + 50)
    assert s.error_scroll == top
    for _ in range(top + 50):
        s = S.apply(s, S.Key("UP"))
    assert s.error_scroll == 0


def test_resize_keeps_scroll_valid():
    stderr = "\n".join(LONG + str(i) for i in range(30)).encode()
    for a, b in (((120, 40), (80, 24)), ((80, 24), (120, 40))):
        s = err_state(stderr, a)
        s = _down(s, 500)
        s = S.apply(s, S.Tick(s.now, b))
        top = max(0, len(visual(s)) - S.error_rows(s))
        assert 0 <= s.error_scroll <= top
        out = text_of(s, width=b[0], height=b[1])
        assert visual(s)[-1].strip()[-4:] in out


@pytest.mark.parametrize("size", SIZES)
def test_state_and_screen_share_function(size):
    s = err_state(("\n".join(LONG + str(i) for i in range(30))).encode(), size)
    s = _down(s, 500)
    assert s.error_scroll == len(S.stderr_visual_lines(s)) - S.error_rows(s)


@pytest.mark.parametrize("size", SIZES)
def test_bytes_none_and_log_fallback(size):
    s = err_state(b"linha um\nlinha dois\n", size)
    assert visual(s) == ["linha um", "linha dois"]
    s = err_state(None, size)
    assert isinstance(visual(s), list)
    assert "…" not in text_of(s, width=size[0], height=size[1])

LONG_M = LONG.replace("saida versao 3", "saida v3")


def _scroll_windows(s, limit=200):
    outs = [text_of(s, width=s.size[0], height=s.size[1])]
    for _ in range(limit):
        nxt = S.apply(s, S.Key("DOWN"))
        if nxt.error_scroll == s.error_scroll:
            break
        s = nxt
        outs.append(text_of(s, width=s.size[0], height=s.size[1]))
    return outs


@pytest.mark.parametrize("size", SIZES)
def test_behavior_long_line_reachable_by_down_without_ellipsis(size):
    s = err_state((LONG + "\n").encode(), size)
    outs = _scroll_windows(s)
    assert any("Permission denied" in o for o in outs)
    assert all("…" not in o for o in outs)


@pytest.mark.parametrize("size", SIZES)
def test_behavior_last_logical_markers_reachable(size):
    lines = [f"{LONG_M} FIM-{n:02d}" for n in range(30)]
    s = err_state("\n".join(lines).encode(), size)
    joined = "\n".join(_scroll_windows(s))
    for n in range(30):
        assert f"FIM-{n:02d}" in joined
    assert "…" not in joined


def test_behavior_resize_at_end_keeps_permission_denied_visible():
    lines = [f"{LONG_M} FIM-{n:02d}" for n in range(30)]
    s = err_state("\n".join(lines).encode(), (120, 40))
    for _ in range(200):
        s = S.apply(s, S.Key("DOWN"))
    s = S.apply(s, S.Tick(s.now, (80, 24)))
    out = text_of(s, width=80, height=24)
    assert "Permission denied" in out
    assert "…" not in out
