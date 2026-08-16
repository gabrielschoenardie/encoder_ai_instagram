# Render Queue — Progresso Ao Vivo Durante o Job (VF2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar sinal visual de vida durante um job em andamento no `--batch` — hoje a tabela fica congelada do início ao fim do encode, o que o usuário reportou como "parece travado".

**Architecture:** `render_queue.run_job` passa a rodar `encode_fn` numa `threading.Thread` em background; o loop principal (que já possui o `Live`) fica livre pra chamar um callback `on_tick` a cada ~250ms enquanto a thread roda, redesenhando a tabela. `build_table` ganha a capacidade de calcular a duração **ao vivo** (`time.time() - job.started_at`) para o job com `status == "processando"`, em vez do `"—"` estático atual.

**Tech Stack:** Python 3.11+, `threading` (stdlib), `rich` (já dependência do projeto).

**Spec:** `docs/superpowers/specs/2026-08-16-render-queue-design.md` (design original) + `.claude/memory/FINDINGS.md` § achado `VF2` (gap identificado após teste real do usuário).

## Global Constraints

- Sem nova dependência — só `threading` (stdlib) e `rich`, já usados no projeto.
- Não reintroduzir o conflito de dois `Live`s concorrentes corrigido no ciclo W (`VF1`) — o `on_tick` só chama `live.update()` a partir do **mesmo** `Live`/thread principal que já existe; nenhuma segunda `Progress`/`Live` é criada.
- `on_tick` é opcional (`None` por padrão) — chamadas existentes de `run_job` sem esse argumento continuam funcionando exatamente como antes (comportamento do Ciclo V/W preservado).
- `console.capture()` continua envolvendo a execução completa de `encode_fn` (rodando agora dentro da thread) — o design de "capturar e só mostrar se falhar" do Ciclo V não muda.

---

### Task 1: `render_queue.py` — `run_job` em thread + `on_tick`, duração ao vivo em `build_table`

**Files:**
- Modify: `render_queue.py`
- Modify: `test_render_queue.py`

**Interfaces:**
- Produces (assinatura nova de `run_job`, substitui a existente):
  `run_job(job: QueueJob, encode_fn: Callable[[], None], console: Console, on_tick: Callable[[], None] | None = None, tick_interval: float = 0.25) -> None`
- `build_table` mantém a assinatura atual (`build_table(jobs, eta_seconds=None, title=None) -> Table`), só muda o cálculo interno da coluna Duração.

- [ ] **Step 1: Adicionar os testes novos em `test_render_queue.py`**

Adicionar `import threading` e `import time` já existe (usado por `_finished_job`, mas `time` não é importado no arquivo de teste hoje — conferir e adicionar `import time` no topo se ainda não houver). Acrescentar ao fim do arquivo:

```python
def test_run_job_calls_on_tick_while_encode_runs():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO())
    tick_count = {"n": 0}

    def encode_fn():
        time.sleep(0.2)

    def on_tick():
        tick_count["n"] += 1

    run_job(job, encode_fn, console, on_tick=on_tick, tick_interval=0.05)

    assert job.status == "ok"
    assert tick_count["n"] >= 2


def test_build_table_shows_ticking_duration_for_running_job():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4", status="processando")
    job.started_at = time.time() - 5.0

    table = build_table([job], eta_seconds=None)

    output = io.StringIO()
    console = Console(file=output, width=120)
    console.print(table)
    text = output.getvalue()

    assert "—" not in text.split("a.mp4", 1)[1].split("\n", 1)[0]
    assert any(f"00:0{n}" in text for n in (3, 4, 5, 6, 7))
```

- [ ] **Step 2: Rodar os testes novos e confirmar que falham do jeito certo**

Run: `python -m pytest test_render_queue.py -v -k "on_tick or ticking_duration"`
Expected: `test_run_job_calls_on_tick_while_encode_runs` falha porque `run_job` ainda não aceita `on_tick=`/`tick_interval=` (`TypeError: run_job() got an unexpected keyword argument 'on_tick'`); `test_build_table_shows_ticking_duration_for_running_job` falha porque a duração ainda é `"—"` estático.

- [ ] **Step 3: Reescrever `run_job` em `render_queue.py`**

Adicionar `import threading` junto dos outros imports do topo (`import statistics`, `import time`). Substituir a função `run_job` inteira por:

```python
def run_job(
    job: QueueJob,
    encode_fn: Callable[[], None],
    console: Console,
    on_tick: Callable[[], None] | None = None,
    tick_interval: float = 0.25,
) -> None:
    job.status = "processando"
    job.started_at = time.time()
    failure: Exception | None = None

    def _target() -> None:
        nonlocal failure
        try:
            encode_fn()
        except Exception as exc:  # noqa: BLE001 - repassado via job.error, nao propagado
            failure = exc

    with console.capture() as capture:
        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        while worker.is_alive():
            if on_tick is not None:
                on_tick()
            worker.join(timeout=tick_interval)

    job.finished_at = time.time()
    if failure is not None:
        job.status = "falha"
        job.error = str(failure)
        job.log = capture.get()
    else:
        job.status = "ok"
```

- [ ] **Step 4: Atualizar o cálculo de duração em `build_table`**

Localizar o bloco de loop dentro de `build_table`:

```python
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
```

Substituir por:

```python
    for idx, job in enumerate(jobs, start=1):
        symbol = STATUS_SYMBOLS[job.status]
        if (
            job.status in ("ok", "falha")
            and job.started_at is not None
            and job.finished_at is not None
        ):
            duration = format_duration(job.finished_at - job.started_at)
        elif job.status == "processando" and job.started_at is not None:
            duration = format_duration(time.time() - job.started_at)
        else:
            duration = "—"
        table.add_row(str(idx), job.input_path, symbol, duration)
```

- [ ] **Step 5: Rodar todos os testes de `test_render_queue.py` e confirmar que passam**

Run: `python -m pytest test_render_queue.py -v`
Expected: todos os testes `PASSED` (14 testes — os 12 anteriores + os 2 novos deste task).

- [ ] **Step 6: Commit**

```bash
git add render_queue.py test_render_queue.py
git commit -m "feat(batch): progresso ao vivo durante o job — thread + cronômetro em run_job/build_table (VF2)"
```

---

### Task 2: Fiar o `on_tick` no loop `--batch` de `Reels_Encoder_v2_FINAL.py`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py` (bloco `# ─── BATCH MODE ───`, já modificado no Ciclo V — hoje contém `with Live(...) as live:` seguido do loop `for job in jobs:`)

Localizar pelo comentário `# ─── BATCH MODE ───` se os números de linha tiverem deslocado.

**Interfaces:**
- Consumes (de Task 1): `render_queue.run_job(job, encode_fn, console, on_tick=None, tick_interval=0.25)` — novo parâmetro opcional `on_tick`.

- [ ] **Step 1: Substituir o corpo do `with Live(...) as live:`**

Localizar o trecho atual (escrito no Ciclo V):

```python
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
```

Substituir por:

```python
        with Live(
            render_queue.build_table(jobs, eta_seconds=None),
            console=console,
            refresh_per_second=4,
        ) as live:

            def _refresh_table() -> None:
                remaining = sum(1 for j in jobs if j.status == "aguardando")
                live.update(render_queue.build_table(jobs, render_queue.estimate_eta(jobs, remaining)))

            for job in jobs:
                if os.path.exists(job.output_path):
                    job.status = "pulado"
                    _refresh_table()
                    continue

                # Padrão default-arg: fixa o valor de `job` no momento da definição,
                # evitando o late-binding de closures dentro de loops em Python.
                def _do_encode(_input=job.input_path, _output=job.output_path):
                    _encode_single_file(_input, _output, args, is_batch=True)

                try:
                    render_queue.run_job(job, _do_encode, console, on_tick=_refresh_table)
                except KeyboardInterrupt:
                    live.stop()
                    console.print("\n[yellow]⚠ Interrompido pelo usuário[/yellow]")
                    sys.exit(1)

                _refresh_table()
```

(A mudança em relação ao Ciclo V: os dois blocos duplicados de `remaining = ...; live.update(...)` viram uma função local `_refresh_table()`, reaproveitada também como `on_tick` do `run_job`.)

- [ ] **Step 2: Checar sintaxe**

Run: `python -m py_compile Reels_Encoder_v2_FINAL.py`
Expected: sem saída, exit 0.

- [ ] **Step 3: Rodar a suíte de testes (regressão)**

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q`
Expected: as mesmas 4 falhas nominais do baseline já documentado (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`), zero falhas novas.

- [ ] **Step 4: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py
git commit -m "feat(batch): ligar o cronômetro ao vivo no loop --batch (VF2)"
```

---

### Task 3: Smoke test real — confirmar que o cronômetro anda de verdade

**Files:**
- Read/Run only: `Reels_Encoder_v2_FINAL.py` (via CLI)
- Modify: `.claude/memory/STATE.md` (append)

- [ ] **Step 1: Montar uma fila com 1 clipe real (encode longo o bastante pra ver o cronômetro andar)**

```bash
python - <<'PY'
import os
import shutil
import tempfile

scratch_in = tempfile.mkdtemp(prefix="render_queue_tick_in_")
scratch_out = tempfile.mkdtemp(prefix="render_queue_tick_out_")

# Prefira o clipe real mais longo disponível na raiz do repo para garantir
# alguns segundos de encode visíveis (ver `ls *.mp4` na raiz do projeto).
shutil.copy("teste.mp4", os.path.join(scratch_in, "clip.mp4"))

print("IN=" + scratch_in)
print("OUT=" + scratch_out)
PY
```

- [ ] **Step 2: Rodar o batch e capturar a saída ao longo do tempo**

Run (substituindo `<IN>`/`<OUT>`), redirecionando para um arquivo pra poder inspecionar depois:

```bash
python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance off > /tmp/tick_smoke.log 2>&1
```

Expected: exit code `0`. Abrir `/tmp/tick_smoke.log` (ou usar `grep`) e confirmar que a coluna Duração da linha `clip.mp4` aparece com **múltiplos valores diferentes** ao longo da saída capturada (ex.: `00:00`, depois `00:01`, `00:02`, ... antes do valor final) — não só um único valor estático do início ao fim. Se o log só tiver o snapshot final (porque o terminal não é interativo e o redirecionamento não captura os frames intermediários do `Live`), documentar isso explicitamente e, em vez disso, confirmar via teste automatizado (Task 1) mais uma leitura manual do Orquestrador/usuário no terminal real — não bloquear neste passo por limitação de captura não-interativa.

- [ ] **Step 3: Limpar e rodar a suíte completa mais uma vez**

```bash
python - <<'PY'
import shutil
shutil.rmtree("<IN>", ignore_errors=True)
shutil.rmtree("<OUT>", ignore_errors=True)
PY
```

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q`
Expected: mesmo baseline de sempre (4 falhas nominais, zero novas).

- [ ] **Step 4: Registrar em `.claude/memory/STATE.md`**

Acrescentar (append) uma seção nova no fim do arquivo:

```markdown
## Ciclo X — progresso ao vivo durante o job (VF2) — 2026-08-16

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| X1 | done | render_queue.py, test_render_queue.py | 14 testes, todos PASS — colar saída real do Step 5 da Task 1 |
| X2 | done | Reels_Encoder_v2_FINAL.py | py_compile OK; regressão sem falha nova — colar saída real do Task 2 Step 3 |
| X3 | done | .claude/memory/STATE.md | smoke test real: cronômetro incrementando confirmado (ou nota explícita da limitação de captura não-interativa) — colar saída real do Task 3 |
```

- [ ] **Step 5: Commit**

```bash
git add .claude/memory/STATE.md
git commit -m "docs(state): evidência real do progresso ao vivo no batch (Ciclo X)"
```

## Self-Review

- **Cobertura:** thread em background + `on_tick` (Task 1 Step 3) → resolve o bloqueio do loop principal descrito no achado `VF2`. Duração ao vivo (Task 1 Step 4) → dá o sinal visual concreto que faltava. Fio no loop real (Task 2) → conecta as duas peças sem reintroduzir o conflito de `Live`s do `VF1` (nenhum `Progress`/`Live` novo é criado, só chamadas a `live.update()` do mesmo `Live` já existente).
- **Placeholder scan:** nenhum "TBD"/"TODO". A única ressalva documentada (Task 3 Step 2) é uma limitação real de ambiente (captura não-interativa pode não registrar frames intermediários do `Live`), não um placeholder de projeto.
- **Consistência de tipos:** `run_job(job, encode_fn, console, on_tick=None, tick_interval=0.25)` — mesma assinatura entre Task 1 (definição) e Task 2 (uso, só passa `on_tick=_refresh_table`, usa o `tick_interval` default).
