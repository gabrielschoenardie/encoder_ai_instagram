# P3D Batch de Pasta na TUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m ui.tui` passa a rodar batch de pasta (preset 3 e o ramo "Pasta" do preset 5) de HOME até um relatório final da fila em tela cheia, e o ffprobe do SOURCE deixa de poder congelar a TUI (P3CF1).

**Architecture:** `forms.py` ganha o formulário BATCH e dois campos de **estado de formulário** guardados no rascunho (`source_kind`, `output_dir_on`) que `F.to_config` remove antes de validar o `EncodeConfig`. O reducer `state.py` ganha SOURCE de pasta (status `EMPTY`, seletor TIPO no preset 5), o campo de caminho da pasta de saída, e os estados QUEUE/REPORT alimentados pelos eventos de fila que `D.run_batch` já emite. O `App` conta vídeos com `RE.find_video_files`, arma o batch sem saída de arquivo único, revalida a pasta no START e chama `run_batch` (injetável). `ui/probe.py` ganha `timeout`.

**Tech Stack:** Python ≥ 3.11, Rich, Pydantic (via `ui/config.py`), stdlib.

**Spec:** `docs/superpowers/specs/2026-10-06-tui-batch-queue-design.md` (ler inteiro). Wireframes/regras: `docs/Phase_2_TUI_Specification.md` §C, §D.3, §I, §J, §L, §M, §S, §T, §V. Ciclo anterior: `docs/superpowers/specs/2026-10-05-tui-config-screens-design.md` e `docs/superpowers/plans/2026-10-05-tui-config-screens.md`.

## Global Constraints

- Inalterados: motor (`Reels_Encoder_v2_FINAL.py`), `ui/tui_driver.py` (`run_batch`), `reporter.py`, `ui/launcher.py`, `ui/config.py`. Única mudança fora de `ui/tui/`: `timeout` em `ui/probe.py` (P3CF1).
- Paridade: para as mesmas escolhas a TUI produz o mesmo `EncodeConfig.to_namespace()` que o wizard (`ui/launcher.py` `_flow_batch` 141–148, `_flow_advanced` 172–186). Rótulos verbatim do wizard sem "?" final: "Definir pasta de saída separada", "Pasta de saída", "Usar film look (Cineon)", "Pasta de saída separada".
- Toggle de pasta de saída é estado de formulário, não campo de `EncodeConfig`: off ⇒ `output_dir = None`; on ⇒ caminho digitado (aspas removidas com `W.clean_path`); on + vazio ⇒ "Informe a pasta de saída." e não avança. Em arquivo único `output_dir` é sempre `None`.
- Códigos de saída: 0 ok, 1 algum job falhou, 2 validação, 130 interrompido (B-7). Cancelar = fila inteira (B-5).
- 120 × 40; nenhuma linha > 120 colunas; sem emoji nas regiões fixas (D-20). `⚡` é emoji-presentation e reprova em `assert_no_emoji` — o status interrompido usa `⚠ CANCELLED`. Seta de foco é `▸` (nunca `▶`).
- Toda célula de `Table` e todo título que contém nome de arquivo/pasta é `Text(...)` ou passa por `rich.markup.escape` (nomes com `[1080p]` não podem virar markup).
- Testes nunca fixam um estilo de canto de caixa (`┌` no Windows, `╭` no Linux).
- Testes de App ponta a ponta: teclas enfileiradas antes do encode são descartadas no `_arm` e drenadas depois do `run_*`; ENTER no READY e no REPORT é empurrado pelo `sleep` injetado (padrão `make_home`/`test_full_flow_home_to_completed`), com o `Clock` que avança 0,5 s por chamada (respeita `READY_HOLD_S`/`KEY_GAP_S`). Teclas com caractere usam `CharReader`, não `FakeReader`.
- Invariantes do P3C mantidas: erro de campo some ao mudar o foco; ENTER no ADVANCED avança campo a campo e aba a aba; cadeias de ESC nunca formam ciclo (`came_from`/`adv_back`).
- Python: `venv\Scripts\python.exe`. Suíte canônica: `venv\Scripts\python.exe -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Lint: `venv\Scripts\python.exe -m ruff check .` (o CI roda só `ruff check`; regras E4/E7/E9/F/I — imports ordenados).
- Commits em português, no formato `tipo(escopo): descrição (P3D)`, terminando com os trailers de atribuição da sessão executora (`Co-Authored-By: …` e `Claude-Session: …`), como nos commits do P3C.
- Sem comentários narrativos, sem abstrações novas além das listadas, sem refatorar (CLAUDE.md).

## Review Focus

1. **Eventos da fila sem carimbo** — `run_batch` emite `QueueInit/JobStart/JobSkip/JobDone/QueueDone` com `ts=0.0`; duração, ETA e tempo total têm de vir do relógio do tick (`s.now`), nunca negativos nem "época". → `test_events_without_timestamp_use_tick_clock` (Task 4).
2. **Estágio QC ou fim da fila com DETAILS/LOG aberto em batch** — nunca abre a tela QC de arquivo único; o fim da fila leva ao REPORT. → `test_qc_stage_in_batch_never_opens_qc_screen` (Task 4).
3. **Output parcial que não pôde ser removido após cancelar a fila** — na próxima rodada ele seria pulado como "saída já existe"; o REPORT tem de avisar. → `test_report_warns_unremovable_partial` (Task 6).
4. **Pasta onde se espera arquivo e vice-versa** (TIPO trocado, arquivo arrastado no preset 3) — INVALID, nunca VALID; subpastas e arquivos de saída do motor não contam. → `test_check_source_folder_counts_videos_like_engine` (Task 7).
5. **Nomes longos ou com colchetes** (`[2026] lote`, `clip [1080p].mov`) — sem quebra de markup, nenhuma linha > 120. → `test_preview_folder_with_brackets` (Task 5) e `test_long_and_bracketed_names_fit` (Task 6).

## File Structure

| arquivo | responsabilidade nesta fase |
|---------|-----------------------------|
| `ui/probe.py` | `PROBE_TIMEOUT_S = 10`; `timeout` no `check_output` |
| `ui/tui/forms.py` | `ENABLED_PRESETS` 1–5; `BATCH`; campos de pasta de saída na aba Source; `SOURCE_KIND/FILE/FOLDER/OUTDIR_ON/FORM_ONLY/OUTDIR_EMPTY`; `is_folder`, `to_config`, `outdir_missing`; `new_draft(3)` |
| `ui/tui/state.py` | SOURCE de pasta + TIPO; campo `path`; `Job`; QUEUE/REPORT; eventos de fila; `queue_counts`, `queue_eta` |
| `ui/tui/screens.py` | SOURCE pasta, CONFIGURATION BATCH, PREVIEW/READY de pasta, QUEUE, REPORT, trilho batch, `queue_summary` |
| `ui/tui/app.py` | `_check_source` de pasta; `_arm` batch; revalidação no START; `run_batch` injetável; resumo da fila |
| `ui/test_probe.py`, `ui/tui/test_forms.py`, `test_state_config.py`, `test_state_batch.py` (novo), `test_screens_config.py`, `test_screens_batch.py` (novo), `test_app.py`, `test_parity_wizard.py` | testes |

---

### Task 1: P3CF1 — `probe_source_dims` com timeout

**Files:**
- Modify: `ui/probe.py:16-41`
- Test: `ui/test_probe.py`

**Interfaces:**
- Produces: `ui.probe.PROBE_TIMEOUT_S = 10`; `probe_source_dims(path) -> tuple[int, int] | None` passa `timeout=PROBE_TIMEOUT_S` ao `subprocess.check_output`; estouro (`subprocess.TimeoutExpired`) cai no `except Exception` existente → `None`.

- [ ] **Step 1: Ajustar fakes e escrever os testes que falham** — em `ui/test_probe.py`:
  - imports do topo passam a ser `import json`, `import subprocess`, `import sys`, `import time` (nessa ordem), depois `import pytest`, depois os imports do projeto;
  - toda assinatura de fake `(cmd, stderr=None)` vira `(cmd, stderr=None, **kwargs)` — são 5: `_fake_check_output` dentro de `_fake_check_output_factory`, `_fake_check_output` em `test_probe_argv_contract`, os dois `_raise` e `_fake_check_output` em `test_probe_corrupted_output_returns_none`;
  - acrescentar no fim:

```python
def test_probe_passes_timeout(monkeypatch):
    seen = {}

    def _fake_check_output(cmd, stderr=None, **kwargs):
        seen.update(kwargs)
        return _payload()

    monkeypatch.setattr("ui.probe.subprocess.check_output", _fake_check_output)
    assert probe_source_dims("x.mp4") == (1920, 1080)
    assert seen["timeout"] == 10


@pytest.mark.timeout(60)
def test_probe_hung_ffprobe_returns_none_fast(monkeypatch):
    real = subprocess.check_output

    def _slow(cmd, **kwargs):
        return real([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)

    monkeypatch.setattr("ui.probe.PROBE_TIMEOUT_S", 1)
    monkeypatch.setattr("ui.probe.subprocess.check_output", _slow)
    t0 = time.monotonic()
    assert probe_source_dims("x.mp4") is None
    assert time.monotonic() - t0 < 8
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/test_probe.py -v` → `test_probe_passes_timeout` falha (`KeyError: 'timeout'`) e `test_probe_hung_ffprobe_returns_none_fast` falha (`AttributeError: PROBE_TIMEOUT_S` no monkeypatch).

- [ ] **Step 3: Implement** — em `ui/probe.py`, logo abaixo do bloco `try/except` do `FFPROBE`:

```python
PROBE_TIMEOUT_S = 10
```

e no `subprocess.check_output(...)` de `probe_source_dims`, depois de `stderr=subprocess.PIPE,`:

```python
            timeout=PROBE_TIMEOUT_S,
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/test_probe.py -v` → todos verdes (inclusive os paramétricos que comparam com `get_input_resolution`); `venv\Scripts\python.exe -m ruff check ui/probe.py ui/test_probe.py`.

- [ ] **Step 5: Commit**

```bash
git add ui/probe.py ui/test_probe.py
git commit -m "fix(probe): timeout de 10 s no ffprobe do SOURCE (P3CF1, P3D)"
```

---

### Task 2: `forms.py` — preset 3, campos de pasta de saída e estado de formulário

**Files:**
- Modify: `ui/tui/forms.py`, `ui/tui/screens.py` (só `FOOTER_KEYS[S.HOME]`), `ui/tui/app.py` (só `_arm` + import)
- Test: `ui/tui/test_forms.py`, `ui/tui/test_state_config.py` (2 testes de HOME), `ui/tui/test_screens_config.py` (`test_home_screen`), `ui/tui/test_parity_wizard.py` (`tui_ns`), `ui/tui/test_app.py` (1 teste novo)

**Interfaces:**
- Produces (em `ui.tui.forms`):
  - `SOURCE_KIND = "source_kind"`, `FILE = "file"`, `FOLDER = "folder"`, `OUTDIR_ON = "output_dir_on"`, `FORM_ONLY = frozenset({SOURCE_KIND, OUTDIR_ON})`, `OUTDIR_EMPTY = "Informe a pasta de saída."`
  - `is_folder(d: dict) -> bool` (`d[SOURCE_KIND] == FOLDER`)
  - `BATCH: tuple[Field, ...]` = toggle `OUTDIR_ON` "Definir pasta de saída separada" · `Field("output_dir", "path", "Pasta de saída")` visível só com pasta + toggle on · toggle `cineon_pipeline` "Usar film look (Cineon)"
  - `ADVANCED["Source"]` começa com toggle `OUTDIR_ON` "Pasta de saída separada" (visível só com pasta) e `output_dir` (pasta + toggle on); resto inalterado
  - `ENABLED_PRESETS = (1, 2, 3, 4, 5)`; `form_for(3) is BATCH`
  - `new_draft(3) = {**EncodeConfig.preset_batch().model_dump(), SOURCE_KIND: FOLDER, OUTDIR_ON: "off"}`; `new_draft(5) = {**EncodeConfig().model_dump(), SOURCE_KIND: FILE, OUTDIR_ON: "off"}`; 1 e 2 inalterados
  - `to_config(d: dict) -> dict` — remove `FORM_ONLY`; `output_dir = None` se não há `batch` ou toggle off
  - `outdir_missing(d: dict) -> bool` — pasta + toggle on + `output_dir` vazio
  - `apply_change` e `output_name` validam `to_config(...)`
- Nova `Field.kind`: `"path"` (texto livre; editado pelo reducer na Task 3).

- [ ] **Step 1: Write the failing tests**

Em `ui/tui/test_forms.py`, substituir `all_fields`, `test_every_field_is_an_encodeconfig_field_and_options_validate`, `test_hidden_fields_never_exposed`, `test_preset_labels_are_the_wizard_labels` e `test_new_draft_matches_factories`, e acrescentar os demais:

```python
def all_fields():
    return F.QUICK + F.CINEON + F.BATCH + tuple(f for tab in F.TABS for f in F.ADVANCED[tab])


def test_every_field_is_an_encodeconfig_field_or_form_state_and_options_validate():
    names = set(EncodeConfig.model_fields) | F.FORM_ONLY
    for f in all_fields():
        assert f.name in names, f.name
        for opt in f.options:
            EncodeConfig.model_validate({**EncodeConfig().model_dump(), f.name: opt})


def test_hidden_fields_never_exposed():
    exposed = {f.name for f in all_fields()}
    assert exposed.isdisjoint({"report", "cineon_lut", "debug", "hardware_info", "ui", "batch", "input"})


def test_preset_labels_are_the_wizard_labels():
    from ui.launcher import PRESETS
    assert F.PRESET_LABELS == tuple(PRESETS)
    assert F.ENABLED_PRESETS == (1, 2, 3, 4, 5)
    assert "P3D" not in F.PRESET_HELP[3]


def test_new_draft_matches_factories():
    assert F.new_draft(1) == EncodeConfig.preset_quick_ffmpeg().model_dump()
    assert F.new_draft(2) == EncodeConfig.preset_film_cineon().model_dump()
    assert F.new_draft(3) == {**EncodeConfig.preset_batch().model_dump(), F.SOURCE_KIND: F.FOLDER, F.OUTDIR_ON: "off"}
    assert F.new_draft(5) == {**EncodeConfig().model_dump(), F.SOURCE_KIND: F.FILE, F.OUTDIR_ON: "off"}
    assert F.is_folder(F.new_draft(3)) and not F.is_folder(F.new_draft(5)) and not F.is_folder(F.new_draft(1))


def test_batch_form_order_labels_and_visibility():
    d = F.new_draft(3)
    assert F.form_for(3) is F.BATCH
    assert [f.label for f in F.BATCH] == ["Definir pasta de saída separada", "Pasta de saída", "Usar film look (Cineon)"]
    assert [f.name for f in F.visible(F.BATCH, d)] == [F.OUTDIR_ON, "cineon_pipeline"]
    assert [f.name for f in F.visible(F.BATCH, {**d, F.OUTDIR_ON: "on"})] == [F.OUTDIR_ON, "output_dir", "cineon_pipeline"]
    assert next(f for f in F.BATCH if f.name == "output_dir").kind == "path"


def test_advanced_source_tab_outdir_fields_only_for_folder():
    d = F.new_draft(5)

    def names(dd):
        return [f.name for f in F.visible(F.ADVANCED["Source"], dd)]

    base = ["cineon_pipeline", "fit", "fps", "scale", "mode", "performance"]
    assert names(d) == base
    folder = {**d, F.SOURCE_KIND: F.FOLDER}
    assert names(folder) == [F.OUTDIR_ON] + base
    assert names({**folder, F.OUTDIR_ON: "on"}) == [F.OUTDIR_ON, "output_dir"] + base
    assert F.ADVANCED["Source"][0].label == "Pasta de saída separada"


def test_to_config_strips_form_state_and_applies_output_dir_rules():
    d = {**F.new_draft(3), "batch": "C:/v/lote", "output_dir": "D:/saida"}
    cfg = F.to_config(d)
    assert F.OUTDIR_ON not in cfg and F.SOURCE_KIND not in cfg and cfg["output_dir"] is None
    assert F.to_config({**d, F.OUTDIR_ON: "on"})["output_dir"] == "D:/saida"
    file5 = {**F.new_draft(5), "input": "C:/v/a.mov", F.OUTDIR_ON: "on", "output_dir": "D:/saida"}
    assert F.to_config(file5)["output_dir"] is None
    EncodeConfig.model_validate(F.to_config({**d, F.OUTDIR_ON: "on"}))


def test_outdir_missing():
    d = {**F.new_draft(3), "batch": "C:/v/lote", F.OUTDIR_ON: "on"}
    assert F.outdir_missing(d)
    assert F.outdir_missing({**d, "output_dir": "  "})
    assert not F.outdir_missing({**d, "output_dir": "D:/saida"})
    assert not F.outdir_missing({**d, F.OUTDIR_ON: "off"})
    assert not F.outdir_missing({**F.new_draft(5), F.OUTDIR_ON: "on"})


def test_apply_change_accepts_form_state_keys():
    nd, err = F.apply_change(F.new_draft(3), F.OUTDIR_ON, "on")
    assert err is None and nd[F.OUTDIR_ON] == "on"
    nd, err = F.apply_change(nd, "output_dir", "D:/saida")
    assert err is None and nd["output_dir"] == "D:/saida"
```

Em `ui/tui/test_state_config.py`, substituir os dois primeiros testes de HOME:

```python
def test_home_navigation_visits_all_presets_and_wraps():
    s = home()
    assert s.home_focus == 0
    for want in (1, 2, 3, 4, 0):
        s = S.apply(s, key("DOWN"))
        assert s.home_focus == want
    s = S.apply(home(), key("UP"))
    assert s.home_focus == 4


def test_home_digits_open_presets():
    s = S.apply(home(), key("CHAR", "3"))
    assert s.screen == S.SOURCE and s.preset == 3 and S.draft(s) == F.new_draft(3)
    s = S.apply(home(), key("CHAR", "4"))
    assert s.action == "tools" and s.screen == S.HOME
    s = S.apply(home(), key("CHAR", "2"))
    assert s.screen == S.SOURCE and s.preset == 2
    assert S.draft(s) == F.new_draft(2)
    s = S.apply(home(), key("ESC"))
    assert s.action == "exit" and s.exit_code == 0
```

Em `ui/tui/test_screens_config.py`, substituir `test_home_screen`:

```python
def test_home_screen():
    out = text_of(home())
    for txt in ("REELS ENCODER", "Encode rápido (FFmpeg)", "Film look (Cineon)", "Batch de pasta",
                "Tools", "Configurar avançado", "O QUE FAZ", "SYSTEM", "ffprobe.exe",
                "detectado no início do encode", "[1-5] Abrir"):
        assert txt in out, txt
    assert "chega no P3D" not in out and "[1 2 4 5]" not in out
    assert "▸" in out
    assert_fits(out)
    assert_no_emoji(out)
```

Em `ui/tui/test_parity_wizard.py`, a última linha de `tui_ns` passa a ser:

```python
    return EncodeConfig.model_validate(F.to_config(S.draft(s))).to_namespace()
```

Em `ui/tui/test_app.py`, acrescentar `from ui.tui import forms as F` entre `from ui.tui import app as A` e `from ui.tui import screens as V`, e no fim:

```python
def test_arm_strips_form_state_keys(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=5,
                          drafts=((5, {**F.new_draft(5), "input": str(src)}),))
    app._arm()
    assert app.state.screen == S.READY and app.state.field_error is None
    assert F.OUTDIR_ON not in app.state.config and F.SOURCE_KIND not in app.state.config
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_forms.py ui/tui/test_state_config.py ui/tui/test_screens_config.py ui/tui/test_parity_wizard.py ui/tui/test_app.py -v` → FAIL (`AttributeError: ... BATCH/FORM_ONLY/to_config`, HOME ainda pula o 3, rodapé `[1 2 4 5]`).

- [ ] **Step 3: Implement**

Em `ui/tui/forms.py`, depois de `MODE = ("crf", "2pass")`:

```python
SOURCE_KIND = "source_kind"
FILE = "file"
FOLDER = "folder"
OUTDIR_ON = "output_dir_on"
FORM_ONLY = frozenset({SOURCE_KIND, OUTDIR_ON})
OUTDIR_EMPTY = "Informe a pasta de saída."
```

Depois de `_ai_on`:

```python
def is_folder(d: dict) -> bool:
    return d.get(SOURCE_KIND) == FOLDER


def _outdir_on(d: dict) -> bool:
    return is_folder(d) and d.get(OUTDIR_ON) == "on"
```

Depois de `CINEON = (...)`:

```python
BATCH = (
    Field(OUTDIR_ON, "toggle", "Definir pasta de saída separada"),
    Field("output_dir", "path", "Pasta de saída", visible_if=_outdir_on),
    Field("cineon_pipeline", "toggle", "Usar film look (Cineon)"),
)
```

No início da tupla `ADVANCED["Source"]`, antes de `Field("cineon_pipeline", ...)`:

```python
        Field(OUTDIR_ON, "toggle", "Pasta de saída separada", visible_if=is_folder),
        Field("output_dir", "path", "Pasta de saída", visible_if=_outdir_on),
```

Trocar `ENABLED_PRESETS` e `PRESET_HELP[3]`:

```python
ENABLED_PRESETS = (1, 2, 3, 4, 5)
```

```python
    3: "Todos os vídeos de uma pasta (sem subpastas), um por vez. Pasta de saída e film look opcionais.",
```

Substituir `new_draft`, `form_for`, `apply_change`, `output_name` e acrescentar `to_config`/`outdir_missing`:

```python
def new_draft(preset: int) -> dict:
    if preset == 1:
        return EncodeConfig.preset_quick_ffmpeg().model_dump()
    if preset == 2:
        return EncodeConfig.preset_film_cineon().model_dump()
    if preset == 3:
        return {**EncodeConfig.preset_batch().model_dump(), SOURCE_KIND: FOLDER, OUTDIR_ON: "off"}
    if preset == 5:
        return {**EncodeConfig().model_dump(), SOURCE_KIND: FILE, OUTDIR_ON: "off"}
    return EncodeConfig().model_dump()


def form_for(preset: int) -> tuple:
    return {1: QUICK, 3: BATCH}.get(preset, CINEON)


def to_config(draft: dict) -> dict:
    out = {k: v for k, v in draft.items() if k not in FORM_ONLY}
    if not draft.get("batch") or draft.get(OUTDIR_ON) != "on":
        out["output_dir"] = None
    return out


def outdir_missing(draft: dict) -> bool:
    return _outdir_on(draft) and not str(draft.get("output_dir") or "").strip()
```

```python
def apply_change(draft: dict, name: str, value) -> tuple:
    new = derive({**draft, name: value})
    try:
        EncodeConfig.model_validate(to_config(new))
    except ValidationError as exc:
        return draft, exc.errors()[0]["msg"]
    return new, None


def output_name(draft: dict) -> str:
    if not draft.get("input"):
        return "—"
    out = EncodeConfig.model_validate(to_config(draft)).output_path()
    return os.path.basename(out) if out else "—"
```

Em `ui/tui/screens.py`, `FOOTER_KEYS[S.HOME]`:

```python
    S.HOME: "[↑↓] Navegar   [1-5] Abrir   [ENTER] Abrir   [ESC] Sair",
```

Em `ui/tui/app.py`, import `from ui.tui import forms as F` antes de `from ui.tui import state as S`, e em `_arm` a primeira linha do `try`:

```python
            cfg = EncodeConfig.model_validate(F.to_config(S.draft(self.state)))
```

- [ ] **Step 4: Run** — o comando do Step 2 → verdes; `venv\Scripts\python.exe -m pytest ui/tui/ -q`; `venv\Scripts\python.exe -m ruff check ui/tui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/forms.py ui/tui/screens.py ui/tui/app.py ui/tui/test_forms.py ui/tui/test_state_config.py ui/tui/test_screens_config.py ui/tui/test_parity_wizard.py ui/tui/test_app.py
git commit -m "feat(tui): formulário do batch e pasta de saída como estado de formulário (P3D)"
```

---

### Task 3: `state.py` (1/2) — SOURCE de pasta, TIPO, `EMPTY` e campo de caminho

**Files:**
- Modify: `ui/tui/state.py`
- Test: `ui/tui/test_state_config.py`

**Interfaces:**
- Consumes: `F.is_folder`, `F.SOURCE_KIND`, `F.FILE`, `F.FOLDER`, `F.OUTDIR_ON`, `F.OUTDIR_EMPTY`, `F.outdir_missing`, `F.to_config` (Task 2).
- Produces:
  - `SourceChecked(path: str, status: str, dims: tuple | None = None, count: int | None = None)`; status novo `"EMPTY"`.
  - `UIState.source_count: int | None = None` (vídeos achados no último `SourceChecked`).
  - SOURCE: o caminho vai para `draft["batch"]` quando `F.is_folder(draft)`, senão para `draft["input"]`. Preset 5: `tab_focus` (o mesmo campo do ADVANCED) marca o foco na linha TIPO; ↑ no caminho → TIPO; ↓ no TIPO → caminho; ←→/SPACE no TIPO alternam arquivo/pasta (troca `input`↔`batch`, o outro vira `None`, revalida); outras teclas no TIPO são ignoradas, salvo ENTER/ESC.
  - Campo `path`: teclas de edição começam a edição com o valor atual; ENTER/↑/↓ confirmam (`W.clean_path`); vazio → `F.OUTDIR_EMPTY`; ESC cancela a edição.
  - `_to_preview` bloqueia com `F.outdir_missing`: volta à aba 0 (ADVANCED), foca `output_dir`, `field_error=F.OUTDIR_EMPTY`.

- [ ] **Step 1: Write the failing tests** — acrescentar ao fim de `ui/tui/test_state_config.py`:

```python
def at_folder(preset=3, path="C:/v/lote", count=3):
    from dataclasses import replace
    s = S.apply(home(), key("CHAR", str(preset)))
    if preset == 5:
        s = S.apply(S.apply(S.apply(s, key("UP")), key("RIGHT")), key("DOWN"))
    s = replace(type_text(s, path), action=None)
    s = S.apply(s, S.SourceChecked(path, "VALID", None, count))
    return S.apply(s, key("ENTER"))


def test_preset3_opens_folder_source_and_routes_to_configuration():
    s = S.apply(home(), key("CHAR", "3"))
    assert s.screen == S.SOURCE and F.is_folder(S.draft(s)) and not s.tab_focus
    s = type_text(s, "C:/v/lote")
    assert s.action == "check_source" and s.source_status == "CHECKING" and s.source_count is None
    s = S.apply(s, S.SourceChecked("C:/v/lote", "VALID", None, 3))
    assert s.source_status == "VALID" and s.source_count == 3
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION
    assert S.draft(s)["batch"] == "C:/v/lote" and S.draft(s)["input"] is None


def test_empty_folder_blocks_enter():
    s = type_text(S.apply(home(), key("CHAR", "3")), "C:/v/vazia")
    s = S.apply(s, S.SourceChecked("C:/v/vazia", "EMPTY", None, 0))
    assert s.source_status == "EMPTY" and s.source_count == 0
    assert S.apply(s, key("ENTER")).screen == S.SOURCE


def test_preset5_tipo_switches_kind_and_keeps_other_edits():
    from dataclasses import replace
    s = S.apply(home(), key("CHAR", "5"))
    s = replace(s, drafts=((5, {**S.draft(s), "fps": "60"}),))
    s = replace(type_text(s, "C:/v/lote"), action=None)
    s = S.apply(s, key("UP"))
    assert s.tab_focus and s.screen == S.SOURCE
    assert S.apply(s, key("CHAR", "x")) == s
    s = S.apply(s, key("RIGHT"))
    d = S.draft(s)
    assert F.is_folder(d) and d["batch"] == "C:/v/lote" and d["input"] is None and d["fps"] == "60"
    assert s.source_status == "CHECKING" and s.action == "check_source"
    s = S.apply(replace(s, action=None), key("LEFT"))
    d = S.draft(s)
    assert not F.is_folder(d) and d["input"] == "C:/v/lote" and d["batch"] is None and d["fps"] == "60"
    s = S.apply(s, key("DOWN"))
    assert not s.tab_focus
    assert S.apply(s, key("CHAR", "x")).source.text == "C:/v/lotex"


def test_preset5_tipo_with_empty_path_is_invalid_without_check():
    s = S.apply(S.apply(S.apply(home(), key("CHAR", "5")), key("UP")), key("SPACE"))
    assert F.is_folder(S.draft(s)) and s.source_status == "INVALID" and s.action is None


def test_preset5_folder_advanced_source_tab_starts_with_outdir_toggle():
    s = at_folder(5)
    assert s.screen == S.ADVANCED and not s.tab_focus and s.adv_back == S.SOURCE
    assert [f.name for f in S.form_items(s)][:2] == [F.OUTDIR_ON, "cineon_pipeline"]
    assert S.draft(s)["batch"] == "C:/v/lote" and S.draft(s)["input"] is None


def test_source_esc_remembers_folder():
    s = type_text(S.apply(home(), key("CHAR", "3")), "C:/v/lote")
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME and S.draft(s)["batch"] == "C:/v/lote"
    s = S.apply(s, key("CHAR", "3"))
    assert s.source.text == "C:/v/lote" and s.action == "check_source"


def test_batch_form_outdir_toggle_shows_path_field():
    s = at_folder(3)
    assert [f.name for f in S.form_items(s)] == [F.OUTDIR_ON, "cineon_pipeline", "__continue__"]
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)[F.OUTDIR_ON] == "on"
    assert [f.name for f in S.form_items(s)] == [F.OUTDIR_ON, "output_dir", "cineon_pipeline", "__continue__"]


def test_outdir_empty_blocks_with_inline_error_cleared_on_focus_change():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    assert focused(s).name == "output_dir"
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and s.field_error == F.OUTDIR_EMPTY and focused(s).name == "output_dir"
    s = S.apply(s, key("DOWN"))
    assert s.field_error is None and focused(s).name == "cineon_pipeline"
    s = S.apply(S.apply(s, key("DOWN")), key("ENTER"))
    assert s.screen == S.CONFIGURATION and s.field_error == F.OUTDIR_EMPTY and focused(s).name == "output_dir"
    assert S.apply(s, key("UP")).field_error is None


def test_outdir_typing_hotkey_letters_and_commit():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    s = type_text(s, "D:/clips/lote")
    assert s.edit.text == "D:/clips/lote" and s.modal is None and s.screen == S.CONFIGURATION
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["output_dir"] == "D:/clips/lote" and s.edit is None and focused(s).name == "cineon_pipeline"
    assert F.to_config(S.draft(s))["output_dir"] == "D:/clips/lote"
    s = S.apply(S.apply(S.apply(s, key("UP")), key("UP")), key("SPACE"))
    assert S.draft(s)[F.OUTDIR_ON] == "off"
    assert F.to_config(S.draft(s))["output_dir"] is None and S.draft(s)["output_dir"] == "D:/clips/lote"


def test_outdir_edit_esc_cancels_and_quoted_empty_commit_errors():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    s = S.apply(type_text(s, "X:/a"), key("ESC"))
    assert s.edit is None and S.draft(s)["output_dir"] is None and s.screen == S.CONFIGURATION
    s = S.apply(type_text(s, '""'), key("ENTER"))
    assert s.field_error == F.OUTDIR_EMPTY and S.draft(s)["output_dir"] is None and s.edit is None


def test_advanced_folder_enter_walks_tabs_with_outdir_then_preview():
    s = S.apply(at_folder(5), key("SPACE"))
    s = S.apply(type_text(S.apply(s, key("DOWN")), "D:/saida"), key("ENTER"))
    assert focused(s).name == "cineon_pipeline" and s.tab == 0
    tabs = []
    for _ in range(60):
        if s.screen != S.ADVANCED:
            break
        tabs.append(s.tab)
        s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and S.draft(s)["output_dir"] == "D:/saida"
    assert tabs == sorted(tabs) and set(tabs) == {0, 1, 2, 3, 4}


def test_advanced_continue_with_empty_outdir_jumps_back_to_source_tab():
    from dataclasses import replace
    s = replace(S.apply(at_folder(5), key("SPACE")), tab=4)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.ADVANCED and s.tab == 0 and not s.tab_focus
    assert focused(s).name == "output_dir" and s.field_error == F.OUTDIR_EMPTY


def test_esc_chain_preset3_after_revisar_never_loops():
    s = at_folder(3)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.CONFIGURATION
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED and s.adv_back == S.PREVIEW
    assert S.form_items(s)[0].name == F.OUTDIR_ON
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW
    for want in (S.CONFIGURATION, S.SOURCE, S.HOME):
        s = S.apply(s, key("ESC"))
        assert s.screen == want
    assert S.draft(s)["batch"] == "C:/v/lote"


def test_esc_chain_preset5_folder_after_revisar_never_loops():
    s = at_folder(5)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.ADVANCED
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED and s.adv_back == S.PREVIEW
    for want in (S.PREVIEW, S.ADVANCED, S.SOURCE, S.HOME):
        s = S.apply(s, key("ESC"))
        assert s.screen == want
    assert F.is_folder(S.draft(s))
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_state_config.py -v` → novos falham (`TypeError: SourceChecked() takes ... 4 positional`, `draft["batch"]` não gravado, etc.).

- [ ] **Step 3: Implement** — em `ui/tui/state.py`:

`SourceChecked` ganha `count`:

```python
@dataclass(frozen=True)
class SourceChecked:
    path: str
    status: str
    dims: tuple | None = None
    count: int | None = None
```

`UIState` ganha, depois de `system: tuple = ()`:

```python
    source_count: int | None = None
```

Em `apply`, o ramo `SourceChecked` termina em:

```python
        return replace(s, source_status=ev.status, source_dims=ev.dims, source_count=ev.count)
```

Substituir `_commit` e `_to_preview`:

```python
def _commit(s: UIState, field) -> UIState:
    if field.kind == "path":
        value = W.clean_path(s.edit.text)
        s = _set_value(s, field.name, value or None)
        return s if value else replace(s, field_error=F.OUTDIR_EMPTY)
    value, err = W.parse_number(s.edit.text, field.lo, field.hi, field.integer)
    if err:
        return replace(s, field_error=err, edit=None)
    return _set_value(s, field.name, value)


def _to_preview(s: UIState) -> UIState:
    if F.outdir_missing(draft(s)):
        if s.screen == ADVANCED:
            s = replace(s, tab=0, tab_focus=False)
        names = [f.name for f in form_items(s)]
        s = _set_focus(s, focus_key(s), names.index("output_dir"))
        return replace(s, field_error=F.OUTDIR_EMPTY, edit=None)
    origin = s.came_from if s.screen == ADVANCED and s.adv_back == PREVIEW else s.screen
    return replace(s, screen=PREVIEW, came_from=origin, action_focus=0, field_error=None)
```

Em `_form_key`, entre o bloco `if item is F.CONTINUE:` e a linha `if k == "ENTER": return _enter_next(s, key, items, i)`, inserir:

```python
    if item.kind == "path":
        if k in _EDIT_KEYS:
            cur = draft(s).get(item.name) or ""
            return replace(s, edit=W.edit_text(W.TextBuf(cur, len(cur)), k, ch), field_error=None)
        if k == "ENTER" and not str(draft(s).get(item.name) or "").strip():
            return replace(s, field_error=F.OUTDIR_EMPTY)
```

Em `_home_key`, substituir as três linhas a partir de `text = d.get("input") or ""`:

```python
    text = d.get("batch" if F.is_folder(d) else "input") or ""
    s = replace(s, screen=SOURCE, source=W.TextBuf(text, len(text)), source_status="INVALID", source_dims=None,
                source_count=None, tab_focus=False)
    return replace(s, source_status="CHECKING", action="check_source") if text else s
```

Substituir `_source_key` e acrescentar `_toggle_kind` antes dele:

```python
def _toggle_kind(s: UIState) -> UIState:
    d = draft(s)
    folder = not F.is_folder(d)
    path = W.clean_path(s.source.text) or None
    d = {**d, F.SOURCE_KIND: F.FOLDER if folder else F.FILE,
         "batch": path if folder else None, "input": None if folder else path}
    s = replace(_with_draft(s, d), source_dims=None, source_count=None, field_error=None)
    if path is None:
        return replace(s, source_status="INVALID")
    return replace(s, source_status="CHECKING", action="check_source")


def _source_key(s: UIState, k: str, ch: str | None) -> UIState:
    if s.preset == 5:
        if s.tab_focus:
            if k in ("LEFT", "RIGHT", "SPACE"):
                return _toggle_kind(s)
            if k == "DOWN":
                return replace(s, tab_focus=False)
            if k not in ("ENTER", "ESC"):
                return s
        elif k == "UP":
            return replace(s, tab_focus=True)
    field = "batch" if F.is_folder(draft(s)) else "input"
    if k == "ESC":
        s = _with_draft(s, {**draft(s), field: W.clean_path(s.source.text) or None})
        return replace(s, screen=HOME, tab_focus=False)
    if k == "ENTER":
        if s.source_status != "VALID":
            return s
        s = _with_draft(s, {**draft(s), field: W.clean_path(s.source.text)})
        if s.preset == 5:
            return replace(s, screen=ADVANCED, adv_back=SOURCE, tab_focus=False, edit=None, field_error=None)
        return replace(s, screen=CONFIGURATION, edit=None, field_error=None)
    buf = W.edit_text(s.source, k, ch)
    if buf == s.source:
        return s
    if buf.text == s.source.text:
        return replace(s, source=buf)
    return replace(s, source=buf, source_status="CHECKING", source_dims=None, source_count=None,
                   action="check_source")
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -q` (P3B/P3C inteiros verdes, inclusive `test_parity_wizard.py`); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/state.py ui/tui/test_state_config.py
git commit -m "feat(tui): SOURCE de pasta, seletor TIPO e campo da pasta de saída (P3D)"
```

---

### Task 4: `state.py` (2/2) — fila, QUEUE, REPORT e `Finished` em batch

**Files:**
- Modify: `ui/tui/state.py`
- Test: `ui/tui/test_state_batch.py` (novo)

**Interfaces:**
- Consumes: eventos `R.QueueInit(jobs)`, `R.JobStart(index)`, `R.JobSkip(index, reason)`, `R.JobDone(index, status, error)`, `R.QueueDone(exit_code)` (`reporter.py` 136–171; `run_batch` emite todos com `ts=0.0`).
- Produces:
  - Telas `QUEUE = "QUEUE"`, `REPORT = "REPORT"`; `FINAL_SCREENS = frozenset({COMPLETED, ERROR, CANCELLED, REPORT})`; `REPORT_ROWS = 21`.
  - `Job(input: str, output: str, status: str = "aguardando", started: float | None = None, finished: float | None = None, reason: str | None = None)` (frozen). Status: `aguardando`, `processando`, `ok`, `pulado`, `falha`, `interrompido` (mesmos de `render_queue`).
  - Campos de `UIState`: `queue: tuple = ()`, `active_job: int | None = None`, `queue_started: float | None = None`, `queue_finished: float | None = None`, `is_batch: bool = False`, `queue_scroll: int = 0`.
  - `queue_counts(queue: tuple) -> dict` (chaves: os 6 status + `"total"`); `queue_eta(s: UIState) -> float | None` (média das durações `ok`/`falha` × `aguardando` + o que falta do job ativo — mesma regra de `render_queue.estimate_eta`).
  - Regras: `Armed` grava `is_batch = bool(config["batch"])`; READY ENTER → QUEUE se `is_batch` (senão ENCODING); `QueueInit` monta a fila; `JobStart` zera o painel do job ativo e põe `output_path` = saída do job; `JobSkip` → `pulado`/"saída já existe"; `JobDone` → status (vira `interrompido` se houve cancelamento e não é `ok`), motivo = "ok" / "interrompido" / 1ª linha do erro; `QueueDone` → `exit_code`, `queue_finished`, job ativo `processando` vira `interrompido` se 130, tela REPORT; `R.Error` com fila montada só vai ao log; `Finished` em batch com fila (ou código 0/130) → REPORT; sem fila e código 1/2 → ERROR (P3B). Estágio QC em batch não muda de tela. QUEUE aceita D, L e C (mesma trava do ENCODING). REPORT: ↑↓ rolam (`queue_scroll` limitado a `len(queue) - REPORT_ROWS`), ENTER/ESC → `action="exit"`.
  - Tempo de cada evento de fila: `ev.ts` se não zero, senão `s.now` (relógio do tick).

- [ ] **Step 1: Write the failing test** — `ui/tui/test_state_batch.py`

```python
import reporter as R
from ui.tui import state as S

JOBS = tuple((f"C:/v/lote/{n}.mov", f"C:/v/lote/{n}_Hollywood_CRF18.mp4") for n in ("a", "b", "c"))
CFG = {"batch": "C:/v/lote", "input": None, "output_dir": None, "mode": "crf", "cineon_pipeline": "off"}


def run(s, *evs):
    for ev in evs:
        s = S.apply(s, ev)
    return s


def tick(s, t):
    return S.apply(s, S.Tick(t, (120, 40)))


def armed():
    s = S.UIState(config={}, screen=S.PREVIEW, preset=3)
    return S.apply(s, S.Armed(dict(CFG), "", False))


def in_queue(now=10.0):
    s = S.apply(tick(armed(), now), S.Key("ENTER"))
    return S.apply(s, R.QueueInit(JOBS))


def test_armed_batch_and_ready_enter_opens_queue():
    s = armed()
    assert s.screen == S.READY and s.is_batch and s.output_path == ""
    s = S.apply(s, S.Key("ENTER"))
    assert s.screen == S.QUEUE and s.action == "start"
    assert S.apply(armed(), S.Key("ESC")).screen == S.PREVIEW
    single = S.apply(S.UIState(config={}, screen=S.PREVIEW, preset=1), S.Armed({"input": "a.mov"}, "o.mp4", False))
    assert not single.is_batch and S.apply(single, S.Key("ENTER")).screen == S.ENCODING


def test_queue_init_builds_waiting_table():
    s = in_queue(now=10.0)
    assert s.screen == S.QUEUE and len(s.queue) == 3 and s.is_batch
    assert all(j.status == "aguardando" and j.reason is None for j in s.queue)
    assert (s.queue[0].input, s.queue[0].output) == JOBS[0]
    assert s.queue_started == 10.0 and s.active_job is None


def test_events_without_timestamp_use_tick_clock():
    s = S.apply(in_queue(now=50.0), R.JobStart(0))
    s = S.apply(tick(s, 80.0), R.JobDone(0, "ok", None))
    job = s.queue[0]
    assert (job.started, job.finished, job.status, job.reason) == (50.0, 80.0, "ok", "ok")
    s = S.apply(tick(s, 95.0), R.QueueDone(0))
    assert s.queue_finished == 95.0 and s.queue_finished - s.queue_started == 45.0


def test_job_start_resets_active_job_panel():
    s = run(in_queue(), R.JobStart(0, job_id=0, ts=10.0), R.Stage(R.PASS, "1", job_id=0, ts=11.0),
            R.Pass(1, 1, "Encode", "start", job_id=0, ts=11.0),
            R.Progress(10, 100, 30.0, 1.0, "00:00:03", 1.0, job_id=0, ts=12.0),
            R.Info("Aviso: ffprobe falhou", job_id=0, ts=12.0), R.Qc({"checks": []}, job_id=0, ts=13.0),
            R.JobDone(0, "ok", None, job_id=0, ts=20.0), R.JobStart(1, job_id=1, ts=20.0))
    assert s.active_job == 1 and s.queue[1].status == "processando" and s.queue[0].status == "ok"
    assert s.stage is None and s.passes == () and s.progress is None and s.log == ()
    assert s.qc is None and s.error is None and s.warnings == 0 and s.job_started is None
    assert s.output_path == JOBS[1][1] and s.screen == S.QUEUE


def test_skip_and_failure_reasons_do_not_go_to_error():
    s = run(in_queue(), R.JobSkip(0, "output existe", job_id=0),
            R.JobStart(1, job_id=1, ts=10.0),
            R.Error("CalledProcessError", "ffmpeg saiu com 1\nstderr...", "tail", 1, "tb", job_id=1, ts=15.0),
            R.JobDone(1, "falha", "ffmpeg saiu com 1\nstderr...", job_id=1, ts=15.0))
    assert (s.queue[0].status, s.queue[0].reason) == ("pulado", "saída já existe")
    assert (s.queue[1].status, s.queue[1].reason) == ("falha", "ffmpeg saiu com 1")
    assert s.screen == S.QUEUE and s.error is None
    assert any("ffmpeg saiu com 1" in r.text for r in s.log)


def test_error_before_queue_goes_to_error_screen():
    s = run(S.apply(armed(), S.Key("ENTER")),
            R.Error("validation", "--output-dir só se aplica a --batch", None, None, None), S.Finished(2))
    assert s.screen == S.ERROR and s.error.kind == "validation" and s.exit_code == 2
    s = run(S.apply(armed(), S.Key("ENTER")),
            R.Error("batch_folder", "Pasta não encontrada: C:/v/lote", None, None, None), S.Finished(1))
    assert s.screen == S.ERROR and s.exit_code == 1


def test_queue_done_goes_to_report_and_finished_is_idempotent():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.JobDone(0, "ok", None, ts=70.0), R.JobSkip(1, "output existe"),
            R.JobStart(2, ts=70.0), R.JobDone(2, "falha", "boom", ts=80.0), R.QueueDone(1, ts=80.0))
    assert s.screen == S.REPORT and s.exit_code == 1 and s.queue_finished == 80.0
    assert S.apply(s, S.Finished(1)) == s
    c = S.queue_counts(s.queue)
    assert (c["ok"], c["pulado"], c["falha"], c["interrompido"], c["total"]) == (1, 1, 1, 0, 3)


def test_empty_queue_done_zero_goes_to_report():
    s = run(S.apply(armed(), S.Key("ENTER")), R.Info("Nenhum vídeo encontrado em: C:/v/lote"), R.QueueDone(0),
            S.Finished(0))
    assert s.screen == S.REPORT and s.queue == () and s.exit_code == 0


def test_cancel_marks_active_job_interrupted_and_keeps_waiting_jobs():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Cancel("requested", ts=12.0),
            R.JobDone(0, "falha", "cancelado pelo usuário", ts=13.0), R.Cancel("terminated", ts=13.0),
            R.Cancel("cleaned", True, ts=14.0), R.QueueDone(130, ts=14.0))
    assert s.screen == S.REPORT and s.exit_code == 130 and s.modal is None
    assert (s.queue[0].status, s.queue[0].reason) == ("interrompido", "interrompido")
    assert [j.status for j in s.queue[1:]] == ["aguardando", "aguardando"]


def test_ctrl_c_without_job_done_marks_active_interrupted():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Cancel("requested", ts=12.0), R.QueueDone(130, ts=14.0))
    assert s.queue[0].status == "interrompido" and s.queue[0].finished == 14.0
    s = run(in_queue(), R.JobStart(0, ts=10.0), S.Finished(130))
    assert s.screen == S.REPORT and s.queue[0].status == "interrompido" and s.exit_code == 130


def test_queue_keys_overlays_and_cancel_modal():
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.Stage(R.PASS, "1", ts=11.0))
    d = S.apply(s, S.Key("D"))
    assert d.screen == S.DETAILS and d.back == S.QUEUE
    assert S.apply(d, S.Key("ESC")).screen == S.QUEUE
    assert S.apply(s, S.Key("L")).screen == S.LOG
    m = S.apply(s, S.Key("C"))
    assert m.modal == "CANCEL"
    m = S.apply(S.apply(m, S.Key("RIGHT")), S.Key("ENTER"))
    assert m.action == "cancel" and m.modal is None
    blocked = S.apply(s, R.Stage(R.ANALYZING, "mctf_mask", ts=12.0))
    assert S.apply(blocked, S.Key("C")).modal is None


def test_qc_stage_in_batch_never_opens_qc_screen():
    s = run(in_queue(), R.JobStart(0, ts=10.0))
    assert S.apply(s, R.Stage(R.QC, ts=11.0)).screen == S.QUEUE
    d = run(S.apply(s, S.Key("D")), R.Stage(R.QC, ts=11.0))
    assert d.screen == S.DETAILS and d.back == S.QUEUE
    d = run(d, R.JobDone(0, "ok", None, ts=20.0), R.QueueDone(0, ts=30.0))
    assert d.screen == S.REPORT


def test_report_keys_scroll_and_exit():
    jobs = tuple((f"C:/v/{i}.mov", f"C:/v/{i}_o.mp4") for i in range(30))
    s = run(S.apply(armed(), S.Key("ENTER")), R.QueueInit(jobs), R.QueueDone(0))
    assert S.apply(s, S.Key("UP")).queue_scroll == 0
    for _ in range(20):
        s = S.apply(s, S.Key("DOWN"))
    assert s.queue_scroll == 30 - S.REPORT_ROWS
    assert S.apply(s, S.Key("ENTER")).action == "exit"
    assert S.apply(s, S.Key("ESC")).action == "exit"


def test_queue_eta_mean_times_remaining_plus_in_flight():
    assert S.queue_eta(run(in_queue(), R.JobStart(0, ts=10.0))) is None
    s = run(in_queue(), R.JobStart(0, ts=10.0), R.JobDone(0, "ok", None, ts=70.0), R.JobStart(1, ts=70.0))
    assert S.queue_eta(tick(s, 90.0)) == 100.0
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_state_batch.py -v` → FAIL (`AttributeError: QUEUE`, `is_batch`).

- [ ] **Step 3: Implement** — em `ui/tui/state.py`:

Constantes (substituir `FINAL_SCREENS` e acrescentar as demais logo após `PREVIEW = "PREVIEW"`):

```python
QUEUE = "QUEUE"
REPORT = "REPORT"
```

```python
FINAL_SCREENS = frozenset({COMPLETED, ERROR, CANCELLED, REPORT})
```

```python
REPORT_ROWS = 21
```

Depois de `LogRow`:

```python
@dataclass(frozen=True)
class Job:
    input: str
    output: str
    status: str = "aguardando"
    started: float | None = None
    finished: float | None = None
    reason: str | None = None
```

`UIState` ganha, depois de `source_count`:

```python
    queue: tuple = ()
    active_job: int | None = None
    queue_started: float | None = None
    queue_finished: float | None = None
    is_batch: bool = False
    queue_scroll: int = 0
```

Depois de `filtered_log`:

```python
def queue_counts(queue: tuple) -> dict:
    out = dict.fromkeys(("aguardando", "processando", "ok", "pulado", "falha", "interrompido"), 0)
    for job in queue:
        out[job.status] = out.get(job.status, 0) + 1
    out["total"] = len(queue)
    return out


def queue_eta(s: UIState) -> float | None:
    durations = [j.finished - j.started for j in s.queue
                 if j.status in ("ok", "falha") and j.started is not None and j.finished is not None]
    if not durations:
        return None
    mean = sum(durations) / len(durations)
    eta = mean * sum(1 for j in s.queue if j.status == "aguardando")
    active = s.queue[s.active_job] if s.active_job is not None and s.active_job < len(s.queue) else None
    if active is not None and active.status == "processando" and active.started is not None:
        eta += max(0.0, mean - (s.now - active.started))
    return eta
```

No ramo `Armed` de `apply` (sem erro), acrescentar `is_batch=bool(ev.config.get("batch")),` ao `replace`.

Antes de `_engine`:

```python
_QUEUE_EVENTS = (R.QueueInit, R.JobStart, R.JobSkip, R.JobDone, R.QueueDone)
_JOB_RESET = {
    "stage": None, "substep": None, "stages_done": (), "passes": (), "progress": None, "job_started": None,
    "probe": None, "encode_params": None, "log": (), "warnings": 0, "qc": None, "done": None, "error": None,
    "seal_reveal_start": None,
}


def _at(s: UIState, ev) -> float:
    return ev.ts if ev.ts else s.now


def _first_line(text) -> str:
    return next((ln.strip() for ln in str(text or "").splitlines() if ln.strip()), "")


def _with_job(s: UIState, index: int, **changes) -> UIState:
    if not 0 <= index < len(s.queue):
        return s
    jobs = list(s.queue)
    jobs[index] = replace(jobs[index], **changes)
    return replace(s, queue=tuple(jobs))


def _interrupt_active(s: UIState, at: float) -> UIState:
    i = s.active_job
    if i is None or not 0 <= i < len(s.queue) or s.queue[i].status != "processando":
        return s
    return _with_job(s, i, status="interrompido", finished=at, reason="interrompido")


def _to_report(s: UIState) -> UIState:
    return replace(s, screen=REPORT, modal=None, modal_focus=0, action_focus=0, queue_scroll=0)


def _queue_event(s: UIState, ev) -> UIState:
    at = _at(s, ev)
    if isinstance(ev, R.QueueInit):
        jobs = tuple(Job(str(i), str(o)) for i, o in ev.jobs)
        screen = QUEUE if s.screen in (READY, ENCODING) else s.screen
        return replace(s, queue=jobs, is_batch=True, active_job=None, queue_started=at, screen=screen)
    if isinstance(ev, R.JobStart):
        if not 0 <= ev.index < len(s.queue):
            return s
        s = replace(s, active_job=ev.index, output_path=s.queue[ev.index].output, **_JOB_RESET)
        return _with_job(s, ev.index, status="processando", started=at, finished=None, reason=None)
    if isinstance(ev, R.JobSkip):
        return _with_job(s, ev.index, status="pulado", reason="saída já existe")
    if isinstance(ev, R.JobDone):
        status = "interrompido" if s.cancel_phase is not None and ev.status != "ok" else ev.status
        if status in ("ok", "interrompido"):
            reason = status
        else:
            reason = _first_line(ev.error) or status
        return _with_job(s, ev.index, status=status, finished=at, reason=reason)
    s = replace(s, exit_code=ev.exit_code, queue_finished=at)
    if ev.exit_code == 130:
        s = _interrupt_active(s, at)
    return _to_report(s)
```

Em `_engine`, primeira linha do corpo:

```python
    if isinstance(ev, _QUEUE_EVENTS):
        return _queue_event(s, ev)
```

No ramo `R.Stage`, trocar `if ev.name == R.QC:` por:

```python
        if ev.name == R.QC and not s.is_batch:
```

Trocar o ramo `R.Error`:

```python
    if isinstance(ev, R.Error):
        if s.is_batch and s.queue:
            return _log(s, "WARNING", f"{ev.kind}: {ev.message}")
        return _log(replace(s, error=ev), "WARNING", f"{ev.kind}: {ev.message}")
```

Início de `_finished`:

```python
def _finished(s: UIState, code: int) -> UIState:
    if s.is_batch and (s.queue or code in (0, 130)):
        s = replace(s, exit_code=code)
        if s.screen == REPORT:
            return s
        if code == 130:
            s = _interrupt_active(s, s.now)
        finished = s.queue_finished if s.queue_finished is not None else s.now
        return _to_report(replace(s, queue_finished=finished))
    s = replace(s, exit_code=code, modal=None, action_focus=0)
```

(o resto de `_finished` não muda.)

Em `_key`, o ENTER do READY:

```python
        if k == "ENTER":
            return replace(s, screen=QUEUE if s.is_batch else ENCODING, action="start", ready_error=None)
```

Logo antes de `if s.screen in FINAL_SCREENS:`:

```python
    if s.screen == REPORT:
        if k in ("UP", "DOWN"):
            top = max(0, len(s.queue) - REPORT_ROWS)
            return replace(s, queue_scroll=max(0, min(top, s.queue_scroll + (1 if k == "DOWN" else -1))))
        if k in ("ENTER", "ESC"):
            return replace(s, action="exit")
        return s
```

E o bloco final de `_key`:

```python
    if s.screen in (ENCODING, QC, QUEUE):
        if k == "D":
            return replace(s, screen=DETAILS, back=s.screen)
        if k == "L":
            return replace(s, screen=LOG, back=s.screen)
        if k == "C" and s.screen in (ENCODING, QUEUE) and s.cancel_phase is None and not cancel_blocked(s):
            return replace(s, modal="CANCEL", modal_focus=0)
    return s
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -q` (P3B/P3C verdes; `test_app.py` usa `S.FINAL_SCREENS` nos ganchos de `sleep`, e o REPORT entrar nele é intencional); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/state.py ui/tui/test_state_batch.py
git commit -m "feat(tui): fila de jobs, telas QUEUE e REPORT no reducer (P3D)"
```

---

### Task 5: `screens.py` (1/2) — SOURCE pasta, CONFIGURATION BATCH, PREVIEW e READY de pasta

**Files:**
- Modify: `ui/tui/screens.py`
- Test: `ui/tui/test_screens_config.py`

**Interfaces:**
- Consumes: `F.is_folder`, `F.to_config`, `F.OUTDIR_ON`, `F.OUTDIR_EMPTY`, `S.UIState.source_count`, `S.UIState.is_batch` (Tasks 2–4).
- Produces (em `ui.tui.screens`, usados pela Task 6): `elide(text, width: int) -> str` (mantém o fim, prefixo "…"; `None`/vazio → "—"); `folder_name(path) -> str`; `videos(n: int | None) -> str` ("1 vídeo", "3 vídeos", "— vídeos"); `output_dir_text(cfg: dict) -> str` ("mesma pasta" ou caminho elidido a 50); `source_text(cfg: dict, count) -> str` ("pasta <nome> · N vídeos" com `batch`, senão basename do `input`).
- Regras de tela: SOURCE de pasta com rótulo PASTA, STATUS (`VALID` "✓ pasta encontrada · N vídeos", `EMPTY` "⚠ nenhum vídeo encontrado", `NOT_FOUND` "✗ pasta não encontrada", `INVALID` "⚠ informe uma pasta de vídeos", `CHECKING`), VÍDEOS, SAÍDA, e PROGRAM padrão com "pasta · N vídeos" (sem dimensões). Preset 5: linha TIPO "● Arquivo único   ○ Pasta (batch)" (foco `▎▸`), rodapé com `[↑] Tipo` / `[←→] Tipo`. CONFIGURATION BATCH: resumo com PASTA · vídeos · saída; rodapé sem `[0-9]`. Campo `path`: valor elidido ou "—"; buffer em edição. PREVIEW de pasta: título "PREVIEW · pasta <nome> · N vídeos ▸ saída: …" (escapado). READY de pasta: SOURCE/OUTPUT com pasta e saída, certificado "por vídeo", monitor EBU "suprimido em batch (motor)", botão "START QUEUE".

- [ ] **Step 1: Write the failing tests** — em `ui/tui/test_screens_config.py`: o bloco de imports do topo passa a ser exatamente

```python
from ui.config import EncodeConfig
from ui.tui import forms as F
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of
```

(`replace` continua importado localmente dentro das funções, como o arquivo já faz — um import de módulo somado ao import local em `test_program_frame_cover_portrait_keeps_bars_aligned` arrisca F811 no ruff); **remover** `test_source_preset5_shows_disabled_batch`; acrescentar no fim:

```python
def folder_state(status="VALID", count=3, preset=3, path="C:/v/lote", **kw):
    d = {**F.new_draft(preset), F.SOURCE_KIND: F.FOLDER}
    return S.UIState(config={}, screen=S.SOURCE, preset=preset, drafts=((preset, d),),
                     source=W.TextBuf(path, len(path)), source_status=status,
                     source_count=count if status in ("VALID", "EMPTY") else None, **kw)


def test_source_folder_states():
    cases = (("VALID", 3, "✓ pasta encontrada · 3 vídeos"), ("VALID", 1, "✓ pasta encontrada · 1 vídeo"),
             ("EMPTY", 0, "⚠ nenhum vídeo encontrado"), ("NOT_FOUND", None, "✗ pasta não encontrada"),
             ("INVALID", None, "informe uma pasta"), ("CHECKING", None, "verificando"))
    for status, count, txt in cases:
        out = text_of(folder_state(status, count))
        assert txt in out, status
        assert "PASTA" in out and "PROGRAM" in out and "ENTER → CONFIGURATION" in out
        assert "DIMENSÕES" not in out and "ARQUIVO" not in out
        assert_fits(out)
        assert_no_emoji(out)
    out = text_of(folder_state())
    assert "pasta · 3 vídeos" in out and "mesma pasta" in out


def test_source_preset5_tipo_row_and_footer():
    from dataclasses import replace
    s = S.UIState(config={}, screen=S.SOURCE, preset=5, drafts=((5, F.new_draft(5)),))
    out = text_of(s)
    assert "● Arquivo único" in out and "○ Pasta (batch)" in out and "ENTER → ADVANCED" in out
    assert "chega no P3D" not in out and "▎▸ ●" not in out
    assert "[↑] Tipo" in "\n".join(out.splitlines()[-2:])
    out = text_of(replace(s, tab_focus=True))
    assert "▎▸ ● Arquivo único" in out
    foot = "\n".join(out.splitlines()[-2:])
    assert "[←→] Tipo" in foot and "[↓] Caminho" in foot
    out = text_of(folder_state(preset=5))
    assert "○ Arquivo único" in out and "● Pasta (batch)" in out and "PASTA" in out
    assert_fits(out)
    assert_no_emoji(out)


def batch_cfg_state(**kw):
    d = {**F.new_draft(3), "batch": "C:/v/lote", **kw.pop("draft", {})}
    return S.UIState(config={}, screen=kw.pop("screen", S.CONFIGURATION), preset=3, drafts=((3, d),),
                     source_count=3, **kw)


def test_configuration_batch_form():
    out = text_of(batch_cfg_state())
    for txt in ("Definir pasta de saída separada", "Usar film look (Cineon)", "CONTINUAR", "PADRÕES",
                "C:/v/lote", "3 vídeos", "mesma pasta"):
        assert txt in out, txt
    assert "Pasta de saída" not in out
    foot = "\n".join(out.splitlines()[-2:])
    assert "[digite] Pasta" in foot and "[0-9]" not in foot
    assert_fits(out)
    assert_no_emoji(out)
    on = batch_cfg_state(draft={F.OUTDIR_ON: "on", "output_dir": "D:/saida"})
    out = text_of(on)
    assert "Pasta de saída" in out and "D:/saida" in out
    editing = batch_cfg_state(draft={F.OUTDIR_ON: "on"}, focus=((S.CONFIGURATION, 1),), edit=W.TextBuf("D:/sa", 5))
    assert "D:/sa" in text_of(editing)
    err = batch_cfg_state(draft={F.OUTDIR_ON: "on"}, focus=((S.CONFIGURATION, 1),), field_error=F.OUTDIR_EMPTY)
    assert "Informe a pasta de saída." in text_of(err)


def test_preview_folder_text():
    out = text_of(batch_cfg_state(screen=S.PREVIEW))
    for txt in ("PREVIEW", "pasta lote · 3 vídeos", "saída: mesma pasta", "PROGRAM", "EXPORT SETTINGS"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_preview_folder_with_brackets():
    s = batch_cfg_state(screen=S.PREVIEW, draft={"batch": "C:/v/[2026] lote"})
    out = text_of(s)
    assert "[2026] lote" in out and "erro ao desenhar" not in out
    assert_fits(out)


def test_ready_folder_text():
    cfg = {**vars(EncodeConfig.preset_batch("C:/v/lote").to_namespace()), "output_dir": "D:/saida"}
    out = text_of(S.UIState(config=cfg, screen=S.READY, preset=3, is_batch=True, source_count=12))
    for txt in ("READY TO ENCODE", "pasta lote · 12 vídeos", "saída: D:/saida", "START QUEUE", "por vídeo",
                "suprimido em batch"):
        assert txt in out, txt
    assert "START ENCODE" not in out
    assert_fits(out)
    assert_no_emoji(out)
```

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_screens_config.py -v` → novos falham.

- [ ] **Step 3: Implement** — em `ui/tui/screens.py`:

Import (ordem do isort, junto dos outros `rich`): `from rich.markup import escape` entre `from rich.layout import Layout` e `from rich.panel import Panel`.

Constantes, depois de `MODAL_KEYS`:

```python
SOURCE_TIPO_KEYS = "[←→] Tipo   [↓] Caminho   [ENTER] Continuar   [ESC] Voltar   [Ctrl+C] Sair"
CONFIG_BATCH_KEYS = "[↑↓] Campo   [←→] On/Off   [digite] Pasta   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair"
```

Helpers, depois de `fmt_secs`:

```python
def elide(text, width: int) -> str:
    text = str(text) if text else "—"
    return text if len(text) <= width else "…" + text[-(width - 1):]


def folder_name(path) -> str:
    raw = str(path or "")
    return os.path.basename(raw.rstrip("/\\")) or raw or "—"


def videos(n: int | None) -> str:
    if n is None:
        return "— vídeos"
    return f"{n} vídeo{'' if n == 1 else 's'}"


def output_dir_text(cfg: dict) -> str:
    out = cfg.get("output_dir")
    return elide(out, 50) if out else "mesma pasta"


def source_text(cfg: dict, count: int | None) -> str:
    if cfg.get("batch"):
        return f"pasta {elide(folder_name(cfg['batch']), 40)} · {videos(count)}"
    return basename(cfg.get("input"))
```

Em `footer`, logo antes de `elif s.screen == S.READY and s.preset:`:

```python
    elif s.screen == S.SOURCE and s.preset == 5:
        keys = SOURCE_TIPO_KEYS if s.tab_focus else "[↑] Tipo   " + keys
    elif s.screen == S.CONFIGURATION and s.preset == 3:
        keys = CONFIG_BATCH_KEYS
```

Substituir `_ready` inteira:

```python
def _ready(s: S.UIState) -> RenderableType:
    cfg = s.config
    g = glyphs()
    batch = bool(cfg.get("batch"))
    src = source_text(cfg, s.source_count)
    out = f"saída: {output_dir_text(cfg)}" if batch else basename(s.output_path)
    top = hero([
        Text(""),
        Text("   READY TO ENCODE", style="title"),
        Text(""),
        Text(f"   {src}   {g['arrow']}   {out}"),
        Text(f"   {pipeline_label(cfg)}", style="muted"),
    ], height=7)
    two = cfg.get("mode") == "2pass"
    cineon = cfg.get("cineon_pipeline") == "on"
    key = panel(kv_table([
        ("SOURCE", src),
        ("OUTPUT", out),
        ("PIPELINE", pipeline_label(cfg)),
        ("", ""),
        ("MODO", f"{cfg.get('mode')} · {'2 passes' if two else '1 passe'}"),
        ("FPS", f"{cfg.get('fps')} · {cfg.get('fit')} · scale {cfg.get('scale')}"),
        ("COR", f"LUT {cfg.get('lut')} · HDR {cfg.get('hdr')} · {cfg.get('tonemap')}"),
        ("ÁUDIO", f"loudnorm {cfg.get('loudnorm')} · alvo instagram"),
        ("ENHANCE", f"{cfg.get('enhance')} · AI {cfg.get('enhance_ai')} · MCTF {cfg.get('mctf')} · dither {cfg.get('dither')}"),
        ("PERF", f"{cfg.get('performance')} · threads {cfg.get('threads')}"),
    ]), "KEY SETTINGS", height=15)
    analyzing = [n for n, on in (("enhance", cfg.get("enhance") == "on"),
                                 ("MCTF máscara", cfg.get("mctf") == "on" and cfg.get("enhance_ai") == "on"),
                                 ("loudness da fonte", cfg.get("loudnorm") == "on")) if on]
    if cineon:
        encoding = f"FILM RENDER · {'PASS 1 / 2 + PASS 2 / 2' if two else 'passe único'}"
    else:
        encoding = "PASS 1 / 2 + PASS 2 / 2" if two else "passe único CRF"
    report_on = cfg.get("report", "on") == "on"
    plan = panel(kv_table([
        ("○ PREPARING", "hardware · validação"),
        ("○ PROBING", "duração · frames · fps · HDR"),
        ("○ ANALYZING", " · ".join(analyzing) if analyzing else "—"),
        ("○ ENCODING", encoding),
        ("○ QC", "EBU R128 · checks do master"),
        ("○ COMPLETED", "MASTER QC · certificado" if report_on else "MASTER QC · certificado desativado"),
    ]), "PIPELINE PLAN", height=15)
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(key, plan)
    if batch:
        cert = "<vídeo>.qc.html · .qc.json por vídeo" if report_on else "certificado desativado (--report off)"
        meter = "suprimido em batch (motor)"
    else:
        base = os.path.splitext(basename(s.output_path))[0]
        cert = f"{base}.qc.html · .qc.json" if report_on else "certificado desativado (--report off)"
        meter = "FFplay ANTES / DEPOIS" if cfg.get("ebu_meter", "on") == "on" else "desligado"
    qc = panel(kv_table([
        ("10 checks no master", "Container · Video · Resolution · Bit Depth · Color · FPS"),
        ("", "Loudness · True Peak · Codec · Sample Rate"),
        ("certificado", cert),
        ("monitor EBU", meter),
    ]), "QC / DELIVERY", height=6)
    actions = Table.grid(expand=True)
    actions.add_column(justify="left")
    actions.add_column(justify="right")
    esc = "Voltar" if s.preset else "Sair"
    start = "START QUEUE" if batch else "START ENCODE"
    actions.add_row(Text(f"   [ ESC  {esc} ]", style="muted"),
                    Text(f"{g['tab_l']}{g['arrow']}   {start}   ", style="tab.active"))
    parts = [top, mid, qc]
    if s.ready_error:
        parts.append(Text(f"   {s.ready_error}", style="err"))
    parts.append(actions)
    return Group(*parts)
```

Acrescentar, antes de `_SOURCE_STATUS`:

```python
_FOLDER_STATUS = {
    "VALID": ("✓ pasta encontrada · {videos}", "ok"),
    "EMPTY": ("⚠ nenhum vídeo encontrado", "warn"),
    "NOT_FOUND": ("✗ pasta não encontrada", "err"),
    "INVALID": ("⚠ informe uma pasta de vídeos", "warn"),
    "CHECKING": ("verificando…", "muted"),
}


def _program(s: S.UIState, d: dict, folder: bool) -> RenderableType:
    fit = d.get("fit", "contain")
    if folder:
        return Group(Text(f" pasta · {videos(s.source_count)}", style="muted"),
                     C.viewer_frame(fit=fit, src_dims=None, title="PROGRAM"))
    return C.viewer_frame(fit=fit, src_dims=s.source_dims, title="PROGRAM")


def _tipo_row(s: S.UIState, folder: bool) -> Text:
    g = glyphs()
    style = "tab.active" if s.tab_focus else "value"
    out = Text(f"{g['tab_l']}{g['arrow']} " if s.tab_focus else "", style=style)
    out.append(f"{'○' if folder else '●'} Arquivo único   {'●' if folder else '○'} Pasta (batch)", style=style)
    return out
```

Substituir `_source` inteira:

```python
def _source(s: S.UIState) -> RenderableType:
    dd = S.draft(s)
    folder = F.is_folder(dd)
    path = W.clean_path(s.source.text) or None
    d = {**dd, ("batch" if folder else "input"): path}
    rows = []
    if s.preset == 5:
        rows.append(("TIPO", _tipo_row(s, folder)))
    if folder:
        msg, style = _FOLDER_STATUS.get(s.source_status, ("—", "muted"))
        rows += [
            ("PASTA", path_field(s.source, 60)),
            ("STATUS", Text(msg.format(videos=videos(s.source_count)), style=style)),
            ("VÍDEOS", videos(s.source_count) if s.source_count is not None else "—"),
            ("SAÍDA", output_dir_text(F.to_config(d))),
        ]
    else:
        msg, style = _SOURCE_STATUS.get(s.source_status, ("—", "muted"))
        rows += [
            ("ARQUIVO", path_field(s.source, 60)),
            ("STATUS", Text(msg, style=style)),
            ("DIMENSÕES", f"{s.source_dims[0]} × {s.source_dims[1]}" if s.source_dims else "—"),
            ("SAÍDA", F.output_name(d)),
        ]
    left = panel(kv_table(rows), "SOURCE", height=26)
    right = Panel(_program(s, d, folder), height=26, box=PANEL_BOX, border_style="panel.border")
    mid = Table.grid(expand=True)
    mid.add_column(ratio=76)
    mid.add_column(ratio=40)
    mid.add_row(left, right)
    nxt = "ENTER → ADVANCED" if s.preset == 5 else "ENTER → CONFIGURATION"
    return Group(mid, panel(Text(f" {nxt}", style="accent"), "PRÓXIMO", height=4))
```

Substituir `_value_text`:

```python
def _value_text(s: S.UIState, field, d: dict, focused: bool) -> Text:
    if field is F.CONTINUE:
        return Text("[ CONTINUAR ▸ ]", style="tab.active" if focused else "accent")
    if focused and s.edit is not None and field.kind in ("number", "path"):
        return path_field(s.edit, 20)
    v = d.get(field.name)
    if field.kind == "choice":
        return Text(f"◂ {v} ▸")
    if field.kind == "toggle":
        return Text(f"[{v}]", style="ok" if v == "on" else "muted")
    if field.kind == "number":
        return Text(W._fmt(v))
    if field.kind == "path":
        return Text(elide(v, 20) if v else "—", style="value" if v else "muted")
    return Text(str(v))
```

Em `_configuration`, substituir as duas primeiras linhas do corpo (de `d = S.draft(s)` até o `strip = panel(...)` inclusive):

```python
    d = S.draft(s)
    if F.is_folder(d):
        cfg = F.to_config(d)
        where = ("PASTA", f"{elide(cfg.get('batch'), 50)} · {videos(s.source_count)} · saída: {output_dir_text(cfg)}")
    else:
        where = ("ENTRADA", basename(d.get("input")))
    strip = panel(kv_table([("PIPELINE", pipeline_label(d)), where]), "RESUMO", height=4)
```

Substituir `_preview` inteira:

```python
def _preview(s: S.UIState) -> RenderableType:
    g = glyphs()
    d = S.draft(s)
    folder = F.is_folder(d)
    if folder:
        cfg = F.to_config(d)
        title = f"PREVIEW · {source_text(cfg, s.source_count)} {g['arrow']} saída: {output_dir_text(cfg)}"
    else:
        title = f"PREVIEW · {basename(d.get('input'))} {g['arrow']} {F.output_name(d)}"
    inner = Table.grid(expand=True)
    inner.add_column(ratio=34)
    inner.add_column(ratio=78)
    inner.add_row(Panel(_program(s, d, folder), height=20, box=PANEL_BOX, border_style="panel.border"),
                  panel(kv_table(preview_rows(d)), "EXPORT SETTINGS", height=20))
    card = Panel(Group(inner, _chips_line(d)), title=f"[panel.title]{escape(title)}[/]", title_align="left",
                 box=PANEL_BOX, border_style="accent", height=28)
    actions = Text("   ")
    for i, label in enumerate(("CONTINUAR ▸ READY", "REVISAR")):
        focused = s.action_focus == i
        actions.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    parts = [card]
    if s.field_error:
        parts.append(Text(f"   {s.field_error}", style="err"))
    parts.append(actions)
    return Group(*parts)
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -q` (inclui `test_program_frame_cover_portrait_keeps_bars_aligned`, que aceita os dois estilos de canto); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens_config.py
git commit -m "feat(tui): telas SOURCE, CONFIGURATION, PREVIEW e READY para pasta (P3D)"
```

---

### Task 6: `screens.py` (2/2) — QUEUE, REPORT, trilho batch e resumo da fila

**Files:**
- Modify: `ui/tui/screens.py`
- Test: `ui/tui/test_screens_batch.py` (novo)

**Interfaces:**
- Consumes: `S.QUEUE`, `S.REPORT`, `S.REPORT_ROWS`, `S.Job`, `S.queue_counts`, `S.queue_eta`, `UIState.queue/active_job/queue_started/queue_finished/is_batch/queue_scroll/removal_failed` (Task 4); `elide`, `folder_name`, `videos`, `output_dir_text`, `source_text` (Task 5).
- Produces:
  - `BATCH_RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "QUEUE", "REPORT")`; `batch_view(s) -> bool` (telas de configuração: preset ≠ 0 e rascunho de pasta, fora da HOME; demais: `s.is_batch`).
  - `QUEUE_ROWS = 9`; `mmss(seconds) -> str`; `job_status(s, job) -> Text`; `job_time(job) -> str`; `queue_start(total, active, rows, scroll=None) -> int`; `queue_table(s, start, rows) -> Table`.
  - `queue_summary(s, code: int) -> Text` — usado pela Task 7: `✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)`; `✗ fila: 0 ok · 1 pulado · 1 falha (código 1)`; `⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 1 interrompido (código 130)`.
  - Renderers `SCREEN_RENDERERS[S.QUEUE]`, `SCREEN_RENDERERS[S.REPORT]`; `STATUS`/`FOOTER_KEYS` para as duas; cabeçalho `QUEUE · JOB n/N` com spinner; `cancel_modal` diz "CANCELAR FILA?" em batch.
  - Layout QUEUE (34 linhas): faixa 1 + RENDER QUEUE 12 (cabeçalho + 9 linhas) + `_progress_header` 7 + LOG 14. REPORT: hero 6 + FILA `REPORT_ROWS + 3` + aviso opcional 1 + ação 1.

- [ ] **Step 1: Write the failing test** — `ui/tui/test_screens_batch.py`

```python
from dataclasses import replace

import reporter as R
from ui.config import EncodeConfig
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of
from ui.tui.test_screens_config import folder_state


def batch_cfg(**kw):
    return {**vars(EncodeConfig.preset_batch("C:/v/lote").to_namespace()), **kw}


def queue_state(n=3, active=1):
    jobs = tuple((f"C:/v/lote/clip_{i:02d}.mov", f"C:/v/lote/clip_{i:02d}_Hollywood_CRF18.mp4") for i in range(n))
    s = S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3, now=100.0, source_count=n)
    t = 100.0
    evs = [R.QueueInit(jobs, ts=t)]
    for i in range(active):
        evs += [R.JobStart(i, job_id=i, ts=t), R.JobDone(i, "ok", None, job_id=i, ts=t + 60)]
        t += 60
    evs += [R.JobStart(active, job_id=active, ts=t), R.Stage(R.PASS, "1", job_id=active, ts=t + 1),
            R.Pass(1, 1, "Encode", "start", job_id=active, ts=t + 1),
            R.Progress(300, 900, 30.0, 1.2, "00:00:20", 10.0, job_id=active, ts=t + 11),
            R.FfmpegLine("frame=  300 fps= 30", job_id=active, ts=t + 11)]
    for ev in evs:
        s = S.apply(s, ev)
    return replace(s, now=t + 20)


def report_state(cancel=False):
    jobs = tuple((f"C:/v/lote/clip_{i}.mov", f"C:/v/lote/clip_{i}_Hollywood_CRF18.mp4") for i in range(4))
    msg = "Command '[ffmpeg]' returned non-zero exit status 1."
    evs = [R.QueueInit(jobs, ts=100.0), R.JobStart(0, ts=100.0), R.JobDone(0, "ok", None, ts=160.0),
           R.JobSkip(1, "output existe"), R.JobStart(2, ts=160.0),
           R.Error("CalledProcessError", msg, None, 1, "tb", job_id=2, ts=200.0),
           R.JobDone(2, "falha", msg + "\nTraceback (most recent call last)", ts=200.0), R.JobStart(3, ts=200.0)]
    if cancel:
        evs += [R.Cancel("requested", ts=210.0), R.JobDone(3, "falha", "cancelado pelo usuário", ts=211.0),
                R.Info("NÃO foi possível remover clip_3_Hollywood_CRF18.mp4", job_id=3, ts=212.0),
                R.QueueDone(130, ts=212.0)]
    else:
        evs += [R.JobDone(3, "ok", None, ts=260.0), R.QueueDone(1, ts=260.0)]
    s = S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3, now=100.0)
    for ev in evs:
        s = S.apply(s, ev)
    return s


def test_queue_screen_three_jobs():
    out = text_of(queue_state())
    for txt in ("BATCH", "C:/v/lote", "3 arquivos", "saída: mesma pasta", "RENDER QUEUE", "Job 2 de 3",
                "ETA 01:40", "JOB", "ARQUIVO", "STATUS", "ETA/DURAÇÃO", "RESULTADO", "clip_00.mov",
                "✓ COMPLETED", "01:00", "ENCODING", "· QUEUED", "…", "PASS 1 / 1", "frame=  300", "LOG",
                "QUEUE · JOB 2/3", "[C] Cancelar fila", "[D] Details"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_queue_screen_twenty_jobs_scrolls_to_active():
    out = text_of(queue_state(n=20, active=15))
    assert "clip_15.mov" in out and "clip_19.mov" in out and "clip_00.mov" not in out
    assert "Job 16 de 20" in out and "ETA 04:40" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_queue_eta_dash_before_first_done():
    out = text_of(queue_state(active=0))
    assert "ETA —" in out and "Job 1 de 3" in out


def test_queue_cancel_modal_and_blocked_footer():
    out = text_of(S.apply(queue_state(), S.Key("C")))
    assert "CANCELAR FILA?" in out and "CONTINUAR FILA" in out and "CANCELAR FILA ]" in out
    assert "RENDER QUEUE" in out
    assert_fits(out)
    blocked = S.apply(queue_state(), R.Stage(R.ANALYZING, "mctf_mask", ts=500.0))
    assert "░[C] Cancelar fila" in text_of(blocked)


def test_batch_rail_on_queue_and_folder_source():
    rail = text_of(queue_state()).splitlines()[1]
    assert "QUEUE" in rail and "REPORT" in rail and "DELIVERY" not in rail and "✓ READY" in rail
    rail = text_of(folder_state()).splitlines()[1]
    assert "REPORT" in rail and "DELIVERY" not in rail
    rail = text_of(S.UIState(config={}, screen=S.SOURCE, preset=1)).splitlines()[1]
    assert "DELIVERY" in rail and "REPORT" not in rail


def test_report_with_failure():
    out = text_of(report_state())
    for txt in ("✗ FILA CONCLUÍDA COM FALHAS", "Sucesso 2/4", "Pulados 1", "Falhas 1", "Interrompidos 0",
                "Tempo total 00:02:40", "Código de saída 1", "saída já existe", "Command '[ffmpeg]' returned",
                "✓ COMPLETED", "○ SKIPPED", "✗ FAILED", "SAIR", "[ENTER] Sair"):
        assert txt in out, txt
    assert "Traceback" not in out and "NÃO foi possível remover" not in out
    assert_fits(out)
    assert_no_emoji(out)


def test_report_with_interrupted():
    out = text_of(report_state(cancel=True))
    for txt in ("⚠ FILA INTERROMPIDA", "Sucesso 1/4", "Interrompidos 1", "Código de saída 130",
                "⚠ CANCELLED", "interrompido"):
        assert txt in out, txt
    assert "⚡" not in out
    assert_fits(out)
    assert_no_emoji(out)


def test_report_warns_unremovable_partial():
    out = text_of(report_state(cancel=True))
    assert "NÃO foi possível remover clip_3_Hollywood_CRF18.mp4" in out and "rodar a fila de novo" in out


def test_report_scrolls_long_queue():
    jobs = tuple((f"C:/v/lote/clip_{i:02d}.mov", f"C:/v/lote/clip_{i:02d}_o.mp4") for i in range(30))
    s = S.apply(S.UIState(config=batch_cfg(), screen=S.QUEUE, is_batch=True, preset=3), R.QueueInit(jobs))
    s = S.apply(s, R.QueueDone(0))
    out = text_of(s)
    assert "clip_00.mov" in out and "clip_20.mov" in out and "clip_21.mov" not in out
    for _ in range(5):
        s = S.apply(s, S.Key("DOWN"))
    out = text_of(s)
    assert "clip_05.mov" in out and "clip_25.mov" in out and "clip_04.mov" not in out
    assert_fits(out)


def test_long_and_bracketed_names_fit():
    folder = "C:/v/[2026] " + "p" * 200
    name = "clip [1080p] " + "n" * 150
    jobs = ((f"{folder}/{name}.mov", f"{folder}/{name}_Hollywood_CRF18.mp4"),)
    cfg = batch_cfg(batch=folder, output_dir="D:/" + "o" * 200)
    s = S.UIState(config=cfg, screen=S.QUEUE, is_batch=True, preset=3, now=100.0)
    s = S.apply(S.apply(s, R.QueueInit(jobs, ts=100.0)), R.JobStart(0, ts=100.0))
    out = text_of(s)
    assert "erro ao desenhar" not in out and "nnnn" in out
    assert_fits(out)
    s = S.apply(S.apply(s, R.JobDone(0, "falha", "[x] " + "e" * 300, ts=150.0)), R.QueueDone(1, ts=150.0))
    out = text_of(s)
    assert "erro ao desenhar" not in out and "[x] eee" in out
    assert_fits(out)
    ready = S.UIState(config=cfg, screen=S.READY, is_batch=True, preset=3, source_count=1)
    assert_fits(text_of(ready))


def test_queue_summary_lines():
    assert V.queue_summary(report_state(), 1).plain == "✗ fila: 2 ok · 1 pulado · 1 falha (código 1)"
    assert V.queue_summary(report_state(cancel=True), 130).plain == \
        "⚠ fila interrompida: 1 ok · 1 pulado · 1 falha · 1 interrompido (código 130)"
    ok = S.UIState(config={}, queue=(S.Job("a", "b", "ok"), S.Job("c", "d", "ok")))
    assert V.queue_summary(ok, 0).plain == "✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)"
```

As durações dos jobs vêm dos `ts` dos eventos (60 s cada) e o "agora" do job ativo é `now = t + 20`, então ETA = 60 × restantes + (60 − 20). Em `report_state`, o tempo total é 260 − 100 = 160 s.

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_screens_batch.py -v` → FAIL (`AttributeError: queue_summary`, tela QUEUE sem renderer).

- [ ] **Step 3: Implement** — em `ui/tui/screens.py`:

Constantes, depois de `RAIL`:

```python
BATCH_RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "QUEUE", "REPORT")
QUEUE_ROWS = 9
JOB_LABEL = {
    "aguardando": ("· QUEUED", "muted"), "ok": ("✓ COMPLETED", "ok"), "pulado": ("○ SKIPPED", "muted"),
    "falha": ("✗ FAILED", "err"), "interrompido": ("⚠ CANCELLED", "warn"),
}
REPORT_TITLE = {0: ("✓ FILA CONCLUÍDA", "ok"), 1: ("✗ FILA CONCLUÍDA COM FALHAS", "err"),
                130: ("⚠ FILA INTERROMPIDA", "warn")}
```

Em `STATUS` acrescentar `S.QUEUE: "QUEUE", S.REPORT: "● REPORT",`; em `FOOTER_KEYS`:

```python
    S.QUEUE: "[D] Details   [L] Log   [C] Cancelar fila   [Ctrl+C] Interrupt",
    S.REPORT: "[↑↓] Rolar   [ENTER] Sair   [ESC] Sair",
```

Substituir `_status`, `_rail_active`, `header`, `footer` e acrescentar `batch_view`:

```python
def _status(s: S.UIState) -> str:
    base = STATUS.get(s.screen, s.screen)
    if s.modal == "CANCEL":
        return "⚠ CANCEL?"
    if s.cancel_phase is not None and s.screen not in S.FINAL_SCREENS and s.screen != S.READY:
        return "⚠ CANCELANDO"
    if s.screen in (S.ENCODING, S.QC, S.QUEUE) and s.exit_code is None:
        spin = SPINNER[int(s.now * 10) % len(SPINNER)]
        track = S.active_pass(s)
        if s.screen == S.QUEUE:
            suffix = f" · JOB {s.active_job + 1}/{len(s.queue)}" if s.active_job is not None else ""
        else:
            suffix = f" · PASS {track.index}/{track.total}" if s.screen == S.ENCODING and track else ""
        return f"{spin} {base}{suffix}"
    return base


def _rail_active(s: S.UIState) -> str:
    if s.screen == S.REPORT:
        return "REPORT"
    if s.screen == S.QUEUE:
        return "QUEUE"
    if s.screen == S.HOME:
        return "HOME"
    if s.screen == S.SOURCE:
        return "SOURCE"
    if s.screen in (S.CONFIGURATION, S.ADVANCED):
        return "CONFIG"
    if s.screen == S.PREVIEW:
        return "PREVIEW"
    if s.screen == S.READY:
        return "READY"
    if s.screen in (S.COMPLETED,):
        return "DELIVERY"
    if s.screen == S.QC:
        return "QC"
    return "ENCODE"


def batch_view(s: S.UIState) -> bool:
    if s.screen in S.CONFIG_SCREENS:
        return s.screen != S.HOME and bool(s.preset) and F.is_folder(S.draft(s))
    return s.is_batch


def header(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = Table.grid(expand=True)
    top.add_column(justify="left")
    top.add_column(justify="right")
    top.add_row(Text(f" REELS ENCODER  v{__version__}", style="title"), Text(_status(s) + " ", style="accent"))
    names = BATCH_RAIL if batch_view(s) else RAIL
    active = _rail_active(s)
    if active not in names:
        active = "QUEUE"
    idx = names.index(active)
    rail = Text(" ")
    for i, name in enumerate(names):
        if i < idx or (s.screen == S.COMPLETED and name != "DELIVERY"):
            rail.append(f"{g['ok']} {name}   ", style="ok")
        elif name == active:
            rail.append(f"{g['tab_l']}{name}   ", style="tab.active")
        else:
            rail.append(f"  {name}   ", style="tab.inactive")
    return Group(top, rail, Rule(characters="─", style="muted"))


def footer(s: S.UIState) -> RenderableType:
    keys = FOOTER_KEYS.get(s.screen, "")
    if s.modal == "CANCEL":
        keys = MODAL_KEYS
    elif s.screen in (S.QC, S.DETAILS) and s.back in S.FINAL_SCREENS:
        keys = "[ESC] Voltar"
    elif s.screen == S.LOG and s.back in S.FINAL_SCREENS:
        keys = "[←→] Filtro   [ESC] Voltar"
    elif s.screen in (S.ENCODING, S.QUEUE) and (S.cancel_blocked(s) or s.cancel_phase is not None):
        keys = keys.replace("[C] Cancel", "░[C] Cancel")
    elif s.screen == S.SOURCE and s.preset == 5:
        keys = SOURCE_TIPO_KEYS if s.tab_focus else "[↑] Tipo   " + keys
    elif s.screen == S.CONFIGURATION and s.preset == 3:
        keys = CONFIG_BATCH_KEYS
    elif s.screen == S.READY and s.preset:
        keys = keys.replace("[ESC] Sair", "[ESC] Voltar")
    return Group(Rule(characters="─", style="muted"), Text(" " + keys, style="muted"))
```

`_log_panel` ganha tamanho opcional:

```python
def _log_panel(s: S.UIState, rows: int = 9, height: int = 11) -> Panel:
    title = "LOG" + (f" [warn]⚠ {s.warnings}[/]" if s.warnings else "")
    return panel(log_rows(s.log, rows), title, height=height)
```

Substituir `cancel_modal`:

```python
def cancel_modal(s: S.UIState) -> RenderableType:
    g = glyphs()
    track = S.active_pass(s)
    where = f"{s.stage or '—'}{' · ' + s.substep if s.substep else ''}"
    pct = f" · {track.pct:.0f}%" if track else ""
    noun = "FILA" if s.is_batch else "ENCODE"
    buttons = Text("   ")
    for i, label in enumerate((f"CONTINUAR {noun}", f"CANCELAR {noun}")):
        focused = s.modal_focus == i
        buttons.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    lines = [
        Text(""),
        Text(f"  etapa ativa: {where}{pct}"),
        Text("  usa o caminho de interrupção existente (o mesmo do Ctrl+C)", style="muted"),
        Text(f"  parcial: {basename(s.output_path)}", style="muted"),
    ]
    if s.is_batch:
        lines.append(Text("  cancela a fila inteira; os jobs restantes não rodam", style="muted"))
    body = Group(*lines, Text(""), buttons)
    box = Panel(body, title=f"[warn]CANCELAR {noun}?[/]", box=PANEL_BOX, border_style="warn", width=64, height=12)
    return Align.center(box, vertical="middle", height=13)
```

Depois de `SCREEN_RENDERERS[S.LOG] = _log_screen`, acrescentar:

```python
def mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def job_status(s: S.UIState, job: S.Job) -> Text:
    if job.status == "processando":
        return Text(f"{SPINNER[int(s.now * 10) % len(SPINNER)]} ENCODING", style="accent")
    label, style = JOB_LABEL.get(job.status, (job.status, "value"))
    return Text(label, style=style)


def job_time(job: S.Job) -> str:
    if job.status == "processando":
        return "…"
    if job.started is not None and job.finished is not None:
        return mmss(job.finished - job.started)
    return "—"


def queue_start(total: int, active: int | None, rows: int, scroll: int | None = None) -> int:
    if total <= rows:
        return 0
    if scroll is not None:
        return min(max(0, scroll), total - rows)
    if active is None:
        return 0
    return max(0, min(active - rows // 2, total - rows))


def queue_table(s: S.UIState, start: int, rows: int) -> Table:
    t = Table(box=None, expand=True, padding=(0, 1), header_style="label")
    t.add_column("JOB", width=4, justify="right", no_wrap=True)
    t.add_column("ARQUIVO", width=40, no_wrap=True, overflow="ellipsis")
    t.add_column("STATUS", width=13, no_wrap=True)
    t.add_column("ETA/DURAÇÃO", width=11, no_wrap=True)
    t.add_column("RESULTADO", ratio=1, no_wrap=True, overflow="ellipsis")
    for i, job in enumerate(s.queue[start:start + rows], start=start):
        style = "err" if job.status == "falha" else "muted"
        t.add_row(Text(str(i + 1)), Text(elide(os.path.basename(job.input), 40)), job_status(s, job),
                  Text(job_time(job)), Text(job.reason or "—", style=style))
    return t


def _queue_strip(s: S.UIState) -> Text:
    g = glyphs()
    cfg = s.config
    out = cfg.get("output_dir")
    line = Text(" BATCH ", style="accent")
    line.append(elide(cfg.get("batch"), 36), style="value")
    line.append(f" · {len(s.queue)} arquivos ", style="muted")
    line.append(f"{g['arrow']} saída: {elide(out, 40) if out else 'mesma pasta'}", style="info")
    return line


def _queue(s: S.UIState) -> RenderableType:
    counts = S.queue_counts(s.queue)
    eta = S.queue_eta(s)
    title = (f"RENDER QUEUE · Job {counts['total'] - counts['aguardando']} de {counts['total']}"
             f" · ETA {mmss(eta) if eta is not None else '—'}")
    start = queue_start(len(s.queue), s.active_job, QUEUE_ROWS)
    table = panel(queue_table(s, start, QUEUE_ROWS), title, height=QUEUE_ROWS + 3)
    lower = [cancel_modal(s)] if s.modal == "CANCEL" else [_progress_header(s), _log_panel(s, 12, 14)]
    return Group(_queue_strip(s), table, *lower)


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def queue_summary(s: S.UIState, code: int) -> Text:
    c = S.queue_counts(s.queue)
    body = f"{c['ok']} ok · {_count(c['pulado'], 'pulado', 'pulados')} · {_count(c['falha'], 'falha', 'falhas')}"
    if code == 130:
        tail = _count(c["interrompido"], "interrompido", "interrompidos")
        return Text(f"⚠ fila interrompida: {body} · {tail} (código 130)", style="warn")
    if code == 0:
        return Text(f"✓ fila: {body} (código 0)", style="ok")
    return Text(f"✗ fila: {body} (código {code})", style="err")


def _report(s: S.UIState) -> RenderableType:
    g = glyphs()
    c = S.queue_counts(s.queue)
    code = s.exit_code
    title, style = REPORT_TITLE.get(code, (f"✗ FILA ENCERRADA (código {code})", "err"))
    total = s.queue_finished - s.queue_started \
        if s.queue_finished is not None and s.queue_started is not None else None
    top = hero([
        Text(f"   {title}", style=style),
        Text(f"   Sucesso {c['ok']}/{c['total']}   ·   Pulados {c['pulado']}   ·   Falhas {c['falha']}"
             f"   ·   Interrompidos {c['interrompido']}"),
        Text(f"   Tempo total {fmt_secs(total)}   ·   Código de saída {code if code is not None else '—'}",
             style="muted"),
        Text(""),
    ], height=6)
    start = queue_start(len(s.queue), None, S.REPORT_ROWS, s.queue_scroll)
    table = panel(queue_table(s, start, S.REPORT_ROWS), f"FILA · {len(s.queue)} arquivos", height=S.REPORT_ROWS + 3)
    parts = [top, table]
    if s.removal_failed:
        parts.append(Text(f"   ⚠ NÃO foi possível remover {basename(s.output_path)} — apague à mão antes de "
                          "rodar a fila de novo", style="warn"))
    parts.append(Text(f"   {g['arrow']}[ SAIR ]", style="tab.active"))
    return Group(*parts)


SCREEN_RENDERERS[S.QUEUE] = _queue
SCREEN_RENDERERS[S.REPORT] = _report
```

`_queue_strip` usa `elide(..., 36)` e `elide(..., 40)` (não `output_dir_text`, que elide a 50) para a faixa caber em 120 colunas.

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -q` (inclui `test_cancel_modal_over_dashboard`, que exige "CANCELAR ENCODE?" fora de batch); ruff.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/screens.py ui/tui/test_screens_batch.py
git commit -m "feat(tui): telas QUEUE e REPORT, trilho do batch e resumo da fila (P3D)"
```

---

### Task 7: `app.py` — pasta no SOURCE, arm batch, START com `run_batch` e resumo

**Files:**
- Modify: `ui/tui/app.py`
- Test: `ui/tui/test_app.py`

**Interfaces:**
- Consumes: `S.SourceChecked(..., count)`, `S.Armed`, `S.ReadyBlocked`, `UIState.is_batch`, `S.REPORT`, `S.FINAL_SCREENS` (Tasks 3–4); `F.is_folder`, `F.to_config` (Task 2); `queue_summary` (Task 6); `D.run_batch(ns, events, control, on_tick) -> int`; `RE.find_video_files(folder) -> list`.
- Produces: `App(..., run_batch=None)` (padrão `D.run_batch`); `_check_source` de pasta (`VALID` com contagem / `EMPTY` com 0 / `NOT_FOUND` / `INVALID` se vazio ou arquivo) sem chamar o probe; `_arm` em batch → `Armed(vars(ns), "", False, err)`; START revalida (`"pasta não encontrada: <pasta>"`, `"nenhum vídeo encontrado em: <pasta>"`, e o `"arquivo de entrada não encontrado: <arq>"` do P3C) e chama `run_batch` quando `is_batch`; `_summary` imprime `queue_summary(s, code)` no REPORT.

- [ ] **Step 1: Write the failing tests** — em `ui/tui/test_app.py`: imports do topo passam a ser

```python
import argparse
import os
import sys
from dataclasses import replace

import pytest

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from ui.theme import get_console
from ui.tui import app as A
from ui.tui import forms as F
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui import widgets as W
```

e acrescentar no fim:

```python
def batch_folder(tmp_path, names=("a.mov", "b.mov")):
    folder = tmp_path / "lote"
    folder.mkdir()
    for n in names:
        (folder / n).write_bytes(b"x")
    return folder


def fake_batch(events, code, record):
    def run(ns_, q, control, on_tick):
        record.append(ns_)
        jobs = tuple((p, os.path.splitext(p)[0] + "_Hollywood_CRF18.mp4") for p in RE.find_video_files(ns_.batch))
        for ev in (R.QueueInit(jobs), *events, R.QueueDone(code)):
            q.put(ev)
            on_tick()
        record.append(control.cancelled)
        return code
    return run


def batch_app(folder, run_batch, **kw):
    holder = []

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS | {S.READY}:
            holder[0]._queue.put(S.Key("ENTER"))

    def no_single(*a):
        raise AssertionError("run_single chamado em batch")

    def no_probe(p):
        raise AssertionError("probe chamado para pasta")

    keys = [("CHAR", "3")] + keys_for(str(folder)) + ["ENTER"] * 6
    app = A.App(run_single=no_single, run_batch=run_batch, reader_factory=CharReader(keys),
                live_factory=lambda c: FakeLive(), clock=Clock(), sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=no_probe, **kw)
    holder.append(app)
    return app


def summary_lines(con):
    return [ln for ln in con.export_text().splitlines() if ln.strip()]


@pytest.mark.timeout(30)
def test_batch_flow_home_to_report_code_0(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.JobDone(0, "ok", None), R.JobStart(1), R.JobDone(1, "ok", None)]
    app = batch_app(folder, fake_batch(evs, 0, rec), console=con)
    assert app.run() == 0
    ns_ = rec[0]
    assert ns_.batch == str(folder) and ns_.input is None and ns_.output_dir is None
    assert ns_.cineon_pipeline == "off" and not hasattr(ns_, F.OUTDIR_ON)
    assert app.state.screen == S.REPORT and [j.status for j in app.state.queue] == ["ok", "ok"]
    assert summary_lines(con) == ["✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)"]


@pytest.mark.timeout(30)
def test_batch_flow_failure_code_1(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.Error("CalledProcessError", "ffmpeg falhou", None, 1, "tb", job_id=0),
           R.JobDone(0, "falha", "ffmpeg falhou\ndetalhe"), R.JobSkip(1, "output existe")]
    app = batch_app(folder, fake_batch(evs, 1, rec), console=con)
    assert app.run() == 1
    assert [(j.status, j.reason) for j in app.state.queue] == [("falha", "ffmpeg falhou"), ("pulado", "saída já existe")]
    assert app.state.screen == S.REPORT and app.state.error is None
    assert summary_lines(con) == ["✗ fila: 0 ok · 1 pulado · 1 falha (código 1)"]


@pytest.mark.timeout(30)
def test_batch_cancel_from_queue_code_130(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.Stage(R.PASS, "1", job_id=0), S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"),
           R.JobDone(0, "falha", "cancelado pelo usuário"), R.Cancel("terminated"), R.Cancel("cleaned", True)]
    app = batch_app(folder, fake_batch(evs, 130, rec), console=con, terminate=lambda: True)
    assert app.run() == 130
    assert rec[-1] is True
    assert [j.status for j in app.state.queue] == ["interrompido", "aguardando"]
    assert summary_lines(con) == ["⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 1 interrompido (código 130)"]


@pytest.mark.timeout(30)
def test_batch_error_before_queue_goes_to_error_screen(tmp_path):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        q.put(R.Error("batch_folder", f"Pasta não encontrada: {ns_.batch}", None, None, None))
        on_tick()
        return 1

    app = batch_app(folder, run, console=con)
    assert app.run() == 1 and app.state.screen == S.ERROR
    assert summary_lines(con) == [f"✗ erro (código 1): batch_folder: Pasta não encontrada: {folder}"]


def test_check_source_folder_counts_videos_like_engine(tmp_path):
    lote = batch_folder(tmp_path, names=("a.mov", "B.MP4", "a_Hollywood_CRF18.mp4", "notas.txt"))
    (lote / "sub").mkdir()
    (lote / "sub" / "c.mov").write_bytes(b"x")
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    app, _, _ = make_home(tmp_path, [])

    def no_probe(p):
        raise AssertionError("probe chamado para pasta")

    app._probe = no_probe
    app.state = S.apply(app.state, S.Key("CHAR", "3"))
    cases = ((lote, "VALID", 2), (vazia, "EMPTY", 0), (tmp_path / "nada", "NOT_FOUND", None),
             (lote / "a.mov", "INVALID", None), ("", "INVALID", None))
    for path, status, count in cases:
        text = str(path)
        app.state = replace(app.state, source=W.TextBuf(text, len(text)))
        app._check_source()
        assert (app.state.source_status, app.state.source_count) == (status, count), path


def test_arm_batch_has_no_single_output(tmp_path):
    folder = batch_folder(tmp_path)
    app, _, _ = make_home(tmp_path, [])
    d = {**F.new_draft(3), "batch": str(folder), F.OUTDIR_ON: "on", "output_dir": str(tmp_path / "saida")}
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=3, drafts=((3, d),), source_count=2)
    app._arm()
    s = app.state
    assert s.screen == S.READY and s.is_batch and s.output_path == "" and not s.output_preexisted
    assert s.config["batch"] == str(folder) and s.config["input"] is None
    assert s.config["output_dir"] == str(tmp_path / "saida")


def ready_batch_app(tmp_path, folder, ran, monkeypatch, seen_errors):
    app, _, _ = make_home(tmp_path, ["ENTER", "ESC", "ESC", "ESC", "ESC", "ESC"],
                          run_batch=lambda *a: ran.append(1) or 0)
    app.state = S.UIState(config={"batch": str(folder), "input": None}, screen=S.READY, preset=3, is_batch=True)
    app._ready_at = 0.0
    orig_apply = S.apply

    def spy(s, ev):
        out = orig_apply(s, ev)
        if out.ready_error:
            seen_errors.append(out.ready_error)
        return out

    monkeypatch.setattr(S, "apply", spy)
    return app


def test_ready_blocks_emptied_folder(tmp_path, monkeypatch):
    folder = batch_folder(tmp_path, names=("a.mov",))
    (folder / "a.mov").unlink()
    ran, errors = [], []
    app = ready_batch_app(tmp_path, folder, ran, monkeypatch, errors)
    assert app.run() == 0
    assert ran == [] and errors and errors[0] == f"nenhum vídeo encontrado em: {folder}"


def test_ready_blocks_missing_folder(tmp_path, monkeypatch):
    ran, errors = [], []
    app = ready_batch_app(tmp_path, tmp_path / "sumiu", ran, monkeypatch, errors)
    assert app.run() == 0
    assert ran == [] and errors and errors[0] == f"pasta não encontrada: {tmp_path / 'sumiu'}"


@pytest.mark.timeout(30)
def test_batch_held_enter_after_arm_never_starts_queue(tmp_path):
    folder = batch_folder(tmp_path)
    ran = []
    clock = StillClock()
    seen = {"ready": None, "loops": 0}

    def sleep(_):
        seen["loops"] += 1
        if seen["loops"] > 2000:
            raise KeyboardInterrupt
        if app.state.screen in S.FINAL_SCREENS:
            app._queue.put(S.Key("ENTER"))
        elif app.state.screen == S.READY:
            if seen["ready"] is None:
                seen["ready"] = clock.t
            if clock.t - seen["ready"] > 6.0:
                raise KeyboardInterrupt
            clock.t += 0.03
            app._queue.put(S.Key("ENTER"))

    app = A.App(run_batch=lambda *a: ran.append(1) or 0, reader_factory=CharReader(["ENTER"]),
                live_factory=lambda c: FakeLive(), clock=clock, sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=lambda p: None)
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=3, source_count=2,
                          drafts=((3, {**F.new_draft(3), "batch": str(folder)}),))
    assert app.run() == 130
    assert ran == [] and app.state.screen == S.READY and app.state.is_batch
```

Notas para o executor: (1) as teclas do `CharReader` chegam todas no início; as ENTER extras depois do `arm` são descartadas por `_drop_queued_keys` — por isso o ENTER do READY e o do REPORT vêm do `sleep` (como em `test_full_flow_home_to_completed`), e o `Clock` de +0,5 s por chamada vence `READY_HOLD_S`/`KEY_GAP_S`. (2) Em `fake_batch`, as `S.Key` postas direto na fila (sem `_Arrived`) são aceitas fora do READY. (3) A sequência de ESC em `ready_batch_app` volta READY → PREVIEW → CONFIGURATION → SOURCE → HOME → sair.

- [ ] **Step 2: Run to verify it fails** — `venv\Scripts\python.exe -m pytest ui/tui/test_app.py -v` → novos falham (`TypeError: unexpected keyword 'run_batch'`).

- [ ] **Step 3: Implement** — em `ui/tui/app.py`:

Import: `from ui.tui.screens import error_message, partial_wording, queue_summary, render`.

Construtor: acrescentar `run_batch=None` depois de `run_single=None` na assinatura e, depois de `self._run_single = ...`:

```python
        self._run_batch = run_batch or D.run_batch
```

`_summary`, primeiro ramo:

```python
        if s.screen == S.REPORT:
            line = queue_summary(s, code)
        elif s.screen == S.COMPLETED:
```

(o `if s.screen == S.COMPLETED:` existente vira `elif`.)

Em `_session`, substituir o trecho do `inp = ...` até o `code = self._run_single(...)`:

```python
            blocked = self._start_blocked()
            if blocked:
                self.state = S.apply(self.state, S.ReadyBlocked(blocked))
                continue
            break
        ns = self._ns if self._ns is not None else argparse.Namespace(**self.state.config)
        runner = self._run_batch if self.state.is_batch else self._run_single
        code = runner(ns, self._queue, self._control, self._tick)
```

Novo método, depois de `_session`:

```python
    def _start_blocked(self) -> str | None:
        cfg = self.state.config
        if self.state.is_batch:
            folder = cfg.get("batch") or ""
            if not os.path.isdir(folder):
                return f"pasta não encontrada: {folder}"
            if not RE.find_video_files(folder):
                return f"nenhum vídeo encontrado em: {folder}"
            return None
        inp = cfg.get("input") or ""
        if not os.path.isfile(inp):
            return f"arquivo de entrada não encontrado: {inp}"
        return None
```

Substituir `_check_source` e acrescentar `_check_folder`:

```python
    def _check_source(self) -> None:
        path = W.clean_path(self.state.source.text)
        if F.is_folder(S.draft(self.state)):
            self.state = S.apply(self.state, self._check_folder(path))
            return
        if not path or os.path.isdir(path):
            status = "INVALID"
        elif os.path.isfile(path):
            status = "VALID"
        else:
            status = "NOT_FOUND"
        dims = None
        if status == "VALID":
            if self._probed is None or self._probed[0] != path:
                self._probed = (path, self._probe(path))
            dims = self._probed[1]
        self.state = S.apply(self.state, S.SourceChecked(path, status, dims))

    @staticmethod
    def _check_folder(path: str) -> S.SourceChecked:
        if not path or os.path.isfile(path):
            return S.SourceChecked(path, "INVALID")
        if not os.path.isdir(path):
            return S.SourceChecked(path, "NOT_FOUND")
        count = len(RE.find_video_files(path))
        return S.SourceChecked(path, "VALID" if count else "EMPTY", None, count)
```

Em `_arm`, substituir as linhas de `err = ...` até `armed = S.Armed(...)` dentro do `try`:

```python
            err = RE._validate_args_consistency(ns)
            if ns.batch:
                armed = S.Armed(vars(ns), "", False, err)
            else:
                out = D._single_output_path(ns)
                armed = S.Armed(vars(ns), out, os.path.exists(out), err)
```

- [ ] **Step 4: Run** — `venv\Scripts\python.exe -m pytest ui/tui/ -v` 3× (flake de tempo); `venv\Scripts\python.exe -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`; `venv\Scripts\python.exe -m ruff check .`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui/app.py ui/tui/test_app.py
git commit -m "feat(tui): App roda a fila com run_batch, revalida a pasta e resume a fila (P3D)"
```

---

### Task 8: Paridade TUI × wizard nos cenários batch

**Files:**
- Modify: `ui/tui/test_parity_wizard.py`

**Interfaces:**
- Consumes: `ui.launcher.run_launcher`, `ask_folder` (importado por nome em `ui/launcher.py` → monkeypatch em `L`), `L.Confirm.ask`; `F.OUTDIR_ON`, `F.is_folder`, `F.to_config`; helpers do próprio arquivo (`press`, `type_text`, `goto_field`, `set_field`).

- [ ] **Step 1: Write the test** — acrescentar ao fim de `ui/tui/test_parity_wizard.py`:

```python
BATCH_SCENARIOS = [
    pytest.param(3, False, {}, {}, id="preset3-so-pasta"),
    pytest.param(3, True, {"Usar film look": "on"}, {"cineon_pipeline": "on"}, id="preset3-saida-cineon"),
    pytest.param(5, True, {"É um batch": "on"}, {}, id="preset5-pasta-saida"),
]


def wizard_batch_ns(monkeypatch, preset, folder, out_dir, answers, used):
    folders = {"Pasta com os vídeos": folder, "Pasta de saída": out_dir}

    def pick(message, default):
        for k, v in answers.items():
            if k in message:
                used.add(k)
                return v
        return default

    def confirm(message, *a, **k):
        if "Iniciar" in message:
            return True
        if "saída separada" in message:
            return out_dir is not None
        return k.get("default", False)

    def no_path(con, message, must_exist=True):
        raise AssertionError(f"ask_path em batch: {message}")

    monkeypatch.setattr(L, "ask_choice", lambda con, title, options, default=1: preset)
    monkeypatch.setattr(L, "ask_folder",
                        lambda con, message, must_exist=True: next(v for k, v in folders.items() if k in message))
    monkeypatch.setattr(L, "ask_path", no_path)
    monkeypatch.setattr(L, "ask_select", lambda con, message, options, default: pick(message, default))
    monkeypatch.setattr(L, "ask_toggle", lambda con, message, default_on=True: pick(message, "on" if default_on else "off"))
    monkeypatch.setattr(L, "ask_number",
                        lambda con, message, default, lo=None, hi=None, integer=False: pick(message, default))
    monkeypatch.setattr(L, "probe_source_dims", lambda p: None, raising=False)
    monkeypatch.setattr(L.Confirm, "ask", confirm)
    return L.run_launcher(Console(file=io.StringIO(), width=120, theme=THEME))


def tui_batch_ns(preset, folder, out_dir, values):
    s = S.UIState(config={}, screen=S.HOME)
    s = press(s, "CHAR", str(preset))
    if preset == 5:
        s = press(press(press(s, "UP"), "RIGHT"), "DOWN")
    assert F.is_folder(S.draft(s))
    s = type_text(s, folder)
    s = S.apply(s, S.SourceChecked(folder, "VALID", None, 1))
    s = press(s, "ENTER")
    if out_dir is not None:
        s = set_field(s, F.OUTDIR_ON, "on")
        s, _ = goto_field(s, "output_dir")
        s = press(type_text(s, out_dir), "ENTER")
        assert s.field_error is None
    for name, value in values.items():
        s = set_field(s, name, value)
    return EncodeConfig.model_validate(F.to_config(S.draft(s))).to_namespace()


@pytest.mark.parametrize("preset,with_out,answers,values", BATCH_SCENARIOS)
def test_tui_batch_matches_line_wizard(monkeypatch, tmp_path, preset, with_out, answers, values):
    folder = tmp_path / "lote"
    folder.mkdir()
    (folder / "a.mov").write_bytes(b"x")
    out_dir = str(tmp_path / "saida") if with_out else None
    used = set()
    want = wizard_batch_ns(monkeypatch, preset, str(folder), out_dir, answers, used)
    assert set(answers) == used
    got = tui_batch_ns(preset, str(folder), out_dir, values)
    assert got.batch == str(folder) and got.input is None and got.output_dir == out_dir
    assert vars(got) == vars(want)
```

No wizard, o preset 5 só pergunta "É um batch de pasta?" porque não há `input`/`batch` ainda (`_flow_advanced` 175); o "Pipeline Cineon (film look)?" do preset 5 não casa com a chave `"Usar film look"` do preset 3.

- [ ] **Step 2: Run** — `venv\Scripts\python.exe -m pytest ui/tui/test_parity_wizard.py -v` → 5 + 3 verdes. Se algum cenário batch divergir, **parar**: o relatório traz o diff dos dois `Namespace` e a causa; corrigir só `forms.py`/reducer para espelhar o wizard — nunca o teste nem o wizard.

- [ ] **Step 3: Commit**

```bash
git add ui/tui/test_parity_wizard.py
git commit -m "test(tui): paridade do batch da TUI com o wizard de linha (P3D)"
```

---

### Task 9: Verificação manual no Windows Terminal (Orquestrador + usuário)

- [ ] Orquestrador prepara o roteiro com uma pasta de teste curta (ex.: `C:\p3d\lote`) contendo 3 clipes curtos, 1 deles com a saída `_Hollywood_CRF18.mp4` já presente, e 1 arquivo de vídeo quebrado (ex.: `quebrado.mov` com bytes aleatórios); mais uma pasta vazia.
- [ ] Usuário roda `python -m ui.tui` e cobre: preset 3 até o REPORT (3 ok/1 pulado/1 falha, código 1, motivo resumido da falha); preset 5 → TIPO Pasta → pasta de saída separada (inexistente; o motor cria) até o REPORT; pasta vazia bloqueando no SOURCE ("⚠ nenhum vídeo encontrado"); `C` no meio da fila → modal "CANCELAR FILA?" → REPORT com `⚠ CANCELLED` e código 130; Ctrl+C no meio da fila → 130. Após cada: `$LASTEXITCODE`, `Get-Process ffmpeg -ErrorAction SilentlyContinue` (nada órfão), terminal normal, linha de resumo impressa.
- [ ] Orquestrador registra em `.claude/memory/VALIDATION.md`.

---

### Task 10: Fechamento (Orquestrador)

- [ ] Suíte canônica com `venv\Scripts\python.exe -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120` + `venv\Scripts\python.exe -m ruff check .`.
- [ ] STATE.md / FINDINGS.md / VALIDATION.md; merge/push só com pedido do usuário.

---

## Agente alvo

| ID | agente alvo | Task | arquivo(s) | aceite |
|----|-------------|------|------------|--------|
| P3D-1 | executor | Task 1 | `ui/probe.py`, `ui/test_probe.py` | timeout 10 s; ffprobe travado → `None` rápido |
| P3D-2 | executor | Task 2 | `ui/tui/forms.py` (+ 1 linha em `screens.py` e `app.py`), testes de forms/HOME/paridade | BATCH, `to_config`, presets 1–5 |
| P3D-3 | executor | Task 3 | `ui/tui/state.py`, `ui/tui/test_state_config.py` | SOURCE pasta, TIPO, `EMPTY`, campo de caminho, ESC sem ciclo |
| P3D-4 | executor | Task 4 | `ui/tui/state.py`, `ui/tui/test_state_batch.py` | fila, QUEUE/REPORT, `Finished` em batch |
| P3D-5 | executor | Task 5 | `ui/tui/screens.py`, `ui/tui/test_screens_config.py` | telas de pasta; ≤120 col; sem emoji |
| P3D-6 | executor | Task 6 | `ui/tui/screens.py`, `ui/tui/test_screens_batch.py` | QUEUE/REPORT, trilho, resumo |
| P3D-7 | executor-pesado | Task 7 | `ui/tui/app.py`, `ui/tui/test_app.py` | `run_batch`, revalidação, códigos 0/1/130, resumo |
| P3D-8 | executor | Task 8 | `ui/tui/test_parity_wizard.py` | 3 cenários batch com `Namespace` idêntico |
| P3D-9 | Orquestrador + usuário | Task 9 | roteiro | manual no Windows Terminal |
| P3D-10 | Orquestrador | Task 10 | `.claude/memory/*` | suíte + ruff |
