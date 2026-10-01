# B-4 Reporter Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao encoder um canal opcional de eventos (`reporter`) e um condutor headless para a TUI, sem mudar nada no CLI clássico.

**Architecture:** Funções do encoder ganham `reporter=None`; com `None` o caminho é o de hoje linha por linha. Com `QueueReporter`, o encoder não abre `Live`, emite eventos imutáveis numa `queue.Queue`, e um condutor em `ui/tui_driver.py` roda single-file e batch sobre `render_queue.run_job`, com cancelamento `C` e Ctrl+C preservando exit codes e limpeza atuais.

**Tech Stack:** Python ≥ 3.11, Rich, pytest + pytest-timeout, FFmpeg (`bin/ffmpeg.exe` local), PyAV/colour para Cineon.

**Spec:** `docs/superpowers/specs/2026-09-30-tui-reporter-seam-design.md` (ler inteiro antes de qualquer tarefa). Contexto: Sign-off da Phase 2 (§4 itens #7, #12–#15, #18; D-10, D-11, D-22).

## Global Constraints

- `reporter=None` ⇒ console e argv FFmpeg idênticos ao baseline (goldens da Task 2).
- Nenhuma mudança em: argv FFmpeg, pipes, threads de stderr, `_ACTIVE_FFMPEG`, `terminate_active_ffmpeg`, `discard_partial_output`, cleanup, exit codes, bloco batch de `main()` (`RE:4479–4590`), line wizard, `launcher.ps1`, `--help`.
- Exit codes: sucesso 0 · erro 1 · validação 2 · Ctrl+C/cancel 130 · batch sem vídeos 0 · batch com `falha` 1.
- D-11: Ctrl+C (inclusive no QC) apaga o output se ele não pré-existia (single) / sempre o do job corrente (batch).
- D-22 + D-11: `C` recusada nas etapas `ANALYZING·mctf_mask` e `QC`; Ctrl+C sempre ativo.
- Captura: remove marcação Rich e caracteres Unicode `So`, U+FE0E, U+FE0F, U+200D; descarta linhas vazias; restaura o console em `finally`.
- Python ≥ 3.11 (`pyproject.toml`); novos módulos com `from __future__ import annotations`.
- Suíte canônica: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Testes em `tmp_path`, nada na raiz.
- Não refatorar, não adicionar features, não escrever comentários narrativos (CLAUDE.md).

## Review Focus

1. **Cancel `C` antes de existir FFmpeg ativo** (ex.: durante `ANALYZING·preflight`): o usuário espera que o encode pare, não que o Pass 1 comece. → teste `test_cancel_before_ffmpeg_stops_at_next_stage` (Task 6).
2. **Ctrl+C durante QC na TUI**: master apagado, exit 130, igual ao clássico (D-11). → `test_ctrl_c_during_qc_deletes_new_master` (Task 6).
3. **Output pré-existente + Ctrl+C (single)**: arquivo antigo preservado. → `test_ctrl_c_keeps_preexisting_output` (Task 6).
4. **Exceção lançada pelo reporter numa thread de leitura de stderr** travaria o pipe: `FfmpegLine` nunca pode lançar. → `test_ffmpeg_line_never_raises_when_cancelled` (Task 1).
5. **Console capturado não restaurado após erro**: CLI posterior no mesmo processo sairia mudo. → `test_capture_restores_on_exception` (Task 5).

## File Structure

| arquivo | responsabilidade |
|---------|------------------|
| `reporter.py` (novo, raiz) | eventos imutáveis, `QueueReporter`, `CancelControl`, `CancelRequested`, nomes de etapa |
| `Reels_Encoder_v2_FINAL.py` (mod.) | `reporter=None` em `_run_encoding`, `run_ffmpeg`, `run_ffmpeg_with_cineon`, `_encode_single_file`; `on_line` em `ffmpeg_live_reader` |
| `ui/tui_capture.py` (novo) | `strip_symbols`, `ConsoleCapture` |
| `ui/tui_driver.py` (novo) | `run_single`, `run_batch` headless |
| `ui/test_reporter.py`, `enhance/test_classic_golden.py`, `enhance/golden/*.json`, `enhance/test_reporter_events.py`, `ui/test_tui_capture.py`, `ui/test_tui_driver.py`, `ui/test_tui_parity.py` (novos) | testes |

Refinamentos da spec feitos por este plano (aprovar junto): (a) etapa `ANALYZING·preflight` (enhance-ai, `RE:4044`) antes de `mctf_mask`; (b) `BETWEEN_PASSES·pass1_log` também no Cineon 2-pass; (c) `run_post_encode_qc` não recebe `reporter` — `_encode_single_file` emite `Stage QC` antes e `Qc` com o valor retornado; (d) `C` sem FFmpeg ativo aborta na próxima etapa via `CancelRequested`.

---

### Task 1: `reporter.py` — eventos, `QueueReporter`, `CancelControl`

**Files:**
- Create: `reporter.py`
- Test: `ui/test_reporter.py`

**Interfaces:**
- Produces:
  - Etapas: `PREPARING, PROBING, ANALYZING, PASS, BETWEEN_PASSES, FINALIZING, QC, DONE` (str) e `CANCEL_BLOCKED = {(ANALYZING, "mctf_mask"), (QC, None)}`.
  - Dataclasses `frozen=True`, todas com `job_id: int = 0`, `ts: float = 0.0` por último: `Stage(name, substep=None)`, `Hardware(fields: dict)`, `Probe(duration, total_frames, fps, width, height, is_hdr)`, `EncodeParams(vbv_key, target, maxrate, bufsize, vbv_init, x264_preset, mode)`, `Pass(index, total, label, phase)`, `Progress(frame, total, fps, speed, eta, elapsed)`, `FfmpegLine(line)`, `Info(text)`, `Qc(payload)`, `Done(output_path, seconds)`, `Error(kind, message, stderr_tail, returncode, traceback)`, `Cancel(phase, partial_removed=None)`, `QueueInit(jobs)`, `JobStart(index)`, `JobSkip(index, reason)`, `JobDone(index, status, error)`, `QueueDone(exit_code)`.
  - `class CancelRequested(Exception)`.
  - `class CancelControl(terminate: Callable[[], bool])` com `stage: tuple[str, str | None] | None`, `cancelled: bool` (property), `request_cancel() -> bool` (recusa se `stage in CANCEL_BLOCKED`), `force_cancel() -> None` (Ctrl+C: sem checar etapa, não chama terminate).
  - `class QueueReporter(events: queue.Queue, job_id: int = 0, control: CancelControl | None = None, progress_interval: float = 0.1)` com `emit(event) -> None`.

Regras de `emit`: preenche `job_id` e `ts=time.monotonic()` via `dataclasses.replace`; `Stage` atualiza `control.stage`; `Progress` é descartado se chegou < `progress_interval` s após o último `Progress` enviado, exceto quando `frame >= total`; depois de enfileirar, se `control.cancelled` e o evento é `Stage`, `Pass` ou `Progress`, lança `CancelRequested`. `FfmpegLine`/`Info` nunca lançam.

- [ ] **Step 0: Branch e baseline**

```bash
git switch -c claude/ciclo-p3a-reporter-seam
python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120
```
Registrar em STATE.md a contagem (passed/skipped) do baseline.

- [ ] **Step 1: Write the failing test** — `ui/test_reporter.py`

```python
import dataclasses
import queue

import pytest

import reporter as R


def _drain(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def test_events_are_frozen():
    ev = R.Stage(R.PASS, "1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.name = "X"


def test_emit_stamps_job_id_and_ts():
    q = queue.Queue()
    R.QueueReporter(q, job_id=3).emit(R.Info("oi"))
    (ev,) = _drain(q)
    assert ev.job_id == 3 and ev.ts > 0 and ev.text == "oi"


def test_progress_throttled_but_last_frame_passes(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(R.time, "monotonic", lambda: now[0])
    q = queue.Queue()
    rep = R.QueueReporter(q, progress_interval=0.1)
    rep.emit(R.Progress(1, 10, 1.0, 1.0, "x", 0.0))
    now[0] += 0.05
    rep.emit(R.Progress(2, 10, 1.0, 1.0, "x", 0.0))
    now[0] += 0.01
    rep.emit(R.Progress(10, 10, 1.0, 1.0, "x", 0.0))
    assert [e.frame for e in _drain(q)] == [1, 10]


def test_stage_updates_control_and_blocks_cancel():
    calls = []
    ctl = R.CancelControl(terminate=lambda: calls.append(1) or True)
    rep = R.QueueReporter(queue.Queue(), control=ctl)
    rep.emit(R.Stage(R.ANALYZING, "mctf_mask"))
    assert ctl.request_cancel() is False and calls == []
    rep.emit(R.Stage(R.QC))
    assert ctl.request_cancel() is False
    rep.emit(R.Stage(R.PASS, "1"))
    assert ctl.request_cancel() is True and calls == [1] and ctl.cancelled


def test_cancel_raises_on_next_stage_pass_progress():
    ctl = R.CancelControl(terminate=lambda: False)
    q = queue.Queue()
    rep = R.QueueReporter(q, control=ctl)
    rep.emit(R.Stage(R.ANALYZING, "preflight"))
    assert ctl.request_cancel() is True
    with pytest.raises(R.CancelRequested):
        rep.emit(R.Stage(R.PROBING))
    assert isinstance(_drain(q)[-1], R.Stage)


def test_ffmpeg_line_never_raises_when_cancelled():
    ctl = R.CancelControl(terminate=lambda: False)
    ctl.force_cancel()
    rep = R.QueueReporter(queue.Queue(), control=ctl)
    rep.emit(R.FfmpegLine("frame=1"))
    rep.emit(R.Info("x"))


def test_force_cancel_ignores_blocked_stage_and_does_not_terminate():
    calls = []
    ctl = R.CancelControl(terminate=lambda: calls.append(1) or True)
    ctl.stage = (R.QC, None)
    ctl.force_cancel()
    assert ctl.cancelled and calls == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ui/test_reporter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reporter'`.

- [ ] **Step 3: Implement** — `reporter.py`

```python
from __future__ import annotations

import dataclasses
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

PREPARING = "PREPARING"
PROBING = "PROBING"
ANALYZING = "ANALYZING"
PASS = "PASS"
BETWEEN_PASSES = "BETWEEN_PASSES"
FINALIZING = "FINALIZING"
QC = "QC"
DONE = "DONE"

CANCEL_BLOCKED = {(ANALYZING, "mctf_mask"), (QC, None)}


class CancelRequested(Exception):
    pass


@dataclass(frozen=True)
class Stage:
    name: str
    substep: str | None = None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Hardware:
    fields: dict
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Probe:
    duration: float
    total_frames: int
    fps: int
    width: int
    height: int
    is_hdr: bool
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class EncodeParams:
    vbv_key: str
    target: int
    maxrate: int
    bufsize: int
    vbv_init: float
    x264_preset: str
    mode: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Pass:
    index: int
    total: int
    label: str
    phase: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Progress:
    frame: int
    total: int
    fps: float
    speed: float
    eta: str
    elapsed: float
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class FfmpegLine:
    line: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Info:
    text: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Qc:
    payload: Any
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Done:
    output_path: str
    seconds: float
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Error:
    kind: str
    message: str
    stderr_tail: str | None
    returncode: int | None
    traceback: str | None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class Cancel:
    phase: str
    partial_removed: bool | None = None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class QueueInit:
    jobs: tuple
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobStart:
    index: int
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobSkip:
    index: int
    reason: str
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class JobDone:
    index: int
    status: str
    error: str | None
    job_id: int = 0
    ts: float = 0.0


@dataclass(frozen=True)
class QueueDone:
    exit_code: int
    job_id: int = 0
    ts: float = 0.0


class CancelControl:
    def __init__(self, terminate: Callable[[], bool]):
        self._terminate = terminate
        self._flag = threading.Event()
        self.stage: tuple[str, str | None] | None = None

    @property
    def cancelled(self) -> bool:
        return self._flag.is_set()

    def request_cancel(self) -> bool:
        if self.stage in CANCEL_BLOCKED:
            return False
        self._flag.set()
        self._terminate()
        return True

    def force_cancel(self) -> None:
        self._flag.set()


_CHECKPOINTS = (Stage, Pass, Progress)


class QueueReporter:
    def __init__(
        self,
        events: queue.Queue,
        job_id: int = 0,
        control: CancelControl | None = None,
        progress_interval: float = 0.1,
    ):
        self._events = events
        self._job_id = job_id
        self._control = control
        self._interval = progress_interval
        self._last_progress: float | None = None

    def emit(self, event) -> None:
        now = time.monotonic()
        if isinstance(event, Progress):
            last = self._last_progress
            if last is not None and now - last < self._interval and event.frame < event.total:
                return
            self._last_progress = now
        if isinstance(event, Stage) and self._control is not None:
            self._control.stage = (event.name, event.substep)
        self._events.put(dataclasses.replace(event, job_id=self._job_id, ts=now))
        if (
            self._control is not None
            and self._control.cancelled
            and isinstance(event, _CHECKPOINTS)
        ):
            raise CancelRequested()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ui/test_reporter.py -v` → Expected: 7 passed. Then `ruff check reporter.py ui/test_reporter.py`.

- [ ] **Step 5: Commit**

```bash
git add reporter.py ui/test_reporter.py
git commit -m "feat(reporter): eventos imutáveis, QueueReporter e CancelControl"
```

---

### Task 2: Goldens do caminho clássico (antes de tocar no encoder)

**Files:**
- Create: `enhance/test_classic_golden.py`, `enhance/golden/` (4 JSON gerados)

**Interfaces:**
- Produces: `enhance/test_classic_golden.py::run_classic(tmp_path, monkeypatch, scenario) -> dict` com chaves `argv` (lista normalizada) e `console` (lista de linhas normalizadas); reutilizada pela Task 8. Cenários: `native_crf`, `native_2pass`, `cineon_crf`, `cineon_2pass`.

- [ ] **Step 1: Write the test** — `enhance/test_classic_golden.py`

```python
import io
import json
import os
import re
import subprocess

import pytest
from rich.console import Console

import Reels_Encoder_v2_FINAL as RE
from ui.config import EncodeConfig

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
UPDATE = os.environ.get("REELS_UPDATE_GOLDEN") == "1"
SCENARIOS = {
    "native_crf": {"cineon_pipeline": "off", "mode": "crf"},
    "native_2pass": {"cineon_pipeline": "off", "mode": "2pass"},
    "cineon_crf": {"cineon_pipeline": "on", "mode": "crf"},
    "cineon_2pass": {"cineon_pipeline": "on", "mode": "2pass"},
}


def _runs(binary):
    try:
        return subprocess.run([binary, "-hide_banner", "-version"],
                              capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _fixed_hardware():
    hw = RE.HardwareProfile()
    hw.cpu_name, hw.cpu_cores, hw.cpu_threads, hw.cpu_freq_mhz = "GOLDEN CPU", 4, 8, 3000
    hw.cpu_arch, hw.os_name, hw.os_version = "x86_64", "GoldenOS", "1"
    hw.ram_total_gb, hw.ram_available_gb, hw.ram_percent_used = 16.0, 8.0, 50.0
    hw.tier, hw.perf_score = "medium", 50
    hw.recommended_threads, hw.recommended_preset = 1, "veryfast"
    hw.recommended_lookahead, hw.recommended_filter_threads = 10, 1
    hw.recommended_decoder_threads = 1
    return hw


def _source(tmp_path):
    src = str(tmp_path / "src.mp4")
    proc = subprocess.run(
        [RE.FFMPEG, "-hide_banner", "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=90x160:rate=30:duration=1",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-c:a", "aac", "-shortest", src],
        capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "ignore")[-800:]
    return src


def _norm_token(tok, tmp):
    s = str(tok).replace("\\", "/")
    for needle, label in ((tmp, "<TMP>"),
                          (os.path.dirname(os.path.abspath(RE.__file__)).replace("\\", "/"), "<REPO>"),
                          (str(RE.FFMPEG).replace("\\", "/"), "<FFMPEG>"),
                          (str(RE.FFPROBE).replace("\\", "/"), "<FFPROBE>")):
        s = s.replace(needle, label)
    return s


def _norm_argv(argv, tmp):
    out = [_norm_token(t, tmp) for t in argv]
    if out and out[-1] == RE.DEVNULL_FF:
        out[-1] = "<NULL>"
    return out


def _norm_line(line, tmp):
    s = _norm_token(line, tmp)
    s = re.sub(r"\d+(?:[.,]\d+)?", "N", s)
    return s.rstrip()


def run_classic(tmp_path, monkeypatch, scenario, reporter=None):
    if SCENARIOS[scenario]["cineon_pipeline"] == "on":
        pytest.importorskip("av")
        pytest.importorskip("colour")
    src = _source(tmp_path)
    out = str(tmp_path / f"{scenario}.mp4")
    calls = []
    real_popen, real_run = subprocess.Popen, subprocess.run

    def _popen(args, *a, **k):
        calls.append(list(args))
        return real_popen(args, *a, **k)

    def _run(args, *a, **k):
        if isinstance(args, (list, tuple)):
            calls.append(list(args))
        return real_run(args, *a, **k)

    buf = io.StringIO()
    cons = Console(file=buf, width=120, force_terminal=False, color_system=None,
                   legacy_windows=False)
    monkeypatch.setattr(subprocess, "Popen", _popen)
    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(RE, "console", cons)
    monkeypatch.setattr(RE, "detect_hardware", _fixed_hardware)
    ns = EncodeConfig(input=src, ebu_meter="off", report="off", enhance="off",
                      **SCENARIOS[scenario]).to_namespace()
    kwargs = {} if reporter is None else {"reporter": reporter}
    RE._encode_single_file(src, out, ns, **kwargs)
    tmp = str(tmp_path).replace("\\", "/")
    return {
        "argv": [_norm_argv(c, tmp) for c in calls],
        "console": [_norm_line(line, tmp) for line in buf.getvalue().splitlines()],
        "output": out,
    }


@pytest.fixture(autouse=True)
def _require_ffmpeg():
    if not (_runs(RE.FFMPEG) and _runs(RE.FFPROBE)):
        pytest.skip("ffmpeg/ffprobe indisponíveis")


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_classic_path_matches_golden(tmp_path, monkeypatch, scenario):
    got = run_classic(tmp_path, monkeypatch, scenario)
    got.pop("output")
    path = os.path.join(GOLDEN_DIR, f"classic_{scenario}.json")
    if UPDATE:
        os.makedirs(GOLDEN_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(got, fh, ensure_ascii=False, indent=1)
        pytest.skip("golden gravado")
    with open(path, encoding="utf-8") as fh:
        want = json.load(fh)
    assert got["argv"] == want["argv"]
    assert got["console"] == want["console"]
```

Se `EncodeConfig` rejeitar algum campo usado acima, conferir os nomes em `ui/config.py` e usar os existentes (sem criar campo); registrar em STATE.md.

- [ ] **Step 2: Gravar goldens no HEAD sem mudanças no encoder**

Run (PowerShell): `$env:REELS_UPDATE_GOLDEN='1'; python -m pytest enhance/test_classic_golden.py -v; Remove-Item Env:REELS_UPDATE_GOLDEN`
Expected: 4 skipped ("golden gravado"); arquivos `enhance/golden/classic_*.json` criados.

- [ ] **Step 3: Estabilidade** — rodar 3 vezes seguidas, sem a variável:

Run: `python -m pytest enhance/test_classic_golden.py -v` (repetir 3×)
Expected: 4 passed em todas. Se algum cenário oscilar entre execuções, **parar**: `blocked` com o diff (não afrouxar a normalização por conta própria).

- [ ] **Step 4: Commit**

```bash
git add enhance/test_classic_golden.py enhance/golden/classic_native_crf.json enhance/golden/classic_native_2pass.json enhance/golden/classic_cineon_crf.json enhance/golden/classic_cineon_2pass.json
git commit -m "test(golden): console e argv do caminho clássico antes do reporter"
```

---

### Task 3: Seam native — `_run_encoding`, `run_ffmpeg`, `_encode_single_file`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py` — `ffmpeg_live_reader` (`:793`), `_run_encoding` (`:2025`, bloco `:2054–2063`), `run_ffmpeg` (`:2487`; pontos `:2520`, `:2564`, `:2651`, `:2717`, `:2730`, `:2779`, `:2803`, `:2843`, `:2850`, `:2909`), `_encode_single_file` (`:4030`; pontos `:4044`, `:4068–4074`, `:4089`, `:4144–4159`)
- Test: `enhance/test_reporter_events.py`

**Interfaces:**
- Consumes: tudo de `reporter.py` (Task 1); `run_classic` (Task 2).
- Produces: `ffmpeg_live_reader(pipe, hud, sink=None, on_line=None)`; `_run_encoding(..., reporter=None)`; `run_ffmpeg(..., reporter=None)`; `_encode_single_file(input_file, output_file, args, is_batch=False, reporter=None)`; helpers `_emit(reporter, event)` e `_progress_from_hud(hud) -> reporter.Progress`.

- [ ] **Step 1: Write the failing test** — `enhance/test_reporter_events.py`

```python
import queue

import pytest

import reporter as R
from enhance.test_classic_golden import SCENARIOS, run_classic


def _events(tmp_path, monkeypatch, scenario):
    q = queue.Queue()
    run_classic(tmp_path, monkeypatch, scenario, reporter=R.QueueReporter(q))
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _stages(events):
    return [(e.name, e.substep) for e in events if isinstance(e, R.Stage)]


EXPECTED = {
    "native_crf": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.QC, None), (R.DONE, None)],
    "native_2pass": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.BETWEEN_PASSES, "pass1_log"), (R.PASS, "2"),
        (R.QC, None), (R.DONE, None)],
}


@pytest.mark.parametrize("scenario", ["native_crf", "native_2pass"])
def test_native_stage_order(tmp_path, monkeypatch, scenario):
    assert _stages(_events(tmp_path, monkeypatch, scenario)) == EXPECTED[scenario]


def test_native_2pass_payload_events(tmp_path, monkeypatch):
    ev = _events(tmp_path, monkeypatch, "native_2pass")
    kinds = [type(e).__name__ for e in ev]
    assert kinds.index("Hardware") < kinds.index("Probe") < kinds.index("EncodeParams")
    passes = [(e.index, e.total, e.label, e.phase) for e in ev if isinstance(e, R.Pass)]
    assert passes == [(1, 2, "Pass 1", "start"), (1, 2, "Pass 1", "end"),
                      (2, 2, "Pass 2", "start"), (2, 2, "Pass 2", "end")]
    probe = next(e for e in ev if isinstance(e, R.Probe))
    assert (probe.width, probe.height, probe.fps) == (90, 160, 30)
    params = next(e for e in ev if isinstance(e, R.EncodeParams))
    assert params.vbv_key == "ultra_short" and params.mode == "2pass"
    assert any(isinstance(e, R.Progress) for e in ev)
    assert any(isinstance(e, R.FfmpegLine) for e in ev)
    assert isinstance(ev[-1], R.Done)


def test_native_reporter_mode_prints_no_hud(tmp_path, monkeypatch):
    q = queue.Queue()
    got = run_classic(tmp_path, monkeypatch, "native_crf", reporter=R.QueueReporter(q))
    assert not any("ETA" in line for line in got["console"])
```

Nota: se a linha do HUD no golden não contiver "ETA", trocar a asserção pelo texto fixo do cabeçalho do HUD que aparece em `enhance/golden/classic_native_crf.json` (ler o arquivo; não inventar).

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest enhance/test_reporter_events.py -v`
Expected: FAIL — `TypeError: _encode_single_file() got an unexpected keyword argument 'reporter'`.

- [ ] **Step 3: Implement** — em `Reels_Encoder_v2_FINAL.py`

3a. Import perto dos outros imports de módulos locais:

```python
import reporter as _rep
```

3b. Helpers logo antes de `ffmpeg_live_reader`:

```python
def _emit(reporter, event) -> None:
    if reporter is not None:
        reporter.emit(event)


def _progress_from_hud(hud) -> "_rep.Progress":
    return _rep.Progress(
        frame=hud.current_frame, total=hud.total_frames, fps=hud.fps,
        speed=hud.speed, eta=hud.eta, elapsed=time.time() - hud.start_time,
    )
```

3c. `ffmpeg_live_reader`: assinatura `def ffmpeg_live_reader(pipe, hud: ResolveProgressHUD, sink=None, on_line=None):` e, logo após `sink.append(line)`:

```python
        if on_line is not None:
            on_line(line.rstrip())
```

3d. `_run_encoding`: acrescentar `reporter=None` ao fim da assinatura. Thread do reader:

```python
        _on_line = None if reporter is None else (lambda s: reporter.emit(_rep.FfmpegLine(s)))
        t = threading.Thread(
            target=ffmpeg_live_reader, args=(process.stderr, hud, stderr_tail, _on_line), daemon=True
        )
        t.start()
        if reporter is None:
            with Live(hud.render(), refresh_per_second=7, console=console) as live:
                while process.poll() is None:
                    time.sleep(0.1)
                    live.update(hud.render())
        else:
            while process.poll() is None:
                time.sleep(0.1)
                reporter.emit(_progress_from_hud(hud))
```

(o `finally` existente continua igual e mata o processo se `CancelRequested` subir.)

3e. `run_ffmpeg`: `reporter=None` no fim da assinatura; repassar `reporter=reporter` nas 3 chamadas de `_run_encoding` (`:2779`, `:2843`, `:2909`). Emissões (cada uma na mesma indentação da linha de referência):

- logo após `hw_profile = detect_hardware()` (`:2520`): `_emit(reporter, _rep.Hardware(dataclasses.asdict(hw_profile)))` (adicionar `import dataclasses` se ausente);
- imediatamente antes de `_probe = probe_video(input_file)` (`:2564`): `_emit(reporter, _rep.Stage(_rep.PROBING))`; imediatamente depois:

```python
    _emit(reporter, _rep.Probe(_probe.duration, _probe.nb_frames, _probe.fps_int,
                               _probe.width, _probe.height, _probe.is_hdr))
```

- imediatamente antes de `build_enhance_profile(` (`:2651`, dentro do mesmo `if`): `_emit(reporter, _rep.Stage(_rep.ANALYZING, "enhance"))`;
- logo após `vbv = get_vbv_preset(duration)` (`:2717`):

```python
    _emit(reporter, _rep.EncodeParams(
        next(k for k, v in VBV_PRESETS.items() if v is vbv),
        vbv["target"], vbv["maxrate"], vbv["bufsize"], vbv["vbv_init"],
        hw_profile.recommended_preset, mode))
```

- imediatamente antes de `analyze_audio_loudness(` (`:2730`, dentro do mesmo `if`): `_emit(reporter, _rep.Stage(_rep.ANALYZING, "loudness"))`;
- CRF (`:2779`): antes `_emit(reporter, _rep.Stage(_rep.PASS, "1")); _emit(reporter, _rep.Pass(1, 1, "Encode", "start"))`; depois `_emit(reporter, _rep.Pass(1, 1, "Encode", "end"))`;
- Pass 1 (`:2843`): antes `Stage(PASS, "1")` + `Pass(1, 2, "Pass 1", "start")`; depois `Pass(1, 2, "Pass 1", "end")`;
- antes de `_p1_stats = _analyze_pass1_log(logfile)` (`:2850`): `Stage(BETWEEN_PASSES, "pass1_log")`;
- Pass 2 (`:2909`): antes `Stage(PASS, "2")` + `Pass(2, 2, "Pass 2", "start")`; depois `Pass(2, 2, "Pass 2", "end")`.

Todas via `_emit(reporter, ...)`.

3f. `_encode_single_file`: assinatura `def _encode_single_file(input_file: str, output_file: str, args, is_batch: bool = False, reporter=None) -> None:`.
- Primeira linha do corpo após a docstring: `_emit(reporter, _rep.Stage(_rep.PREPARING))`.
- Antes de `try:` do preflight (`if enhance_ai and input_file:` `:4044`), dentro do `if`, antes do `try`: `_emit(reporter, _rep.Stage(_rep.ANALYZING, "preflight"))`.
- MCTF (`:4068`): dentro do `if`, antes do `try`: `_emit(reporter, _rep.Stage(_rep.ANALYZING, "mctf_mask"))`; trocar `show_progress=not is_batch` por `show_progress=not is_batch and reporter is None`.
- Repassar `reporter=reporter` para `run_ffmpeg(...)` (Task 4 fará o mesmo para `run_ffmpeg_with_cineon`).
- QC (`:4144`): antes do `try:` `_emit(reporter, _rep.Stage(_rep.QC))`; trocar `run_post_encode_qc(` por `_qc_payload = run_post_encode_qc(`; logo após o fechamento da chamada, ainda dentro do `try`: `_emit(reporter, _rep.Qc(_qc_payload))`.
- Após o bloco `try/except` do QC (fim da função):

```python
    _emit(reporter, _rep.Stage(_rep.DONE))
    _emit(reporter, _rep.Done(output_file, time.time() - _t0))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest enhance/test_reporter_events.py enhance/test_classic_golden.py -v`
Expected: eventos native passam; os 4 goldens continuam passando (prova de `reporter=None` idêntico). Depois a suíte canônica completa: mesma contagem do baseline + novos.

- [ ] **Step 5: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py enhance/test_reporter_events.py
git commit -m "feat(encoder): reporter opcional no caminho native (B-4)"
```

---

### Task 4: Seam Cineon — `run_ffmpeg_with_cineon` e `_render_pass`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py` — `run_ffmpeg_with_cineon` (`:3154`; pontos `:3208`, `:3248`, `:3326`, `:3342`, `:3421`, `:3510`, `:3597`, `:3613`, `:3674–3676`, `:3766`, `:3800`, `:3840`), `_encode_single_file` (chamada `:4090`)
- Test: `enhance/test_reporter_events.py` (acrescentar)

**Interfaces:**
- Consumes: `_emit`, `_progress_from_hud`, eventos (Tasks 1, 3).
- Produces: `run_ffmpeg_with_cineon(..., reporter=None)`.

- [ ] **Step 1: Write the failing test** — acrescentar a `enhance/test_reporter_events.py`:

```python
EXPECTED.update({
    "cineon_crf": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.FINALIZING, "remux"), (R.QC, None), (R.DONE, None)],
    "cineon_2pass": [
        (R.PREPARING, None), (R.PROBING, None), (R.ANALYZING, "loudness"),
        (R.PASS, "1"), (R.BETWEEN_PASSES, "pass1_log"), (R.PASS, "2"),
        (R.FINALIZING, "remux"), (R.QC, None), (R.DONE, None)],
})


@pytest.mark.parametrize("scenario", ["cineon_crf", "cineon_2pass"])
def test_cineon_stage_order(tmp_path, monkeypatch, scenario):
    assert _stages(_events(tmp_path, monkeypatch, scenario)) == EXPECTED[scenario]


def test_cineon_2pass_payload_events(tmp_path, monkeypatch):
    ev = _events(tmp_path, monkeypatch, "cineon_2pass")
    kinds = [type(e).__name__ for e in ev]
    assert kinds.index("Probe") < kinds.index("Hardware") < kinds.index("EncodeParams")
    passes = [(e.index, e.total, e.label, e.phase) for e in ev if isinstance(e, R.Pass)]
    assert passes == [(1, 2, "Pass 1", "start"), (1, 2, "Pass 1", "end"),
                      (2, 2, "Pass 2", "start"), (2, 2, "Pass 2", "end")]
    assert any(isinstance(e, R.Progress) for e in ev)
    assert isinstance(ev[-1], R.Done)
```

Antes de implementar, conferir no código: (a) `run_ffmpeg_with_cineon` chama `_analyze_pass1_log` no 2-pass; (b) o remux de `:3840` roda em CRF e 2-pass. Se qualquer um for falso, ajustar **apenas** a lista `EXPECTED` correspondente e registrar em STATE.md com a linha de evidência.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest enhance/test_reporter_events.py -k cineon -v`
Expected: FAIL — `TypeError: run_ffmpeg_with_cineon() got an unexpected keyword argument 'reporter'`.

- [ ] **Step 3: Implement**

- `reporter=None` no fim da assinatura de `run_ffmpeg_with_cineon`; `_encode_single_file` repassa `reporter=reporter` na chamada (`:4090`).
- Antes de `_probe = probe_video(input_file)` (`:3208`): `Stage(PROBING)`; depois: o mesmo `Probe(...)` da Task 3.
- Após `hw_profile = detect_hardware()` (`:3248`): `Hardware(dataclasses.asdict(hw_profile))`.
- Após `vbv = get_vbv_preset(duration)` (`:3326`): o mesmo `EncodeParams(...)` da Task 3 com `mode`.
- Antes de `loudness_stats = analyze_audio_loudness(` (`:3342`, mesmo `if`): `Stage(ANALYZING, "loudness")`.
- Antes de `build_enhance_profile(` (`:3421`, mesmo `if`): `Stage(ANALYZING, "enhance")`.
- Reader de stderr (`:3597`): repassar `on_line` à função alvo do thread com o mesmo padrão da Task 3 (`None` sem reporter). Se a função alvo não for `ffmpeg_live_reader`, acrescentar a ela o mesmo parâmetro `on_line=None` chamado com `line.rstrip()` para cada linha lida (decodificar como ela já decodifica).
- `Live` (`:3613`): substituir `with Live(hud.render(), refresh_per_second=7, console=console) as live:` por

```python
        _live_cm = (Live(hud.render(), refresh_per_second=7, console=console)
                    if reporter is None else contextlib.nullcontext())
        with _live_cm as live:
```

e `live.update(hud.render())` (`:3676`) por

```python
                    if reporter is None:
                        live.update(hud.render())
                    else:
                        reporter.emit(_progress_from_hud(hud))
```

(`import contextlib` se ausente.)
- Chamadas de passe: `:3766` → antes `Stage(PASS, "1")` + `Pass(1, 2, "Pass 1", "start")`, depois `Pass(1, 2, "Pass 1", "end")`; `:3800` → com `_lbl = "Pass 2" if mode == "2pass" else "Encode"`, `_idx, _tot = (2, 2) if mode == "2pass" else (1, 1)`: antes `Stage(PASS, str(_idx))` + `Pass(_idx, _tot, _lbl, "start")`, depois `Pass(_idx, _tot, _lbl, "end")`. Passar `_lbl` para `_render_pass` no lugar da expressão atual (mesmo valor).
- Antes do `_analyze_pass1_log` do Cineon: `Stage(BETWEEN_PASSES, "pass1_log")`.
- Primeira linha do bloco de remux (`:3840`, dentro da mesma condição que o executa): `Stage(FINALIZING, "remux")`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest enhance/test_reporter_events.py enhance/test_classic_golden.py -v` → todos passam; suíte canônica sem regressão.

- [ ] **Step 5: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py enhance/test_reporter_events.py
git commit -m "feat(encoder): reporter opcional no pipeline Cineon (B-4)"
```

---

### Task 5: Captura do console — `ui/tui_capture.py`

**Files:**
- Create: `ui/tui_capture.py`
- Test: `ui/test_tui_capture.py`

**Interfaces:**
- Consumes: `reporter.Info`.
- Produces: `strip_symbols(text: str) -> str`; `class ConsoleCapture(console, emit: Callable[[Info], None])` (context manager; troca `console.file` e `console.width`, restaura em `__exit__`).

- [ ] **Step 1: Write the failing test** — `ui/test_tui_capture.py`

```python
import io

import pytest
from rich.console import Console

import reporter as R
from ui.tui_capture import ConsoleCapture, strip_symbols


def test_strip_symbols_removes_emoji_and_graphics():
    assert strip_symbols("📊 Pass 1: Analisando complexidade...") == "Pass 1: Analisando complexidade..."
    assert strip_symbols("✓ LUT Portra 400 carregada") == "LUT Portra 400 carregada"
    assert strip_symbols("⚠️  MCTF falhou") == "MCTF falhou"
    assert strip_symbols("────────") == ""
    assert strip_symbols("x264 ▶ ref frames: 4 · keyint") == "x264 ref frames: 4 · keyint"


def _console():
    return Console(file=io.StringIO(), width=80, force_terminal=True)


def test_capture_emits_clean_info_lines():
    cons, got = _console(), []
    with ConsoleCapture(cons, got.append):
        cons.print("[yellow]Aviso: ffprobe falhou, usando duração padrão 30s[/yellow]")
        cons.rule()
        cons.print("🎬 Pass 2: Encoding final...")
    assert [e.text for e in got] == [
        "Aviso: ffprobe falhou, usando duração padrão 30s",
        "Pass 2: Encoding final...",
    ]
    assert all(isinstance(e, R.Info) for e in got)


def test_capture_restores_on_exception():
    cons = _console()
    orig_file, orig_width = cons.file, cons.width
    with pytest.raises(RuntimeError):
        with ConsoleCapture(cons, lambda e: None):
            raise RuntimeError("boom")
    assert cons.file is orig_file and cons.width == orig_width


def test_capture_does_not_write_to_original_file():
    cons = _console()
    with ConsoleCapture(cons, lambda e: None):
        cons.print("nada na tela")
    assert cons.file.getvalue() == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ui/test_tui_capture.py -v` → FAIL (`ModuleNotFoundError: ui.tui_capture`).

- [ ] **Step 3: Implement** — `ui/tui_capture.py`

```python
from __future__ import annotations

import re
import threading
import unicodedata
from typing import Callable

import reporter as R

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_DROP = {"︎", "️", "‍"}


def strip_symbols(text: str) -> str:
    kept = "".join(
        ch for ch in _ANSI.sub("", text)
        if ch not in _DROP and unicodedata.category(ch) != "So"
    )
    return " ".join(kept.split())


class _Sink:
    def __init__(self, emit: Callable[[R.Info], None]):
        self._emit = emit
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._lock:
            self._buf += text
            *lines, self._buf = self._buf.split("\n")
        for line in lines:
            clean = strip_symbols(line)
            if clean:
                self._emit(R.Info(clean))
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False


class ConsoleCapture:
    def __init__(self, console, emit: Callable[[R.Info], None], width: int = 1000):
        self._console = console
        self._emit = emit
        self._width = width

    def __enter__(self) -> "ConsoleCapture":
        self._orig_file = self._console.file
        self._orig_width = self._console.width
        self._console.file = _Sink(self._emit)
        self._console.width = self._width
        return self

    def __exit__(self, *exc) -> None:
        self._console.file = self._orig_file
        self._console.width = self._orig_width
```

Nota: `test_capture_emits_clean_info_lines` usa `force_terminal=True` de propósito — prova que a limpeza por regex de ANSI funciona mesmo se o console tema forçar terminal.

- [ ] **Step 4: Run** — `python -m pytest ui/test_tui_capture.py -v` → 5 passed; `ruff check ui/tui_capture.py ui/test_tui_capture.py`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui_capture.py ui/test_tui_capture.py
git commit -m "feat(ui): captura do console para o LOG da TUI sem emoji (B-4)"
```

---

### Task 6: Condutor single-file — `ui/tui_driver.run_single`

**Files:**
- Create: `ui/tui_driver.py`
- Test: `ui/test_tui_driver.py`

**Interfaces:**
- Consumes: `reporter` (Task 1); `RE._encode_single_file(..., reporter=)` (Tasks 3–4); `RE.terminate_active_ffmpeg`, `RE._validate_args_consistency`; `render_queue.QueueJob`, `render_queue.run_job(job, encode_fn, console, on_tick=None)`, `render_queue.discard_partial_output(job) -> bool`.
- Produces: `WORKER_WAIT_S = 30.0`; `run_single(ns, events: queue.Queue, control: CancelControl, on_tick: Callable[[], None]) -> int`; helper `_run_one(job, ns, events, control, on_tick, job_id, is_batch) -> str` (retorna `"ok" | "falha" | "cancelado"`; lança `KeyboardInterrupt` se o Ctrl+C chegou), reutilizado pela Task 7.

Comportamento de `run_single`:
1. `err = RE._validate_args_consistency(ns)`; se `err`: emite `Error("validation", err, None, None, None)` e retorna 2.
2. `output_preexisted = os.path.exists(output_path)` com `output_path = EncodeConfig`-equivalente: usar o mesmo cálculo de output do caminho single de `main()` (`RE:4595–4612`) — copiar a expressão exatamente, sem reescrever.
3. `_run_one(...)`:
   - `worker_done = threading.Event()`; `state = {}`.
   - `encode_fn` chama `RE._encode_single_file(inp, out, ns, is_batch=is_batch, reporter=QueueReporter(events, job_id, control))`; `except CancelRequested` → `raise RuntimeError("cancelado pelo usuário")`; `except Exception` → guarda `state["exc"]`, `state["tb"] = traceback.format_exc()`, relança; `finally: worker_done.set()`.
   - `render_queue.run_job(job, encode_fn, RE.console, on_tick=on_tick)`.
   - Após retorno: se `control.cancelled` → `"cancelado"`; se `job.status == "falha"` → emite `Error(type(exc).__name__, str(exc), getattr(exc, "stderr", None), getattr(exc, "returncode", None), tb)` e retorna `"falha"`; senão `"ok"`.
   - `except KeyboardInterrupt`: `control.force_cancel()`; `RE.terminate_active_ffmpeg()`; `worker_done.wait(WORKER_WAIT_S)`; relança.
4. Resultado: `"ok"` → 0; `"falha"` → 1; `"cancelado"` ou `KeyboardInterrupt` → emite `Cancel("terminated")`, se `not output_preexisted`: `removed = render_queue.discard_partial_output(job)`, emite `Cancel("cleaned", removed)`; retorna 130.

- [ ] **Step 1: Write the failing test** — `ui/test_tui_driver.py`

```python
import os
import queue
import threading

import pytest

import render_queue
import reporter as R
import Reels_Encoder_v2_FINAL as RE
from ui import tui_driver as D
from ui.config import EncodeConfig


@pytest.fixture
def ns(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    return EncodeConfig(input=str(src), ebu_meter="off", report="off").to_namespace()


def _out(ns):
    return D._single_output_path(ns)


def _drain(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _ctl(calls=None):
    return R.CancelControl(terminate=lambda: (calls.append(1) if calls is not None else None) or True)


def _fake_encode(monkeypatch, body):
    def fake(inp, out, args, is_batch=False, reporter=None):
        body(inp, out, reporter)
    monkeypatch.setattr(RE, "_encode_single_file", fake)


def test_success_returns_0(ns, monkeypatch):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PASS, "1"))
        open(out, "wb").close()
        rep.emit(R.Done(out, 0.1))
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 0
    assert isinstance(_drain(q)[-1], R.Done)


def test_error_returns_1_with_traceback(ns, monkeypatch):
    def body(inp, out, rep):
        raise ValueError("falhou")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    err = next(e for e in _drain(q) if isinstance(e, R.Error))
    assert err.kind == "ValueError" and "falhou" in err.traceback


def test_validation_error_returns_2(ns, monkeypatch):
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda a: "combinação inválida")
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 2
    assert _drain(q)[-1].kind == "validation"


def test_cancel_before_ffmpeg_stops_at_next_stage(ns, monkeypatch):
    ctl = _ctl()
    started = []

    def body(inp, out, rep):
        rep.emit(R.Stage(R.ANALYZING, "preflight"))
        assert ctl.request_cancel()
        rep.emit(R.Stage(R.PROBING))
        started.append("pass1")
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), ctl, on_tick=lambda: None) == 130
    assert started == []


def test_cancel_refused_during_mctf_and_qc(ns, monkeypatch):
    ctl = _ctl()
    answers = []

    def body(inp, out, rep):
        rep.emit(R.Stage(R.ANALYZING, "mctf_mask"))
        answers.append(ctl.request_cancel())
        rep.emit(R.Stage(R.QC))
        answers.append(ctl.request_cancel())
        open(out, "wb").close()
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), ctl, on_tick=lambda: None) == 0
    assert answers == [False, False]


def _ctrl_c_on_first_tick():
    fired = []

    def tick():
        if not fired:
            fired.append(1)
            raise KeyboardInterrupt
    return tick


def test_ctrl_c_during_qc_deletes_new_master(ns, monkeypatch):
    in_qc = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        rep.emit(R.Stage(R.QC))
        in_qc.set()
        release.wait(5)

    _fake_encode(monkeypatch, body)
    terminated = []
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: terminated.append(1) or False)

    def tick():
        if in_qc.is_set() and not terminated:
            release.set()
            raise KeyboardInterrupt

    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=tick) == 130
    assert not os.path.exists(_out(ns))
    assert any(isinstance(e, R.Cancel) and e.phase == "cleaned" and e.partial_removed for e in _drain(q))


def test_ctrl_c_keeps_preexisting_output(ns, monkeypatch):
    out = _out(ns)
    with open(out, "wb") as fh:
        fh.write(b"old")
    release = threading.Event()

    def body(inp, o, rep):
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    assert D.run_single(ns, queue.Queue(), _ctl(), on_tick=_ctrl_c_on_first_tick()) == 130
    with open(out, "rb") as fh:
        assert fh.read() == b"old"
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/test_tui_driver.py -v` → FAIL (`ModuleNotFoundError: ui.tui_driver`).

- [ ] **Step 3: Implement** — `ui/tui_driver.py`

```python
from __future__ import annotations

import os
import queue
import threading
import traceback
from typing import Callable

import render_queue
import reporter as R
import Reels_Encoder_v2_FINAL as RE

WORKER_WAIT_S = 30.0


def _single_output_path(ns) -> str:
    raise NotImplementedError  # substituído no Step 3b


def _run_one(job, ns, events, control, on_tick, job_id, is_batch) -> str:
    worker_done = threading.Event()
    state: dict = {}
    rep = R.QueueReporter(events, job_id=job_id, control=control)

    def encode_fn() -> None:
        try:
            RE._encode_single_file(job.input_path, job.output_path, ns,
                                   is_batch=is_batch, reporter=rep)
        except R.CancelRequested:
            raise RuntimeError("cancelado pelo usuário") from None
        except Exception as exc:
            state["exc"] = exc
            state["tb"] = traceback.format_exc()
            raise
        finally:
            worker_done.set()

    try:
        render_queue.run_job(job, encode_fn, RE.console, on_tick=on_tick)
    except KeyboardInterrupt:
        control.force_cancel()
        RE.terminate_active_ffmpeg()
        worker_done.wait(WORKER_WAIT_S)
        raise
    worker_done.wait(WORKER_WAIT_S)
    if control.cancelled:
        return "cancelado"
    if job.status == "falha":
        exc = state.get("exc")
        events.put(R.Error(
            type(exc).__name__ if exc else "Exception",
            str(exc) if exc else (job.error or ""),
            getattr(exc, "stderr", None), getattr(exc, "returncode", None),
            state.get("tb"), job_id=job_id))
        return "falha"
    return "ok"


def _cancel_cleanup(job, events, remove_partial: bool, job_id: int) -> None:
    events.put(R.Cancel("terminated", job_id=job_id))
    if remove_partial:
        removed = render_queue.discard_partial_output(job)
        events.put(R.Cancel("cleaned", removed, job_id=job_id))


def run_single(ns, events: queue.Queue, control: R.CancelControl,
               on_tick: Callable[[], None]) -> int:
    err = RE._validate_args_consistency(ns)
    if err:
        events.put(R.Error("validation", err, None, None, None))
        return 2
    out = _single_output_path(ns)
    job = render_queue.QueueJob(input_path=ns.input, output_path=out)
    output_preexisted = os.path.exists(out)
    try:
        result = _run_one(job, ns, events, control, on_tick, 0, is_batch=False)
    except KeyboardInterrupt:
        result = "cancelado"
    if result == "ok":
        return 0
    if result == "falha":
        return 1
    _cancel_cleanup(job, events, remove_partial=not output_preexisted, job_id=0)
    return 130
```

- [ ] **Step 3b: `_single_output_path`** — ler `RE:4592–4613` (branch single de `main()`) e substituir o `raise NotImplementedError` pela **mesma** expressão que `main()` usa para `output_file` a partir de `args`, lendo de `ns` os mesmos atributos. Não reescrever a regra; se ela depender de variáveis locais de `main()`, copiar as linhas que as calculam. Adicionar a `ui/test_tui_driver.py`:

```python
def _call_main(monkeypatch, ns):
    monkeypatch.setattr(RE, "missing_ffmpeg_binaries", lambda *a, **k: [], raising=False)
    monkeypatch.setattr(RE, "parse_cli", lambda *a, **k: ns, raising=False)
    try:
        RE.main()
    except SystemExit:
        pass


def test_single_output_path_matches_main(ns, monkeypatch):
    seen = {}
    monkeypatch.setattr(RE, "_encode_single_file",
                        lambda i, o, a, is_batch=False, reporter=None: seen.setdefault("out", o))
    _call_main(monkeypatch, ns)
    assert D._single_output_path(ns) == seen["out"]
```

(Sucesso single-file em `main()` retorna sem `sys.exit`; por isso `_call_main` aceita os dois.)

Se `main()` não usar `parse_cli` ou o preflight de binários tiver outro nome, ajustar os `monkeypatch` para os nomes reais lidos em `RE:4422–4460` (só os monkeypatch; a asserção fica).

- [ ] **Step 4: Run** — `python -m pytest ui/test_tui_driver.py -v` → todos passam; suíte canônica; `ruff check ui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui_driver.py ui/test_tui_driver.py
git commit -m "feat(ui): condutor headless single-file com cancel C e Ctrl+C (B-4)"
```

---

### Task 7: Condutor batch — `ui/tui_driver.run_batch`

**Files:**
- Modify: `ui/tui_driver.py`
- Test: `ui/test_tui_driver.py` (acrescentar)

**Interfaces:**
- Consumes: `_run_one`, `_cancel_cleanup` (Task 6); `RE.find_video_files(folder) -> list`.
- Produces: `_batch_jobs(ns) -> tuple[str, list[render_queue.QueueJob]]` (pasta de saída, jobs); `run_batch(ns, events, control, on_tick) -> int`.

Comportamento (espelha `RE:4479–4590`; D-11, D-18):
1. Validação como `run_single` (→ 2).
2. Pasta inexistente → `Error("batch_folder", ...)`, retorna 1. `find_video_files` vazio → `Info("Nenhum vídeo encontrado em: <pasta>")`, `QueueDone(0)`, retorna 0.
3. `_batch_jobs`: copiar de `RE:4479–4521` o cálculo de `output_folder` e a regra de nome (`_Cineon_Film.mp4` / `_Hollywood_CRF18.mp4` / `_Hollywood_2Pass.mp4`) sem reescrever.
4. `QueueInit(tuple((j.input_path, j.output_path) for j in jobs))`. Para cada índice `i`: se `os.path.exists(job.output_path)` → `job.status = "pulado"`, `JobSkip(i, "output existe")`; senão `JobStart(i)`, `result = _run_one(job, ns, events, control, on_tick, job_id=i, is_batch=True)`, `JobDone(i, job.status, job.error)`; `result == "cancelado"` (tecla `C`) → `_cancel_cleanup(job, events, True, i)`, `QueueDone(130)`, retorna 130.
5. `KeyboardInterrupt` → `_cancel_cleanup(job_corrente, events, True, i)`, `QueueDone(130)`, retorna 130.
6. Fim: `code = 1 if any(j.status == "falha" for j in jobs) else 0`; `QueueDone(code)`; retorna `code`.

- [ ] **Step 1: Write the failing test** — acrescentar:

```python
@pytest.fixture
def batch_ns(tmp_path):
    folder = tmp_path / "lote"
    folder.mkdir()
    for n in ("a.mp4", "b.mp4"):
        (folder / n).write_bytes(b"x")
    return EncodeConfig(batch=str(folder), ebu_meter="off", report="off").to_namespace()


def test_batch_zero_videos_returns_0(tmp_path):
    folder = tmp_path / "vazio"
    folder.mkdir()
    ns = EncodeConfig(batch=str(folder), ebu_meter="off", report="off").to_namespace()
    q = queue.Queue()
    assert D.run_batch(ns, q, _ctl(), on_tick=lambda: None) == 0
    assert _drain(q)[-1].exit_code == 0


def test_batch_jobs_match_classic_main(batch_ns, monkeypatch):
    seen = []
    monkeypatch.setattr(RE, "_encode_single_file",
                        lambda i, o, a, is_batch=False, reporter=None: seen.append((i, o)))
    _call_main(monkeypatch, batch_ns)
    _, jobs = D._batch_jobs(batch_ns)
    assert [(j.input_path, j.output_path) for j in jobs] == seen


def test_batch_skip_fail_and_exit_1(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)
    open(jobs[0].output_path, "wb").close()

    def body(inp, out, rep):
        raise ValueError("x")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 1
    ev = _drain(q)
    assert any(isinstance(e, R.JobSkip) and e.index == 0 for e in ev)
    assert any(isinstance(e, R.JobDone) and e.index == 1 and e.status == "falha" for e in ev)


def test_batch_all_ok_returns_0(batch_ns, monkeypatch):
    _fake_encode(monkeypatch, lambda inp, out, rep: open(out, "wb").close())
    assert D.run_batch(batch_ns, queue.Queue(), _ctl(), on_tick=lambda: None) == 0


def test_batch_ctrl_c_discards_current_even_if_complete(batch_ns, monkeypatch):
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    _, jobs = D._batch_jobs(batch_ns)
    assert D.run_batch(batch_ns, queue.Queue(), _ctl(), on_tick=_ctrl_c_on_first_tick()) == 130
    assert not os.path.exists(jobs[0].output_path)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest ui/test_tui_driver.py -k batch -v` → FAIL (`AttributeError: run_batch`).

- [ ] **Step 3: Implement** — acrescentar a `ui/tui_driver.py`:

```python
def _batch_jobs(ns) -> tuple[str, list]:
    raise NotImplementedError  # substituído no Step 3b


def run_batch(ns, events: queue.Queue, control: R.CancelControl,
              on_tick: Callable[[], None]) -> int:
    err = RE._validate_args_consistency(ns)
    if err:
        events.put(R.Error("validation", err, None, None, None))
        return 2
    folder = ns.batch
    if not os.path.isdir(folder):
        events.put(R.Error("batch_folder", f"Pasta não encontrada: {folder}", None, None, None))
        return 1
    if not RE.find_video_files(folder):
        events.put(R.Info(f"Nenhum vídeo encontrado em: {folder}"))
        events.put(R.QueueDone(0))
        return 0
    _, jobs = _batch_jobs(ns)
    events.put(R.QueueInit(tuple((j.input_path, j.output_path) for j in jobs)))
    current = None
    try:
        for i, job in enumerate(jobs):
            current = (i, job)
            if os.path.exists(job.output_path):
                job.status = "pulado"
                events.put(R.JobSkip(i, "output existe", job_id=i))
                continue
            events.put(R.JobStart(i, job_id=i))
            result = _run_one(job, ns, events, control, on_tick, job_id=i, is_batch=True)
            events.put(R.JobDone(i, job.status, job.error, job_id=i))
            if result == "cancelado":
                _cancel_cleanup(job, events, True, i)
                events.put(R.QueueDone(130))
                return 130
    except KeyboardInterrupt:
        i, job = current
        _cancel_cleanup(job, events, True, i)
        events.put(R.QueueDone(130))
        return 130
    code = 1 if any(j.status == "falha" for j in jobs) else 0
    events.put(R.QueueDone(code))
    return code
```

- [ ] **Step 3b: `_batch_jobs`** — ler `RE:4479–4521` e implementar copiando o cálculo de `output_folder` (incluindo `args.output_dir`) e o loop de montagem de `jobs` (citado no Sign-off §4 #3 / spec §8). Retornar `(output_folder, jobs)`.

- [ ] **Step 4: Run** — `python -m pytest ui/test_tui_driver.py -v` → todos passam; suíte canônica; `ruff check ui/`.

- [ ] **Step 5: Commit**

```bash
git add ui/tui_driver.py ui/test_tui_driver.py
git commit -m "feat(ui): condutor headless de batch com verdict por job (B-4)"
```

---

### Task 8: Paridade clássico × condutor

**Files:**
- Create: `ui/test_tui_parity.py`

**Interfaces:**
- Consumes: `run_classic` (Task 2), `run_single` (Task 6).

- [ ] **Step 1: Write the test**

```python
import hashlib
import queue

import pytest

import reporter as R
from enhance.test_classic_golden import SCENARIOS, run_classic


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_reporter_path_matches_classic_argv_and_output(tmp_path, monkeypatch, scenario):
    (tmp_path / "c").mkdir()
    (tmp_path / "t").mkdir()
    classic = run_classic(tmp_path / "c", monkeypatch, scenario)
    tui = run_classic(tmp_path / "t", monkeypatch, scenario,
                      reporter=R.QueueReporter(queue.Queue()))
    assert tui["argv"] == classic["argv"]
    assert _sha(tui["output"]) == _sha(classic["output"])
```

(`run_classic` fixa `recommended_threads=1` via `_fixed_hardware`, o que torna o hash determinístico.)

- [ ] **Step 2: Run** — `python -m pytest ui/test_tui_parity.py -v` → 4 passed (Cineon pula sem `av`/`colour`).

- [ ] **Step 3: Commit**

```bash
git add ui/test_tui_parity.py
git commit -m "test(parity): caminho com reporter gera mesmo argv e mesmo arquivo (B-4)"
```

---

### Task 9: Verificação manual no Windows Terminal (usuário)

**Files:**
- Create (scratchpad, fora do repo): `<SCRATCH>\b4\b4_driver_probe.py` e `<SCRATCH>\b4\B4_ROTEIRO.md`, onde `<SCRATCH>` = scratchpad da sessão do Orquestrador.

- [ ] **Step 1:** Script que monta `EncodeConfig(input=<arquivo real do usuário>, ...)`, cria `queue`, `CancelControl(terminate=RE.terminate_active_ffmpeg)`, entra em `ConsoleCapture(RE.console, q.put)`, inicia thread de teclado (`msvcrt.getwch`; `c` → `control.request_cancel()`, registrando o retorno), roda `run_single` com `on_tick` que esvazia a fila num `rich.Live` próprio (etapa atual, última linha de progresso, últimas 5 linhas de LOG) e grava todos os eventos em `b4_<hhmmss>.log`; `sys.exit(<código retornado>)`.
- [ ] **Step 2:** Roteiro T1–T5 como no B-3 (Ctrl+C no Pass 1; `c` no Pass 1; `c` durante `mctf_mask` com `--mctf on` → recusado; Ctrl+C durante QC → master apagado; Ctrl+C ×2). Anotar exit code, `ffmpeg.exe` órfão, terminal utilizável, conteúdo do log.
- [ ] **Step 3:** Usuário roda e devolve; Orquestrador registra em VALIDATION.md.

---

### Task 10: Fechamento (Orquestrador)

- [ ] Suíte canônica completa + `ruff check .`; comparar com o baseline da Task 1 Step 0.
- [ ] STATE.md / FINDINGS.md atualizados; Sign-off: B-4 → CLOSED; status `PHASE 3 READY` somente após aprovação explícita do usuário.
- [ ] Push da branch e PR (só com pedido do usuário).
