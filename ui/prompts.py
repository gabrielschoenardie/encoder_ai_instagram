"""
ui.prompts
==========
Validated interactive input helpers built on ``rich.prompt``.

The *rendering* of a choice menu is split out (``render_choice_menu``) from the
input loop so it can be unit-tested without stdin. The interactive functions are
thin and defensive: they loop until the input validates, and they never run
inside a ``Live`` context (the launcher finishes all prompts before any
dashboard starts).
"""

from __future__ import annotations

import os
from typing import Optional, Sequence

from rich.console import RenderableType
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from .theme import PANEL_BOX, glyphs


def render_choice_menu(title: str, options: Sequence[str], console=None) -> RenderableType:
    """Pure: render a numbered menu of options (no input)."""
    g = glyphs(console)
    body = Text()
    for i, opt in enumerate(options, 1):
        body.append(f" {i} ", style="tab.active")
        body.append(f" {opt}", style="value")
        if i != len(options):
            body.append("\n")
    return Panel(body, title=title, title_align="left",
                 border_style="panel.border", box=PANEL_BOX, padding=(1, 2))


def ask_choice(console, title: str, options: Sequence[str], default: int = 1) -> int:
    """Show a numbered menu; return the chosen 1-based index."""
    console.print(render_choice_menu(title, options, console))
    choices = [str(i) for i in range(1, len(options) + 1)]
    raw = Prompt.ask("[primary]>[/primary]", choices=choices,
                     default=str(default), console=console, show_choices=False)
    return int(raw)


def ask_path(console, message: str, must_exist: bool = True) -> str:
    """Prompt for a file path; loop until it exists (if required)."""
    g = glyphs(console)
    while True:
        raw = Prompt.ask(f"[primary]{message}[/primary]", console=console).strip().strip('"')
        if not raw:
            console.print(f"[warn]{g['warn']} Informe um caminho.[/warn]")
            continue
        if must_exist and not os.path.isfile(raw):
            console.print(f"[err]{g['err']} Arquivo não encontrado:[/err] {raw}")
            continue
        return raw


def ask_folder(console, message: str, must_exist: bool = True) -> str:
    """Prompt for a folder path; loop until it exists (if required)."""
    g = glyphs(console)
    while True:
        raw = Prompt.ask(f"[primary]{message}[/primary]", console=console).strip().strip('"')
        if must_exist and not os.path.isdir(raw):
            console.print(f"[err]{g['err']} Pasta não encontrada:[/err] {raw}")
            continue
        return raw


def ask_toggle(console, message: str, default_on: bool = True) -> str:
    """Yes/No toggle returning the engine's '"on"'/'"off"' strings."""
    return "on" if Confirm.ask(f"[primary]{message}[/primary]",
                               default=default_on, console=console) else "off"


def ask_select(console, message: str, options: Sequence[str], default: str) -> str:
    """Constrained single value from `options` (returns the string value)."""
    return Prompt.ask(f"[primary]{message}[/primary]", choices=list(options),
                      default=default, console=console)


def ask_number(console, message: str, default: float,
               lo: Optional[float] = None, hi: Optional[float] = None,
               integer: bool = False) -> float:
    """Numeric prompt with range validation; loops until valid."""
    g = glyphs(console)
    while True:
        raw = Prompt.ask(f"[primary]{message}[/primary]",
                         default=str(default), console=console)
        try:
            val = int(raw) if integer else float(raw)
        except ValueError:
            console.print(f"[err]{g['err']} Número inválido:[/err] {raw}")
            continue
        if lo is not None and val < lo:
            console.print(f"[warn]{g['warn']} Mínimo é {lo}.[/warn]")
            continue
        if hi is not None and val > hi:
            console.print(f"[warn]{g['warn']} Máximo é {hi}.[/warn]")
            continue
        return val
