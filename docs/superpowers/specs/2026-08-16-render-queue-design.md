# Render Queue Profissional (Batch de Verdade) — design

**Date:** 2026-08-16
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

O `--batch` de `Reels_Encoder_v2_FINAL.py` hoje é uma lista sequencial: `for`
loop simples, `console.print`/`console.rule` por arquivo, resumo final em
texto puro no fim (`Reels_Encoder_v2_FINAL.py:4311-4394`). Não há progresso
global, ETA, nem visão de status por arquivo enquanto a fila roda — só se
sabe o que aconteceu com um arquivo depois que ele termina.

Este spec adiciona uma fila com progresso global visível durante a execução
inteira: "job N de M", ETA total, e uma tabela ao vivo com status por
arquivo (aguardando / processando / ok / falha / pulado), seguida de um
relatório final consolidado. É o padrão que qualquer ferramenta de encode
paga (Handbrake queue, Adobe Media Encoder) já oferece.

## Non-goals

- Não introduzir paralelismo — a fila continua processando um arquivo por
  vez, sequencialmente. Só a *visualização* muda, não a execução.
- Não criar uma abstração `Queue`/`Job` reutilizável para outros fluxos
  (ex.: uma fila futura via UI). O único ponto de uso hoje é o `--batch` da
  CLI; abstrair para reuso hipotético viola a política anti-escopo do
  projeto (`CLAUDE.md`: "não criar abstrações").
- Não adicionar nova dependência — o projeto já importa `rich.live.Live`,
  `rich.table.Table` e `rich.panel.Panel` (usados no medidor EBU R128); a
  fila reaproveita a mesma biblioteca.
- Não mudar o comportamento de skip-se-já-existe, nem o de abortar em
  `KeyboardInterrupt` — ambos preservados como estão hoje.

## Architecture

Novo módulo `render_queue.py` na raiz do projeto (mesmo nível de
`ebu_meter.py`), com funções puras + um dataclass de estado — sem
hierarquia de classes. O loop de controle continua em
`Reels_Encoder_v2_FINAL.py` (bloco `# ─── BATCH MODE ───`,
linhas 4311-4394); ele passa a chamar as funções do módulo em vez de fazer
`console.print`/`console.rule` diretamente para o progresso por-arquivo.

Module boundary: `render_queue.py` não sabe nada sobre FFmpeg, `EncodeConfig`
ou o pipeline Cineon — ele recebe uma função de encode (`encode_fn`) já
fechada sobre esses detalhes e só orquestra estado/renderização/tempo.

## Estado por job

```python
@dataclass
class QueueJob:
    input_path: str
    output_path: str
    status: str  # "aguardando" | "processando" | "ok" | "falha" | "pulado"
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    log: str = ""  # capturado via console.capture(); só relevante se status == "falha"
```

A fila inteira é `list[QueueJob]`, construída antes do loop começar a partir
da mesma lista `video_files` que já existe hoje (via `find_video_files`).
Sem classe `Queue` própria — o `for` loop em `Reels_Encoder_v2_FINAL.py` já
é o runner.

## Renderização e ETA

`render_queue.py` expõe quatro funções:

- **`build_table(jobs: list[QueueJob], eta_seconds: float | None) -> Table`**
  — monta a tabela (colunas: `#`, arquivo, status, duração) mais uma
  linha/painel de rodapé com "Job N de M" e o ETA total formatado
  (`--:--` enquanto `eta_seconds is None`, i.e. antes do primeiro job
  terminar).
- **`estimate_eta(jobs: list[QueueJob], remaining: int) -> float | None`**
  — média móvel simples: `mean(finished_durations) * remaining`. Retorna
  `None` se nenhum job terminou ainda (sem histórico pra estimar).
- **`run_job(job: QueueJob, encode_fn: Callable[[], None]) -> None`** —
  envolve a chamada de `encode_fn` (fechamento sobre `_encode_single_file`)
  com `console.capture()` do Rich. Atualiza `status`, `started_at`,
  `finished_at` in-place; se `encode_fn` lançar exceção, popula `job.error`
  e `job.log` com o conteúdo capturado e re-marca `status="falha"` — a
  exceção NÃO propaga (o loop externo decide se continua ou aborta, como
  hoje).
- **`render_final_report(jobs: list[QueueJob]) -> None`** — imprime o
  resumo final: tabela consolidada (mesmos status), tempo total da fila, e
  para cada job com `status == "falha"`, o log capturado — completo se
  couber em 4000 caracteres, senão só os últimos 4000 (mais chance de
  conter a exceção real, que costuma vir no fim do output).

O loop em `Reels_Encoder_v2_FINAL.py` usa `with rich.live.Live(...) as live:`
envolvendo o loop inteiro — mesmo padrão já usado no medidor EBU — chamando
`live.update(build_table(...))` a cada transição de status de job.

### Por que capturar output em vez de deixá-lo rolar

O encode de cada arquivo hoje imprime bastante coisa fora dos logs do
FFmpeg: preflight de `--enhance-ai`, geração de máscara MCTF, aviso de
dither, hardware info. Com a tabela ao vivo como única superfície visível
durante o batch, esse output por-job é redirecionado para um buffer via
`console.capture()` (mecanismo nativo do Rich, sem redirecionar stdout na
mão) e só é exibido se aquele job falhar — como um runner de CI que
colapsa steps verdes e expande os que falharam. O medidor EBU R128 (janela
FFplay) já é suprimido em modo batch hoje (`is_batch=True` →
`_show_meter=False`), então não há conflito com essa captura.

## Erros e interrupção

- Falha de um job (exceção capturada em `run_job`) marca `status="falha"`,
  guarda `error`/`log`, e a fila **continua** para o próximo arquivo —
  mesmo comportamento atual (batch não aborta em uma falha isolada).
- `KeyboardInterrupt` continua abortando a fila inteira (comportamento
  atual preservado), mas agora o `with Live(...) as live:` garante que o
  terminal seja liberado corretamente antes do aviso de interrupção ser
  impresso — hoje o `sys.exit(1)` no meio do loop não passa por nenhum
  contexto de Live, então essa é uma correção de robustez, não só
  cosmética.
- Skip-se-já-existe (`os.path.exists(output_file)`) continua sendo checado
  antes de `run_job` ser chamado; o job correspondente vai direto para
  `status="pulado"` sem passar pela captura de output.

## Testing

`test_render_queue.py` na raiz do projeto (pytest, sem config de
`testpaths` restringindo — roda junto com o resto da suíte). Sem FFmpeg
real: `encode_fn` é sempre um fake nos testes.

- `estimate_eta`: zero jobs concluídos → `None`; médias simples com 1-3
  jobs concluídos → valor esperado.
- `build_table`: uma linha por job, símbolo de status correto para cada um
  dos 5 estados, painel de rodapé mostra "Job N de M" e o ETA formatado
  (incluindo o caso `eta_seconds is None` → `--:--`).
- `run_job`: com `encode_fn` fake que sucede → `status="ok"`, `log==""`;
  com `encode_fn` fake que lança exceção → `status="falha"`, `error` e
  `log` populados, exceção não propaga.

## Files touched

- `render_queue.py` (novo, raiz do projeto)
- `test_render_queue.py` (novo, raiz do projeto)
- `Reels_Encoder_v2_FINAL.py` (bloco `# ─── BATCH MODE ───`, linhas
  ~4311-4394): loop passa a usar `render_queue` em vez de
  `console.print`/`console.rule` direto para progresso por-arquivo; resumo
  final delega para `render_final_report`.
