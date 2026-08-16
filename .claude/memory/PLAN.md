<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo W: corrigir flicker do MCTF durante --batch (VF1)

Data: 2026-08-16 | Ciclo: W | Origem: usuário testou o `--batch` real (Ciclo V) e reportou
com captura de tela a barra "MCTF masks" piscando linha a linha. Achado:
`.claude/memory/FINDINGS.md` § "Ciclo V, regressão da fila de render" (`VF1`).

## Diagnóstico

Regressão introduzida pelo próprio Ciclo V. `generate_mctf_mask_video()`
(`enhance_visualizer.py:406-496`) abre sua própria `rich.progress.Progress(...)`
sem `console=` explícito — cai no console global singleton do Rich, diferente
do `console` que a fila usa em `Reels_Encoder_v2_FINAL.py`. Antes do Ciclo V
isso era inofensivo (nada mais desenhava ao vivo durante o `--batch`); agora a
fila envolve o loop inteiro num `with Live(tabela) as live:`, e os dois
displays ao vivo (o da fila e o do MCTF) brigam pela mesma região do
terminal a cada frame processado — daí o piscar. Só ocorre com `--mctf on`
**e** `--enhance-ai on` explícitos (default de `--mctf` é `off`); batch
padrão não é afetado.

Fix: mesmo padrão já usado para suprimir o medidor EBU em batch
(`_show_meter = (...) and not is_batch`, `Reels_Encoder_v2_FINAL.py:4011`).
`Progress` do Rich já suporta `disable=True` nativamente (vira no-op, sem
renderizar nada, sem quebrar as chamadas `.add_task`/`.update` do corpo da
função) — não precisa de branch novo dentro do loop de frames.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| W1 | Adicionar `show_progress: bool = True` à assinatura de `generate_mctf_mask_video()` (`enhance_visualizer.py:406-409`); trocar `with Progress(...) as progress:` (linha 489) por `with Progress(..., disable=not show_progress) as progress:`. No call site (`Reels_Encoder_v2_FINAL.py:3942`), passar `show_progress=not is_batch`. Nenhuma outra linha tocada em nenhum dos dois arquivos. | `executor` | `enhance_visualizer.py`, `Reels_Encoder_v2_FINAL.py` | `python -m py_compile enhance_visualizer.py Reels_Encoder_v2_FINAL.py` limpo; `grep -n "show_progress" enhance_visualizer.py Reels_Encoder_v2_FINAL.py` mostra as 3 ocorrências (assinatura, `disable=`, call site); `python -m pytest test_render_queue.py enhance/ ui/ -q` sem falha nova (baseline: as 4 falhas nominais já documentadas) — **done**, commit `6d86eb6` (377 passed, 4 failed nominais) |
| W2 | Smoke test real: rodar `--batch` numa pasta de 1 clipe com `--mctf on --enhance-ai on --performance speed` (fora do repo, `tempfile.mkdtemp()`, mesmo padrão do Ciclo V/Task 3) e confirmar que a barra "MCTF masks" **não aparece mais** durante a fila (capturar a saída completa do comando — não deve conter a string `"MCTF masks"` nem os caracteres de barra de progresso do Rich). Confirmar que `generate_mctf_mask_video` ainda roda de verdade (arquivos `mctf_deband_mask.mp4`/`mctf_sharpen_mask.mp4` criados em `enhance_maps/`, tamanho > 0) — `disable=True` só desliga o desenho, não a geração das máscaras. Limpar tudo depois. Colar saída real em `STATE.md` § nova seção `## Ciclo W`. | `executor` | `.claude/memory/STATE.md` | saída do smoke test sem "MCTF masks"; `enhance_maps/mctf_*.mp4` gerados com tamanho > 0; `git status` limpo após cleanup — **done**, commit `035c53d` (0 ocorrências de "MCTF masks"; máscaras 211290216 + 513079464 bytes; fila `1/1`; 377 passed, 4 failed nominais) |

## Notas de execução

- W1 e W2 são sequenciais (W2 depende do fix de W1 já commitado).
- Não mudar `_show_meter`/EBU meter nem qualquer outro comportamento do
  `--batch` — escopo é só a barra do MCTF.
- `enhance_maps/` é gerado fora de controle de versão pelo próprio encoder
  (pasta de trabalho); confirmar que o smoke test do W2 não deixa lixo no
  repo (`git status` limpo — a pasta já deve estar no `.gitignore`; se não
  estiver, isso é um achado novo, não corrigir sem perguntar).
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
