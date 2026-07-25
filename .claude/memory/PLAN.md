<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Correções pós-auditoria: A3 (guard de constantes) + E3d (doc)

Data: 2026-07-25 | Ciclo: correção | Origem: `.claude/memory/FINDINGS.md` (auditoria 2026-07-18)

**Objetivo:** fechar os dois achados corrigíveis da auditoria Cineon. A3 é o único
bug estrutural (S2): o guard de constantes referenciado pelo pipeline nunca foi
escrito, então nada barra regressão silenciosa dos valores canônicos. E3d é uma
linha errada de documentação (S3): o código está correto, o doc é que descreve a
ordem de quantização invertida.

**F2 não entra neste ciclo** — ver "Decisão sobre F2" no fim.

**Escopo fechado (arquivos permitidos):**
- `cineon_pipeline.py` — apenas: nova função `_validate_cineon_constants` + seu call site
- teste novo em `tests/` (ou junto dos testes existentes de `cineon_pipeline`, o que o repo já usar)
- `.claude/skills/instagram-reels-encoder/references/cineon-pipeline.md` — apenas a linha 55

**Fora de escopo:** qualquer LUT `.cube`, FFmpeg Mode, VBV/GOP/zones, `enhance/`,
matemática dos nós 1–5 (auditada e PASS). Bug fora do escopo → uma linha em
`FINDINGS.md`, sem investigar.

## Fonte dos valores canônicos

**Não estão transcritos aqui de propósito.** Carregue a skill e leia de lá:

> `skill: instagram-reels-encoder` → `references/cineon-pipeline.md`
> § fórmula Cineon log (ref black, ref white, fator de escala, black_offset derivado)
> § ordem canônica dos 5 nós

A auditoria de 2026-07-18 confirmou que os valores **no código hoje estão corretos**
(A2/B1/B2 PASS contra `colour-science`, Δ ≤ 3.2e-4). O trabalho aqui não é mudar
valor nenhum — é impedir que mudem sem ninguém notar.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| G1 | Escrever `_validate_cineon_constants()` em `cineon_pipeline.py`: valida as constantes da fórmula Cineon log e o `black_offset` **derivado** (não hardcoded) contra os valores canônicos da skill. Levanta exceção com a constante divergente nomeada; não corrige, não faz fallback. | `executor` | `cineon_pipeline.py` | função existe, `python -c "import cineon_pipeline; cineon_pipeline._validate_cineon_constants()"` roda sem exceção |
| G2 | Chamar `_validate_cineon_constants()` no caminho do Cineon Mode, **antes** do primeiro frame ser processado — não em import time, não dentro do loop per-frame. Registrar no STATE.md a função/linha exata onde o call site foi posto e por quê. | `executor` | `cineon_pipeline.py` | grep mostra ≥1 call site; adulterar uma constante faz o Cineon Mode falhar antes do 1º frame |
| G3 | Teste de regressão: adultera cada constante (uma por vez, via monkeypatch) e afirma que `_validate_cineon_constants` levanta. Mais um caso feliz com os valores reais. | `executor` | teste novo | `python -m pytest <arquivo do teste> -q` verde |
| G4 | Corrigir `references/cineon-pipeline.md` linha 55: a ordem documentada da quantização final está invertida. A ordem correta é a que o código já implementa (`cineon_pipeline.py:982`) — ×255 → dither → round → clip. Clipar antes faz 255.5 arredondar para 256 e estourar o uint8. | `executor` | `.../references/cineon-pipeline.md` | linha 55 descreve a ordem do código; nenhuma outra linha do arquivo tocada |

## Notas de execução

- **G1–G3 são um bloco.** Carregue `superpowers:test-driven-development`: escreva G3
  antes de G1 passar. O teste que adultera a constante deve **falhar** enquanto a
  função não existir — é isso que prova que o guard guarda alguma coisa.
- **Antes de marcar qualquer ID como `done`**, carregue
  `superpowers:verification-before-completion` e cole no STATE.md a saída real do
  comando do critério de done. Sem output, o item fica `blocked`.
- **G2 é a parte que já falhou uma vez.** Um guard que existe mas nunca roda no
  caminho do Cineon é o bug A3 de novo com mais linhas. Se não houver um ponto
  claro de "antes do primeiro frame" no código, PARE e registre `blocked` com a
  pergunta — não invente um call site em import time.
- **G4 é independente** e pode ir antes ou depois.
- Retorno: uma linha por ID conforme o protocolo. Detalhe no STATE.md.

## Decisão sobre F2 (não corrigir — fechado)

`FilmLook_Portra400_SkinPriority_D65.cube` em (0,0,0) devolve −0.025429, fora do
critério [0, 0.05] da auditoria. **Não será corrigido**, pelo seguinte:

- A entrada real da LUT neste pipeline é ≥ 0.0928: `log_encoding_cineon` (node3)
  clipa em [0,1] e lin=0 mapeia para 0.0928. Medido: `output(0.0928) = +1.58e-05`, são.
- O toe negativo só é alcançável usando a `.cube` standalone (Resolve, `lut3d` do
  FFmpeg) fora deste pipeline.
- Corrigir o toe alteraria o grade Portra em toda a faixa baixa para consertar um
  caso que o pipeline nunca produz.

Ação: registrar em `FINDINGS.md` como limitação aceita, com a condição de reabertura
— se a `.cube` passar a ser distribuída para uso standalone, F2 volta a valer.
