<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BE: loudness de fonte mono, teto de bitrate ≤15s e skill × código

Data: 2026-09-27 | Ciclo: BE | Origem: fila de fechamento do Ciclo BD — `BDF16`, `BDF9`, `BDF10`, nessa
ordem, com aprovação explícita do usuário para o design (incluindo a mudança do áudio entregue de fonte
mono e a medição de GOP em segundos no validador). Ciclo anterior: BD (fechado, PR #66).
Evidência de cada achado: `.claude/memory/FINDINGS.md` § "Achados — 2026-09-27".

## Diagnóstico (medido, não presumido)

| achado | medido |
|--------|--------|
| `BDF16` fonte mono sai 3 LU abaixo do alvo | −17,0 LUFS nos dois pipelines (3 s e 10 s), fonte −21,8 LUFS; o upmix `-ac 2` do FFmpeg preserva a loudness integrada, então o `dual_mono` vira erro de −3 LU |
| `BDF9` 2-pass em ≤15s | base do tier `ultra_short` = 12000 = o próprio teto; `mean_q<18` → 13799 médio / 15178 maxrate; `mean_q<21` → 12960 / 14256 |
| `BDF9` CRF padrão em ≤15s | `testsrc2` 1080×1920 60 fps 3 s → 13.656 kbps (`validate_encode.sh` ✗ `≤ 12000`); `maxrate` 13000 > teto médio 12000 |
| `BDF10` skill × código | só o tier ≤15s difere em valor (código 12000/13000/17550 × skill 10000/11200/15000); tier 15–30s do código (9800/11000/14850) ≈ skill; Level 4.1 é aceito (`instagram-ingest-rules.md:14` "4.0 ou 4.1"); `keyint` do código = 2 s, validador exige ≤60 frames — coincidem em 30 fps (padrão), divergem em `--fps 60` |
| cobertura | nenhum teste cobre `get_vbv_preset` nem `_adaptive_2pass_x264_params` (ambas puras); `enhance/test_loudnorm.py` tem dois testes que fixam o `dual_mono` como contrato |

## Decisões (Orquestrador, aprovadas pelo usuário)

1. **`BDF16`: o upmix para estéreo passa a valer para toda fonte que não seja estéreo**, dentro da cadeia
   `-af`, antes do `loudnorm`, nos dois passes. O `dual_mono` é removido, sem flag para manter o
   comportamento antigo. **Muda o áudio entregue:** fonte mono sai perto de −14 LUFS em vez de −17.
2. **`BDF9`: só o tier `ultra_short` desce ao perfil ≤30s da skill** (`target` 10000, `maxrate` 11200,
   `bufsize` 15000). Tiers 15–90s intocados. `vbv_init` intocado (0,9).
3. **`BDF9`: a Regra de Ouro 6 vira invariante do 2-pass**, independente do tier: média ≤ 12000 e
   `maxrate` ≤ 15000 depois de aplicar o fator adaptativo.
4. **`BDF10`: skill passa a descrever o código real** (5 tiers, Level 4.0/4.1, `keyint` ≤2 s). O
   `validate_encode.sh` passa a medir GOP em segundos, porque a regra da plataforma é em tempo e o
   validador é mais estrito que ela em `--fps 60`.
5. **Se o CRF de ≤15s ainda reprovar depois da BE2** (margem estimada de ~2%: 11200 × 1,05 ≈ 11760), o
   executor **não escolhe** a alavanca: para com `blocked` e devolve a medição. A alavanca seguinte
   (baixar `vbv_init` em ≤15s) é decisão do Orquestrador.
6. **Fora do ciclo:** `BDF11`/`12`/`13` (exigem A/B com o usuário), `BDF15`, `BDF17`.

Conhecimento de encoder: `skill: instagram-reels-encoder` § "Regras de Ouro" (regra 6),
`references/instagram-ingest-rules.md` § vídeo e § áudio. Não transcrever — carregar a skill.

## Desenho

### BE1 — loudness de fonte mono (`BDF16`)

- `_loudnorm_channel_prefix(channels)` (`Reels_Encoder_v2_FINAL.py`, localizar por nome): devolve
  `"aformat=channel_layouts=stereo,"` para `channels` truthy e `!= 2`; `""` para 2 e para
  ausente/0 (mesmo default de estéreo que `probe_audio_channels` já usa). Atualizar a docstring: a razão
  deixa de ser "`>2` canais" e passa a ser "medir e normalizar no layout entregue".
- Remover `_loudnorm_dual_mono` e seus dois usos (`build_loudnorm_measure_filter`,
  `build_loudnorm_filter`). Nenhum outro consumidor.
- O `-ac 2` final de `_audio_output_args` fica (vira no-op).
- **TDD:** escrever primeiro o e2e, ver reprovar, só então mudar o código (registrar a saída vermelha no
  STATE). E2e em `enhance/test_loudnorm.py`: fonte `lavfi sine` mono (amplitude padrão, ~−21,8 LUFS),
  medida com `build_loudnorm_measure_filter` → aplicada com `build_loudnorm_filter` → saída medida com
  `ebur128`; afirma `I ∈ [−15, −13]`. Pula (`pytest.skip`) se o FFmpeg resolvido por `ui.binaries` não
  executar. Pré-fix mede ≈ −17,0. Se o pré-fix **não** reproduzir ≈ −17, `blocked` (a hipótese do achado
  seria falsa e o design muda).
- Reescrever `test_dual_mono_for_mono_source` e `test_dual_mono_for_mono`: prefixo `aformat` presente,
  `dual_mono` ausente. Os testes de estéreo e 5.1 ficam intocados e verdes.

### BE2 — teto de bitrate ≤15s (`BDF9`)

- `VBV_PRESETS["ultra_short"]`: `target` 10000, `maxrate` 11200, `bufsize` 15000. O comentário
  `# maxrate × 1.35s` deste tier deixa de valer (15000 ≠ 11200×1,35): trocar por
  `# perfil ≤30s da skill`. Nada mais no dicionário muda.
- Duas constantes de módulo com o nome da regra: `_INGEST_MAX_AVG_KBPS = 12000`,
  `_INGEST_MAX_PEAK_KBPS = 15000`.
- Em `_adaptive_2pass_x264_params`: `adapted_bitrate = min(adapted_bitrate, _INGEST_MAX_AVG_KBPS)`;
  `vbv_maxrate = min(int(adapted_bitrate * 1.10), _INGEST_MAX_PEAK_KBPS)`; `vbv_bufsize` sai do
  `vbv_maxrate` já limitado. O `return` devolve os valores limitados.
- Testes novos em `enhance/test_vbv_ceiling.py` (sem FFmpeg, TDD — reprovam antes):
  - `get_vbv_preset`: 15,0 s → `ultra_short` com 10000/11200/15000; 15,1 s → `short` (9800/11000/14850).
  - `_adaptive_2pass_x264_params`: para cada duração representativa de cada tier × `mean_q` ∈
    {10, 17, 19, 22, 30} × `log_found` ∈ {True, False}: média ≤ 12000 e `maxrate` ≤ 15000.
  - o clamp em si: chamar com `base_bitrate=12000` e `mean_q=10` devolve média 12000 (não 13799) —
    prova que o teto vale mesmo com a base no limite (protege contra alguém subir um tier depois).
- Depois da mudança: `grep -rn "17550" --include=*.py --include=*.md` fora de `.claude/memory` e
  `docs/superpowers`. Cada ocorrência que descreva o tier ≤15s é atualizada; as que não descrevem, listadas
  no retorno.

### BE3 — skill × código (`BDF10`)

- `.claude/skills/instagram-reels-encoder/SKILL.md` § "Perfis de Encode": tabela com os 5 tiers reais
  (valores pós-BE2, lidos de `VBV_PRESETS`, não copiados de memória); nota de que `keyint` é limitado a 2 s
  (`fps × 2`, 1 s em ≤15s); nota de que Level 4.0 e 4.1 são aceitos, o encoder usa 4.1. A Regra de Ouro 6
  não muda.
- `.claude/skills/instagram-reels-encoder/scripts/validate_encode.sh` (linhas de GOP): comparar `MAX_GOP`
  com `ceil(2 × fps)` em vez de `60`, com `fps` lido do stream (`avg_frame_rate` → número). O `ceil` é
  obrigatório: a 29,97 fps o teto é 59,94 e um GOP de 60 frames é válido. Se o fps não for detectável,
  cai no comportamento atual (`≤ 60`). Mensagens passam a citar segundos e o fps medido.
- Prova do script, com fixtures pequenas (`lavfi testsrc2`, 2 s, `libx264 -g N -keyint_min N`, `+bt709`
  irrelevante): 30 fps `-g 60` → ✓; 60 fps `-g 120` → ✓ (antes: ✗); 60 fps `-g 180` → ✗; 30 fps `-g 90`
  → ✗; 29,97 fps `-g 60` → ✓. Registrar só a linha de GOP de cada caso no STATE.
- Não alterar `references/instagram-ingest-rules.md` (já é em tempo).

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| BE1 | § BE1 | executor | `Reels_Encoder_v2_FINAL.py`, `enhance/test_loudnorm.py` | e2e mono reprova antes (≈−17) e passa depois (`I ∈ [−15,−13]`); `grep -n "dual_mono" Reels_Encoder_v2_FINAL.py` → 0; testes de estéreo/5.1 verdes; `ruff check .` limpo (0.14.10) |
| BE2 | § BE2 | executor | `Reels_Encoder_v2_FINAL.py`, `enhance/test_vbv_ceiling.py` (novo) | testes reprovam antes e passam depois; suíte completa verde com e sem FFmpeg no PATH; `ruff check .` limpo |
| BE3 | § BE3 (depois da BE2) | executor | `.claude/skills/instagram-reels-encoder/SKILL.md`, `.claude/skills/instagram-reels-encoder/scripts/validate_encode.sh` | os 5 casos de GOP dão o resultado esperado; tabela do SKILL.md bate com `VBV_PRESETS` (conferir por leitura do dicionário) |
| BE4 | encodes reais + validação | validador | `.claude/memory/VALIDATION.md` | ver § "Validação" |
| BE5 | fechamento: STATE/FINDINGS, memória do usuário, push, PR | Orquestrador | `.claude/memory/*` | — |

Ordem: BE1 → BE1b → BE2 → BE3 → BE3b → BE4 → BE5. Nada em paralelo: BE1 e BE2 editam `Reels_Encoder_v2_FINAL.py`.
Um commit por ID.

Adendos durante a execução (decisão do Orquestrador, registrados no STATE.md):

| ID | origem | agente | arquivos | critério de done |
|----|--------|--------|----------|------------------|
| BE1b | revisão do Orquestrador sobre a BE1: `README.md:327` ainda diz que fonte mono recebe correção `dual_mono` (−3 LU), o que a BE1 tornou falso; o plano não listava o README | executor | `README.md` | a frase descreve o comportamento real (mono, como 5.1, é convertida para estéreo dentro da cadeia, nos dois passes, para medição e entrega usarem o mesmo layout), sem citar `dual_mono` nem prometer número; `grep -n "dual_mono\|-3 LU" README.md` → 0; `npx --yes markdownlint-cli2@0.23.1 README.md` → 0 issues; um commit |
| BE3b | revisão do Orquestrador sobre a BE3: o `SKILL.md` ficou com passagens que contradizem a tabela nova de tiers — as linhas 234–235 citam "Maximum Quality (≤30s)" e "Safe Premium (≥40s)", nomes que agora rotulam os tiers ≤15s e 45–60s; a linha 191 atribui à plataforma um cap de `keyint ≤ 60` em frames, enquanto a tabela diz que a regra é em tempo | executor | `.claude/skills/instagram-reels-encoder/SKILL.md` | 234–235: trocar os nomes pelas faixas de duração ("Reels ≤30s" e "Reels ≥40s"), mantendo os limiares 93 e 90; 191: verificar no código do planejador de GOP (localizar por `gop_profile`) se o cap de 60 é dele e reescrever só a atribuição ("cap do planejador, conservador; a regra da plataforma é 2 s"), sem mudar o número; linhas 79, 85 e 186 (templates de 30 fps) intocadas; um commit |

## Validação (BE4)

Reusar a fonte do BD10: ler o `VALIDATION.md` atual **antes de sobrescrevê-lo** para copiar os comandos
exatos da fixture (`testsrc2` 1080×1920 60 fps 3 s + `sine` mono, tags BT.709). Três encodes pela CLI
(`Reels_Encoder_v2_FINAL.py --help` para a sintaxe), com `--ebu-meter off`:

| # | encode | o que prova |
|---|--------|-------------|
| a | FFmpeg, CRF, defaults | `BDF9` no caminho padrão: bitrate ≤ 12000 kbps (era 13.656) |
| b | FFmpeg, `--mode 2pass` | `BDF9` no 2-pass ponta a ponta com o tier novo |
| c | `--cineon-pipeline on` (CRF) | `BDF16` no pipeline Cineon |

Nos três: `validate_encode.sh` sem ✗ e loudness integrada em [−15, −13] (a fonte é mono, então (a) e (c)
provam o `BDF16`; era −17,0). Se (a) reprovar só no bitrate → `blocked` conforme a decisão 5, com a
medição. VMAF não se aplica (fixture sintética).

## Critérios de aceite do ciclo

1. CI verde nos jobs `lint`, `tests` (4 pernas), `pester` (2) e `pester-winps51` no PR.
2. Fonte mono entregue em −14 ±1 LUFS nos pipelines FFmpeg e Cineon.
3. Nenhum caminho de 2-pass produz média > 12000 ou `maxrate` > 15000 (teste parametrizado).
4. `validate_encode.sh` aprova GOP de 2 s em 30 e 60 fps e reprova acima disso.
5. Tiers 15–90s, dither, tonemap e enhance: bytes idênticos aos de antes.

## Notas de execução

- **Branch:** `claude/ciclo-be-loudnorm-vbv` (já em checkout, a partir de `main` `a402649`). Não trocar
  de branch. Não fazer push — o Orquestrador faz na BE5.
- **Ambiente:** Windows local. **Usar o venv do scratchpad** (Python 3.13.3, PyAV 18.1.0, pytest,
  pytest-timeout, `ruff==0.14.10`, projeto instalado em modo editável):
  `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`.
  **Não usar o Python de sistema** (PyAV 16.1.0, abaixo do piso `av>=17.0.0` do BD2: faz
  `test_cineon_color_io.py::test_red_bt709_full_range` reprovar por ambiente) **nem o `venv/` do projeto**
  (sem pytest; é o venv do launcher do usuário). FFmpeg resolvido por `ui.binaries` (`./bin` → PATH). Suíte canônica:
  `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Para provar o "sem FFmpeg",
  rodar com um PATH que não o contenha e sem `./bin/ffmpeg*` resolvível, e registrar como foi feito.
  Ferramenta ausente (pytest, ruff, ffmpeg) → `blocked`, não instalar nada global.
- **Commits:** um por ID, mensagem convencional em português, terminando com os trailers
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01YAkCQqmjArMiXpfCyrPcuf`.
- **Nunca `git add -A` nem `git add .`** — adicionar por caminho explícito. Não commitar `__pycache__`,
  `enhance_maps/`, `videos/`, `testResults.xml` nem os `docs/*.md` não rastreados que já estão no working
  tree. Não commitar fixtures geradas.
- Sem `[skip ci]` em nenhum commit deste ciclo (armadilha do Ciclo BB).
- STATE.md (261 KB — não ler inteiro): anexar `## Ciclo BE` ao fim, uma linha por ID; saída de comando
  relevante (o e2e vermelho da BE1, os 5 casos de GOP da BE3) em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
