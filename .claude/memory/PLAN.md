<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — R-03: layout compacto 80×24 (tui-review.md)

Data: 2026-11-17 | Branch: `fix/tui-review-r03-polish` (base `7920e07` = `origin/main`). Agente alvo: **`executor-pesado`**.

Origem: `tui-review.md` § R-03, § 3 prioridade 2, § 4 critério de aceite R-03, § 5.2. Decisão travada pelo usuário: **mínimo 80×24**; estratégia escolhida: **layout compacto por tela** (não rolagem genérica, não voltar a 120×40).

## Regras

- **Sem commit/push/`git add`.** Sem `reset --hard`, `clean`, `stash`, `restore` em arquivo que você não criou.
- Pendências preexistentes não são suas: `.claude/memory/VALIDATION.md` (M), `docs/terminal-ui-masterplan.md` (D), `Reels_Encoder_AI.ico`, `docs/*.md` e `tui-review.md` não rastreados.
- Arquivos permitidos: `ui/tui/state.py`, `ui/tui/screens.py`, `ui/tui/widgets.py`, `ui/tui/__main__.py`, testes em `ui/tui/test_*.py`, e `tests/screens/` (só capturas). Nada no motor, launcher, `ui/tui_driver.py`.
- Sem refactor paralelo, sem feature nova, sem comentário narrativo. N-1 (`_temp_path`) **fora** — não tocar.
- Ambíguo → `blocked` com a pergunta exata em STATE.md.

## Comportamento alvo

| tamanho | comportamento |
| --- | --- |
| ≥ 120×40 | **idêntico a hoje** (byte a byte no render; a suíte existente é a guarda de regressão) |
| 80×24 ≤ tamanho < 120×40 | **layout compacto**: toda tela cabe sem corte, foco visível, rodapé de teclas inteiro na última área, navegação por teclas funciona |
| < 80×24 | fallback `_small` com mínimo **80×24** na mensagem; teclas ignoradas fora de encode (como hoje); durante encode mostra "o encode continua rodando" e Ctrl+C continua funcionando |

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| R03-1 | `ui/tui/state.py` | Separar constantes: `MIN_SIZE = (80, 24)` (gate de `too_small` e mensagem do `_small`) e `FULL_SIZE = (120, 40)` (default de `UIState.size` e limiar compacto/completo). Default de `size` passa a `FULL_SIZE` para não mudar os testes existentes. `FALLBACK_SIZE` continua (80,24) — se ficar redundante com `MIN_SIZE`, `__main__.terminal_ok` passa a usar `MIN_SIZE` e `FALLBACK_SIZE` só se ainda tiver outro uso. Helper `compact(s) -> bool` (`size` abaixo de `FULL_SIZE` em qualquer eixo). |
| R03-2 | `ui/tui/state.py` | Limites de rolagem dependentes da altura: `REPORT_ROWS` (21) e `ERROR_ROWS` (17) usados no clamp de `queue_scroll`/`error_scroll` (`:705`, `:717`) devem vir de função da altura disponível (ex.: `report_rows(s)`, `error_rows(s)`), igual ao que o renderer usa — senão o item focado/final some no compacto. Em ≥120×40 os valores continuam 21/17. |
| R03-3 | `ui/tui/screens.py` | `render()`: em compacto, cabeçalho de **1 linha** (título + tela atual; sem a faixa de abas ou abas abreviadas em 1 linha) e rodapé de **1 linha**; corpo = `h − header − footer`, não `size=34` fixo. Em ≥120×40 mantém 3/34/3. |
| R03-4 | `ui/tui/screens.py` | Variante compacta de **cada** renderer em `SCREEN_RENDERERS` (HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW, READY, ENCODING, DETAILS, LOG, QC, COMPLETED, ERROR, CANCELLED, QUEUE, REPORT): remover banners/linhas em branco decorativas, empilhar painéis lado a lado quando não couberem em 80 col, reduzir `height=` fixos (ver `:242,256,272,289,388,403,421,430,473–511,597,633,702,711,718–719,739`). Conteúdo funcional (campos, foco, valores, ações finais, chips de QC, tabela EBU, log/erro com rolagem) tem que continuar visível. `QUEUE_ROWS`/`REPORT_ROWS`/linhas de LOG/ERROR derivam da altura. Preferir parametrizar por `compact(s)` dentro do renderer existente a duplicar a tela inteira. |
| R03-5 | `ui/tui/screens.py` | Rodapé: toda string de teclas (`FOOTER_KEYS`, `SOURCE_TIPO_KEYS`, `CONFIG_BATCH_KEYS` = 115 col, e as montadas dinamicamente) tem que caber em **uma linha de 80 col** no compacto — versão curta das legendas (ex.: `[↑↓] Campo [←→] On/Off [ENTER] Próx [ESC] Voltar [^C] Sair`) ou `no_wrap` + `overflow="ellipsis"` como rede de segurança. Não trocar idioma/rótulos aqui (isso é R-13). |
| R03-6 | `ui/tui/screens.py` | `_small`: mensagem cita `MIN_SIZE` (80×24). |
| R03-7 | `ui/tui/__main__.py` | Guarda e ajuda/erro coerentes com 80×24 (já é; só conferir que referencia a mesma constante). |
| R03-8 | `ui/tui/test_screens_compact.py` (novo) | Para **cada** tela, com estados **preenchidos** (reaproveitar fixtures de `test_screens*.py`/`test_app.py`: probe completo, caminho de fonte longo, fila com 12+ jobs, LOG com 50+ linhas, ERROR com traceback longo, QC com todos os checks e EBU), renderizar **corpo e rodapé separadamente em altura ilimitada** (`console.render_lines` sem height) a W∈{80,100,119} e H∈{24,30,39}: afirmar `altura_natural(corpo) ≤ H − header − footer`, `altura(rodapé) == linhas do rodapé`, nenhuma linha > W. (Rich `Layout` corta em silêncio — por isso medir sem layout.) Afirmar também: `too_small` falso em 80×24, verdadeiro em 79×24 e 80×23; em 80×24 `apply(Key("DOWN"))` na HOME muda `home_focus`; rolagem de REPORT/ERROR alcança a última linha em 80×24. Em 120×40: render idêntico ao de antes (a suíte existente cobre; não alterar asserções existentes, só se a mudança de default exigir — registrar em STATE.md). |
| R03-9 | — | `venv\Scripts\python.exe -m pytest -q` (suíte inteira), `venv\Scripts\python.exe -m ruff check .`, `git diff --check`. Números reais em STATE.md (§ R-03). Capturas reais **não** são sua tarefa (o Orquestrador roda `tests/screens/capture.py` via ConPTY) — mas você pode usá-lo: `venv\Scripts\python.exe tests\screens\capture.py 80x24 <out.txt> down enter ...` (teclas: down up left right enter esc tab ctrlc wait:<s> resize:WxH text:<str>). Fora do escopo → FINDINGS.md. |

## Retorno

Ponteiro + veredito: status por ID em uma linha cada; detalhe em `.claude/memory/STATE.md` § R-03.

## Adendo R03-10 (auditoria ui-flow-reviewer, 2026-11-17)

| ID | arquivos | tarefa |
| --- | --- | --- |
| R03-10a | `ui/tui/screens.py` (~:310-311) | READY compacto: `ready_error` não pode ser cortado por `oneline()` — mensagem de erro (ex.: permissão com caminho) tem que aparecer inteira, com quebra de linha como no layout completo, sem estourar o corpo em 80×24. Teste: `ready_error` de ~200 caracteres em 80×24 → texto completo presente e corpo ≤ h−2. |
| R03-10b | `ui/tui/screens.py` (~:880-882, `_error`) | ERROR compacto: card com 2 linhas de conteúdo corta mensagem > ~150 caracteres. A mensagem tem que caber inteira (card dimensionado pelo texto, cedendo linhas do STDERR) e `error_rows(s)` no `state.py` tem que continuar coerente com o que o renderer desenha. Teste: mensagem de ~300 caracteres em 80×24 → texto completo, corpo ≤ h−2, rolagem do STDERR alcança a última linha. |
| R03-10c | `ui/tui/test_screens_compact.py` | Teste-guarda: CONFIGURATION/ADVANCED em 80×24 com o pior caso de campos + `field_error` → corpo natural ≤ h−2 (falha se um campo novo empurrar CONTINUAR para fora). Teste de resize compacto↔completo com `queue_scroll`/`error_scroll` ≠ 0 sem exceção e com foco/última linha visível. |

## Adendo R03-11 (captura ConPTY real em 80×24, 2026-11-17)

Evidência: capturas do Orquestrador (LOG e DETAILS durante encode real em 80×24).

| ID | arquivos | tarefa |
| --- | --- | --- |
| R03-11a | `ui/tui/screens.py` (`log_rows`, ~:390) | Coluna de nível aparece como `IN…`/`FF…`/`SY…`/`WA…` na tela LOG compacta quando o texto é longo (Rich encolhe a coluna `width=8`). Garantir a largura do nível (ex.: `min_width=8`) para que `INFO`/`SYSTEM`/`WARNING`/`FFMPEG` fiquem legíveis; o texto é que cede com "…". Em ≥120×40 o render tem que continuar byte a byte idêntico. Teste: LOG em 80×24 com linhas de 200 caracteres de cada `kind` → o nome do nível aparece inteiro. |
| R03-11b | `ui/tui/screens.py` (`_details`, ramo compacto ~:567) | DETAILS compacto empilha seções por coluna (0,2,4 | 1,3,5) e os títulos desalinham entre as colunas (" PROGRESS" sai na linha de "x264 preset"). Parear por linha como no layout cheio: SOURCE|HARDWARE, ENCODING|CONFIG, OUTPUT|PROGRESS (cada par numa linha do grid, títulos na mesma linha). Tem que caber em h−2 em 80×24 com estado cheio. Teste: em 80×24, cada par de títulos está na mesma linha renderizada e o corpo ≤ h−2. |
| R03-11c | — | `pytest ui/tui -q`, `ruff check .`, `git diff --check`; a suíte inteira **não** precisa rodar se só `screens.py` e testes de `ui/tui` mudarem — o Orquestrador decide. Registrar em STATE.md § R-03. |
