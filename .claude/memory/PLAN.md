<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AU: reconciliar J-b (já corrigido) e fechar a lista irmã defasada

Data: 2026-09-03 | Ciclo: AU | Origem: `.claude/memory/FINDINGS.md` § `J-b` (Ciclo J, 2026-07-25), último da fila do usuário.

## Diagnóstico

Remedido hoje. O `J-b` como escopado — a lista de fallback do `APÊNDICE A`
(`MANUAL_INSTALACAO.txt:295-309`) — **já foi corrigido**, no commit `9b6ed26`
("fix(docs,lint): fechar J-b e I-a"), em 2026-07-25. O apêndice hoje não tem lista de
pacotes: aponta para `pip install -e .[opencv]` e diz que as deps reais vivem no
`pyproject.toml` — exatamente o fix que o achado recomendava. Mesmo padrão do `I-a`
(Ciclo AO): corrigido em julho, nunca marcado fechado no `FINDINGS.md`.

**Mas o achado citou o range errado.** O mesmo defeito — lista de pacotes mantida à mão,
divergente do `pyproject.toml` — sobrevive nas linhas **121-129** do mesmo arquivo, no
bloco "Isso vai instalar:" do PASSO 3. Medido contra as deps reais:

| pyproject (core) | na lista 121-129? |
|---|---|
| rich, numpy, av, Pillow, psutil, colour-science, pymediainfo | sim |
| **pydantic** | **não** |
| **scipy** | **não** |
| matplotlib | não (ver achado novo abaixo) |
| opencv-python (extra `[opencv]`) | sim |

Faltam `pydantic` e `scipy` — **os dois pacotes exatos que o texto do `J-b` nomeia** como
ausentes. A lista irmã é a instância viva do defeito que o achado descreve; o fix de julho
tocou o apêndice e deixou esta passar.

### Achado novo — `AUF1` (dep declarada e não usada)

Verificando a lista contra o código: `matplotlib` está declarado em `pyproject.toml:29`
(`"matplotlib>=3.9,<4"`) mas **não é importado em nenhum arquivo rastreado** — `git grep
matplotlib` só acha a própria declaração no `pyproject.toml`. `scipy` (analyzers) e
`pydantic` (`ui/config.py`) são reais e usados; `matplotlib` não. É classe diferente do
`J-b` (dep morta no pacote, não doc defasada) e decisão do usuário — remover do
`pyproject.toml` ou confirmar necessidade. Registrado, **não** corrigido neste ciclo, e
**não** adicionado à lista do manual: documentar uma dep que pode ser removida
entrincheiraria um possível erro.

## Desenho

Corrigir a lista das linhas 121-129 acrescentando `pydantic` e `scipy`, com descrição
honesta baseada no uso real (`pydantic` → validação de configuração da UI, `ui/config.py`;
`scipy` → filtros de análise de imagem, `enhance/analyzers/`). Nada mais no arquivo — o
`APÊNDICE A` já está certo, não se toca.

Não substituir a lista inteira por "veja pyproject.toml" como foi feito no apêndice: aqui
a lista tem valor de UX num manual de usuário final (descreve em português o que cada
pacote faz). Corrigir o conteúdo, preservando a forma. Fica registrado que continua sendo
lista mantida à mão — risco de drift inerente a doc, aceito.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AU1 | Em `MANUAL_INSTALACAO.txt`, no bloco "Isso vai instalar:" (linhas ~121-129), acrescentar duas linhas: `pydantic` (validação de configuração) e `scipy` (filtros de análise de imagem), no mesmo formato `  ✓ nome (descrição)` das existentes. Não adicionar `matplotlib`. Não tocar no `APÊNDICE A` nem em nenhuma outra parte do arquivo. | executor | `MANUAL_INSTALACAO.txt` | `git diff` mostra só as 2 linhas adicionadas no bloco certo |
| AU2 | Fechar `J-b` (reconciliação: corrigido em `9b6ed26` + a lista irmã fechada por este ciclo) e registrar `AUF1` (matplotlib declarado e não usado) no `FINDINGS.md`. | Orquestrador | `.claude/memory/FINDINGS.md` | — |

## Critérios de aceite

- Só `MANUAL_INSTALACAO.txt` muda, e só o bloco das linhas 121-129 — duas linhas
  acrescentadas. `APÊNDICE A` intocado. Nenhum `.py`, nenhum `pyproject.toml`.
- A lista passa a conter `pydantic` e `scipy`. **Não** contém `matplotlib` (pendente da
  decisão do `AUF1`).
- Nenhum teste muda (nada cobre o manual). Suíte Python: `467 passed`, sem regressão —
  confirmação de que o ciclo não tocou código, não prova do fix.
- **A prova do fix não é CI** — nada testa o conteúdo do manual. A prova é o `git diff`
  mostrar as duas linhas certas e a lista bater com as deps core do `pyproject.toml`
  (menos `matplotlib`, deliberado).

## Notas de execução

- Este é o ciclo mais leve da fila: uma edição de doc de duas linhas. Não expandir —
  não reescrever a lista, não mexer no apêndice, não corrigir `matplotlib` (é decisão do
  usuário via `AUF1`).
- Não tocar em `pyproject.toml`. O `AUF1` é registro, não conserto.
- CI vai rodar de qualquer forma (o push dispara) e deve ficar verde, mas isso só atesta
  ausência de regressão de código — a correção da doc se prova lendo o diff.
- **Nunca `git add -A` nem `git add .`** — há arquivos não rastreados (`961576A_*.qc.*`,
  `docs/*.md` novos, `testResults.xml`, `videos/`). Adicionar por caminho explícito.
- Ao anexar ao `STATE.md` (se registrar algo), começar com `## Ciclo AU` e cabeçalho.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
