<!-- Escreve: executor / executor-pesado (append-only, nunca reescrever linhas). Lê: Orquestrador. -->
# STATE

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| A2 | done | audit_tmp/audit_cineon_math.py | 3 pontos de referencia + 3 round-trips, todos \|Δ\|≤1e-3 (fwd) / ≤1e-4 (rt) — PASS |
| B1 | done | audit_tmp/audit_cineon_math.py | MATRIX_REC709_TO_DWG max\|Δ\|=4.96e-8, MATRIX_DWG_TO_REC709 max\|Δ\|=2.54e-7 vs colour-science — PASS |
| B2 | done | audit_tmp/audit_cineon_math.py | M_709→DWG·M_DWG→709 max\|Δ\| vs identidade = 6.79e-8 — PASS |
| D2 | done | audit_tmp/audit_cineon_math.py | continuidade no knee Δ=1.19e-8 (PASS), monotonicidade min-derivada=1.31e-5≥0 (PASS), assintota=1.0 (PASS) |
| D3 | done | audit_tmp/audit_cineon_math.py | 7 amostras fora de gamut, max Δhue=1.91e-6° (tolerancia 0.5°) — PASS |
| Z1 | blocked | ui/launcher.py | tupla removida de TOOLS (linha 60); doc não listava a opção como item numerado (sem edição necessária); py_compile OK; mas `pytest ui/ -q` gera 2 falhas NOVAS (`test_launcher.py::test_tools_flow_runs_tool_then_returns_to_menu`, `::test_tools_flow_subprocess_exception_does_not_crash`) — hardcodam `ask_choice=[4,1,6,1]` com `6`="Voltar" no submenu Ferramentas; com TOOLS de 5→4 itens "Voltar" virou índice 5, então `6` fica fora do range. Correção exige editar `ui/test_launcher.py`, fora da lista de arquivos de Z1 no PLAN.md. PERGUNTA para o Orquestrador: `ui/test_launcher.py` deve entrar no escopo de Z1 (para atualizar a sequência de índices dos 2 testes) ou isso vira um item Z1b/novo ID? Nenhum commit foi feito. |
| Z1 | done | ui/launcher.py, ui/test_launcher.py | Orquestrador ampliou escopo de Z1 (PLAN.md) para incluir ui/test_launcher.py; índices `6`→`5` ("Voltar") corrigidos nos 2 testes; `py_compile` OK; `pytest ui/ -q` → 2 failed, 128 passed (só as 2 falhas nominais pré-existentes: test_readme_assets, test_theme); commit bf6d637 |
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

## Ciclo infra/docs — fechar J-b: APENDICE A desatualizado — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| M1 | done | MANUAL_INSTALACAO.txt | Linhas 294-309 (APENDICE A) reescritas: removida a lista fixa de 8 pacotes e os passos "abra o bloco de notas / cole / salve como .txt"; corpo agora diz que `requirements.txt` normalmente ja vem com o projeto, aponta para `pyproject.toml`, e instrui `pip install -e .[opencv]` na pasta do projeto caso o arquivo falte (sem recriar a mao). `grep -n "pymediainfo\|colour-science" MANUAL_INSTALACAO.txt` -> 6 ocorrencias, todas fora da regiao do apendice A (linhas 122,128,141,142,153,154,246,251,316 — nenhuma entre 294-309); leitura direta das linhas 293-307 confirma o novo texto sem lista hardcoded. |

## Ciclo I-a — fechar debito de lint E4/E7/E9/F fora de `enhance/` — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| N1 | done | tools/compare_frames.py, tools/time_to_frame_interactive.py, ui/prompts.py | `--fix` resolveu os 11 F541 (`f""` -> `""`); E731 e F841 nao tem fix automatico no ruff 0.14.10 (`7 hidden fixes ... --unsafe-fixes`), foram feitos a mao: 6 lambdas nomeadas (`CYAN/GREEN/YELLOW/RED/BOLD/DIM`) viraram `def` com o mesmo corpo `clr(codigo, t)`; `g = glyphs(console)` morto removido de `render_choice_menu` (`glyphs` e pura — so retorna dict, sem efeito colateral; continua importada e usada em `ask_path`). |
| N2 | done | ebu_meter.py, tools/clean_cache.py, tools/compare_frames.py, ui/test_dashboard.py, pyproject.toml | 6 apagados (import morto de verdade) + 6 mantidos com `per-file-ignores`. Ver tabela de decisao abaixo. |
| N3 | done | .claude/skills/instagram-reels-encoder/scripts/analyze_source.py, tools/compare_frames.py, ui/test_binaries.py | 13 E701 + 2 E702 quebrados em linhas separadas, logica identica: `recompression_score` (5 `if ...: s += N`), `_lvl` (2 `if ...: return`), 3 blocos `try: os.remove(f) / except: pass` em `compare_frames.py`, 2 `binp = tmp_path / "bin"; binp.mkdir()` em `test_binaries.py`. |
| N4 | done | Reels_Encoder_v2_FINAL.py, ui/test_components.py | `l` -> `line` na list-comp de `wmic cpu get name` (3 ocorrencias no mesmo comprehension, escopo fechado); `l` -> `landscape` em `test_viewer_frame_portrait_and_landscape` (2 ocorrencias: assignment + assert). Nenhum outro uso de `l` nos escopos. |
| N5 | done | tools/compare_frames.py | 5 `except:` -> `except Exception:` (linhas 268, 439, 463, 470, 477 do arquivo pre-N3). Nenhum dos 5 esta em caminho que dependa de capturar `KeyboardInterrupt`/`SystemExit`: 3 sao `os.remove` de temporario com `pass`, 1 e parse de `--zoom` com fallback, 1 e `get_video_info` com dict default. |
| N6 | done | pyproject.toml | E402 IGNORADO, nao reordenado. Arquivo lido inteiro: linhas 14-17 fazem `_ROOT = dirname(dirname(abspath(__file__)))` + `sys.path.insert(0, _ROOT)`, e so entao as linhas 19-24 importam `version`, `ebu_meter`, `ui.*`. Mover os imports para o topo quebraria `python tools/gen_readme_assets.py` a partir de qualquer cwd — a ordem e proposital (padrao de script standalone descrito na nota de risco do PLAN). `tools/gen_readme_assets.py` nao foi editado. |
| N7 | done | — | Ruff repo inteiro limpo e suite no baseline `4 failed, 342 passed`. Saidas coladas abaixo. |

### N2 — decisao por F401 (os 12 originais, um a um)

| # | ocorrencia | decisao | motivo (verificado por leitura + grep) |
|---|-----------|---------|----------------------------------------|
| 1 | `Reels_Encoder_v2_FINAL.py:105` `COLOUR_AVAILABLE` | mantido + ignore | dentro do `try: from cineon_pipeline import (...)` / `except ImportError: CINEON_AVAILABLE = False` (linhas 103-113) — apagar o simbolo estreita o que o probe verifica |
| 2 | `Reels_Encoder_v2_FINAL.py:106` `LUT3D` | mantido + ignore | mesmo bloco probe; usado no runtime via re-import local em `run_ffmpeg_with_cineon` (linha 3176) |
| 3 | `Reels_Encoder_v2_FINAL.py:107` `process_frame_full_pipeline` | mantido + ignore | mesmo bloco probe; re-import local na linha 3177, chamada na 3564 |
| 4 | `Reels_Encoder_v2_FINAL.py:122` `build_enhance_profile_from_metrics` | mantido + ignore | dentro do `try: from enhance.profile import (...)` / `except ImportError: ENHANCE_AVAILABLE = False` (linhas 117-128) |
| 5 | `Reels_Encoder_v2_FINAL.py:124` `print_enhance_report` | mantido + ignore | mesmo bloco `ENHANCE_AVAILABLE` |
| 6 | `Reels_Encoder_v2_FINAL.py:131` `av` | mantido + ignore | `try: import av / import numpy as np` / `except ImportError: PYAV_AVAILABLE = False`; `av.open` so aparece em 2875/3470, cada um precedido do seu proprio `import av` local (linhas 2873 e 3466) — o do topo e exclusivamente o probe |
| 7 | `ebu_meter.py:33` `sys` | APAGADO | `grep -n "sys\." ebu_meter.py` -> nenhum match; import morto, fora de qualquer try/except |
| 8 | `tools/clean_cache.py:1` `os` | APAGADO | `grep -n "os\." tools/clean_cache.py` -> nenhum match; o modulo usa `pathlib.Path` |
| 9 | `tools/compare_frames.py:18` `Path` | APAGADO | `grep -n "Path" tools/compare_frames.py` -> so a propria linha do import; o modulo usa `os.path` |
| 10 | `tools/verificador_instalacao.py:293` `Reels_Encoder_v2_FINAL` | mantido + ignore | o import E o teste: corpo de `testar_import_projeto()`, dentro de `try/except Exception` que grava `self.results["summary"]["projeto_import"]`. Ja tinha `# pylint: disable=...unused-import` |
| 11 | `ui/test_dashboard.py:5` `EncodeDashboard` | APAGADO | `grep -n EncodeDashboard ui/test_dashboard.py` -> so a linha do import; nenhum teste referencia a classe, e `make_dashboard` (a factory, mesma linha) continua importada e usada |
| 12 | `ui/test_packaging.py:10` `version` | mantido + ignore | unico ponto que prova que o modulo `version` existe/importa; `test_name_and_dynamic_version` so le a string `"version.__version__"` do pyproject, nao importa o modulo. Apagar deixaria `[tool.setuptools.dynamic] version = {attr = "version.__version__"}` sem cobertura nenhuma |

`per-file-ignores` acrescentado em `pyproject.toml` (4 entradas, cada uma restrita a 1 arquivo + 1 regra, com comentario de 1 linha):

```toml
[tool.ruff.lint.per-file-ignores]
# imports de probe: falham dentro de try/except ImportError para definir CINEON_AVAILABLE / ENHANCE_AVAILABLE / PYAV_AVAILABLE
"Reels_Encoder_v2_FINAL.py" = ["F401"]
# o import do projeto e o proprio teste de instalacao (testar_import_projeto)
"tools/verificador_instalacao.py" = ["F401"]
# `import version` e o smoke-check do modulo referenciado por [tool.setuptools.dynamic]
"ui/test_packaging.py" = ["F401"]
# imports do projeto so resolvem depois do sys.path.insert(_ROOT) que roda acima deles
"tools/gen_readme_assets.py" = ["E402"]
```

### N7 — evidencia de verificacao (comandos rodados, saida real)

Baseline medido ANTES de qualquer edicao (`python -m ruff --version` -> `ruff 0.14.10`):

```
$ python -m ruff check . --select E4,E7,E9,F --statistics
13	E701	[ ] multiple-statements-on-one-line-colon
12	F401	[-] unused-import
11	F541	[*] f-string-missing-placeholders
 6	E402	[ ] module-import-not-at-top-of-file
 6	E731	[ ] lambda-assignment
 5	E722	[ ] bare-except
 2	E702	[ ] multiple-statements-on-one-line-semicolon
 2	E741	[ ] ambiguous-variable-name
 1	F841	[ ] unused-variable
Found 58 errors.
[*] 17 fixable with the `--fix` option (7 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

Comando exigido pelo criterio de done do N7 (repo inteiro):

```
$ python -m ruff check . --select E4,E7,E9,F
All checks passed!
RUFF_EXIT=0
```

Mesmo comando com a config do repo sem override de `--select` (cobre tambem o `I` do ciclo I2):

```
$ python -m ruff check .
All checks passed!
RUFF_FULL_EXIT=0
```

Suite de teste:

```
$ python -m pytest enhance/ ui/ -q
ui\test_theme.py:64: AssertionError
=========================== short test summary info ===========================
FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionErr...
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: as...
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeE...
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - Assertion...
4 failed, 342 passed in 5.31s
```

As 4 falhas sao nominalmente identicas ao baseline documentado nos ciclos I3/H2c/K7/L4
(2 em `enhance/test_ebu_meter.py`, 2 de encoding de console em `ui/test_readme_assets.py`
e `ui/test_theme.py`) — zero regressao nova. A suite tambem foi rodada apos N1 (`4 failed,
342 passed in 5.22s`) e apos N2 (`4 failed, 342 passed in 5.05s`), sempre as mesmas 4.

Verificacoes extras (nao exigidas):

```
$ python -m ruff check enhance/ --output-format=github
CI_ENHANCE_EXIT=0
```
(exit 0, sem output — comando literal do CI; `enhance/` nao foi tocado neste ciclo)

```
$ python -m py_compile <os 10 arquivos .py tocados>
PYCOMPILE OK
$ python -c "import ebu_meter; print('ebu_meter OK')"
ebu_meter OK
$ python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['tool']['ruff']['lint']['per-file-ignores'])"
{'Reels_Encoder_v2_FINAL.py': ['F401'], 'tools/verificador_instalacao.py': ['F401'], 'ui/test_packaging.py': ['F401'], 'tools/gen_readme_assets.py': ['E402']}
```

Contabilidade dos 58: 11 F541 + 6 E731 + 1 F841 (N1) + 6 F401 apagados (N2) + 13 E701 +
2 E702 (N3) + 2 E741 (N4) + 5 E722 (N5) = 46 fixados; 6 F401 + 6 E402 = 12 cobertos por
`per-file-ignores` nomeado. 46 + 12 = 58, nenhum sobrando sem explicacao.

Arquivos `.py` tocados neste ciclo (10) + `pyproject.toml`:
`.claude/skills/instagram-reels-encoder/scripts/analyze_source.py`, `Reels_Encoder_v2_FINAL.py`,
`ebu_meter.py`, `tools/clean_cache.py`, `tools/compare_frames.py`,
`tools/time_to_frame_interactive.py`, `ui/prompts.py`, `ui/test_binaries.py`,
`ui/test_components.py`, `ui/test_dashboard.py`. `enhance/` intocado (confirmado por
`git diff --stat`). `MANUAL_INSTALACAO.txt` NAO foi tocado por este agente (Parte 1 / M1).
Nada commitado.

Observacao para o Orquestrador (nao bloqueante, nao corrigido): `tools/compare_frames.py`
linha 2 e `tools/time_to_frame_interactive.py` linha 2 mantem `# pylint: disable=bare-except,
multiple-statements,...` / `unnecessary-lambda-assignment` que ficaram obsoletos apos N3/N5/N1.
Remover e refactor fora do escopo dos itens N1-N7; registrar em FINDINGS.md se interessar.

| O1 | done | README.md | "105 testes" → "111 testes" nas 3 ocorrências (linhas 434, 625, 637), contagem confirmada via `python -m pytest ui/ -q --collect-only` |
| O2 | done | README.md | nota de rodapé da tabela de Requisitos (linha 147) esclarece que `pip install -r requirements.txt` inclui opencv por padrão e que `pip install .` é o caminho sem opencv; marcador `⚪` da tabela não foi alterado |

## Notas de execução O1/O2

Verificação (`superpowers:verification-before-completion`):

```
$ python -m pytest ui/ -q --collect-only | tail -1
111 tests collected in 0.32s

$ grep -n "105 testes" README.md
(sem saída)

$ grep -n "111 testes" README.md
434:│   └── test_*.py                  # Suíte de testes da UI (111 testes)
625:# Só a UI interativa (111 testes)
637:- UI (`ui/`, 111 testes): round-trip do `EncodeConfig`, tokens do tema, render dos

$ grep -n "Dependências opcionais" README.md
147:> ⚪ Dependências opcionais ativam funcionalidades extras mas não são obrigatórias para o funcionamento básico. `pip install -r requirements.txt` (Quick Start e Instalação Completa) instala o opencv-python por padrão via `-e .[opencv]`; para instalar sem opencv use `pip install .` (seção "Instalação via pip").
```

Nenhum outro arquivo tocado (`requirements.txt`, `pyproject.toml`, `.py` intactos).

## Ciclo P — zerar os 112 avisos markdownlint do README.md — 2026-07-25

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| P1a | done | .markdownlint.jsonc | Arquivo criado na raiz com o conteúdo exato do PLAN.md (MD013 off, MD033 allowed_elements div/img/p, MD036 off, MD041 off, comentários `//` preservados). |
| P1b | done | README.md | `npx --yes markdownlint-cli2@0.23.1 --fix README.md` → `Attempted: 92 fixes in 1 file`, `Summary: 6 issues in 1 file` restantes, exatamente os 6 previstos (MD045×1 linha 3, MD040×5 linhas 235/330/361/392/540) — bate com o previsto pelo Orquestrador. |
| P2a | done | README.md | Linha 3: adicionado `alt="Reels Encoder AI"` na tag `<img>` do banner capsule-render, antes de `width="100%"` continuar seguido de `/>`. |
| P2b | done | README.md | 5 fences ASCII sem linguagem trocados de ` ``` ` para ` ```text ` nas linhas 235, 330, 361, 392, 540 (conteúdo dos blocos e fence de fechamento intocados). |
| P3 | done | — (verificação) | `npx --yes markdownlint-cli2@0.23.1 README.md` → `Summary: 0 issues in 0 files`, exit code 0. Nota: texto difere do previsto no PLAN ("0 issues in 1 file") — nesta versão do markdownlint-cli2 o denominador de "N files" no summary conta só arquivos COM issues (0 aqui), não arquivos lintados; substância (0 issues, exit 0) bate com o critério de done. |

### Notas de execução P1-P3

Saída completa de P1b:
```
markdownlint-cli2 v0.23.1 (markdownlint v0.41.1)
Finding: README.md
Linting: 1 file
Attempted: 92 fixes in 1 file
Summary: 6 issues in 1 file
README.md:3:1 error MD045/no-alt-text Images should have alternate text (alt text)
README.md:235 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
README.md:330 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
README.md:361 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
README.md:392 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
README.md:540 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
```

Saída completa de P3 (verificação final, após P2a+P2b):
```
markdownlint-cli2 v0.23.1 (markdownlint v0.41.1)
Finding: README.md
Linting: 1 file
Summary: 0 issues in 0 files
EXIT_CODE=0
```

`git diff --stat README.md .markdownlint.jsonc` (estado final, P1b+P2a+P2b combinados):
```
README.md | 43 +++++++++++++++++++++++--------------------
1 file changed, 23 insertions(+), 20 deletions(-)
```
(`.markdownlint.jsonc` é arquivo novo, não aparece em `--stat` de diff contra HEAD por não estar staged; `git status` confirma `?? .markdownlint.jsonc`.)

Escopo respeitado: `requirements.txt`, `pyproject.toml`, `FINDINGS.md` e todo `.py` intocados
(único diff de conteúdo é `README.md` + `.markdownlint.jsonc` novo). Nada commitado.

## Ciclo Q — launcher portátil (launcher.ps1) — validação de integração — 2026-08-14

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| Q9.0 | done | bin/WindowsTerminal (movido p/ fora do repo), teste.mp4 (copiado) | preparação de baseline: WT da Task 7 movido p/ `C:\Users\Usuario\Documents\GitHub\_task9_wt_backup`, `teste.mp4` (2900358 bytes) copiado da raiz do repo principal |
| Q9.1 | done | — | baseline: venv=False, ffmpeg=False, wt=False antes do teste |
| Q9.2 | done | bin/ffmpeg.exe, bin/ffprobe.exe, bin/ffplay.exe | fetch_ffmpeg.ps1 OK (winget BtbN.FFmpeg.GPL.6.1 6.1.3-20250831), exit 0 |
| Q9.3 | done | venv/, venv.lock | launcher.ps1 -Debug sem args: venv novo + pip install + venv.lock + fallback 2 janelas PowerShell — OK |
| Q9.4 | done | bin/WindowsTerminal/ | fetch_wt_portable.ps1 (checksum confere) + launcher.ps1 -InputFile teste.mp4 -Profile fast -Debug: venv reaproveitado + 2 abas WT reais — OK; encode `--performance speed --enhance off` rodou ponta-a-ponta até DELIVERY READY |
| Q9.5 | done | — | 4 falhas tratadas disparadas de proposito; 3 conferem com a tabela "Falhas tratadas" do spec, 1 (-SkipValidation) divergiu do esperado por causa de ffmpeg no PATH global — ver nota Q9.5-d |
| Q9.6 | done | .claude/memory/STATE.md | checklist e saídas reais registradas neste bloco |

### Nota Q9.0 — por que o Step 0 foi necessário (plan defect)

O plano original assumia que a Task 9 rodaria numa árvore 100% limpa. Não é o
caso: a Task 7 já tinha baixado e extraído `bin/WindowsTerminal/wt.exe` de
verdade nesta mesma worktree (commits `e06fd12`/`cc72648`). Com o WT presente,
o Step 3 nunca exercitaria o caminho de fallback (2 janelas PowerShell) — o
launcher iria direto pro caminho de 2 abas e o resultado não bateria com o
"Expected" documentado. O Orquestrador acrescentou o Step 0 para mover o WT
pra fora da árvore antes do baseline. Também: `teste.mp4` não existe nesta
worktree (só na raiz do repo principal) e precisou ser copiado.

Saída real do Step 0:

```text
--- bin ---
.gitignore
README.md
--- backup ---
True
--- teste.mp4 ---
2900358
```

### Step 1 — baseline

`Test-Path .\venv; Test-Path .\bin\ffmpeg.exe; Test-Path .\bin\WindowsTerminal\wt.exe`

```text
False
False
False
```

### Step 2 — `.\tools\fetch_ffmpeg.ps1`

```text
Instalando FFmpeg 6.1 via winget...
Encontrado FFmpeg (GPL static variant, 6.1 release branch) [BtbN.FFmpeg.GPL.6.1] Versão 6.1.3-20250831
Este aplicativo é licenciado para você pelo proprietário.
A Microsoft não é responsável por, nem concede licenças a pacotes de terceiros.
Baixando https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2025-08-31-13-00/ffmpeg-n6.1.3-win64-gpl-6.1.zip
Hash do instalador verificado com êxito
Extraindo arquivo...
Arquivo extraído com êxito
Iniciando a instalação do pacote...
Variável de ambiente do caminho modificada; reinicie seu shell para usar o novo valor.
O alias da linha de comando foi adicionado: "ffmpeg"
O alias da linha de comando foi adicionado: "ffplay"
O alias da linha de comando foi adicionado: "ffprobe"
Instalado com êxito
OK    ffmpeg.exe -> ./bin
OK    ffprobe.exe -> ./bin
OK    ffplay.exe -> ./bin
Concluido. Binarios em: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\bin
EXIT=0
```

Efeito colateral relevante pro Step 5: o `winget` do `fetch_ffmpeg.ps1` também
instala o FFmpeg **globalmente** e mexe no `PATH` (`where.exe ffmpeg` →
`C:\ffmpeg\bin\ffmpeg.exe`). Isso muda o resultado do cenário `-SkipValidation`
(ver Q9.5-d).

### Step 3 — `.\launcher.ps1 -Debug` (venv novo + WT ausente → fallback)

Primeira tentativa abortou **por artefato do harness de teste, não do
launcher**. Foi invocado como `.\launcher.ps1 -Debug *>&1 | Tee-Object ...`; o
`*>&1` funde o stream de erro no de sucesso e, com o
`$ErrorActionPreference = "Stop"` que o próprio launcher define, o `[notice]`
que o pip escreve em stderr vira um `NativeCommandError` terminante de mensagem
vazia. Saída real da falha:

```text
Successfully installed Pillow-12.3.0 annotated-types-0.8.0 av-18.1.0 colour-science-0.4.7 markdown-it-py-4.2.0 mdurl-0.1.2 numpy-2.5.2 opencv-python-5.0.0.93 psutil-7.2.2 pydantic-2.13.4 pydantic-core-2.46.4 pygments-2.20.0 pymediainfo-7.0.1 reels-encoder-ai-2.1.0 rich-15.0.0 scipy-1.18.0 typing-extensions-4.16.0 typing-inspection-0.4.4
Write-LauncherLog : Não é possível associar o argumento ao parâmetro 'Message' porque ele é uma cadeia de caracteres
vazia.
No C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\launcher.ps1:286
caractere:27
+         Write-LauncherLog $_.Exception.Message "Error"
+                           ~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : InvalidData: (:) [Write-LauncherLog], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : ParameterArgumentValidationErrorEmptyStringNotAllowed,Write-LauncherLog
```

Diagnóstico controlado (mesmo pip install, mesma `$ErrorActionPreference`,
única variável = a fusão de streams):

```text
# COM *>&1
Successfully installed reels-encoder-ai-2.1.0
python.exe :
No linha:1 caractere:32
    + CategoryInfo          : NotSpecified: (:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError

# SEM *>&1
[notice] A new release of pip is available: 25.0.1 -> 26.2.1
Successfully installed reels-encoder-ai-2.1.0
LASTEXITCODE=0
SOBREVIVEU
```

`venv/` e `venv.lock` foram apagados e o Step 3 foi refeito do zero (baseline
reconfirmado: venv=False, ffmpeg=True, wt=False), agora com redirecionamento no
nível do SO (`> log 2>&1`) em vez de fusão de streams do PowerShell. Saída real
completa (78 linhas, `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
./launcher.ps1 -Debug`, exit 0):

```text
[INFO]  Criando venv em C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv ...
[OK]    Venv criado.
[INFO]  Instalando dependencias (pip install -r requirements.txt) ...
Obtaining file:///C:/Users/Usuario/Documents/GitHub/encoder_ai_instagram/.claude/worktrees/launcher-portavel
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Collecting rich>=13.0.0 (from reels-encoder-ai==2.1.0)
  Using cached rich-15.0.0-py3-none-any.whl.metadata (18 kB)
Collecting pydantic<3,>=2 (from reels-encoder-ai==2.1.0)
  Using cached pydantic-2.13.4-py3-none-any.whl.metadata (109 kB)
Collecting numpy>=1.24.0 (from reels-encoder-ai==2.1.0)
  Using cached numpy-2.5.2-cp313-cp313-win_amd64.whl.metadata (6.6 kB)
Collecting av>=11.0.0 (from reels-encoder-ai==2.1.0)
  Using cached av-18.1.0-cp311-abi3-win_amd64.whl.metadata (5.1 kB)
Collecting Pillow>=10.0.0 (from reels-encoder-ai==2.1.0)
  Using cached pillow-12.3.0-cp313-cp313-win_amd64.whl.metadata (9.3 kB)
Collecting psutil>=5.9.0 (from reels-encoder-ai==2.1.0)
  Using cached psutil-7.2.2-cp37-abi3-win_amd64.whl.metadata (22 kB)
Collecting colour-science>=0.4.7 (from reels-encoder-ai==2.1.0)
  Using cached colour_science-0.4.7-py3-none-any.whl.metadata (59 kB)
Collecting pymediainfo>=1.0.0 (from reels-encoder-ai==2.1.0)
  Using cached pymediainfo-7.0.1-py3-none-win_amd64.whl.metadata (9.0 kB)
Collecting scipy>=1.10 (from reels-encoder-ai==2.1.0)
  Using cached scipy-1.18.0-cp313-cp313-win_amd64.whl.metadata (61 kB)
Collecting opencv-python>=4.8.0 (from reels-encoder-ai==2.1.0)
  Using cached opencv_python-5.0.0.93-cp37-abi3-win_amd64.whl.metadata (20 kB)
Collecting annotated-types>=0.6.0 (from pydantic<3,>=2->reels-encoder-ai==2.1.0)
  Using cached annotated_types-0.8.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.46.4 (from pydantic<3,>=2->reels-encoder-ai==2.1.0)
  Using cached pydantic_core-2.46.4-cp313-cp313-win_amd64.whl.metadata (6.7 kB)
Collecting typing-extensions>=4.14.1 (from pydantic<3,>=2->reels-encoder-ai==2.1.0)
  Using cached typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Collecting typing-inspection>=0.4.2 (from pydantic<3,>=2->reels-encoder-ai==2.1.0)
  Using cached typing_inspection-0.4.4-py3-none-any.whl.metadata (2.6 kB)
Collecting markdown-it-py>=2.2.0 (from rich>=13.0.0->reels-encoder-ai==2.1.0)
  Using cached markdown_it_py-4.2.0-py3-none-any.whl.metadata (7.4 kB)
Collecting pygments<3.0.0,>=2.13.0 (from rich>=13.0.0->reels-encoder-ai==2.1.0)
  Using cached pygments-2.20.0-py3-none-any.whl.metadata (2.5 kB)
Collecting mdurl~=0.1 (from markdown-it-py>=2.2.0->rich>=13.0.0->reels-encoder-ai==2.1.0)
  Using cached mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
Using cached av-18.1.0-cp311-abi3-win_amd64.whl (27.6 MB)
Using cached colour_science-0.4.7-py3-none-any.whl (9.1 MB)
Using cached numpy-2.5.2-cp313-cp313-win_amd64.whl (12.5 MB)
Using cached opencv_python-5.0.0.93-cp37-abi3-win_amd64.whl (44.0 MB)
Using cached pillow-12.3.0-cp313-cp313-win_amd64.whl (7.2 MB)
Using cached psutil-7.2.2-cp37-abi3-win_amd64.whl (137 kB)
Using cached pydantic-2.13.4-py3-none-any.whl (472 kB)
Using cached pydantic_core-2.46.4-cp313-cp313-win_amd64.whl (2.1 MB)
Using cached pymediainfo-7.0.1-py3-none-win_amd64.whl (3.3 MB)
Using cached rich-15.0.0-py3-none-any.whl (310 kB)
Using cached scipy-1.18.0-cp313-cp313-win_amd64.whl (36.6 MB)
Using cached annotated_types-0.8.0-py3-none-any.whl (13 kB)
Using cached markdown_it_py-4.2.0-py3-none-any.whl (91 kB)
Using cached pygments-2.20.0-py3-none-any.whl (1.2 MB)
Using cached typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Using cached typing_inspection-0.4.4-py3-none-any.whl (14 kB)
Using cached mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Building wheels for collected packages: reels-encoder-ai
  Building editable for reels-encoder-ai (pyproject.toml): started
  Building editable for reels-encoder-ai (pyproject.toml): finished with status 'done'
  Created wheel for reels-encoder-ai: filename=reels_encoder_ai-2.1.0-0.editable-py3-none-any.whl size=14583 sha256=a4cb1b7be98e1b2cdc63a8237cedecef647d4f08588c345be3659a7bf1cddac2
  Stored in directory: C:\Users\Usuario\AppData\Local\Temp\pip-ephem-wheel-cache-dsbks_a3\wheels\1c\98\08\1bedb6d55bb2d88ab4c0c0b9ed5a5eef5c10a12dec05de1c1d
Successfully built reels-encoder-ai
Installing collected packages: typing-extensions, pymediainfo, pygments, psutil, Pillow, numpy, mdurl, av, annotated-types, typing-inspection, scipy, pydantic-core, opencv-python, markdown-it-py, colour-science, rich, pydantic, reels-encoder-ai
Successfully installed Pillow-12.3.0 annotated-types-0.8.0 av-18.1.0 colour-science-0.4.7 markdown-it-py-4.2.0 mdurl-0.1.2 numpy-2.5.2 opencv-python-5.0.0.93 psutil-7.2.2 pydantic-2.13.4 pydantic-core-2.46.4 pygments-2.20.0 pymediainfo-7.0.1 reels-encoder-ai-2.1.0 rich-15.0.0 scipy-1.18.0 typing-extensions-4.16.0 typing-inspection-0.4.4

[notice] A new release of pip is available: 25.0.1 -> 26.2.1
[notice] To update, run: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv\Scripts\python.exe -m pip install --upgrade pip
[OK]    Dependencias instaladas.
[DEBUG] venv.lock atualizado (diagnostico, nao versionado).
[AVISO] Windows Terminal portatil nao encontrado (C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\bin\WindowsTerminal\wt.exe) - vai usar janelas PowerShell separadas. Rode .\tools\fetch_wt_portable.ps1 para instalar (opcional).
[INFO]  Abrindo janelas PowerShell separadas (fallback) ...
```

Bate com o "Expected" do plano item por item: venv criado, requirements
instalados, `venv.lock` gerado (518 bytes), aviso de WT ausente, fallback de 2
janelas PowerShell.

Prova de que as 2 janelas abriram com os comandos certos (`Win32_Process`):

```text
ProcessId   : 3356
CommandLine : "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoExit -Command & 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' --hardware-info

ProcessId   : 15804
CommandLine : "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoExit -Command & 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' --ui
```

A janela Encode tinha um `python.exe --ui` vivo (PIDs 7068/15684, filhos de
15804) — wizard em execução. A janela Setup já tinha terminado o
`--hardware-info` (one-shot) com o shell vivo por causa do `-NoExit`. Rodando o
mesmo comando de forma capturável para provar que não deu erro:

```text
──────────────────────────── 🔧 Hardware Detection ────────────────────────────
───────────────────────────── 🔧 Hardware Profile ─────────────────────────────
                             🖥️ Hardware Detectado
  CPU             AMD Ryzen 5 2600X Six-Core          3800 MHz
  Cores/Threads   6C / 12T                            Arch: AMD64
  RAM Total       31.9 GB                             Disponível: 22.9 GB 🟢
  Sistema         Windows 10
⚡ Performance Score: █████████░░░░░░░░░░░ 45/100
🏆 Tier: HIGH
  Encoder Threads      12           x264 threads
  Filter Threads       4            Filtros (scale, tonemap, sharpen)
  Decoder Threads      6            Decodificação do input
  Preset x264          slow         Qualidade vs Velocidade
  Lookahead            90           Análise de cena (frames)
EXIT=0
```

Janelas 3356/15804 e os pythons órfãos 7068/15684 fechados antes do Step 4
(recontagem = 0).

### Step 4 — `.\tools\fetch_wt_portable.ps1` + `.\launcher.ps1 -InputFile teste.mp4 -Profile fast -Debug`

Primeira tentativa do `fetch_wt_portable.ps1` falhou, de novo **por artefato do
ambiente do harness, não do script**:

```text
Baixando Windows Terminal 1.24.11911.0 (distribuicao portatil oficial) ...
Verificando SHA256 ...
Get-FileHash : O termo 'Get-FileHash' não é reconhecido como nome de cmdlet, função, arquivo de script ou programa
operável. Verifique a grafia do nome ou, se um caminho tiver sido incluído, veja se o caminho está correto e tente
novamente.
No C:\Users\Usuario\...\tools\fetch_wt_portable.ps1:38 caractere:16
+ $actualHash = (Get-FileHash -Path $TempZip -Algorithm SHA256).Hash
+                ~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (Get-FileHash:String) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : CommandNotFoundException
EXIT=1
```

Causa-raiz: o shell Git Bash exporta um `PSModulePath` poluído com os diretórios
de módulo do PowerShell 7 **na frente** dos do Windows PowerShell, então o
`powershell.exe` 5.1 carrega o manifesto `Microsoft.PowerShell.Utility` do PS7
(versão 7.0.0.0) e não expõe `Get-FileHash`. Prova controlada:

```text
# PSModulePath herdado (poluído)
PSModulePath=C:\Users\Usuario\Documents\PowerShell\Modules;C:\Program Files\PowerShell\Modules;c:\program files\powershell\7\Modules;C:\Program Files\WindowsPowerShell\Modules;C:\Windows\system32\WindowsPowerShell\v1.0\Modules
Microsoft.PowerShell.Utility 7.0.0.0 C:\Windows\System32\WindowsPowerShell\v1.0
(Get-Command Get-FileHash -> nada)

# PSModulePath limpo / não herdado (default nativo do PS 5.1)
Name         Version
----         -------
Get-FileHash 3.1.0.0
PSModulePath=C:\Users\Usuario\Documents\WindowsPowerShell\Modules;C:\Program Files\WindowsPowerShell\Modules;C:\Windows\system32\WindowsPowerShell\v1.0\Modules

# pwsh 7
Get-FileHash 7.0.0.0
```

Um usuário abrindo um PowerShell normal (Explorer/menu Iniciar) recebe o
`PSModulePath` nativo e não é afetado. Todos os comandos restantes desta task
foram rodados com `env -u PSModulePath` para reproduzir essa condição real.

Saída real do `fetch_wt_portable.ps1` (exit 0):

```text
Baixando Windows Terminal 1.24.11911.0 (distribuicao portatil oficial) ...
Verificando SHA256 ...
OK    checksum confere (7691EFEB71C8DD0B95536C84E366FA4CF809A42C534912F9CEFA1056534383BD)
Extraindo para C:\Users\Usuario\AppData\Local\Temp\wt_portable_extract_58e7472e42d241b19620c32f7d19030f ...
OK    Windows Terminal portatil instalado em: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\bin\WindowsTerminal
      wt.exe: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\bin\WindowsTerminal\wt.exe
```

Saída do `launcher.ps1 -InputFile "teste.mp4" -Profile "fast" -Debug` (exit 0;
as 39 linhas do resolvedor do pip entre a linha 2 e a 42 são o bloco
`Requirement already satisfied` / rebuild do editable, idêntico em forma ao do
Step 3):

```text
[INFO]  Venv existente reaproveitado (C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv).
[INFO]  Instalando dependencias (pip install -r requirements.txt) ...
[notice] A new release of pip is available: 25.0.1 -> 26.2.1
[notice] To update, run: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv\Scripts\python.exe -m pip install --upgrade pip
[OK]    Dependencias instaladas.
[DEBUG] venv.lock atualizado (diagnostico, nao versionado).
[INFO]  Abrindo Windows Terminal (2 abas: Setup, Encode) ...
```

Bate com o "Expected": `[INFO] Venv existente reaproveitado`, **nenhum**
`[AVISO]` de WT ausente (WT foi detectado) e caminho de 2 abas em vez de
fallback. Prova do processo real do WT portátil e das 2 abas:

```text
ProcessId   : 14944
Name        : WindowsTerminal.exe
CommandLine : wt.exe new-tab --title Setup powershell -NoExit -Command "& 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' --hardware-info" ; new-tab --title Encode powershell -NoExit -Command "& 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' 'teste.mp4' --performance speed --enhance off"

ProcessId   : 8164
Name        : OpenConsole.exe
CommandLine : "C:\...\launcher-portavel\bin\WindowsTerminal\OpenConsole.exe" --headless --textMeasurement graphemes --width 120 --height 30 ...

ProcessId   : 7928
Name        : OpenConsole.exe
CommandLine : "C:\...\launcher-portavel\bin\WindowsTerminal\OpenConsole.exe" --headless --textMeasurement graphemes --width 120 --height 30 ...

=== powershell tabs ===
ProcessId   : 1600
CommandLine : powershell -NoExit -Command "& 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' --hardware-info"

ProcessId   : 2044
CommandLine : powershell -NoExit -Command "& 'C:\...\venv\Scripts\python.exe' 'C:\...\Reels_Encoder_v2_FINAL.py' 'teste.mp4' --performance speed --enhance off"
```

Os dois `OpenConsole.exe` saem de `bin\WindowsTerminal\` (não do WT do sistema
nem do conpty do VS Code), confirmando que o binário portátil é o que está
sendo usado. Comando da aba Encode reproduzido de forma capturável — rodou
ponta-a-ponta (exit 0, 126 linhas):

```text
⚠ --enhance-ai on requer --enhance on. Ignorando --enhance-ai.
🎲 Dither: Blue-noise ativado — quebra coerência de banding pré-quantização
───────────────── 🎬 Encode CRF 18 - Hollywood LUT Transport ──────────────────
[...]
│ > [libx264 @ 0000025566c80d40] Weighted P-Frames: Y:2.4% UV:0.0%            │
│ > [libx264 @ 0000025566c80d40] ref P L0: 60.3% 14.2% 19.5%  5.9%  0.2%      │
│ > [libx264 @ 0000025566c80d40] ref B L0: 80.6% 16.8%  2.7%                  │
│ > [libx264 @ 0000025566c80d40] kb/s:9385.39                                 │
│ > [aac @ 0000025568a28ec0] Qavg: 533.823                                    │
✓ Render finalizado!
📋 Metadados: BT.709 TV | CRF 18 | VBV Ultra Short (≤15s) — Maximum Quality |
Loudnorm: -14 LUFS
───────────────────── 🎧 EBU R128 — Auditoria pós-encode ──────────────────────
┌─────────────────────┬──────────────────┬────────────────┬────────┐
│ Métrica             │ ANTES (original) │ DEPOIS (final) │   Alvo │
├─────────────────────┼──────────────────┼────────────────┼────────┤
│ Integrated (LUFS-I) │          -14.0 ✓ │        -13.7 ✓ │    -14 │
│ True Peak (dBTP)    │           -3.9 ✓ │         -3.5 ✓ │ ≤ -1.5 │
│ Loudness Range (LU) │              2.7 │            2.7 │    ~11 │
│ Codec               │              aac │            aac │ AAC-LC │
│ Sample Rate (Hz)    │            44100 │          48000 │  48000 │
└─────────────────────┴──────────────────┴────────────────┴────────┘
╔═ MASTER QC ═════════════════════════════════════════════════════════════════╗
║  OK Container  MP4          OK Video  H.264 High@4.1                        ║
║  OK Resolution  1080x1920   OK Bit Depth  8-bit                             ║
║  OK Color  BT.709           OK FPS  30 fps                                  ║
║  OK Loudness  -13.7 LUFS    OK True Peak  -3.5 dBTP                         ║
║  OK Codec  aac              OK Sample Rate  48000                           ║
║                      *  D E L I V E R Y   R E A D Y  *                      ║
╚═════════════════════════════════════════════════════════════════════════════╝
📄 Certificado de entrega: teste_Hollywood_CRF18.qc.html
🎧 Monitor EBU R128 aberto (2 janela(s)) — feche-as quando terminar a inspeção.
EXIT=0
```

Artefatos gerados: `teste_Hollywood_CRF18.mp4` (14986471 bytes),
`teste_Hollywood_CRF18.qc.html` (12984 bytes). Este encode **não** é um encode
validado/aprovado pela metodologia (o Step 4 só exige que o comando dispare e
produza output coerente) — o `DELIVERY READY` acima é o QC do próprio encoder,
não um sign-off do ciclo.

Janela do WT (14944), abas e janelas do medidor EBU (`ffplay`) fechadas —
recontagem `WindowsTerminal`+`ffplay` = 0. Backup `_task9_wt_backup` removido
conforme o plano (o WT real foi re-obtido pelo fetch script nesta task).

### Step 5 — falhas tratadas disparadas de propósito

**Q9.5-a — `requirements.txt` ausente** (renomeado para `requirements.txt.bak`,
restaurado depois):

```text
[INFO]  Venv existente reaproveitado (C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv).
[ERRO]  requirements.txt nao encontrado em: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\requirements.txt
EXIT=1
```

Confere com o spec ("`requirements.txt` ausente → Erro claro com o path
esperado"): a mensagem traz o path absoluto esperado e o exit é 1.

**Q9.5-b — `-SkipEnvSetup` sem venv** (`venv` movido para `venv_bak`,
restaurado depois):

```text
[AVISO] Setup do venv pulado (-SkipEnvSetup).
[ERRO]  -SkipEnvSetup exige um venv existente em C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv, mas Scripts\python.exe nao foi encontrado.
EXIT=1
```

Confere com o comportamento real do `launcher.ps1:259-261`. Relaciona-se à
linha do spec "Criação do venv falha → Sugere `-SkipEnvSetup` pra reusar venv
existente; diagnóstico" pelo lado inverso: aqui é o `-SkipEnvSetup` usado sem
venv, e a mensagem nomeia o path exato e o arquivo faltante.

**Q9.5-c — perfil inválido**:

```text
[INFO]  Venv existente reaproveitado (C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\venv).
[INFO]  Instalando dependencias (pip install -r requirements.txt) ...
[OK]    Dependencias instaladas.
[ERRO]  Perfil 'inexistente' nao existe em launch-config.json. Perfis disponiveis: fast, balanced, quality, cinematic, batch
EXIT=1
```

Este cenário **não está** na tabela "Falhas tratadas" do spec; validado contra o
código real (`Build-ProfileArgs`, `launcher.ps1:177-180`). Bate: nomeia o perfil
inválido, o arquivo de configuração e lista os 5 perfis válidos.

**Q9.5-d — `-SkipValidation` com `bin/ffmpeg.exe` renomeado**. Controle primeiro
(mesma condição, **sem** a flag), para provar que a validação de fato dispararia:

```text
--- controle: sem -SkipValidation ---
[AVISO] Setup do venv pulado (-SkipEnvSetup).
[ERRO]  ffmpeg.exe nao encontrado em: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\launcher-portavel\bin\ffmpeg.exe
Rode .\tools\fetch_ffmpeg.ps1 para baixar o FFmpeg.
EXIT_CONTROLE=1

--- com -SkipValidation ---
[AVISO] Setup do venv pulado (-SkipEnvSetup).
[AVISO] Validacao de binarios pulada (-SkipValidation).
[INFO]  Abrindo Windows Terminal (2 abas: Setup, Encode) ...
EXIT_SKIP=0
```

O controle confere com o spec ("FFmpeg/FFprobe ausentes → Hard fail, instrui
`.\tools\fetch_ffmpeg.ps1`") — mensagem exata, hint exato, exit 1. Com
`-SkipValidation` a validação é pulada e o launcher abre o WT mesmo assim
(exit 0), como o plano previa:

```text
ProcessId   : 2180
CommandLine : wt.exe new-tab --title Setup powershell -NoExit -Command "& 'C:\...\Reels_Encoder_v2_FINAL.py' --hardware-info" ; new-tab --title Encode powershell -NoExit -Command "& 'C:\...\Reels_Encoder_v2_FINAL.py' --ui"
```

**Divergência honesta em relação ao "Expected" do plano:** o plano esperava que
"o erro, se houver, vem de dentro do encoder". Nenhum erro veio. Rodando o
encoder na mesma condição (`bin/ffmpeg.exe` renomeado), ele encodou normalmente
(exit 0) porque o `fetch_ffmpeg.ps1` do Step 2 instalou o FFmpeg **globalmente**
via winget e ele está no `PATH` (`where.exe ffmpeg` → `C:\ffmpeg\bin\ffmpeg.exe`).
Ou seja: nesta máquina o cenário "sem FFmpeg" não é reproduzível só renomeando
`bin/ffmpeg.exe` — a parte verificável (validação pulada + launcher abre mesmo
assim) foi confirmada; a parte "erro do encoder" não pôde ser observada por
causa desse fallback de PATH. `bin/ffmpeg.exe` restaurado depois.

### Estado final da worktree após o Step 5

```text
Test-Path .\venv                        -> True
Test-Path .\bin\ffmpeg.exe              -> True
Test-Path .\bin\WindowsTerminal\wt.exe  -> True
Test-Path .\venv.lock                   -> True

git status --short
 M docs/superpowers/plans/2026-08-13-launcher-portavel.md
```

Artefatos de teste removidos (`teste.mp4`, `teste_Hollywood_CRF18.mp4`,
`teste_Hollywood_CRF18.qc.html`, `teste_Hollywood_CRF18.qc.json`) e backup
`_task9_wt_backup` apagado. O único arquivo modificado é o plano (correção do
Step 0 feita pelo Orquestrador, fora do escopo deste commit — o Step 7 comita
apenas `.claude/memory/STATE.md`).

### Achados para o Orquestrador (não corrigidos — Task 9 não altera código)

1. `launcher.ps1` define `$ErrorActionPreference = "Stop"` e chama comandos
   nativos com `| Out-Host`. Se qualquer chamador funde os streams
   (`*>&1`, `2>&1` no nível do PowerShell), o `[notice]` do pip em stderr vira
   `NativeCommandError` terminante e o `catch` da linha 286 estoura de novo
   porque `$_.Exception.Message` vem vazio e `Write-LauncherLog` tem
   `[Parameter(Mandatory)][string]$Message`. O usuário vê um stack trace do
   PowerShell no lugar de qualquer mensagem útil, e o launcher morre **depois**
   de já ter instalado tudo com sucesso. Não afeta o uso normal (duplo clique /
   PowerShell interativo), mas afeta CI e qualquer wrapper que capture saída.
2. `-SkipValidation` não é observável de ponta a ponta enquanto houver FFmpeg no
   `PATH` global — e o próprio `tools/fetch_ffmpeg.ps1` coloca um lá via winget.
   Se o objetivo é garantir isolamento portátil, vale checar se o encoder
   prefere `./bin/ffmpeg.exe` ao do `PATH`.

## Ciclo R — esclarecer QF2 em launcher.ps1 (2026-08-14)

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| R1a | done | launcher.ps1 | comentário acrescentado acima de `[switch]$SkipValidation` no bloco `param()`, sem mudança de código |
| R1b | done | launcher.ps1 | comentário QF2 acrescentado dentro do bloco `if ($SkipValidation) { ... }`, sem mudança de código |
| R2 | done | launcher.ps1 | `git diff launcher.ps1` conferido — só as 2 linhas de comentário aparecem, nenhuma linha executável tocada (saída abaixo) |

`git diff launcher.ps1`:

```diff
diff --git a/launcher.ps1 b/launcher.ps1
index 814075a..9a068c7 100644
--- a/launcher.ps1
+++ b/launcher.ps1
@@ -9,6 +9,7 @@ param(
     [string]$InputFile,
     [string]$Profile,
     [switch]$Debug,
+    # Pula só a checagem local (Test-Path) de bin/ffmpeg.exe e bin/ffprobe.exe feita por Resolve-Binaries; não impede o encoder de usar FFmpeg do PATH via ui/binaries.py::resolve_binary (que prefere bin/ e cai pro PATH como fallback).
     [switch]$SkipValidation,
     [switch]$SkipEnvSetup
 )
@@ -265,6 +266,7 @@ if ($MyInvocation.InvocationName -ne '.') {
         }
 
         if ($SkipValidation) {
+            # QF2: se houver FFmpeg no PATH global (ex.: instalado via tools/fetch_ffmpeg.ps1/winget), o encoder ainda vai encontrar e usar esse binário mesmo sem o bin/ffmpeg.exe local — -SkipValidation não força isolamento estrito.
             Write-LauncherLog "Validacao de binarios pulada (-SkipValidation)." "Warn"
             $wtPath = Join-Path $Script:RepoRoot $config.paths.windowsTerminalExe
             $binaries = [PSCustomObject]@{
```

## Ciclo S — corrigir QF1 (stderr do pip promovido a erro terminante) em launcher.ps1 (2026-08-14)

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| S1a | blocked | launcher.ps1 | linha `$PSNativeCommandUseErrorActionPreference = $false` aplicada logo após `$ErrorActionPreference = "Stop"` (critério textual do PLAN cumprido), mas a verificação real (S3a/S3b abaixo) mostra que **não neutraliza o gatilho** no motor onde o crash original ocorreu (Windows PowerShell 5.1) — ver pergunta ao Orquestrador abaixo. |
| S2a | done | launcher.ps1 | `catch` agora usa `$errMsg` com fallback quando `$_.Exception.Message` é vazio/nulo, testado e confirmado nos dois motores (S3a/S3b, teste dedicado abaixo) — a chamada `Write-LauncherLog $_.Exception.Message "Error"` original quebra com `ParameterArgumentValidationErrorEmptyStringNotAllowed` quando Message é `""`; com o fallback, não quebra. |
| S3a | done (resultado contradiz o diagnóstico do PLAN) | — | ver evidência abaixo |
| S3b | done (resultado contradiz o diagnóstico do PLAN) | — | ver evidência abaixo |
| S3c | blocked | — | pré-condição do item ("venv já existe de sessões anteriores — reaproveitar, não recriar do zero") não é satisfeita: não há `venv/` nem em `<repo>/venv` nem em `.claude/worktrees/launcher-portavel` (worktree existe como diretório vazio, não registrado em `git worktree list`). Rodar `pip install` de verdade exigiria criar um venv novo, o que o item proíbe explicitamente. |
| S3d | done | — | parse-check OK nos dois motores |

### Evidência S3a/S3b — o mecanismo do crash não é o que o PLAN diagnosticou

Repro sintético (`powershell -Command "[Console]::Error.WriteLine('[notice] fake'); exit 0"`,
`$ErrorActionPreference='Stop'`, script mimetizando `launcher.ps1` invocado com
`*>&1` externo — igual ao `.\launcher.ps1 -Debug *>&1 | Tee-Object` que
causou o crash original):

```text
=== pwsh 7.5.1, SEM fix ===
[notice] fake pip stderr
SOBREVIVEU LASTEXITCODE=0
EXIT_OUTER=0

=== pwsh 7.5.1, COM fix ===
[notice] fake pip stderr
SOBREVIVEU LASTEXITCODE=0
EXIT_OUTER=0

=== powershell.exe 5.1, SEM fix ===
CAPTURADO_NO_SCRIPT: System.Management.Automation.RemoteException MESSAGE='[notice] fake pip stderr'
EXIT_OUTER=-1

=== powershell.exe 5.1, COM fix ===
CAPTURADO_NO_SCRIPT: System.Management.Automation.RemoteException MESSAGE='[notice] fake pip stderr'
EXIT_OUTER=-1
```

`Write-Host "Default value: $PSNativeCommandUseErrorActionPreference"` em pwsh
7.5.1, shell limpo (`-NoProfile`): `Default value: False` — já vem `$false`
por padrão nesta instalação (não `$true` como o PLAN presumia para "pwsh
7.3+").

Conclusão empírica: nesta máquina (pwsh 7.5.1 + Windows PowerShell 5.1.x), o
crash de stderr-mesclado-vira-erro-terminante só reproduz em **Windows
PowerShell 5.1**, onde `$PSNativeCommandUseErrorActionPreference` não existe
e é, como o próprio PLAN já previa, um no-op — só que o PLAN tratava o no-op
como "inofensivo porque o motor de risco é o pwsh 7+"; na prática o motor de
risco real (onde o crash de fato ocorreu no Step 3 original, invocado via
`powershell.exe -File`) é o 5.1, onde a variável nunca teve efeito algum. Em
pwsh 7.5.1 o crash já não ocorre nem sem o fix (o padrão já é `$false` nesta
versão). Ou seja: **S1a não altera o comportamento observável em nenhum dos
dois motores testados nesta máquina** — nem em pwsh (onde já não crashava),
nem em 5.1 (onde continua crashando, com ou sem a linha).

### Evidência S2a — teste dedicado de mensagem vazia (`throw [System.Exception]::new("")`)

```text
=== powershell 5.1 ===
--- SEM S2a (chamada direta, replica o bug original) ---
QUEBROU_DE_NOVO: Não é possível associar o argumento ao parâmetro 'Message' porque ele é uma cadeia de caracteres vazia.
--- COM S2a (fallback) ---
[Error] Erro sem mensagem (possivel stderr de comando nativo promovido a erro terminante). Rode com -Debug para ver o stack trace completo.
NAO_QUEBROU
=== pwsh 7 ===
--- SEM S2a (chamada direta, replica o bug original) ---
QUEBROU_DE_NOVO: Cannot bind argument to parameter 'Message' because it is an empty string.
--- COM S2a (fallback) ---
[Error] Erro sem mensagem (possivel stderr de comando nativo promovido a erro terminante). Rode com -Debug para ver o stack trace completo.
NAO_QUEBROU
```

S2a confirmado nos dois motores: elimina o crash secundário (exceção não
tratada dentro do próprio `catch`, mascarando o erro real com stack trace de
parameter-binding do PowerShell) de forma independente de S1a.

### Evidência S3d — parse-check

```text
powershell 5.1: PARSE_OK
pwsh 7.5.1:     PARSE_OK_PWSH
```

### Pergunta ao Orquestrador (S1a bloqueado)

O diagnóstico original (Task 9 / PLAN.md linhas 11-29) atribui o crash a
`$PSNativeCommandUseErrorActionPreference` (feature de pwsh 7.3+), mas o
crash reproduzido no Step 3 original foi invocado via `powershell.exe`
(Windows PowerShell 5.1 — ver `CommandLine` nos logs de STATE.md em torno da
linha 640), motor onde essa variável não existe e nunca teve efeito. A causa
real observável do `NativeCommandError`/`RemoteException` em 5.1 é o
comportamento clássico e sempre existente de "stderr mesclado via
`*>&1`/`2>&1` vira registro de erro no stream de erro, terminante sob
`$ErrorActionPreference='Stop'`" — independente dessa variável. S2a (a
blindagem do `catch`) resolve o crash-sobre-crash e a mensagem confusa, mas
**não** resolve o falso-negativo em si (o launcher ainda sai com `exit 1`
mesmo quando `pip install` teve sucesso, quando um chamador funde streams via
`*>&1`/`2>&1` sob Windows PowerShell 5.1). Pergunta exata: o Orquestrador
quer (a) manter S1a como está (documentado como mitigação parcial/vácua nesta
máquina, sem reverter — é inofensiva) e fechar QF1 como "parcialmente
corrigido" citando esse limite, ou (b) reabrir um novo ciclo de diagnóstico
para endereçar a causa real em Windows PowerShell 5.1 (ex.: capturar stderr
do `pip install` explicitamente com `2>$null` + checagem de `$LASTEXITCODE`
em vez de depender de `$ErrorActionPreference`, já que os testes acima
mostram que isso é o único caminho que sobreviveria nos dois motores)?

## Ciclo T — corrigir a causa real do QF1 em Windows PowerShell 5.1 (2026-08-14)

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| T1a | done | launcher.ps1 | `New-ProjectVenv` — `& $pythonCmd -m venv $VenvPath \| Out-Host` envolvida em try/finally escopando `$ErrorActionPreference = "Continue"` durante a chamada, restaurado no finally; `if ($LASTEXITCODE -ne 0)` inalterado. |
| T1b | done | launcher.ps1 | Mesmo padrão em `Install-Requirements` (`& $VenvPython -m pip install -r $reqPath \| Out-Host`). |
| T1c | done | launcher.ps1 | Mesmo padrão em `Write-VenvLock` (`& $VenvPython -m pip freeze \| Out-File ...`). |
| T2a | done | — | Repro sintético do Ciclo S, adaptado pro padrão try/finally novo (função `Invoke-FakeNative` com o mesmo wrapper), em Windows PowerShell 5.1: `SOBREVIVEU`. |
| T2b | done | — | Mesmo repro em pwsh 7 (via `command -v pwsh` — disponível nesta máquina): `SOBREVIVEU`, sem regressão. |
| T2c | done | — | `Install-Requirements` real (venv novo criado na raiz do repo, gitignored) invocado por dot-source de `launcher.ps1` sob `powershell.exe 5.1`, com streams mesclados pelo chamador externo (`2>&1` no bash externo, equivalente ao `*>&1` de um chamador PowerShell): pip install real completo, log "Dependencias instaladas." emitido, `EXIT_OUTER=0`, sem `NativeCommandError`/`RemoteException`. `venv/` e `venv.lock` removidos depois do teste. |
| T2d | done | — | Parse-check nos dois motores após o try/finally: `PARSE_OK` (powershell 5.1) e `PARSE_OK_PWSH` (pwsh 7). |

### Evidência T2a/T2b — repro sintético sobrevive nos dois motores com o padrão novo

```text
=== powershell.exe 5.1, COM fix (ciclo T) ===
[notice] fake pip stderr
SOBREVIVEU LASTEXITCODE=0
EXIT_OUTER=0

=== pwsh 7, COM fix (ciclo T) ===
[notice] fake pip stderr
SOBREVIVEU LASTEXITCODE=0
EXIT_OUTER=0
```

Diferença em relação ao Ciclo S: em Windows PowerShell 5.1, sem o fix, o
mesmo repro dava `CAPTURADO_NO_SCRIPT: System.Management.Automation.RemoteException`
com `EXIT_OUTER=-1`. Com o `$ErrorActionPreference = "Continue"` escopado
por `finally`, o mesmo motor agora sobrevive.

### Evidência T2c — pip install real sob 5.1, streams mesclados, sem erro

Trecho relevante da saída (execução completa, dot-source de `launcher.ps1`,
`New-ProjectVenv` + `Install-Requirements` chamadas diretamente, streams
mesclados pelo chamador externo):

```text
[INFO]  Criando venv em ...\venv ...
[OK]    Venv criado.
[INFO]  Instalando dependencias (pip install -r requirements.txt) ...
... (pip install completo, incluindo "[notice] A new release of pip is available: ...") ...
Successfully installed Pillow-12.3.0 ... reels-encoder-ai-2.1.0 ...
[OK]    Dependencias instaladas.
T2C_FIM_OK
EXIT_OUTER=0
```

Confirma que o `[notice]` do pip (a causa raiz original do crash na Task 9)
não dispara mais `NativeCommandError`/`RemoteException` sob Windows
PowerShell 5.1, mesmo com streams mesclados pelo chamador.

### Evidência T2d — parse-check

```text
powershell 5.1: PARSE_OK
pwsh 7:         PARSE_OK_PWSH
```

### Conclusão

QF1 corrigido — o repro sintético do Ciclo S e o `pip install` real
sobrevivem agora em Windows PowerShell 5.1 (o motor de produção real) com
`*>&1`/streams mesclados pelo chamador, sem regressão em pwsh 7. `FINDINGS.md`
atualizado de "parcialmente corrigido — bloqueado (ciclo S)" para "corrigido
— ciclo T".

## Ciclo U — Pester para o launcher — 2026-08-15

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| U1 | done | tests/launch-config.Tests.ps1 | contrato do JSON — 13 blocos `It`, 21 testes expandidos |
| U2 | done | tests/launcher.Tests.ps1 | dot-source + `Build-*` — total acumulado 57 testes |
| U3 | done | tests/launcher.Tests.ps1 | `Initialize-Environment` / `Resolve-Binaries` — total acumulado 75 testes |
| U4 | done | tests/launcher.Tests.ps1 | `Read-LauncherConfig` / `Write-LauncherLog` / fallback — total acumulado 91 testes |
| U5 | done | .github/workflows/ci.yml | job `pester`, matriz ubuntu-latest + windows-latest, `fail-fast: false` |
| U6 | **blocked** | .claude/memory/STATE.md, .claude/memory/FINDINGS.md | push feito, mas o workflow `CI` **não disparou** na branch `worktree-pester-launcher` (o filtro `branches:` não cobre esse nome) — sem run, sem evidência dos dois legs. Ver `UF1` em FINDINGS.md e a pergunta exata no fim desta seção |

### Evidência U6-a — push real (Step 1)

```text
$ git push -u origin HEAD
remote:
remote: Create a pull request for 'worktree-pester-launcher' on GitHub by visiting:
remote:      https://github.com/gabrielschoenardie/encoder_ai_instagram/pull/new/worktree-pester-launcher
remote:
branch 'worktree-pester-launcher' set up to track 'origin/worktree-pester-launcher'.
To https://github.com/gabrielschoenardie/encoder_ai_instagram.git
 * [new branch]      HEAD -> worktree-pester-launcher
```

HEAD empurrado: `1e82cee6c61d0dfe0bbcbea05800d2517aa5bd4c`
(`ci: rodar Pester do launcher em ubuntu-latest e windows-latest`).

### Evidência U6-b — o workflow `CI` não disparou (Step 1/2, causa do bloqueio)

```text
$ gh run list --branch worktree-pester-launcher --limit 10
in_progress    ci: rodar Pester do launcher em ubuntu-latest e windows-latest    Pylint    worktree-pester-launcher    push    31921009460    33s    2026-08-16T02:03:58Z
```

```text
$ gh run list --workflow=ci.yml --limit 5
completed  success  docs: design + plano dos testes Pester para o launcher (Ciclo U) (#38)   CI  main                      push          31887342201  33s  2026-08-15T13:29:25Z
completed  success  docs: design + plano dos testes Pester para o launcher (Ciclo U)         CI  claude/slack-session-...  pull_request  31887211825  41s  2026-08-15T13:26:25Z
completed  success  docs(plans): plano de implementação dos testes Pester (6 tasks, Ciclo U) CI  claude/slack-session-...  push          31887149285  39s  2026-08-15T13:25:01Z
completed  success  fix(launcher): isolar EAP por chamada nativa - resolve QF1 em Windows... CI  main                      push          31853015423  38s  2026-08-15T00:14:49Z
completed  success  docs(memory): registrar plano do Ciclo R (esclarecimento QF2)            CI  main                      push          31823201266  41s  2026-08-14T17:16:08Z
```

Nenhum run de `CI` para a branch empurrada — só o `Pylint` rodou. Causa raiz
medida, comparando os gatilhos dos dois workflows:

```text
$ head -8 .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, "claude/**", "feature/**"]
  pull_request:
    branches: [main]
```

```text
$ head -4 .github/workflows/pylint.yml
name: Pylint

on: [push]
```

`worktree-pester-launcher` não casa com `main`, `claude/**` nem `feature/**`,
então o `push` não dispara o `CI` — e o `CI` é quem contém o job `pester`
criado em U5. O `Pylint` usa `on: [push]` sem filtro, por isso apareceu.
`gh run watch` não tem run para observar; `ci.yml` não tem `workflow_dispatch`,
então `gh workflow run` também não é opção sem alterar o arquivo.

Steps 3 e 4 do brief (ler os dois legs / colar evidência de CI) ficam **sem
evidência** até o desbloqueio. Não houve divergência entre legs a interpretar
porque não houve leg nenhum.

### Evidência U6-c — evidência local real, anterior ao CI (contexto)

Ao contrário do que o spec original assumia (§ Validação: "não há `pwsh` no
sandbox de desenvolvimento"), **este** ambiente tem pwsh 7.5.1 e Windows
PowerShell 5.1 com Pester 5.7.1, e os 91 testes já rodaram nos dois motores
durante as Tasks 1-4. Saída bruta, copiada de
`.superpowers/sdd/2026-08-14-pester-launcher/task-4-report.md` (estado final da
suíte, após U4):

```text
$ pwsh -NoProfile -Command "Invoke-Pester -Path ./tests -CI"

Starting discovery in 2 files.
Discovery found 91 tests in 261ms.
Running tests.
[+] ...\tests\launch-config.Tests.ps1 849ms (245ms|432ms)
[+] ...\tests\launcher.Tests.ps1 1.28s (918ms|298ms)
Tests completed in 2.16s
Tests Passed: 91, Failed: 0, Skipped: 0, Inconclusive: 0, NotRun: 0
```

```text
$ powershell.exe -NoProfile -Command "Invoke-Pester -Path ./tests -CI"

Starting discovery in 2 files.
Discovery found 91 tests in 1.02s.
Running tests.
[+] launch-config.Tests.ps1 3.95s (1.35s|1.87s)
[+] launcher.Tests.ps1 3.08s (2.42s|476ms)
Tests completed in 7.14s
Tests Passed: 91, Failed: 0, Skipped: 0, Inconclusive: 0, NotRun: 0
```

Isso **não substitui** a evidência de CI que a U6 pede — os runners do GitHub
Actions são outro ambiente (`ubuntu-latest` não tem Windows PowerShell 5.1, tem
pwsh 7 sobre Linux, com separador de path e case-sensitivity diferentes, que é
exatamente a superfície que o Step 3 do brief manda vigiar). Mas registra-se
aqui que a suíte **não** está "implementada e nunca executada": ela já rodou
verde nos dois motores de PowerShell da máquina Windows antes do push.

### Evidência U6-d — suíte pytest sem regressão (Step 5)

```text
$ python -m pytest ui/ enhance/ -q
=========================== short test summary info ===========================
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeE...
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - Assertion...
FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionErr...
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: as...
4 failed, 365 passed in 6.90s
```

As 4 falhas são exatamente as 4 nominais do baseline histórico (encoding de
console no Windows; ver item L4 do Ciclo L e item N7 do Ciclo N nesta mesma
página). Zero regressão. Prova mais forte que a contagem: nenhum arquivo Python
foi tocado pelo ciclo — o diff completo contra `origin/main` são 3 arquivos,
todos só-adição:

```text
$ git diff --stat origin/main
 .github/workflows/ci.yml      |  29 +++
 tests/launch-config.Tests.ps1 | 121 +++++++++++
 tests/launcher.Tests.ps1      | 476 ++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 626 insertions(+)
```

### Evidência U6-e — `launcher.ps1` intacto no ciclo inteiro (Step 6)

```text
$ git diff --stat origin/main -- launcher.ps1 launch-config.json
(nenhuma linha de saída)
```

Saída vazia, como o critério exige. A Global Constraint mais importante do
plano (read-only em `launcher.ps1` e `launch-config.json`) está fechada: os
dois arquivos não têm uma linha alterada desde `origin/main`.

### Pergunta exata ao Orquestrador (desbloqueio da U6)

O trabalho das Tasks 1-5 está completo e empurrado; falta só um run de `CI` na
branch. Existem três caminhos, e a escolha é de escopo — não improviso:

1. **Abrir PR `worktree-pester-launcher` → `main`.** Dispara o `CI` pelo gatilho
   `pull_request: branches: [main]`, sem tocar em arquivo nenhum e sem merge. É
   o caminho usado pelo próprio ciclo anterior (PR #38). Recomendado.
2. **Empurrar o mesmo HEAD para um nome que case com o filtro** (ex.:
   `git push origin HEAD:feature/pester-launcher`). Dispara pelo gatilho de
   `push`, mas deixa uma branch duplicada no remote.
3. **Alterar `.github/workflows/ci.yml`** para cobrir o padrão de nome que a
   ferramenta de worktree gera e/ou adicionar `workflow_dispatch`. É a correção
   real do `UF1`, mas é arquivo fora da lista da U6 e mudança de escopo —
   precisa de item próprio no PLAN.

Nenhuma foi executada.

## Ciclo U — U6 desbloqueada: CI verde nos dois legs — 2026-08-15

Ruling do humano, via Orquestrador: **caminho 1** (abrir PR para `main`, sem
merge, só para disparar o gatilho `pull_request`). `ci.yml` **não** foi editado —
a correção do `UF1` continua fora do escopo desta task. Esta seção é append; a
linha `| U6 | blocked |` da tabela acima fica preservada por causa da regra
append-only do arquivo, e é substituída pela linha abaixo.

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| U6 | done | .claude/memory/STATE.md, .claude/memory/FINDINGS.md | CI **verde nos dois legs**, 91/91 em cada um. Run: <https://github.com/gabrielschoenardie/encoder_ai_instagram/actions/runs/31921343582> (evento `pull_request`, PR de diagnóstico <https://github.com/gabrielschoenardie/encoder_ai_instagram/pull/39>, sha `16e3a2a`). Zero divergência entre legs |

### Evidência U6-f — como o run foi disparado (parte do `UF1`)

O run **não** veio de push direto: o filtro `on.push.branches` do `ci.yml` não
cobre `worktree-pester-launcher` (`UF1`). Foi preciso abrir o PR #39
(`worktree-pester-launcher` → `main`) só para acionar o gatilho
`on.pull_request.branches: [main]`. O PR fica **aberto e sem merge** — é
instrumento de diagnóstico, não entrega.

```text
$ gh pr create --base main --head worktree-pester-launcher --title "test(launcher): cobertura Pester para launcher.ps1 (Ciclo U)" ...
https://github.com/gabrielschoenardie/encoder_ai_instagram/pull/39
```

```text
$ gh run list --workflow=ci.yml --limit 3
in_progress    test(launcher): cobertura Pester para launcher.ps1 (Ciclo U)  CI  worktree-pester-launcher  pull_request  31921343582  4s   2026-08-16T02:11:53Z
completed  success  docs: design + plano dos testes Pester para o launcher (Ciclo U) (#38)  CI  main  push  31887342201  33s  2026-08-15T13:29:25Z
completed  success  docs: design + plano dos testes Pester para o launcher (Ciclo U)        CI  claude/slack-session-fp2uqr  pull_request  31887211825  41s  2026-08-15T13:26:25Z
```

Consequência prática do `UF1`, agora medida e não só prevista: **enquanto o
filtro não for corrigido, o job `pester` só roda se alguém abrir um PR.** Um
push direto para uma branch de worktree passa com `Pylint` verde e zero teste do
launcher executado.

### Evidência U6-g — resultado do run (Step 2)

```text
$ gh run view 31921343582 --json status,conclusion,url,headSha,event
status=completed conclusion=success event=pull_request sha=16e3a2a89039eb3e8de574c4a7245badd55da825
url=https://github.com/gabrielschoenardie/encoder_ai_instagram/actions/runs/31921343582
```

```text
$ gh run view 31921343582 --json jobs
Pester (launcher.ps1) (windows-latest) | completed | success | .../job/95101567161
Pester (launcher.ps1) (ubuntu-latest)  | completed | success | .../job/95101567167
Tests (Python 3.12)                    | completed | success | .../job/95101567189
Lint (ruff)                            | completed | success | .../job/95101567203
Tests (Python 3.11)                    | completed | success | .../job/95101567253
```

### Evidência U6-h — leg `ubuntu-latest` (saída bruta, ANSI removido)

`$PSVersionTable` do passo de diagnóstico:

```text
shell: /usr/bin/pwsh -command ". '{0}'"

Name  : PSVersion
Value : 7.6.4

Name  : PSEdition
Value : Core

Name  : GitCommitId
Value : 7.6.4

Name  : OS
Value : Ubuntu 24.04.4 LTS

Name  : Platform
Value : Unix

Name  : PSCompatibleVersions
Value : {1.0, 2.0, 3.0, 4.0…}

Name  : PSRemotingProtocolVersion
Value : 2.4

Name  : SerializationVersion
Value : 1.1.0.1
```

`OS matrix leg: ubuntu-latest`

Pester disponível após o `Install-Module` e a execução:

```text
Name   Version
----   -------
Pester 6.1.0
Pester 5.9.0

Running tests from 2 files.
[+] /home/runner/work/encoder_ai_instagram/encoder_ai_instagram/tests/launch-config.Tests.ps1 838ms (21 tests)
[+] /home/runner/work/encoder_ai_instagram/encoder_ai_instagram/tests/launcher.Tests.ps1 2.74s (70 tests)
Tests completed in 3.61s
Tests Passed: 91, Failed: 0, Skipped: 0, Inconclusive: 0, NotRun: 0
```

### Evidência U6-i — leg `windows-latest` (saída bruta, ANSI removido)

`$PSVersionTable` do passo de diagnóstico:

```text
shell: C:\Program Files\PowerShell\7\pwsh.EXE -command ". '{0}'"

Name  : PSVersion
Value : 7.6.4

Name  : PSEdition
Value : Core

Name  : GitCommitId
Value : 7.6.4

Name  : OS
Value : Microsoft Windows 10.0.26100

Name  : Platform
Value : Win32NT

Name  : PSCompatibleVersions
Value : {1.0, 2.0, 3.0, 4.0…}
```

`OS matrix leg: windows-latest`

Pester disponível após o `Install-Module` e a execução:

```text
Name   Version
----   -------
Pester 6.1.0
Pester 5.9.0
Pester 3.4.0

Running tests from 2 files.
[+] D:\a\encoder_ai_instagram\encoder_ai_instagram\tests\launch-config.Tests.ps1 1.29s (21 tests)
[+] D:\a\encoder_ai_instagram\encoder_ai_instagram\tests\launcher.Tests.ps1 2.35s (70 tests)
Tests completed in 3.78s
Tests Passed: 91, Failed: 0, Skipped: 0, Inconclusive: 0, NotRun: 0
```

### Evidência U6-j — divergência entre legs (Step 3)

**Nenhuma.** `91 passed / 0 failed` idênticos nos dois legs, mesma partição por
arquivo (21 + 70), inclusive com separador de path oposto (`/home/runner/...`
vs `D:\a\...`) e com case-sensitivity de sistema de arquivos diferente. Os três
candidatos a divergir previstos no spec § "Riscos conhecidos" — asserção de path
que escapou do `-match`, `Mock Write-Host` interferindo na saída do Pester, e
`ConvertFrom-Json` de JSON malformado emitindo erro não-terminante num dos
motores — **não** se materializaram. Nenhum `UF` de divergência foi aberto.

Duas observações de cobertura saíram desta leitura; nenhuma é falha de teste nem
bug do `launcher.ps1`, e as duas foram registradas em `FINDINGS.md`:

- **`UF2`** — o leg `windows-latest` roda `C:\Program Files\PowerShell\7\pwsh.EXE`
  (PSVersion 7.6.4, PSEdition Core), **não** Windows PowerShell 5.1. Ou seja: o
  motor de produção real do launcher — e o único onde o `QF1` reproduzia — não é
  exercitado por nenhum leg do CI. Os dois legs são o mesmo pwsh 7.6.4; o que
  varia entre eles é o SO, não o motor.
- **`UF3`** — `Import-Module Pester -MinimumVersion 5.5.0` sem teto: os runners
  têm 6.1.0 e 5.9.0 instaladas, e a suíte rodou sob a 6.x (o banner
  `Running tests from 2 files.` difere do `Starting discovery in 2 files.` que a
  5.7.1 local imprime). Passou nas duas famílias de versão, o que é uma boa
  notícia, mas não foi uma decisão — é a versão que o runner tinha no dia.

### Evidência U6-k — cobertura combinada (local + CI)

Somando as duas fontes, a suíte tem `91 passed / 0 failed` em **quatro**
combinações motor×SO, e nenhuma delas divergiu:

| onde | motor | SO | resultado |
|------|-------|----|-----------|
| local (Tasks 1-4) | Windows PowerShell 5.1, Pester 5.7.1 | Windows 10 19045 | 91 passed, 0 failed |
| local (Tasks 1-4) | pwsh 7.5.1, Pester 5.7.1 | Windows 10 19045 | 91 passed, 0 failed |
| CI leg 1 | pwsh 7.6.4 Core, Pester 6.1.0 | Ubuntu 24.04.4 LTS | 91 passed, 0 failed |
| CI leg 2 | pwsh 7.6.4 Core, Pester 6.1.0 | Windows 10.0.26100 | 91 passed, 0 failed |

A linha do 5.1 vem só do local (`UF2`): o CI não a cobre.

### Evidência U6-l — suíte pytest sem regressão, no estado final (Step 5)

```text
$ python -m pytest ui/ enhance/ -q
FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionErr...
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: as...
4 failed, 365 passed in 5.19s
```

Mesmas 4 falhas nominais do baseline histórico (itens L4 e N7). O job
`Tests (Python 3.11)` e o `Tests (Python 3.12)` do mesmo run do CI passaram
verdes — na máquina limpa do runner as 4 falhas de encoding de console do
Windows nem aparecem.

### Evidência U6-m — `launcher.ps1` intacto no fim do ciclo (Step 6)

```text
$ git diff --stat origin/main -- launcher.ps1 launch-config.json
(nenhuma linha de saída)
```

Diff completo do ciclo contra `origin/main`, para o registro — 5 arquivos, todos
só-adição, nenhum deles `launcher.ps1`, `launch-config.json` ou `.py`:

```text
$ git diff --stat origin/main
 .claude/memory/FINDINGS.md    |  23 ++
 .claude/memory/STATE.md       | 169 +++++++++++++++
 .github/workflows/ci.yml      |  29 +++
 tests/launch-config.Tests.ps1 | 121 +++++++++++
 tests/launcher.Tests.ps1      | 476 ++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 818 insertions(+)
```

### Conclusão do Ciclo U

Objetivo do ciclo cumprido: `launcher.ps1` deixou de ser o único artefato do
repo com zero teste automatizado. 91 testes verdes em CI nos dois legs, mais 91
verdes localmente nos dois motores de Windows, com `launcher.ps1` e
`launch-config.json` sem uma linha alterada. Três achados de infra abertos
(`UF1`, `UF2`, `UF3`) — nenhum é bug do launcher, nenhum foi corrigido aqui.
Pendência operacional: o **PR #39 está aberto e não deve ser mergeado por
engano** — foi aberto como instrumento para disparar o CI.
*(Linha acima escrita às ~02:18Z e **superada** ~4 min depois: o PR já tinha sido
mergeado às 02:14:36Z, o que o executor só descobriu ao fim da task. Preservada
por causa da regra append-only do arquivo; ver a nota U6-n logo abaixo.)*

### Nota U6-n — o PR #39 foi mergeado pelo humano durante a task

A instrução ao executor era abrir o PR **sem** mergear (instrumento de
diagnóstico). O merge aconteceu mesmo assim, feito pela conta dona do repo,
enquanto o executor ainda lia os logs dos legs:

```text
$ gh pr view 39 --json state,mergedAt,mergedBy,mergeCommit,autoMergeRequest
state=MERGED
mergedAt=2026-08-16T02:14:36Z
mergedBy=gabrielschoenardie
mergeCommit=d78bd2d967994b84d8906a11a4d438008d04a694
autoMerge=null
```

Cronologia: PR criado ~02:11:50Z → CI concluído 02:12:26Z (verde) → merge
02:14:36Z. Não foi ação do executor nem auto-merge (`autoMerge=null`); foi merge
manual da conta `gabrielschoenardie`, ~2 min depois do CI ficar verde. Registrado
aqui porque muda o estado do repo, não como reclamação: o Ciclo U está em `main`.

Consequências medidas:

1. `main` avançou para `d78bd2d` (squash de `worktree-pester-launcher`). A
   Regra de Ouro do ciclo continua válida **no próprio `main`**, o que é uma
   verificação mais forte que a do Step 6:

   ```text
   $ git diff --stat ef7b0e3 d78bd2d -- launcher.ps1 launch-config.json
   (nenhuma linha de saída)

   $ git diff --stat ef7b0e3 d78bd2d
    .claude/memory/FINDINGS.md    |  23 ++
    .claude/memory/STATE.md       | 169 +++++++++++++++
    .github/workflows/ci.yml      |  29 +++
    tests/launch-config.Tests.ps1 | 121 +++++++++++
    tests/launcher.Tests.ps1      | 476 ++++++++++++++++++++++++++++++++++++++++++
    5 files changed, 818 insertions(+)
   ```

   `launcher.ps1` e `launch-config.json` são byte-idênticos entre o `main`
   pré-ciclo (`ef7b0e3`) e o `main` pós-merge (`d78bd2d`).
2. O merge levou o estado do ciclo até `16e3a2a` — ou seja, `main` tem a seção
   `## Ciclo U` **com a linha `| U6 | blocked |`** e sem nenhuma das evidências
   de CI. Tudo o que está desta seção `## Ciclo U — U6 desbloqueada` em diante
   (evidências U6-f…U6-n, `UF2`, `UF3`) foi commitado **depois** do merge e vive
   só na branch `worktree-pester-launcher`. `git diff --stat origin/main` na
   ponta da branch: `2 files changed, 252 insertions(+)`, só `STATE.md` e
   `FINDINGS.md`.
3. Decisão de escopo pendente para o Orquestrador: como levar esses 252 linhas
   para `main` (novo PR da mesma branch, ou cherry-pick). O executor não abriu
   segundo PR — o ruling autorizou um PR de diagnóstico, não uma política de
   merge.

Os blocos de `git diff --stat origin/main` das evidências U6-d e U6-m foram
medidos **antes** deste merge, contra o `main` de então (`ef7b0e3`); continuam
sendo a saída real do momento em que rodaram, e o parágrafo 1 acima refaz a mesma
verificação contra o `main` novo.

## Ciclo V — render queue profissional (batch de verdade) — 2026-08-16

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| V1 | done | render_queue.py, test_render_queue.py | `python -m pytest test_render_queue.py -v` -> 12 testes coletados, `12 passed in 0.31s` (nao 13 como o PLAN previa — o teste literal do plano so tem 12 funcoes `test_*`; nenhuma foi omitida, contagem "13 testes" no plano estava incorreta, registrado como desvio nao-bloqueante). Passo intermediario confirmado: antes de criar `render_queue.py`, `python -m pytest test_render_queue.py -v` falhou com `ModuleNotFoundError: No module named 'render_queue'` em toda a coleta, como esperado (TDD). Commit `13d2d17` — `feat(batch): módulo render_queue com estado de job, ETA e relatório final`. |
| V2 | done | Reels_Encoder_v2_FINAL.py | py_compile limpo; pytest test_render_queue.py enhance/ ui/ -q -> 4 failed, 377 passed (mesmas 4 falhas nominais do baseline: enhance/test_ebu_meter.py::test_measure_cmd_basic_shape, enhance/test_ebu_meter.py::test_ffplay_args_basic, ui/test_readme_assets.py::test_anchor_strings_present, ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii; zero falhas em test_render_queue.py; zero regressao nova), commit c0e04e2 |
| V3 | done | .claude/memory/STATE.md | Smoke test real com ffmpeg de verdade, pasta de fila fora do repo (`tempfile.mkdtemp()`): IN=`render_queue_smoke_in_ksntktoe`, OUT=`render_queue_smoke_out_es1npsgm`, 2 arquivos (`clip_ok.mp4` copia de `teste.mp4`, `clip_falha.mp4` bytes invalidos `b"nao e um video valido"`). 1a rodada (`python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance off`): EXIT=1, relatorio final `✓ Sucesso:  1/2`, `✗ Falhas:   1/2` com `clip_falha.mp4 → Command '[...ffmpeg.EXE...]' returned non-zero exit status 3199971767` e log ffmpeg capturado (`moov atom not found`, `Error opening input: Invalid data found when processing input`); `Tempo total da fila: 00:29`; `<OUT>/clip_ok_Hollywood_CRF18.mp4` criado, 14991335 bytes (>0), mais `.qc.html` e `.qc.json` de QC automatico. 2a rodada (mesmo comando, sem apagar `<OUT>`): EXIT=1, `✓ Sucesso:  0/2`, `○ Pulados:  1/2`, `✗ Falhas:   1/2` — tabela mostra linha 2 (`clip_ok`) com status `○` e duracao `—` (pulado, sem reencode), linha 1 (`clip_falha`) falhou de novo com o mesmo erro (nunca produziu output a pular). Limpeza: `shutil.rmtree` das duas pastas temp; `git status --short` pos-limpeza mostrou so `M .claude/memory/PLAN.md`, `M docs/superpowers/plans/2026-08-16-render-queue.md` e `?? docs/launcher-portavel-reels-encoder.md` — nenhum arquivo novo relacionado ao smoke test (pastas eram fora da arvore do repo). Suite completa refeita: `python -m pytest test_render_queue.py enhance/ ui/ -q` -> `4 failed, 377 passed in 5.14s`, mesmas 4 falhas nominais do baseline (identicas ao Step V2), zero regressao nova. |

## Ciclo W — corrigir flicker do MCTF durante --batch (VF1) — 2026-08-16

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| W1 | done | enhance_visualizer.py, Reels_Encoder_v2_FINAL.py | `show_progress: bool = True` adicionado a assinatura de `generate_mctf_mask_video()`; `disable=not show_progress` passado ao `Progress(...)`; call site em `_encode_single_file` agora passa `show_progress=not is_batch`. `py_compile` limpo (exit 0); `grep -n show_progress` -> 3 ocorrencias (enhance_visualizer.py:409 assinatura, enhance_visualizer.py:496 disable=, Reels_Encoder_v2_FINAL.py:3942 call site); `pytest test_render_queue.py enhance/ ui/ -q` -> `4 failed, 377 passed`, mesmas 4 falhas nominais do baseline (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`) — zero regressao. Commit 6d86eb6. |
| W2 | done | .claude/memory/STATE.md | Smoke test real: pasta temp fora do repo (`tempfile.mkdtemp`) com `teste.mp4` copiado; comando `python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance on --enhance-ai on --mctf on`, exit code 0. Saida completa (stdout+stderr, 35 linhas) capturada em arquivo e inspecionada: `grep -c "MCTF masks"` -> 0 ocorrencias (string ausente, confirma supressao da barra durante o batch). Máscaras MCTF geradas de verdade apesar de `disable=True`: `enhance_maps/mctf_deband_mask.mp4` = 211290216 bytes (≈201 MB), `enhance_maps/mctf_sharpen_mask.mp4` = 513079464 bytes (≈489 MB), ambos > 0 e junto com os PNGs de debug (`consensus_*_mask.png`, `frame_N_*.png`) confirmando que a análise MCTF completa rodou. Relatório final da fila renderizou limpo: tabela `Job 1 de 1` e `Resumo da fila` com colunas `#`/`Arquivo`/`Status`/`Duração`, linha `1 ... ✓ 03:23`, `✓ Sucesso: 1/1`, `Tempo total da fila: 03:23`, sem nenhuma interferência visual/flicker. Cleanup: `rm -rf` na pasta temp de IN/OUT e em `enhance_maps/` (gerada no cwd do repo); `git status --short` pós-cleanup mostra apenas `M .claude/memory/STATE.md` e dois itens untracked pré-existentes e não relacionados (`docs/launcher-portavel-reels-encoder.md`, `videos/`) — nenhum resíduo do smoke test rastreado ou sujo (mp4/png de `enhance_maps/` cobertos por `*.mp4`/`*.png` no `.gitignore`, e a própria pasta já foi apagada). Suíte completa re-executada: `pytest test_render_queue.py enhance/ ui/ -q` -> `4 failed, 377 passed`, mesmas 4 falhas nominais do baseline (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`) — zero regressao nova. |

## Ciclo X — progresso ao vivo durante o job (VF2) — 2026-08-16

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| X1 | blocked | render_queue.py, test_render_queue.py | RED confirmado certo (`python -m pytest test_render_queue.py -v -k "on_tick or ticking_duration"` -> 2 failed pelo motivo esperado: `TypeError: run_job() got an unexpected keyword argument 'on_tick'` e duração ainda `"—"` estático). Implementado o código literal do plano (Step 3 e Step 4, `docs/superpowers/plans/2026-08-16-render-queue-live-progress.md` § Task 1). `python -m pytest test_render_queue.py -v` -> `1 failed, 13 passed`: `test_run_job_marks_failure_and_captures_log` (teste pré-existente do Ciclo V, não tocado) quebrou — `job.log` fica `''` em vez de conter `"preparando encode..."`. Causa raiz confirmada isoladamente (`python -c` com `Console.capture()` + `threading.Thread`): `rich.console.Console._buffer` e `_buffer_index` são `@property` sobre `self._thread_locals` (thread-local storage) — `console.print()` chamado dentro da `threading.Thread` de `_target()` grava no buffer *daquela* thread, nunca no buffer da thread principal onde `with console.capture()` roda; `capture.get()` sempre retorna vazio para qualquer print feito dentro da worker thread. Isso é uma incompatibilidade real entre o Step 3 literal do plano (que envolve a criação/join da thread com `console.capture()` no thread principal) e a biblioteca Rich de fato instalada — não um erro de sintaxe nem conflito de nome de teste, então não corrigi por conta própria (fora do mandato do executor). PERGUNTA EXATA para o Orquestrador: as próprias notas de execução do plano dizem "console.capture() continua envolvendo o encode inteiro, agora dentro da thread" — isso deveria ser lido como "mover `with console.capture()` para dentro de `_target()` (rodando na worker thread)" em vez do texto literal do Step 3 (que envolve só a criação/join da thread, no thread principal)? Ou existe uma estratégia de captura thread-safe diferente pretendida (lock compartilhado, redirecionar `job.log` via outro mecanismo)? Revertido apenas o commit — código de `render_queue.py`/`test_render_queue.py` permanece no working tree com os 2 testes novos (RED verificado) e a implementação do Step 3/4, mas SEM commit (Step 6 não executado) até a decisão de design. Suíte real: 13 passed, 1 failed (regressão da própria mudança do X1, não do baseline pré-existente de 4 falhas nominais). |

X1 (retomado após correção do Orquestrador, plano atualizado em `3b8bd2d`) | done | render_queue.py, test_render_queue.py | `console.capture()` movido para dentro de `_target()` (worker thread) por instrução explícita do Orquestrador — thread principal só lê `failure`/`log_text` via `nonlocal` depois de `worker.join()` (happens-before). `python -m pytest test_render_queue.py -v` → `14 passed in 0.53s`, todos os testes incluindo `test_run_job_marks_failure_and_captures_log`. Commit `d14d4a9`.
| X2 | done | Reels_Encoder_v2_FINAL.py | Código literal do plano § Task 2 aplicado sem desvio: `_refresh_table()` extraída dentro do `with Live(...) as live:`, chamada no caminho "pulado" e após cada `run_job`, passada como `on_tick=_refresh_table` para `render_queue.run_job(job, _do_encode, console, on_tick=_refresh_table)`. `python -m py_compile Reels_Encoder_v2_FINAL.py` → sem saída, exit 0. `python -m pytest test_render_queue.py enhance/ ui/ -q` → `4 failed, 379 passed in 5.34s`, exatamente as 4 falhas nominais do baseline (`enhance/test_ebu_meter.py::test_measure_cmd_basic_shape`, `enhance/test_ebu_meter.py::test_ffplay_args_basic`, `ui/test_readme_assets.py::test_anchor_strings_present`, `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`), zero falhas novas. Commit `1fd79c4`.
| X3 | done | .claude/memory/STATE.md | Smoke test real (plano § Task 3, adaptado p/ Windows: `tempfile.mkdtemp()`/`tempfile.mkstemp()` em vez de `/tmp` literal). Fila com 1 clipe (`teste.mp4` copiado p/ pasta IN via `tempfile.mkdtemp`), `python Reels_Encoder_v2_FINAL.py --batch <IN> --output-dir <OUT> --performance speed --enhance off` redirecionado p/ arquivo de log (`tempfile.mkstemp`) — exit code 0. Log inspecionado (34 linhas): coluna Duração da linha do clipe aparece só **uma vez**, com o valor final (`00:29`), tanto na tabela do job quanto no "Resumo da fila" — **limitação de ambiente confirmada, não falha do fix**: o redirecionamento não-interativo do `> log 2>&1` só captura o snapshot final que o `rich.Live` escreve ao encerrar (mais o output bruto do `x264`/console de progresso do encode em si), não os frames intermediários do `live.update()` chamados via `on_tick` a cada ~250ms — exatamente a limitação já antecipada no plano § Task 3 Step 2 ("se o terminal não é interativo... documentar isso explicitamente"). O mecanismo de tick em si já está provado pelo teste automatizado `test_run_job_calls_on_tick_while_encode_runs` (X1, `tick_count["n"] >= 2` com `tick_interval=0.05`) — essa é só a confirmação best-effort adicional, não bloqueante, conforme o próprio PLAN.md previa. Cleanup: `shutil.rmtree` nas pastas IN/OUT temporárias + remoção do arquivo de log; `git status --short` pós-cleanup mostra só `.claude/memory/PLAN.md` (M pré-existente, não tocado por este item), `.claude/memory/STATE.md` (M, esta edição) e 2 untracked pré-existentes não relacionados (`docs/launcher-portavel-reels-encoder.md`, `videos/`) — nenhum resíduo do smoke test. Suíte completa re-executada: `python -m pytest test_render_queue.py enhance/ ui/ -q` → `4 failed, 379 passed in 5.39s`, exatamente as mesmas 4 falhas nominais do baseline, zero regressão nova.

## Ciclo Y — interrupção segura, log e ETA — 2026-08-17

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| Y5 | done | .claude/memory/STATE.md, .claude/memory/PLAN.md, .claude/memory/FINDINGS.md | Smoke test real de ponta a ponta: `exit=130` real, `⚡ Interrompidos: 1/3`, job interrompido **refeito** (não `○ pulado`) na execução seguinte, ETA `01:59` > `00:00` durante o último job. Um achado novo registrado: `YF1` (janela em que `discard_partial_output` falha no Windows). Detalhe colado abaixo. |

### Ambiente

Windows 10 Pro 10.0.19045, git-bash (MSYS), Python 3.12.10, ffmpeg 7.1.1-full_build-www.gyan.dev.
Pastas do smoke test dentro do worktree (`./.smoke/batch_in`, `./.smoke/batch_out`) em vez de
`/tmp/batch_in` e `/tmp/batch_out` do plano — decisão de ambiente, para não depender de como
`/tmp` resolve no git-bash local. Removidas ao final (ver § Cleanup).

### Suíte

```
$ python -m pytest test_render_queue.py enhance/ ui/ -q
=========================== short test summary info ===========================
FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionErr...
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: as...
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeE...
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - Assertion...
4 failed, 388 passed in 5.37s
```

As 4 falhas são exatamente as nominais do baseline. `388 passed` = `379` do baseline
pré-ciclo + `9` testes novos das Tasks 2/3.

```
$ python -m pytest test_render_queue.py -q -k "discard_partial_output"
..                                                                       [100%]
2 passed, 21 deselected in 0.12s
```

### Step 1 — pasta de batch

`ffmpeg -version` presente no PATH (`ffmpeg version 7.1.1-full_build-www.gyan.dev`). 3 clipes
sintéticos gerados exatamente com o comando do plano
(`testsrc=size=1080x1920:rate=30:duration=8` + `sine=frequency=440:duration=8`,
`-c:v libx264 -c:a aac -shortest`), só com o caminho trocado:

```
gen_exit=0
total 552
drwxr-xr-x 1 Usuario 197121      0 Aug 17 21:36 .
drwxr-xr-x 1 Usuario 197121      0 Aug 17 21:36 ..
-rw-r--r-- 1 Usuario 197121 187935 Aug 17 21:36 clip1.mp4
-rw-r--r-- 1 Usuario 197121 187935 Aug 17 21:36 clip2.mp4
-rw-r--r-- 1 Usuario 197121 187935 Aug 17 21:36 clip3.mp4
```

### Step 2a — `kill -INT` do git-bash NÃO entrega o sinal (condição do escape hatch)

Comando literal do plano (`python ... --batch ... &` / `sleep 12` / `kill -INT $PID` /
`wait $PID; echo "exit=$?"` / `ls -la`):

```
=== ls batch_out ANTES ===
total 4
drwxr-xr-x 1 Usuario 197121 0 Aug 17 21:35 .
drwxr-xr-x 1 Usuario 197121 0 Aug 17 21:36 ..
=== run ===
exit=130
=== ls batch_out DEPOIS ===
total 10940
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:43 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:36 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:39 clip1_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:39 clip1_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2761 Aug 17 21:39 clip1_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:41 clip2_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:41 clip2_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2760 Aug 17 21:41 clip2_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:43 clip3_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:43 clip3_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2761 Aug 17 21:43 clip3_Hollywood_CRF18.qc.json
```

O `exit=130` acima é **artefato do shell MSYS, não do processo**: os três jobs rodaram até o
fim, 7 minutos depois do `kill -INT`. Fim real do log da mesma execução:

```
✓ Sucesso:  3/3
Tempo total da fila: 06:55
```

Segunda tentativa de sinal real, com `CREATE_NEW_PROCESS_GROUP` +
`os.kill(pid, signal.CTRL_C_EVENT)` a partir de um pai Python:

```
sent=CTRL_C_EVENT ok
child_rc= TIMEOUT (nao interrompido)
```

Também não entrega. Confirmado: **este ambiente não entrega um Ctrl+C de console** a um
Python+ffmpeg Win32 nativo — a condição exata do escape hatch pré-autorizado do plano.

### Step 2b — interrupção real via `_thread.interrupt_main()` (em vez de parar no teste unitário)

Em vez de cair direto no escape hatch (validar `XF1` só pelo teste unitário), foi executado o
caminho `--batch` **real e completo** (`runpy.run_path(".../Reels_Encoder_v2_FINAL.py",
run_name="__main__")` com o `sys.argv` do plano), entregando um `KeyboardInterrupt` **real na
main thread** via `_thread.interrupt_main()` a partir de uma thread-timer — o mesmo mecanismo
que o CPython usa para o Ctrl+C do console, e exatamente o ponto de entrega que o fix assume
(spec § Architecture). Nenhum código de produção foi tocado nem monkey-patchado.

Interrupção aos 200 s (job 1 concluído, job 2 em voo):

```
=== ls batch_out ANTES ===
total 8
drwxr-xr-x 1 Usuario 197121 0 Aug 17 21:46 .
drwxr-xr-x 1 Usuario 197121 0 Aug 17 21:46 ..
=== run (interrupt em 200s) ===
exit_do_processo=130
=== ls batch_out DEPOIS ===
total 3652
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:48 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:46 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:48 clip1_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:48 clip1_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2759 Aug 17 21:48 clip1_Hollywood_CRF18.qc.json
```

Relatório final real (colado do log):

```
                           Job 2 de 3  ·  ETA: 03:29

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:15
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⏳       01:02
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

⚠ Fila interrompida pelo usuário

────────────────────────── 📊 Fila — Relatório Final ──────────────────────────
                                Resumo da fila

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:15
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⚡           —
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

✓ Sucesso:  1/3
⚡ Interrompidos: 1/3
Tempo total da fila: 02:15

exit=130
```

Bate com o esperado do plano: `exit=130`, `⚡ Interrompidos: 1/3`, nenhum `.mp4` do job
interrompido em `batch_out`, job já concluído preservado. Nota: a linha
`● output parcial removido: ...` **não** apareceu — aos 200 s o job 2 ainda estava na fase de
análise e o ffmpeg ainda não havia criado o arquivo de saída, então `discard_partial_output`
devolveu `False` sem nada para remover. Ver `YF1` para o que acontece quando o arquivo
**existe**.

### Step 3 — o job interrompido é refeito, não pulado (prova direta do XF1)

```
=== ls batch_out ANTES ===
total 3652
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:48 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:50 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:48 clip1_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:48 clip1_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2759 Aug 17 21:48 clip1_Hollywood_CRF18.qc.json
=== run completo ===
exit=0
=== ls batch_out DEPOIS ===
total 10940
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:55 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 21:50 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:48 clip1_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:48 clip1_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2759 Aug 17 21:48 clip1_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:52 clip2_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:52 clip2_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2759 Aug 17 21:52 clip2_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 21:55 clip3_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 17 21:55 clip3_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2761 Aug 17 21:55 clip3_Hollywood_CRF18.qc.json
```

Relatório final real:

```
────────────────────────── 📊 Fila — Relatório Final ──────────────────────────
                                Resumo da fila

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ○            —
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:10
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:10

✓ Sucesso:  2/3
○ Pulados:  1/3
Tempo total da fila: 04:20
```

Exatamente o esperado: clip1 (concluído antes da interrupção) = `○ pulado`; **clip2 (o
interrompido) = `✓`, reprocessado do zero em 02:10, não pulado**; clip3 = `✓`.

### Step 4 — ETA > 00:00 durante o último job (XF3)

O `rich.Live` só escreve o frame final quando a saída é um pipe, então o log vanilla do Step 3
registra apenas uma linha de título — e nela os 3 jobs já tinham terminado:

```
$ grep -n "ETA:" step3.log
37:                           Job 3 de 3  ·  ETA: 00:00
```

Para observar o título **durante** o último job, o mesmo estado do Step 3 foi reproduzido (só
`clip1_*` em `batch_out`) e a execução repetida com `FORCE_COLOR=1`, que faz o Rich emitir
todos os frames de refresh. Nada além do rendering muda. Linha de título observada com o
**último** job em voo:

```
                           Job 3 de 3  ·  ETA: 01:59

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ○            —
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:13
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⏳       00:14
```

Contagem regressiva completa no job 3 (498 frames com `Job 3 de 3`), do máximo até zero:

```
$ grep -a -o "Job 3 de 3  ·  ETA: [0-9][0-9:]*" step4.log | head -6
Job 3 de 3  ·  ETA: 02:13
Job 3 de 3  ·  ETA: 02:13
Job 3 de 3  ·  ETA: 02:13
Job 3 de 3  ·  ETA: 02:12
Job 3 de 3  ·  ETA: 02:12
Job 3 de 3  ·  ETA: 02:12
$ grep -a -o "Job 3 de 3  ·  ETA: [0-9][0-9:]*" step4.log | tail -3
Job 3 de 3  ·  ETA: 00:00
Job 3 de 3  ·  ETA: 00:00
Job 3 de 3  ·  ETA: 00:00
$ grep -a -o "Job 3 de 3  ·  ETA: [0-9][0-9:]*" step4.log | sort -t: -k2 | tail -1
Job 3 de 3  ·  ETA: 02:13
```

`XF3` provado: no último job (`remaining == 0`) o ETA parte de `02:13` e decresce até `00:00`,
em vez de exibir `00:00` durante o encode inteiro.

### Achado novo — YF1 (registrado em FINDINGS.md, não corrigido aqui)

Sondagem da janela em que o `.mp4` parcial existe de fato no disco (poll a cada 5 s no
`batch_out` durante o job 1; linhas `mp4=nao` omitidas):

```
t=115s mp4=SIM size=0
t=120s mp4=SIM size=524336
t=125s mp4=SIM size=1310768
t=130s mp4=SIM size=2097200
t=135s mp4=SIM size=3710103
t=140s mp4=SIM size=3710103
t=140s job1 CONCLUIDO
probe done
```

Interrupção real dentro dessa janela (125 s), com o parcial já no disco:

```
=== ls batch_out ANTES ===
total 8
drwxr-xr-x 1 Usuario 197121 0 Aug 17 22:06 .
drwxr-xr-x 1 Usuario 197121 0 Aug 17 22:06 ..
=== run (interrupt em 125s, com o .mp4 parcial ja no disco) ===
exit_do_processo=130
=== ls batch_out DEPOIS ===
total 1800
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:08 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:06 ..
-rw-r--r-- 1 Usuario 197121 1310768 Aug 17 22:08 clip1_Hollywood_CRF18.mp4
```

```
$ grep -a -n "output parcial|Fila interrompida|Interrompidos|Sucesso|exit=" step2d.log
33:⚠ Fila interrompida pelo usuário
44:✓ Sucesso:  0/3
45:⚡ Interrompidos: 1/3
48:exit=130
```

`⚡ Interrompidos: 1/3` e `exit=130` corretos, mas **o parcial de 1310768 bytes sobreviveu** e a
linha `● output parcial removido:` não foi impressa — `discard_partial_output` devolveu `False`
(o `os.remove` falha porque o ffmpeg filho, órfão, ainda mantém o arquivo aberto no Windows).
Segundos depois esse ffmpeg órfão terminou de escrever sozinho e morreu:

```
$ ffprobe -v error -show_entries format=duration,size -of default=nw=1 clip1_Hollywood_CRF18.mp4
duration=8.000000
size=3710103
ffprobe_exit=0
$ ls -la .smoke/batch_out
total 3632
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:08 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:06 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 22:08 clip1_Hollywood_CRF18.mp4
$ tasklist | grep -i ffmpeg
nenhum ffmpeg em execucao agora
```

Consequência confirmada na execução seguinte — o output do job interrompido é promovido a
pronto:

```
=== ls batch_out ANTES (sobrou o output do job interrompido) ===
total 3632
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:08 .
drwxr-xr-x 1 Usuario 197121       0 Aug 17 22:08 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 17 22:08 clip1_Hollywood_CRF18.mp4
=== run seguinte (interrompido em 20s so para ler o status do job 1) ===
exit_do_processo=130
=== frame ===
                           Job 2 de 3  ·  ETA: --:--

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ○            —
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⏳       00:17
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

⚠ Fila interrompida pelo usuário
```

Nenhum `.qc.json`/`.qc.html` foi gerado para esse arquivo — ele nunca passou pelo pós-encode
(remux do átomo `colr`, QC), mas o loop o trata como pronto. Registrado como `YF1`; **não
corrigido neste ciclo** (fora do escopo do PLAN.md do Ciclo Y). Nenhum `<base>_temp.mp4` órfão
foi observado em nenhuma das execuções — o risco residual citado na Self-Review do plano não
se materializou.

### Cleanup

`.smoke/` (clipes de entrada, outputs, logs e scripts do smoke test) removida ao final;
`git status --short` pós-cleanup colado no relatório da task.
| AA1 | done | README.md | Início Rápido reescrito: launcher.ps1 único passo 1/2, TOC renomeado p/ "Instalação Alternativa" |
| AA2 | done | README.md | sub-seção "Launcher portátil" removida de Portabilidade, substituída por cross-link p/ Início Rápido |
| AA3 | done | README.md | "Instalação Completa" renomeada p/ "Instalação Alternativa (Python puro / outros SOs)", conteúdo técnico preservado |
| AA4 | done | README.md | contagem real confirmada via pytest --collect-only (130 tests collected); "111 testes"→"130 testes" nas 3 ocorrências |
| AA5 | done | README.md | headings AA1/AA3 batem com âncoras da TOC (slug GitHub verificado manualmente); commit d9ca99d |
| AA2-fix | done | README.md | detalhe técnico (venv/abas WT/fallback/nota CRF) recolocado no Início Rápido após review do orquestrador flagrar referência circular vazia; pytest ui/ reconfirma 130 testes; commit 22eb7e3 |
| AB1 | done | README.md | 4 ocorrências "FASE 27" removidas (TOC, tabela CLI, diagrama, heading); âncora TOC bate com novo heading `#-módulo-de-ia` |
| AB2 | done | enhance/ffmpeg_filters.py, enhance/processor.py | prefixo "FASE 27D — " removido dos 2 docstrings de módulo, descrição intacta |
| AB3 | done | enhance/ai/interface.py, enhance/ai/mock_cnn.py, enhance/ai/__init__.py, enhance/profile.py, enhance/test_mock_cnn.py | referência "(Fase 27F)"/"Fase 27F —"/"Fase 27F:" removida em 6 pontos (incl. profile.py:233 e :451), frase gramatical preservada |
| AB4 | done | enhance/sampler.py, enhance/profile.py | comentário sampler.py:2 limpo; separador profile.py:267 recomposto com largura idêntica (79 chars) preenchendo `─` |
| AB5 | done | enhance/__init__.py, enhance/test_processors.py | docstrings de módulo limpos, resto da frase preservado |
| AB6 | done | enhance/test_mock_cnn.py, enhance/test_processors.py | 3 prints de banner de teste limpos, bordas `=`/`─` não realinhadas (não fazia parte do critério) |
| AB7 | done | (verificação) | grep `-ri "fase 27\|fase27"` repo-wide: zero match fora de `.claude/memory/PLAN.md` (não editável); `pytest enhance/ ui/ -q` → 4 failed/365 passed, mas 2 falhas extras (`test_ebu_meter.py::test_measure_cmd_basic_shape`, `::test_ffplay_args_basic`) confirmadas pré-existentes via `git stash` antes das edições — baseline preservado; commit 7422051 |

## Ciclo AC — Task 3 (Steps 1-3) — 2026-08-18

| ID | done ou blocked | arquivo tocado | resultado em 1 linha |
|----|------------------|-----------------|------------------------|
| AC3 (steps 1-3) | done (parcial) | .github/workflows/ci.yml | job tests convertido p/ matriz os:[ubuntu-latest,windows-latest] x python-version, continue-on-error só na perna windows-latest, fail-fast:false; nenhum step da tests precisou de shell: bash (nenhum run: usa sintaxe POSIX-only); commit 618b5f9, sem push |

Step 4 (colher a lista real de FAILED em Windows via logs do CI) ficou pendente nesta
passagem — nao havia acesso a um run de CI real neste worktree local. **Fechado abaixo**
pelo Orquestrador apos push + PR #41, que disparou o workflow e colheu os logs reais.

### Step 4 — lista real de falhas (run 32159250931, PR #41)

Evidencia colada literalmente pelo Orquestrador, a partir de `gh run view --job <id> --log`,
step "Run tests", das duas pernas Windows do run `32159250931`.

**Windows, Python 3.11** (job 95783890924):

```
enhance/test_ebu_meter.py::test_measure_cmd_basic_shape FAILED           [ 19%]
enhance/test_ebu_meter.py::test_ffplay_args_basic FAILED                 [ 21%]
ui/test_readme_assets.py::test_anchor_strings_present FAILED             [ 92%]
ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii FAILED        [ 98%]

FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionError: assert 'ffmpeg.exe' == 'ffmpeg'
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: assert 'ffplay.exe' == 'ffplay'
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 5207: character maps to <undefined>
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - AssertionError: assert '|' == '▎'\n  \n  - ▎\n  + '|'
======================== 4 failed, 388 passed in 5.05s ========================
```

**Windows, Python 3.12** (job 95783891099): mesmas 4 linhas `FAILED`, na mesma ordem
(`test_measure_cmd_basic_shape`, `test_ffplay_args_basic`, `test_anchor_strings_present`,
`test_idle_glyphs_wired_unicode_and_ascii`), `4 failed, 388 passed in 5.03s`.

Confirmações:

- 3.11 e 3.12 falham nos **mesmos 4 testes**, mesma ordem, mesmas exceções — nenhuma
  divergência entre versões de Python.
- A contagem bate com as "4 falhas nominais" relatadas à mão (mesmos 4 nomes já
  documentados como baseline pré-existente em ciclos anteriores — I3/H2c/K7/L4/N7/O1 —
  rodando em Linux/local); confirmado adicionalmente pelo Orquestrador batendo com a
  suíte local rodada na mesma máquina Windows antes da Task 1. **Não é achado novo de
  divergência de contagem.**

AC3 fecha aqui: Steps 1-3 (matriz de SO + verificação de shell) + Step 4 (lista real
colhida acima) completos.
