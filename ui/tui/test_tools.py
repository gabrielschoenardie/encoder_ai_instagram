import os

from ui.theme import get_console
from ui.tui import tools as T


def _seq(values):
    it = iter(values)
    return lambda *a, **k: next(it)


def _patch(monkeypatch, choices, run):
    monkeypatch.setattr(T, "ask_choice", _seq(choices))
    monkeypatch.setattr(T, "subprocess", type("S", (), {"run": staticmethod(run)}))
    monkeypatch.setattr(T, "Prompt", type("P", (), {"ask": staticmethod(lambda *a, **k: "")}))


def test_tools_flow_runs_tool_from_repo_root_then_returns(monkeypatch):
    ran = []
    _patch(monkeypatch, [1, len(T.TOOLS) + 1], lambda cmd, cwd=None: ran.append((cmd, cwd)))
    T._flow_tools(get_console(record=True, width=80))
    assert ran == [(T.TOOLS[0][1], T._REPO_ROOT)]
    assert os.path.isfile(os.path.join(ran[0][1], "Reels_Encoder_v2_FINAL.py"))


def test_tools_flow_subprocess_exception_does_not_crash(monkeypatch):
    def boom(cmd, cwd=None):
        raise FileNotFoundError("script missing")

    con = get_console(record=True, width=80)
    _patch(monkeypatch, [1, len(T.TOOLS) + 1], boom)
    T._flow_tools(con)
    assert "script missing" in con.export_text()
