<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AN: leitura de `.cube` independente de plataforma (fecha ACF1, fecha ANF1)

Data: 2026-09-03 | Ciclo: AN | Origem: `.claude/memory/FINDINGS.md` § `ACF1`, aberto no Ciclo AC (Task 4) e adiado desde então.

## Diagnóstico

`cineon_pipeline.py:810` (`LUT3D._load_cube_file`) abre o `.cube` sem `encoding=`:

```python
with open(path, "r") as f:
```

Cai no default da plataforma — `cp1252` no Windows, `utf-8` no Linux. É código de
produto, não de teste, e é alcançável pelo usuário final: `--cineon-lut`
(`Reels_Encoder_v2_FINAL.py:4300`) aceita caminho arbitrário de `.cube`, e o call site é
`Reels_Encoder_v2_FINAL.py:3294`, dentro de `run_ffmpeg_with_cineon`. Resolve e FCPX
gravam UTF-8.

Agrava que as linhas imediatamente acima (`:3285-3287`) validam `os.path.exists` com
mensagem vermelha amigável, e aí a linha seguinte estoura traceback cru.

### O repro registrado no `ACF1` está errado — medido nesta investigação

O achado afirma que `TITLE "Portra 400 — Skin"` já basta para estourar em Windows. **Não
basta.** O travessão existe em cp1252 (`0x97`); decodifica como mojibake, sem exceção, e o
parser descarta a linha `TITLE` de qualquer forma. Quem tentasse verificar o `ACF1` pelo
repro documentado concluiria que não é bug.

O que quebra de fato é acentuada **maiúscula** cujo segundo byte UTF-8 cai num slot
indefinido do cp1252 — `Á` (`C3 81`), `Í` (`C3 8D`), `Ï` (`C3 8F`), `Ð` (`C3 90`),
`Ý` (`C3 9D`):

```
TITLE "ÁGUA Film Look"
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 8
```

Minúsculas acentuadas (`á`, `ç`, `ã`), travessão e emoji passam. O caso real é LUT
titulada em caixa alta em português — `CINEMATOGRÁFICO`, `ÁGUA` — que é convenção comum
de colorista.

### Achado novo descoberto no planejamento: `ANF1` (BOM)

Um `.cube` gravado com BOM UTF-8 e `LUT_3D_SIZE` na **primeira** linha já falha hoje, em
**qualquer** plataforma: o BOM vira prefixo da primeira linha, `line.startswith("LUT_3D_SIZE")`
nunca casa, e o parser levanta `ValueError: LUT_3D_SIZE não encontrado` — mensagem que
aponta para a causa errada. É defeito independente do `ACF1`, na mesma função, e a mesma
linha conserta os dois. Registrado como `ANF1` e fechado por este ciclo, não adiado.

## Desenho

O fix de uma linha prescrito no `ACF1` (`encoding="utf-8"`) é **insuficiente e
regressivo**. Matriz medida no planejamento — quatro `.cube` reais gravados em disco,
lidos pelo parser real:

| caso | hoje (default) | `utf-8` | `utf-8-sig` | `utf-8-sig` + `errors="replace"` |
|---|---|---|---|---|
| BOM, `LUT_3D_SIZE` na 1a linha | ✗ sem SIZE | ✗ sem SIZE | ✓ | ✓ |
| UTF-8, `TITLE "ÁGUA"` | ✗ Windows / ✓ Linux | ✓ | ✓ | ✓ |
| cp1252, `TITLE "ÁGUA"` | ✓ Windows / ✗ Linux | ✗ | ✗ | ✓ |
| ASCII puro (a LUT do repo) | ✓ | ✓ | ✓ | ✓ |

`encoding="utf-8"` troca um crash por outro: mata o caso UTF-8 e passa a matar o caso
cp1252, que hoje funciona em Windows. Só a última coluna é verde nas quatro linhas.

**Decisão: `open(path, "r", encoding="utf-8-sig", errors="replace")`.**

Justificativa do `errors="replace"`, que normalmente seria suspeito: este parser consome
exclusivamente `LUT_3D_SIZE` e linhas numéricas, ambas ASCII em qualquer `.cube` real. Ele
**descarta** `TITLE`, comentários `#` e `LUT_3D_INPUT_RANGE`. Byte indecodificável só pode
aparecer nos campos descartados, então substituí-lo não perde informação que o parser use
— e é a diferença entre abortar o encode e ignorar um caractere de um título que já era
ignorado. Se o parser um dia passar a ler `TITLE`, esta decisão precisa ser revisitada.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AN1 | Trocar `open(path, "r")` por `open(path, "r", encoding="utf-8-sig", errors="replace")` em `_load_cube_file`. Uma linha. Nada mais no arquivo. | executor | `cineon_pipeline.py` | `git diff --stat` mostra 1 arquivo, 1 linha |
| AN2 | Testes em `enhance/test_cineon_lut.py`: parametrizar sobre os 4 casos da matriz, gravando `.cube` reais em `tmp_path` com `encoding=` explícito (`utf-8-sig`, `utf-8`, `cp1252`, `ascii`) e `newline=""`. Cada caso afirma `lut.lut_size == 2` após `LUT3D(str(p))`. | executor | `enhance/test_cineon_lut.py` | 4 casos passam; ver critério de simetria abaixo |
| AN3 | Matriz de mutação: aplicar M1-M4 em `cineon_pipeline.py`, rodar `pytest enhance/test_cineon_lut.py`, registrar qual teste morre, **reverter**. Colar a tabela medida em `STATE.md`. | executor | `.claude/memory/STATE.md` | 4/4 mutantes mortos, `git diff --stat -- cineon_pipeline.py` vazio ao fim |
| AN4 | Corrigir o repro do `ACF1` no registro (o travessão não quebra; `Á`/`Í`/`Ï`/`Ð`/`Ý` quebram), registrar `ANF1`, marcar os dois fechados. | Orquestrador | `.claude/memory/FINDINGS.md` | — |
| AN5 | Fechar o ciclo com CI real verde. | Orquestrador | `.claude/memory/STATE.md` | log real do CI, não execução local |

## Critério de simetria de plataforma (a lição do AJF3)

Este é o ponto que decide se o ciclo vale alguma coisa. Antes do AN1, o conjunto de
testes do AN2 tem de ficar **vermelho nos dois SOs**, por casos diferentes:

- **Windows** (`cp1252`): o caso UTF-8 `ÁGUA` estoura `UnicodeDecodeError`; o caso cp1252 passa.
- **Linux** (`utf-8`): o caso cp1252 `ÁGUA` estoura `UnicodeDecodeError`; o caso UTF-8 passa.
- **Ambos**: o caso BOM levanta `ValueError`.

Os dois casos acentuados são complementares de propósito — sozinho, cada um seria verde
por acidente numa das pernas do CI, que é exatamente a doença que o `AJF3` denunciou. Um
conjunto que só contivesse o caso UTF-8 passaria verde no Linux antes do fix e ninguém
notaria.

## Matriz de mutação (AN3)

| # | mutante em `cineon_pipeline.py:810` | o que ele quebra | esperado |
|---|---|---|---|
| M1 | voltar para `open(path, "r")` | default da plataforma | vermelho nos dois SOs, por casos diferentes |
| M2 | `encoding="utf-8"` (o fix prescrito no `ACF1`) | mata BOM e cp1252 | casos BOM e cp1252 vermelhos, os outros 2 verdes |
| M3 | `encoding="utf-8"` + `errors="replace"` | BOM sobrevive na 1a linha | só o caso BOM vermelho |
| M4 | `encoding="utf-8-sig"` sem `errors` | header legado estoura | só o caso cp1252 vermelho |

M2, M3 e M4 existem para provar que cada metade da decisão é necessária: um mutante que
sobrevive significa que aquele pedaço do fix não está sendo testado, e o `errors="replace"`
ou o `-sig` viraria escolha não justificada por medição.

**Correção de plano (AN3).** A coluna "esperado" do M2 dizia originalmente "caso cp1252
vermelho, os outros 3 verdes", o que contradiz a matriz do § Desenho — onde a coluna
`utf-8` já mostra o caso BOM como `✗ sem SIZE`. O executor mediu `bom` + `cp1252`,
registrou a divergência em `STATE.md` em vez de dobrar o medido para bater com a
narrativa, e não bloqueou o item porque o critério de aceite real ("ao menos um teste em
FAIL") estava satisfeito. Erro meu de redação da tabela, não do executor nem da decisão
técnica; a linha acima está corrigida.

**Como o M2 fecha a metade Linux do critério de simetria.** O AN3 roda numa máquina
Windows, então o M1 (default da plataforma) só exercita a perna cp1252. Mas o M2 **é** o
default do Linux: ler com `encoding="utf-8"` é exatamente o que a perna Ubuntu faz hoje sem
`encoding=`. Que o M2 derrube `bom` + `cp1252` é, portanto, medição direta de que o estado
pré-fix é vermelho também no Linux — por casos diferentes dos que derrubam o Windows
(`bom` + `utf8`, via M1). A simetria fica provada pela matriz de mutação, sem depender de
rodar o CI com o mutante aplicado.

## Critérios de aceite

- `cineon_pipeline.py` muda em **exatamente uma linha**. Nenhuma outra alteração no
  arquivo — sem refactor do parser, sem tratar `TITLE`, sem mensagem de erro nova.
- Os 4 mutantes têm ao menos um teste em FAIL na tabela do AN3.
- A LUT real do repo (`FilmLook_Portra400_SkinPriority_D65.cube`, ASCII, `TITLE` na 1a
  linha) continua carregando — os dois testes existentes de `test_cineon_lut.py`
  (`test_roundtrip_neutral_ramp_transparente`, `test_roundtrip_white_atinge_pico`) seguem
  verdes sem alteração.
- Suíte completa: `457 passed` + os testes novos, sem regressão.
- CI real verde nos 7 jobs, com atenção às pernas Windows **e** Ubuntu — a simetria é o
  produto deste ciclo.

## Notas de execução

- Gravar os `.cube` de teste com `newline=""` para que o conteúdo em disco não dependa do
  SO que rodou o teste.
- **Não** consertar `audit_tmp/audit_lut.py:43`, que tem o mesmo `open(path, "r")`: o
  diretório não é rastreado pelo git (`git ls-files audit_tmp/` = vazio). Não é código de
  produto.
- Não tocar em `Reels_Encoder_v2_FINAL.py`. O call site (`:3294`) e a validação de
  existência (`:3285-3287`) ficam como estão.
- **Reverter cada mutante do AN3 antes do próximo.** Rodar `git diff --stat --
  cineon_pipeline.py` no fim do AN3 e confirmar vazio.
- Não fechar o ciclo com base em execução local. A prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
