# Fila — Interrupção Segura, Log Preservado e ETA Correto — design

**Date:** 2026-08-17
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

Corrigir três defeitos da fila de render (`--batch`) introduzidos/expostos
pelos Ciclos V–X, registrados em `.claude/memory/FINDINGS.md` como
`XF1`/`XF2`/`XF3`:

- **XF1** — `Ctrl+C` durante `--batch` deixa um `.mp4` truncado no disco; a
  lógica de skip da execução seguinte trata esse arquivo parcial como
  pronto, entregando vídeo cortado.
- **XF2** — a saída capturada de um job **bem-sucedido** é descartada;
  avisos legítimos (preflight, MCTF, dither) somem sem deixar rastro.
- **XF3** — `estimate_eta` só conta jobs `aguardando`; o job em execução
  fica fora da conta e o ETA exibe `00:00` durante todo o último encode.

## Non-goals / constraints

- Não alterar o caminho single-file (`Reels_Encoder_v2_FINAL.py:4411-4424`)
  — ele já limpa o output parcial corretamente (snapshot de pré-existência,
  `os.remove` guardado, saída 130).
- Não refatorar o naming de output (os 4 sites duplicados / `_OUTPUT_SUFFIXES`)
  — achado `M1`, fora de escopo.
- Não ampliar o escopo para `<base>_temp.mp4` (arquivo intermediário do
  remux do átomo `colr`). O caminho single-file também não limpa isso;
  registrar como achado novo se observado, não corrigir aqui.
- Mudança de comportamento visível e intencional: `--batch` passa a sair
  com **130** em interrupção (hoje sai `1`), alinhando com o caminho
  single-file.

## Architecture

Toda a lógica nova vive em `render_queue.py` (módulo puro, já testado), e
não em `Reels_Encoder_v2_FINAL.py`. Motivo: `main()` do engine tem 383
linhas, monta o argparse inline e encerra cada branch com `sys.exit(...)`
— é intestável na prática, e nenhum teste do repo importa
`Reels_Encoder_v2_FINAL`. O engine recebe apenas o mínimo necessário:
chamar os helpers novos e ajustar o cálculo de `remaining`/ETA no loop
`--batch`.

**O mecanismo da interrupção.** Desde o Ciclo X, `encode_fn` roda numa
daemon thread dentro de `run_job` (`render_queue.py:116-117`). O CPython
entrega `KeyboardInterrupt` **só à main thread**, que está bloqueada em
`on_tick()` ou em `worker.join(...)` dentro do laço `while
worker.is_alive():`. Por isso o `except Exception` interno de `_target`
(`render_queue.py:112`) nunca vê o sinal — `KeyboardInterrupt` não é
`Exception` — e as linhas de fechamento do job (`:123-129`, que marcam
`status`/`finished_at`) nunca executam. O resultado observado é `status`
preso em `"processando"` e `finished_at is None` mesmo depois do processo
ter encerrado.

A correção estrutural é envolver o laço `while worker.is_alive():` num
`try`/`except KeyboardInterrupt:` na main thread, marcar o job como
`"interrompido"` (com `finished_at` e `job.log = log_text`) e
**repropagar** a exceção — o chamador (`Reels_Encoder_v2_FINAL.py`) decide
o que fazer com a fila (parar tudo, remover output parcial, sair com 130).
Na prática `job.log` fica vazio (`""`) quando a interrupção cai durante o
encode: `log_text` só é atribuído depois que o `with console.capture()`
sai normalmente dentro de `_target`, e uma interrupção no meio do job
nunca deixa a worker thread chegar lá — o buffer de captura ainda não foi
fechado nesse ponto. Não é o log parcial capturado até aquele ponto.

**Consequência para os testes.** Um `encode_fn` que levanta
`KeyboardInterrupt` diretamente **não** reproduz o cenário real: `_target`
só captura `Exception`, então a exceção morreria dentro da worker thread
sem nunca chegar à main thread. A simulação fiel do bug é levantar
`KeyboardInterrupt` a partir do callback `on_tick`, que roda na main thread
dentro do próprio laço de `run_job`.

**ETA (XF3).** `estimate_eta` ganha um parâmetro opcional
`in_flight_elapsed: float | None`: quando informado, soma à estimativa o
tempo restante estimado do job em execução (`max(0, média − elapsed)`), em
vez de tratar `remaining` como se só existissem jobs que ainda nem
começaram. O chamador (`Reels_Encoder_v2_FINAL.py`) passa o `started_at`
do job com `status == "processando"`, se houver.

**Log preservado (XF2).** `run_job` já captura toda a saída do job via
`console.capture()` na worker thread; o bug é só não atribuir esse buffer a
`job.log` no caminho de sucesso. Fix: mover a atribuição de `job.log` para
antes do `if failure is not None:`, cobrindo os dois desfechos.

## Riscos conhecidos

- `build_table` faz lookup **não guardado** em `STATUS_SYMBOLS`
  (`render_queue.py:79`, `STATUS_SYMBOLS[job.status]`) — qualquer status
  novo sem entrada correspondente no dicionário gera `KeyError` na próxima
  chamada de render. O novo status `"interrompido"` precisa de entrada em
  `STATUS_SYMBOLS` **antes** de qualquer job poder assumir esse status,
  senão a primeira interrupção quebra o próprio tratamento de erro.
- Remoção do output parcial pode falhar silenciosamente no Windows se o
  processo do FFmpeg ainda estiver liberando o handle do arquivo no
  instante da tentativa (`OSError`); o helper de descarte deve devolver
  `False` nesse caso em vez de propagar, e o chamador decide se avisa o
  usuário.
- Janela de corrida entre `finished_at` do job interrompido e o timestamp
  real de encerramento do processo do FFmpeg: aceitável, não afeta a
  correção do XF1 (o que importa é remover o arquivo, não o timestamp
  exato).

## Validação

- `python -m pytest test_render_queue.py -v` cobrindo: preservação de log
  em sucesso (XF2), ETA considerando o job em voo (XF3), status
  `"interrompido"` e descarte de output parcial simulando
  `KeyboardInterrupt` via `on_tick` (XF1).
- `python -m pytest test_render_queue.py enhance/ ui/ -q` sem regressão
  além do baseline nominal de 4 falhas pré-existentes.
- Smoke test real de `--batch` interrompido no meio de um job: confirmar
  saída `130`, ausência de `.mp4` truncado no diretório de saída, e que a
  execução seguinte refaz o job interrompido em vez de pulá-lo.
