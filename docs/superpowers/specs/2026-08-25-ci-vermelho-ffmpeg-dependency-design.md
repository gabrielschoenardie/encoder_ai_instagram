# CI Vermelho — Isolar os Testes de --output-dir da Dependência de FFmpeg — design

**Date:** 2026-08-25
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

`main` está com o CI vermelho desde o Ciclo AG, registrado em
`.claude/memory/FINDINGS.md` como `AIF1` (Ciclo AI). Confirmado no log real
do job "Tests (ubuntu-latest, Python 3.11)" do run `32590519448`
(SHA `3f12070`): `2 failed, 423 passed in 3.07s`, ambas `assert 1 == 0`. Os
dois testes de `enhance/test_output_dir_and_pipeline_tag.py` chamam
`main()` de ponta a ponta com `--batch` para validar comportamento do
parser, mas o caminho atravessa a checagem de dependência do ffmpeg em
`Reels_Encoder_v2_FINAL.py:4399-4414` antes de chegar lá. Nenhum runner do
GitHub Actions vem com ffmpeg pré-instalado, e o `ci.yml` não o instala.

## Non-goals / constraints

- **Não tocar em `Reels_Encoder_v2_FINAL.py`.** A ordem de checagem
  (dependência antes de escaneamento de pasta) é intencional e correta;
  mudar isso para acomodar um teste seria inverter causa e efeito.
- **Não instalar ffmpeg no runner do CI.** Isso mascararia o problema real
  (os testes não deveriam precisar de um binário externo para validar
  lógica de parser) e adicionaria minutos a cada execução de CI para todos
  os jobs.
- **Localizar por âncora, não por número de linha.** Os números citados são
  do commit `3f12070` e vão deslocar.
- **Baseline a preservar:** localmente, sem ffmpeg no PATH: `2 failed, 423
  passed` em `enhance/` (isolado). Meta ao final: `425 passed` na suíte
  completa, sem regressão.

## Architecture

A correção fica inteiramente no arquivo de teste. **Por que consertar o
teste e não o produto:** a ordem de checagem em `main()` é intencional —
falhar rápido numa dependência ausente é melhor UX do que só descobrir
isso depois de escanear arquivos de batch. O defeito é o teste ter escopo
maior do que precisa: ele testa uma decisão de parser (`--output-dir` sem
`--batch` dispara `parser.error()`), mas para isso exercita `main()`
inteiro, o que arrasta consigo a checagem de dependência de ffmpeg que não
tem relação com o que está sendo validado. A correção usa `monkeypatch` —
convenção já estabelecida no repo (`ui/test_launcher.py`,
`enhance/test_cineon_constants_guard.py`,
`enhance/test_hdr_pipeline.py`) — para neutralizar a checagem de
dependência apenas nesses dois testes, sem tocar em produto.

## Riscos conhecidos

- Ambientes locais com ffmpeg no PATH não reproduzem a falha — a única
  evidência confiável de que o CI está vermelho é o log real do run, não a
  execução local. O mesmo vale para a prova de que a correção funciona: a
  suíte local pode passar mesmo com o teste ainda acoplado a ffmpeg
  instalado, mascarando a regressão.
- `monkeypatch.setattr` mira `ui.preflight.missing_ffmpeg_binaries` no
  módulo de origem, não em `Reels_Encoder_v2_FINAL`; funciona porque o
  `import` local dentro de `main()` resolve o nome no namespace de
  `ui.preflight` no momento da chamada.

## Validação

- `python -m pytest enhance/test_output_dir_and_pipeline_tag.py -v` →
  `11 passed`, zero failed, localmente sem ffmpeg no PATH.
- `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → sem
  regressão fora do escopo deste ciclo.
- CI real (não execução local): os 4 jobs `Tests` (ubuntu×windows,
  3.11×3.12) do run mais recente `success`, com a linha de sumário final
  colada literalmente em `STATE.md`.
