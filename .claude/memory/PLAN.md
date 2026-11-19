<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — L2F4: painel SYSTEM da TUI indica ffplay ausente apesar de resolvível

Data: 2026-11-18 | Branch: `fix/l2f4-ffplay-status` (base `2de77bd` = `origin/main`). Agente alvo: **`executor`**.

Origem: `FINDINGS.md` L2F4. Causa confirmada pelo Orquestrador: `ui/tui/app.py` `App._system_rows` (l.108-117) calcula `has_ffplay` só com `shutil.which("ffplay")` ou `ffplay[.exe]` ao lado de `RE.FFMPEG`; ignora `REELS_FFPLAY` e `bin\`, que `ui.binaries.available("ffplay")` considera (é o que `ebu_meter._FFPLAY_OK` usa). `shutil` é usado em `app.py` só nessa linha.

## Regras

- **Sem commit/push/`git add`/merge.** Sem `reset`, `clean`, `stash`, `restore`, `checkout --` em arquivo que você não criou. Branch atual: `fix/l2f4-ffplay-status`; não trocar.
- Há alteração não commitada só neste `PLAN.md`. Arquivos permitidos: `ui/tui/app.py`, `ui/tui/test_system_rows.py` (novo), `.claude/memory/STATE.md` (só append), `.claude/memory/FINDINGS.md` (só a linha L2F4, coluna de status). Fora do escopo: `ebu_meter.py`, `ui/binaries.py`, pipeline, `launcher.*`, a precedência do resolvedor, N-1.
- Sem downloads, sem instalações, sem rede, sem subprocesso novo, sem reprodução de áudio. Sem comentário narrativo.
- ffplay segue **opcional**: o texto do painel, o rótulo "ffplay" e a ordem das 4 linhas não mudam.

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| L2F4-1 | `ui/tui/test_system_rows.py` (novo) | Escrever os testes **antes** da correção e registrar o vermelho em STATE.md. Chamar `A.App._system_rows()` (staticmethod, `from ui.tui import app as A`) e verificar `dict(rows)["ffplay"]`: `"ok"` quando disponível, começando com `"⚠ ausente"` quando não. Isolamento por `monkeypatch`, **resolvedor real** (sem trocar `available`/`which`): `monkeypatch.setattr("ui.binaries._proj_dir", lambda: str(tmp_path))` (aponta `bin\` para a pasta temporária), `monkeypatch.setenv("PATH", <pasta temporária controlada>)`, `monkeypatch.delenv("REELS_FFPLAY", raising=False)` (e `REELS_FFMPEG`/`REELS_FFPROBE`), `monkeypatch.chdir(tmp_path)`, e `monkeypatch.setattr(RE, "FFMPEG", <caminho do ffmpeg falso numa pasta do PATH temporário, sem ffplay ao lado>)` para reproduzir "FFmpeg no PATH". Arquivos falsos com `write_text("x")`, nome `ffplay.exe` se `os.name == "nt"` senão `ffplay` com `chmod 0o755` (padrão de `ui/test_binaries.py::_ext`). Casos: (1) FFmpeg no PATH (pasta sem ffplay) e ffplay somente em `tmp/bin/` → `ok`; (2) ffplay só via `REELS_FFPLAY` apontando para arquivo existente fora de `bin\` e do PATH → `ok`; (3) ffplay somente numa pasta do PATH (e nenhum em `bin\`) → `ok`; (4) realmente ausente (PATH = pasta vazia, `bin\` vazio, sem env) → começa com `⚠ ausente` e contém `monitor EBU desligado`; (5) caminho com espaços: pasta `"pasta com espaco"` usada para o ffplay em `bin\` e também para `REELS_FFPLAY` e para o PATH (três variações parametrizadas) → `ok`; (6) as linhas FFmpeg/ffprobe/hardware continuam as mesmas (`os.path.basename(RE.FFMPEG)`, `os.path.basename(RE.FFPROBE)`, `"detectado no início do encode"`) e a ordem das 4 chaves é `FFmpeg, ffprobe, ffplay, hardware`. Não depender do ffplay/FFmpeg globais nem de `bin\` do checkout. |
| L2F4-2 | `ui/tui/app.py` | Correção mínima: em `_system_rows`, `has_ffplay = available("ffplay")` com `from ui.binaries import available` adicionado aos imports (ordem alfabética existente: junto de `from ui import tui_driver as D`/`from ui.config ...`), removendo a variável `side` e o `import shutil` (agora sem uso — conferir por grep antes). Não mudar o texto das linhas. |
| L2F4-3 | — | Em **foreground**, com `venv\Scripts\python.exe`: (a) antes da correção, `python -m pytest ui/tui/test_system_rows.py -v --timeout=60` e registrar quais falham; (b) depois, o mesmo arquivo (esperado 100% verde); (c) `python -m pytest ui/tui/ ui/test_binaries.py ui/test_preflight.py ui/test_tui_driver.py -q --timeout=60`; (d) `python -m ruff check ui/tui/app.py ui/tui/test_system_rows.py` e `python -m ruff check .` (se o CI usa o projeto todo; ver `.github/workflows/ci.yml` job Lint e use o mesmo comando); (e) a suíte do job `Tests` do CI (`python -m pytest test_render_queue.py enhance/ ui/ tools/ -v --timeout=60`); (f) `git diff --check`. Números reais, sem presumir. |
| L2F4-4 | `.claude/memory/STATE.md`, `.claude/memory/FINDINGS.md` | STATE: append `## L2F4 — ffplay no painel SYSTEM (2026-11-18)` (status por ID, vermelho por caso, verde, números dos comandos acima). **Append em bytes/ao final**: o arquivo tem um byte não UTF-8 legado e CRLF; não regravar o arquivo inteiro nem converter encoding. FINDINGS: na linha L2F4, trocar só a coluna de status `aberto` por `corrigido na branch fix/l2f4-ffplay-status; aguarda integração`, preservando CRLF e o resto da linha (edição por bytes, uma ocorrência verificada). |

## Retorno

Ponteiro + veredito: status por ID, uma linha cada; detalhe em `.claude/memory/STATE.md` § L2F4. Listar arquivos tocados e qualquer limitação.
