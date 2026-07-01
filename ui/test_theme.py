"""Unit tests for ui.theme (pure: builds renderable infra, no engine)."""

from rich.console import Console

from ui.theme import PALETTE, THEME, get_console, glyphs


REQUIRED_STYLES = {
    "primary", "accent", "info", "ok", "warn", "err", "muted", "title",
    "label", "value", "seal", "tab.active", "tab.inactive", "panel.border",
}


def test_theme_has_required_styles():
    for name in REQUIRED_STYLES:
        assert THEME.styles.get(name) is not None, f"missing style: {name}"


def test_palette_keys_are_hex():
    for key, val in PALETTE.items():
        assert val.startswith("#") and len(val) == 7, f"{key}={val} not a hex color"


def test_get_console_returns_themed_console():
    con = get_console()
    assert isinstance(con, Console)
    # themed styles must resolve
    assert con.get_style("ok") is not None


def test_glyphs_unicode_default():
    g = glyphs(Console())
    assert "ok" in g and "block_full" in g


def test_glyphs_ascii_fallback_on_non_utf():
    """A non-UTF (e.g. cp1252) console must downgrade to ASCII glyphs."""
    class _FakeConsole:
        legacy_windows = False
        encoding = "cp1252"

    g = glyphs(_FakeConsole())  # type: ignore[arg-type]
    assert g["ok"] == "OK"
    assert g["block_full"] == "#"


def test_glyphs_ascii_fallback_on_legacy_windows():
    class _FakeConsole:
        legacy_windows = True
        encoding = "utf-8"

    g = glyphs(_FakeConsole())  # type: ignore[arg-type]
    assert g["warn"] == "!"


def test_theme_has_dim_variants():
    for name in ("accent.dim", "info.dim", "value.dim"):
        assert THEME.styles.get(name) is not None, f"missing style: {name}"


def test_idle_glyphs_wired_unicode_and_ascii():
    """The now-wired glyphs must resolve to Unicode on a utf console and
    downgrade to their ASCII forms on a non-utf (cp1252) console."""
    u = glyphs(Console())
    assert u["tab_l"] == "▎"
    assert u["audio"] == "🎧"
    assert u["spark"] == "✨"

    class _FakeConsole:
        legacy_windows = False
        encoding = "cp1252"

    a = glyphs(_FakeConsole())  # type: ignore[arg-type]
    assert a["tab_l"] == "|"
    assert a["audio"] == "[A]"
    assert a["spark"] == "*"
