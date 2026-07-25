<!-- Escreve: executor / executor-pesado (append-only, nunca reescrever linhas). Lê: Orquestrador. -->
# STATE

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| A2 | done | audit_tmp/audit_cineon_math.py | 3 pontos de referencia + 3 round-trips, todos \|Δ\|≤1e-3 (fwd) / ≤1e-4 (rt) — PASS |
| B1 | done | audit_tmp/audit_cineon_math.py | MATRIX_REC709_TO_DWG max\|Δ\|=4.96e-8, MATRIX_DWG_TO_REC709 max\|Δ\|=2.54e-7 vs colour-science — PASS |
| B2 | done | audit_tmp/audit_cineon_math.py | M_709→DWG·M_DWG→709 max\|Δ\| vs identidade = 6.79e-8 — PASS |
| D2 | done | audit_tmp/audit_cineon_math.py | continuidade no knee Δ=1.19e-8 (PASS), monotonicidade min-derivada=1.31e-5≥0 (PASS), assintota=1.0 (PASS) |
| D3 | done | audit_tmp/audit_cineon_math.py | 7 amostras fora de gamut, max Δhue=1.91e-6° (tolerancia 0.5°) — PASS |
| D4 | done | audit_tmp/audit_cineon_math.py | razao linear (+1 stop, ancora 18% grey) = 2.0000004, \|Δ\|=4.11e-7 — PASS |
| F1 | done | audit_tmp/audit_lut.py | neutralidade max\|canal-media\|=4.44e-16 (PASS); branco Cineon (t=0.6696) saida=1.00164, erro=1.64e-3 (PASS) |
| F2 | done | audit_tmp/audit_lut.py | output(0)=-0.025429, FORA de [0,0.05] — FAIL pelo criterio estrito (toe unclamped abaixo de zero); output(0)≤output(0.0928) sem crush — PASS |
| F3 | done | audit_tmp/audit_lut.py | monotonicidade eixo neutro e R/G/B: min derivada discreta=3.35e-3 (todas ≥0) — PASS |
| F4 | done | audit_tmp/audit_lut.py | 9 amostras skin (grade R×G ±0.03 em torno de (0.55,0.48,0.42), B fixo), Δhue entre -0.86° e -4.40° (tolerancia 5°) — PASS |
| F5 | done | audit_tmp/audit_lut.py | 2a derivada max no highlight [0.9,1.0]=+0.932 (convexo, nao-compressivo) — FAIL pelo criterio estrito; sem hard-clip antes de t=0.95 — PASS; erro no peak (branco Cineon)=1.64e-3 vs tolerancia 3.5e-2 — PASS |
| F6 | done | audit_tmp/audit_lut.py | LUT_3D_SIZE=33 coerente com 35937 pontos, DOMAIN=[0,1], sem NaN/Inf; LUT3D do encoder vs parser proprio em 5 pontos aleatorios, max\|Δ\|=9.54e-8 — PASS |

## Auditoria matematica Cineon + LUT Portra400 — 2026-07-18 14:57:56 -0300

Scripts em `audit_tmp/` (nao commitados): `audit_cineon_math.py` (A2, B1, B2, D2, D3, D4),
`audit_lut.py` (F1-F6). Ambos importam as funcoes reais de `cineon_pipeline.py`
(modulo importado por `Reels_Encoder_v2_FINAL.py` em runtime, linhas 104/3171 —
nao ha argparse/CLI em module-level, import direto seguro). `colour-science`
0.4.7 disponivel, nenhum erro de import. Nenhuma correcao aplicada (fora de escopo
deste ciclo).

Nota de divergencia de escopo (nao bloqueante): o PLAN.md descreve
`_validate_cineon_constants` como parte do escopo em `Reels_Encoder_v2_FINAL.py`;
essa funcao nao foi encontrada no codebase (grep sem match fora de PLAN.md e da
propria skill doc). Isso e tarefa do `leitor` (A3), registrado aqui apenas como
observacao de suporte, sem impacto nos itens do executor.

### Tabela 1 — audit_cineon_math.py (A2, B1, B2, D2, D3, D4)

| ID | medido | esperado | Delta | PASS/FAIL |
|----|--------|----------|-------|-----------|
| A2 (lin=0.0) | 0.09286412596702576 | 0.0928 | 6.412596702576323e-05 | PASS |
| A2 (lin=0.18) | 0.45731961727142334 | 0.457 | 0.0003196172714233225 | PASS |
| A2 (lin=1.0) | 0.6695992350578308 | 0.6697 | -0.00010076494216915144 | PASS |
| A2 roundtrip (lin=0.0) | 0.09286412596702576 | 0.09286412596702576 | 0.0 | PASS |
| A2 roundtrip (lin=0.18) | 0.45731961727142334 | 0.45731961727142334 | 0.0 | PASS |
| A2 roundtrip (lin=1.0) | 0.6695992350578308 | 0.6695992350578308 | 0.0 | PASS |
| B1 MATRIX_REC709_TO_DWG | [[0.562767505645752, 0.3235165476799011, 0.11371593177318573], [0.07775465399026871, 0.7495773434638977, 0.17266802489757538], [0.06466921418905258, 0.1919986605644226, 0.7433321475982666]] | [[0.5627674560071076, 0.32351658870395933, 0.1137159552889327], [0.07775463528504596, 0.7495773461632221, 0.17266801855173203], [0.06466919991632825, 0.19199869204629894, 0.743332108037373]] | 4.9638644306071456e-08 | PASS |
| B1 MATRIX_DWG_TO_REC709 | [[1.8986146450042725, -0.7921761870384216, -0.10643871128559113], [-0.16894882917404175, 1.4889757633209229, -0.3200269937515259], [-0.12153918296098709, -0.3156757652759552, 1.437214970588684]] | [[1.8986148993059058, -0.7921761834040436, -0.10643871590186224], [-0.16894878647615938, 1.4889757541181161, -0.32002696764195643], [-0.12153916060431863, -0.31567585305224316, 1.4372150136565618]] | 2.543016333067527e-07 | PASS |
| B2 roundtrip M_709->DWG . M_DWG->709 | [[0.9999999403953552, -6.786452644291785e-08, -4.240636286567678e-08], [-1.254998860389378e-08, 1.0, -2.207577587398646e-08], [-1.4807612913614321e-08, -6.466514435032877e-09, 1.0]] | [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]] | 6.786452644291785e-08 | PASS |
| D2 continuidade no knee | 0.800000011920929 | 0.8 | 1.1920928910669204e-08 | PASS |
| D2 monotonicidade (min derivada discreta) | 1.3113021850585938e-05 | 0.0 | 0.0 | PASS (derivada negativa = nao-monotonico) |
| D2 assintota <= 1.0 | 1.0 | 1.0 | 0.0 | PASS (output > 1.0 = falha) |
| D3 hue sample [1.600000023841858, 0.05000000074505806, 0.05000000074505806] | 0.0 | 0.0 | 0.0 | PASS |
| D3 hue sample [0.05000000074505806, 1.600000023841858, 0.05000000074505806] | 120.00000000000001 | 119.99999809189768 | 1.9081023197031755e-06 | PASS |
| D3 hue sample [0.05000000074505806, 0.05000000074505806, 1.600000023841858] | -120.00000000000001 | -120.00000000000001 | 0.0 | PASS |
| D3 hue sample [1.399999976158142, -0.30000001192092896, 0.10000000149011612] | -13.003911772115497 | -13.003912130010072 | 3.5789457797363866e-07 | PASS |
| D3 hue sample [-0.20000000298023224, 1.2999999523162842, 0.4000000059604645] | 143.41322679063668 | 143.41322392750058 | 2.8631361033149005e-06 | PASS |
| D3 hue sample [0.8999999761581421, 0.8999999761581421, -0.5] | 60.00000000000001 | 60.00000000000001 | 0.0 | PASS |
| D3 hue sample [1.2000000476837158, 0.6000000238418579, -0.4000000059604645] | 38.21321160375636 | 38.213210098154796 | 1.5056015740810835e-06 | PASS |
| D4 razao linear (+1 stop, ancora 18%) | 2.000000410609775 | 2.0 | 4.106097750700144e-07 | PASS |

### Tabela 2 — audit_lut.py (F1-F6)

| ID | medido | esperado | Delta | PASS/FAIL |
|----|--------|----------|-------|-----------|
| F1 neutralidade max\|canal-media\| (todo t) | 4.440892098500626e-16 | 0.0 | 4.440892098500626e-16 | PASS (pior em t=0.9206) |
| F1 branco Cineon (t=0.6696) saida | [1.0016447381591795, 1.0016447381591798, 1.0016447381591795] | [1.0, 1.0, 1.0] | 0.0016447381591797594 | PASS |
| F2 output(0) em [0, 0.05] | -0.025428999999999997 | [0, 0.05] | -0.025428999999999997 | FAIL (FAIL se fora do intervalo) |
| F2 output(0) <= output(0.0928) | -0.025428999999999997 | 1.5804799999997864e-05 | 0.0 | PASS (FAIL se output(0) > output(0.0928)) |
| F3 monotonicidade eixo neutro (min derivada) | 0.0033467936507936454 | 0.0 | 0.0 | PASS |
| F3 monotonicidade eixo R (min derivada canal R) | 0.003346793650793649 | 0.0 | 0.0 | PASS |
| F3 monotonicidade eixo G (min derivada canal G) | 0.003346793650793649 | 0.0 | 0.0 | PASS |
| F3 monotonicidade eixo B (min derivada canal B) | 0.003346793650793649 | 0.0 | 0.0 | PASS |
| F4 skin hue (R-0.03/G-0.03) | 14.903286460718608 | 16.996088057177158 | -2.0928015964585427 | PASS |
| F4 skin hue (R-0.03/G+0.00) | 33.96362625814996 | 36.586775553629444 | -2.623149295479493 | PASS |
| F4 skin hue (R-0.03/G+0.03) | 53.92661159687444 | 54.79128089714489 | -0.8646693002704637 | PASS |
| F4 skin hue (R+0.00/G-0.03) | 10.553034470217638 | 12.730527788398271 | -2.1774933181806375 | PASS |
| F4 skin hue (R+0.00/G+0.00) | 23.95671978553881 | 27.457076095938245 | -3.5003563103994395 | PASS |
| F4 skin hue (R+0.00/G+0.03) | 39.487677211135946 | 42.51982979723962 | -3.0321525861036775 | PASS |
| F4 skin hue (R+0.03/G-0.03) | 7.960192835702878 | 10.158329786241994 | -2.198136950539123 | PASS |
| F4 skin hue (R+0.03/G+0.00) | 17.883863270860022 | 21.786789298261795 | -3.902926027401776 | PASS |
| F4 skin hue (R+0.03/G+0.03) | 29.73147843239113 | 34.12781030451268 | -4.39633187212155 | PASS |
| F5 roll-off: max segunda derivada (deve ser <=0, compressivo) | 0.9319800000001042 | 0.0 | 0.9319800000001042 | FAIL (positivo = curva convexa (nao-compressiva) nos highlights) |
| F5 sem hard-clip antes de t=0.95 (min derivada 1a, t<0.95) | 8.533759999999816 | >0 | 0.0 | PASS (FAIL se derivada ~0 (clip) antes de t=0.95) |
| F5 erro no peak (branco Cineon t=0.6696) | 1.0016447381591798 | 1.0 | 0.0016447381591797594 | PASS (historico documentado: 2.93e-2 pre-fix) |
| F6 LUT_3D_SIZE coerente com n pontos | 35937 | 35937 | 0 | PASS |
| F6 DOMAIN_MIN/MAX (LUT_3D_INPUT_RANGE) | (0.0, 1.0) | (0.0, 1.0) | 0 | PASS |
| F6 sem NaN | False | False | 0 | PASS |
| F6 sem Inf | False | False | 0 | PASS |
| F6 LUT3D encoder vs parser proprio (pt=[0.7739560604095459, 0.43887844681739807, 0.8585979342460632]) | [1.4960952997207642, 0.3750569522380829, 2.0553667545318604] | [1.4960953067016602, 0.3750569361562729, 2.055366659109116] | 9.54227443727973e-08 | PASS |
| F6 LUT3D encoder vs parser proprio (pt=[0.6973680257797241, 0.09417735040187836, 0.9756223559379578]) | [1.1160802841186523, 0.0005311025306582451, 3.159249782562256] | [1.1160802547531126, 0.0005311025528907775, 3.159249692350387] | 9.021186864188735e-08 | PASS |
| F6 LUT3D encoder vs parser proprio (pt=[0.7611396908760071, 0.7860643267631531, 0.12811362743377686]) | [1.4256491661071777, 1.565720558166504, 0.015849702060222626] | [1.4256491575164796, 1.5657204682712555, 0.015849701885223385] | 8.9895248356342e-08 | PASS |
| F6 LUT3D encoder vs parser proprio (pt=[0.4503859281539917, 0.3707980215549469, 0.926764965057373]) | [0.3966781198978424, 0.2653389275074005, 2.6428868770599365] | [0.3966781126899719, 0.26533893525886537, 2.6428869611511234] | 8.409118690266837e-08 | PASS |
| F6 LUT3D encoder vs parser proprio (pt=[0.6438651084899902, 0.822761595249176, 0.44341421127319336]) | [0.9048219323158264, 1.7981548309326172, 0.3835791051387787] | [0.9048219253845216, 1.7981548368453981, 0.38357909327697753] | 1.1861801152424079e-08 | PASS |

Erros de execucao: nenhum. `colour` importado com sucesso (0.4.7); `cineon_pipeline`
importado sem efeitos colaterais (guard `if __name__ == "__main__"` na linha 989).

## Ciclo de correcao pos-auditoria — 2026-07-25 (G1-G4)

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| G1 | done | cineon_pipeline.py | `_validate_cineon_constants()` escrita (linha ~373-421) com constantes de modulo `CINEON_REF_BLACK=95`, `CINEON_REF_WHITE=685`, `CINEON_GAIN=300`; valida `black_offset` derivado e os 3 pontos de referencia (0.0928/0.457/0.6697) contra `log_encoding_cineon`. `python -c "import cineon_pipeline; cineon_pipeline._validate_cineon_constants()"` -> sem excecao (saida vazia, exit 0). Nota: doc `references/cineon-pipeline.md` linha 117 afirma `black_offset ≈ 0.005012`, mas a propria formula (`10**((95-685)/300)`) da 0.010798 — usei 0.010798 (valor matematicamente consistente com a formula e com os 3 pontos de referencia do mesmo doc, e identico ao literal default de `colour.models.log_encoding_Cineon`). O "≈0.005012" do doc parece erro de aritmetica; registrar em FINDINGS.md, fora do escopo de G4 (que so autoriza tocar a linha 55). |
| G2 | done | cineon_pipeline.py | Call site em `LUT3D.__init__` (linha ~795), dentro do bloco `if lut_file_path is not None:`, antes de `self._load_cube_file(...)`. `LUT3D(cineon_lut_path)` e instanciado uma unica vez em `Reels_Encoder_v2_FINAL.py:3176` (`run_ffmpeg_with_cineon`), antes do loop de decode PyAV que chama `process_frame_full_pipeline()` por frame (linha 3560) — nao e import time, nao e per-frame. Testado: monkeypatch em `cp.log_encoding_cineon` para desviar o ponto black fez `cp.LUT3D('nonexistent_file.cube')` levantar `RuntimeError` da validacao (antes de qualquer `FileNotFoundError` do parser `.cube`), confirmando ordem correta. `grep _validate_cineon_constants cineon_pipeline.py` -> 2 ocorrencias (def na linha 373, call site na linha 795). |
| G3 | done | enhance/test_cineon_constants_guard.py | 7 testes: 1 caso feliz (`test_validate_cineon_constants_passes_with_real_values`), 1 sem colour-science, 5 de adulteracao individual via monkeypatch (`CINEON_REF_BLACK`, `CINEON_REF_WHITE`, `CINEON_GAIN`, `CINEON_EXPECTED_BLACK_OFFSET`, `CINEON_REFERENCE_POINTS`) — todas levantam `RuntimeError`. Refatorei as constantes de locais-a-funcao para modulo (`cineon_pipeline.py`) para tornar cada uma monkeypatchable individualmente, conforme exigido pelo criterio de done do G3. `python -m pytest enhance/test_cineon_constants_guard.py -q` -> `7 passed in 2.09s`. Suite completa dos testes cineon existentes + novo tambem verde: `enhance/test_cineon_log_encoding.py enhance/test_cineon_exposure.py enhance/test_cineon_tonemap.py enhance/test_cineon_dither.py enhance/test_cineon_lut.py enhance/test_cineon_constants_guard.py` -> `29 passed in 2.31s`. |
| G4 | done | .claude/skills/instagram-reels-encoder/references/cineon-pipeline.md | Linha 55 corrigida de `clip [0,1] → ×255 → dither RPDF opcional → round → uint8` para `×255 → dither RPDF opcional → round → clip [0,255] → uint8`, batendo com `quantize_uint8_dithered()` real (linhas 979-982: `scaled=frame*255`; dither opcional; `np.clip(np.round(scaled),0,255)`). `git diff --stat` do arquivo -> `1 file changed, 1 insertion(+), 1 deletion(-)`, nenhuma outra linha tocada. |

## Ciclo H1+H2 — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| H1a | done | .claude/skills/instagram-reels-encoder/references/cineon-pipeline.md | Linha 117: `≈ 0.005012` → `≈ 0.010798`, fórmula intocada. `grep -rn "0.005012" .claude/skills/` → sem match. |
| H1b | done | cineon_pipeline.py | Docstring linha 342 (`log_encoding_cineon`): mesmo valor corrigido para `≈ 0.010798`. `grep -n "0.005012" cineon_pipeline.py` → sem match. |
| H2a | done | cineon_pipeline.py | Removida a chamada `_validate_cineon_constants()` e o comentário de justificativa (linhas ~795-802) de dentro de `LUT3D.__init__`; a função e as constantes de módulo permanecem intactas (linhas 373-421). `grep -n "_validate_cineon_constants" cineon_pipeline.py` → só a definição na linha 389. |
| H2b | done | Reels_Encoder_v2_FINAL.py | `from cineon_pipeline import _validate_cineon_constants` + chamada `_validate_cineon_constants()` inseridos como primeira instrução executável do corpo de `run_ffmpeg_with_cineon` (linhas 2995-2997), antes de `console.rule(...)`, `os.path.abspath`, `probe_video`, qualquer LUT3D ou I/O. `python -c "import ast; ..."` confirma sintaxe válida. |
| H2c | done | enhance/test_cineon_constants_guard.py | Novo teste `test_run_ffmpeg_with_cineon_calls_guard_before_touching_disk_or_ffmpeg`: monkeypatch em `cp._validate_cineon_constants` para levantar `RuntimeError` e em `R.probe_video` para levantar `AssertionError` se chamado; chama `R.run_ffmpeg_with_cineon(input_file="nonexistent-input-does-not-exist.mp4", output_file="nonexistent-output-does-not-exist.mp4")` e afirma `pytest.raises(RuntimeError, match="adulterado para o teste")` — prova que o guard dispara antes de `probe_video` (e, por transitividade, antes de qualquer LUT3D/FFmpeg mais adiante no corpo da função). `python -m pytest enhance/test_cineon_constants_guard.py -q` → `8 passed in 2.61s`. Regressão: `python -m pytest enhance/ ui/ -q` → `4 failed, 342 passed` (as 4 falhas batem exatamente com o baseline pré-existente documentado no PLAN — 2 em `enhance/test_ebu_meter.py`, 2 de encoding de console em `ui/test_readme_assets.py`/`ui/test_theme.py`). |

Nota para FINDINGS.md (fora de escopo, nao investigado): `references/cineon-pipeline.md` linha 117 tem `black_offset = 10^((95-685)/300) ≈ 0.005012` — o valor correto da mesma formula e ≈0.010798 (confirmado batendo com `colour.models.log_encoding_Cineon` default e com os 3 pontos de referencia do proprio doc). Parece typo aritmetico isolado, distinto do bug E3d (linha 55, ja corrigido em G4).

## Ciclo infra/CI — pin ruff + config explicita — 2026-07-25

| I1 | done | .github/workflows/ci.yml | pin `ruff==0.14.10` na linha 22, nenhuma outra linha alterada |
| I2 | done | pyproject.toml | secao `[tool.ruff.lint]` select=[E4,E7,E9,F,I] acrescentada; `python -m ruff check enhance/` (0.14.10) agora reporta 14 erros incluindo I001 |
| I3 | done | 23 arquivos `.py` (lista abaixo) | `python -m ruff check . --fix --select I` → `Found 33 errors (33 fixed, 0 remaining)`; suite pos-fix identica ao baseline (`4 failed, 342 passed`) |

### I3 — evidencia de verificacao (comandos rodados, saida real)

Pre-condicoes conferidas antes de rodar o fix: `python -m ruff --version` → `ruff 0.14.10`
(bate com o pin do I1); `.github/workflows/ci.yml` linha 22 → `run: pip install ruff==0.14.10`;
`pyproject.toml` linhas 51-52 → `[tool.ruff.lint]` / `select = ["E4", "E7", "E9", "F", "I"]`.
Ordem obrigatoria (I1 e I2 antes do I3) respeitada.

Baseline antes do fix:
- `python -m ruff check . --select I --statistics` → `33  I001  [*] unsorted-imports` /
  `Found 33 errors.` / `[*] 33 fixable with the --fix option.` (exit 1) — bate com os 33 do PLAN.
- `python -m pytest enhance/ ui/ -q` → `4 failed, 342 passed in 5.54s`, exatamente as 4 do
  baseline documentado: `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`,
  `enhance/test_ebu_meter.py::test_ffplay_args_basic`,
  `ui/test_readme_assets.py::test_anchor_strings_present`,
  `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`.

Fix: `python -m ruff check . --fix --select I` → `Found 33 errors (33 fixed, 0 remaining)` (exit 0).
`--select I` usado literalmente conforme a nota do PLAN; **nenhum** `--fix` sem `--select` foi
executado, logo os 58 erros pre-existentes de E4/E7/E9/F (tools/, .claude/scripts, ui/)
permanecem intocados.

Criterios de done:
- `python -m ruff check . --select I` → `All checks passed!` (exit 0). **PASS**
- `python -m pytest enhance/ ui/ -q` → `4 failed, 342 passed in 6.03s`, mesmas 4 falhas
  nominais do baseline, zero regressao. **PASS**

Verificacoes extras (nao exigidas, para descartar quebra de import condicional/lazy):
- Comando exato do CI: `python -m ruff check enhance/ --output-format=github` → exit 0, sem output.
- `ast.parse` em todo `.py` do repo (excluindo `audit_tmp/`) → `SYNTAX BAD: []`.
- Import real dos 10 modulos tocados com maior risco (`cineon_pipeline`, `Reels_Encoder_v2_FINAL`,
  `ebu_meter`, `enhance_visualizer`, `ui.components`, `ui.binaries`, `enhance.profile`,
  `enhance.processor`, `enhance.analyzers`, `enhance.ffmpeg_filters`) → todos `OK`, exit 0.
- `python -m py_compile` nos 4 scripts de `tools/` + `analyze_source.py` → `PYCOMPILE OK`.

Revisao manual do diff em `Reels_Encoder_v2_FINAL.py` (o arquivo de risco citado no PLAN):
todas as 20 linhas sao reordenacao dentro de blocos contiguos — stdlib (`shutil` acima de
`subprocess`, `Optional, Tuple`), bloco `rich` (`box` acima de `Console`), os simbolos dentro
do `from cineon_pipeline import (...)` no `try`, os 3 `from enhance.*` no `try`,
`from ui.binaries import FFMPEG, FFPLAY, FFPROBE`, e o par de imports lazy dentro do preflight
(`ui.components` antes de `ui.preflight`). Nenhum import atravessou barreira de codigo:
os blocos `try/except ImportError` que definem `PSUTIL_AVAILABLE`, `CINEON_AVAILABLE` e
`ENHANCE_AVAILABLE` continuam com o mesmo escopo e a mesma ordem relativa entre si.
Em `cineon_pipeline.py`, `import numpy as np` desceu para o grupo third-party depois de
`warnings`/`typing`, com `from __future__ import annotations` intocado no topo.
As unicas insercoes liquidas (`enhance/analyzers/banding.py` +2, `detail.py` +2, `noise.py` +1,
`ui/components.py` +1) sao linhas em branco de separacao de grupo, nao codigo.

Arquivos `.py` alterados pelo fix (23): `.claude/skills/instagram-reels-encoder/scripts/analyze_source.py`,
`Reels_Encoder_v2_FINAL.py`, `cineon_pipeline.py`, `ebu_meter.py`, `enhance_visualizer.py`,
`enhance/analyzers/__init__.py`, `enhance/analyzers/banding.py`, `enhance/analyzers/detail.py`,
`enhance/analyzers/noise.py`, `enhance/processor.py`, `enhance/profile.py`,
`enhance/test_analyzers.py`, `enhance/test_ebu_meter.py`, `enhance/test_loudnorm.py`,
`enhance/test_processors.py`, `enhance/test_profile.py`, `tools/compare_frames_interactive.py`,
`tools/gen_readme_assets.py`, `tools/time_to_frame_interactive.py`,
`tools/verificador_instalacao.py`, `ui/components.py`, `ui/test_config.py`, `ui/test_theme.py`.
`git diff --stat` total: `28 files changed, 129 insertions(+), 97 deletions(-)` — os 5 nao-`.py`
sao `.github/workflows/ci.yml` (I1), `pyproject.toml` (I2) e os 3 markdown de `.claude/memory/`.
Nada commitado, nada revertido.

## Ciclo infra/CI — instalar do pyproject e rodar a suite inteira — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| J1 | done | pyproject.toml | Acrescentado `dev = ["pytest>=7", "pytest-timeout"]` em `[project.optional-dependencies]`, extra `opencv` intocado. `python -m pip install --dry-run -e ".[opencv,dev]"` -> resolve sem erro, `Would install pytest-timeout-2.4.0 reels-encoder-ai-2.1.0` (demais ja satisfeitos). Ambiente local e Python 3.12 (nao 3.9/3.11 da matriz) — nao prova a perna 3.9 citada nas notas de risco; sem erro de resolucao observado aqui. |
| J2 | done | .github/workflows/ci.yml | Linha 54: `pip install numpy>=1.24.0 Pillow>=10.0.0 rich>=13.0.0 psutil>=5.9.0 opencv-python>=4.8.0 scipy pytest pytest-timeout` -> `pip install -e ".[opencv,dev]"`; linha 53 (`python -m pip install --upgrade pip`) intocada. |
| J3 | done | .github/workflows/ci.yml | Linha 47: `hashFiles('requirements.txt')` -> `hashFiles('pyproject.toml')`. |
| J4 | done | .github/workflows/ci.yml | Linha 57: lista de 4 arquivos -> `python -m pytest enhance/ ui/ -v --timeout=60`. |
| J5 | done | — | `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"` -> `OK`, exit 0. |

Nota (nao bloqueante, conforme instrucoes do PLAN): esta maquina nao roda o CI real
(ubuntu-latest, matriz 3.9/3.11); os criterios de done acima sao de sintaxe/resolucao
local, nao de execucao do runner. Verificacao real do resultado do CI e do Orquestrador
apos push.

Achado registrado (fora de escopo, nao investigado): `requirements.txt` mantem os mesmos
9 pacotes do `[project] dependencies` do `pyproject.toml` a mao; apos J2 o CI deixa de ler
`requirements.txt`, que passa a ser documentacao sem execucao — mesma classe de defeito do
ciclo I (config duplicada divergindo sem deteccao). Registrar consolidacao em ciclo proprio.

## Ciclo infra — assumir Python >= 3.11 em todo lugar que declara versao — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| K1 | done | pyproject.toml | linha 10 -> `requires-python = ">=3.11"` |
| K2 | done | pyproject.toml | classifiers agora `["Programming Language :: Python :: 3", "...3.11", "...3.12", "Environment :: Console", ...]`, sem 3.9/3.10 |
| K3 | done | .github/workflows/ci.yml | linha 33 -> `python-version: ["3.11", "3.12"]` |
| K4 | done | .github/workflows/pylint.yml | linha 11 -> `python-version: ["3.11", "3.12"]` |
| K5 | done | README.md | linha 5 badge -> `Python-3.11%2B`; linha 133 tabela -> `3.11+`; `grep -n "3\.9" README.md` -> sem match |
| K6 | done | MANUAL_INSTALACAO.txt | linha 8 -> `Versão Python: 3.11+`, unica linha alterada |
| K7 | done | — | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); yaml.safe_load(open('.github/workflows/pylint.yml')); print('OK')"` -> `OK`, exit 0, ambos parseiam |

Verificacao extra (nota do PLAN): `python -m pytest enhance/ ui/ -q` -> `4 failed, 342 passed in 4.98s`,
as mesmas 4 falhas nominais do baseline documentado (2 em `enhance/test_ebu_meter.py`, 2 de
encoding de console em `ui/test_readme_assets.py`/`ui/test_theme.py`) — zero regressao.
Perna 3.12 nunca rodou no CI real; conforme nota do PLAN, resultado do run apos push e
decisao do Orquestrador, fora do alcance desta maquina.

## Ciclo infra — fechar J-a: requirements.txt aponta para o pyproject — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| L1 | done | requirements.txt | Conteudo substituido por cabecalho de comentario (aponta para `pyproject.toml`, avisa para nao reexpandir) + linha `-e .[opencv]` (sem aspas, sem extra `dev`). Comparacao dos dois `--dry-run`: `pip install --dry-run -r requirements.txt` e `pip install --dry-run -e ".[opencv]"` -> saidas identicas linha a linha (mesmos 9 pacotes "already satisfied" + `Would install reels-encoder-ai-2.1.0`). |
| L2 | done | .github/workflows/ci.yml | Acrescentado step "Validate requirements.txt (end-user install path)" (`pip install --dry-run -r requirements.txt`) logo apos "Install dependencies" no job `tests`; o step "Install dependencies" (`pip install -e ".[opencv,dev]"`) permanece intacto e antes dele. |
| L3 | done | — (so leitura) | `MANUAL_INSTALACAO.txt` linhas 106-129 ("PASSO 1... requirements.txt", "PASSO 3: pip install -r requirements.txt", lista "Isso vai instalar") e linha 250 ("Execute: pip install -r requirements.txt") continuam verdadeiras: o arquivo `requirements.txt` continua existindo e `pip install -r requirements.txt` continua funcionando (confirmado em L1). Achado nao-bloqueante, pre-existente e fora de escopo: linhas 295-309 (`APENDICE A: CONTEUDO DE requirements.txt`) instruem o usuario a criar manualmente um `requirements.txt` com 8 pacotes fixos (falta `pydantic` e `scipy`, que ja faltavam antes deste ciclo) caso o arquivo nao exista — esse conteudo de fallback ja divergia do `pyproject.toml`/`requirements.txt` real antes desta mudanca e diverge ainda mais agora (o arquivo real virou `-e .[opencv]`, nao uma lista fixa). Nao e falso (e so um fallback manual que instalaria pacotes desatualizados, nao usado no caminho normal), mas registrar em FINDINGS.md como candidato a ciclo futuro. |
| L4 | done | — | `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"` -> `OK`, exit 0. `python -m pytest enhance/ ui/ -q` -> `4 failed, 342 passed in 5.76s`, as mesmas 4 falhas nominais do baseline (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`) — zero regressao. |
