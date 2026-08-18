# Fila — Interrupção Segura, Log Preservado e ETA Correto (Ciclo Y) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Delegação (política deste repo, `CLAUDE.md`):** cada task lista um **Agent** — despache via Task para esse agente exato (`executor` ou `executor-pesado`), não para um subagente genérico.

**Goal:** Corrigir três defeitos da fila de render introduzidos/expostos pelos Ciclos V–X: (XF1) `Ctrl+C` durante `--batch` deixa um `.mp4` truncado no disco que a lógica de skip trata como pronto nas execuções seguintes — o usuário entrega arquivo corrompido; (XF2) a saída capturada de jobs bem-sucedidos é descartada, então avisos legítimos somem; (XF3) o ETA ignora o job em execução e exibe `00:00` durante todo o último encode.

**Architecture:** Toda a lógica nova vive em `render_queue.py` (módulo puro, já testado), porque `main()` do engine tem 383 linhas e termina cada branch com `sys.exit(...)` — é intestável na prática. O engine recebe apenas o mínimo: chamar o helper novo e ajustar o cálculo de `remaining`. A interrupção é simulada nos testes levantando `KeyboardInterrupt` a partir do callback `on_tick`, que roda na main thread dentro do loop do `run_job`.

**Tech Stack:** Python 3.11+, `rich`, `pytest` (já dependências do projeto).

**Spec:** `docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md` (criado na Task 1) + `.claude/memory/FINDINGS.md` § achados `XF1`/`XF2`/`XF3`

## Global Constraints

- **Mudança de comportamento visível e intencional:** o `--batch` passa a sair com **130** em interrupção (hoje sai `1`), alinhando com o caminho single-file (`Reels_Encoder_v2_FINAL.py:4424`). Isso é deliberado, não efeito colateral.
- **Não alterar o caminho single-file.** Ele já limpa o output parcial corretamente (`:4411-4424`); permanece intocado.
- **Não refatorar o naming de output** (os 4 sites duplicados / `_OUTPUT_SUFFIXES`) — é o achado M1, fora de escopo.
- **Não ampliar o escopo para `_temp.mp4`.** Uma interrupção durante o remux do átomo `colr` pode deixar `<base>_temp.mp4`; o caminho single-file também não limpa isso. Registrar como achado novo, não corrigir aqui.
- **Localizar por âncora, não por número de linha.** Os números abaixo são do commit `92dbd90` e vão deslocar. Use o comentário `# ─── BATCH MODE ───` e as strings literais indicadas.
- **Baseline de regressão a preservar:** `python -m pytest test_render_queue.py enhance/ ui/ -q` → hoje `379 passed, 4 failed`. As 4 falhas são nominais do baseline (acoplamento de console Windows), documentadas em `.claude/memory/PLAN.md`. Ao final, esperado: `379 + <novos> passed, 4 failed`.
- Estilo de teste da casa: sem fixtures, sem `monkeypatch`, sem classes. Funções `def test_*()` planas, helper `_finished_job`, `io.StringIO()` + `Console(file=...)` para asserções de render, `pytest.approx` para números.

---

## File Structure

```text
render_queue.py                                        ← modificado (Tasks 2, 3)
test_render_queue.py                                   ← modificado (Tasks 2, 3)
Reels_Encoder_v2_FINAL.py                              ← modificado (Task 4)
docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md   ← novo (Task 1)
docs/superpowers/plans/2026-08-17-fila-interrupcao.md          ← novo (Task 1, este arquivo)
.claude/memory/FINDINGS.md                             ← modificado (Task 1)
.claude/memory/PLAN.md                                 ← reescrito para Ciclo Y (Task 1)
.claude/memory/STATE.md                                ← append (Task 5)
```

---

### Task 1: Registrar os achados e abrir o Ciclo Y

**Agent:** `executor`

**Files:**
- Create: `docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md`
- Create: `docs/superpowers/plans/2026-08-17-fila-interrupcao.md` (salvar este plano na íntegra)
- Modify: `.claude/memory/FINDINGS.md`
- Modify: `.claude/memory/PLAN.md`

**Interfaces:**
- Produces: os IDs `XF1`/`XF2`/`XF3` referenciados por todas as tasks seguintes e pelas mensagens de commit.

- [ ] **Step 1: Anexar os três achados ao `FINDINGS.md`**

Manter o formato vigente do arquivo (cabeçalho `## Achado — <data> (ciclo <L>, <descrição>)`, tabela, depois parágrafos por ID). **Não reutilizar `H1`/`H2`** — já ocupados pelo Ciclo G.

```markdown
## Achado — 2026-08-17 (ciclo X, auditoria pós-fila) — corrigindo no ciclo Y

Evidência: leitura direta de `Reels_Encoder_v2_FINAL.py:4367-4383` e `render_queue.py:124-129`; comparação com o handler single-file em `:4411-4424`.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| XF1 | perda de integridade de entrega | `Reels_Encoder_v2_FINAL.py:4378-4383` | Ctrl+C no batch não remove o output parcial; skip posterior trata o truncado como pronto | S2 | esperado: arquivo parcial removido e refeito na próxima execução; medido: `.mp4` truncado permanece e vira `○ pulado` |
| XF2 | perda de diagnóstico | `render_queue.py:124-129` | `job.log` só é preenchido em falha; saída de job bem-sucedido com avisos é descartada | S3 | esperado: avisos recuperáveis após a fila; medido: buffer capturado descartado no retorno de `run_job` |
| XF3 | UX incorreta | `Reels_Encoder_v2_FINAL.py:4364` | `remaining` conta só `aguardando`; job em execução fica fora do ETA | S4 | esperado: ETA > 0 enquanto há encode rodando; medido: `ETA: 00:00` durante todo o último job |

- **XF1:** O caminho single-file protege o usuário desde o PR #22 (`:4411-4424`: snapshot de pré-existência, `os.remove` guardado, saída 130). O caminho de batch nunca ganhou equivalente — em `:4380-4383` ele apenas para o `Live`, imprime um aviso e sai com 1. Como o loop pula qualquer job cujo output já exista (`:4368`), o arquivo truncado é promovido a "pronto" na execução seguinte. O risco prático é entregar vídeo cortado. Correção no `.claude/memory/PLAN.md` § Ciclo Y.
- **XF2:** `run_job` captura stdout do job na worker thread (`render_queue.py:109-114`) mas só transfere para `job.log` dentro do ramo de falha (`:127`). Antes do Ciclo V essa saída rolava visível no terminal; agora some. Não há `--verbose` nem log em arquivo para recuperar.
- **XF3:** O bug é inteiramente do chamador. `estimate_eta` multiplica a média pelo `remaining` que recebe, e o engine passa apenas a contagem de `aguardando` — o job `processando` fica de fora. No último job, `remaining == 0` e o título exibe `ETA: 00:00` durante o encode inteiro.
```

- [ ] **Step 2: Escrever o spec**

`docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md`, espelhando o esqueleto da casa (`# Título` / `**Date:** / **Status:** / **Author:**` / `## Goal` / `## Non-goals / constraints` / `## Architecture` / `## Riscos conhecidos` / `## Validação`). Conteúdo obrigatório em `## Architecture`:

- Por que a lógica vai para `render_queue.py` e não para o engine: `main()` tem 383 linhas, monta o argparse inline e encerra cada branch com `sys.exit`; nenhum teste do repo importa `Reels_Encoder_v2_FINAL`.
- O mecanismo da interrupção: desde o Ciclo X, `encode_fn` roda numa daemon thread (`render_queue.py:116-117`). O CPython entrega `KeyboardInterrupt` **só à main thread**, que está em `on_tick()` ou `worker.join(...)`. Logo o `except Exception` interno (`:112`) nunca vê o sinal, e as linhas `:123-129` não executam — daí `status` preso em `"processando"` e `finished_at is None`.
- Consequência para os testes: um `encode_fn` que levante `KeyboardInterrupt` **não** reproduz o cenário (o `_target` só pega `Exception`; a exceção morreria na thread). A simulação fiel é levantar do `on_tick`.
- Em `## Riscos conhecidos`: `build_table` faz lookup **não guardado** em `STATUS_SYMBOLS` (`:79`) — qualquer status novo sem entrada no dicionário gera `KeyError`.

- [ ] **Step 3: Reescrever `.claude/memory/PLAN.md` para o Ciclo Y**

Manter o formato vigente: comentário HTML de cabeçalho, `# PLAN — Ciclo Y: interrupção segura, log preservado e ETA correto (XF1/XF2/XF3)`, linha `Data: 2026-08-17 | Ciclo: Y | Origem: ...`, `## Diagnóstico`, a tabela `| ID | tarefa | agente alvo | arquivos | critério de done |` com as linhas Y1..Y5 espelhando as tasks deste plano, e `## Notas de execução` preservando o baseline das 4 falhas nominais. Citar o plano, não transcrevê-lo.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-17-fila-interrupcao-design.md \
        docs/superpowers/plans/2026-08-17-fila-interrupcao.md \
        .claude/memory/FINDINGS.md .claude/memory/PLAN.md
git commit -m "docs: registrar XF1/XF2/XF3 e abrir o Ciclo Y (fila)"
```

---

### Task 2: `render_queue.py` — preservar o log (XF2) e corrigir o ETA (XF3)

**Agent:** `executor`

**Files:**
- Modify: `render_queue.py`
- Modify: `test_render_queue.py`

**Interfaces:**
- Produces (assinatura nova, substitui a existente):
  `estimate_eta(jobs: list[QueueJob], remaining: int, in_flight_elapsed: float | None = None) -> float | None`
- Produces: `job.log` passa a ser preenchido em **todos** os desfechos de `run_job`, não só em falha.
- Consumido pela Task 4 (engine).

- [ ] **Step 1: Preservar o log em qualquer desfecho**

Localizar em `render_queue.py` o bloco final de `run_job` (âncora: a linha `job.finished_at = time.time()`):

```python
    job.finished_at = time.time()
    if failure is not None:
        job.status = "falha"
        job.error = str(failure)
        job.log = log_text
    else:
        job.status = "ok"
```

Substituir por:

```python
    job.finished_at = time.time()
    job.log = log_text
    if failure is not None:
        job.status = "falha"
        job.error = str(failure)
    else:
        job.status = "ok"
```

- [ ] **Step 2: Estender `estimate_eta` para contar o job em execução**

Substituir a função inteira por:

```python
def estimate_eta(
    jobs: list[QueueJob],
    remaining: int,
    in_flight_elapsed: float | None = None,
) -> float | None:
    """Estima o tempo restante da fila, em segundos.

    `remaining` conta os jobs que ainda nao comecaram. `in_flight_elapsed`, quando
    informado, e o tempo ja decorrido do job em execucao: o que falta dele entra na
    estimativa, descontado do que ja passou. Sem amostras concluidas, retorna None.
    """
    durations = [
        job.finished_at - job.started_at
        for job in jobs
        if job.status in ("ok", "falha")
        and job.started_at is not None
        and job.finished_at is not None
    ]
    if not durations:
        return None
    mean = statistics.mean(durations)
    eta = mean * remaining
    if in_flight_elapsed is not None:
        eta += max(0.0, mean - in_flight_elapsed)
    return eta
```

- [ ] **Step 3: Corrigir o teste que codifica o comportamento antigo**

Em `test_render_queue.py`, o teste `test_run_job_marks_success_and_leaves_log_empty` afirma `assert job.log == ""` — isso agora está errado por construção. Renomear e inverter:

```python
def test_run_job_marks_success_and_keeps_log():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    output = io.StringIO()
    console = Console(file=output, width=120)

    def encode_fn():
        console.print("trabalhando...")

    run_job(job, encode_fn, console)

    assert job.status == "ok"
    assert job.error is None
    assert "trabalhando..." in job.log
```

- [ ] **Step 4: Testes novos do ETA**

Anexar, seguindo o helper `_finished_job` já existente no arquivo:

```python
def test_estimate_eta_accounts_for_in_flight_job():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    # media = 15s. 1 job na fila + 5s ja decorridos do job em execucao.
    eta = estimate_eta(jobs, remaining=1, in_flight_elapsed=5.0)
    assert eta == pytest.approx(15.0 + 10.0)


def test_estimate_eta_in_flight_longer_than_average_never_goes_negative():
    jobs = [_finished_job(10.0)]
    eta = estimate_eta(jobs, remaining=0, in_flight_elapsed=999.0)
    assert eta == pytest.approx(0.0)


def test_estimate_eta_without_in_flight_is_unchanged():
    jobs = [_finished_job(10.0), _finished_job(20.0)]
    assert estimate_eta(jobs, remaining=2) == pytest.approx(30.0)


def test_estimate_eta_still_none_without_samples():
    jobs = [QueueJob(input_path="a.mp4", output_path="b.mp4")]
    assert estimate_eta(jobs, remaining=1, in_flight_elapsed=3.0) is None
```

- [ ] **Step 5: Verificar**

Run: `python -m pytest test_render_queue.py -v`
Expected: todos passam (14 originais, com um renomeado, + 4 novos = **18 passed**). Se `test_run_job_marks_success_and_keeps_log` falhar com `AssertionError: assert 'trabalhando...' in ''`, o Step 1 não foi aplicado.

- [ ] **Step 6: Commit**

```bash
git add render_queue.py test_render_queue.py
git commit -m "fix(batch): preservar log de jobs bem-sucedidos e contar job em voo no ETA (XF2, XF3)"
```

---

### Task 3: `render_queue.py` — interrupção segura (XF1)

**Agent:** `executor`

**Files:**
- Modify: `render_queue.py`
- Modify: `test_render_queue.py`

**Interfaces:**
- Produces: `discard_partial_output(job: QueueJob) -> bool` — consumido pela Task 4.
- Produces: novo status `"interrompido"`, com símbolo em `STATUS_SYMBOLS` e contagem em `render_final_report`.
- Produces: `run_job` passa a marcar `job.status = "interrompido"` e `job.finished_at` antes de repropagar o `KeyboardInterrupt`.

- [ ] **Step 1: Importar `os`**

No topo de `render_queue.py`, adicionar `import os` ao bloco stdlib (ordem alfabética: fica antes de `statistics`). O `ruff` do repo tem a regra `I` (isort) ativa — ordem errada quebra o lint.

- [ ] **Step 2: Registrar o símbolo do novo status**

`build_table` faz `STATUS_SYMBOLS[job.status]` **sem guarda** — sem esta entrada, qualquer render após uma interrupção levanta `KeyError`.

```python
STATUS_SYMBOLS = {
    "aguardando": "·",
    "processando": "⏳",
    "ok": "✓",
    "falha": "✗",
    "pulado": "○",
    "interrompido": "⚡",
}
```

- [ ] **Step 3: Helper de descarte do output parcial**

Adicionar logo após `format_eta` (antes de `estimate_eta`):

```python
def discard_partial_output(job: QueueJob) -> bool:
    """Remove o output parcial de um job interrompido.

    Retorna True se removeu de fato. Nunca levanta: um arquivo travado pelo
    processo do ffmpeg ainda encerrando (comum no Windows) devolve False.
    """
    path = job.output_path
    if not path or not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except OSError:
        return False
```

- [ ] **Step 4: Marcar o job em `run_job` antes de repropagar**

Localizar o laço do worker (âncora: `while worker.is_alive():`) e substituir:

```python
    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    while worker.is_alive():
        if on_tick is not None:
            on_tick()
        worker.join(timeout=tick_interval)
```

por:

```python
    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    try:
        while worker.is_alive():
            if on_tick is not None:
                on_tick()
            worker.join(timeout=tick_interval)
    except KeyboardInterrupt:
        # O KeyboardInterrupt chega na main thread (aqui), nunca no worker: o
        # `except Exception` de _target nao ve BaseException. Sem isto o job
        # ficaria preso em "processando" com finished_at=None.
        job.finished_at = time.time()
        job.log = log_text
        job.status = "interrompido"
        raise
```

- [ ] **Step 5: Contabilizar interrompidos no relatório final**

Em `render_final_report`, após a linha `skipped = [...]`, adicionar:

```python
    interrupted = [job for job in jobs if job.status == "interrompido"]
```

E, logo após o bloco `if skipped:`, adicionar:

```python
    if interrupted:
        console.print(f"[yellow]⚡ Interrompidos: {len(interrupted)}/{total}[/yellow]")
```

- [ ] **Step 6: Testes novos**

```python
def test_discard_partial_output_removes_existing_file(tmp_path):
    partial = tmp_path / "clip_Hollywood_CRF18.mp4"
    partial.write_bytes(b"\x00" * 128)
    job = QueueJob(input_path="clip.mp4", output_path=str(partial))

    assert discard_partial_output(job) is True
    assert not partial.exists()


def test_discard_partial_output_returns_false_when_absent(tmp_path):
    job = QueueJob(
        input_path="clip.mp4",
        output_path=str(tmp_path / "nao_existe.mp4"),
    )
    assert discard_partial_output(job) is False


def test_run_job_marks_interrupted_and_reraises():
    # O KeyboardInterrupt precisa vir do on_tick: ele roda na main thread dentro
    # do laco do run_job. Levantado de dentro do encode_fn morreria no worker.
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    console = Console(file=io.StringIO(), width=120)

    def encode_fn():
        time.sleep(1.0)

    def on_tick():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_job(job, encode_fn, console, on_tick=on_tick, tick_interval=0.01)

    assert job.status == "interrompido"
    assert job.finished_at is not None


def test_build_table_renders_interrupted_symbol():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    job.status = "interrompido"
    job.started_at = 100.0
    job.finished_at = 105.0

    output = io.StringIO()
    console = Console(file=output, width=120)
    console.print(build_table([job]))
    text = output.getvalue()

    assert "⚡" in text


def test_render_final_report_counts_interrupted():
    done = _finished_job(10.0)
    stopped = QueueJob(input_path="b.mp4", output_path="b_out.mp4")
    stopped.status = "interrompido"
    stopped.started_at = 100.0
    stopped.finished_at = 104.0

    output = io.StringIO()
    console = Console(file=output, width=120)
    render_final_report([done, stopped], console)
    text = output.getvalue()

    assert "Interrompidos: 1/2" in text
```

Adicionar `discard_partial_output` ao bloco `from render_queue import (...)` no topo do arquivo de teste.

- [ ] **Step 7: Verificar**

Run: `python -m pytest test_render_queue.py -v`
Expected: **23 passed**. Se `test_build_table_renders_interrupted_symbol` falhar com `KeyError: 'interrompido'`, o Step 2 não foi aplicado.

- [ ] **Step 8: Commit**

```bash
git add render_queue.py test_render_queue.py
git commit -m "feat(batch): status interrompido e descarte de output parcial na fila (XF1)"
```

---

### Task 4: Engine — ligar o descarte e o ETA no loop `--batch`

**Agent:** `executor`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py`

**Interfaces:**
- Consumes (da Task 2): `render_queue.estimate_eta(jobs, remaining, in_flight_elapsed=...)`
- Consumes (da Task 3): `render_queue.discard_partial_output(job) -> bool`

- [ ] **Step 1: Corrigir o cálculo do ETA**

Localizar pelo comentário `# ─── BATCH MODE ───` e depois pela definição `def _refresh_table()` (os números de linha terão deslocado). Substituir:

```python
            def _refresh_table() -> None:
                remaining = sum(1 for j in jobs if j.status == "aguardando")
                live.update(render_queue.build_table(jobs, render_queue.estimate_eta(jobs, remaining)))
```

por:

```python
            def _refresh_table() -> None:
                remaining = sum(1 for j in jobs if j.status == "aguardando")
                in_flight = next(
                    (j for j in jobs if j.status == "processando"), None
                )
                elapsed = (
                    time.time() - in_flight.started_at
                    if in_flight is not None and in_flight.started_at is not None
                    else None
                )
                live.update(
                    render_queue.build_table(
                        jobs,
                        render_queue.estimate_eta(
                            jobs, remaining, in_flight_elapsed=elapsed
                        ),
                    )
                )
```

(`time` já está importado no módulo — não adicionar import.)

- [ ] **Step 2: Descartar o output parcial na interrupção**

Localizar o `except KeyboardInterrupt:` imediatamente após a chamada `render_queue.run_job(...)`. Substituir:

```python
                try:
                    render_queue.run_job(job, _do_encode, console, on_tick=_refresh_table)
                except KeyboardInterrupt:
                    live.stop()
                    console.print("\n[yellow]⚠ Interrompido pelo usuário[/yellow]")
                    sys.exit(1)
```

por:

```python
                try:
                    render_queue.run_job(job, _do_encode, console, on_tick=_refresh_table)
                except KeyboardInterrupt:
                    live.stop()
                    console.print("\n[yellow]⚠ Fila interrompida pelo usuário[/yellow]")
                    # Paridade com o caminho single-file: um output truncado seria
                    # tratado como pronto pelo skip da proxima execucao.
                    if render_queue.discard_partial_output(job):
                        console.print(
                            f"[dim]  ● output parcial removido: "
                            f"{os.path.basename(job.output_path)}[/dim]"
                        )
                    render_queue.render_final_report(jobs, console)
                    sys.exit(130)
```

Nota: o job que chega ao `run_job` nunca tinha output pré-existente — o `continue` do skip garante isso — então não é preciso um snapshot `output_preexisted` como no caminho single-file.

- [ ] **Step 3: Verificar sintaxe e regressão**

Run: `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ -q`
Expected: compila sem saída; suíte em `384 passed, 4 failed` (379 + 5 novos da Task 3; as 4 falhas são o baseline nominal já documentado). Nenhuma falha nova além dessas 4.

- [ ] **Step 4: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py
git commit -m "fix(batch): remover output parcial e sair com 130 ao interromper a fila (XF1, XF3)"
```

---

### Task 5: Smoke test real e evidência

**Agent:** `executor-pesado`

**Files:**
- Modify: `.claude/memory/STATE.md`
- Modify: `.claude/memory/PLAN.md` (marcar Y1..Y5 como **done** + sha)

- [ ] **Step 1: Preparar uma pasta de batch**

Copiar 3 clipes curtos (5–10 s) para uma pasta temporária. Se não houver material real disponível, gerar com o ffmpeg embarcado:

```bash
mkdir -p /tmp/batch_in /tmp/batch_out
for i in 1 2 3; do
  ffmpeg -y -f lavfi -i testsrc=size=1080x1920:rate=30:duration=8 \
         -f lavfi -i sine=frequency=440:duration=8 \
         -c:v libx264 -c:a aac -shortest /tmp/batch_in/clip$i.mp4
done
```

- [ ] **Step 2: Interromper a fila e verificar o descarte**

```bash
python Reels_Encoder_v2_FINAL.py --batch /tmp/batch_in --output-dir /tmp/batch_out &
sleep 12
kill -INT %1
wait %1; echo "exit=$?"
ls -la /tmp/batch_out
```

Expected: `exit=130`; o relatório final é impresso mostrando `⚡ Interrompidos: 1/3`; e **nenhum `.mp4` truncado** do job interrompido em `/tmp/batch_out` (jobs já concluídos antes da interrupção permanecem, o que é correto).

**Escape hatch pré-autorizado:** se o ambiente não conseguir entregar um SIGINT limpo ao grupo de processos (comum em runners não interativos), documentar a limitação no `STATE.md` com a saída real obtida e validar o XF1 pelo teste unitário `test_discard_partial_output_removes_existing_file` — não bloquear o ciclo por isso.

- [ ] **Step 3: Provar que o job interrompido é refeito, não pulado**

```bash
python Reels_Encoder_v2_FINAL.py --batch /tmp/batch_in --output-dir /tmp/batch_out
```

Expected: o job interrompido roda de novo (`⏳ processando` → `✓ ok`), **não** aparece como `○ pulado`. Esta é a prova direta do XF1. Os jobs já concluídos aparecem como `○ pulado`, o que é o comportamento correto.

- [ ] **Step 4: Observar o ETA durante o último job**

Durante a execução do Step 3, verificar que o título da tabela mostra `ETA:` com valor **maior que `00:00`** enquanto o último arquivo está codificando. Colar a linha de título observada.

- [ ] **Step 5: Registrar a evidência**

Anexar ao `.claude/memory/STATE.md` uma seção `## Ciclo Y — interrupção segura, log e ETA — 2026-08-17`, com subseções `### Step N` contendo **saída real colada, nunca parafraseada** (política `superpowers:verification-before-completion`), incluindo: contagem da suíte, `exit=` observado, listagem do `/tmp/batch_out` antes e depois, e a linha de título com o ETA.

Se algo divergir do esperado, registrar como achado novo (`YF1`, …) no `FINDINGS.md` em vez de ajustar o teste para passar.

- [ ] **Step 6: Commit**

```bash
git add .claude/memory/STATE.md .claude/memory/PLAN.md
git commit -m "docs(state): evidência real do Ciclo Y (XF1/XF2/XF3)"
```

---

## Self-Review

- **Cobertura:** XF1 → Task 3 (Steps 2–5: status, helper, `run_job`, relatório) + Task 4 Step 2 (engine) + Task 5 Steps 2–3 (prova end-to-end). XF2 → Task 2 Step 1 + Step 3 (teste antigo corrigido). XF3 → Task 2 Step 2 (função) + Task 4 Step 1 (chamador) + Task 5 Step 4 (observação real). Registro dos achados → Task 1.
- **Placeholder scan:** nenhum "TBD"/"implementar depois". Todo código está literal. A única ramificação condicional é o escape hatch do Step 2 da Task 5, deliberado e com critério explícito.
- **Consistência de tipos:** `estimate_eta` recebe `in_flight_elapsed` como terceiro parâmetro nomeado na Task 2 e é chamada exatamente assim na Task 4 Step 1. `discard_partial_output(job) -> bool` é definida na Task 3 Step 3 e consumida como valor booleano na Task 4 Step 2. O status `"interrompido"` é introduzido na Task 3 Step 4 e tem entrada em `STATUS_SYMBOLS` (Step 2) **antes** de qualquer render — ordem obrigatória, pois `build_table` faz lookup não guardado.
- **Risco residual conhecido:** uma interrupção durante a janela do remux do átomo `colr` pode deixar `<base>_temp.mp4` órfão. O caminho single-file tem o mesmo comportamento. Fora de escopo por decisão explícita — registrar como achado separado se observado na Task 5.