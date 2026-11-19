<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — R03F2: linhas longas do STDERR cortadas com "…" na tela ERROR

Data: 2026-11-19 | Branch: `fix/r03f2-error-stderr-wrap` (base `8f09f2d` = `origin/main`). Agente alvo: **`executor`**.

Origem: `FINDINGS.md` R03F2. Causa confirmada pelo Orquestrador: `ui/tui/screens.py` `_error` desenha cada linha de `S.stderr_lines(...)` com `Text(ln, overflow="ellipsis", no_wrap=True)` dentro de `panel(body, "FFMPEG STDERR", height=rows + 2)`; a causa real de uma falha (ex.: `Error opening output file <caminho>: Permission denied`) fica cortada. O limite de rolagem em `ui/tui/state.py` (tecla UP/DOWN com `screen == ERROR`, ~l. 746) conta linhas lógicas (`len(stderr_lines(...))`).

## Regras

- **Sem commit/push/`git add`/merge.** Sem `reset`, `clean`, `stash`, `restore`, `checkout --` em arquivo que você não criou. Branch atual: `fix/r03f2-error-stderr-wrap`; não trocar.
- Arquivos permitidos: `ui/tui/state.py`, `ui/tui/screens.py`, testes em `ui/tui/` (arquivo novo `ui/tui/test_error_stderr_wrap.py`; ajustar testes existentes só se a mudança exigir, e dizer quais), `.claude/memory/STATE.md` (só append) e `.claude/memory/FINDINGS.md` (só a linha R03F2, coluna de status).
- **Fora do escopo (não tocar):** painel LOG / `log_rows` (o truncamento do LOG permanece), motor, `ui/tui_driver.py`, código de saída, preflight, R03F5, launcher, N-1, o cartão `error_card`/`error_lines` (mensagem de cabeçalho). Se precisar ampliar, **pare e escreva `blocked` em STATE.md** com a necessidade.
- Sem downloads, sem rede, sem subprocesso novo. Sem comentário narrativo.
- Sem dependência circular: o cálculo vive em `state.py` (que já importa `textwrap`, `reporter`, `forms`, `widgets`; `screens.py` já importa `state as S`). `rich` 15.0.0 está no venv; `rich.cells.cell_len` e `rich.cells.chop_cells` existem.

## Contrato

1. **Uma só fonte das linhas visuais** em `state.py`: uma função pura (ex.: `stderr_visual_lines(s)` ou `(err, log, width)`) que parte de `stderr_lines(err, log)` (inalterada: continua filtrando linhas em branco, decodificando bytes e usando o fallback do LOG) e quebra cada linha lógica pela **largura útil real do painel em células** (não em caracteres): `rich.cells.chop_cells` após `expandtabs` (é o que o `Text` do Rich faria). Linha curta → 1 linha visual idêntica; ordem e conteúdo preservados; sem `strip`, sem hifenização, sem perda de espaços iniciais. Largura útil = `s.size[0]` menos as 2 colunas da borda do painel menos o padding horizontal padrão do `Panel` (1 por lado); **confirme empiricamente** renderizando um painel de teste (não chute o 4) e fixe a constante/função de largura em `state.py`, usada por **ambos** (estado e tela). Mínimo 10 colunas.
2. **Renderização** em `_error` (layouts cheio e compacto) usa essas linhas visuais, cada uma como `Text(ln, no_wrap=True, overflow="crop")` — texto **literal**, sem markup (colchetes como `[red]` aparecem como estão). Sem `…` por truncamento.
3. **Rolagem**: o teto da rolagem (`top`) usa `len(linhas_visuais) - error_rows(s)` com o mesmo cálculo; UP/DOWN existentes inalterados. Em `_tick` (resize), quando `s.screen == ERROR`, reclampar `error_scroll` ao novo teto (a janela já é clampada no render; o estado também deve ficar válido). Posição de rolagem nunca negativa nem acima do teto.
4. `error_rows`, `ERROR_ROWS`, alturas dos painéis e o `assert_fits` das telas não mudam: o painel tem a mesma altura; só mudam as linhas que cabem nele.

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| R03F2-1 | `ui/tui/test_error_stderr_wrap.py` (novo) | Escrever os testes **antes** da correção e registrar o vermelho em STATE.md (quais falham). Usar `test_screens.py`/`test_screens_compact.py` como modelo (`text_of`, `assert_fits`, `error_state`, `_tick`, `_down`). Casos, em **80×24 e 120×40**: (a) STDERR com uma linha longa contendo caminho com espaços e terminando em `Permission denied` → o texto aparece **completo** nas linhas visuais renderizadas (reconstruir juntando as linhas visuais, com o scroll no fim e percorrendo toda a janela), sem `…`; (b) texto com colchetes (`[red]x[/red] [bold]`) e largura variável (acentos, CJK como `映像`, combinante) → idêntico ao original, sem interpretação de markup e nenhuma linha visual excede a largura útil em células (`cell_len`); (c) linhas curtas, ordem e conteúdo inalterados; (d) `assert_fits` na saída renderizada; (e) rolagem: DOWN repetido alcança a última linha visual e não passa do teto; UP volta a 0 e não fica negativo; (f) resize 120×40 → 80×24 e 80×24 → 120×40 com a rolagem no fim: `error_scroll` válido (0 ≤ x ≤ teto novo) e a última linha visual visível; (g) o estado e a tela usam a mesma função (teto = `len(visual) - error_rows`); (h) stderr em `bytes` e `None` continuam funcionando. |
| R03F2-2 | `ui/tui/state.py`, `ui/tui/screens.py` | Implementar o contrato acima, mínimo. |
| R03F2-3 | — | Foreground, `venv\Scripts\python.exe`: (a) antes da correção: `python -m pytest ui/tui/test_error_stderr_wrap.py -v --timeout=60`, registrar quais falham; (b) depois: o mesmo (esperado verde); (c) `python -m pytest ui/tui/ -q --timeout=60`; (d) o comando do job Lint do CI (`ruff check .`, ver `.github/workflows/ci.yml`); (e) a suíte do job Tests do CI (`python -m pytest test_render_queue.py enhance/ ui/ tools/ -v --timeout=60`); (f) `git diff --check`. Números reais, sem presumir. |
| R03F2-4 | `.claude/memory/STATE.md`, `.claude/memory/FINDINGS.md` | STATE: append `## R03F2 — STDERR na tela ERROR (2026-11-19)` (status por ID, vermelho, verde, números). **Append em bytes/ao final** (byte não UTF-8 legado, CRLF; não regravar o arquivo nem converter encoding; sem barras invertidas via literais Python não-raw: use `chr(92)`). FINDINGS: na linha R03F2, trocar só o status `aberto — Orquestrador` por `corrigido na branch fix/r03f2-error-stderr-wrap (somente a tela ERROR; o truncamento no LOG permanece aberto); aguarda integração`, preservando CRLF e o resto da linha (uma ocorrência verificada). |

## Retorno

Ponteiro + veredito: status por ID, uma linha cada; detalhe em `.claude/memory/STATE.md` § R03F2. Listar arquivos tocados e qualquer limitação.
