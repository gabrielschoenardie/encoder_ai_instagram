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

**Windows, Python 3.12** (job 95783891099):

```
enhance/test_ebu_meter.py::test_measure_cmd_basic_shape FAILED           [ 19%]
enhance/test_ebu_meter.py::test_ffplay_args_basic FAILED                 [ 21%]
ui/test_readme_assets.py::test_anchor_strings_present FAILED             [ 92%]
ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii FAILED        [ 98%]

FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionError: assert 'ffmpeg.exe' == 'ffmpeg'
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: assert 'ffplay.exe' == 'ffplay'
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 5207: character maps to <undefined>
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - AssertionError: assert '|' == '▎'\n  \n  - ▎\n  + '|'
======================== 4 failed, 388 passed in 5.03s ========================
```

Confirmações (o bloco acima confirma a equivalência com a 3.11: mesmos 4 testes, mesma
ordem, mesmas exceções, só o tempo final difere):

- 3.11 e 3.12 falham nos **mesmos 4 testes**, mesma ordem, mesmas exceções — nenhuma
  divergência entre versões de Python.
- A contagem bate com as "4 falhas nominais" relatadas à mão (mesmos 4 nomes já
  documentados como baseline pré-existente em ciclos anteriores — I3/H2c/K7/L4/N7/O1 —
  rodando em Linux/local); confirmado adicionalmente pelo Orquestrador batendo com a
  suíte local rodada na mesma máquina Windows antes da Task 1. **Não é achado novo de
  divergência de contagem.**

AC3 fecha aqui: Steps 1-3 (matriz de SO + verificação de shell) + Step 4 (lista real
colhida acima) completos.

## Ciclo AC — Task 4 (corrigir as falhas de Windows) — 2026-08-18

Executor: `executor-pesado`. Brief: `.superpowers/sdd/windows-ci-e-interrupcao-robusta/task-4-brief.md`.
Relatório completo: `.superpowers/sdd/windows-ci-e-interrupcao-robusta/task-4-report.md`.
Plataforma: máquina Windows real (Windows 10 Pro 19045, Python 3.12) — as 4 falhas
reproduzem localmente, então correção e verificação foram feitas onde o bug ocorre.

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AC4-1 | done | (classificação, sem arquivo) | 4 falhas classificadas: 2× "teste acoplado a detalhe POSIX", 2× "teste acoplado ao ambiente"; zero bug de produto, zero `skipif` |
| AC4-2a | done | `enhance/test_ebu_meter.py` | commit `ee26691` — asserção passa a comparar o stem do basename de `argv[0]`, não o caminho literal |
| AC4-2b | done | `ui/test_readme_assets.py` | commit `f968c19` — SVGs lidos com `encoding="utf-8"` explícito |
| AC4-2c | done | `ui/test_theme.py` | commit `503a7ae` — ramo utf do teste de glifos usa console explícito, não `Console()` do ambiente |
| AC4-3 | done | `.claude/memory/FINDINGS.md` | commit `da71b1f` — zero `skipif` concedido (registrado explicitamente); ACF1/ACF2 abertos como achados vizinhos fora de escopo |
| AC4-4 | done | (verificação) | `392 passed` local (era `4 failed, 388 passed`), `ruff check enhance/` limpo |

### Step 1 — classificação das 4 falhas (categorias do brief)

| # | teste | categoria | por quê | ação |
|---|-------|-----------|---------|------|
| 1 | `enhance/test_ebu_meter.py::test_measure_cmd_basic_shape` | teste acoplado a detalhe POSIX | `argv[0]` vem de `ui.binaries.resolve_binary`, que devolve o caminho **invocável**: `ffmpeg` (Linux sem ffmpeg), `ffmpeg.exe` (Windows sem ffmpeg, = CI), `C:\ffmpeg\bin\ffmpeg.EXE` (Windows com ffmpeg no PATH, = esta máquina), `bin/ffmpeg` (bundled). O produto está certo; a asserção `== "ffmpeg"` só passava no CI Linux porque o runner não tem ffmpeg no PATH | afrouxar a asserção para o stem do basename |
| 2 | `enhance/test_ebu_meter.py::test_ffplay_args_basic` | idem (mesma causa, `FFPLAY`) | idem | idem |
| 3 | `ui/test_readme_assets.py::test_anchor_strings_present` | teste acoplado a detalhe POSIX (encoding implícito) | `read_text()` sem `encoding=` usa o default da plataforma (cp1252 no Windows). O gerador está correto: `rich.Console.save_svg` grava UTF-8 sempre — e o próprio arquivo de teste já lia o `.html` com `encoding="utf-8"` na linha 45 | declarar `encoding="utf-8"` na leitura |
| 4 | `ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii` | teste acoplado ao ambiente | `glyphs()` **não** tem bug: medido nesta máquina, `Console()` reporta `legacy_windows=True` e `encoding=cp1252`, então o set ASCII é a resposta correta. O teste é que afirmava o glifo Unicode incondicionalmente a partir de um `Console()` nu, contradizendo o próprio docstring | declarar os dois consoles (o ramo cp1252 já usava `_FakeConsole`; o ramo utf passa a usar o mesmo idioma) |

Nenhuma das 4 caiu em "ausência de ffmpeg no runner" (nenhuma invoca subprocesso) nem em
"genuinamente só-POSIX" (as 4 testam comportamento que existe e importa em Windows) — as
duas únicas categorias do brief que autorizariam `skipif`. **Zero `skipif` adicionado.**

### Step 2 — correção, uma categoria por commit

```
ee26691 test(ebu): assertar o binario invocado, nao a forma do caminho (ABF1)
f968c19 test(readme-assets): ler os SVGs com encoding explicito UTF-8 (ABF1)
503a7ae test(theme): declarar os dois consoles do teste de glifos (ABF1)
da71b1f docs(findings): ACF1/ACF2 achados na Task 4; zero skipif concedido (ABF1)
```

Nenhum arquivo de produto foi tocado — as 3 correções são nos próprios testes, e em cada
caso o produto foi verificado como correto **antes** de a asserção ser mexida (não é
mascarar sintoma: `resolve_binary` deve devolver `.exe` em Windows; `save_svg` deve gravar
UTF-8; `glyphs()` deve cair para ASCII num console cp1252/legacy).

Red-check das 3 asserções afrouxadas (prova de que continuam pegando quebra real):

```
RED-CHECK theme: detectou a quebra (bom)      # _GLYPHS_UNICODE['tab_l']='X'
RED-CHECK ebu: detectou binario errado (bom)  # FFMPEG := C:\bin\ffprobe.exe
RED-CHECK ffplay: detectou binario errado (bom)  # FFPLAY := /usr/bin/ffmpeg
```

### Step 4 — verificação (literal)

Antes (baseline desta máquina, HEAD `8300881`):

```
FAILED enhance/test_ebu_meter.py::test_measure_cmd_basic_shape - AssertionError: assert 'C:\ffmpeg\bin\ffmpeg.EXE' == 'ffmpeg'
FAILED enhance/test_ebu_meter.py::test_ffplay_args_basic - AssertionError: assert 'C:\ffmpeg\bin\ffplay.EXE' == 'ffplay'
FAILED ui/test_readme_assets.py::test_anchor_strings_present - UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 5207...
FAILED ui/test_theme.py::test_idle_glyphs_wired_unicode_and_ascii - AssertionError: assert '|' == '▎'
4 failed, 388 passed in 5.54s
```

Depois (`python -m pytest test_render_queue.py enhance/ ui/ -q`, HEAD `da71b1f`):

```
........................................................................ [ 91%]
................................                                         [100%]
392 passed in 4.98s
```

`392 passed` também sob `PYTHONUTF8=1` (4.90s) — as correções não dependem do modo UTF-8
do interpretador. `python -m ruff check enhance/` → `All checks passed!`.

Nota de ambiente (registrada como ACF2 no `FINDINGS.md`): a sessão do agente herda
`FORCE_COLOR=3`/`COLORTERM=truecolor`, e com isso 4 testes de `test_render_queue.py`
falham por ANSI nas asserções de substring (`8 failed, 384 passed`). Não é regressão nem
tem relação com as 4 falhas desta task — some ao rodar sem `FORCE_COLOR`, que é a
condição do CI e a do baseline do Orquestrador. Todos os números acima foram medidos com
`FORCE_COLOR` fora do ambiente.

As duas pernas Windows do CI **não** foram verificadas aqui: push e leitura do CI real
ficaram explicitamente com o Orquestrador (instrução da task).

## Ciclo AC — Task 5 (fecha o Ciclo AC) — 2026-08-18

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AC5-S1 | done | (só verificação) | Step 1 satisfeito com evidência real já colhida pelo Orquestrador: run de CI `32166523153` (branch deste worktree, via PR #41 aberto só para disparar o workflow) — os 7 jobs do workflow `CI` terminaram `success`, incluindo `Tests (windows-latest, Python 3.11): success` e `Tests (windows-latest, Python 3.12): success`. Nenhum `skipif` pendente de justificativa (Task 4 corrigiu as 4 falhas reais, zero `skipif` concedido). Nada reproduzido nesta máquina; o run é citado diretamente conforme instrução do Orquestrador. |
| AC5-S2 | done | .github/workflows/ci.yml | Removida a linha `continue-on-error: ${{ matrix.os == 'windows-latest' }}` e o comentário de duas linhas acima dela ("A perna Windows entra não-bloqueante..."); `fail-fast: false` mantido intocado. `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"` → `OK`. |
| AC5-S3 | done | .github/workflows/ci.yml | Commit `cc0e99c` ("ci: tornar a perna windows bloqueante no job tests (fecha ABF1)"), 1 file changed, 3 deletions(-). **Nenhum push** foi feito — fica a cargo do Orquestrador, conforme instrução recebida. |
| AC5-S4 | done | .claude/memory/STATE.md, .claude/memory/PLAN.md, .claude/memory/FINDINGS.md | `PLAN.md`: linha AC5 marcada **done** com sha `cc0e99c`; AC1–AC4 também anotadas **done** explicitamente (antes só descritas em prosa, sem o marcador). `FINDINGS.md`: nova seção "Status (2026-08-18, fechamento do Ciclo AC, Task 5)" — ABF1 e ABF2 marcados **corrigido**, ABF3 mantido **aberto — adiado**. |

### Nota sobre a contagem de jobs (Step 4)

A contagem real do workflow `CI` confirmada pelo run `32166523153` é **7 jobs**, não 6
como uma nota antiga do brief da Task 5 estimava: `Lint (ruff)` ×1, `Tests` ×4 (2 SO × 2
versões de Python: ubuntu-latest/windows-latest × 3.11/3.12), `Pester (launcher.ps1)` ×2
(ubuntu-latest + windows-latest). Os 7 terminaram `success` nesse run, incluindo as duas
pernas Windows do job `tests` — na época do run `32166523153` essa perna ainda era
non-blocking (`continue-on-error: true`), mas o resultado real já era verde.

### O que falta (fora do alcance desta task)

O Step 2 (remoção do `continue-on-error`) só foi commitado (`cc0e99c`) DEPOIS do run
`32166523153` — ou seja, ainda não existe um run de CI real que prove a perna Windows
bloqueante **e** verde ao mesmo tempo (a evidência atual prova "verde", não "verde com a
rede de segurança removida"). Registrado explicitamente aqui: a confirmação final "perna
Windows bloqueante e verde" fica para o Orquestrador, após o push deste commit — ele
mesmo registra o run novo (ou chama o executor de volta com o número do run). Nenhum run
posterior a `cc0e99c` foi inventado ou presumido nesta entrada.

**Confirmado:** run `32167268000` (push do commit `6b040a0`) — perna Windows já
bloqueante (sem `continue-on-error`) e os 7 jobs em `success`:

```
Lint (ruff): success
Tests (ubuntu-latest, Python 3.11): success
Tests (ubuntu-latest, Python 3.12): success
Tests (windows-latest, Python 3.11): success
Tests (windows-latest, Python 3.12): success
Pester (launcher.ps1) (ubuntu-latest): success
Pester (launcher.ps1) (windows-latest): success
```

Lacuna fechada.

## Ciclo AD — Task 6 (abrir o ciclo, YF1) — 2026-08-18

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AD1 | done | .claude/memory/PLAN.md | reescrito para Ciclo AD (YF1), tabela AD1..AD4 espelhando Tasks 6-9, commit 86a5d93 |
| AD3 | done | Reels_Encoder_v2_FINAL.py | `_register_ffmpeg`/`_ACTIVE_FFMPEG_LOCK` + `terminate_active_ffmpeg(timeout=5.0)` no topo; registro no `Popen` real (`_run_encoding:1947`, helper que `run_ffmpeg` chama — `run_ffmpeg` não tem `Popen` próprio) e limpeza no `finally` existente; `terminate_active_ffmpeg()` + aviso vermelho quando o parcial sobrevive nos 2 handlers de `KeyboardInterrupt` (batch e single-file); `py_compile` limpo e `pytest test_render_queue.py enhance/ ui/ -q` → **395 passed in 4.95s** (com `FORCE_COLOR` desativado, ACF2); commit 4656a41; ressalva: o 2º `Popen` (Cineon/PyAV, linha ~3486) não foi registrado — fora do escopo do brief, já coberto pelo `terminate()` próprio daquele caminho (detalhe em `.superpowers/sdd/windows-ci-e-interrupcao-robusta/task-8-report.md`) |

## Ciclo AD — interrupção robusta (YF1) — 2026-08-18

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AD4 | done | .claude/memory/STATE.md, .claude/memory/PLAN.md, .claude/memory/FINDINGS.md | Smoke test real em Windows, na janela medida do `YF1`: interrupção em t=125 s com o `.mp4` parcial já no disco → **nenhum ffmpeg órfão** após a saída do Python, **parcial removido** (`● output parcial removido: clip1_Hollywood_CRF18.mp4`), `exit=130`; execução seguinte na **mesma pasta** → `✓ Sucesso: 3/3`, nenhuma linha `○ Pulados`. Ramo do aviso **reproduzido de verdade** (2 execuções), segurando o handle do parcial num processo separado: a remoção falha mesmo com a retentativa, o aviso aparece (`✗ NÃO foi possível remover ...`), `exit=130`, **sem órfão**, e o que sobra é um arquivo truncado (0 e 262192 bytes; `ffprobe` → `moov atom not found`) — no `YF1` original o órfão terminava o arquivo sozinho (3710103 bytes, `ffprobe` limpo) e a execução seguinte o promovia a pronto. Saída literal abaixo. |

### Correção de rigor desta seção (2ª captura, após revisão)

A **primeira** captura desta task foi refeita do zero. Motivo, registrado sem maquiagem: os dois
comandos de extração colados aqui apareciam como
`grep -a -n "output parcial|Fila interrompida|..."`, com `|` nu. O comando **realmente executado**
usava `\|` (alternação de BRE do GNU grep, que funciona); ao transcrever para este arquivo as
barras invertidas foram perdidas, e o comando como ficou escrito **não** reproduz a saída colada
logo abaixo dele. As linhas de saída eram cópia literal do terminal, mas um comando que não
reproduz o que está colado embaixo dele não é evidência verificável — e esta seção é o que fecha
o `YF1`. Comprovação da diferença, nesta máquina:

```
$ grep --version | head -1
grep (GNU grep) 3.0
$ printf 'linha com foo\nlinha com bar\n' > .smoke/grep_check.txt
$ grep -n "foo|bar" .smoke/grep_check.txt
rc=1
$ grep -n "foo\|bar" .smoke/grep_check.txt
1:linha com foo
2:linha com bar
rc=0
$ grep -E -n "foo|bar" .smoke/grep_check.txt
1:linha com foo
2:linha com bar
rc=0
```

Na captura nova, **toda** extração usa `grep -E` explícito (ou `sed -n` de faixa de linhas, sem
regex nenhuma), exatamente como está colado. Os logs brutos ficaram em `.smoke/` para conferência
de terceiros: `step1.log`, `step2.log`, `step3.log`, `step3b.log`, `probe_step1.log`,
`probe_step3.log`, `probe_step3b.log`, `hold.log`, `artefato_step3_parcial.mp4`,
`color_check*.log`/`.txt`, `grep_check.txt`.

O mesmo defeito de transcrição existe **fora** desta seção, na evidência do Ciclo Y (linha ~1913
deste arquivo: `$ grep -a -n "output parcial|Fila interrompida|Interrompidos|Sucesso|exit=" step2d.log`,
também com `|` nu e também seguido de 4 linhas de saída que ele não produziria). Não foi tocado
aqui — é registro de outro ciclo, e reescrever evidência alheia sem reexecutá-la seria o erro
oposto. Fica anotado para o Orquestrador decidir (os logs daquele ciclo já não existem, então a
correção lá só pode ser uma nota, não uma recaptura).

### Ambiente

Windows 10 Pro 10.0.19045, git-bash (MSYS), Python 3.12.10, ffmpeg 7.1.1-full_build-www.gyan.dev,
GNU grep 3.0. Mesmo arranjo do Ciclo Y: pastas `.smoke/batch_in` e `.smoke/batch_out` dentro do
worktree, 3 clipes sintéticos gerados com o comando do plano
(`testsrc=size=1080x1920:rate=30:duration=8` + `sine=frequency=440:duration=8`,
`-c:v libx264 -c:a aac -shortest`), interrupção entregue por `_thread.interrupt_main()` de uma
thread-timer sobre `runpy.run_path(..., run_name="__main__")` — o mesmo caminho de entrega do
Ctrl+C do console. Nenhum código de produção foi tocado nem monkey-patchado. Duas diferenças de
ambiente em relação ao Ciclo Y, ambas só de captura: `PYTHONIOENCODING=utf-8` (senão o log
redirecionado quebra em cp1252) e `FORCE_COLOR` fora do ambiente (`ACF2`). Runner:
`python .smoke/run_interrupt.py <delay> <probe.log> [t_hold] [dur_hold]`, com
`sys.argv = ["Reels_Encoder_v2_FINAL.py", "--batch", <in>, "--output-dir", <out>]`.

Clipes de entrada (2ª captura):

```
gen_exit=0
.smoke/batch_in:
total 556
drwxr-xr-x 1 Usuario 197121      0 Aug 18 15:45 .
drwxr-xr-x 1 Usuario 197121      0 Aug 18 15:45 ..
-rw-r--r-- 1 Usuario 197121 187935 Aug 18 15:45 clip1.mp4
-rw-r--r-- 1 Usuario 197121 187935 Aug 18 15:45 clip2.mp4
-rw-r--r-- 1 Usuario 197121 187935 Aug 18 15:45 clip3.mp4
```

### Step 1 — interrupção dentro da janela medida (t=125 s)

Sonda do próprio runner (a cada 5 s, só `os.path.getsize` no `batch_out`) — confirma que o `.mp4`
parcial **existia no disco** no instante da interrupção, que é a condição do `YF1`. Trecho final de
`.smoke/probe_step1.log` (o arquivo integral tem uma linha a cada 5 s desde t=0):

```
t=110s mp4=nao
t=115s mp4=SIM clip1_Hollywood_CRF18.mp4=0
t=120s mp4=SIM clip1_Hollywood_CRF18.mp4=48
t=125s mp4=SIM clip1_Hollywood_CRF18.mp4=786480
```

```
=== ls batch_out ANTES ===
total 4
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:45 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:45 ..
=== run (interrupt em 125s) ===
exit=130
=== tasklist LOGO APOS a saida do python ===
nenhum ffmpeg em execucao agora
=== ls batch_out DEPOIS ===
total 4
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:47 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:45 ..
```

```
$ grep -E -a -n "output parcial|Fila interrompida|Interrompidos|Sucesso|NAO foi possivel|exit_do_processo" .smoke/step1.log
33:⚠ Fila interrompida pelo usuário
34:  ● output parcial removido: clip1_Hollywood_CRF18.mp4
45:✓ Sucesso:  0/3
46:⚡ Interrompidos: 1/3
49:exit_do_processo=130
rc=0

$ wc -l .smoke/step1.log
49 .smoke/step1.log

$ sed -n "30,50p" .smoke/step1.log
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

⚠ Fila interrompida pelo usuário
  ● output parcial removido: clip1_Hollywood_CRF18.mp4

────────────────────────── 📊 Fila — Relatório Final ──────────────────────────
                                Resumo da fila

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⚡           —
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

✓ Sucesso:  0/3
⚡ Interrompidos: 1/3
Tempo total da fila: 00:00

exit_do_processo=130
```

(O padrão `NAO foi possivel` sem acento entra na alternação de propósito: é a mesma extração usada
no Step 3, onde há linha para casar. Aqui ela não casa porque a remoção **funcionou** — que é o
resultado esperado deste step.)

Comparação direta com o `YF1` do Ciclo Y, mesma janela e mesmo preset: lá o parcial de
1310768 bytes **sobreviveu** e a linha `● output parcial removido:` nunca apareceu.

### Step 2 — os três sintomas do YF1

| # | critério | medido | veredito |
|---|----------|--------|----------|
| 1 | ffmpeg após a saída do Python | `tasklist \| grep -i ffmpeg` → `nenhum ffmpeg em execucao agora`, colhido no mesmo comando, logo após o `exit=130` (repetido nas 3 execuções interrompidas) | **sem órfão** |
| 2 | arquivo parcial | `batch_out` vazio no `ls` posterior + linha `● output parcial removido: clip1_Hollywood_CRF18.mp4` | **removido** |
| 3 | execução seguinte (mesma pasta) | `✓ Sucesso: 3/3`; o `grep -E` por `Pulados` não devolve **nenhuma** linha; `.qc.json`/`.qc.html` gerados para os 3 | **refeito, não pulado** |

Sintoma 3, saída literal (fila completa rodada de novo na **mesma** `batch_in`/`batch_out`):

```
=== ls batch_out ANTES ===
total 4
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:47 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:45 ..
=== run completo (mesma pasta) ===
exit=0
=== ls batch_out DEPOIS ===
total 10940
drwxr-xr-x 1 Usuario 197121       0 Aug 18 15:54 .
drwxr-xr-x 1 Usuario 197121       0 Aug 18 15:48 ..
-rw-r--r-- 1 Usuario 197121 3710103 Aug 18 15:50 clip1_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 18 15:50 clip1_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2773 Aug 18 15:50 clip1_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 18 15:52 clip2_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 18 15:52 clip2_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2773 Aug 18 15:52 clip2_Hollywood_CRF18.qc.json
-rw-r--r-- 1 Usuario 197121 3710103 Aug 18 15:54 clip3_Hollywood_CRF18.mp4
-rw-r--r-- 1 Usuario 197121   12987 Aug 18 15:54 clip3_Hollywood_CRF18.qc.html
-rw-r--r-- 1 Usuario 197121    2773 Aug 18 15:54 clip3_Hollywood_CRF18.qc.json
=== grep -E -a -n "Sucesso|Pulados|Interrompidos" .smoke/step2.log ===
66:✓ Sucesso:  3/3
rc=0
=== tail -14 .smoke/step2.log ===
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:15

────────────────────────── 📊 Fila — Relatório Final ──────────────────────────
                                Resumo da fila

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:14
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:11
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ✓        02:15

✓ Sucesso:  3/3
Tempo total da fila: 06:41
```

O `grep -E` por `Pulados` devolvendo **só** a linha de `Sucesso` é a prova negativa direta: o job 1
— o interrompido — foi **refeito do zero em 02:14** e passou pelo pós-encode (`.qc.json`/`.qc.html`
presentes), em vez de virar `○ pulado` como no `YF1`.

### Step 3 — o ramo do aviso, provado de verdade (duas execuções)

Método: um processo Python **separado** (`.smoke/hold_handle.py`, lançado por `subprocess.Popen` a
partir do runner, sem tocar em código de produção) espera o `.mp4` de saída aparecer, abre-o com
`open(path, "rb")` e segura o handle por 40–50 s — muito além da janela de retentativa do
`discard_partial_output` (3 tentativas × 0.5 s). No Windows o `open()` do CPython não concede
`FILE_SHARE_DELETE`, então o `DeleteFileW` por trás do `os.remove` falha com `OSError` mesmo depois
de o ffmpeg ter sido encerrado.

**3ª execução** (`step3`, interrupção em t=125 s, handle a partir de t=110 s por 40 s):

```
=== ls batch_out ANTES ===
total 8
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:55 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:55 ..
=== run (interrupt em 125s, handle preso a partir de t=110s por 40s) ===
exit=130
=== tasklist LOGO APOS a saida do python ===
nenhum ffmpeg em execucao agora
=== hold.log ===
HOLD: handle aberto em C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\windows-ci-interrupcao-robusta\.smoke\batch_out\clip1_Hollywood_CRF18.mp4 (t=12.2s do holder)
=== ls batch_out DEPOIS ===
total 8
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:57 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:57 ..
-rw-r--r-- 1 Usuario 197121 0 Aug 18 15:57 clip1_Hollywood_CRF18.mp4
=== probe_step3.log (ultimas 6) ===
t=100s mp4=nao
t=105s mp4=nao
t=110s mp4=nao
t=115s mp4=nao
t=120s mp4=nao
t=125s mp4=SIM clip1_Hollywood_CRF18.mp4=0
```

```
$ grep -E -a -n "output parcial|Fila interrompida|Interrompidos|Sucesso|foi poss|incompleto|exit_do_processo" .smoke/step3.log
33:⚠ Fila interrompida pelo usuário
34:  ✗ NÃO foi possível remover clip1_Hollywood_CRF18.mp4
35:    Este arquivo está incompleto e NÃO passou pelo controle de qualidade. 
47:✓ Sucesso:  0/3
48:⚡ Interrompidos: 1/3
51:exit_do_processo=130
rc=0

$ wc -l .smoke/step3.log
51 .smoke/step3.log

$ sed -n "30,55p" .smoke/step3.log
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

⚠ Fila interrompida pelo usuário
  ✗ NÃO foi possível remover clip1_Hollywood_CRF18.mp4
    Este arquivo está incompleto e NÃO passou pelo controle de qualidade.
Apague-o à mão antes de rodar a fila de novo, ou ele será tratado como pronto.

────────────────────────── 📊 Fila — Relatório Final ──────────────────────────
                                Resumo da fila

  #   Arquivo                                                Status   Duração
 ─────────────────────────────────────────────────────────────────────────────
  1   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ⚡           —
  2   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —
  3   C:\Users\Usuario\Documents\GitHub\encoder_ai_instag…     ·            —

✓ Sucesso:  0/3
⚡ Interrompidos: 1/3
Tempo total da fila: 00:00

exit_do_processo=130
```

Esta execução saiu **mais lenta** que a do Step 1: o `.mp4` só apareceu perto de t=122 s, então o
parcial retido tinha 0 byte. O ramo do aviso está provado, mas com um parcial vazio o contraste
"arquivo truncado × arquivo de aparência íntegra" fica fraco — por isso a execução foi repetida com
a interrupção 7 s mais tarde.

**4ª execução** (`step3b`, interrupção em t=132 s, handle a partir de t=112 s por 50 s):

```
=== ls batch_out ANTES ===
total 8
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:58 .
drwxr-xr-x 1 Usuario 197121 0 Aug 18 15:58 ..
=== run step3b (interrupt em 132s, handle preso a partir de t=112s por 50s) ===
exit=130
=== tasklist LOGO APOS a saida do python ===
nenhum ffmpeg em execucao agora
=== hold.log ===
HOLD: handle aberto em C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\.claude\worktrees\windows-ci-interrupcao-robusta\.smoke\batch_out\clip1_Hollywood_CRF18.mp4 (t=11.4s do holder)
=== ls batch_out DEPOIS ===
total 268
drwxr-xr-x 1 Usuario 197121      0 Aug 18 16:01 .
drwxr-xr-x 1 Usuario 197121      0 Aug 18 15:58 ..
-rw-r--r-- 1 Usuario 197121 262192 Aug 18 16:01 clip1_Hollywood_CRF18.mp4
=== probe_step3b.log (ultimas 6) ===
t=105s mp4=nao
t=110s mp4=nao
t=115s mp4=nao
t=120s mp4=nao
t=125s mp4=SIM clip1_Hollywood_CRF18.mp4=0
t=130s mp4=SIM clip1_Hollywood_CRF18.mp4=48
=== grep -E -a -n "output parcial|Fila interrompida|Interrompidos|Sucesso|foi poss|incompleto|exit_do_processo" .smoke/step3b.log ===
33:⚠ Fila interrompida pelo usuário
34:  ✗ NÃO foi possível remover clip1_Hollywood_CRF18.mp4
35:    Este arquivo está incompleto e NÃO passou pelo controle de qualidade. 
47:✓ Sucesso:  0/3
48:⚡ Interrompidos: 1/3
51:exit_do_processo=130
```

Estado do parcial depois de o holder soltar o handle, e `ffprobe`:

```
=== estado do parcial do step3b ~1min depois ===
total 268
drwxr-xr-x 1 Usuario 197121      0 Aug 18 16:01 .
drwxr-xr-x 1 Usuario 197121      0 Aug 18 15:58 ..
-rw-r--r-- 1 Usuario 197121 262192 Aug 18 16:01 clip1_Hollywood_CRF18.mp4
nenhum ffmpeg em execucao agora
=== ffprobe do parcial ===
[mov,mp4,m4a,3gp,3g2,mj2 @ 000002466d7ab140] moov atom not found
.smoke/batch_out/clip1_Hollywood_CRF18.mp4: Invalid data found when processing input
ffprobe_exit=1
```

Os três pontos do brief para este step, nas duas execuções: a mensagem aparece, o `exit` continua
**130**, e — mesmo no caminho de falha — **não sobra órfão**. O arquivo que sobra é comprovadamente
truncado (`moov atom not found`, e o tamanho **não** cresce depois da saída do Python), não um
arquivo de aparência íntegra. Contraste literal com o `YF1` do Ciclo Y, mesma janela: lá o
`ffprobe` do arquivo que sobrou devolvia `duration=8.000000` / `size=3710103` / `ffprobe_exit=0` —
o órfão tinha terminado de escrever sozinho.

### Sobre os tamanhos que se repetem entre execuções (pergunta da revisão)

Os valores `0`, `48`, `262192` e `786480` reaparecem em execuções diferentes, mas **os instantes
não**: o `.mp4` apareceu em t≈113 s no Step 1, em t≈122 s na 3ª execução e em t≈122 s na 4ª. Ou
seja, o relógio derrapa vários segundos entre execuções — o que se repete é o **tamanho**, não o
tempo. A razão é que o tamanho no disco é uma função-escada de degrau grosso: o mp4 é escrito em
blocos de 256 KiB acima de um cabeçalho de 48 bytes, e a sonda de 5 s quase sempre cai no meio de
um degrau.

```
$ python -c "..."
48-48 = 0
262192-48 = 262144 = 256KiB* 1.0
786480-48 = 786432 = 256KiB* 3.0
```

Todos os tamanhos observados são exatamente `48 + k × 256 KiB` (k = 0, 1, 3). Por isso duas
execuções com fases diferentes podem devolver o mesmo número inteiro — e por isso, quando a fase
muda o bastante (3ª e 4ª execuções), a leitura muda junto (`0` em t=125 s em vez de `786480`).
Confirmação pedida pela revisão: **não**, as tabelas de sondagem não são idênticas entre steps
nesta 2ª captura; a coincidência da 1ª captura era de quantização, não de transcrição.

### Limitação de captura: o vermelho não aparece em log redirecionado (não é divergência de produto)

Neste console o `rich` reporta `legacy_windows=True` e `color_system=windows` — a cor sai por API
Win32, não por escape ANSI, então **qualquer** markup perde a cor ao ser redirecionado para
arquivo, não só este aviso. Reprodução isolada, artefatos em `.smoke/color_check*`:

```
FORCE_COLOR=1, Console() padrao, saida redirecionada:
  bytes= 56  ESC(0x1b)= 0
  conteudo= b'  X NAO foi possivel remover clip1_Hollywood_CRF18.mp4\r\n'
legacy_windows= True is_terminal= True color_system= windows
Mesmo markup em console nao-legacy:
   '\x1b[1;31m  X NAO foi possivel remover clip1_Hollywood_CRF18.mp4\x1b[0m\n'
```

O verificável, portanto: (a) a linha do aviso é impressa — literal acima, em duas execuções; (b) o
markup no fonte é `[bold red]` (`Reels_Encoder_v2_FINAL.py`, handler de `KeyboardInterrupt` do
batch e do single-file); (c) o mesmo markup renderiza `\x1b[1;31m` num console capaz de ANSI.
Registrado como limitação do método de captura nesta máquina, **não** como achado novo: nenhum
comportamento observado divergiu do esperado pelo brief.

### Suíte

```
$ python -m pytest test_render_queue.py enhance/ ui/ -q
........................................................................ [ 91%]
...................................                                      [100%]
395 passed in 4.96s
```

(`FORCE_COLOR` fora do ambiente, conforme `ACF2`.)

### Cleanup

A pasta `.smoke/` foi mantida **intacta** ao fim da recaptura — logs brutos, sondas, scripts do
runner, o parcial truncado da 3ª execução (`artefato_step3_parcial.mp4`) e os artefatos de cor — a
pedido do Orquestrador, para conferência independente antes de qualquer remoção. Ele conferiu
direto nos arquivos brutos (`grep -E` nos 3 logs batendo byte a byte com o que está colado acima,
`wc -l` em 49/51/51, e as sondagens confirmando a quantização em degraus de 256 KiB com tempos de
primeiro aparecimento genuinamente distintos entre execuções: 115 s / 122 s / 125 s) e liberou o
cleanup. `.smoke/` removida em seguida, mesmo padrão do Ciclo Y:

```
$ rm -rf .smoke
$ tasklist | grep -i ffmpeg
nenhum ffmpeg em execucao agora
$ ls -d .smoke
.smoke removida
$ git status --short
?? docs/windows-ci-e-interrupcao-robusta.md
```

O único não-rastreado restante já existia antes desta task.

## Fix wave da revisão final de branch — Ciclo AD (2026-08-18)

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| I2 | done | `Reels_Encoder_v2_FINAL.py` (`ed338f2`) | `run_ffmpeg_with_cineon`: corpo a partir do `Popen` envolvido em `try/finally` com `_register_ffmpeg(ffmpeg_process)` / `_register_ffmpeg(None)`; `git diff -w` = 4 linhas adicionadas, resto puro reindent |
| I3 | done | `Reels_Encoder_v2_FINAL.py` (`f15c830`) | handler single-file passa a usar `render_queue.discard_partial_output(QueueJob(...))` (3 tentativas × 0,5 s) com o mesmo aviso vermelho do batch |
| M1 | done | `Reels_Encoder_v2_FINAL.py` (`a2924e2`) | `try:` de `_run_encoding` movido para logo após `_register_ffmpeg(process)`, cobrindo a criação/`start()` da thread do reader |
| M2 | done | `Reels_Encoder_v2_FINAL.py` (`48a3d70`) | `terminate_active_ffmpeg`: `wait(timeout)` também depois do `kill()`; docstring passa a dizer que o `True` significa "havia processo vivo", não "morte confirmada" |
| M4 | done | `test_render_queue.py` (`274a483`) | `test_discard_partial_output_gives_up_after_attempts` conta as chamadas e exige `calls["remove"] == 3`; mutação de controle (`range(attempts)` → `range(1)`) faz o teste falhar, e o teste volta a passar com o código restaurado |

Verificação final (Windows real, worktree `windows-ci-interrupcao-robusta`):

```
$ python -m pytest test_render_queue.py enhance/ ui/ -q
395 passed in 5.20s
$ python -m py_compile Reels_Encoder_v2_FINAL.py
PY_COMPILE_OK (limpo)
```

Cobertura do `try/finally` do I2 conferida por AST, não por leitura: o `Try` é o
**último** statement do corpo de `run_ffmpeg_with_cineon` (linhas 3540→3896, fim da
função em 3896), o primeiro statement do `try` é `_register_ffmpeg(ffmpeg_process)`
e o `finalbody` é `_register_ffmpeg(None)`. Os 3 `raise` que ficam fora do `try`
(3217 LUT ausente, 3517 falha do `av.open`, 3538 falha ao iniciar o `Popen`) são todos
**anteriores** à existência do processo — não há registro a limpar neles.

Smoke real do I2, em Windows, `--batch --cineon-pipeline on` com clipe sintético de
6 s (`testsrc2` 1080×1920 + `anullsrc`), mesmo mecanismo da Task 9 (`runpy` +
`_thread.interrupt_main()`); o watchdog detecta o ffmpeg do encode pela linha de
comando (`Win32_Process` contendo `_Cineon_Film`) — detecção independente do fix — e
interrompe 6 s depois, com o pipe de frames aberto:

```
com o fix (HEAD 274a483):
[smoke] encode Cineon vivo: ['19072']
[smoke] disparando KeyboardInterrupt
[smoke] exit=130 apos 99s
[smoke] ORFAOS apos 3s: nenhum
[smoke] conteudo de .../clips:
[smoke]   clipA.mp4  4961983 bytes
[smoke]   enhance_ai_log.json  1035 bytes

controle (mesma árvore, com `_register_ffmpeg(ffmpeg_process)` trocado por `pass`):
[smoke] encode Cineon vivo: ['19388']
[smoke] disparando KeyboardInterrupt
[smoke] exit=130 apos 99s
[smoke] ORFAOS apos 3s: ['19388']
[smoke] conteudo de .../clips:
[smoke]   clipA.mp4  4961983 bytes
[smoke]   clipA_Cineon_Film.mp4  48 bytes
[smoke]   enhance_ai_log.json  2067 bytes
```

O controle reproduz o `YF1` na íntegra dentro do caminho Cineon (ffmpeg órfão vivo
após `exit=130` + parcial `clipA_Cineon_Film.mp4` sobrevivendo, que a execução
seguinte da fila promoveria a `○ pulado`); com o fix, nenhum órfão e nenhum parcial.
A mutação de controle foi revertida com `git checkout --` e a árvore reconferida
(`git status --short` só com o `docs/windows-ci-e-interrupcao-robusta.md` que já
existia antes desta task). Artefatos do smoke ficaram fora do repo, em
`%TEMP%\smoke_fix1\` (`run_smoke.py`, `fixed.log`, `control.log`).

## Correção de registro — Ciclo AD, causa raiz do batch (2026-08-18)

**Conclusão original (Task 8, `.superpowers/sdd/windows-ci-e-interrupcao-robusta/task-8-report.md`
§ "Preocupações", item 2):** "`terminate_active_ffmpeg()` no handler do batch tende a
retornar `False` no caso comum. Como `_run_encoding` já limpa o registro no seu `finally`
(que também mata o processo) antes de a exceção subir até `main()`, quando o handler do
batch roda o registro normalmente já está `None` [...] Isso é defesa em profundidade, não
o caminho quente."

**Por que estava errada:** a revisão final de branch (posterior à Task 8) confirmou, com
evidência direta do próprio código, que essa premissa não se sustenta. `render_queue.py:172-177`
documenta explicitamente: "O KeyboardInterrupt chega na main thread (aqui), nunca no worker: o
`except Exception` de `_target` não vê `BaseException`." Em `--batch`, o encode roda dentro de
uma worker thread (`run_job`, `render_queue.py`) via `_target()`; o `finally` de `_run_encoding`
vive nessa worker thread. Quando `Ctrl+C` chega, o `KeyboardInterrupt` é entregue à **main**
thread (dentro de `worker.join(timeout=tick_interval)`, `render_queue.py:171`) — a worker
thread continua rodando, o `finally` de `_run_encoding` **não roda antes** do handler da main
thread reagir. Ou seja: em `--batch`, `terminate_active_ffmpeg()` não é defesa em profundidade
redundante — é o **único** mecanismo real de terminação do ffmpeg do encode.

**Consequência real que essa correção revelou:** ao reexaminar a causa raiz do batch, a
revisão identificou que o caminho Cineon (`run_ffmpeg_with_cineon`, `Popen` da linha ~3486)
nunca registrava seu processo em `_register_ffmpeg` — o mesmo gap do `YF1`, só que dentro do
pipeline Cineon. Fechado na fix wave da revisão final de branch já documentada acima em
"Fix wave da revisão final de branch — Ciclo AD (2026-08-18)": item I2, commit `ed338f2`
(`try/finally` com `_register_ffmpeg`/`_register_ffmpeg(None)` em torno do `Popen` Cineon),
com smoke test real confirmando o fechamento do gap (commits `ed338f2`..`a2578ae`, ver seção
acima para a saída literal do smoke com/sem o fix).

---

## Ciclo AE — LUT W80 — 2026-08-22

| ID | status | arquivo tocado | resultado |
| --- | --- | --- | --- |
| AE2 | done | `tools/generate_hollywood_lut_cooler.py`, `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube` | gerador determinístico + cube assado (33³ = 35.937 nós, 823 no clamp) |
| AE3 | done | `tools/test_generate_hollywood_lut_cooler.py` | 6 asserts de propriedade, `6 passed` |

### Ordem TDD executada

Teste escrito **antes** do bake. RED verificado: `6 failed in 0.84s`, cada um pela razão
esperada — `FileNotFoundError` no cube ausente (5 testes) e
`can't open file '...tools\generate_hollywood_lut_cooler.py'` / `returncode 2` no teste de
determinismo. Só depois o gerador foi escrito e o cube assado.

### Transformação aplicada (§ "Transformação" do PLAN, literal)

`delta = o - i` ; `out' = o - 0.20 * (delta · ŵ) * ŵ` com `ŵ = (1,0,-1)/√2` ;
`out' = clip(out', LO, HI)`. `FATOR = 0.20` é constante nomeada no topo, exposta como
`--fator`. `LO`/`HI` derivados por leitura do cube fonte, com `assert` de que valem
`0.031373` / `0.921569` — clamp para o envelope da fonte, **nunca** para `[0,1]`.

Ordem red-fastest (`k = ri + gi*N + bi*N²`) **verificada no fonte**, não presumida:
`k=32` (entrada `1,0,0`) → `0.638644 0.100937 0.101338` (vermelho);
`k=32*N` (entrada `0,1,0`) → `0.385600 0.816980 0.385931` (verde);
`k=32*N²` (entrada `0,0,1`) → `0.126615 0.126549 0.534452` (azul).
Confirmação cruzada: os ganhos medidos nessa ordem reproduzem exatamente os números do
diagnóstico do PLAN (warm `0.767991`, green-magenta `0.714632`).

Arquivo: CRLF (mesma convenção do fonte), ASCII, `%.6f`, 2 linhas de header + 35.937 de
dados, 1.006.351 bytes. Header `TITLE "... - Neutral Shadows - Warm 80%"` + `LUT_3D_SIZE 33`.

### Números medidos (ajuste linear pela origem, nós com saturação de entrada > 0.05)

| métrica | v6.7B fonte | v6.7B-W80 | alvo do PLAN |
| --- | --- | --- | --- |
| ganho warm-cool `(R−B)` | `0.767991` | **`0.813692`** | `0.8144 ± 0.002` ✓ |
| ganho green-magenta `(2G−R−B)` | `0.714632` | **`0.714818`** | `0.7146 ± 0.001` ✓ |
| ganho de luma (`0.2126R+0.7152G+0.0722B`) | `0.989460` | **`0.989629`** | inalterado (Δ `1.7e-4`) ✓ |
| ganho de saturação (`max−min`) | `0.741595` | `0.765175` | — (consequência) |
| envelope min / max | `0.031373` / `0.921569` | `0.031373` / `0.921569` | preservado ✓ |

**Nós no clamp: 823** de 35.937 (2,29%) — `780` no teto `HI`, `43` no piso `LO`.
Overshoot máximo antes do clamp: `+0.045872` acima de `HI`, `-0.004845` abaixo de `LO`.
Confirma a previsão do PLAN: sem esse clamp, nós claros e saturados estourariam o teto de
1.5 IRE e quebrariam a conformidade `Instagram8bit_TVRange`.

Eixo neutro: os 33 nós `i=j=k` saem **byte a byte idênticos** ao fonte (`delta = 0` no eixo
acromático → `out' = o`), comparados como strings `%.6f`. É o requisito de não mexer na
temperatura do material sem LUT.

Efeito por amostra (Δ warm contra a entrada): azul puro `(0,0,1)` de `+0.5922` para
`+0.4737`; laranja-pele `(0.85,0.65,0.5)` de `+0.0119` para `+0.0095` — queda de ~20% do
push na pele, sutil por desenho, como o PLAN antecipou para a AE6.

### Verificação literal

```
$ python -m pytest tools/test_generate_hollywood_lut_cooler.py -v
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram
configfile: pyproject.toml
plugins: anyio-4.14.2, hydra-core-1.3.4, typeguard-4.5.2
collecting ... collected 6 items

tools/test_generate_hollywood_lut_cooler.py::test_neutral_axis_identical_to_source PASSED [ 16%]
tools/test_generate_hollywood_lut_cooler.py::test_envelope_preserved PASSED [ 33%]
tools/test_generate_hollywood_lut_cooler.py::test_warm_cool_gain_attenuated PASSED [ 50%]
tools/test_generate_hollywood_lut_cooler.py::test_green_magenta_and_luma_unchanged PASSED [ 66%]
tools/test_generate_hollywood_lut_cooler.py::test_structure PASSED       [ 83%]
tools/test_generate_hollywood_lut_cooler.py::test_generator_is_deterministic PASSED [100%]

============================== 6 passed in 1.57s ==============================
```

`tools/` **é** coletado pelo pytest sem `conftest.py` nem entrada em `testpaths` (não há
seção `[tool.pytest.ini_options]` no `pyproject.toml`); os testes leem os `.cube` por
caminho absoluto derivado de `__file__`, sem import do módulo gerador.

Baseline da casa preservada: `python -m pytest test_render_queue.py enhance/ ui/ -q` →
`395 passed in 5.72s`. `python -m ruff check` nos dois arquivos novos → `All checks passed!`.

Determinismo: o teste roda o gerador duas vezes via `subprocess` e compara os bytes do
arquivo — idênticos.

### Estado ao fim de AE2+AE3, por desenho

O pipeline **continua apontando para a LUT v6.7B antiga**: `_HOLLYWOOD_LUT_FILENAME` em
`Reels_Encoder_v2_FINAL.py` não foi tocado (é a AE4). O cube fonte permanece no repo para
A/B e rollback. AE4, AE5 e AE6 não foram executadas.

| AE5 | done | `.claude/skills/instagram-reels-encoder/references/color-pipeline.md`, `references/encoder-modes.md`, `references/adaptive-analysis.md`, `scripts/analyze_source.py` | filename trocado nos 4 arquivos + bullet W80 acrescentado em `color-pipeline.md` com os números medidos do PLAN |

### AE5 — Verificação literal

```
$ python -m py_compile .claude/skills/instagram-reels-encoder/scripts/analyze_source.py && echo COMPILE_OK
COMPILE_OK
```

Grep por `v6\.7B_1\.5IRE` (filename antigo) em `.claude/skills/`: **0 ocorrências**.

Anti-escopo respeitado: `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `README.md`,
`tools/verificador_instalacao.py` não tocados (AE4, outro agente). Modo Cineon e
Portra400 não tocados.

| AE4 | done | `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `tools/verificador_instalacao.py`, `README.md` | filename trocado para W80 nos 4 arquivos; mensagem de erro aponta para `tools/generate_hollywood_lut_cooler.py`; `pyproject.toml` mantém a LUT v6.7B original na lista de `data-files` |

### AE4 — Verificação literal

```
$ python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ -q
........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 54%]
........................................................................ [ 72%]
........................................................................ [ 91%]
...................................                                      [100%]
395 passed in 5.12s
```

Baseline `395 passed` preservada, `ui/test_packaging.py::test_data_files_include_luts`
incluso no run (casamento por sufixo `.cube` genérico, não quebrou).

Anti-escopo respeitado: `.claude/skills/` não tocado (é a AE5, outro agente); modo Cineon,
`FilmLook_Portra400_SkinPriority_D65.cube` e `ui/launcher.py` não tocados; LUT v6.7B
original não apagada.

**Nota operacional:** por concorrência com o agente da AE5 rodando em paralelo no mesmo
worktree, `git add` + `git commit` da AE4 (commit `e0f23ac`) capturou também os arquivos
da AE5 (`.claude/memory/STATE.md`, os 4 arquivos de `.claude/skills/instagram-reels-encoder/`)
que foram staged pelo outro processo entre o `git add` e o `git commit` desta tarefa. O
plano pedia "Commite a AE4 sozinha"; isso não foi possível dado o race condition — o
commit ficou com escopo AE4+AE5 combinado, mas o conteúdo de cada arquivo está correto e
isolado (nenhum arquivo tem edições cruzadas entre as duas tarefas).
| AE7 | done | `tools/generate_hollywood_lut_cooler.py`, `tools/test_generate_hollywood_lut_cooler.py`, `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube` | rebake na variante B (`max(dw, 0)`): ganho warm-cool `0.790588`, 0 violações do invariante 7, mesmo filename, baseline `395 passed` |

### AE7 — Verificação literal

Ordem TDD respeitada. Asserts atualizados **antes** do rebake, rodados contra o cube da
variante A (commit `9ebc425`) para provar que medem alguma coisa:

```
$ python -m pytest tools/test_generate_hollywood_lut_cooler.py -v
FAILED tools/test_generate_hollywood_lut_cooler.py::test_warm_cool_gain_attenuated
FAILED tools/test_generate_hollywood_lut_cooler.py::test_no_node_warmer_than_source
FAILED tools/test_generate_hollywood_lut_cooler.py::test_cooling_nodes_identical_to_source
========================= 3 failed, 5 passed in 2.17s =========================
```

O assert 7 acusou **17.791 nós mais quentes que a v6.7B** na variante A, e o assert 8
acusou dif máxima `0.057204` nos nós com `dw ≤ 0` — a confirmação numérica do achado da
revisão pós-bake. Depois do rebake:

```
$ python tools/generate_hollywood_lut_cooler.py
OK: HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube (33^3 = 35937 pontos, fator=0.2)
    envelope: LO=0.031373 HI=0.921569 | nos no clamp: 370

$ python -m pytest tools/test_generate_hollywood_lut_cooler.py -v
============================== 8 passed in 1.88s ==============================

$ python -m pytest test_render_queue.py enhance/ ui/ -q
395 passed in 4.89s
```

Medição independente sobre o arquivo assado (não sobre a matriz em memória):

| métrica | PLAN.md | medido | veredito |
| --- | --- | --- | --- |
| ganho warm-cool | `0.790588` | `0.790588` (fonte `0.767991`) | casa |
| ganho green-magenta | `0.714645` | `0.714645` (fonte `0.714632`) | casa |
| nós no clamp | `370`, todos no teto | `370`, todos no teto, 0 no piso | casa |
| violações do invariante 7 | `0` | `0` | casa |
| difs do invariante 8 | `0` | `0` em 17.831 nós com `dw ≤ 0` | casa |
| min / max do cube | `0.031373` / `0.921569` | `0.031373` / `0.921569` | casa |
| eixo neutro | exato vs v6.7B | exato (33/33 nós, string `%.6f`) | casa |

Nenhuma divergência contra os números do PLAN.md; `FATOR = 0.20` e a tolerância dos
asserts não foram recalibrados.

Mudanças: no gerador, uma linha de matemática — `projection = np.maximum(delta @
WARM_COOL, 0.0)` — mais o docstring. No teste, assert 3 de `0.8144` para `0.790588`,
assert 4 intocado (`0.7146 ± 0.001` já cobre `0.714645`), e os asserts 7
(`test_no_node_warmer_than_source`) e 8 (`test_cooling_nodes_identical_to_source`) novos.
Preservados: clamp no envelope da fonte, ordem red-fastest, `%.6f`, CRLF (35.939 CRLF,
0 LF solto), `TITLE`/`LUT_3D_SIZE` e o filename — AE4/AE5 não foram tocadas.

**Nota de precisão, sem impacto no resultado:** `delta @ WARM_COOL` (matmul, com FMA) e
`(δR − δB)/√2` discordam de sinal em 18 nós onde `dw ≈ 0` (17.813 vs 17.831 nós com
`dw ≤ 0`). O PLAN.md cita `17.831`, que é a contagem da segunda forma — a usada no teste.
A diferença de saída entre as duas é da ordem de `1e-18`, invisível em `%.6f`, e o
invariante 8 passa nas duas contagens. Não é divergência de resultado, é de contagem
intermediária.

Anti-escopo respeitado: `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `README.md`,
`tools/verificador_instalacao.py` e `.claude/skills/` não tocados; LUT v6.7B original
não apagada; filename não renomeado. `PLAN.md` tem edição pendente do Orquestrador no
working tree e ficou **fora** deste commit.

### AE6 — A/B real e QC de entrega (2026-08-22)

Material (indicado pelo usuário, substituiu o par `calebbrunkow_AFTER` que o Orquestrador
tinha escolhido): fonte `Captions_C32BA2.mp4` (1080x1920, 30fps) e baseline v6.7B
`Captions_C32BA2_Hollywood_2Pass.mp4` (2026-08-21 23:40, encoder 2.1.0). Par superior ao
original porque o baseline é de ontem, mesma geração de código — no par antigo (18/ago)
parte da diferença poderia vir do encoder e não da LUT, contaminando a conclusão.

Reprodutibilidade: parâmetros extraídos do `.qc.json` e do comment tag do MP4 —
`--mode 2pass --performance quality`, VBV `target:8075k max:8882k buf:11990k`. O encode
novo bate no mesmo VBV, byte a byte. Mesma configuração dos dois lados.

**Veredito: aprovado, sem regressão.**

| item | v6.7B (antigo) | W80 (novo) |
|---|---|---|
| `validate_encode.sh` | 19 ✅ / 1 ⚠ / 0 ❌ | 19 ✅ / 1 ⚠ / 0 ❌ |
| checks do `.qc.json` (10) | — | `value` e `passed` idênticos em todos os 10 |
| VMAF não-NEG médio | 90.20 | 90.23 |
| VMAF harmonic mean | 90.06 | 90.08 |
| VMAF mínimo | 82.69 | 82.47 |
| bitrate vídeo | 8054 kbps | 8042 kbps |
| LUFS-I / TP / LRA | −14.0 / −1.4 / 2.6 | −14.0 / −1.4 / 2.6 |

VMAF com modelo não-NEG (`vmaf_v0.6.1`) por decisão de metodologia: o NEG sub-pontua grade
estilizado em ~6 pontos e daria falso negativo. Delta de +0.03 no médio e −0.05 no harmonic
mean é ruído de subsample=5, não movimento material — o esperado para mudança puramente
cromática no eixo warm-cool.

**O ⚠ é pré-existente:** `True Peak −1.4 dBTP` contra recomendado `≤ −1.5`. O `.qc.json` de
21/ago já registrava esse mesmo check como `passed: false`. O Ciclo AE não tocou no caminho
de áudio. Fix fora de escopo deste ciclo (seria `loudnorm` `TP=-1.5`); não corrigido aqui
por decisão de anti-escopo, não por descuido.

**Incidente operacional, ver `FINDINGS.md` § `AEF1`:** ao tentar reproduzir o encode do par
ANTIGO, o agente usou `--output-dir` em modo single-file, onde o flag é no-op silencioso.
Resultado: `videos/calebbrunkow_AFTER_Hollywood_CRF18.mp4` (+ `.qc.json`/`.qc.html` e
`enhance_ai_log.json`) foi sobrescrito com um encode W80. Arquivos untracked, nenhum
arquivo versionado afetado; a fonte `videos/calebbrunkow_AFTER.mp4` está intacta. O par
`Captions_C32BA2` na raiz **não foi tocado** (o agente copiou a fonte para scratchpad antes
de encodar).


## Ciclo AF — teto 96 IRE — 2026-08-22

| ID | status | arquivo tocado | resultado |
| --- | --- | --- | --- |
| AF2 | done | `tools/generate_hollywood_lut_cooler.py`, `HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube` | etapa 1 (lift aditivo) + etapa 2 (warm 80%) nessa ordem; cube assado, 35.937 nós, **0 no clamp** |
| AF3 | done | `tools/test_generate_hollywood_lut_cooler.py` | 10 asserts de propriedade (8 adaptados + INV 9 + INV 10; INV 11 é o `test_no_node_warmer_than_source` adaptado), `10 passed` |

### Ordem TDD executada

Teste reescrito **antes** de tocar o gerador. RED verificado rodando a suíte nova contra o
cube **W80 atual** copiado para o filename da v6.8: `8 failed, 2 passed`. Passaram só
`test_generator_is_deterministic` (meta-teste) e `test_no_node_warmer_than_source` (INV 11 é
invariante que a W80 também satisfaz — é guarda, não medida da mudança). Falhas pelas razões
esperadas: `0.921569 != 0.960000` (teto e eixo neutro), ganho warm-cool `0.790588` vs
`0.790686`, green-magenta `0.7146455` vs `0.714632` (a W80 tem 370 nós clampados que sujam o
eixo green-magenta), `TITLE` v6.7C, lift zero acima do pivô (INV 9, INV 10 e o teste de nós
que já esfriavam).

Após o GREEN, duas asserções foram **corrigidas por defeito de teste, não recalibradas**:
`delta > 0` para todo nó acima do pivô é falso por quantização — imediatamente acima de
`L = 0.75` o lift é menor que meio-ulp de `%.6f` e não aparece no arquivo (23 dos 5.721 nós).
Trocado por `delta >= 0` em todos e `max(delta) == 0.038431` (`= 0.96 − 0.921569`, o teto
inteiro no nó branco), que continua falhando contra a W80 — RED re-verificado: `8 failed,
1 passed` (determinismo deselecionado).

### Transformação aplicada (§ "Transformação" do PLAN, literal)

Etapa 1, `expand_highlights()`: `L = 0.2126R + 0.7152G + 0.0722B` sobre o cube **v6.7B**;
`k = (0.921569 − 0.75)/(0.96 − 0.75)`; `t = clip((L − P)/(HIo − P), 0, None)`;
`L' = P + (HIn − P)(kt + (1−k)t²)` se `L > P`; `E = v + (L' − L)` **somado igualmente aos
três canais**. Para `L <= P`, `L' − L` é `0.0` exato → `E` é bitwise igual ao fonte.

Etapa 2, `cool_warm_axis()` (inalterada): `dw = (E − i)·ŵ`, `F = clip(E − 0.20·max(dw,0)·ŵ,
0.031373, 0.96)` com `ŵ = (1,0,−1)/√2`.

O lift tem projeção **zero** no eixo warm-cool (`ŵ_r + ŵ_b = 0`), então `dw` da etapa 2 é
idêntico ao que a v6.7B crua daria — é isso que faz o teto subir sem reaquecer nada.

Constantes no topo, parametrizáveis: `FATOR = 0.20` (`--fator`), `PIVO = 0.75` (`--pivo`),
`TETO_NOVO = 0.96` (`--teto`). `ENVELOPE_LO = 0.031373` e `ENVELOPE_HI = 0.921569` seguem
sendo lidos do fonte com `assert`. O piso **não mudou**.

### Números medidos (ajuste linear pela origem, nós com saturação de entrada > 0.05)

| métrica | alvo do PLAN | medido na v6.8 | W80 |
| --- | --- | --- | --- |
| teto | `0.960000` (96.00 IRE) | `0.960000` ✅ | `0.921569` |
| piso | `0.031373`, idêntico à v6.7B | `0.031373` ✅ (igualdade exata com o fonte) | `0.031373` |
| nós no clamp | `0` | `0` ✅ | `370` |
| nós mais quentes que a v6.7B | `0` | `0` ✅ (também com tolerância `1e-9`) | `0` |
| ganho warm-cool | `0.790686` | `0.790686` ✅ | `0.790588` |
| ganho green-magenta | `0.714632` = v6.7B | `0.714632` ✅ | `0.714645` |
| eixo neutro | `R=G=B` nos 33; topo `96.00` IRE | ✅, e estritamente monotônico | topo `92.16` IRE |

Os `+9.8e-5` de ganho warm-cool contra a W80 **não** são reaquecimento: são os 370 nós que a
W80 truncava em `B = 0.921569` (clamp para baixo no azul = mais quente). Com teto em `0.96`
ninguém é truncado, e o `R − B` de todo nó é exatamente o da W80 sem clamp. Idem o
green-magenta: a v6.8 volta ao valor da v6.7B porque não há mais truncamento.

**Divergência a reportar, uma:** "saturação média acima do pivô `0.43519` (W80 `0.43511`)".
O PLAN não define a fórmula e nenhuma das 12 definições testadas reproduz `0.435`
(`(max−min)/max`, `(max−min)`, `/média`, `/luma`, norma de croma, sob máscaras de luma do
fonte / da saída / da grade). Com `(max−min)/max` sobre nós com `luma(v6.7B) > 0.75`:
v6.8 `0.40821`, W80 `0.41097`, v6.7B `0.40831`. Em toda definição testada a v6.8 fica a
menos de `0.003` da W80, e as definições absolutas (`max−min`, sem normalizar por luma)
reproduzem o **sinal** do PLAN (v6.8 acima da W80). A queda relativa vem do denominador —
a luma subiu e o croma foi preservado exato, que é justamente o invariante pedido. Nenhuma
constante e nenhum teste foram ajustados por causa disso; a métrica não é critério de done e
não tem teste. **Se o Orquestrador quiser fechar o número, precisa dar a fórmula.**

### Verificação literal

- `python -m pytest tools/test_generate_hollywood_lut_cooler.py -v` → `10 passed in 2.50s`
- `python -m pytest test_render_queue.py enhance/ ui/ -q` → `395 passed in 5.15s` (baseline intocada)
- `python tools/generate_hollywood_lut_cooler.py` → `envelope: LO=0.031373 HI=0.960000 | nos no clamp: 0`
- arquivo: 35.937 linhas de dados + 2 de header, CRLF, ASCII, `%.6f`, `LUT_3D_SIZE 33`,
  ordem red-fastest, `TITLE "Hollywood Cinema Ultimate v6.8 3.1-96IRE_Instagram8bit_TVRange - Neutral Shadows - Warm 80%"`

### Estado ao fim de AF2+AF3, por desenho

O pipeline **continua apontando para a W80** — `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`,
`README.md`, `tools/verificador_instalacao.py` e `.claude/skills/**` não foram tocados; isso é
AF4. A v6.7B e a W80 permanecem no repo. O gerador agora escreve **só** a v6.8 (a W80 no
disco é o artefato do Ciclo AE, preservado byte a byte). `--teto 0.921569` reproduz a W80
linha a linha — **verificado**: com `hi_new == hi_old` sai `k = 1`, o termo quadrático zera e
o lift é `0` em todo nó. O `OUT_PATH` é único, então a W80 não é mais reassada
automaticamente.

| ID | status | arquivo | resultado |
| --- | --- | --- | --- |
| AF4 | done | `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `README.md`, `tools/verificador_instalacao.py`, `.claude/skills/instagram-reels-encoder/references/{color-pipeline,encoder-modes,adaptive-analysis}.md`, `.claude/skills/instagram-reels-encoder/scripts/analyze_source.py` | filename W80 trocado para v6.8 nos 9 arquivos; pyproject.toml e o bullet de rollback em color-pipeline.md retêm a W80 intencionalmente (A/B/rollback); color-pipeline.md ganhou o bullet técnico do lift 96 IRE com os números medidos do Orquestrador |

### AF4 — verificação literal

- `python -m py_compile Reels_Encoder_v2_FINAL.py .claude/skills/instagram-reels-encoder/scripts/analyze_source.py` → sem output (sucesso)
- `python -m pytest test_render_queue.py enhance/ ui/ -q` → `395 passed in 4.95s` (baseline intocada)
- grep de `v6.7B-W80` fora de `.claude/memory/`: só 2 ocorrências, ambas intencionais —
  `pyproject.toml` (lista de rollback) e `color-pipeline.md` linha 90 ("a v6.7B e a v6.7B-W80
  permanecem")
- commit: `24ad1ac` — "docs(lut): apontar produto e skill para HollywoodCinema v6.8 96 IRE (AF4)"

**Divergência da AF2/AF3 fechada pelo Orquestrador (falha de documentação, não do cube).**
A métrica "saturação média acima do pivô" usa máscara sobre o **canal máximo** da v6.7B
(`v6.7B.max(canal) > 0.75` → 16.764 nós), não sobre a luma — o `PLAN.md` omitiu a fórmula,
por isso o executor não reproduziu. Medido no cube v6.8 já assado, com a máscara correta:
v6.7B `0.43013` | W80 `0.43511` | **v6.8 `0.43519`**, batendo com o valor do PLAN.
O executor agiu certo ao parar e reportar em vez de recalibrar o número.

Confirmações independentes do Orquestrador no cube assado: teto `0.960000` (96.00 IRE),
piso `0.031373` com igualdade exata à v6.7B, eixo neutro `R=G=B` em 33/33, e `0` nós mais
quentes que a v6.7B. A saturação praticamente não se move (`0.43511 → 0.43519`, oitava
casa) — é a evidência de que o lift aditivo levantou brilho sem expandir croma. A variante
por canal, descartada, levaria a mesma métrica a `0.45107`.

### AF5 — A/B de três vias e medição de range (2026-08-22)

**Veredito: aprovado. A aposta do teto se sustentou — não recuar para 0.945.**

`validate_encode.sh`: **19 ✅ / 1 ⚠ / 0 ❌**, o mesmo ⚠ pré-existente de True Peak
(`−1.4 dBTP`), confirmado por audit `ebur128` independente. Caminho de áudio não tocado.

Range Y (plano puro, 13 frames, sem conversão):

| métrica | FONTE | v6.7B | W80 | **v6.8** |
| --- | --- | --- | --- | --- |
| `Y > 235` | `0.13708%` | `0.00377%` | `0.00324%` | `0.01383%` |
| `Y < 16` | `0.04285%` | `0.00670%` | `0.00644%` | `0.00634%` |
| p99 / p99.9 | 225 / 236 | 215 / 220 | 215 / 220 | **222 / 227** |
| pico por-frame `Y>235` | `0.24460%` | `0.02812%` | `0.02117%` | `0.08275%` |

- **Piso intocado**, como projetado: `0.00634%` vs `0.00644%` da W80 — 3ª casa, sem tendência.
- **Teto subiu como projetado**: p99 `215→222`, p99.9 `220→227`. Colchão até 235 caiu para
  **8 níveis** (previsão era ~9).
- **Clipping não se materializou.** O pico por-frame de `Y>235` é `0.08275%`, contra o
  gatilho de `>10% dos frames` do `artifact-diagnosis.md`. Três ordens de grandeza de
  margem. Subiu 4,3× em termos relativos, mas o absoluto é irrelevante.

**CORREÇÃO DO ORQUESTRADOR À LEITURA DE VMAF — importante para ciclos futuros.**

Medido: v6.7B `90.20` | W80 `90.25` | v6.8 **`94.90`** (+4,65 pts).

O validador leu isso como ganho de qualidade. **Não é.** O VMAF aqui é medido contra a
fonte **sem grade**, e a LUT muda a imagem de propósito. Logo o VMAF nesta configuração
mede *quanto o grade se afasta da fonte*, não quanto o codec degradou. Subir o teto de
92.16 para 96 IRE torna a LUT tonalmente **menos agressiva**, aproximando o output da
fonte — e o VMAF premia isso. Levar o teto a 100 IRE subiria o VMAF ainda mais, e seria
simplesmente *não gradar*.

Consequência prática: **VMAF-contra-a-fonte não serve como alvo de otimização para decisão
de LUT.** Serve para o que foi usado no Ciclo AE — detectar que uma mudança de croma *não*
degradou nada (`90.20 → 90.23`, ruído). Para julgar teto e piso, o critério válido é o de
range (`YHIGH>235`, `YLOW<16`) e o olho. Mesma família da armadilha já registrada em
`project_vmaf_neg_stylized`: o número sobe ou desce por motivo que não é qualidade.

Os três encodes passam o alvo Safe Premium (≥90) de qualquer forma.

## Ciclo AG — AEF1 e AFF1 — 2026-08-22

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| AG2 | done | Reels_Encoder_v2_FINAL.py | `parser.error()` logo após `parse_args()` se `args.output_dir` e `args.batch is None`; código 2, mensagem cita `--batch` |
| AG3 | done | Reels_Encoder_v2_FINAL.py | `pipeline_tag` deriva de `_HOLLYWOOD_LUT_FILENAME` via regex `_v(\d+\.\d+[\w-]*)_` (fallback: stem); `import re` adicionado ao topo; ramo Cineon intocado |
| AG4 | done | enhance/test_output_dir_and_pipeline_tag.py (novo) | 5 testes; TDD confirmado — 2 falham contra o código pré-fix (`code 1 != 2`, `v6.7 != v6.8`), passam pós-fix; `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → 410 passed (405 baseline + 5) |

Verificação: `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `410 passed in 7.46s`, zero falhas.

Commit `c51516e` (AG2+AG3+AG4 juntos).

Achado reportado, não corrigido: `comment` continua com `HollywoodLUT_*` mesmo
com `--lut off`. `lut_enabled` não é parâmetro de `_build_metadata_args` — não
acessível no escopo de `:1925-1940`. Ver `.claude/memory/FINDINGS.md` § AFF1
para detalhe e call sites a tocar se virar ciclo próprio.

## Ciclo AH — tag NoLUT — 2026-08-22

Passo zero confirmado: `grep lut_enabled cineon_pipeline.py` → 0 ocorrências.
Cineon/Portra400 não conhece `lut_enabled`; `--lut off` não afeta o Cineon.
Critério de aceite 4 do PLAN.md está correto, sem mudança de escopo.

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| AH2 | done | Reels_Encoder_v2_FINAL.py | `lut_enabled: bool = True` adicionado a `_build_metadata_args`; ramo não-Cineon usa `pipeline_tag = "NoLUT"` se `lut_enabled` falso, regex do Ciclo AG intocada se verdadeiro; repassado `lut_enabled=lut_enabled` nos 2 call sites de `run_ffmpeg` (crf e 2pass); os 2 call sites de `run_ffmpeg_with_cineon` não tocados (passam `cineon_mode=True`, curto-circuita) |
| AH3 | done | enhance/test_output_dir_and_pipeline_tag.py | 6 testes novos cobrindo os 5 critérios de aceite (NoLUT quando desabilitado, tag derivada quando habilitado, default preservado, Cineon ignora lut_enabled=False, formato do comment em crf e 2pass) |

Verificação: `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `416 passed in 7.36s` (410 baseline + 6 novos), zero falhas.

Commit `50bed9f` (AH2+AH3 juntos). `FINDINGS.md` § AFF1 fechado, contagem de call sites corrigida de 4 para 2.

## Ciclo AI — ADF1 — 2026-08-22

Escopo confirmado antes de tocar código: 6 `subprocess.run` no módulo, 3 são
ffmpeg de fase de análise (`:1271` de-rotação, `:1363` loudnorm pass 1, `:3783`
remux do átomo `colr`), 3 não (`:383` wmic, `:605` e `:3860` ffprobe). O achado
registrava 2; são 3.

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| AI2 | done | Reels_Encoder_v2_FINAL.py | `_swap_active_ffmpeg(proc) -> prev` (troca atômica sob `_ACTIVE_FFMPEG_LOCK`); `_register_ffmpeg` delega a ela e segue devolvendo `None`; `_run_ffmpeg_tracked(cmd, *, capture_output, text, encoding, errors, check, stdout, stderr, cwd, popen=subprocess.Popen)` registra o proc, `communicate()`, **restaura o anterior no `finally`** e monta `CompletedProcess`; `check` usa `check_returncode()` (CalledProcessError com stdout/stderr) |
| AI3 | done | Reels_Encoder_v2_FINAL.py | 3 call sites migrados com kwargs idênticos: `_strip_residual_rotation` (`check=True, stdout=DEVNULL, stderr=PIPE`), `analyze_audio_loudness` (`capture_output=True, text=True, encoding="utf-8", errors="ignore"`), remux `colr` em `run_ffmpeg_with_cineon` (`check=True, capture_output=True, cwd=script_dir`); `:383`/`:605`/`:3860` intocados; `Popen` principal (`:2004`, `:3554`) intocado |
| AI4 | done | enhance/test_ffmpeg_tracked.py (novo) | 19 testes cobrindo os 7 critérios de aceite; fakes via `types.SimpleNamespace` (sem classes, sem `monkeypatch`, sem fixtures) |

TDD: testes escritos antes da implementação, RED confirmado —
`python -m pytest enhance/test_ffmpeg_tracked.py -q` → `17 failed, 2 passed`
(os 2 que passavam eram os que asseram comportamento pré-existente:
`_register_ffmpeg` e os probes que continuam em `subprocess.run`).

Red-green do critério 2 (assert central do ciclo), feito explicitamente: com o
`finally` degradado para `_register_ffmpeg(None)` — a implementação ingênua que
zera em vez de restaurar — `pytest -k restores` dá `4 failed, 1 passed`, com
`assert None is namespace(...)` em `test_restores_previous_process_not_none`.
Restaurado o `_swap_active_ffmpeg(prev)`, `19 passed`. Ou seja: o teste falha de
verdade contra o clobber que o desenho existe para evitar, não só contra a
ausência do helper.

Verificação: `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `435 passed in 7.28s` (416 baseline + 19 novos), zero falhas. `python -m ruff check enhance/` → `All checks passed!`.

Commit `d66887f` (AI2+AI3+AI4 juntos). `FINDINGS.md` § ADF1 fechado, escopo
corrigido de 2 para 3 processos e risco de clobber registrado.

## Ciclo AJ — CI vermelho por dependência de ffmpeg (AIF1) — 2026-08-25

**Antes (o achado):** run `32590519448`, SHA `3f12070`, job "Tests (ubuntu-latest, Python 3.11)":
`2 failed, 423 passed in 3.07s` — ambas `assert 1 == 0`.

**Verificação local sob PATH sem ffmpeg (reproduz a condição do CI):**
RED, em `fb870bd`: `2 failed, 9 passed in 3.55s`, banner `✗ DEPENDÊNCIA AUSENTE`.
GREEN, em `658598a`: `11 passed`.

**Suíte completa local (PATH normal), antes e depois:** `435 passed` — sem regressão.

**Depois (a correção), CI real:** run `32870623915`, SHA `658598a`, workflow `CI`. Os 4 jobs `Tests`, todos `success`:

| job id | job | conclusion |
|--------|-----|------------|
| 97876458809 | Tests (ubuntu-latest, Python 3.11) | success |
| 97876458827 | Tests (ubuntu-latest, Python 3.12) | success |
| 97876458851 | Tests (windows-latest, Python 3.11) | success |
| 97876458742 | Tests (windows-latest, Python 3.12) | success |

Linha de sumário literal do job 97876458809 (ubuntu-latest, Python 3.11):

```
2026-08-25T16:13:49.6577224Z ============================= 425 passed in 4.45s ==============================
```

Demais jobs do mesmo run, também `success`: `Lint (ruff)`, `Pylint` (run `32870623940`),
`Pester (launcher.ps1) (ubuntu-latest)`, `Pester (launcher.ps1) (windows-latest)`.

423 passed + as 2 que falhavam = 425 passed. Nenhum teste novo foi adicionado neste ciclo;
os dois testes que falhavam agora passam, e é exatamente isso que a contagem mostra.

Ciclo fechado com evidência de CI real, não local — a causa raiz deste ciclo foi
exatamente confiar em execução local que não reflete o ambiente onde o bug vive.

## Ciclo AK — pinar .cube (CRLF) e ligar tools/ no CI (2026-08-25)

| ID | done ou blocked | arquivo tocado | resultado em 1 linha |
|----|------------------|-----------------|------------------------|
| AK1 | done | .gitattributes, os 4 *.cube, .claude/memory/FINDINGS.md | `*.cube -text` criado, blobs renormalizados p/ CRLF, commit `71bc478` — `git cat-file -s HEAD:<arquivo>` == tamanho do worktree para os 4 arquivos |
| AK2 | done | .github/workflows/ci.yml | `tools/` acrescentado à linha do `Run tests`, commit `692d7e4` — `pytest tools/ -q` = 10 passed, árvore limpa depois, `pytest test_render_queue.py enhance/ ui/ tools/ -q` = 435 passed |

Push: `git push -u origin claude/ciclo-ak-cube-crlf-ci` — branch nova enviada, sem PR aberto.

## AK3 — fechamento do Ciclo AK com evidência real de CI (2026-08-25)

**Depois (a correção), run `32875583211`, commit `692d7e4` — os 4 jobs `Tests` `success`:**

| job id | job | conclusion |
|--------|-----|------------|
| 97892573585 | Tests (ubuntu-latest, Python 3.11) | success |
| 97892573549 | Tests (ubuntu-latest, Python 3.12) | success |
| 97892573740 | Tests (windows-latest, Python 3.11) | success |
| 97892573611 | Tests (windows-latest, Python 3.12) | success |

Linhas literais do log do job `97892573585` (ubuntu-latest, Python 3.11) — o job que teria
reprovado antes da correção (`.cube` chegaria em LF sem `.gitattributes`, `test_structure`
mediria 0 CRLF em vez de 35939):

```
2026-08-25T17:03:40.0765441Z tools/test_generate_hollywood_lut_cooler.py::test_structure PASSED       [ 98%]
2026-08-25T17:03:41.4255798Z ============================= 435 passed in 6.86s ==============================
```

435 = os 425 da seleção anterior + os 10 de `tools/`. Nenhum teste novo foi escrito neste ciclo.

**Verificação local complementar (blob == worktree, medida no HEAD atual):** para os 4
`.cube`, `git cat-file -s HEAD:<arquivo>` é **igual** ao tamanho no worktree (1016677 /
1006351 / 1006340 / 1006353) — antes do ciclo (commit `92ae2e6`) diferiam exatamente pela
contagem de `\r` de cada arquivo. O blob de
`HollywoodCinema_Ultimate_v6.8_...cube` agora contém 35939 CRLF, que é exatamente
`DATA_LINES + 2`.

| ID | done ou blocked | arquivo tocado | resultado em 1 linha |
|----|------------------|-----------------|------------------------|
| AK3 | done | .claude/memory/STATE.md, .claude/memory/PLAN.md, .claude/memory/FINDINGS.md | Evidência real de CI verde (run `32875583211`, 4 jobs `Tests` success, 435 passed) registrada; AJF1 fechado; AKF1 aberto (CRLF em `cineon_pipeline.py`/`enhance_visualizer.py`) |

## Ciclo AL — extrair build_parser()/parse_cli() de main() (R8) — 2026-08-25

Run `32878346319`, commit `caf4eb3`, os 4 jobs `Tests` `success`:

| job id | job | conclusion |
|--------|-----|------------|
| 97901632205 | Tests (ubuntu-latest, Python 3.11) | success |
| 97901632247 | Tests (ubuntu-latest, Python 3.12) | success |
| 97901632150 | Tests (windows-latest, Python 3.11) | success |
| 97901632175 | Tests (windows-latest, Python 3.12) | success |

Linha literal do log do job `97901632205`:

```
2026-08-25T17:31:44.8401703Z ============================= 435 passed in 5.38s ==============================
```

Verificações locais (medidas pelo Orquestrador em `caf4eb3`):

- `--help` byte-idêntico ao baseline de `def5ac2`: 139 linhas, md5
  `7dd773cde1f068982e6d97554bacda99` nos dois, `diff` vazio.
- `main`, `build_parser`, `parse_cli` todos callable no módulo.
- `grep -cE "monkeypatch|AIF1" enhance/test_output_dir_and_pipeline_tag.py` → `0`. O
  andaime do Ciclo AJ foi deletado por inteiro.
- Com o PATH sem ffmpeg e **sem nenhum monkeypatch**: `11 passed`.

435 passed = mesma contagem do Ciclo AK; nenhum teste novo foi adicionado, os 3 testes de
`--output-dir` foram reescritos (AL1) para chamar `parse_cli()` direto em vez de `main()`
inteiro via `monkeypatch`.

| ID | done ou blocked | arquivo tocado | resultado em 1 linha |
|----|------------------|-----------------|------------------------|
| AL3 | done | .claude/memory/STATE.md, .claude/memory/PLAN.md, .claude/memory/FINDINGS.md | Evidência real de CI verde (run `32878346319`, 4 jobs `Tests` success, 435 passed) registrada; AJF2 fechado; ALF1 aberto (bloco de UI de `main()` contorna validação de `parse_cli()`) |
| AM1 | done | ui/test_probe.py | Matriz de decisão completa (10 casos parametrizados) via monkeypatch de `subprocess.check_output`, sem ffmpeg/fixture; commit 045192e |
| AM2 | done | ui/test_probe.py | `test_probe_argv_contract` afirma `stream=width,height:stream_tags=rotate:side_data:format_tags=rotate` e o path no argv; mata M8 (ver AM4) |
| AM3 | done | ui/test_probe.py | `test_probe_matches_engine_rotation_swap` compara `probe_source_dims` com `get_input_resolution` (import direto, sem tocar `Reels_Encoder_v2_FINAL.py`) sob o mesmo payload sintético (rotate=90); ambos batem em (1080,1920) |
| AM4 | done | .claude/memory/STATE.md | Matriz de mutação medida em `ui/probe.py` — todos os 8 mutantes revertidos ao final; `git diff --stat -- ui/probe.py` vazio. Tabela abaixo. |

### AM4 — Matriz de mutação medida

| # | mutante | teste(s) que morreram |
|---|---|---|
| M1 | remover swap `width, height = height, width` (linha 71) | `stream_rotate_90`, `stream_rotate_270`, `display_matrix_negative_90`, `tag_90_plus_display_matrix_0_does_not_erase_tag`, `format_rotate_used_when_no_stream_rotation`, `test_probe_matches_engine_rotation_swap` (6 testes) |
| M2 | `if rotation in (90, 270)` (nega ângulos negativos) | `display_matrix_negative_90` |
| M3 | `if rot != 0` → sempre verdadeiro (Display Matrix 0 apaga tag) | `tag_90_plus_display_matrix_0_does_not_erase_tag` |
| M4 | remover guard `if rotation == 0:` antes de `format_tags` | `stream_rotate_wins_over_format_rotate` |
| M5 | remover leitura de `stream_tags.rotate` | `stream_rotate_90`, `stream_rotate_270`, `tag_90_plus_display_matrix_0_does_not_erase_tag`, `stream_rotate_wins_over_format_rotate`, `test_probe_matches_engine_rotation_swap` (5 testes) |
| M6 | remover loop de `side_data_list` (Display Matrix) | `display_matrix_negative_90` |
| M7 | `if width > 0 and height > 0` → sempre verdadeiro | `empty_streams_list`, `zero_width` |
| M8 | remover `stream_tags=rotate` de `-show_entries` | `test_probe_argv_contract` (único teste que pega — confirma a razão de existir do AM2) |
| M9 | trocar conjunto de swap para `(90, 270)` (nega ângulos negativos) | `display_matrix_negative_90` (AM1) e `test_probe_matches_engine_rotation_swap[display_matrix_negative_90]` (AM3-b, parametrizado) |
| M10 | remover `-select_streams v:0` do argv | `test_probe_argv_contract` (único teste que pega) |

Nenhum mutante sobreviveu. `pytest ui/test_probe.py -v` → 24 passed. Suíte completa `test_render_queue.py enhance/ ui/ tools/` → 457 passed (baseline 448 + 9 novos da parametrização do AM3-b), sem regressão.

### AM3-b + AM2-b (correção pós-revisão do Orquestrador)

`test_probe_matches_engine_rotation_swap` parametrizado sobre `ROTATION_MATRIX_CASES` (mesma matriz do AM1): nos casos de dims válidas, `probe_dims == engine_dims == expected`; nos casos `None`, `probe_dims is None and engine_dims == (0, 0)` (contrato assimétrico documentado em `Reels_Encoder_v2_FINAL.py:998-1001`, preservado). `test_probe_argv_contract` ganhou asserção de `-select_streams v:0` no argv. `ui/probe.py` sem diff ao final (`git diff --stat -- ui/probe.py` vazio).

## AM5 — fechamento do Ciclo AM com evidência real de CI — 2026-08-26

`AJF3` fechado. Prova é log real do CI, não execução local.

Run `32993470718` (https://github.com/gabrielschoenardie/encoder_ai_instagram/actions/runs/32993470718),
commit `771d83e`, branch `claude/ciclo-am-probe-rotation-coverage`, PR #46. Os 7 jobs `success`:

| job | conclusão |
|----|-----------|
| Lint (ruff) | success |
| Tests (ubuntu-latest, Python 3.11) | success |
| Tests (ubuntu-latest, Python 3.12) | success |
| Tests (windows-latest, Python 3.11) | success |
| Tests (windows-latest, Python 3.12) | success |
| Pester (launcher.ps1) (ubuntu-latest) | success |
| Pester (launcher.ps1) (windows-latest) | success |

Sumário do pytest colado dos 4 legs de `Tests`:

```
Tests (ubuntu-latest, Python 3.12)  ============================= 457 passed in 7.71s ==============================
Tests (ubuntu-latest, Python 3.11)  ============================= 457 passed in 8.37s ==============================
Tests (windows-latest, Python 3.11) ============================ 457 passed in 10.24s =============================
Tests (windows-latest, Python 3.12) ============================ 457 passed in 21.04s =============================
```

457 = 435 (baseline do Ciclo AL) + 22 novos em `ui/test_probe.py` (2 → 24). Os 22 são:
10 casos de `test_probe_rotation_matrix`, 10 de `test_probe_matches_engine_rotation_swap`,
`test_probe_argv_contract`, e `test_probe_corrupted_output_returns_none`. Os dois testes
originais não foram deletados — foram tornados determinísticos, então não contam como novos.

`ui/probe.py` não foi modificado em nenhum dos 3 commits do ciclo. Confirmado por
`git diff --stat main..HEAD -- ui/probe.py` vazio, medido antes e depois de cada mutante
da matriz do AM4.

**Nota operacional — atraso do CI.** O run não apareceu no push. Diagnosticado ao vivo:
branch no remoto com o SHA certo, `claude/ciclo-am-**` casando com o filtro `branches:`
de `ci.yml:4`, PR aberto contra `main`, Actions `enabled: true`, workflow `CI`
`state=active`, e mesmo assim `total_count: 0` na API de runs por ~10 minutos — sem run
nenhum no repo desde 25/08 17:53. O run entrou sozinho depois, sem nova ação. Não é o
`UF1` (filtro de branch de worktree): esse filtro casa. Foi latência do lado do GitHub.
Registrado porque a confusão custou tempo e vai se repetir: `gh run list` vazio logo após
um push **não** é evidência de que o CI não vai rodar.

## Ciclo AN

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AN1 | done | `cineon_pipeline.py` | Linha 810: `open(path, "r")` → `open(path, "r", encoding="utf-8-sig", errors="replace")`. `git diff --stat` confirma 1 arquivo, 1 linha. |
| AN2 | done | `enhance/test_cineon_lut.py` | Adicionado `test_load_cube_file_independente_de_encoding`, parametrizado sobre 4 `.cube` reais gravados em `tmp_path` (`utf-8-sig` com BOM, `utf-8` com `TITLE "ÁGUA..."`, `cp1252` com o mesmo título, `ascii` puro), `newline=""`, `lut_size==2`. 6/6 testes do arquivo passam (2 pré-existentes + 4 novos). |

### AN3 — matriz de mutação medida

Ordem: aplicar mutante em `cineon_pipeline.py:810`, rodar `pytest enhance/test_cineon_lut.py`, registrar, reverter para o fix do AN1 antes do próximo.

| # | mutante | testes que falham (medido) | esperado no PLAN.md | bate? |
|---|---|---|---|---|
| M1 | `open(path, "r")` (default da plataforma) | `bom_lut_size_primeira_linha`, `utf8_title_acentuado_maiusculo` (medido no Windows/cp1252) | vermelho nos dois SOs, por casos diferentes | sim — nesta perna (Windows), os dois casos que dependem de UTF-8 falham; cp1252 e ascii passam por acidente da plataforma |
| M2 | `encoding="utf-8"` | `bom_lut_size_primeira_linha`, `cp1252_title_acentuado_maiusculo` | PLAN.md diz "só cp1252 vermelho, outros 3 verdes", mas a própria matriz do § Desenho (coluna `utf-8`) já mostra BOM como `✗ sem SIZE` | não integralmente — a coluna "esperado" da tabela de mutação (linha 105) contradiz a matriz do § Desenho (linha 60), que está correta e bate com o medido. Registrando o medido, não a narrativa; não bloqueia o item porque o critério de aceite real ("ao menos um teste em FAIL") é satisfeito |
| M3 | `encoding="utf-8"` + `errors="replace"` | só `bom_lut_size_primeira_linha` | só o caso BOM vermelho | sim |
| M4 | `encoding="utf-8-sig"` sem `errors` | só `cp1252_title_acentuado_maiusculo` | só o caso cp1252 vermelho | sim |

4/4 mutantes mortos (cada um mata ao menos 1 teste). `git diff --stat -- cineon_pipeline.py` ao final do AN3: `1 file changed, 1 insertion(+), 1 deletion(-)` — só a linha do AN1, todos os mutantes revertidos.

Suíte completa pós-ciclo: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `461 passed` (457 baseline + 4 casos novos do AN2). Sem regressão. `--timeout=60` não aplicado localmente: `pytest-timeout` não está instalado neste ambiente (`pip show pytest-timeout` → not found); não é item do escopo AN, não instalado para não desviar do PLAN.
## Ciclo AO

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AO1 | done | `.github/workflows/ci.yml` | Linha 25: `ruff check enhance/` → `ruff check . --output-format=github`. `git diff --stat` confirma 1 arquivo, 1 linha (`1 file changed, 1 insertion(+), 1 deletion(-)`). Commit `9f895b7`. |
| AO2 | done | `.claude/memory/STATE.md` | Matriz de mutação: 4/4 áreas com `enhance/` cego e `.` pegando. Tabela abaixo. `git status --porcelain -- '*.py'` vazio ao final. |

### AO2 — matriz de mutação do gate (injeção `import os, sys` + `x=1;y=2`, revertida após medição)

| arquivo | `ruff check enhance/` | `ruff check .` |
|---|---|---|
| `ui/probe.py` | All checks passed! | 6 erros (E401, E402, I001, F401×2, E702) |
| `tools/verificador_instalacao.py` | All checks passed! | 4 erros (E401, E402, I001, E702) |
| `ebu_meter.py` (raiz) | All checks passed! | 6 erros (E401, E402, I001, F811, F401, E702) |
| `.claude/skills/instagram-reels-encoder/scripts/analyze_source.py` | All checks passed! | 6 erros (E401, E402, I001, F401, F811, E702) |

Suíte completa pós-ciclo: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `461 passed`, sem regressão (baseline). `ruff check .` no repo inteiro após reversão: `All checks passed!`.
## Ciclo AP

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AP1 | done | `.github/workflows/ci.yml` | `Install-Module`/`Import-Module Pester -MinimumVersion 5.5.0` → `-RequiredVersion 5.7.1` nas duas linhas do job `pester`. `git diff --stat` confirma 1 arquivo, `2 insertions(+), 2 deletions(-)`. Commit `db0ec13`. |
| AP2 | done | `.claude/memory/STATE.md` | 3/3 medido localmente com `pwsh 7.5.1` (só 5.7.1 instalada). Detalhe abaixo. |

### AP2 — evidência de que `-RequiredVersion` vincula

(a) `Import-Module Pester -RequiredVersion 5.7.1; (Get-Module Pester).Version`:
```
Major Minor Build Revision
----- ----- ----- --------
5     7     1     -1
```
Carregou 5.7.1, como esperado.

(b) Sessão limpa, `Import-Module Pester -RequiredVersion 9.9.9`:
```
Import-Module: The specified module 'Pester' with version '9.9.9' was not loaded because no valid module file was found in any module directory.
```
Falhou alto (exit code 1), não degradou para outra versão — confirma que o flag vincula.

(c) `Import-Module Pester -RequiredVersion 5.7.1; Invoke-Pester -Path ./tests -CI`:
```
Starting discovery in 2 files.
Discovery found 91 tests in 270ms.
...
Tests Passed: 91, Failed: 0, Skipped: 0, Inconclusive: 0, NotRun: 0
```
Banner de 5.x (`Starting discovery in`), `91` testes, todos passando, sob o pin.

Suíte Python inalterada: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `461 passed`.

## Ciclo AQ

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AQ1 | done | .github/workflows/ci.yml, .github/workflows/pylint.yml | 8 linhas trocadas (checkout v4→v5, setup-python v5/v3→v6, cache v4→v5), `git diff --stat` confirma 12+4 linhas / 8 alterações efetivas em 2 arquivos |

## Ciclo AR

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AR1 | done | .gitattributes | acrescentada `*.py text eol=lf` com comentário; `*.cube -text` intacta; commit a675036 |
| AR2 | done | cineon_pipeline.py, enhance_visualizer.py | `git add --renormalize` escopado aos 2 arquivos; commit 12593d1; `git diff -b a675036..12593d1 -- cineon_pipeline.py enhance_visualizer.py` vazio (exit 0); `file` pós-checkout confirma sem CRLF |
| AR3 | done | — | Correção do Orquestrador sobre o resultado reportado pelo executor: **não é regressão de `rich`, é `ACF2`** (achado já registrado, terceiro incidente nesta sessão — Task 4 do Ciclo AC, verificação do merge do Ciclo AP, e agora aqui). As 4 falhas batem exatamente com a assinatura do `ACF2`: `FORCE_COLOR`/`COLORTERM` herdados do shell do executor fazem o `rich` emitir ANSI onde os testes esperam texto puro. Reexecutei de forma independente com `env -u FORCE_COLOR -u COLORTERM python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `461 passed`, exit 0. `git diff -b a2a9f9d..HEAD -- test_render_queue.py` vazio, confirmando que este ciclo não tocou o arquivo — não havia achado novo a abrir. `ruff check .` limpo (confirmado pelo executor). Critério de aceite do AR3 satisfeito. |
| AQ2 | done | — | YAML válido em ambos (`yaml.safe_load` sem erro); suíte Python `461 passed` (com `FORCE_COLOR` do shell desligado — variável de ambiente do terminal, não do repo, mascarava 4 testes de saída Rich) |

## Ciclo AS

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AS1 | done | test_render_queue.py | `force_terminal=False` acrescentado às 10 instanciações de `Console(...)` (linhas 79, 92, 106, 121, 138, 153, 175, 291, 313, 328); `git diff` só adiciona o parâmetro, `render_queue.py` intocado; commit 09243ba |
| AS2 | done | — | `FORCE_COLOR=3 COLORTERM=truecolor python -m pytest test_render_queue.py -q` → `26 passed`, exit 0; sem essas variáveis → `26 passed`, exit 0 idêntico |
| AS3 | done | — | `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` com `FORCE_COLOR=3 COLORTERM=truecolor` → `461 passed`, exit 0; sem essas variáveis → `461 passed`, exit 0 idêntico |

## Ciclo AT

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| AT1 | done | Reels_Encoder_v2_FINAL.py | `_validate_args_consistency(args) -> Optional[str]` extraída; `parse_cli()` chama e faz `parser.error(msg)`; caminho da UI em `main()` (após `args = launched`) chama e faz `sys.exit(2)` com `console.print` se `msg` não for `None`; `ui/launcher.py` e `ui/config.py` intocados |
| AT2 | done | enhance/test_output_dir_and_pipeline_tag.py | 4 grupos (a,b,c,d) adicionados: (a) 3 testes `None` p/ input só, batch só, batch+output_dir; (b) msg com `--batch` p/ output_dir sem batch via `EncodeConfig(...).to_namespace()`; (c) teste-ponte confirma Namespace do launcher sujeito à mesma validação; (d) teste de wiring monkeypatcha `R.parse_cli`, `ui.preflight.missing_ffmpeg_binaries`, `ui.launcher.run_launcher` e afirma `SystemExit(2)` em `R.main()`; `pytest enhance/test_output_dir_and_pipeline_tag.py -v` → `17 passed`, exit 0; suíte completa `python -m pytest -q` → `467 passed`, exit 0 |
| AT3 | done | .claude/memory/STATE.md | matriz de mutação abaixo; 2/2 mutantes mortos por testes distintos; ambos revertidos; `git diff --stat -- Reels_Encoder_v2_FINAL.py` ao fim = `18 insertions(+), 5 deletions(-)`, idêntico ao AT1 isolado |

### Matriz de mutação AT3

| mutante | mudança | teste que morre | resultado (`pytest enhance/test_output_dir_and_pipeline_tag.py -v`) | revertido |
|---------|---------|------------------|------------------------------------------------------------------------|-----------|
| M1 | remove chamada de `_validate_args_consistency` no caminho da UI em `main()` | `test_main_exits_2_when_ui_namespace_is_inconsistent` (grupo d) | `16 passed, 1 failed` — só o teste de wiring cai (`assert 1 == 2`); os 3 testes de `parse_cli` seguem verdes | sim |
| M2 | remove chamada de `_validate_args_consistency` em `parse_cli()` | `test_output_dir_without_batch_exits_with_usage_error` | `16 passed, 1 failed` — só esse teste cai (`assert False`, `SystemExit` não levantado); o teste de wiring (d) segue verde | sim |

M1 e M2 são mortos por testes distintos (grupo d vs. teste de CLI), confirmando que os dois call sites são cobertos separadamente — não há sobreposição de cobertura entre os dois pontos de validação.

## Ciclo AU

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| AU1 | done | MANUAL_INSTALACAO.txt | Acrescentadas 2 linhas ao bloco "Isso vai instalar:" (após colour-science, antes de opencv-python): `  ✓ pydantic (validação de configuração)` e `  ✓ scipy (filtros de análise de imagem)`; `matplotlib` não adicionado; APÊNDICE A intocado; `git diff --stat` = `1 file changed, 2 insertions(+)`; commit 1f0134c |

## Ciclo AV

| ID | status | arquivo tocado | resultado |
|----|--------|-----------------|-----------|
| AV1 | done | .github/workflows/ci.yml | job `pester` revertido para o estado byte-idêntico do `main`; job `pester-winps51` adicionado (windows-latest, 3 steps com `shell: powershell` fixo + bootstrap TLS1.2/NuGet); `git diff main` mostra só o novo job (31 insertions, 12 deletions no arquivo); nenhuma chave `shell:` com `${{`; `yaml.safe_load` OK; commit 2730600, pushed a claude/ciclo-av-uf2-winps51 |
