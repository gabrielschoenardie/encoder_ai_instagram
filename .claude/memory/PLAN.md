<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AM: cobrir a lógica de rotação de `ui/probe.py` (fecha AJF3)

Data: 2026-08-26 | Ciclo: AM | Origem: `.claude/memory/FINDINGS.md` § `AJF3`, aberto na varredura do Ciclo AJ e deixado fora do escopo dos Ciclos AK e AL.

## Diagnóstico

`ui/probe.py:19-78` expõe `probe_source_dims(path)`, que `ui/launcher.py:105`
chama a cada volta do loop de preview para orientar o viewer do Program. A
função faz três coisas: monta o argv do ffprobe, parseia o JSON, e decide se
troca largura por altura.

Os únicos dois testes que existem (`ui/test_probe.py:6-13`) afirmam
`probe_source_dims(...) is None` — e chegam nesse `None` por caminhos
**diferentes** em cada ambiente:

- **local:** o binário `ffprobe` existe, o arquivo não; `check_output` levanta
  `CalledProcessError` e o `except Exception` devolve `None`.
- **CI:** não há ffmpeg no PATH; `check_output` levanta `FileNotFoundError`
  antes de qualquer coisa, e o mesmo `except` devolve o mesmo `None`.

Dois caminhos de código distintos, mesmo resultado observável, e **nenhum dos
dois entra no parse**. Tudo entre as linhas 43 e 75 — parse, leitura de
`stream_tags`, leitura de Display Matrix, precedência de `format_tags`, e a
troca de rotação — nunca executa em teste nenhum.

Isso é diferente dos outros achados abertos: `AJF4` e `AKF1` são débito
conhecido e estável. Aqui o teste **afirma um verde que não prova nada sobre a
lógica que ele parece cobrir** — e a lógica em questão é a que decide se o
usuário vê o preview do Reel na orientação certa.

**Segundo fato, medido nesta investigação e não registrado no `AJF3`
original:** `get_input_resolution` (`Reels_Encoder_v2_FINAL.py:947-1012`) é o
gêmeo de onde `probe.py` foi copiado — argv idêntico, parse idêntico, mesmo
conjunto `(90, -90, 270, -270)`. Também tem **zero teste** (`grep
get_input_resolution` em `*test*.py` → nenhum match). As duas diferenças são
deliberadas: `probe` devolve `None` e é silenciosa, o motor devolve `(0, 0)` e
imprime. O docstring de `probe.py:23` afirma "Mirrors the engine's rotation
swap" — hoje nada guarda essa afirmação contra drift.

## Desenho

Injetar `subprocess.check_output` por `monkeypatch` em `ui.probe` e alimentar
payloads de ffprobe sintéticos. Nenhum ffmpeg, nenhum arquivo de vídeo,
nenhuma fixture binária no repo — o mesmo princípio que fechou o `AIF1`.

Formato dos payloads: bytes de JSON como o ffprobe realmente emite. Dois
detalhes de fidelidade que **não** podem ser "limpos":

- `stream_tags=rotate` vem como **string** (`"rotate": "90"`), não int.
- Display Matrix vem como **float negativo** (`"rotation": -90.000000`) — é
  essa a forma do caso iPhone vertical.

Um payload que use int onde o ffprobe usa string testa um contrato que não
existe.

### Matriz de decisão a cobrir

| entrada | rotação efetiva | dims 1920x1080 viram |
|---|---|---|
| sem tag, sem side_data | 0 | 1920x1080 |
| `stream_tags.rotate = "90"` | 90 | 1080x1920 |
| `stream_tags.rotate = "180"` | 180 | 1920x1080 (sem swap) |
| `stream_tags.rotate = "270"` | 270 | 1080x1920 |
| Display Matrix `rotation = -90.0` | -90 | 1080x1920 |
| tag `"90"` + Display Matrix `rotation = 0` | 90 | 1080x1920 (o 0 **não** apaga a tag) |
| tag `"180"` + `format_tags.rotate = "90"` | 180 | 1920x1080 (format só vale se stream deu 0) |
| sem stream rot + `format_tags.rotate = "90"` | 90 | 1080x1920 |
| `streams: []` | — | `None` |
| `width: 0` | — | `None` |

### Os dois testes existentes

Não são deletados — a degradação graciosa é comportamento real e vale teste.
São **tornados determinísticos**: cada um passa a injetar a exceção que
pretende testar (`FileNotFoundError` para binário ausente, `CalledProcessError`
para caminho inválido), de modo que local e CI percorram o mesmo caminho. O
`JSONDecodeError` de saída corrompida ganha o seu.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AM1 | Reescrever `ui/test_probe.py`: helper de payload, a matriz de rotação inteira da tabela acima, e os três testes de degradação determinísticos (`FileNotFoundError`, `CalledProcessError`, `JSONDecodeError`). Sem ffmpeg, sem fixture em disco. | executor | `ui/test_probe.py` | arquivo verde; `pytest ui/test_probe.py -v` roda com PATH sem ffmpeg |
| AM2 | Teste de contrato do argv: afirmar que o comando montado contém `stream=width,height:stream_tags=rotate:side_data:format_tags=rotate` e o `path` recebido. | executor | `ui/test_probe.py` | mata o mutante M8 (ver matriz) |
| AM3 | Guarda de drift: um teste que roda o **mesmo** payload por `probe_source_dims` e por `get_input_resolution` e afirma que as dims batem. Escopo estrito: um único teste, sem tocar em `Reels_Encoder_v2_FINAL.py`. | executor | `ui/test_probe.py` | o teste falha se o conjunto de swap de um dos dois divergir |
| AM4 | Matriz de mutação: aplicar cada mutante M1-M8 em `ui/probe.py`, rodar `pytest ui/test_probe.py`, registrar qual teste morre, **reverter**. Colar a tabela medida em `STATE.md`. | executor | `.claude/memory/STATE.md` | tabela com 8 linhas, cada mutante com ao menos um FAIL |
| AM5 | Fechar o ciclo com CI real verde e marcar `AJF3` corrigido. | executor | `.claude/memory/STATE.md`, `.claude/memory/FINDINGS.md`, `.claude/memory/PLAN.md` | log real do CI, não execução local |

## Matriz de mutação (AM4) — mutantes obrigatórios

| # | mutante em `ui/probe.py` | o que ele quebra |
|---|---|---|
| M1 | deletar `width, height = height, width` (linha 71) | swap nunca acontece |
| M2 | `if rotation in (90, 270)` (linha 70) | ângulos negativos param de rodar |
| M3 | `if rot != 0` → sempre verdadeiro (linha 62) | Display Matrix 0 apaga a tag do stream |
| M4 | remover o guard `if rotation == 0:` (linha 65) | `format_tags` passa a ganhar do stream |
| M5 | deletar o bloco `if "rotate" in tags` (56-57) | `stream_tags` ignorado |
| M6 | deletar o loop de `side_data_list` (59-63) | Display Matrix ignorado |
| M7 | `if width > 0 and height > 0` → sempre verdadeiro (73) | devolve `(0, 0)` em vez de `None` |
| M8 | tirar `stream_tags=rotate` do `-show_entries` (35) | ffprobe para de emitir a tag; **só o AM2 pega** |

M8 é o motivo do AM2 existir: testes que injetam JSON sintético continuam todos
verdes com o argv quebrado, porque o payload vem de dentro do teste. Sem o
teste de contrato do comando, a cobertura nova teria a mesma doença do `AJF3`.

## Critérios de aceite

- `ui/probe.py` **não é modificado**. O ciclo é sobre cobrir comportamento
  existente, não corrigi-lo. Se a cobertura revelar bug, ele vai para
  `FINDINGS.md` como achado novo — não é consertado aqui.
- Os testes rodam com o PATH sem ffmpeg. Prova: `pytest ui/test_probe.py` num
  shell onde `shutil.which("ffprobe")` é `None`.
- Cada um dos 8 mutantes tem ao menos um teste em FAIL na tabela do AM4. Um
  mutante que sobrevive é cobertura de fachada — é a coisa exata que o `AJF3`
  denuncia, e reintroduzi-la reprova o ciclo.
- Suíte completa: `435 passed` + os testes novos, sem regressão.
- CI real verde nos 7 jobs.

## Notas de execução

- Payloads fiéis ao ffprobe: `rotate` string, `rotation` float negativo. Não
  "normalizar" para int.
- `monkeypatch.setattr("ui.probe.subprocess.check_output", fake)` — o
  `monkeypatch` do pytest restaura sozinho; não usar `try/finally` à mão.
- **Reverter cada mutante do AM4 antes do próximo.** Rodar `git diff --stat --
  ui/probe.py` no fim do AM4 e confirmar vazio.
- Não tocar em `ui/launcher.py`, `ui/components.py`, nem no
  `Reels_Encoder_v2_FINAL.py`. O AM3 só **importa** `get_input_resolution`.
- Se `get_input_resolution` imprimir no console durante o AM3, isso é esperado
  (`Reels_Encoder_v2_FINAL.py:995`) — não silenciar mexendo no motor.
- Não fechar o ciclo com base em execução local. A prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
