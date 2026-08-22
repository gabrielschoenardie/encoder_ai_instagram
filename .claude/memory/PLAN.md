<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AH: fechar o caso residual do AFF1 (`--lut off`)

Data: 2026-08-22 | Ciclo: AH | Origem: `.claude/memory/FINDINGS.md` § `AFF1`, bloco "Achado novo, não corrigido". Ciclo AG fechado e pushado (`4335218`).

## Diagnóstico

Com `--lut off`, o metadado `comment` do MP4 continua declarando
`HollywoodLUT_v6.8`, embora nenhuma LUT tenha sido aplicada. O Ciclo AG
corrigiu a *versão* da tag mas não o caso de ausência — a tag ainda pode mentir,
só que agora de outro jeito.

**Correção ao que ficou registrado no `FINDINGS.md`:** o achado diz "4 call sites
a tocar". São **2**. Verificado:

| call site | função | precisa mudar? |
| --- | --- | --- |
| `:2665` | `run_ffmpeg` (`:2412`) | **sim** — `lut_enabled` já está na assinatura (`:2416`), em escopo |
| `:2788` | `run_ffmpeg` | **sim** — idem |
| `:3253` | `run_ffmpeg_with_cineon` (`:3003`) | não — passa `cineon_mode=True`, curto-circuita |
| `:3468` | `run_ffmpeg_with_cineon` | não — idem |

O `lut_enabled` nasce em `:4048` (`args.lut == "on"`) e desce por `:2592 → :2366
→ :2266`. Não precisa de parâmetro novo em lugar nenhum além do próprio
`_build_metadata_args`.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AH1 | Escrever este `PLAN.md`. | Orquestrador | `.claude/memory/PLAN.md` | **done** |
| AH2 | Adicionar `lut_enabled: bool = True` a `_build_metadata_args` (`:1925`). No ramo não-Cineon, se `lut_enabled` for falso, `pipeline_tag = "NoLUT"`; caso contrário, a derivação por regex do Ciclo AG, intocada. Repassar `lut_enabled=lut_enabled` nos dois call sites de `run_ffmpeg` (`:2665`, `:2788`). **Não** tocar nos dois de `run_ffmpeg_with_cineon`. | `executor` | `Reels_Encoder_v2_FINAL.py` | pendente |
| AH3 | Testes. Estilo da casa: sem fixtures salvo `tmp_path`, sem `monkeypatch`, sem classes. Acrescentar ao arquivo já criado no Ciclo AG. | `executor` | `enhance/test_output_dir_and_pipeline_tag.py` | pendente |

## Critérios de aceite (AH3)

1. `lut_enabled=False`, não-Cineon → tag é exatamente `NoLUT`.
2. `lut_enabled=True`, não-Cineon → tag segue derivada do filename (regressão do
   Ciclo AG). Continuar **sem hardcodar `v6.8`** como literal solto — extrair da
   constante, como já feito.
3. Default preservado: chamar sem `lut_enabled` mantém o comportamento atual
   (tag derivada). Garante que os 2 call sites de Cineon não mudam de saída.
4. `cineon_mode=True` → `Cineon+Portra400`, **mesmo com `lut_enabled=False`**.
   O `--lut off` não desliga a Portra400 (`cineon_pipeline.py` não conhece
   `lut_enabled`); a tag do Cineon está correta como está e deve continuar.
5. O `comment` completo mantém o formato nos dois modos: `crf:18` para CRF e
   `target:Nk` para 2pass, com o tag novo no lugar do antigo.

## Notas de execução

- **Confirmar antes de codar**, e reportar: `--lut off` realmente não afeta o
  Cineon? A busca por `lut_enabled` em `cineon_pipeline.py` não retorna nada, o
  que sustenta o critério 4 — mas confirme, porque se `--lut off` desligasse a
  Portra400 o critério 4 estaria errado e o plano precisa mudar.
- Tag `"NoLUT"` é literal, sem versão — não há LUT para versionar.
- Anti-escopo: não tocar em áudio (`TP=-1.4` é decisão fechada, ver `FINDINGS.md`),
  LUT, VBV, GOP nem container. Não mexer na derivação por regex do Ciclo AG.
- Baseline: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` →
  **410 passed**. Ao final: 410 + os novos.
- Ao fim, fechar o bloco "Achado novo, não corrigido" do `AFF1` no
  `FINDINGS.md` com o SHA, e **corrigir ali a contagem de call sites de 4 para 2**.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
