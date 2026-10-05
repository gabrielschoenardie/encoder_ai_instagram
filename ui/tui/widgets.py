from __future__ import annotations

from dataclasses import dataclass, replace

_INSERT = frozenset({"CHAR", "SPACE", "D", "L", "C"})


@dataclass(frozen=True)
class TextBuf:
    text: str = ""
    cursor: int = 0


def edit_text(buf: TextBuf, name: str, char: str | None) -> TextBuf:
    t, c = buf.text, buf.cursor
    if name in _INSERT and char:
        return TextBuf(t[:c] + char + t[c:], c + len(char))
    if name == "BACKSPACE" and c > 0:
        return TextBuf(t[:c - 1] + t[c:], c - 1)
    if name == "DELETE" and c < len(t):
        return TextBuf(t[:c] + t[c + 1:], c)
    if name == "LEFT":
        return replace(buf, cursor=max(0, c - 1))
    if name == "RIGHT":
        return replace(buf, cursor=min(len(t), c + 1))
    return buf


def clean_path(text: str) -> str:
    return text.strip().strip('"').strip()


def _fmt(n) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def parse_number(text: str, lo, hi, integer: bool):
    raw = text.strip().replace(",", ".")
    try:
        val = int(raw) if integer else float(raw)
    except ValueError:
        return None, f"Número inválido: {text}"
    if lo is not None and val < lo:
        return None, f"Mínimo é {_fmt(lo)}."
    if hi is not None and val > hi:
        return None, f"Máximo é {_fmt(hi)}."
    return val, None


def change(field, current, name: str):
    if field.kind == "choice" and name in ("LEFT", "RIGHT"):
        opts = list(field.options)
        i = opts.index(current) if current in opts else 0
        return opts[(i + (1 if name == "RIGHT" else -1)) % len(opts)]
    if field.kind == "toggle" and name in ("LEFT", "RIGHT", "SPACE"):
        return "off" if current == "on" else "on"
    if field.kind == "number" and name in ("LEFT", "RIGHT"):
        val = float(current) + (field.step if name == "RIGHT" else -field.step)
        if field.lo is not None:
            val = max(field.lo, val)
        if field.hi is not None:
            val = min(field.hi, val)
        return int(round(val)) if field.integer else round(val, 2)
    return None
