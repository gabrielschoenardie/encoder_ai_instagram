# P3C Telas de Configuração da TUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m ui.tui` passa a montar a configuração em tela cheia (HOME → SOURCE → CONFIGURATION | ADVANCED → PREVIEW → READY) no lugar do wizard de linha, produzindo o mesmo `Namespace` que o wizard.

**Architecture:** Lógica pura nova em `ui/tui/widgets.py` (edição de campos) e `ui/tui/forms.py` (lista declarativa que espelha `ui/launcher.py`). O reducer `ui/tui/state.py` ganha as telas de configuração e devolve **ações** (`check_source`, `arm`, `tools`, `start`, `exit`) que o `App` executa com I/O (existência de arquivo, `probe_source_dims`, validação, Tools), devolvendo eventos (`SourceChecked`, `Armed`, `ReadyBlocked`). O encode continua sendo o do P3B.

**Tech Stack:** Python ≥ 3.11, Rich, Pydantic (já usado por `ui/config.py`), stdlib.

**Spec:** `docs/superpowers/specs/2026-10-05-tui-config-screens-design.md` (ler inteiro). Wireframes/regras: `docs/Phase_2_TUI_Specification.md` §E, §F, §H, §I, §J, §K, §L. Casca: `docs/superpowers/specs/2026-10-01-tui-shell-encode-design.md`.

## Global Constraints

- Mesmas opções, padrões e condições do wizard (`ui/launcher.py` `_flow_quick` 122–128, `_flow_cineon` 131–138, `_flow_advanced` 170–235); nenhum campo novo (D-06). Nunca expostos: `report`, `cineon_lut`, `debug`, `hardware_info`, `ui`, `batch`, `output_dir` (D-07).
- Teclas 1–5 na HOME (D-05); PREVIEW e READY separados (D-08). Preset 3 e o ramo batch do 5 desativados ("chega no P3D").
- Ctrl+C em telas de configuração → 130; ESC na HOME → 0 + "Cancelado pelo usuário.".
- 120 × 40; nenhuma linha > 120 colunas; sem emoji em regiões fixas (D-20) — não usar `C.banner`, `C.settings_preview` nem `C.quality_row` diretamente (contêm 🎞/🎧/✨); reproduzir o conteúdo deles com glifos do tema.
- Nada muda em `ui/launcher.py`, `ui/config.py`, `ui/prompts.py`, encoder, `reporter.py`, `ui/tui_driver.py`, `ui/tui_capture.py`.
- Python de testes: `venv\Scripts\python.exe` do projeto. Suíte canônica: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Testes em `tmp_path`.
- Novos módulos com `from __future__ import annotations`; sem comentários narrativos; não refatorar além do pedido (CLAUDE.md).

## Review Focus

1. **Digitar `c`, `d` ou `l` no campo de caminho** — o leitor de teclado entrega essas letras como `C`/`D`/`L` (atalhos do encode); no campo de texto elas têm de virar caracteres, nunca abrir cancelamento/detalhes. → `test_source_typing_hotkey_letters_inserts_chars` (Task 4).
2. **Caminho colado/arrastado com aspas e espaços** (`"C:\Meus Vídeos\clip.mov"`) — esperado VALID. → `test_clean_path_strips_quotes_and_spaces` (Task 1) e `test_check_source_quoted_path_with_spaces_is_valid` (Task 8).
3. **Número fora da faixa ou inválido digitado** (exposição `5`, `abc`) — esperado erro inline e valor anterior mantido. → `test_number_out_of_range_keeps_value_and_shows_error` (Task 5).
4. **Ligar/desligar Cineon ou enhance com o foco num campo que some** — o foco não pode apontar para fora da lista. → `test_focus_clamped_after_visibility_change` (Task 5).
5. **Resultado de verificação atrasado** (o usuário continuou digitando) — `SourceChecked` de um caminho antigo não pode marcar o atual como VALID. → `test_stale_source_check_ignored` (Task 4).

## File Structure

| arquivo | responsabilidade |
|---------|------------------|
| `ui/tui/widgets.py` (novo) | `TextBuf`, `edit_text`, `clean_path`, `parse_number`, `change` |
| `ui/tui/forms.py` (novo) | `Field`, `CONTINUE`, `QUICK`, `CINEON`, `TABS`, `ADVANCED`, `PRESET_LABELS`, `PRESET_HELP`, `ENABLED_PRESETS`, `new_draft`, `form_for`, `visible`, `derive`, `apply_change`, `output_name` |
| `ui/tui/keys.py` | decodificação de SPACE, BACKSPACE, DELETE e caracteres imprimíveis; `Key` com `char` |
| `ui/tui/state.py` | telas HOME/SOURCE/CONFIGURATION/ADVANCED/PREVIEW, eventos `SourceChecked`/`Armed`/`ReadyBlocked`, ações |
| `ui/tui/screens.py` | renderers das 5 telas novas; trilho e status para elas |
| `ui/tui/app.py` | início na HOME, execução das ações, Tools (suspender/retomar) |
| `ui/tui/__main__.py` | preflight antes; sem `run_launcher` |
| `ui/tui/test_widgets.py`, `test_forms.py`, `test_state_config.py`, `test_screens_config.py`, `test_parity_wizard.py` (novos); `test_keys.py`, `test_app.py`, `test_main.py` (ajustados) | testes |

---

### Task 1: `widgets.py` — edição pura de campos

**Files:**
- Create: `ui/tui/widgets.py`
- Test: `ui/tui/test_widgets.py`

**Interfaces:**
- Produces: `TextBuf(text: str = "", cursor: int = 0)` (frozen); `edit_text(buf: TextBuf, name: str, char: str | None) -> TextBuf`; `clean_path(text: str) -> str`; `parse_number(text: str, lo: float | None, hi: float | None, integer: bool) -> tuple[float | int | None, str | None]`; `change(field, current, name: str)` → novo valor ou `None` (usa `field.kind`, `field.options`, `field.lo`, `field.hi`, `field.step`, `field.integer`).

Regras: `edit_text` — `CHAR`/`SPACE`/`D`/`L`/`C` com `char` inserem `char` na posição do cursor; `BACKSPACE` apaga antes do cursor; `DELETE` apaga no cursor; `LEFT`/`RIGHT` movem o cursor (limitado a 0..len); qualquer outro nome devolve o mesmo `buf`. `clean_path` = `text.strip().strip('"').strip()`. `parse_number` espelha `ui/prompts.ask_number`: `int(text)` ou `float(text)` com `,` aceita como `.`; inválido → `(None, "Número inválido: <text>")`; `< lo` → `(None, "Mínimo é <lo>.")`; `> hi` → `(None, "Máximo é <hi>.")`. `change`: `choice` — `LEFT`/`RIGHT` circulam as opções; `toggle` — `LEFT`/`RIGHT`/`SPACE` alternam on↔off; `number` — `LEFT`/`RIGHT` somam ∓`step`, limitam a `[lo, hi]`, arredondam a 2 casas (inteiro se `integer`); outros nomes → `None`.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_widgets.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_widgets.py -v` → FAIL (`ModuleNotFoundError: ui.tui.widgets`).

- [ ] **Step 3: Implement** — `ui/tui/widgets.py`

```python
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
```

`parse_number` formata os limites sem ".0" para casar com as mensagens do teste (o wizard imprime `Mínimo é -2.0.`/`Máximo é 2.0.` porque recebe floats; na TUI o texto é só exibido inline — não entra no `Namespace`).

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/test_widgets.py -v` → verdes; `venv\Scripts\python.exe -m ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/widgets.py ui/tui/test_widgets.py
git commit -m "feat(tui): edição pura de campos de texto, número, lista e on/off (P3C)"
```

---

### Task 2: `forms.py` — espelho declarativo do wizard

**Files:**
- Create: `ui/tui/forms.py`
- Test: `ui/tui/test_forms.py`

**Interfaces:**
- Consumes: `ui.config.EncodeConfig` (`preset_quick_ffmpeg`, `preset_film_cineon`, `model_dump`, `model_validate`, `output_path`); `ui.launcher.PRESETS` (rótulos verbatim).
- Produces: `Field(name, kind, label, options=(), lo=None, hi=None, step=1.0, integer=False, visible_if=None)` (frozen); `CONTINUE: Field` (kind `"action"`); `QUICK`, `CINEON`: `tuple[Field, ...]`; `TABS = ("Source", "Color/LUT", "Audio", "Enhance", "Export")`; `ADVANCED: dict[str, tuple[Field, ...]]`; `PRESET_LABELS: tuple[str, ...]`; `PRESET_HELP: dict[int, str]`; `ENABLED_PRESETS = (1, 2, 4, 5)`; `new_draft(preset: int) -> dict`; `form_for(preset: int) -> tuple[Field, ...]` (1 → QUICK, 2 → CINEON); `visible(fields, draft: dict) -> tuple[Field, ...]`; `derive(draft: dict) -> dict`; `apply_change(draft: dict, name: str, value) -> tuple[dict, str | None]`; `output_name(draft: dict) -> str`.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_forms.py`

```python
from ui.config import EncodeConfig
from ui.tui import forms as F


def all_fields():
    return F.QUICK + F.CINEON + tuple(f for tab in F.TABS for f in F.ADVANCED[tab])


def test_every_field_is_an_encodeconfig_field_and_options_validate():
    names = set(EncodeConfig.model_fields)
    for f in all_fields():
        assert f.name in names, f.name
        for opt in f.options:
            EncodeConfig.model_validate({**EncodeConfig().model_dump(), f.name: opt})


def test_hidden_fields_never_exposed():
    exposed = {f.name for f in all_fields()}
    assert exposed.isdisjoint({"report", "cineon_lut", "debug", "hardware_info", "ui", "batch", "output_dir", "input"})


def test_preset_labels_are_the_wizard_labels():
    from ui.launcher import PRESETS
    assert F.PRESET_LABELS == tuple(PRESETS)
    assert F.ENABLED_PRESETS == (1, 2, 4, 5)


def test_new_draft_matches_factories():
    assert F.new_draft(1) == EncodeConfig.preset_quick_ffmpeg().model_dump()
    assert F.new_draft(2) == EncodeConfig.preset_film_cineon().model_dump()
    assert F.new_draft(5) == EncodeConfig().model_dump()


def test_quick_and_cineon_field_order():
    assert [f.name for f in F.QUICK] == ["fit", "fps", "mode"]
    assert [f.name for f in F.CINEON] == ["exposure_offset", "saturation", "fit"]


def test_advanced_tabs_and_conditions():
    d = F.new_draft(5)
    names = lambda tab, dd: [f.name for f in F.visible(F.ADVANCED[tab], dd)]
    assert names("Source", d) == ["cineon_pipeline", "fit", "fps", "scale", "mode", "performance"]
    assert names("Color/LUT", d) == ["lut", "hdr", "tonemap"]
    assert names("Color/LUT", {**d, "cineon_pipeline": "on"}) == ["exposure_offset", "saturation", "hdr", "tonemap"]
    assert names("Audio", d) == ["loudnorm", "ebu_meter"]
    assert names("Enhance", d) == ["enhance", "enhance_ai", "dither"]
    assert names("Enhance", {**d, "enhance_ai": "on"}) == ["enhance", "enhance_ai", "mctf", "dither"]
    assert names("Enhance", {**d, "enhance": "off", "enhance_ai": "on"}) == ["enhance", "dither"]
    assert names("Export", d) == ["show_hardware", "threads"]


def test_derive_mctf_follows_wizard_rule():
    d = {**F.new_draft(5), "enhance": "on", "enhance_ai": "off", "mctf": "on"}
    assert F.derive(d)["mctf"] == "off"
    d2 = {**F.new_draft(5), "enhance": "off", "enhance_ai": "on", "mctf": "on"}
    assert F.derive(d2)["mctf"] == "on"


def test_apply_change_validates_and_derives():
    d = {**F.new_draft(5), "enhance_ai": "on", "mctf": "on"}
    nd, err = F.apply_change(d, "enhance_ai", "off")
    assert err is None and nd["mctf"] == "off"
    same, err = F.apply_change(d, "exposure_offset", 5.0)
    assert same == d and err


def test_output_name():
    d = {**F.new_draft(1), "input": "C:/v/clip.mov"}
    assert F.output_name(d).endswith(".mp4")
    assert F.output_name(F.new_draft(1)) == "—"
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_forms.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** — `ui/tui/forms.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from ui.config import EncodeConfig
from ui.launcher import PRESETS

FIT = ("contain", "cover")
FPS = ("auto", "24", "25", "30", "60")
MODE = ("crf", "2pass")


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    label: str
    options: tuple = ()
    lo: float | None = None
    hi: float | None = None
    step: float = 1.0
    integer: bool = False
    visible_if: Callable[[dict], bool] | None = None


CONTINUE = Field("__continue__", "action", "CONTINUAR")


def _cineon_on(d: dict) -> bool:
    return d.get("cineon_pipeline") == "on"


def _cineon_off(d: dict) -> bool:
    return d.get("cineon_pipeline") != "on"


def _enhance_on(d: dict) -> bool:
    return d.get("enhance") == "on"


def _ai_on(d: dict) -> bool:
    return d.get("enhance") == "on" and d.get("enhance_ai") == "on"


QUICK = (
    Field("fit", "choice", "Enquadramento", FIT),
    Field("fps", "choice", "FPS", FPS),
    Field("mode", "choice", "Modo", MODE),
)
CINEON = (
    Field("exposure_offset", "number", "Exposure offset (EV, -2..+2)", lo=-2.0, hi=2.0, step=0.1),
    Field("saturation", "number", "Saturação (0..2)", lo=0.0, hi=2.0, step=0.05),
    Field("fit", "choice", "Enquadramento", FIT),
)
TABS = ("Source", "Color/LUT", "Audio", "Enhance", "Export")
ADVANCED = {
    "Source": (
        Field("cineon_pipeline", "toggle", "Pipeline Cineon (film look)"),
        Field("fit", "choice", "Enquadramento", FIT),
        Field("fps", "choice", "FPS", FPS),
        Field("scale", "choice", "Downscale 4K→1080p", ("auto", "off")),
        Field("mode", "choice", "Modo de encode", MODE),
        Field("performance", "choice", "Performance", ("quality", "balanced", "speed")),
    ),
    "Color/LUT": (
        Field("exposure_offset", "number", "Exposure offset (EV)", lo=-2.0, hi=2.0, step=0.1, visible_if=_cineon_on),
        Field("saturation", "number", "Saturação", lo=0.0, hi=2.0, step=0.05, visible_if=_cineon_on),
        Field("lut", "toggle", "Aplicar Hollywood LUT", visible_if=_cineon_off),
        Field("hdr", "choice", "HDR→SDR", ("auto", "off")),
        Field("tonemap", "choice", "Tonemap", ("mobius", "reinhard", "hable")),
    ),
    "Audio": (
        Field("loudnorm", "toggle", "Loudnorm EBU R128 (-14 LUFS)"),
        Field("ebu_meter", "toggle", "Monitor EBU R128 pós-encode (FFplay)"),
    ),
    "Enhance": (
        Field("enhance", "toggle", "Enhancement engine (denoise/sharpen/deband)"),
        Field("enhance_ai", "toggle", "Decisões via AI (mock CNN)", visible_if=_enhance_on),
        Field("mctf", "toggle", "MCTF mask video (anti-flicker)", visible_if=_ai_on),
        Field("dither", "choice", "Dither (ruído anti-banding)", ("auto", "on", "off")),
    ),
    "Export": (
        Field("show_hardware", "toggle", "Exibir perfil de hardware"),
        Field("threads", "number", "Threads (0 = auto)", lo=0, hi=None, step=1, integer=True),
    ),
}
PRESET_LABELS = tuple(PRESETS)
ENABLED_PRESETS = (1, 2, 4, 5)
PRESET_HELP = {
    1: "FFmpeg nativo com LUT Hollywood. Você escolhe enquadramento, FPS e modo (CRF ou 2-pass).",
    2: "Pipeline Cineon (film look). Você ajusta exposição, saturação e enquadramento.",
    3: "Batch de pasta — chega no P3D.",
    4: "Ferramentas utilitárias: sai da tela cheia, roda a ferramenta e volta à HOME.",
    5: "Todas as opções em 5 abas: Source · Color/LUT · Audio · Enhance · Export.",
}


def new_draft(preset: int) -> dict:
    if preset == 1:
        return EncodeConfig.preset_quick_ffmpeg().model_dump()
    if preset == 2:
        return EncodeConfig.preset_film_cineon().model_dump()
    return EncodeConfig().model_dump()


def form_for(preset: int) -> tuple:
    return QUICK if preset == 1 else CINEON


def visible(fields, draft: dict) -> tuple:
    return tuple(f for f in fields if f.visible_if is None or f.visible_if(draft))


def derive(draft: dict) -> dict:
    if draft.get("enhance") == "on" and draft.get("enhance_ai") != "on":
        return {**draft, "mctf": "off"}
    return draft


def apply_change(draft: dict, name: str, value) -> tuple:
    new = derive({**draft, name: value})
    try:
        EncodeConfig.model_validate(new)
    except ValidationError as exc:
        return draft, exc.errors()[0]["msg"]
    return new, None


def output_name(draft: dict) -> str:
    if not draft.get("input"):
        return "—"
    out = EncodeConfig.model_validate(draft).output_path()
    return os.path.basename(out) if out else "—"
```

Antes de finalizar, conferir em `ui/config.py` os nomes reais das fábricas (`preset_quick_ffmpeg`, `preset_film_cineon`) e a assinatura de `output_path()` (pode exigir argumento); ajustar só a chamada, não o teste.

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/test_forms.py -v` → verdes; ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/forms.py ui/tui/test_forms.py
git commit -m "feat(tui): formulários declarativos espelhando o wizard (P3C)"
```

---

### Task 3: `keys.py` — texto, SPACE, BACKSPACE, DELETE

**Files:**
- Modify: `ui/tui/state.py` (só a dataclass `Key`), `ui/tui/keys.py`
- Test: `ui/tui/test_keys.py` (ajustar casos que mudam de comportamento)

**Interfaces:**
- Produces: `Key(name: str, char: str | None = None)`; `decode_windows(ch, nxt=None) -> str | None` e `decode_posix(seq) -> str | None` agora devolvem também `"SPACE"`, `"BACKSPACE"`, `"DELETE"` (Windows `\xe0S`/`\x00S`; POSIX não suporta DELETE) e `"CHAR"` para qualquer caractere imprimível que não seja `d/l/c` (estes continuam `"D"`/`"L"`/`"C"`); `KeyReader._put(name, raw)` emite `Key(name, raw)` quando `name` ∈ `{"CHAR", "SPACE", "D", "L", "C"}`, senão `Key(name)`.

- [ ] **Step 1: Write the failing test** — em `ui/tui/test_keys.py`, trocar os casos `("x", None, None)` e `("q", None)` por `("x", None, "CHAR")` / `("q", "CHAR")` e acrescentar:

```python
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
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_keys.py -v` → FAIL.

- [ ] **Step 3: Implement**

Em `ui/tui/state.py`, só a dataclass:

```python
@dataclass(frozen=True)
class Key:
    name: str
    char: str | None = None
```

Em `ui/tui/keys.py`, substituir as tabelas e funções de decodificação e `_put`, e passar o caractere bruto nos loops:

```python
_CHARS = {"\r": "ENTER", "\n": "ENTER", "\x1b": "ESC", " ": "SPACE", "\x08": "BACKSPACE", "\x7f": "BACKSPACE"}
_HOTKEYS = {"d": "D", "l": "L", "c": "C"}
_WIN_EXT = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT", "S": "DELETE"}
_ANSI = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}
_WITH_CHAR = frozenset({"CHAR", "SPACE", "D", "L", "C"})


def _plain(ch: str) -> str | None:
    if not ch:
        return None
    if ch in _CHARS:
        return _CHARS[ch]
    if ch.lower() in _HOTKEYS:
        return _HOTKEYS[ch.lower()]
    if len(ch) == 1 and ch.isprintable():
        return "CHAR"
    return None


def decode_windows(ch: str, nxt: str | None = None) -> str | None:
    if ch in ("\x00", "\xe0"):
        return _WIN_EXT.get(nxt or "")
    return _plain(ch)


def decode_posix(seq: str) -> str | None:
    if seq.startswith("\x1b") and len(seq) > 1:
        return _ANSI.get(seq[1:3])
    return _plain(seq)
```

`KeyReader._put`:

```python
    def _put(self, name: str | None, raw: str | None = None) -> None:
        if name is not None:
            self._emit(Key(name, raw if name in _WITH_CHAR else None))
```

Loops: `_windows_loop` → `reader._put(decode_windows(ch, nxt), ch)`; `_posix_loop` → `reader._put(decode_posix(seq), seq if len(seq) == 1 else None)`.

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v` (todos os testes da TUI, inclusive P3B, verdes); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/state.py ui/tui/keys.py ui/tui/test_keys.py
git commit -m "feat(tui): teclas de texto (CHAR, SPACE, BACKSPACE, DELETE) no leitor (P3C)"
```

---

### Task 4: `state.py` (1/2) — HOME, SOURCE, eventos e ações

**Files:**
- Modify: `ui/tui/state.py`
- Test: `ui/tui/test_state_config.py`

**Interfaces:**
- Consumes: `forms` (Task 2), `widgets` (Task 1), `Key.char` (Task 3).
- Produces: telas `HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW`; `CONFIG_SCREENS`; `ACTIONS = ("start", "exit", "tools", "arm", "check_source")`; eventos `SourceChecked(path: str, status: str, dims: tuple | None = None)`, `Armed(config: dict, output_path: str, output_preexisted: bool, error: str | None = None)`, `ReadyBlocked(message: str)`; campos novos de `UIState`: `preset: int = 0`, `drafts: tuple = ()`, `focus: tuple = ()`, `home_focus: int = 0`, `tab: int = 0`, `tab_focus: bool = False`, `edit: TextBuf | None = None`, `field_error: str | None = None`, `source: TextBuf = TextBuf()`, `source_status: str = "INVALID"`, `source_dims: tuple | None = None`, `came_from: str = CONFIGURATION`, `adv_back: str = SOURCE`, `ready_error: str | None = None`, `system: tuple = ()`; helpers `draft(s) -> dict`, `focus_key(s) -> str`, `focus_of(s, key) -> int`, `form_items(s) -> tuple[Field, ...]` (Task 5 completa CONFIGURATION/ADVANCED).

Regras: `apply(Key)` chama `_key(s, ev.name, ev.char)`; telas em `CONFIG_SCREENS` vão para `_config_key`. HOME: ↑↓ circulam pulando o preset 3; ENTER ou `CHAR` "1"–"5" escolhem (3 ignorado); 4 → `action="tools"`; 1/2/5 → `preset`, rascunho criado se não existir (`forms.new_draft`), tela SOURCE com o `input` do rascunho no campo e `action="check_source"` se não vazio; ESC → `action="exit", exit_code=0`. SOURCE: teclas de texto editam `source` (letras `D/L/C` com `char` inserem o caractere), marcam `source_status="CHECKING"` e `action="check_source"`; ENTER só com `VALID` grava `input` (limpo) no rascunho e vai a CONFIGURATION (1, 2) ou ADVANCED (5, `adv_back=SOURCE`); ESC grava o texto atual (limpo, ou `None` se vazio) no `input` do rascunho e volta à HOME (C-4: o caminho digitado é lembrado). `SourceChecked` só se aplica se `path == clean_path(source.text)`. `Armed`: com `error` → fica em PREVIEW com `field_error=error`; sem erro → READY com `config`, `output_path`, `output_preexisted`, `ready_error=None`. `ReadyBlocked` → READY, `ready_error`, `action=None`. READY com `preset != 0`: ESC → PREVIEW (com `preset == 0`, comportamento P3B: sair).

- [ ] **Step 1: Write the failing test** — `ui/tui/test_state_config.py`

```python
import pytest

from ui.tui import forms as F
from ui.tui import state as S


def home():
    return S.UIState(config={}, screen=S.HOME)


def key(name, char=None):
    return S.Key(name, char)


def type_text(s, text):
    for ch in text:
        name = "SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR")
        s = S.apply(s, key(name, ch))
    return s


def test_home_navigation_skips_batch_and_wraps():
    s = home()
    assert s.home_focus == 0
    s = S.apply(s, key("DOWN"))
    assert s.home_focus == 1
    s = S.apply(s, key("DOWN"))
    assert s.home_focus == 3
    s = S.apply(s, key("UP"))
    assert s.home_focus == 1
    s = S.apply(home(), key("UP"))
    assert s.home_focus == 4


def test_home_digits_and_disabled_batch():
    assert S.apply(home(), key("CHAR", "3")) == home()
    s = S.apply(home(), key("CHAR", "4"))
    assert s.action == "tools" and s.screen == S.HOME
    s = S.apply(home(), key("CHAR", "2"))
    assert s.screen == S.SOURCE and s.preset == 2
    assert S.draft(s) == F.new_draft(2)
    s = S.apply(home(), key("ESC"))
    assert s.action == "exit" and s.exit_code == 0


def test_source_typing_hotkey_letters_inserts_chars():
    s = S.apply(home(), key("ENTER"))
    s = type_text(s, "C:\\dlc.mov")
    assert s.source.text == "C:\\dlc.mov"
    assert s.screen == S.SOURCE and s.modal is None
    assert s.action == "check_source" and s.source_status == "CHECKING"


def test_source_enter_requires_valid_then_routes_by_preset():
    s = type_text(S.apply(home(), key("ENTER")), "a.mov")
    assert S.apply(s, key("ENTER")).screen == S.SOURCE
    s = S.apply(s, S.SourceChecked("a.mov", "VALID", (1080, 1920)))
    assert s.source_dims == (1080, 1920)
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and S.draft(s)["input"] == "a.mov"
    s5 = type_text(S.apply(home(), key("CHAR", "5")), "b.mov")
    s5 = S.apply(S.apply(s5, S.SourceChecked("b.mov", "VALID")), key("ENTER"))
    assert s5.screen == S.ADVANCED and s5.adv_back == S.SOURCE


def test_stale_source_check_ignored():
    s = type_text(S.apply(home(), key("ENTER")), "a.mo")
    s = type_text(s, "v")
    s = S.apply(s, S.SourceChecked("a.mo", "VALID"))
    assert s.source_status == "CHECKING"
    s = S.apply(s, S.SourceChecked("a.mov", "NOT_FOUND"))
    assert s.source_status == "NOT_FOUND"


def test_source_quoted_path_matches_check():
    s = type_text(S.apply(home(), key("ENTER")), '"C:\\Meus Vídeos\\x.mov"')
    s = S.apply(s, S.SourceChecked("C:\\Meus Vídeos\\x.mov", "VALID"))
    assert s.source_status == "VALID"
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["input"] == "C:\\Meus Vídeos\\x.mov"


def test_source_esc_back_home_and_draft_remembered():
    s = type_text(S.apply(home(), key("ENTER")), "a.mov")
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME and S.draft(s)["input"] == "a.mov"
    s = S.apply(s, key("ENTER"))
    assert s.source.text == "a.mov" and s.action == "check_source"


def test_armed_and_ready_blocked_and_ready_esc():
    s = S.UIState(config={}, screen=S.PREVIEW, preset=1)
    bad = S.apply(s, S.Armed({}, "", False, error="inválido"))
    assert bad.screen == S.PREVIEW and bad.field_error == "inválido"
    ok = S.apply(s, S.Armed({"input": "a.mov"}, "a_out.mp4", True))
    assert ok.screen == S.READY and ok.config == {"input": "a.mov"} and ok.output_preexisted
    blocked = S.apply(ok, S.ReadyBlocked("arquivo de entrada não encontrado: a.mov"))
    assert blocked.screen == S.READY and blocked.ready_error and blocked.action is None
    assert S.apply(ok, key("ESC")).screen == S.PREVIEW
    legacy = S.UIState(config={"input": "x"}, screen=S.READY)
    assert S.apply(legacy, key("ESC")).action == "exit"
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_state_config.py -v` → FAIL.

- [ ] **Step 3: Implement** — em `ui/tui/state.py`:

1. Imports no topo (junto dos demais): `from ui.tui import forms as F` e `from ui.tui import widgets as W`.
2. Constantes após `CANCELLED`:

```python
HOME = "HOME"
SOURCE = "SOURCE"
CONFIGURATION = "CONFIGURATION"
ADVANCED = "ADVANCED"
PREVIEW = "PREVIEW"
CONFIG_SCREENS = frozenset({HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW})
ACTIONS = ("start", "exit", "tools", "arm", "check_source")
```

3. Eventos após `Finished`:

```python
@dataclass(frozen=True)
class SourceChecked:
    path: str
    status: str
    dims: tuple | None = None


@dataclass(frozen=True)
class Armed:
    config: dict
    output_path: str
    output_preexisted: bool
    error: str | None = None


@dataclass(frozen=True)
class ReadyBlocked:
    message: str
```

4. Campos novos no fim de `UIState` (antes de `action` não importa; acrescentar depois de `action`):

```python
    preset: int = 0
    drafts: tuple = ()
    focus: tuple = ()
    home_focus: int = 0
    tab: int = 0
    tab_focus: bool = False
    edit: W.TextBuf | None = None
    field_error: str | None = None
    source: W.TextBuf = W.TextBuf()
    source_status: str = "INVALID"
    source_dims: tuple | None = None
    came_from: str = CONFIGURATION
    adv_back: str = SOURCE
    ready_error: str | None = None
    system: tuple = ()
```

5. Helpers (após `filtered_log`):

```python
def draft(s: UIState) -> dict:
    found = dict(s.drafts).get(s.preset)
    return dict(found) if found is not None else F.new_draft(s.preset)


def _with_draft(s: UIState, d: dict) -> UIState:
    others = tuple((p, x) for p, x in s.drafts if p != s.preset)
    return replace(s, drafts=others + ((s.preset, d),))


def focus_key(s: UIState) -> str:
    return f"{ADVANCED}:{s.tab}" if s.screen == ADVANCED else s.screen


def focus_of(s: UIState, key: str) -> int:
    return dict(s.focus).get(key, 0)


def _set_focus(s: UIState, key: str, index: int) -> UIState:
    others = tuple((k, v) for k, v in s.focus if k != key)
    return replace(s, focus=others + ((key, index),))


def form_items(s: UIState) -> tuple:
    d = draft(s)
    if s.screen == ADVANCED:
        return F.visible(F.ADVANCED[F.TABS[s.tab]], d) + (F.CONTINUE,)
    if s.screen == CONFIGURATION:
        return F.visible(F.form_for(s.preset), d) + (F.CONTINUE,)
    return ()
```

6. `apply`: trocar `return _key(s, ev.name)` por `return _key(s, ev.name, ev.char)` e acrescentar, antes do `return _engine(s, ev)`:

```python
    if isinstance(ev, SourceChecked):
        if ev.path != W.clean_path(s.source.text):
            return s
        return replace(s, source_status=ev.status, source_dims=ev.dims)
    if isinstance(ev, Armed):
        if ev.error:
            return replace(s, field_error=ev.error)
        return replace(s, screen=READY, config=dict(ev.config), output_path=ev.output_path,
                       output_preexisted=ev.output_preexisted, ready_error=None, field_error=None)
    if isinstance(ev, ReadyBlocked):
        return replace(s, screen=READY, ready_error=ev.message, action=None)
```

7. `_key(s, k, ch=None)`: assinatura nova; no início:

```python
    if s.screen in CONFIG_SCREENS:
        return _config_key(s, k, ch)
    if s.screen == READY:
        if k == "ENTER":
            return replace(s, screen=ENCODING, action="start", ready_error=None)
        if k == "ESC":
            if s.preset:
                return replace(s, screen=PREVIEW, ready_error=None)
            return replace(s, action="exit", exit_code=0)
        return s
```

(substitui o bloco READY existente; o resto de `_key` não muda).

8. Funções novas (HOME/SOURCE; CONFIGURATION/ADVANCED/PREVIEW chegam na Task 5 — por ora `_config_key` devolve `s` para essas telas):

```python
def _config_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.screen == HOME:
        return _home_key(s, k, ch)
    if s.screen == SOURCE:
        return _source_key(s, k, ch)
    return s


def _home_key(s: UIState, k: str, ch: str | None) -> UIState:
    if k in ("UP", "DOWN"):
        i = s.home_focus
        step = 1 if k == "DOWN" else -1
        while True:
            i = (i + step) % len(F.PRESET_LABELS)
            if i + 1 in F.ENABLED_PRESETS:
                return replace(s, home_focus=i)
    if k == "ESC":
        return replace(s, action="exit", exit_code=0)
    if k == "ENTER":
        choice = s.home_focus + 1
    elif ch and ch in "12345":
        choice = int(ch)
    else:
        return s
    if choice not in F.ENABLED_PRESETS:
        return s
    s = replace(s, home_focus=choice - 1)
    if choice == 4:
        return replace(s, action="tools")
    s = replace(s, preset=choice, field_error=None, edit=None)
    d = draft(s)
    s = _with_draft(s, d)
    text = d.get("input") or ""
    s = replace(s, screen=SOURCE, source=W.TextBuf(text, len(text)), source_status="INVALID", source_dims=None)
    return replace(s, source_status="CHECKING", action="check_source") if text else s


def _source_key(s: UIState, k: str, ch: str | None) -> UIState:
    if k == "ESC":
        s = _with_draft(s, {**draft(s), "input": W.clean_path(s.source.text) or None})
        return replace(s, screen=HOME)
    if k == "ENTER":
        if s.source_status != "VALID":
            return s
        s = _with_draft(s, {**draft(s), "input": W.clean_path(s.source.text)})
        if s.preset == 5:
            return replace(s, screen=ADVANCED, adv_back=SOURCE, tab_focus=False, edit=None, field_error=None)
        return replace(s, screen=CONFIGURATION, edit=None, field_error=None)
    buf = W.edit_text(s.source, k, ch)
    if buf == s.source:
        return s
    if buf.text == s.source.text:
        return replace(s, source=buf)
    return replace(s, source=buf, source_status="CHECKING", source_dims=None, action="check_source")
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v` (P3B verdes também); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/state.py ui/tui/test_state_config.py
git commit -m "feat(tui): HOME e SOURCE no reducer com eventos de verificação e armamento (P3C)"
```

---

### Task 5: `state.py` (2/2) — CONFIGURATION, ADVANCED, PREVIEW

**Files:**
- Modify: `ui/tui/state.py`
- Test: `ui/tui/test_state_config.py` (acrescentar)

**Interfaces:**
- Consumes: tudo da Task 4.
- Produces: `_config_key` completo; helper `form_back(s) -> UIState`.

Regras (spec §5–§6, Phase 2 §F/§J/§K/§L): itens = campos visíveis + `CONTINUE`; foco por `focus_key` (restaurado ao voltar; limitado ao tamanho atual da lista). ↑↓ movem (no ADVANCED, ↑ no primeiro item vai à barra de abas; na barra, ←→ trocam de aba, ↓ entra no primeiro item). ←→/SPACE mudam o valor via `widgets.change`; `CHAR` (dígito, `.`, `,`, `-`) num campo `number` abre `edit` com esse caractere; com `edit` aberto, teclas de texto editam; ENTER/↑/↓ confirmam (`parse_number` → erro inline e valor mantido, ou `apply_change`); ESC descarta a edição. ENTER num campo vai ao próximo; se o próximo é `CONTINUE`, vai direto ao PREVIEW. ENTER em `CONTINUE` → PREVIEW (`came_from` = tela atual, `action_focus=0`). ESC: CONFIGURATION → SOURCE; ADVANCED → `adv_back`. Toda mudança passa por `forms.apply_change` (erro → `field_error`, rascunho intacto) e o foco é limitado ao novo tamanho da lista. PREVIEW: ←→ alternam `action_focus` (0 CONTINUAR, 1 REVISAR); ENTER em CONTINUAR → `action="arm"`; ENTER em REVISAR → ADVANCED (`adv_back=PREVIEW`, `tab=0`, `tab_focus=False`); ESC → `came_from`.

- [ ] **Step 1: Write the failing test** — acrescentar a `ui/tui/test_state_config.py`:

```python
def at_config(preset=1, path="a.mov"):
    s = S.apply(home(), key("CHAR", str(preset)))
    s = type_text(s, path)
    s = S.apply(s, S.SourceChecked(path, "VALID"))
    return S.apply(s, key("ENTER"))


def focused(s):
    return S.form_items(s)[min(S.focus_of(s, S.focus_key(s)), len(S.form_items(s)) - 1)]


def test_configuration_quick_choices_and_continue():
    s = at_config(1)
    assert [f.name for f in S.form_items(s)] == ["fit", "fps", "mode", "__continue__"]
    s = S.apply(s, key("RIGHT"))
    assert S.draft(s)["fit"] == "cover"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("LEFT"))
    assert S.draft(s)["fps"] == "25"
    s = S.apply(s, key("ENTER"))
    assert focused(s).name == "mode"
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.CONFIGURATION


def test_number_typing_commit_and_errors():
    s = at_config(2)
    s = S.apply(s, key("CHAR", "-"))
    s = type_text(s, "0.5")
    assert s.edit.text == "-0.5"
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["exposure_offset"] == -0.5 and s.edit is None
    assert focused(s).name == "saturation"


def test_number_out_of_range_keeps_value_and_shows_error():
    s = at_config(2)
    s = S.apply(s, key("CHAR", "5"))
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["exposure_offset"] == 0.0
    assert s.field_error == "Máximo é 2."
    s = S.apply(s, key("CHAR", "x"))
    assert s.edit is None
    s = S.apply(s, key("CHAR", "1"))
    s = S.apply(s, key("ESC"))
    assert s.edit is None and S.draft(s)["exposure_offset"] == 0.0 and s.screen == S.CONFIGURATION


def test_number_arrows_step():
    s = at_config(2)
    s = S.apply(s, key("RIGHT"))
    assert S.draft(s)["exposure_offset"] == 0.1


def test_esc_back_to_source_keeps_draft_and_focus_restored():
    s = at_config(1)
    s = S.apply(S.apply(s, key("DOWN")), key("RIGHT"))
    s = S.apply(s, key("ESC"))
    assert s.screen == S.SOURCE
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and focused(s).name == "fps" and S.draft(s)["fps"] == "60"


def test_advanced_tabs_two_level_focus():
    s = at_config(5)
    assert s.screen == S.ADVANCED and not s.tab_focus and focused(s).name == "cineon_pipeline"
    s = S.apply(s, key("UP"))
    assert s.tab_focus
    s = S.apply(s, key("RIGHT"))
    assert F.TABS[s.tab] == "Color/LUT"
    s = S.apply(s, key("DOWN"))
    assert not s.tab_focus and focused(s).name == "lut"
    s = S.apply(s, key("UP"))
    s = S.apply(s, key("LEFT"))
    assert F.TABS[s.tab] == "Source"


def test_focus_clamped_after_visibility_change():
    from dataclasses import replace
    s = at_config(5)
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["cineon_pipeline"] == "on"
    s = replace(s, tab=1, focus=s.focus + ((f"{S.ADVANCED}:1", 4),))
    assert focused(s) is F.CONTINUE
    s = replace(s, tab=0)
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["cineon_pipeline"] == "off"
    s = replace(s, tab=1)
    assert len(S.form_items(s)) == 4 and focused(s) is F.CONTINUE
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW


def test_enhance_off_hides_ai_and_ai_off_forces_mctf_off():
    s = at_config(5)
    s = S.apply(s, key("UP"))
    for _ in range(3):
        s = S.apply(s, key("RIGHT"))
    assert F.TABS[s.tab] == "Enhance"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["enhance_ai"] == "on"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["mctf"] == "on"
    s = S.apply(s, key("UP"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["enhance_ai"] == "off" and S.draft(s)["mctf"] == "off"


def test_preview_actions():
    s = at_config(1)
    s = S.apply(S.apply(S.apply(s, key("ENTER")), key("ENTER")), key("ENTER"))
    assert s.screen == S.PREVIEW
    assert S.apply(s, key("ENTER")).action == "arm"
    rev = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert rev.screen == S.ADVANCED and rev.adv_back == S.PREVIEW and rev.tab == 0
    assert S.apply(rev, key("ESC")).screen == S.PREVIEW
    assert S.apply(s, key("ESC")).screen == S.CONFIGURATION
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_state_config.py -v` → os novos falham.

- [ ] **Step 3: Implement** — em `ui/tui/state.py`, substituir `_config_key` e acrescentar:

```python
_EDIT_KEYS = frozenset({"CHAR", "SPACE", "BACKSPACE", "DELETE", "LEFT", "RIGHT", "D", "L", "C"})


def _config_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.screen == HOME:
        return _home_key(s, k, ch)
    if s.screen == SOURCE:
        return _source_key(s, k, ch)
    if s.screen == PREVIEW:
        return _preview_key(s, k)
    return _form_key(s, k, ch)


def form_back(s: UIState) -> UIState:
    target = SOURCE if s.screen == CONFIGURATION else s.adv_back
    return replace(s, screen=target, edit=None, field_error=None, tab_focus=False)


def _set_value(s: UIState, name: str, value) -> UIState:
    new, err = F.apply_change(draft(s), name, value)
    if err:
        return replace(s, field_error=err, edit=None)
    s = replace(_with_draft(s, new), field_error=None, edit=None)
    key = focus_key(s)
    return _set_focus(s, key, min(focus_of(s, key), len(form_items(s)) - 1))


def _commit(s: UIState, field) -> UIState:
    value, err = W.parse_number(s.edit.text, field.lo, field.hi, field.integer)
    if err:
        return replace(s, field_error=err, edit=None)
    return _set_value(s, field.name, value)


def _form_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.screen == ADVANCED and s.tab_focus:
        if k in ("LEFT", "RIGHT"):
            return replace(s, tab=(s.tab + (1 if k == "RIGHT" else -1)) % len(F.TABS))
        if k == "DOWN":
            return replace(s, tab_focus=False)
        if k == "ESC":
            return form_back(s)
        return s
    items = form_items(s)
    key = focus_key(s)
    i = min(focus_of(s, key), len(items) - 1)
    item = items[i]
    if s.edit is not None:
        if k == "ESC":
            return replace(s, edit=None, field_error=None)
        if k in _EDIT_KEYS:
            return replace(s, edit=W.edit_text(s.edit, k, ch))
        s = _commit(s, item)
        if s.field_error:
            return s
        items = form_items(s)
        i = min(focus_of(s, key), len(items) - 1)
        if k == "ENTER":
            nxt = min(i + 1, len(items) - 1)
            if items[nxt] is F.CONTINUE:
                return replace(s, screen=PREVIEW, came_from=s.screen, action_focus=0)
            return _set_focus(s, key, nxt)
    if k == "ESC":
        return form_back(s)
    if k == "UP":
        if i == 0 and s.screen == ADVANCED:
            return replace(s, tab_focus=True)
        return _set_focus(s, key, max(0, i - 1))
    if k == "DOWN":
        return _set_focus(s, key, min(len(items) - 1, i + 1))
    if item is F.CONTINUE:
        if k == "ENTER":
            return replace(s, screen=PREVIEW, came_from=s.screen, action_focus=0, field_error=None)
        return s
    if k == "ENTER":
        nxt = min(i + 1, len(items) - 1)
        if items[nxt] is F.CONTINUE:
            return replace(s, screen=PREVIEW, came_from=s.screen, action_focus=0, field_error=None)
        return _set_focus(s, key, nxt)
    if item.kind == "number" and k == "CHAR" and ch and (ch.isdigit() or ch in ".,-"):
        return replace(s, edit=W.TextBuf(ch, 1), field_error=None)
    value = W.change(item, draft(s)[item.name], k)
    if value is None:
        return s
    return _set_value(s, item.name, value)


def _preview_key(s: UIState, k: str) -> UIState:
    if k in ("LEFT", "RIGHT"):
        return replace(s, action_focus=1 - s.action_focus)
    if k == "ESC":
        return replace(s, screen=s.came_from, field_error=None)
    if k == "ENTER":
        if s.action_focus == 0:
            return replace(s, action="arm")
        return replace(s, screen=ADVANCED, adv_back=PREVIEW, tab=0, tab_focus=False, edit=None, field_error=None)
    return s
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v`; ruff. Se um teste de navegação da Task 5 depender de uma ordem de teclas que contradiz a regra escrita acima (o teste é a especificação de comportamento), reportar BLOCKED com o caso — não alterar o teste nem a regra por conta própria.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/state.py ui/tui/test_state_config.py
git commit -m "feat(tui): CONFIGURATION, ADVANCED e PREVIEW no reducer (P3C)"
```

---

### Task 6: `screens.py` (1/2) — HOME e SOURCE

**Files:**
- Modify: `ui/tui/screens.py`
- Test: `ui/tui/test_screens_config.py`

**Interfaces:**
- Consumes: `state` (Tasks 4–5), `forms`, `widgets`; helpers existentes de `screens.py` (`panel`, `kv_table`, `hero`, `basename`, `RAIL`, `STATUS`, `FOOTER_KEYS`, `SCREEN_RENDERERS`, `header`, `footer`, `_rail_active`).
- Produces: `SCREEN_RENDERERS[S.HOME]`, `[S.SOURCE]`; helper `path_field(buf: TextBuf, width: int) -> Text`; `STATUS`/`FOOTER_KEYS` para as 5 telas; trilho correto (Phase 2 §C: ✓ só antes da tela ativa).

Regras de desenho (Phase 2 §H, §I):

- `header`: `RAIL` existente; ✓ somente para itens antes do ativo (trocar `if i < 4 or i < idx` por `if i < idx`); `_rail_active` mapeia HOME→"HOME", SOURCE→"SOURCE", CONFIGURATION/ADVANCED→"CONFIG", PREVIEW→"PREVIEW".
- `STATUS`: HOME "● HOME", SOURCE "● SOURCE", CONFIGURATION "● CONFIG", ADVANCED "● ADVANCED", PREVIEW "● PREVIEW".
- `FOOTER_KEYS`: HOME `"[↑↓] Navegar   [1-5] Abrir   [ENTER] Abrir   [ESC] Sair"`; SOURCE `"[digite] Caminho   [←→] Cursor   [ENTER] Continuar   [ESC] Voltar   [Ctrl+C] Sair"`; CONFIGURATION `"[↑↓] Campo   [←→/SPACE] Valor   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair"`; ADVANCED `"[↑↓] Campo   [←→] Valor/Aba   [SPACE] On/Off   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair"`; PREVIEW `"[←→] Escolher   [ENTER] Confirmar   [ESC] Voltar   [Ctrl+C] Sair"`.
- HOME: hero DOUBLE 7 linhas ("REELS ENCODER" + "Premiere Workspace · escolha um fluxo") — **sem** `C.banner` (emoji); menu 58×17 com os 5 `F.PRESET_LABELS` numerados, foco `▎▸` + `tab.active`, preset 3 em `muted` com "— chega no P3D"; painel "O QUE FAZ" 58×17 com `F.PRESET_HELP[home_focus + 1]`; faixa SYSTEM 118×5 com `kv_table(s.system)`.
- SOURCE: painel SOURCE 76×26 | PROGRAM 40×26; no preset 5, primeira linha "É um batch de pasta?  off  — chega no P3D" em `muted`; linha ARQUIVO com `path_field` (texto com o caractere sob o cursor em `reverse`, janela que acompanha o cursor, largura 60); status (`VALID` `ok` "✓ arquivo encontrado"; `NOT_FOUND` `err` "✗ arquivo não encontrado"; `INVALID` `warn` "⚠ informe um arquivo de vídeo"; `CHECKING` `muted` "verificando…"); dimensões `W × H` ou `—`; saída `F.output_name(draft com input limpo)`; PROGRAM: `C.viewer_frame(fit=draft['fit'], src_dims=s.source_dims, title="PROGRAM")`; faixa PRÓXIMO 118×4: "ENTER → CONFIGURATION" (1, 2) ou "ENTER → ADVANCED" (5).

- [ ] **Step 1: Write the failing test** — `ui/tui/test_screens_config.py`

```python
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of


def home(**kw):
    return S.UIState(config={}, screen=S.HOME,
                     system=(("FFmpeg", "ffmpeg.exe"), ("ffprobe", "ffprobe.exe"), ("ffplay", "ok"),
                             ("hardware", "detectado no início do encode")), **kw)


def test_home_screen():
    out = text_of(home())
    for txt in ("REELS ENCODER", "Encode rápido (FFmpeg)", "Film look (Cineon)", "Batch de pasta",
                "chega no P3D", "Tools", "Configurar avançado", "O QUE FAZ", "SYSTEM", "ffprobe.exe",
                "detectado no início do encode", "[1-5]"):
        assert txt in out, txt
    assert "▸" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_home_rail_has_no_checks_before_home():
    out = text_of(home())
    assert "✓ HOME" not in out and "✓ SOURCE" not in out


def test_source_screen_states():
    base = S.UIState(config={}, screen=S.SOURCE, preset=1, drafts=((1, {**S.draft(S.UIState(config={}, preset=1))}),),
                     source=W.TextBuf("C:/v/clip.mov", 13))
    for status, txt in (("VALID", "arquivo encontrado"), ("NOT_FOUND", "não encontrado"),
                        ("INVALID", "informe um arquivo"), ("CHECKING", "verificando")):
        out = text_of(S.UIState(**{**base.__dict__, "source_status": status}))
        assert txt in out, status
        assert "clip.mov" in out and "PROGRAM" in out and "ENTER → CONFIGURATION" in out
        assert_fits(out)
        assert_no_emoji(out)
    out = text_of(S.UIState(**{**base.__dict__, "source_status": "VALID", "source_dims": (1080, 1920)}))
    assert "1080 × 1920" in out and "clip_Hollywood" in out


def test_source_preset5_shows_disabled_batch():
    s = S.UIState(config={}, screen=S.SOURCE, preset=5)
    out = text_of(s)
    assert "É um batch de pasta?" in out and "chega no P3D" in out and "ENTER → ADVANCED" in out


def test_path_field_long_path_keeps_cursor_visible():
    buf = W.TextBuf("C:/" + "a" * 200 + "/z.mov", 206)
    txt = __import__("ui.tui.screens", fromlist=["path_field"]).path_field(buf, 60)
    assert len(txt.plain) <= 61 and "z.mov" in txt.plain
```

O nome de saída esperado (`clip_Hollywood…`) depende de `EncodeConfig.output_path()`; se o padrão real do preset 1 for outro, ajustar só essa string ao valor que `forms.output_name` devolve para `input="C:/v/clip.mov"` e registrar no relatório.

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_screens_config.py -v` → FAIL.

- [ ] **Step 3: Implement** — em `ui/tui/screens.py`: imports `from ui.tui import forms as F` e `from ui.tui import widgets as W`; atualizar `STATUS`, `FOOTER_KEYS`, `_rail_active`, a condição do trilho em `header`; e acrescentar:

```python
def path_field(buf: W.TextBuf, width: int) -> Text:
    text, cur = buf.text, buf.cursor
    start = max(0, cur - width + 1)
    view = text[start:start + width]
    pos = cur - start
    out = Text()
    out.append(view[:pos], style="value")
    out.append(view[pos:pos + 1] or " ", style="reverse")
    out.append(view[pos + 1:], style="value")
    return out


def _home(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = hero([Text(""), Text("   REELS ENCODER", style="title"),
                Text("   Premiere Workspace · escolha um fluxo", style="muted")], height=7)
    menu = Text()
    for i, label in enumerate(F.PRESET_LABELS):
        n = i + 1
        enabled = n in F.ENABLED_PRESETS
        focused = i == s.home_focus
        prefix = f"{g['tab_l']}{g['arrow']} " if focused else "   "
        line = f"{prefix}{n}  {label}" + ("" if enabled else "   — chega no P3D")
        menu.append(line + "\n\n", style="tab.active" if focused else ("value" if enabled else "muted"))
    help_txt = Text(F.PRESET_HELP[s.home_focus + 1], style="value")
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(panel(menu, "FLUXOS", height=17), panel(help_txt, "O QUE FAZ", height=17))
    return Group(top, mid, panel(kv_table(s.system), "SYSTEM", height=5))


_SOURCE_STATUS = {
    "VALID": ("✓ arquivo encontrado", "ok"),
    "NOT_FOUND": ("✗ arquivo não encontrado", "err"),
    "INVALID": ("⚠ informe um arquivo de vídeo", "warn"),
    "CHECKING": ("verificando…", "muted"),
}


def _source(s: S.UIState) -> RenderableType:
    d = {**S.draft(s), "input": W.clean_path(s.source.text) or None}
    msg, style = _SOURCE_STATUS.get(s.source_status, ("—", "muted"))
    rows = []
    if s.preset == 5:
        rows.append(("BATCH", Text("É um batch de pasta?  off  — chega no P3D", style="muted")))
    rows += [
        ("ARQUIVO", path_field(s.source, 60)),
        ("STATUS", Text(msg, style=style)),
        ("DIMENSÕES", f"{s.source_dims[0]} × {s.source_dims[1]}" if s.source_dims else "—"),
        ("SAÍDA", F.output_name(d)),
    ]
    left = panel(kv_table(rows), "SOURCE", height=26)
    right = Panel(C.viewer_frame(fit=d.get("fit", "contain"), src_dims=s.source_dims, title="PROGRAM"),
                  height=26, box=PANEL_BOX, border_style="panel.border")
    mid = Table.grid(expand=True)
    mid.add_column(ratio=76)
    mid.add_column(ratio=40)
    mid.add_row(left, right)
    nxt = "ENTER → ADVANCED" if s.preset == 5 else "ENTER → CONFIGURATION"
    return Group(mid, panel(Text(f" {nxt}", style="accent"), "PRÓXIMO", height=4))


SCREEN_RENDERERS[S.HOME] = _home
SCREEN_RENDERERS[S.SOURCE] = _source
```

Atenção: `header` lê `RAIL.index(_rail_active(s))` — os novos nomes já estão em `RAIL`. Os testes P3B do READY continuam passando porque para READY o índice é 4 (os 4 primeiros seguem ✓).

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v`; ruff. Exportar HOME e SOURCE (120×40) para `.superpowers/sdd/<workspace>/task-6-exports.txt` como evidência.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens_config.py
git commit -m "feat(tui): telas HOME e SOURCE (P3C)"
```

---

### Task 7: `screens.py` (2/2) — CONFIGURATION, ADVANCED, PREVIEW e READY com erro

**Files:**
- Modify: `ui/tui/screens.py`
- Test: `ui/tui/test_screens_config.py` (acrescentar)

**Interfaces:**
- Consumes: Tasks 4–6.
- Produces: `SCREEN_RENDERERS[S.CONFIGURATION]`, `[S.ADVANCED]`, `[S.PREVIEW]`; helpers `field_rows(s) -> Table`, `preview_rows(cfg: dict) -> list[tuple[str, str]]`, `preview_chips(cfg: dict) -> list[tuple[str, bool]]`; `_ready` mostra `s.ready_error` em `err` acima da linha de ações.

Regras (Phase 2 §J, §K, §L; Sign-off #6):

- Linha de campo: prefixo `▎▸ ` no focado (estilo `tab.active` na linha inteira) ou 3 espaços; rótulo (largura 44); valor: `choice` → `◂ valor ▸`; `toggle` → `[on]`/`[off]` (`ok`/`muted`); `number` → valor formatado (`{:+.1f}` exposição, `{:.2f}` saturação, inteiro threads) ou, com `edit` no campo focado, o buffer com cursor (`path_field`); `CONTINUE` → botão `[ CONTINUAR ▶ ]`. `field_error` em `err` na linha abaixo do campo focado.
- CONFIGURATION: faixa 118×4 (`pipeline_label(draft)`, arquivo de entrada) · formulário 72×29 | PADRÕES 44×29 (somente leitura: `lut`, `hdr`, `tonemap`, `loudnorm`, `ebu_meter`, `enhance`, `dither`, `performance`, `scale` do rascunho).
- ADVANCED: barra de abas (aba ativa `▎Nome` em `tab.active`; com `tab_focus`, `▎▸Nome`) · regra · campos 74×29 | SETTINGS 42×29 (`kv_table(preview_rows(draft))`).
- `preview_rows` (ordem exata de `ui/components.settings_preview`, sem emoji): `Pipeline` (Cineon Film | FFmpeg Native) · `Mode` (upper) · `FPS` · `Scale / Fit` (`"{scale} · {fit}"`) · `LUT` (Hollywood | off) · `HDR` · `Tonemap` · `Audio` (`"loudnorm {loudnorm} · −14 LUFS"`) · `Performance` · se Cineon on: `Exposure / Sat` (`"{exposure:+.1f} EV · {saturation:.2f}"`).
- `preview_chips`: `LUT` (lut on) · `Loudnorm` (loudnorm on) · `Enhance` (enhance on) · `AI` (enhance and ai on) · `MCTF` (enhance, ai and mctf on) · `Dither` (dither != off) · `EBU Meter` (ebu_meter on); render com `C.quality_chip(label, status)` em linha.
- PREVIEW: card 118×28 titulado `PREVIEW · <entrada> → <saída>` com PROGRAM 34×20 (`viewer_frame`) | EXPORT SETTINGS 78×20 (`preview_rows`) e a linha de chips; ações `[ CONTINUAR ▶ READY ]` (foco 0) e `[ REVISAR ]` (foco 1) com o focado em `tab.active`; `field_error` (erro de validação do `Armed`) em `err` acima das ações.

- [ ] **Step 1: Write the failing test** — acrescentar:

```python
from ui.tui import forms as F


def cfg_state(preset=1, **kw):
    d = {**F.new_draft(preset), "input": "C:/v/clip.mov"}
    return S.UIState(config={}, screen=kw.pop("screen", S.CONFIGURATION), preset=preset, drafts=((preset, d),), **kw)


def test_configuration_quick():
    out = text_of(cfg_state(1))
    for txt in ("Enquadramento", "FPS", "Modo", "◂ contain ▸", "CONTINUAR", "PADRÕES", "loudnorm"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_configuration_cineon_numbers_and_error():
    s = cfg_state(2, field_error="Máximo é 2.")
    out = text_of(s)
    assert "+0.0" in out and "1.00" in out and "Máximo é 2." in out


def test_configuration_number_edit_shows_buffer():
    s = cfg_state(2, edit=W.TextBuf("-0.7", 4))
    assert "-0.7" in text_of(s)


def test_advanced_each_tab():
    for i, tab in enumerate(F.TABS):
        s = cfg_state(5, screen=S.ADVANCED, tab=i)
        out = text_of(s)
        for t in F.TABS:
            assert t in out
        for f in F.visible(F.ADVANCED[tab], S.draft(s)):
            assert f.label.split(" (")[0] in out, f.label
        assert "SETTINGS" in out and "Pipeline" in out
        assert_fits(out)
        assert_no_emoji(out)
    focused_bar = text_of(cfg_state(5, screen=S.ADVANCED, tab_focus=True))
    assert "▎▸Source" in focused_bar


def test_preview_rows_and_chips():
    d = {**F.new_draft(5), "cineon_pipeline": "on", "exposure_offset": 0.5, "saturation": 0.8}
    rows = dict(__import__("ui.tui.screens", fromlist=["preview_rows"]).preview_rows(d))
    assert list(rows)[:9] == ["Pipeline", "Mode", "FPS", "Scale / Fit", "LUT", "HDR", "Tonemap", "Audio", "Performance"]
    assert rows["Exposure / Sat"] == "+0.5 EV · 0.80"
    chips = dict(__import__("ui.tui.screens", fromlist=["preview_chips"]).preview_chips(d))
    assert list(chips) == ["LUT", "Loudnorm", "Enhance", "AI", "MCTF", "Dither", "EBU Meter"]


def test_preview_screen_and_error():
    s = cfg_state(1, screen=S.PREVIEW, field_error="combinação inválida")
    out = text_of(s)
    for txt in ("PREVIEW", "EXPORT SETTINGS", "CONTINUAR", "REVISAR", "combinação inválida", "LUT", "EBU Meter"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_ready_shows_ready_error():
    s = S.UIState(config={"input": "C:/v/clip.mov", "mode": "crf", "cineon_pipeline": "off"}, screen=S.READY,
                  preset=1, output_path="C:/v/o.mp4", ready_error="arquivo de entrada não encontrado: C:/v/clip.mov")
    assert "arquivo de entrada não encontrado" in text_of(s)
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_screens_config.py -v` → os novos falham.

- [ ] **Step 3: Implement** — acrescentar a `ui/tui/screens.py`:

```python
def _value_text(s: S.UIState, field, d: dict, focused: bool) -> Text:
    if field is F.CONTINUE:
        return Text("[ CONTINUAR ▶ ]", style="tab.active" if focused else "accent")
    if focused and s.edit is not None and field.kind == "number":
        return path_field(s.edit, 20)
    v = d.get(field.name)
    if field.kind == "choice":
        return Text(f"◂ {v} ▸")
    if field.kind == "toggle":
        return Text(f"[{v}]", style="ok" if v == "on" else "muted")
    if field.name == "exposure_offset":
        return Text(f"{float(v):+.1f}")
    if field.name == "saturation":
        return Text(f"{float(v):.2f}")
    return Text(str(v))


def field_rows(s: S.UIState) -> Table:
    g = glyphs()
    d = S.draft(s)
    items = S.form_items(s)
    cur = min(S.focus_of(s, S.focus_key(s)), len(items) - 1)
    in_fields = not (s.screen == S.ADVANCED and s.tab_focus)
    t = Table.grid(padding=(0, 1))
    t.add_column(width=3, no_wrap=True)
    t.add_column(width=44, no_wrap=True, overflow="ellipsis")
    t.add_column(no_wrap=True, overflow="ellipsis")
    for i, field in enumerate(items):
        focused = in_fields and i == cur
        style = "tab.active" if focused else "value"
        mark = f"{g['tab_l']}{g['arrow']}" if focused else ""
        label = "" if field is F.CONTINUE else field.label
        t.add_row(Text(mark, style=style), Text(label, style=style), _value_text(s, field, d, focused))
        if focused and s.field_error:
            t.add_row(Text(""), Text(s.field_error, style="err"), Text(""))
    return t


def preview_rows(cfg: dict) -> list:
    rows = [
        ("Pipeline", "Cineon Film" if cfg.get("cineon_pipeline") == "on" else "FFmpeg Native"),
        ("Mode", str(cfg.get("mode", "")).upper()),
        ("FPS", str(cfg.get("fps"))),
        ("Scale / Fit", f"{cfg.get('scale')} · {cfg.get('fit')}"),
        ("LUT", "Hollywood" if cfg.get("lut") == "on" else "off"),
        ("HDR", str(cfg.get("hdr"))),
        ("Tonemap", str(cfg.get("tonemap"))),
        ("Audio", f"loudnorm {cfg.get('loudnorm')} · −14 LUFS"),
        ("Performance", str(cfg.get("performance"))),
    ]
    if cfg.get("cineon_pipeline") == "on":
        rows.append(("Exposure / Sat", f"{float(cfg.get('exposure_offset', 0)):+.1f} EV · {float(cfg.get('saturation', 1)):.2f}"))
    return rows


def preview_chips(cfg: dict) -> list:
    enh = cfg.get("enhance") == "on"
    ai = enh and cfg.get("enhance_ai") == "on"
    return [
        ("LUT", cfg.get("lut") == "on"),
        ("Loudnorm", cfg.get("loudnorm") == "on"),
        ("Enhance", enh),
        ("AI", ai),
        ("MCTF", ai and cfg.get("mctf") == "on"),
        ("Dither", cfg.get("dither") != "off"),
        ("EBU Meter", cfg.get("ebu_meter") == "on"),
    ]


def _chips_line(cfg: dict) -> Text:
    out = Text(" ")
    for label, ok in preview_chips(cfg):
        out.append_text(C.quality_chip(label, ok))
        out.append("   ")
    return out


_DEFAULTS_SHOWN = ("lut", "hdr", "tonemap", "loudnorm", "ebu_meter", "enhance", "dither", "performance", "scale")


def _configuration(s: S.UIState) -> RenderableType:
    d = S.draft(s)
    strip = panel(kv_table([("PIPELINE", pipeline_label(d)), ("ENTRADA", basename(d.get("input")))]),
                  "RESUMO", height=4)
    asked = {f.name for f in F.form_for(s.preset)}
    defaults = kv_table([(n, str(d.get(n))) for n in _DEFAULTS_SHOWN if n not in asked])
    row = Table.grid(expand=True)
    row.add_column(ratio=72)
    row.add_column(ratio=44)
    row.add_row(panel(field_rows(s), "CONFIGURATION", height=29), panel(defaults, "PADRÕES", height=29))
    return Group(strip, row)


def _tab_bar(s: S.UIState) -> Text:
    g = glyphs()
    out = Text(" ")
    for i, name in enumerate(F.TABS):
        if i == s.tab:
            mark = f"{g['tab_l']}{g['arrow']}" if s.tab_focus else g["tab_l"]
            out.append(f"{mark}{name}   ", style="tab.active")
        else:
            out.append(f" {name}   ", style="tab.inactive")
    return out


def _advanced(s: S.UIState) -> RenderableType:
    d = S.draft(s)
    row = Table.grid(expand=True)
    row.add_column(ratio=74)
    row.add_column(ratio=42)
    row.add_row(panel(field_rows(s), F.TABS[s.tab].upper(), height=29),
                panel(kv_table(preview_rows(d)), "SETTINGS", height=29))
    return Group(_tab_bar(s), Rule(characters="─", style="muted"), row)


def _preview(s: S.UIState) -> RenderableType:
    g = glyphs()
    d = S.draft(s)
    title = f"PREVIEW · {basename(d.get('input'))} {g['arrow']} {F.output_name(d)}"
    inner = Table.grid(expand=True)
    inner.add_column(ratio=34)
    inner.add_column(ratio=78)
    inner.add_row(Panel(C.viewer_frame(fit=d.get("fit", "contain"), src_dims=s.source_dims, title="PROGRAM"),
                        height=20, box=PANEL_BOX, border_style="panel.border"),
                  panel(kv_table(preview_rows(d)), "EXPORT SETTINGS", height=20))
    card = Panel(Group(inner, _chips_line(d)), title=f"[panel.title]{title}[/]", title_align="left",
                 box=PANEL_BOX, border_style="accent", height=28)
    actions = Text("   ")
    for i, label in enumerate(("CONTINUAR ▶ READY", "REVISAR")):
        focused = s.action_focus == i
        actions.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    parts = [card]
    if s.field_error:
        parts.append(Text(f"   {s.field_error}", style="err"))
    parts.append(actions)
    return Group(*parts)


SCREEN_RENDERERS[S.CONFIGURATION] = _configuration
SCREEN_RENDERERS[S.ADVANCED] = _advanced
SCREEN_RENDERERS[S.PREVIEW] = _preview
```

Em `_ready`, antes de `return Group(top, mid, qc, actions)`, montar `parts = [top, mid, qc]`, acrescentar `Text(f"   {s.ready_error}", style="err")` quando houver e depois `actions`; `return Group(*parts)`.

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v`; ruff. Exportar CONFIGURATION (1 e 2), cada aba do ADVANCED e PREVIEW (120×40) para `task-7-exports.txt`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens_config.py
git commit -m "feat(tui): telas CONFIGURATION, ADVANCED e PREVIEW (P3C)"
```

---

### Task 8: `app.py` — HOME como início, ações e Tools

**Files:**
- Modify: `ui/tui/app.py`
- Test: `ui/tui/test_app.py` (ajustar helpers e acrescentar)

**Interfaces:**
- Consumes: `state` (ações, eventos), `widgets.clean_path`, `ui.probe.probe_source_dims(path) -> tuple | None`, `ui.config.EncodeConfig`, `RE._validate_args_consistency(ns) -> str | None`, `D._single_output_path(ns) -> str`, `ui.launcher._flow_tools(con) -> None`.
- Produces: `App(ns=None, *, console=None, run_single=None, reader_factory=None, live_factory=None, clock=..., sleep=..., perf=None, size=None, output_path=None, terminate=None, tools=None, probe=None, system=None)`. Com `ns` → comportamento P3B (começa no READY). Sem `ns` → começa na HOME.

Comportamento:

- `__init__` sem `ns`: `self.state = S.UIState(config={}, screen=S.HOME, system=system or self._system_rows())`; `self._ns = None`. `_system_rows()` → `(("FFmpeg", basename(RE.FFMPEG)), ("ffprobe", basename(RE.FFPROBE)), ("ffplay", "ok" se `shutil.which("ffplay")` ou existe `ffplay[.exe]` ao lado de `RE.FFMPEG`, senão "⚠ ausente — monitor EBU desligado"), ("hardware", "detectado no início do encode"))`.
- `run()`: guardar `self._reader`, `self._capture` (`ConsoleCapture(RE.console, self._queue.put)`) e `self._orig_stderr` como atributos para o Tools poder suspender e retomar; mesma ordem de restauração do P3B.
- `_drain`: interromper o esvaziamento quando `self.state.action in S.ACTIONS` (antes: só start/exit).
- `_session`:

```python
    def _session(self) -> int:
        while True:
            self._until(lambda s: s.action in S.ACTIONS)
            act = self.state.action
            self.state = replace(self.state, action=None)
            if act == "exit":
                return 0
            if act == "tools":
                self._run_tools()
                continue
            if act == "arm":
                self._arm()
                continue
            if act == "check_source":
                self._check_source()
                continue
            inp = self.state.config.get("input") or ""
            if not os.path.isfile(inp):
                self.state = S.apply(self.state, S.ReadyBlocked(f"arquivo de entrada não encontrado: {inp}"))
                continue
            break
        ns = self._ns if self._ns is not None else argparse.Namespace(**self.state.config)
        code = self._run_single(ns, self._queue, self._control, self._tick)
        self._drain()
        self.state = S.apply(self.state, S.Finished(code))
        self._until(lambda s: s.action == "exit")
        return code
```

- `_check_source`: `path = W.clean_path(self.state.source.text)`; status `INVALID` se vazio ou `os.path.isdir`, `VALID` se `os.path.isfile`, senão `NOT_FOUND`; `dims = self._probe(path)` só se `VALID` (cache: não repetir a mesma `path`); `self.state = S.apply(self.state, S.SourceChecked(path, status, dims))`.
- `_arm`: `cfg = EncodeConfig.model_validate(S.draft(self.state))`; `ns = cfg.to_namespace()`; `err = RE._validate_args_consistency(ns)`; `out = D._single_output_path(ns)`; `self.state = S.apply(self.state, S.Armed(vars(ns), out, os.path.exists(out), err))`.
- `_run_tools`: `self._reader.stop(); self._reader.restore(); sys.stderr = self._orig_stderr; self._capture.__exit__(None, None, None); self._live.stop()`; `try: self._tools(self._console)` `finally: self._live.start(); self._capture.__enter__(); sys.stderr = _Sink(self._queue.put); self._reader = self._reader_factory(self._queue.put); self._reader.start()`. `tools` padrão: `lambda con: ui.launcher._flow_tools(con)` (import local).
- `_summary`: além do P3B, `code == 0` e `s.screen == S.HOME` → imprime `"[warn]Cancelado pelo usuário.[/warn]"`.

- [ ] **Step 1: Write the failing test** — em `ui/tui/test_app.py`: dar a `FakeLive` os métodos `start()`/`stop()` (contadores `starts`, `stops`) e acrescentar:

```python
def make_home(tmp_path, keys, run_single=None, **kw):
    live = FakeLive()
    reader = FakeReader(keys)
    holder = []

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS:
            holder[0]._queue.put(S.Key("ENTER"))

    app = A.App(run_single=run_single or (lambda *a: 0), reader_factory=reader, live_factory=lambda c: live,
                clock=Clock(), sleep=sleep, perf=lambda: (10.0, 20.0, 1.0), size=lambda: (120, 40),
                system=(("FFmpeg", "x"),), probe=lambda p: (1080, 1920), **kw)
    holder.append(app)
    return app, live, reader


def keys_for(text):
    return [("SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR"), ch) for ch in text]


class CharReader(FakeReader):
    def start(self):
        for k in self.keys:
            name, ch = k if isinstance(k, tuple) else (k, None)
            self.emit(S.Key(name, ch))


def test_home_esc_exits_zero_and_prints_cancel(tmp_path):
    from rich.console import Console
    import io
    buf = io.StringIO()
    app, _, _ = make_home(tmp_path, ["ESC"], console=Console(file=buf, width=120))
    assert app.run() == 0
    assert "Cancelado pelo usuário." in buf.getvalue()


def test_full_flow_home_to_completed(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    seen = []

    def run(ns_, q, control, on_tick):
        seen.append(ns_)
        return 0

    keys = [("CHAR", "1")] + keys_for(str(src)) + ["ENTER"] * 7
    live = FakeLive()
    app = A.App(run_single=run, reader_factory=CharReader(keys), live_factory=lambda c: live, clock=Clock(),
                sleep=lambda _: None, perf=lambda: (None, None, None), size=lambda: (120, 40),
                system=(), probe=lambda p: None)
    assert app.run() == 0
    assert seen and seen[0].input == str(src) and seen[0].cineon_pipeline == "off"


def test_check_source_quoted_path_with_spaces_is_valid(tmp_path):
    d = tmp_path / "Meus Vídeos"
    d.mkdir()
    f = d / "x.mov"
    f.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.apply(app.state, S.Key("CHAR", "1"))
    for name, ch in keys_for(f'"{f}"'):
        app.state = S.apply(app.state, S.Key(name, ch))
    app._check_source()
    assert app.state.source_status == "VALID" and app.state.source_dims == (1080, 1920)


def test_ready_revalidates_missing_input(tmp_path, monkeypatch):
    ran = []
    seen_errors = []
    app, _, _ = make_home(tmp_path, ["ENTER", "ESC", "ESC", "ESC", "ESC", "ESC"],
                          run_single=lambda *a: ran.append(1) or 0)
    app.state = S.UIState(config={"input": str(tmp_path / "missing.mov")}, screen=S.READY, preset=1)
    orig_apply = S.apply

    def spy(s, ev):
        out = orig_apply(s, ev)
        if out.ready_error:
            seen_errors.append(out.ready_error)
        return out

    monkeypatch.setattr(S, "apply", spy)
    assert app.run() == 0
    assert ran == [] and seen_errors and "missing.mov" in seen_errors[0]


def test_tools_suspends_and_resumes(tmp_path):
    calls = []
    readers = iter([CharReader([("CHAR", "4")]), CharReader(["ESC"])])
    live = FakeLive()
    app = A.App(reader_factory=lambda emit: next(readers)(emit), live_factory=lambda c: live, clock=Clock(),
                sleep=lambda _: None, perf=lambda: (None, None, None), size=lambda: (120, 40), system=(),
                probe=lambda p: None, tools=lambda con: calls.append("tools"))
    assert app.run() == 0
    assert calls == ["tools"] and live.stops == 1 and live.starts == 1


def test_ctrl_c_in_configuration_returns_130(tmp_path):
    app, _, reader = make_home(tmp_path, [("CHAR", "1")])
    orig = app._tick

    def tick():
        orig()
        if app.state.screen == S.SOURCE:
            raise KeyboardInterrupt

    app._tick = tick
    assert app.run() == 130 and reader.restored
```

`test_ready_revalidates_missing_input` espiona `S.apply` (o `App` chama `S.apply` pelo módulo `ui.tui.state`, então o `monkeypatch` no módulo vale para ele). A sequência de ESC volta READY → PREVIEW → CONFIGURATION (`came_from` padrão) → SOURCE → HOME → sair.

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_app.py -v` → novos falham.

- [ ] **Step 3: Implement** — aplicar o comportamento descrito acima em `ui/tui/app.py` (imports novos: `argparse`, `shutil`, `from ui.config import EncodeConfig`, `from ui.tui import widgets as W`; `probe` padrão importa `ui.probe.probe_source_dims` local). Os testes P3B existentes (construídos com `ns`) devem continuar verdes sem alteração além da `FakeLive` com `start`/`stop`.

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v` 3× (flake); `venv\Scripts\python.exe -m pytest ui/ test_render_queue.py -q --timeout=120`; ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/app.py ui/tui/test_app.py
git commit -m "feat(tui): App começa na HOME, executa ações de configuração e Tools (P3C)"
```

---

### Task 9: `__main__.py` — preflight antes, sem wizard

**Files:**
- Modify: `ui/tui/__main__.py`
- Test: `ui/tui/test_main.py` (ajustar)

**Interfaces:**
- Consumes: `App(console=...)` (Task 8).
- Produces: `main()` = guarda (inalterada) → `_missing_binaries()` (1 + `dependency_error_card`) → `App(console=console).run()`. Remove `run_launcher` e a validação daqui (validação agora no `_arm`).

- [ ] **Step 1: Ajustar testes** — em `ui/tui/test_main.py`: remover `test_launcher_cancel_returns_zero` e `test_validation_error_returns_2`; em `test_missing_binaries_returns_1` e `test_runs_app_and_returns_its_code`, remover o monkeypatch de `run_launcher`/`_validate_args_consistency` e trocar o fake do App por `lambda console=None: types.SimpleNamespace(run=lambda: 130)`; acrescentar:

```python
def test_main_does_not_use_line_wizard(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(M, "App", lambda console=None: types.SimpleNamespace(run=lambda: 0))
    assert not hasattr(M, "run_launcher")
    assert M.main() == 0
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_main.py -v` → FAIL.

- [ ] **Step 3: Implement** — em `ui/tui/__main__.py`, remover `from ui.launcher import run_launcher` e, em `main()`, substituir o trecho após a guarda por:

```python
    missing = _missing_binaries()
    if missing:
        console.print(C.dependency_error_card(missing))
        return 1
    return App(console=console).run()
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v`; ruff; `venv\Scripts\python.exe -c "import ui.tui.__main__"` (sem efeito colateral).

- [ ] **Step 5: Commit**

```bash
git add ui/tui/__main__.py ui/tui/test_main.py
git commit -m "feat(tui): entrada sem wizard de linha e com preflight antes da TUI (P3C)"
```

---

### Task 10: Paridade TUI × wizard de linha

**Files:**
- Create: `ui/tui/test_parity_wizard.py`

**Interfaces:**
- Consumes: `ui.launcher.run_launcher(console)`, `state`, `forms`, `ui.config.EncodeConfig`.

Antes de escrever, ler o bloco de imports de `ui/launcher.py` para saber de onde `ask_choice`, `ask_path`, `ask_select`, `ask_toggle`, `ask_number`, `Confirm` e `probe_source_dims` são resolvidos (monkeypatch no módulo `ui.launcher` se importados por nome; senão no módulo de origem). Ajustar só os alvos do monkeypatch.

- [ ] **Step 1: Write the test** — `ui/tui/test_parity_wizard.py`

```python
import io
from dataclasses import replace

import pytest
from rich.console import Console

import ui.launcher as L
from ui.config import EncodeConfig
from ui.tui import forms as F
from ui.tui import state as S

SCENARIOS = [
    (1, {"Enquadramento": "cover", "FPS": "24", "Modo": "2pass"},
     {"fit": "cover", "fps": "24", "mode": "2pass"}),
    (2, {"Exposure": -0.5, "Satura": 1.2, "Enquadramento": "cover"},
     {"exposure_offset": -0.5, "saturation": 1.2, "fit": "cover"}),
    (5, {"Pipeline Cineon": "on", "Exposure": 0.5, "Satura": 0.8, "Tonemap": "hable"},
     {"cineon_pipeline": "on", "exposure_offset": 0.5, "saturation": 0.8, "tonemap": "hable"}),
    (5, {"Decisões via AI": "on", "MCTF": "on", "Dither": "on"},
     {"enhance_ai": "on", "mctf": "on", "dither": "on"}),
    (5, {"Enhancement engine": "off", "Threads": 4, "Performance": "speed"},
     {"enhance": "off", "threads": 4, "performance": "speed"}),
]


def wizard_ns(monkeypatch, preset, path, answers):
    def pick(message, default):
        for k, v in answers.items():
            if k in message:
                return v
        return default

    monkeypatch.setattr(L, "ask_choice", lambda con, title, options, default=1: preset)
    monkeypatch.setattr(L, "ask_path", lambda con, message, must_exist=True: path)
    monkeypatch.setattr(L, "ask_select", lambda con, message, options, default: pick(message, default))
    monkeypatch.setattr(L, "ask_toggle", lambda con, message, default_on=True: pick(message, "on" if default_on else "off"))
    monkeypatch.setattr(L, "ask_number",
                        lambda con, message, default, lo=None, hi=None, integer=False: pick(message, default))
    monkeypatch.setattr(L, "probe_source_dims", lambda p: None, raising=False)
    monkeypatch.setattr(L.Confirm, "ask",
                        lambda message, *a, **k: True if "Iniciar" in message else k.get("default", False))
    return L.run_launcher(Console(file=io.StringIO(), width=120))


def press(s, name, ch=None):
    s = S.apply(s, S.Key(name, ch))
    return replace(s, action=None) if s.action == "check_source" else s


def type_text(s, text):
    for ch in text:
        name = "SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR")
        s = press(s, name, ch)
    return s


def current(s):
    items = S.form_items(s)
    return items[min(S.focus_of(s, S.focus_key(s)), len(items) - 1)]


def goto_field(s, name):
    if s.screen == S.ADVANCED:
        tab = next(i for i, t in enumerate(F.TABS) if any(f.name == name for f in F.ADVANCED[t]))
        s = replace(s, tab=tab, tab_focus=False)
    s = replace(s, focus=tuple((k, v) for k, v in s.focus if k != S.focus_key(s)))
    for _ in range(len(S.form_items(s))):
        if current(s).name == name:
            return s, current(s)
        s = press(s, "DOWN")
    raise AssertionError(f"campo não alcançado: {name}")


def set_field(s, name, value):
    s, field = goto_field(s, name)
    if field.kind == "number":
        for ch in str(value):
            s = press(s, "CHAR", ch)
        return press(s, "ENTER")
    for _ in range(len(field.options) + 2):
        if S.draft(s)[name] == value:
            return s
        s = press(s, "RIGHT")
    assert S.draft(s)[name] == value, (name, value)
    return s


def tui_ns(preset, path, values):
    s = S.UIState(config={}, screen=S.HOME)
    s = press(s, "CHAR", str(preset))
    s = type_text(s, path)
    s = S.apply(s, S.SourceChecked(path, "VALID"))
    s = press(s, "ENTER")
    for name, value in values.items():
        s = set_field(s, name, value)
    return EncodeConfig.model_validate(S.draft(s)).to_namespace()


@pytest.mark.parametrize("preset,answers,values", SCENARIOS)
def test_tui_form_matches_line_wizard(monkeypatch, tmp_path, preset, answers, values):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    want = wizard_ns(monkeypatch, preset, str(src), answers)
    got = tui_ns(preset, str(src), values)
    assert vars(got) == vars(want)
```

A ordem dos `values` em cada cenário segue a ordem do formulário (campos que habilitam outros vêm antes). `goto_field` zera o foco da tela/aba e desce até o campo — a navegação em si é testada nas Tasks 4–5; aqui o que importa é que os **valores** passem pelas mesmas teclas e pelo mesmo `apply_change`.

- [ ] **Step 2: Run** — `venv\Scripts\python.exe -m pytest ui/tui/test_parity_wizard.py -v` → 5 verdes. Se algum cenário divergir, **parar**: o relatório deve trazer o diff dos dois `Namespace` e a causa (diferença de regra entre wizard e `forms`). Corrigir apenas `forms.py`/reducer para espelhar o wizard; nunca o teste nem o wizard.

- [ ] **Step 3: Commit**

```bash
git add ui/tui/test_parity_wizard.py
git commit -m "test(tui): paridade do formulário da TUI com o wizard de linha (P3C)"
```

---

### Task 11: Verificação manual no Windows Terminal (usuário)

- [ ] Roteiro (Orquestrador escreve; pasta isolada curta como no P3B) com: preset 1 completo até COMPLETED; preset 2 ajustando exposição/saturação (setas e digitação); preset 5 passando pelas 5 abas (Cineon on/off, enhance/AI/MCTF); REVISAR no PREVIEW; arrastar um arquivo para o campo de caminho; caminho inexistente (NOT FOUND); Tools e volta à HOME; preset 3 desativado; ESC na HOME (código 0 + "Cancelado pelo usuário."); Ctrl+C numa tela de configuração (130). Após cada: `$LASTEXITCODE`, `Get-Process ffmpeg`, terminal normal.
- [ ] Usuário roda e devolve; Orquestrador registra em VALIDATION.md.

---

### Task 12: Fechamento (Orquestrador)

- [ ] Suíte canônica com `venv\Scripts\python.exe` + `ruff check .`.
- [ ] STATE.md / FINDINGS.md / VALIDATION.md; merge/push só com pedido do usuário.
