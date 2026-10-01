<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P3A: canal Encoder → TUI (Reporter seam, B-4)

Data: 2026-09-30 | Ciclo: P3A | Origem: Phase 2 Sign-off, blocker B-4. Spec aprovada pelo usuário.
Ciclo anterior: P2-B3 (protótipo Ctrl+C, verificado T1–T5).

- Spec: `docs/superpowers/specs/2026-09-30-tui-reporter-seam-design.md`
- Plano detalhado (passos, código, testes): `docs/superpowers/plans/2026-09-30-tui-reporter-seam.md`

O executor lê os dois inteiros antes da sua tarefa e executa **só** a Task indicada, na ordem.

## Tarefas

| ID | agente alvo | Task do plano | arquivo(s) | aceite |
|----|-------------|---------------|------------|--------|
| P3A-1 | executor | Task 1 (+ Step 0 branch/baseline) | `reporter.py`, `ui/test_reporter.py` | 7 testes verdes; baseline registrado |
| P3A-2 | executor | Task 2 | `enhance/test_classic_golden.py`, `enhance/golden/*.json` | goldens gravados no HEAD sem mudança no encoder; 3 execuções estáveis |
| P3A-3 | executor-pesado | Task 3 | `Reels_Encoder_v2_FINAL.py`, `enhance/test_reporter_events.py` | eventos native verdes; 4 goldens intactos |
| P3A-4 | executor-pesado | Task 4 | `Reels_Encoder_v2_FINAL.py`, `enhance/test_reporter_events.py` | eventos Cineon verdes; goldens intactos |
| P3A-5 | executor | Task 5 | `ui/tui_capture.py`, `ui/test_tui_capture.py` | 5 testes verdes |
| P3A-6 | executor-pesado | Task 6 | `ui/tui_driver.py`, `ui/test_tui_driver.py` | todos os testes single verdes |
| P3A-7 | executor-pesado | Task 7 | `ui/tui_driver.py`, `ui/test_tui_driver.py` | todos os testes batch verdes |
| P3A-8 | executor | Task 8 | `ui/test_tui_parity.py` | argv e hash idênticos nos 4 cenários |
| P3A-9 | executor + usuário | Task 9 | scratchpad `b4\` | roteiro rodado pelo usuário; resultado em VALIDATION.md |
| P3A-10 | Orquestrador | Task 10 | `.claude/memory/*` | suíte + ruff; Sign-off atualizado |

## Notas de execução

- **Branch:** `claude/ciclo-p3a-reporter-seam` (criada no Step 0 da Task 1, a partir de `main`). Sem push — Orquestrador faz na P3A-10 com pedido do usuário.
- **Python:** `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`. FFmpeg: `./bin/ffmpeg.exe`.
- **Commits:** um por Task, mensagem do plano, terminando com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01EpBjK17wXCdV8UhXbMm19r`.
- **Nunca `git add -A`/`.`**; não commitar `docs/*.md` não rastreados, `videos/`, `enhance_maps/`, `__pycache__`, nem a exclusão pendente de `docs/terminal-ui-masterplan.md` (é do usuário).
- STATE.md: anexar `## Ciclo P3A` com `ID | done ou blocked | arquivo | resultado em 1 linha`; saída vermelha pré-fix em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.

---

## Addendum P3A-11 — goldens com impressão digital do ambiente (2026-10-01)

Origem: CI do PR #70 (run 36816965586) — 4 falhas no ubuntu (3.12) e 3 (3.11), todas em `enhance/test_classic_golden.py`:
console `Stream: N×N @ N/N fps` vs `N fps` (ffprobe apt 6.1.1 entrega fps fracionário), banner/opções do libx264 do Debian
reformatados, e argv `aq-strength=0.59` vs `0.6` (cineon_2pass, só 3.11). Causa raiz: golden compara contra um build
específico de FFmpeg/libx264 (local BtbN n6.1.3), não só contra o nosso código. Paridade (`ui/test_tui_parity.py`, mesmo
ambiente) passou no CI. Decisão do usuário: opção 1.

| ID | agente alvo | arquivo(s) | o quê | aceite |
|----|-------------|------------|-------|--------|
| P3A-11 | executor | `enhance/test_classic_golden.py`, `enhance/golden/classic_*.json` | (a) `_env_fingerprint() -> dict` com `ffmpeg` (1ª linha de `<RE.FFMPEG> -version`), `python` (`"3.X"`), `numpy` (`numpy.__version__` ou `None`); (b) função pura `_env_mismatch(recorded: dict \| None, current: dict) -> str \| None` que devolve o motivo (lista das chaves divergentes com os dois valores) ou `None`; golden sem `env` conta como divergente; (c) modo `REELS_UPDATE_GOLDEN=1` grava `{"env", "argv", "console"}`; (d) na comparação, se `_env_mismatch` não for `None` → `pytest.skip(f"golden gravado em outro ambiente: {motivo}")`, senão asserts estritos como hoje; (e) regravar os 4 goldens localmente | TDD: teste unitário de `_env_mismatch` (igual → None; uma chave diferente → motivo cita a chave; `None` gravado → divergente) vermelho antes/verde depois; ao regravar, `argv` e `console` dos 4 JSON **idênticos** aos commitados em 225ecb2 (só entra a chave `env`) — provar com diff; golden passa local 4/4; com fingerprint forçado diferente (monkeypatch) os 4 pulam com o motivo |

Notas: branch `claude/ciclo-p3a-reporter-seam` (PR #70 aberto; não trocar de branch). Não mexer em `run_classic` nem em outros
testes. Commit `test(golden): pular golden quando o ambiente difere do gravado` + trailers do ciclo. Push pelo Orquestrador.
STATE.md: anexar linha P3A-11. Retorno: ponteiro + veredito.
