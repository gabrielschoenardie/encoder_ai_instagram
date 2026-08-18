<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AD: interrupção robusta, encerrar o ffmpeg órfão (YF1)

Data: 2026-08-18 | Ciclo: AD | Origem: `docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md` (CICLO AD, Tasks 6–9) + `docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md` + `.claude/memory/FINDINGS.md` § `YF1`.

## Diagnóstico

O handler de `KeyboardInterrupt` do modo `--batch` remove o arquivo de
saída parcial mas não encerra o subprocesso do ffmpeg que o gerou. No
Windows o ffmpeg ainda segura o handle do arquivo nesse instante, o
`os.remove` de `discard_partial_output` falha com `OSError`, e o
`except OSError: return False` engole o erro em silêncio — nenhum aviso
aparece. Pior: o ffmpeg órfão sobrevive à saída do Python e **termina
de escrever** o `.mp4` sozinho, produzindo um arquivo de tamanho normal
que nunca passou pelo pós-encode (remux do átomo `colr`, `.qc.json`/
`.qc.html`), e que a execução seguinte da fila promove a `○ pulado` —
exatamente o sintoma que o Ciclo Y (fix do `XF1`) queria eliminar. O
Ciclo AC (Windows no CI) é pré-requisito deste ciclo: sem um job de
Python em `windows-latest` não há como provar a correção do `YF1` na
plataforma onde o bug existe — já satisfeito, PR #41 mergeado em
`main` (`340e721`).

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AD1 | Reescrever este `PLAN.md` para o Ciclo AD, com o diagnóstico do `YF1` resumido em três linhas e a tabela AD1..AD4. Espelha a Task 6. | `executor` | `.claude/memory/PLAN.md` | **done** — este arquivo reescrito; commit feito |
| AD2 | `render_queue.py`: substituir `discard_partial_output` por versão com retentativa e parâmetros injetáveis (`remove`, `exists`, `sleep`, `attempts`, `delay`), preservando a assinatura compatível com as duas chamadas existentes. Adicionar os 3 testes novos de retentativa. Espelha a Task 7. | `executor` | `render_queue.py`, `test_render_queue.py` | `python -m pytest test_render_queue.py -v` → **26 passed** (23 + 3 novos); os 2 testes do Ciclo Y (`test_discard_partial_output_removes_existing_file`, `..._returns_false_when_absent`) continuam verdes |
| AD3 | `Reels_Encoder_v2_FINAL.py`: registrar o `Popen` ativo do ffmpeg (`_register_ffmpeg`/`_ACTIVE_FFMPEG_LOCK`), expor `terminate_active_ffmpeg(timeout=5.0) -> bool`, chamá-la nos dois handlers de `KeyboardInterrupt` (batch e single-file) antes do `discard_partial_output`, e tornar visível (aviso vermelho) o caso em que a remoção falha mesmo após o `terminate()`. Espelha a Task 8. | `executor-pesado` | `Reels_Encoder_v2_FINAL.py` | `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ -q` → **395 passed** (392 + 3 da AD2); saída colada literal |
| AD4 | Smoke test real em Windows na janela crítica medida pelo Ciclo Y (t≈113s–135s de um job de ~140s): confirmar ausência de ffmpeg órfão, remoção do parcial (ou aviso vermelho quando falhar), e job refeito (não `○ pulado`) na execução seguinte. Fechar o ciclo com evidência real. Espelha a Task 9. | `executor-pesado` | `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md` | saída real da reprodução colada literal em `STATE.md`; `YF1` marcado corrigido em `FINDINGS.md` só se os 3 sintomas forem verificados na plataforma Windows real — senão registrar "corrigido com prova parcial" e manter aberto; `ABF3` reconfirmado aberto/adiado; `PLAN.md` com AD1..AD4 `done` + sha |

## Notas de execução

- **Ciclo AD não altera o caminho feliz.** Nenhuma mudança observável
  num encode que termina normalmente. O `terminate()` só dispara sob
  `KeyboardInterrupt`.
- **`discard_partial_output` continua sem levantar.** O
  `except OSError: return False` é decisão do Ciclo Y e permanece
  correta; o que falta é o `terminate()` antes e o aviso visível
  depois.
- **Idioma de injeção por argumento default**, já usado em
  `ui/binaries.py` (`resolve_binary(name, which=shutil.which, ...)`) —
  torna a retentativa testável sem `monkeypatch`. Estilo de teste da
  casa: sem fixtures (exceto `tmp_path`), sem `monkeypatch`, sem
  classes.
- **Localizar por âncora, não por número de linha** — os números do
  plano-fonte são do commit `c161ce1` e vão deslocar.
- **Baseline a preservar:** `python -m pytest test_render_queue.py
  enhance/ ui/ -q` → `392 passed` em Linux hoje; `395 passed` ao final
  da AD3 (392 + 3 novos da AD2).
- **AD4 precisa rodar em Windows real.** Reproduzir em Linux não prova
  nada — o `YF1` é um bug de handle de arquivo específico do Windows.
  Se a máquina Windows não estiver disponível, não marcar `YF1` como
  corrigido — registrar "corrigido com prova parcial" e manter aberto,
  para não repetir o padrão do `ABF1` (achado fechado sem evidência na
  plataforma onde existe).
- Sequência: AD1 é pré-requisito de tudo; AD2→AD3 são sequenciais (a
  AD3 consome a assinatura nova da AD2); AD4 consome a evidência das
  duas.
- Retorno do agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
