<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AG: corrigir AEF1 e AFF1

Data: 2026-08-22 | Ciclo: AG | Origem: `.claude/memory/FINDINGS.md` § `AEF1` e § `AFF1`, ambos abertos pelos Ciclos AE e AF. Ciclos AE e AF estão fechados e pushados (`ab611f7`).

## Diagnóstico

Dois defeitos independentes, ambos de uma linha, ambos sem teste que os cubra.

**`AEF1` — `--output-dir` é no-op silencioso fora de `--batch`.** `args.output_dir`
só é lido dentro do ramo `if args.batch is not None:` (`Reels_Encoder_v2_FINAL.py:4364-4391`).
Em modo single-file o `argparse` aceita o flag sem erro nem aviso e o output vai para
a pasta do input (`:4490-4496`, nome derivado de `{base}_Hollywood_2Pass.mp4`),
sobrescrevendo o que houver lá. **Já causou perda real:** na AE6 destruiu
`videos/calebbrunkow_AFTER_Hollywood_CRF18.mp4` e seus `.qc.json`/`.qc.html`.
O `--help` documenta `[BATCH]` (`:4299`), então não é comportamento oculto — mas
falha destrutiva e silenciosa é a pior combinação, daí a severidade S3.

**`AFF1` — proveniência mentirosa no entregável.** `pipeline_tag = "HollywoodLUT_v6.7"`
é literal em `:1941` e não deriva de `_HOLLYWOOD_LUT_FILENAME` (`:2193`). Vai para o
metadado `comment` de **todo** arquivo entregue (`:1944-1946`). Ficou para trás nos
Ciclos AE e AF: encodes feitos com W80 e com v6.8 declaram `v6.7`. O dano é
diagnóstico — nesta sessão esse campo foi usado para recuperar os parâmetros do
encode de 21/ago e provar que o A/B era honesto; com a tag errada essa recuperação
mente sobre qual LUT gerou o arquivo.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AG1 | Escrever este `PLAN.md`. | Orquestrador | `.claude/memory/PLAN.md` | **done** |
| AG2 | `AEF1`: rejeitar `--output-dir` sem `--batch` via `parser.error()`, logo após o `parse_args()`, antes de qualquer dispatch. Mensagem deve dizer o que fazer, não só o que está errado. | `executor` | `Reels_Encoder_v2_FINAL.py` | pendente |
| AG3 | `AFF1`: derivar `pipeline_tag` de `_HOLLYWOOD_LUT_FILENAME` por regex de versão (`_v(\d+\.\d+[\w-]*)_`), com fallback para o stem do filename se não casar. A tag não pode mais poder mentir. | `executor` | `Reels_Encoder_v2_FINAL.py` | pendente |
| AG4 | Testes para os dois. Estilo da casa: sem fixtures salvo `tmp_path`, sem `monkeypatch`, sem classes. Ver § "Critérios de aceite". | `executor` | onde a casa já testa esse módulo — descobrir e reportar | pendente |

## Critérios de aceite (AG4)

1. `--output-dir X` **sem** `--batch` → `SystemExit` com código 2 (`parser.error`), e a
   mensagem cita `--batch`.
2. `--output-dir X` **com** `--batch` → continua funcionando, sem regressão.
3. `--batch` sem `--output-dir` → continua funcionando.
4. `pipeline_tag` derivado casa a versão do filename atual: com
   `HollywoodCinema_Ultimate_v6.8_3.1-96IRE_...` a tag é `HollywoodLUT_v6.8`.
5. O teste **não** pode hardcodar `v6.8` como literal isolado — tem de derivar do
   mesmo filename, senão volta a poder dessincronizar. Comparar tag contra versão
   extraída da constante.
6. Modo Cineon continua com `pipeline_tag = "Cineon+Portra400"`, intocado.

## Notas de execução

- **AG2 vai logo após `parse_args()`**, não dentro do ramo single-file: o objetivo é
  falhar antes de qualquer efeito colateral, incluindo antes de abrir o input.
- **Não "consertar" honrando o flag em single-file.** Seria mudança de semântica e o
  `--help` já declara `[BATCH]`. A correção conservadora é recusar. Se o usuário quiser
  a outra semântica, é ciclo próprio.
- **Observação a reportar, não a corrigir:** o `comment` também declara
  `HollywoodLUT_*` quando o encode roda com `--lut off`. Se `lut_enabled` estiver
  acessível em `:1936`, **apenas reporte** — não altere neste ciclo.
- Anti-escopo: não tocar em áudio/`loudnorm` (o `TP=-1.4` é item separado, ainda em
  decisão do usuário), nem em LUT, VBV, GOP ou container.
- Baseline a preservar: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q`
  → **405 passed** (medido hoje, pós-push). Ao final: 405 + os testes novos.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
