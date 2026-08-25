<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AJ: isolar os testes de --output-dir da dependência de ffmpeg (AIF1)

Data: 2026-08-25 | Ciclo: AJ | Origem: `.claude/memory/FINDINGS.md` § `AIF1` (aberto no Ciclo AI) + `docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md`.

## Diagnóstico

`main` está com o CI vermelho desde o Ciclo AG. Confirmado no log real do
job "Tests (ubuntu-latest, Python 3.11)" do run `32590519448`
(SHA `3f12070`): `2 failed, 423 passed in 3.07s`, ambas `assert 1 == 0`.

Os dois testes de `enhance/test_output_dir_and_pipeline_tag.py`
(`test_output_dir_with_batch_does_not_trigger_usage_error` e
`test_batch_without_output_dir_does_not_trigger_usage_error`, Ciclo AG,
commit `c51516e`) chamam `main()` de ponta a ponta via
`_run_main_with_argv()` para validar comportamento do parser, mas o
caminho atravessa a checagem de dependência do ffmpeg em
`Reels_Encoder_v2_FINAL.py:4399-4414` antes de chegar à lógica de parser
que o teste quer validar. Nenhum runner do GitHub Actions vem com ffmpeg
pré-instalado, e o `ci.yml` não o instala.

**Por que consertar o teste e não o produto:** a ordem de checagem em
`main()` é intencional — falhar rápido numa dependência ausente é melhor
UX do que só descobrir isso depois de escanear arquivos de batch. O
defeito é o teste ter escopo maior do que precisa (testa parser, mas
exercita ffmpeg).

## Desenho

Correção via `monkeypatch.setattr("ui.preflight.missing_ffmpeg_binaries",
lambda *a, **kw: [])` nos dois testes falhando — convenção já estabelecida
no repo (`ui/test_launcher.py`, `enhance/test_cineon_constants_guard.py`,
`enhance/test_hdr_pipeline.py`). Detalhe completo do desenho:
`docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md`.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AJ1 | Registrar o achado `AIF1`, escrever spec + plano na íntegra, reescrever este `PLAN.md`. | executor | `docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md`, `docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md`, `.claude/memory/FINDINGS.md`, `.claude/memory/PLAN.md` | done — `fb870bd` |
| AJ2 | Isolar os dois testes da dependência de ffmpeg via `monkeypatch`. | executor | `enhance/test_output_dir_and_pipeline_tag.py` | done — `658598a` |
| AJ3 | Confirmar verde no CI real (não local) e fechar o ciclo. | executor | `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md` | done — `fb449d2` |

## Notas de execução

- Não tocar em `Reels_Encoder_v2_FINAL.py`. Não instalar ffmpeg no CI.
- Localizar por âncora (nome de função), não por número de linha — os
  números citados são do commit `3f12070` e vão deslocar.
- Baseline do achado, medido no CI real (run `32590519448`, SHA `3f12070`,
  job "Tests (ubuntu-latest, Python 3.11)"): `2 failed, 423 passed` na
  suíte inteira. Baseline local, medido sob PATH sem ffmpeg em `fb870bd`,
  arquivo `enhance/test_output_dir_and_pipeline_tag.py` isolado: `2 failed,
  9 passed`. Meta: `425 passed` na suíte completa — atingida no CI real
  (run `32870623915`).
- **Não fechar o ciclo com base em execução local.** O achado inteiro
  nasceu de uma suíte verde localmente e vermelha no CI real — a prova de
  fechamento (AJ3) exige log real do CI, não apenas `pytest` local.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
