import re

import version


def test_version_is_semver():
    assert re.match(r"^\d+\.\d+\.\d+$", version.__version__)


def test_app_metadata_present():
    assert version.__app_name__
    assert version.__tagline__


def test_banner_can_carry_version():
    from ui import components as C
    from ui.theme import get_console

    con = get_console(record=True, width=80)
    con.print(C.banner("REELS ENCODER", f"v{version.__version__}"))
    assert version.__version__ in con.export_text()


def test_launcher_exposes_version():
    import ui.launcher as L

    assert getattr(L, "_APP_VERSION", None) == version.__version__
