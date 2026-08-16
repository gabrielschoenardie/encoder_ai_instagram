# Render Queue Profissional (Batch de Verdade) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o loop sequencial do `--batch` (`Reels_Encoder_v2_FINAL.py`) por uma fila com progresso global visível durante a execução: "job N de M", ETA total, tabela de status ao vivo por arquivo (aguardando/processando/ok/falha/pulado), e relatório final consolidado.

**Architecture:** Novo módulo `render_queue.py` (raiz do projeto) com um dataclass de estado (`QueueJob`) e quatro funções puras/orquestradoras (`estimate_eta`, `build_table`, `run_job`, `render_final_report`). O loop de controle em `Reels_Encoder_v2_FINAL.py` continua no mesmo lugar, mas passa a construir a lista de jobs, rodar cada um dentro de um `rich.live.Live`, e delegar renderização/captura de log ao módulo novo.

**Tech Stack:** Python 3.11+, `rich` (já é dependência do projeto — `Live`, `Table`, `Console.capture()`), `pytest`.

**Spec:** `docs/superpowers/specs/2026-08-16-render-queue-design.md`

## Global Constraints

- Sem nova dependência — só `rich`, já usado no projeto (Console/Live/Table já importados em `Reels_Encoder_v2_FINAL.py:94-98`).
- Sem paralelismo — a fila continua processando um arquivo por vez; só a visualização muda.
- Sem abstração `Queue`/`Job` reutilizável — único ponto de uso é o `--batch` da CLI hoje.
- Comportamento preservado: skip-se-já-existe continua checado antes de rodar o job; `KeyboardInterrupt` continua abortando a fila inteira; uma falha isolada não aborta o resto da fila.
- Log capturado por job truncado para os últimos 4000 caracteres se ultrapassar esse tamanho (a exceção real geralmente vem no fim do output).

---

### Task 1: `render_queue.py` — estado, ETA, tabela, execução de job, relatório final

**Files:**
- Create: `render_queue.py`
- Test: `test_render_queue.py`

**Interfaces:**
- Produces:
  - `QueueJob` — dataclass com `input_path: str`, `output_path: str`, `status: str = "aguardando"` (`"aguardando" | "processando" | "ok" | "falha" | "pulado"`), `started_at: float | None = None`, `finished_at: float | None = None`, `error: str | None = None`, `log: str = ""`
  - `format_duration(seconds: float) -> str` — `"MM:SS"`
  - `format_eta(eta_seconds: float | None) -> str` — `"--:--"` se `None`, senão `format_duration`
  - `estimate_eta(jobs: list[QueueJob], remaining: int) -> float | None`
  - `build_table(jobs: list[QueueJob], eta_seconds: float | None = None, title: str | None = None) -> rich.table.Table`
  - `run_job(job: QueueJob, encode_fn: Callable[[], None], console: rich.console.Console) -> None`
  - `render_final_report(jobs: list[QueueJob], console: rich.console.Console) -> None`

- [ ] **Step 1: Escrever `test_render_queue.py` completo**

```python
import io

import pytest
from rich.console import Console

from render_queue import (
    QueueJob,
    build_table,
    estimate_eta,
    format_duration,
    format_eta,
    render_final_report,
    run_job,
)


def _finished_job(duration_seconds, status="ok", input_path="job.mp4"):
    job = QueueJob(input_path=input_path, output_path=input_path + ".out")
    job.status = status
    job.started_at = 100.0
    job.finished_at = 100.0 + duration_seconds
    return job


def test_estimate_eta_returns_none_with_no_finished_jobs():
    jobs = [QueueJob(input_path="a.mp4", output_path="a_out.mp4")]
    assert estimate_eta(jobs, remaining=3) is None


def test_estimate_eta_uses_mean_of_finished_durations():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    assert estimate_eta(jobs, remaining=2) == pytest.approx(30.0)


def test_estimate_eta_ignores_skipped_and_pending_jobs():
    jobs = [
        _finished_job(10.0),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4", status="pulado"),
        QueueJob(input_path="c.mp4", output_path="c_out.mp4"),
    ]
    assert estimate_eta(jobs, remaining=1) == pytest.approx(10.0)


def test_format_duration_formats_minutes_and_seconds():
    assert format_duration(75) == "01:15"


def test_format_eta_none_is_placeholder():
    assert format_eta(None) == "--:--"


def test_format_eta_formats_seconds():
    assert format_eta(65) == "01:05"


def test_build_table_title_shows_job_count_and_eta():
    jobs = [
        _finished_job(12.0, input_path="a.mp4"),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4"),
    ]
    table = build_table(jobs, eta_seconds=30.0)
    assert "Job 1 de 2" in table.title
    assert "00:30" in table.title


def test_build_table_lists_every_job_with_its_status_symbol():
    jobs = [
        QueueJob(input_path="a.mp4", output_path="a_out.mp4", status="aguardando"),
        QueueJob(input_path="b.mp4", output_path="b_out.mp4", status="processando"),
        _finished_job(12.0, input_path="c.mp4", status="ok"),
        _finished_job(5.0, input_path="d.mp4", status="falha"),
        QueueJob(input_path="e.mp4", output_path="e_out.mp4", status="pulado"),
    ]
    table = build_table(jobs, eta_seconds=None)

    output = io.StringIO()
    console = Console(file=output, width=120)
    console.print(table)
    text = output.getvalue()

    for job in jobs:
        assert job.input_path in text
    for symbol in ["·", "⏳", "✓", "✗", "○"]:
        assert symbol in text


def test_run_job_marks_success_and_leaves_log_empty():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())

    def encode_fn():
        console.print("trabalhando...")

    run_job(job, encode_fn, console)

    assert job.status == "ok"
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.finished_at >= job.started_at
    assert job.log == ""
    assert job.error is None


def test_run_job_marks_failure_and_captures_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())

    def encode_fn():
        console.print("preparando encode...")
        raise RuntimeError("ffmpeg explodiu")

    run_job(job, encode_fn, console)

    assert job.status == "falha"
    assert job.error == "ffmpeg explodiu"
    assert "preparando encode..." in job.log


def test_render_final_report_lists_failure_with_captured_log():
    output = io.StringIO()
    console = Console(file=output, width=100)

    ok_job = _finished_job(3.0, input_path="ok.mp4", status="ok")
    failed_job = _finished_job(1.0, input_path="falhou.mp4", status="falha")
    failed_job.error = "ffmpeg explodiu"
    failed_job.log = "preparando encode...\nffmpeg explodiu"

    render_final_report([ok_job, failed_job], console)

    text = output.getvalue()
    assert "1/2" in text
    assert "ffmpeg explodiu" in text
    assert "preparando encode..." in text


def test_render_final_report_truncates_long_logs_keeping_the_tail():
    output = io.StringIO()
    console = Console(file=output, width=200)

    failed_job = _finished_job(1.0, input_path="falhou.mp4", status="falha")
    failed_job.error = "erro"
    failed_job.log = "HEAD-MARKER" + ("y" * 4990) + "TAIL-MARKER"

    render_final_report([failed_job], console)

    text = output.getvalue()
    assert "TAIL-MARKER" in text
    assert "HEAD-MARKER" not in text
```

- [ ] **Step 2: Rodar os testes e confirmar que falham por módulo ausente**

Run: `python -m pytest test_render_queue.py -v`
Expected: `ModuleNotFoundError: No module named 'render_queue'` (ou `ImportError` equivalente) em todos os testes coletados.

- [ ] **Step 3: Escrever `render_queue.py` completo**

```python
"""Fila de render para o modo --batch: estado por job, tabela ao vivo, ETA e relatório final."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable

from rich import box
from rich.console import Console
from rich.table import Table

STATUS_SYMBOLS = {
    "aguardando": "·",
    "processando": "⏳",
    "ok": "✓",
    "falha": "✗",
    "pulado": "○",
}

MAX_LOG_CHARS = 4000


@dataclass
class QueueJob:
    input_path: str
    output_path: str
    status: str = "aguardando"
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    log: str = ""


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_eta(eta_seconds: float | None) -> str:
    if eta_seconds is None:
        return "--:--"
    return format_duration(eta_seconds)


def estimate_eta(jobs: list[QueueJob], remaining: int) -> float | None:
    durations = [
        job.finished_at - job.started_at
        for job in jobs
        if job.status in ("ok", "falha")
        and job.started_at is not None
        and job.finished_at is not None
    ]
    if not durations:
        return None
    return statistics.mean(durations) * remaining


def build_table(
    jobs: list[QueueJob],
    eta_seconds: float | None = None,
    title: str | None = None,
) -> Table:
    total = len(jobs)
    current = sum(1 for job in jobs if job.status != "aguardando")
    if title is None:
        title = f"Job {current} de {total}  ·  ETA: {format_eta(eta_seconds)}"

    table = Table(title=title, box=box.SIMPLE_HEAD)
    table.add_column("#", justify="right")
    table.add_column("Arquivo")
    table.add_column("Status", justify="center")
    table.add_column("Duração", justify="right")

    for idx, job in enumerate(jobs, start=1):
        symbol = STATUS_SYMBOLS[job.status]
        if (
            job.status in ("ok", "falha")
            and job.started_at is not None
            and job.finished_at is not None
        ):
            duration = format_duration(job.finished_at - job.started_at)
        else:
            duration = "—"
        table.add_row(str(idx), job.input_path, symbol, duration)

    return table


def run_job(job: QueueJob, encode_fn: Callable[[], None], console: Console) -> None:
    job.status = "processando"
    job.started_at = time.time()
    failure: Exception | None = None
    with console.capture() as capture:
        try:
            encode_fn()
        except Exception as exc:  # noqa: BLE001 - repassado via job.error, nao propagado
            failure = exc
    job.finished_at = time.time()
    if failure is not None:
        job.status = "falha"
        job.error = str(failure)
        job.log = capture.get()
    else:
        job.status = "ok"


def render_final_report(jobs: list[QueueJob], console: Console) -> None:
    total = len(jobs)
    ok = sum(1 for job in jobs if job.status == "ok")
    failed = [job for job in jobs if job.status == "falha"]
    skipped = [job for job in jobs if job.status == "pulado"]
    total_seconds = sum(
        (job.finished_at - job.started_at)
        for job in jobs
        if job.status in ("ok", "falha")
        and job.started_at is not None
        and job.finished_at is not None
    )

    console.print()
    console.rule("[bold magenta]\U0001F4CA Fila — Relatório Final")
    console.print(build_table(jobs, title="Resumo da fila"))
    console.print(f"[green]✓ Sucesso:  {ok}/{total}[/green]")
    if skipped:
        console.print(f"[yellow]○ Pulados:  {len(skipped)}/{total}[/yellow]")
    if failed:
        console.print(f"[red]✗ Falhas:   {len(failed)}/{total}[/red]")
        for job in failed:
            console.print(f"[red]  • {job.input_path} → {job.error}[/red]")
            log_text = job.log if len(job.log) <= MAX_LOG_CHARS else job.log[-MAX_LOG_CHARS:]
            if log_text.strip():
                console.print(log_text, style="dim", markup=False, soft_wrap=True)
    console.print(f"[dim]Tempo total da fila: {format_duration(total_seconds)}[/dim]")
    console.print()
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest test_render_queue.py -v`
Expected: todos os testes `PASSED` (12 testes).

- [ ] **Step 5: Commit**

```bash
git add render_queue.py test_render_queue.py
git commit -m "feat(batch): módulo render_queue com estado de job, ETA e relatório final"
```

---

### Task 2: Integrar a fila no loop `--batch` de `Reels_Encoder_v2_FINAL.py`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py:94-98` (bloco de imports `rich`)
- Modify: `Reels_Encoder_v2_FINAL.py:4339-4394` (bloco `# ─── BATCH MODE ───`, loop + resumo)

Se os números de linha tiverem deslocado desde a escrita deste plano, localizar pelo comentário `# ─── BATCH MODE ───────────────────────────────────────────────────────────` — o bloco a seguir é auto-contido a partir da linha `total = len(video_files)` (que fica intocada) até o antigo `sys.exit(0 if not results_failed else 1)`.

**Interfaces:**
- Consumes (de Task 1): `render_queue.QueueJob`, `render_queue.build_table(jobs, eta_seconds=None, title=None)`, `render_queue.estimate_eta(jobs, remaining)`, `render_queue.run_job(job, encode_fn, console)`, `render_queue.render_final_report(jobs, console)`
- Produces: nenhuma interface nova — este task só troca a implementação interna do bloco `--batch`, chamado de `main()`.

- [ ] **Step 1: Adicionar o import do módulo novo**

Em `Reels_Encoder_v2_FINAL.py`, logo após o bloco de imports do `rich` (linha 98, `from rich.table import Table`), adicionar:

```python
import render_queue
```

- [ ] **Step 2: Substituir o loop de batch e o resumo final**

Localizar o trecho atual (a partir de `results_ok: list = []` até `sys.exit(0 if not results_failed else 1)`, hoje linhas ~4343-4394):

```python
        results_ok: list = []
        results_skipped: list = []
        results_failed: list = []

        for idx, input_file in enumerate(video_files, 1):
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            if args.cineon_pipeline == "on":
                out_name = f"{base_name}_Cineon_Film.mp4"
            elif args.mode == "crf":
                out_name = f"{base_name}_Hollywood_CRF18.mp4"
            else:
                out_name = f"{base_name}_Hollywood_2Pass.mp4"
            output_file = os.path.join(output_folder, out_name)

            if os.path.exists(output_file):
                console.print(
                    f"[yellow]○ [{idx}/{total}] Já existe, pulando: {out_name}[/yellow]"
                )
                results_skipped.append(os.path.basename(input_file))
                continue

            console.rule(
                f"[bold cyan][ {idx}/{total} ]  {os.path.basename(input_file)}"
            )
            try:
                _encode_single_file(input_file, output_file, args, is_batch=True)
                results_ok.append(os.path.basename(input_file))
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠ Interrompido pelo usuário[/yellow]")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]✗ Falhou: {e}[/red]")
                results_failed.append((os.path.basename(input_file), str(e)))

        # ── Summary ──────────────────────────────────────────────────────────
        console.print()
        console.rule("[bold magenta]📊 Batch Summary")
        console.print(
            f"[green]✓ Sucesso:  {len(results_ok)}/{total}[/green]"
        )
        for name in results_ok:
            console.print(f"[green]     • {name}[/green]")
        if results_skipped:
            console.print(f"[yellow]○ Pulados:  {len(results_skipped)}/{total}[/yellow]")
            for name in results_skipped:
                console.print(f"[yellow]     • {name}[/yellow]")
        if results_failed:
            console.print(f"[red]✗ Falhas:   {len(results_failed)}/{total}[/red]")
            for name, err in results_failed:
                console.print(f"[red]     • {name}  →  {err}[/red]")
        console.print()
        sys.exit(0 if not results_failed else 1)
```

Substituir por:

```python
        jobs: list[render_queue.QueueJob] = []
        for input_file in video_files:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            if args.cineon_pipeline == "on":
                out_name = f"{base_name}_Cineon_Film.mp4"
            elif args.mode == "crf":
                out_name = f"{base_name}_Hollywood_CRF18.mp4"
            else:
                out_name = f"{base_name}_Hollywood_2Pass.mp4"
            output_file = os.path.join(output_folder, out_name)
            jobs.append(render_queue.QueueJob(input_path=input_file, output_path=output_file))

        with Live(
            render_queue.build_table(jobs, eta_seconds=None),
            console=console,
            refresh_per_second=4,
        ) as live:
            for job in jobs:
                if os.path.exists(job.output_path):
                    job.status = "pulado"
                    remaining = sum(1 for j in jobs if j.status == "aguardando")
                    live.update(render_queue.build_table(jobs, render_queue.estimate_eta(jobs, remaining)))
                    continue

                # Padrão default-arg: fixa o valor de `job` no momento da definição,
                # evitando o late-binding de closures dentro de loops em Python.
                def _do_encode(_input=job.input_path, _output=job.output_path):
                    _encode_single_file(_input, _output, args, is_batch=True)

                try:
                    render_queue.run_job(job, _do_encode, console)
                except KeyboardInterrupt:
                    live.stop()
                    console.print("\n[yellow]⚠ Interrompido pelo usuário[/yellow]")
                    sys.exit(1)

                remaining = sum(1 for j in jobs if j.status == "aguardando")
                live.update(render_queue.build_table(jobs, render_queue.estimate_eta(jobs, remaining)))

        render_queue.render_final_report(jobs, console)
        sys.exit(0 if not any(job.status == "falha" for job in jobs) else 1)
```

- [ ] **Step 3: Checar sintaxe**

Run: `python -m py_compile Reels_Encoder_v2_FINAL.py`
Expected: sem saída, exit 0.

- [ ] **Step 4: Rodar a suíte de testes existente (regressão)**

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q`
Expected: as mesmas 4 falhas nominais do baseline documentado em `STATE.md` (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`) e zero falhas nos testes de `test_render_queue.py`. Se aparecer qualquer falha nova, é regressão — não seguir para o commit.

- [ ] **Step 5: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py
git commit -m "feat(batch): fila com progresso global, ETA e status por arquivo no --batch"
```

---

### Task 3: Smoke test end-to-end + verificação + registro em STATE.md

**Files:**
- Read/Run only: `Reels_Encoder_v2_FINAL.py` (via CLI)
- Modify: `.claude/memory/STATE.md` (append)

**Interfaces:**
- Consumes: o binário `--batch` já integrado (Task 2), `bin/ffmpeg` ou ffmpeg do PATH (já confirmado disponível nesta máquina), os vídeos de amostra já presentes na raiz do repo (`teste.mp4`).

- [ ] **Step 1: Montar uma pasta de fila com um caso de sucesso e um de falha forçada**

```bash
python - <<'PY'
import os
import shutil
import tempfile

scratch_in = tempfile.mkdtemp(prefix="render_queue_smoke_in_")
scratch_out = tempfile.mkdtemp(prefix="render_queue_smoke_out_")

shutil.copy("teste.mp4", os.path.join(scratch_in, "clip_ok.mp4"))
with open(os.path.join(scratch_in, "clip_falha.mp4"), "wb") as f:
    f.write(b"nao e um video valido")

print("IN=" + scratch_in)
print("OUT=" + scratch_out)
PY
```

Anotar os dois caminhos impressos (`IN=`, `OUT=`) — usados no próximo passo.

- [ ] **Step 2: Rodar o batch de verdade e capturar a saída real**

Run (substituindo `<IN>`/`<OUT>` pelos caminhos do Step 1):

```bash
python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance off
```

Expected: exit code `1` (uma falha na fila). A saída deve conter, no relatório final: `✓ Sucesso:  1/2`, `✗ Falhas:   1/2`, o nome `clip_falha.mp4` com a mensagem de erro, e o log capturado do ffmpeg logo abaixo (não deve aparecer nenhum log verboso de `clip_ok.mp4` fora da tabela — só o resumo). Confirmar também que `<OUT>/clip_ok_Hollywood_2Pass.mp4` (ou `_CRF18`, conforme o modo default) foi criado com tamanho > 0.

- [ ] **Step 3: Confirmar skip-se-já-existe ainda funciona**

Run (mesmo comando do Step 2, de novo, sem apagar `<OUT>`):

```bash
python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance off
```

Expected: o relatório final mostra `clip_ok.mp4` com status `pulado` (símbolo `○`) desta vez, sem re-encodar.

- [ ] **Step 4: Limpar a fila de teste**

```bash
python - <<'PY'
import shutil
shutil.rmtree("<IN>", ignore_errors=True)
shutil.rmtree("<OUT>", ignore_errors=True)
PY
```

Run: `git status`
Expected: nenhum arquivo novo/sujo relacionado ao smoke test (as pastas eram fora do repo, em `tempfile.mkdtemp()`).

- [ ] **Step 5: Rodar a suíte completa uma última vez**

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q`
Expected: mesmo resultado do Task 2 Step 4 (as 4 falhas nominais do baseline, zero novas).

- [ ] **Step 6: Registrar em `.claude/memory/STATE.md`**

Acrescentar (append, nunca reescrever linhas existentes) uma seção nova no fim do arquivo:

```markdown
## Ciclo V — render queue profissional (batch de verdade) — 2026-08-16

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| V1 | done | render_queue.py, test_render_queue.py | 13 testes novos, todos PASS — colar saída real do Step 4 da Task 1 |
| V2 | done | Reels_Encoder_v2_FINAL.py | loop --batch substituído por fila com Live; py_compile OK; regressão sem falha nova — colar saída real do Task 2 Step 4 |
| V3 | done | .claude/memory/STATE.md | smoke test real: 1 sucesso + 1 falha forçada, skip-se-já-existe confirmado no 2º run — colar saída real dos Steps 2/3/5 |
```

Substituir os textos "colar saída real..." pelo output efetivo dos comandos rodados (não resumir, não arredondar — números e mensagens exatas), seguindo o padrão dos ciclos anteriores no mesmo arquivo (ex.: `## Ciclo Q`, `## Ciclo infra`).

- [ ] **Step 7: Commit**

```bash
git add .claude/memory/STATE.md
git commit -m "docs(state): evidência real do smoke test da fila de render (Ciclo V)"
```

## Self-Review

- **Cobertura do spec:** Estado por job (§ Estado por job) → `QueueJob` (Task 1). Render/ETA (§ Renderização e ETA) → `build_table`/`estimate_eta`/`run_job`/`render_final_report` (Task 1). Captura de output (§ Por que capturar) → `console.capture()` dentro de `run_job` (Task 1), fio ligado ao loop real em Task 2. Erros/interrupção (§ Erros e interrupção) → `try/except KeyboardInterrupt` em torno de `run_job` + `with Live(...) as live` (Task 2). Testes (§ Testing) → Task 1 Step 1. Files touched (§ Files touched) → cobertos por Task 1 e Task 2.
- **Placeholder scan:** nenhum "TBD"/"TODO" — os únicos textos a preencher em runtime são os `<IN>`/`<OUT>`/saídas reais da Task 3, que são explicitamente marcados como "substituir pelo output efetivo", não placeholders de projeto.
- **Consistência de tipos:** `render_queue.QueueJob`, `build_table(jobs, eta_seconds=None, title=None)`, `estimate_eta(jobs, remaining)`, `run_job(job, encode_fn, console)`, `render_final_report(jobs, console)` — mesmos nomes e assinaturas entre Task 1 (definição) e Task 2 (uso).
