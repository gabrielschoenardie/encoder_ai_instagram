<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — H1 (valor canônico errado no doc) + H2 (placement do guard)

Data: 2026-07-25 | Ciclo: correção | Origem: `.claude/memory/FINDINGS.md` § "Achado novo — 2026-07-25 (ciclo G)"

**Objetivo:** corrigir os dois achados que o ciclo G destapou. H1 é um número errado
que circulou a auditoria inteira como canônico. H2 é o guard do ciclo G morando no
lugar errado — funciona hoje por convenção de chamada, não por construção.

**Estado de entrada:** o working tree tem as mudanças do ciclo G (G1–G4) **não
commitadas**. Não commitar nem reverter nada; trabalhar por cima.

**Escopo fechado (arquivos permitidos):**
- `.claude/skills/instagram-reels-encoder/references/cineon-pipeline.md` — só a linha 117
- `cineon_pipeline.py` — só o docstring da linha ~342 e a remoção do call site na linha ~801
- `Reels_Encoder_v2_FINAL.py` — só a inserção do call site em `run_ffmpeg_with_cineon` (linha 2950)
- `enhance/test_cineon_constants_guard.py` — só acréscimo de teste

**Fora de escopo:** a matemática do guard (auditada, PASS), qualquer LUT, os 7 testes
existentes do ciclo G (não reescrever), F2 (fechado). Bug fora do escopo → uma linha
em `FINDINGS.md`, sem investigar.

## Fonte dos valores canônicos

> `skill: instagram-reels-encoder` → `references/cineon-pipeline.md` § "Fórmula Cineon Log"

**Atenção — a fonte contém o próprio bug H1.** A *fórmula* nessa seção está correta e
bate com `colour.models.log_encoding_Cineon`; o valor `≈ 0.005012` escrito ao lado dela
está errado. Onde fórmula e valor divergirem, **a fórmula ganha**. Verificado:
`10^((95−685)/300) = 0.0107977`, e `log_encoding_Cineon(0.0) = 0.092864` ⇔
`(685 + 300·log10(0.0107977))/1023`.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| H1a | Corrigir o valor do `black_offset` na linha 117: `≈ 0.005012` → `≈ 0.010798`. A fórmula na mesma linha está certa — não tocar nela. | `executor` | `references/cineon-pipeline.md` | `grep -rn "0.005012" .claude/skills/` sem match; só a linha 117 alterada |
| H1b | Mesmo valor errado replicado no docstring da linha ~342. Corrigir. | `executor` | `cineon_pipeline.py` | `grep -n "0.005012" cineon_pipeline.py` sem match |
| H2a | Remover a chamada de `_validate_cineon_constants()` de `LUT3D.__init__` (linha ~801) e o comentário que a justifica (~795-800). A função `_validate_cineon_constants` e as constantes de módulo **ficam onde estão**. | `executor` | `cineon_pipeline.py` | `grep -n "_validate_cineon_constants" cineon_pipeline.py` mostra só a definição, nenhuma chamada |
| H2b | Chamar `_validate_cineon_constants()` no topo de `run_ffmpeg_with_cineon()` (`Reels_Encoder_v2_FINAL.py:2950`), antes de qualquer I/O — antes de resolver o path da LUT, antes de instanciar `LUT3D`, antes de abrir o FFmpeg. Importar do `cineon_pipeline`. | `executor` | `Reels_Encoder_v2_FINAL.py` | chamada é a primeira instrução executável do corpo da função (depois do docstring) |
| H2c | Teste novo: com `_validate_cineon_constants` adulterada para levantar, `run_ffmpeg_with_cineon` deve falhar **antes** de tocar disco ou spawnar FFmpeg. Ver nota abaixo antes de escrever. | `executor` | `enhance/test_cineon_constants_guard.py` | `python -m pytest enhance/test_cineon_constants_guard.py -q` verde, ≥8 testes |

## Notas de execução

- **H2c é o item que dá valor ao H2.** Sem ele, mover a chamada é só estética: os 7
  testes do ciclo G exercitam a *função*, nenhum exercita o *call site* — foi essa
  lacuna que deixou o placement errado passar. O teste tem de provar que o guard
  dispara no caminho do Cineon Mode.
- **Se `run_ffmpeg_with_cineon` não puder ser entrada num teste sem spawnar FFmpeg**
  (é uma função grande, com I/O), registre `blocked` em H2c com a razão exata e o que
  faltaria. **Não** escreva um teste que só inspeciona o código-fonte à procura da
  string da chamada — isso passa verde sem provar nada. Um `blocked` honesto vale mais.
- **Carregue `superpowers:verification-before-completion` antes de marcar qualquer ID
  como `done`** e cole no STATE.md a saída real do comando do critério.
- **Não rode a suíte inteira como critério.** Há 4 falhas pré-existentes
  (2 `enhance/test_ebu_meter.py`, 2 de encoding de console em `ui/`) que não são deste
  ciclo. Se rodar `pytest enhance/ ui/`, o esperado é `4 failed, N passed` — qualquer
  falha **além** dessas 4 é regressão sua.
- Retorno: uma linha por ID. Detalhe no STATE.md.

## Nota de roteamento (decisão do Orquestrador)

H2 cruza `cineon_pipeline.py` + `Reels_Encoder_v2_FINAL.py` + `enhance/`, o que pela
tabela do CLAUDE.md sugeriria `executor-pesado`. Mantenho **`executor`**: o gatilho de
`executor-pesado` é complexidade e ausência de supervisão, não contagem de arquivos.
Aqui a mudança é mover uma chamada de linha conhecida para linha conhecida, com escopo
fechado e critério de done mecânico. O único item com risco real é H2c, e para ele o
caminho previsto é `blocked`, não improviso.
