<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AC: Windows e a fila de render entram no CI (ABF1/ABF2)

Data: 2026-08-18 | Ciclo: AC | Origem: `docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md` (CICLO AC, Tasks 1–5) + `docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md` + `.claude/memory/FINDINGS.md` § `ABF1`/`ABF2`/`ABF3`.

## Diagnóstico

`.github/workflows/ci.yml` tem um job `tests` `runs-on: ubuntu-latest`
que roda `pytest enhance/ ui/ -v --timeout=60` — nem toca Windows (`ABF1`)
nem alcança `test_render_queue.py`, que mora na raiz do repo com 23
testes da fila de render nunca executados em CI, plataforma alguma
(`ABF2`). O job `lint` roda `ruff check enhance/` apenas, deixando
engine/`ui/`/`render_queue.py`/`tools/` sem lint (`ABF3`, adiado
deliberadamente). Este ciclo corrige `ABF1`+`ABF2`; `ABF3` fica aberto
para ciclo futuro. O Ciclo AD (interrupção robusta, `YF1`) depende deste
ciclo estar fechado e mergeado — sem job de Python em Windows no CI não
há como provar a correção do `YF1` na plataforma onde o bug existe.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AC1 | Registrar os achados `ABF1`/`ABF2`/`ABF3` em `FINDINGS.md`, escrever o spec do ciclo, salvar o plano completo em `docs/superpowers/plans/`, e (re)escrever este `PLAN.md` para o Ciclo AC. Espelha a Task 1 do plano. | `executor` | `docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md`, `docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md`, `.claude/memory/FINDINGS.md`, `.claude/memory/PLAN.md` | **done** — os 3 greps do Step 1 da Task 1 confirmam os achados; spec e plano criados; `FINDINGS.md` com a seção nova; commit feito |
| AC2 | Ampliar o alvo do `pytest` do job `tests` para incluir `test_render_queue.py` (`ABF2`). Espelha a Task 2. | `executor` | `.github/workflows/ci.yml` | **done** — `pytest test_render_queue.py enhance/ ui/ -q --collect-only` coleta exatamente +23 testes vs. `pytest enhance/ ui/ -q --collect-only`; commit feito |
| AC3 | Converter o job `tests` para matriz de SO (`ubuntu-latest`, `windows-latest`), perna Windows `continue-on-error: true`, `fail-fast: false`; corrigir steps acoplados a shell POSIX; colher no CI a lista real de falhas em Windows e registrar em `STATE.md`. Espelha a Task 3. | `executor` | `.github/workflows/ci.yml`, `.claude/memory/STATE.md` | **done**, commits `618b5f9`/`20f0967`/`2fbd858` — matriz aplicada; lista real de `FAILED` colhida do run `32159250931` (PR #41, aberto só para disparar o CI, não mergear) e colada literalmente em `STATE.md` § "Ciclo AC — Task 3 (Steps 1-3) — 2026-08-18" § "Step 4 — lista real de falhas": mesmas 4 falhas em Python 3.11 e 3.12, batendo exatamente com as "4 falhas nominais" relatadas à mão |
| AC4 | Corrigir as falhas reais de Windows colhidas pela AC3, uma categoria por commit (bug real de produto vs. teste acoplado a POSIX vs. ausência de ffmpeg no runner vs. genuinamente só-POSIX), com `skipif` sempre justificado em `FINDINGS.md`. Espelha a Task 4. | `executor-pesado` | a determinar pela AC3 (provavelmente `enhance/`, `ui/`), `.claude/memory/FINDINGS.md` | **done** — `python -m pytest test_render_queue.py enhance/ ui/ -q` continua `392 passed` em Linux; zero `skipif` concedido (as 4 falhas foram corrigidas de verdade); as duas pernas Windows do CI em `success` no run `32166523153` |
| AC5 | Remover o `continue-on-error` da perna Windows (só depois de verde), fechar o ciclo: `STATE.md` com evidência dos jobs verdes, `PLAN.md` com AC1..AC5 `done` + sha, `FINDINGS.md` marcando `ABF1`/`ABF2` corrigidos e `ABF3` mantido aberto/adiado. Espelha a Task 5. | `executor` | `.github/workflows/ci.yml`, `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md` | **done**, commit `cc0e99c` — `continue-on-error` e o comentário de justificativa removidos do job `tests`; evidência de que a perna Windows já era `success` (run `32166523153`) registrada em `STATE.md`; confirmação final "bloqueante e verde" pós-push fica para o Orquestrador (ver nota em `STATE.md`) |

## Notas de execução

- **`main` nunca fica vermelha.** A perna Windows só vira bloqueante na
  AC5, depois de comprovadamente verde. Até lá, `continue-on-error: true`.
- **Não mascarar sintoma com `skipif`.** Corrigir código quando o bug é
  real (assume separador/encoding POSIX); `skipif` só para comportamento
  genuinamente específico de POSIX, sempre com justificativa em
  `FINDINGS.md`.
- **Não alargar o `ruff` neste ciclo.** `ABF3` fica registrado e adiado —
  candidato natural ao próximo ciclo.
- **Localizar por âncora, não por número de linha** — os números do
  plano-fonte são de um commit específico e vão deslocar.
- Baseline a preservar: `python -m pytest test_render_queue.py enhance/
  ui/ -q` → `392 passed` em Linux, fora as 4 falhas nominais de Windows
  que este ciclo existe para expor e corrigir.
- AC1 é pré-requisito de tudo; AC2 pode rodar em seguida (achado mais
  barato, maior retorno); AC3→AC4→AC5 são sequenciais (cada uma consome a
  evidência da anterior).
- Retorno do agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
