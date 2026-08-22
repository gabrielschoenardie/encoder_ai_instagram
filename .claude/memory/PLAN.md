<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AE: esfriar a Hollywood LUT em 20% no eixo warm-cool

Data: 2026-08-22 | Ciclo: AE | Origem: pedido direto do usuário (brainstorming aprovado em sessão, caminho *bounded*). Sem spec em `docs/superpowers/specs/`.

## Diagnóstico

Medição das 35.937 entradas de
`HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube`:

1. **O eixo neutro é identidade em croma.** Nos 33 degraus, `R=G=B` na
   entrada → `R=G=B` na saída, exato. A LUT **não tem desvio de white
   balance** — o `NeutralShadows` do nome é literal.
2. **O calor vem de assimetria por matiz.** Ganhos globais: saturação
   `0.851`, eixo warm-cool (R−B) `0.768`, eixo green-magenta `0.715`.
   Por amostra (Δ warm / Δ sat): laranja-pele `+0.0098 / +0.0098`,
   pele escura `+0.0102 / +0.0102`, ciano `+0.0185 / −0.0185`, verde
   `+0.0146 / −0.0309`, **azul saturado `+0.1591 / −0.1591`**, azul de
   céu `−0.0260 / +0.0260`.
3. Ou seja: a LUT **esmaga o azul saturado** e empurra laranja/pele
   ~1%. Ela não esquenta a imagem — remove o contrapeso frio.

**Consequência que define a solução:** `colortemperature`, `colorbalance`
ou ganho por canal depois do `lut3d` estão **proibidos** neste ciclo.
Todos deslocam o cinza, e o requisito do usuário é exatamente *não*
mudar a temperatura do vídeo original sem LUT. A correção tem de viver
dentro do próprio cube, atenuando só o delta cromático.

## Transformação (especificação exata, não reinterpretar)

Base ortonormal de oponentes de cor em RGB:

| eixo | vetor unitário | destino |
| --- | --- | --- |
| acromático (luma/contraste) | `(1,1,1)/√3` | intacto |
| warm-cool | `ŵ = (1,0,−1)/√2` | **× 0.80** |
| green-magenta | `(−1,2,−1)/√6` | intacto |

Para cada nó, com entrada `i` (a grade) e saída `o` (o cube atual):

```
delta = o - i
out'  = o - 0.20 * (delta · ŵ) * ŵ
out'  = clip(out', LO, HI)
```

`FATOR = 0.20` é constante nomeada no topo do gerador, parametrizável
por argumento. Os três eixos são mutuamente ortogonais: atenuar um não
vaza nos outros. Em todo neutro `delta = 0`, logo `out' = o` — é isso
que preserva o requisito.

**Clamp obrigatório para o envelope do cube de origem, não para
`[0,1]`.** `LO`/`HI` são derivados por leitura do cube fonte
(`min`/`max` sobre todas as entradas) e o gerador **assert**a que valem
`0.031373` e `0.921569`. Reduzir o delta empurra a saída na direção da
entrada, e a entrada vai até `1.0`; sem esse clamp um nó claro e
saturado pode estourar o teto de 1.5 IRE e quebrar a conformidade
`Instagram8bit_TVRange`. Registrar quantos nós encostam no clamp.

**Formato do arquivo.** Ordem red-fastest (`k = ri + gi*N + bi*N²`),
`LUT_3D_SIZE 33`, 35.937 linhas de dados, 6 casas decimais (`%.6f`),
mesma convenção do fonte. Header:

```
TITLE "Hollywood Cinema Ultimate v6.7C 1.5IRE_Instagram8bit_TVRange - Neutral Shadows - Warm 80%"
LUT_3D_SIZE 33
```

Saída: `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube`
na raiz do repo, ao lado do fonte.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AE1 | Escrever este `PLAN.md`. | Orquestrador | `.claude/memory/PLAN.md` | **done** — este arquivo |
| AE2 | Criar o gerador determinístico e assar o cube derivado, seguindo § "Transformação" ao pé da letra. Espelhar o estilo de `tools/generate_portra400_baseline_lut.py` (precedente da casa para gerador de LUT). Escrever os testes de propriedade da AE3 **antes** do bake (TDD) — eles falham sem o cube, passam depois. | `executor-pesado` | `tools/generate_hollywood_lut_cooler.py`, `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube` | pendente |
| AE3 | Testes de propriedade sobre o cube gerado (sobre o arquivo, não sobre pixels de vídeo). Estilo da casa: sem fixtures salvo `tmp_path`, sem `monkeypatch`, sem classes. Ver § "Critérios de aceite" para os 6 asserts obrigatórios. | `executor-pesado` | `tools/test_generate_hollywood_lut_cooler.py` | pendente |
| AE4 | Trocar as referências ao filename da LUT. **Localizar por âncora de texto, não por número de linha.** Em `Reels_Encoder_v2_FINAL.py`: a constante `_HOLLYWOOD_LUT_FILENAME` (~:2193), o label `✓ LUT v6.7:` (~:2262), e a mensagem de erro que hoje manda `Execute: python hollywood_lut.py` (~:2204) — **esse arquivo não existe no repo**; apontar para `python tools/generate_hollywood_lut_cooler.py`. Também `pyproject.toml` (`data-files`, ~:48), `tools/verificador_instalacao.py` (~:195), `README.md` (~:441 árvore, ~:571 tabela). | `executor` | os 5 arquivos acima | pendente |
| AE5 | Atualizar a skill para o filename e o comportamento novos: `color-pipeline.md` (~:14, :75, :84 — e acrescentar ao § da LUT que o eixo warm-cool está a 80%, com o número medido), `encoder-modes.md` (~:16, :31, :192), `adaptive-analysis.md` (~:570), `scripts/analyze_source.py` (`LUT_FFMPEG`, ~:41). | `executor` | 4 arquivos em `.claude/skills/instagram-reels-encoder/` | pendente |
| AE6 | A/B real: encodar o mesmo source com a LUT antiga e a nova, e rodar QC de entrega no output novo. Confirmar que conformidade Instagram e VMAF-contra-o-source não regrediram — a mudança é só croma, VMAF não deve mover de forma material. Colar saída literal em `STATE.md`. | `encode-validator` | `.claude/memory/STATE.md` | pendente — bloqueada pela AE7 |
| AE7 | **Rebake na variante B** (ver § "Revisão pós-bake"). Alterar o gerador para atenuar só o lado quente, reassar o cube no **mesmo filename**, e atualizar os asserts 3 e 4 da AE3 para os valores novos + os 2 invariantes novos. | `executor-pesado` | `tools/generate_hollywood_lut_cooler.py`, `tools/test_generate_hollywood_lut_cooler.py`, `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube` | pendente |

## Critérios de aceite (AE3 — os 6 asserts)

1. **Eixo neutro idêntico ao fonte, tolerância zero.** Para os 33 nós
   `i=j=k`, `out_W80 == out_v6.7B` exatamente (comparar as strings de 6
   casas, não floats).
2. **Envelope preservado.** `min == 0.031373` e `max == 0.921569` no
   cube gerado.
3. **Ganho warm-cool = `0.8144 ± 0.002`.** Ajuste linear de
   `(out_R − out_B)` contra `(in_R − in_B)` sobre os nós com saturação
   de entrada `> 0.05`. Hoje é `0.768`; `1 − 0.80 × 0.232 = 0.8144`.
4. **Green-magenta inalterado em `0.7146 ± 0.001`** e ganho de luma
   (`0.2126R + 0.7152G + 0.0722B`) inalterado em relação ao fonte —
   provam que a projeção não vazou para os outros eixos.
5. **Estrutura.** `LUT_3D_SIZE 33`, exatamente 35.937 linhas de dados,
   todas com 3 floats.
6. **Determinismo.** Rodar o gerador duas vezes produz arquivo
   byte-idêntico.

## Notas de execução

- **Verificação da AE2/AE3:**
  `python -m pytest tools/test_generate_hollywood_lut_cooler.py -v`.
  `tools/` não está no comando de baseline da casa — incluir
  explicitamente e confirmar que o pytest coleta o diretório.
- **Baseline a preservar (AE4/AE5):**
  `python -m pytest test_render_queue.py enhance/ ui/ -q` → `395 passed`
  ao fim do Ciclo AD. Tem de continuar `395 passed`.
  `ui/test_packaging.py::test_data_files_include_luts` casa por sufixo
  `.cube` genérico, então a troca de filename não deve quebrá-lo — se
  quebrar, é sinal de que o `data-files` do `pyproject.toml` ficou
  inconsistente.
- **A LUT v6.7B original permanece no repo.** Não apagar. Serve para
  A/B e para rollback, que é só reverter a constante `_HOLLYWOOD_LUT_FILENAME`.
- **Anti-escopo deste ciclo:** não mexer no modo Cineon nem na
  `FilmLook_Portra400_SkinPriority_D65.cube`; não tocar em CAS, dither,
  ODT ou qualquer outro estágio de `build_sdr_float_pipeline`; não
  adicionar knob de CLI/wizard (decisão explícita do usuário — cube
  assado, sem parâmetro exposto), portanto **não** há mudança em
  `ui/launcher.py` e o `ui-flow-reviewer` não entra neste ciclo.
- **Divergência pré-existente, deixar como está:** o `TITLE` interno do
  cube fonte diz `v6.7C`, o filename diz `v6.7B`. Decisão do usuário:
  não alinhar. O cube novo herda o mesmo `v6.7C` no TITLE.
- **Expectativa de efeito, registrada para a AE6 não se assustar:** a
  20%, o efeito concentra-se no azul saturado (devolve ~`0.032` de
  croma — céu, roupa, neon esfriam de forma perceptível). Na pele o
  push de laranja cai de `+0.0098` para `+0.0078` — sutil por desenho.
  O usuário aprovou o eixo global sabendo disso.
- Sequência: AE2→AE3 juntas (TDD), depois AE4 e AE5 em paralelo, AE6 por
  último consumindo o resultado das duas. **Revisada:** AE7 entra entre
  AE5 e AE6.
- **Lição de orquestração (custo real, registrar):** AE4 e AE5 foram
  despachadas em paralelo no mesmo checkout. O `git add` da AE4 varreu
  as edições da AE5 e as duas caíram no commit `e0f23ac`. Conteúdo
  íntegro (auditado: exatamente AE4 ∪ AE5 ∪ `STATE.md`), só o histórico
  perdeu granularidade. **Duas tarefas de escrita concorrentes exigem
  worktree isolado** (`superpowers:using-git-worktrees`) ou execução
  sequencial. A AE7 roda sozinha.

## Revisão pós-bake — variante B (normativa a partir daqui)

A auditoria do cube da AE2 mostrou que a § "Transformação" original
estava errada quanto à intenção. Achado: **em 17.831 dos 35.937 nós a
v6.7B estava *esfriando*, não esquentando.** Atenuar o delta
simetricamente desfaz 20% desse resfriamento, deixando branco quente
(`−0.0245 → −0.0196`), vermelho (`−0.0904 → −0.0723`) e azul de céu
(`−0.0260 → −0.0208`) **mais quentes** que a v6.7B — o oposto do pedido
— e é a causa mecânica de 780 dos 823 nós no clamp, em luma de entrada
`0.601`–`0.987` (pele ensolarada, céu claro: conteúdo real, não canto de
gamute).

**Transformação corrigida** — atenuar só o lado quente:

```
delta = o - i
dw    = delta · ŵ                    # ŵ = (1,0,−1)/√2
out'  = o - 0.20 * max(dw, 0) * ŵ    # ← única mudança: max(dw, 0)
out'  = clip(out', LO, HI)
```

Contínua em `dw = 0`, logo sem descontinuidade na LUT. Idêntica à
variante A em todo nó com `dw > 0` — pele `+0.0079`, laranja, ciano
`+0.0148`, azul saturado `+0.1273` — que é exatamente o alvo do pedido.

**Valores medidos da variante B, já verificados pelo Orquestrador — os
testes devem casar com estes números, não recalibrar para o que sair:**

| métrica | valor |
| --- | --- |
| ganho warm-cool | `0.790588` (± 0.002) |
| ganho green-magenta | `0.714645` (± 0.001; fonte `0.714632`) |
| nós no clamp | `370`, **todos no teto**, zero no piso |
| overshoot p90 / max | `0.00655` / `0.01548` |
| min / max do cube | `0.031373` / `0.921569` |
| eixo neutro | exato vs v6.7B |

**Dois invariantes novos para a AE3, ambos com violação esperada = 0:**

7. **Nenhum nó fica mais quente que a v6.7B.** Para todo nó,
   `(out'_R − out'_B) ≤ (o_R − o_B) + 1e-9`. Verificado: 0 violações.
   É este assert que codifica a intenção do usuário; se algum dia ele
   quebrar, a mudança está errada por definição.
8. **Onde a LUT esfriava, saída idêntica ao fonte.** Para os 17.831 nós
   com `dw ≤ 0`, `out' == o` com tolerância `1e-9`. Verificado: 0 difs.

O assert 3 muda de `0.8144` para `0.790588`. O `0.79` parece "menos que
20%", mas é artefato da métrica, que faz média das duas direções do
eixo; no lado quente a atenuação é os 20% inteiros. Não ajustar o
`FATOR` para perseguir `0.8144` — seria reintroduzir o bug.
- Retorno do agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
