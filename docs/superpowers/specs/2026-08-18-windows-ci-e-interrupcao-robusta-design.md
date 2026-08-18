# Windows no CI e Interrupção Robusta — design

**Date:** 2026-08-18
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

Fechar o ponto cego de Windows do projeto e blindar o `--batch` contra
interrupção durante a escrita do ffmpeg, registrados em
`.claude/memory/FINDINGS.md` como `ABF1`/`ABF2`/`ABF3` (Ciclo AC) e `YF1`
(Ciclo AD, residual do Ciclo Y):

- **ABF1** — nenhum job de Python roda em Windows; 4 falhas conhecidas
  ficam invisíveis ao CI, observáveis só à mão.
- **ABF2** — `pytest enhance/ ui/` não alcança `test_render_queue.py`, na
  raiz do repo; os 23 testes da fila nunca rodaram em CI, em plataforma
  alguma.
- **ABF3** — `ruff check enhance/` cobre só uma das cinco áreas do repo
  (engine, `ui/`, `render_queue.py`, `tools/` ficam sem lint). Registrado
  e **adiado deliberadamente** neste ciclo.
- **YF1** — no Windows, uma interrupção durante a escrita do `.mp4` deixa
  o ffmpeg órfão segurando o handle do arquivo; a remoção do output
  parcial falha em silêncio e a execução seguinte promove o arquivo
  truncado a `○ pulado`.

## Non-goals / constraints

- **`main` nunca fica vermelha.** A perna Windows entra
  `continue-on-error: true` e só vira bloqueante depois de comprovadamente
  verde (Task 5 do plano).
- **Não "consertar" teste mascarando o sintoma.** Falha causada por
  código que assume separador/encoding de POSIX corrige-se no código, não
  no teste. `skipif` só é aceitável para comportamento genuinamente
  específico de POSIX, com justificativa registrada em `FINDINGS.md`.
- **Não alargar o `ruff` neste ciclo.** `ABF3` fica registrado e adiado;
  o escopo atual (`enhance/`) permanece intocado.
- **Ciclo AD não altera o caminho feliz.** Nenhuma mudança observável num
  encode que termina normalmente; `terminate()` só dispara sob
  `KeyboardInterrupt`.
- **`discard_partial_output` continua sem levantar.** O
  `except OSError: return False` é decisão preexistente do Ciclo Y; o que
  falta é o `terminate()` antes e o aviso visível depois.
- **Baseline a preservar:** `python -m pytest test_render_queue.py
  enhance/ ui/ -q` → `392 passed` em Linux (fora as 4 falhas nominais de
  Windows, que este ciclo existe para expor e corrigir).

## Architecture

**Por que a perna Windows entra não-bloqueante primeiro.** A lista real de
falhas em Windows é desconhecida — a lista de "4 falhas" que circulava
veio de uma execução manual obsoleta, nunca verificada em CI. Entrar
bloqueante de cara deixaria `main` vermelha por tempo indeterminado até
a causa raiz de cada falha ser encontrada, recriando exatamente a
normalização de falha vermelha que o projeto vinha eliminando em Linux
(Ciclo Y). A sequência correta é: (1) rodar a matriz em Windows sem
bloquear nada, só para colher evidência real; (2) corrigir o que a
evidência mostrar; (3) só então remover o escape e tornar a perna
bloqueante — nunca acreditar em "baseline nominal" sem prova em CI.

**Por que o Ciclo AD depende do Ciclo AC.** O `YF1` é um bug de
subprocesso **específico de Windows** — o ffmpeg segura o handle do
arquivo de saída até terminar de escrever, e só o comportamento do
`Popen`/`terminate()` nesse SO expõe o defeito. Sem um job de Python
rodando em Windows no CI, não há como provar a correção onde o bug
existe: a evidência ficaria presa na máquina de um desenvolvedor,
repetindo o mesmo problema estrutural que produziu o `ABF1` (correção
sem verificação automatizada na plataforma de produção). Por isso o
plano ordena os dois ciclos em sequência e proíbe iniciar o AD antes do
AC estar fechado e mergeado.

**Mecanismo do fix do YF1.** Registrar o `Popen` do ffmpeg ativo no
engine (ponto onde o subprocesso nasce), permitindo `terminate()` a partir
do handler de `KeyboardInterrupt`, e endurecer
`discard_partial_output` com retentativa (o handle pode levar alguns ciclos
para ser liberado pelo SO mesmo após o `terminate()`). Segue o idioma de
injeção por argumento default já usado em `ui/binaries.py`
(`resolve_binary(name, which=shutil.which, ...)`), o que torna a lógica
testável sem `monkeypatch`.

## Riscos conhecidos

- Os runners `windows-latest` do GitHub Actions não têm ffmpeg instalado
  por padrão — testes que dependam de invocar o binário real vão falhar
  por um motivo **diferente** do investigado (`FileNotFoundError`), e
  precisam ser distinguidos das falhas genuínas de comportamento antes de
  qualquer correção.
- O encoding padrão do console em Windows é cp1252 (não UTF-8), o que
  quebra asserções sobre glifos Unicode usados no tema/UI — precisa de
  tratamento explícito, não `skipif` cego.
- `os.path.sep` (`\` em vez de `/`) e terminadores de linha `\r\n` (em vez
  de `\n`) quebram asserções literais sobre caminhos e sobre texto
  multi-linha capturado de subprocessos ou de `Console(file=...)`.

## Validação

- `python -m pytest test_render_queue.py enhance/ ui/ -q` → `392 passed`
  em Linux, sem regressão, ao final de cada task do Ciclo AC/AD.
- CI: job `tests` rodando as duas plataformas (`ubuntu-latest`,
  `windows-latest`) × duas versões de Python, com a perna Windows
  primeiro `continue-on-error`, depois bloqueante.
- Smoke test real em Windows, dentro da janela medida do Ciclo Y
  (t≈113s–135s de um job de ~140s), confirmando: nenhum processo ffmpeg
  órfão após a saída do Python; arquivo parcial removido (ou aviso
  vermelho impresso quando não); execução seguinte refaz o job
  interrompido, nunca `○ pulado`.
