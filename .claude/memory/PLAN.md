<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BG: LUT do Cineon fora do repo, texto do loudnorm, certificado e preview do MCTF/AI

Data: 2026-09-28 | Ciclo: BG | Origem: pedido do usuário — fechar `BFF1` (S3), `BFF2` e `BFF3` (S4), abertos no
Ciclo BF. Desenho aprovado pelo usuário antes deste plano. Ciclo anterior: BF (fechado, PR #68).
Evidência: `.claude/memory/FINDINGS.md` § "BFF1", "BFF2", "BFF3".

## Diagnóstico (medido no código em `main` c131e3e)

| achado | onde |
|--------|------|
| `BFF1` default da CLI é nome nu, nunca `None` | `Reels_Encoder_v2_FINAL.py` `--cineon-lut` `default="FilmLook_Portra400_SkinPriority_D65.cube"` (~`:4291`) → `cineon_lut_path=args.cineon_lut` (~`:4080`) → `if cineon_lut_path is None: _find_data_file(...)` (~`:3350`) nunca dispara → `os.path.exists` relativo ao CWD falha fora da raiz |
| `BFF1` wizard idem | `ui/config.py:48` `DEFAULT_CINEON_LUT` (nome nu) em `cineon_lut` (`:80`), repassado ao motor pelo `Namespace` |
| `BFF2` README | `README.md:325` diz "normalização linear (…) sem compressão dinâmica"; o FFmpeg cai em Dynamic quando o linear estouraria o TP alvo (medido em 2 de 3 clipes reais do usuário; I entregue −14,0 e −14,1 LUFS) |
| `BFF3` certificado | `_report_settings` (~`:3986`) grava `enhance_ai` e `mctf` crus do `args`; o motor descarta `enhance_ai` sem `enhance` (~`:4010`) e `mctf` sem `enhance_ai` (`_mctf_ignored_reason`, ~`:3994`) |
| `BFF3` preview | `ui/components.py:443-450`: sem chip de MCTF; chip "AI" olha só `enhance_ai` |

## Decisões (Orquestrador, aprovadas pelo usuário)

1. **`BFF1`: resolver no ponto de uso, não no parser.** Default da CLI, help, README e `ui/config.py` ficam
   como estão. Uma função pura mínima nova `_resolve_cineon_lut(path: Optional[str]) -> str` ao lado de
   `_find_data_file`, com a regra:
   - `None` → `_find_data_file("FilmLook_Portra400_SkinPriority_D65.cube")`;
   - `os.path.exists(path)` → `path` (explícito ou relativo existente, respeitado como hoje);
   - nome nu (`os.path.basename(path) == path`) inexistente no CWD → `_find_data_file(path)`;
   - qualquer outro (caminho com diretório que não existe) → `path` inalterado (o erro atual continua).
   O bloco `if cineon_lut_path is None:` em `run_ffmpeg_with_cineon` vira `cineon_lut_path =
   _resolve_cineon_lut(cineon_lut_path)`. A checagem `os.path.exists` + mensagem de erro seguinte não muda.
   Função pura pelo mesmo precedente do `_mctf_ignored_reason` (BF3): `run_ffmpeg_with_cineon` roda FFmpeg.
2. **`BFF2`: só texto.** Nenhuma mudança de código de áudio.
3. **`BFF3` certificado: gravar o efetivo, com as mesmas regras do motor**, dentro de `_report_settings`
   (sem mexer em `args` nem no fluxo de `_encode_single_file`): se `enhance != "on"`, `enhance_ai` sai `"off"`;
   se o `enhance_ai` efetivo não for `"on"`, `mctf` sai `"off"`. Só normaliza chaves já presentes (a regra
   "omite `None`" continua). Demais chaves intocadas.
4. **`BFF3` preview:** chip "AI" = `enhance == "on" and enhance_ai == "on"`; chip novo "MCTF" logo depois do
   "AI" = `enhance == "on" and enhance_ai == "on" and mctf == "on"`. Rótulo simples `"MCTF"` (sem glifo novo).
   Não é mudança de menu/preset/seção → sem `ui-flow-reviewer`.
5. Nenhuma mudança de imagem, bitrate ou áudio → sem encode de validação nem VMAF.

## Tarefas

| ID | agente alvo | arquivo(s) | o quê | aceite |
|----|-------------|------------|-------|--------|
| BG1 | executor | `Reels_Encoder_v2_FINAL.py`, teste novo `enhance/test_cineon_lut_resolution.py` | Decisão 1 | TDD: testes vermelhos antes (ImportError/AttributeError conta), verdes depois; casos: `None`; nome nu com `monkeypatch.chdir(tmp_path)` → devolve o caminho ao lado do módulo e ele existe; caminho absoluto existente em `tmp_path` → devolvido igual; nome nu que só existe no CWD (arquivo `.cube` criado em `tmp_path`, com `chdir`) → devolve o do CWD **somente se** não houver homônimo ao lado do módulo (usar nome inventado, ex. `bg1_only_cwd.cube`); caminho com diretório inexistente → inalterado. Prova real: CLI com `--cineon-pipeline on` rodada de uma pasta do scratchpad passa do carregamento da LUT (ver a linha "✓ LUT Portra 400 carregada"; pode interromper depois disso ou usar fonte curta da BG1 em `tmp`/scratchpad) |
| BG2 | executor | `README.md` | Decisão 2: reescrever o bullet do Pass 2 (`:325`). Conteúdo: reaplica os valores medidos com `linear=true` e o `offset` do Pass 1; quando o ganho linear levaria o true peak acima de −1,5 dBTP (pico alto para o ganho), o próprio FFmpeg passa para o modo dinâmico, que pode limitar picos; o integrado continua em −14 LUFS (±1). Um bullet, tom e formatação dos vizinhos | diff só nesse bullet |
| BG3 | executor | `Reels_Encoder_v2_FINAL.py`, teste novo `enhance/test_report_settings.py` | Decisão 3 | TDD vermelho antes / verde depois; casos com `argparse.Namespace`: (a) `enhance=off, enhance_ai=on, mctf=on` → `enhance_ai=off, mctf=off`; (b) `enhance=on, enhance_ai=off, mctf=on` → `mctf=off`; (c) tudo `on` → inalterado; (d) Namespace sem `enhance_ai`/`mctf` → chaves ausentes (não inventar) |
| BG4 | executor | `ui/components.py`, `ui/test_components.py` | Decisão 4 | TDD vermelho antes / verde depois; reusar o helper de render dos testes existentes de `settings_preview`; casos: AI com `enhance=off, enhance_ai=on` renderiza como warn (não ok); MCTF presente e ok só com os três `on`; demais testes de preview seguem verdes |
| BG5 | Orquestrador | `.claude/memory/*` | suíte completa + ruff, FINDINGS/STATE fechados, push e PR | — |

Ordem: BG1 → BG2 → BG3 → BG4, um commit por ID.

## Critérios de aceite do ciclo

1. CI verde no PR (`lint`, `tests` 4 pernas, `pester` 2, `pester-winps51`).
2. Cineon acha a LUT padrão rodando de fora da raiz do repo; caminho explícito continua respeitado.
3. Certificado não lista `enhance_ai`/`mctf` "on" que o motor descartou; preview mostra o efetivo.
4. Suíte canônica sem regressão; `ruff check .` limpo.

## Notas de execução

- **Branch:** `claude/ciclo-bg-portabilidade-cert` (já em checkout, a partir de `main` c131e3e). Não trocar de
  branch. Não fazer push — o Orquestrador faz na BG5.
- **Ambiente:** Windows local. Python de teste (venv do ciclo anterior, ainda existe):
  `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`.
  Não usar o Python de sistema nem o `venv/` do projeto. FFmpeg: `./bin/ffmpeg.exe`.
  Suíte canônica: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Baseline no
  HEAD: **585 passed** com FFmpeg (medir antes de começar e registrar).
- **Scratchpad desta sessão** (fixtures, logs, CWD da prova real da BG1):
  `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\81225258-aaf4-42c2-8e2b-ffb1155661c8\scratchpad`.
- **Nada na raiz do repo:** testes usam `tmp_path`; conferir `git status` no fim.
- **Commits:** um por ID, mensagem convencional em português, terminando com os trailers
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01HUbtQDa7PUKaDujFnWXp7B`.
- **Nunca `git add -A` nem `git add .`** — caminho explícito. Não commitar `__pycache__`, `enhance_maps/`,
  `videos/`, `testResults.xml` nem os `docs/*.md` não rastreados. Sem `[skip ci]`.
- STATE.md (grande — não ler inteiro): anexar ao fim uma seção `## Ciclo BG` com tabela `ID | done ou blocked |
  arquivo tocado | resultado em 1 linha`; saída vermelha pré-fix de cada ID em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
