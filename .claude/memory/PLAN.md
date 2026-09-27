<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BD: cor, fps e 2-pass do Cineon + superfície de opções e docs

Data: 2026-09-27 | Ciclo: BD | Origem: pedido do usuário após o resumo do encoder — corrigir os
itens 1, 3, 5, 6 e 7 "tomando as decisões corretas". Itens 2 (teto do 2-pass, `BDF9`) e 4 (skill ×
código, `BDF10`) ficam para o próximo ciclo por decisão do usuário. Ciclo anterior: BC (fechado).
Evidência de cada achado: `.claude/memory/FINDINGS.md` § "Achados — 2026-09-27".

## Diagnóstico (medido, não presumido)

| achado | item do usuário | medido |
|--------|-----------------|--------|
| `BDF1` saída RGB→YUV do Cineon em BT.601, marcada BT.709 | 1 | vermelho Y=81 (601) em vez de 63 (709) — FFmpeg 4.2.2, 6.0.1, 7.0.2 |
| `BDF2` entrada YUV→RGB do Cineon depende do PyAV | 1 | PyAV 12–16 decodificam BT.709 com matriz 601; 17–18 corretos |
| `BDF14` fonte HDR entra no Cineon sem tonemap | 1 | nenhum guard |
| `BDF3` Cineon não converte fps | — (novo) | 60 fps + `--fps 30`: vídeo 4,0 s × áudio 2,0 s; 24 fps: 1,6 s × 2,0 s |
| `BDF4` crash no fim do Cineon em Linux/macOS, Python 3.11/3.12 | — (novo) | `communicate()` após `stdin.close()` → `ValueError: flush of closed file` |
| `BDF5` Pass 1 do Cineon mede pixels diferentes do Pass 2 | 7 | Pass 1 = vídeo nativo via CLI |
| `BDF6` `--tonemap bt2390` sem implementação | 3 | cai em mobius com aviso |
| `BDF7` defaults `--enhance-ai on` + `--mctf on` | 5 | MockCNN não treinado + vídeos de máscara do clipe inteiro no CWD |
| `BDF8` documentação desatualizada | 6 | LUT citada v6.6/v6.7/v6.7B (em uso v6.8); dither descrito como não é |

Controle negativo: os caminhos FFmpeg SDR e HDR já produzem BT.709 correto (o `zscale m=bt709`
negocia `yuv420p` direto). Não mexer neles; só guardar com teste (BD1).

## Decisões (Orquestrador, com a autorização do usuário para decidir)

1. **Item 1 corrige as duas pontas do Cineon.** Corrigir só a saída pioraria quem está em PyAV
   12–16: hoje 601→601 quase se cancela; saída 709 com entrada 601 deixaria o erro visível. Saída com
   `scale` explícito; entrada com `reformat` explícito e piso `av>=17.0.0` (13–16 ignoram os args
   explícitos quando `src_range == dst_range`, medido).
2. **Cineon recusa fonte HDR** com erro acionável (usar o pipeline FFmpeg, que faz tonemap). Não
   criar tonemap no Cineon.
3. **`BDF3` e `BDF4` entram neste ciclo** embora não estivessem na lista: estão no loop que o item 7
   reescreve, são defeitos de correção sem componente criativo, e o 2-pass exige contagem de frames
   determinística entre os passes.
4. **Item 7: o pipeline Cineon é renderizado nos dois passes** (padrão de mercado — HandBrake e
   Resolve rodam os filtros em ambos os passes). Custo ~2× só em `--mode 2pass` (opt-in; o padrão
   continua CRF). Dither com semente fixa por passe → Pass 1 e Pass 2 recebem bytes idênticos.
5. **Item 3: `bt2390` sai de toda a superfície.** O builder passa a levantar `ValueError` em
   algoritmo desconhecido — sem fallback silencioso.
6. **Item 5: `--enhance-ai off` e `--mctf off` por padrão** (CLI e wizard). `--enhance on` continua
   (heurístico, determinístico, 5 frames). Opt-in explícito segue funcionando igual.
7. **Item 6: a documentação passa a descrever o comportamento real, sem mudar comportamento.**
   Versão da LUT de fonte única; dither descrito como é. `VALIDATION.md` é regenerado pelo
   `validador` na BD10.
8. **Fora do ciclo** (FINDINGS): `BDF9`, `BDF10`, e os que mudam a imagem de todo encode e exigem A/B
   com o usuário — `BDF11` (viés do dither), `BDF12` (unidade do `peak` do tonemap), `BDF13` (máscara
   estática do enhance-ai).

Conhecimento de encoder: `skill: instagram-reels-encoder` § "Regras de Ouro" (BT.709, `yuv420p`),
`references/cineon-pipeline.md` (nós, quantização RPDF), `references/color-pipeline.md`. Não
transcrever — carregar a skill.

## Desenho

### BD1 — saída RGB→YUV do Cineon (`BDF1`)

- Constante de módulo em `Reels_Encoder_v2_FINAL.py`:
  `_CINEON_RGB_TO_YUV709_VF = "scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_inp,format=yuv420p"`
  (string medida: carta sai 63/102/240 no vermelho em 6.0.1 e 7.0.2).
- Usada como `-vf` no comando do pipe `rgb24` (depois dos `-map`, antes de `-c:v`).
- Testes novos em `enhance/test_color_matrix.py`. Pulam (`pytest.skip`) se o FFmpeg resolvido por
  `ui.binaries` não executar (`<ffmpeg> -version` falha ou binário inexistente); os de cadeia pulam
  também se `zscale` não aparecer em `ffmpeg -filters`:
  - `test_cineon_output_vf_is_bt709`: carta RGB de 5 patches (vermelho, verde, azul, pele
    0.8/0.6/0.5, cinza 50%) via `-f rawvideo -pix_fmt rgb24 -i - -vf <constante> -f rawvideo
    -pix_fmt yuv420p -` → Y/Cb/Cr do centro de cada patch a ±1 do BT.709 TV teórico.
  - `test_sdr_chain_is_bt709`: `build_sdr_float_pipeline(None, None, lut_enabled=False,
    dither_enabled=False)` sobre carta `yuv420p` BT.709 marcada → identidade ±1.
  - `test_hdr_chain_final_conversion_is_zscale`: cadeia de `build_scene_referred_hdr_pipeline(...)`
    sobre fonte PQ/BT.2020 sintética == mesma cadeia com `format=yuv420p` inserido logo após
    `zscale=t=bt709:m=bt709:r=tv:p=bt709` (bytes idênticos). Guarda a negociação.

### BD2 — entrada YUV→RGB do Cineon (`BDF2`) + recusa de HDR (`BDF14`)

- `pyproject.toml`: `"av>=17.0.0"`.
- Helper de módulo `_pyav_frame_to_rgb24(frame) -> np.ndarray`:
  `frame.reformat(format="rgb24", src_colorspace=<cs>, src_color_range=<rng>, dst_color_range="JPEG").to_ndarray()`.
  `frame.colorspace` (AVColorSpace): 1→`"ITU709"`; 5 e 6→`"ITU601"`; 4→`"FCC"`;
  7→`"SMPTE240M"`; qualquer outro (inclui 2 = não especificado)→`"ITU709"` (mesma política do
  caminho FFmpeg para fonte sem tag). `frame.color_range`: 2→`"JPEG"`; outro→`"MPEG"`.
- O loop do Cineon usa o helper no lugar de `frame.to_ndarray(format="rgb24")`.
- Em `run_ffmpeg_with_cineon`, logo após `probe_video` (o guard `_validate_cineon_constants`
  continua a primeira instrução — teste `test_cineon_constants_guard.py` guarda isso):
  `if _probe.is_hdr: raise RuntimeError(...)` com mensagem acionável (nomeia o tipo HDR e manda usar
  `--cineon-pipeline off`, que faz tonemap). Antes de abrir container, LUT ou FFmpeg.
- Testes em `enhance/test_cineon_color_io.py` — sem FFmpeg; frames sintéticos via
  `av.VideoFrame.from_ndarray(..., format="yuv420p")` com `colorspace`/`color_range` atribuídos
  (atributos graváveis em PyAV 17+, medido):
  - vermelho BT.709 TV (63,102,240) → RGB (255,0,0) ±2; o mesmo vermelho em full-range → idem;
    frame sem tag (colorspace=2) tratado como 709; pele e cinza ±2.
  - HDR recusado antes de qualquer I/O de vídeo (monkeypatch de `probe_video` com `is_hdr=True`;
    `av.open` e `subprocess.Popen` monkeypatched para falhar se chamados).

### BD3 — conversão CFR no Cineon (`BDF3`)

- Gerador de módulo `_cfr_resample(frames, out_fps)` → yields `(frame, is_repeat)`, semântica do
  filtro `fps` do FFmpeg com `round=near`:
  - slot = floor((t − t0)·out_fps + ½), aritmética exata com `Fraction(frame.pts) * frame.time_base`;
    empate exato arredonda para cima; dentro do mesmo slot vence o último frame; slot vazio repete
    o anterior. `pts` ausente → tempo anterior + 1/fps de entrada.
  - Fim: o último frame cobre até `t_last + dur_last` (`frame.duration × time_base` quando > 0,
    senão 1/fps de entrada); total de slots = floor((t_end − t0)·out_fps + ½).
  - Streaming: guarda só o frame pendente.
- No loop: só frames emitidos são convertidos e processados; `is_repeat=True` reescreve os bytes do
  último frame processado (não reprocessa). HUD: total = `round(duration * output_fps)`.
- Testes puros em `enhance/test_cineon_cfr.py` com frames falsos (`pts`, `time_base`, `duration`):
  60→30 escolhe os frames pares e dá 60 slots em 2 s; 24→30 dá 60 slots com 12 repetições
  distribuídas; 30→30 identidade; 30000/1001→30 ≈ 1 repetição a cada 1000; jitter VFR de ±2 ms sem
  drop/dup espúrio; total = duração × fps.

### BD4 — 2-pass do Cineon nos mesmos pixels (`BDF5`) + fim de processo sem `communicate()` (`BDF4`)

- A análise de enhance sobe para ANTES de qualquer passe (o Pass 1 renderiza com enhance).
- Sai o Pass 1 atual via CLI nativo (e o `-vf` de escala dele).
- Um construtor de comando do pipe, parametrizado por passe:
  - CRF: como hoje (com BD1).
  - Pass 1: `-b:v <base>`, `-x264-params` base de `_x264_params_string`, `-pass 1 -passlogfile
    <LOG>`, sem input nem mapa de áudio, `-an -f null DEVNULL_FF`.
  - Pass 2: `-b:v <adaptado>`, params de `_adaptive_2pass_x264_params`, `-pass 2 -passlogfile
    <LOG>`, áudio + metadados + output.
  - Nos três: mesmo `-f rawvideo -pix_fmt rgb24 -s -r`, mesmo `_CINEON_RGB_TO_YUV709_VF`, mesmo
    keyint (os dois builders de x264 já garantem).
- Uma função de passe (aninhada ou de módulo, a critério do executor) que: abre o container;
  `Popen(stdin=PIPE, stdout=DEVNULL, stderr=PIPE)`; `_register_ffmpeg`; HUD; thread de stderr que
  guarda as últimas 50 linhas (`collections.deque`); loop CFR (BD3) com `_pyav_frame_to_rgb24`
  (BD2); fecha o stdin; `wait(timeout=60)` (kill no timeout); `join` da thread; returncode ≠ 0 →
  `CalledProcessError` com as linhas guardadas. **Nunca chamar `communicate()` depois de fechar o
  stdin.** KeyboardInterrupt e erro de processamento: mesma semântica de hoje (terminate + re-raise
  / `RuntimeError`).
- Dither: `np.random.default_rng(_CINEON_DITHER_SEED)` (constante de módulo) criado no início de cada
  passe.
- Metadados do 2-pass Cineon com os overrides do Pass 2 (`vbv_maxrate_override`,
  `vbv_bufsize_override`), como o caminho FFmpeg já faz.
- Logs do 2-pass (`-0.log`, `-0.log.mbtree`) removidos em `finally` — sucesso, erro e interrupção.
- Remux do `colr` e validação ffprobe: só depois do passe final, sem mudança.
- Testes e2e em `enhance/test_cineon_e2e.py` (pulam sem ffmpeg **e** ffprobe executáveis). Fonte
  sintética em `tmp_path`: lavfi `testsrc2` 90×160 + `sine` 48 kHz, 1 s.
  `run_ffmpeg_with_cineon(..., target_fps="30", scale_mode="off", loudnorm_enabled=False,
  enhance_enabled=False, show_hardware=False)`:
  - fonte 60 fps, CRF: `nb_frames == 30`, duração do vídeo = duração do áudio ±1 frame, sem exceção
    (em Python 3.11/3.12 POSIX isso reprova antes do fix — `BDF4`).
  - fonte 60 fps, 2pass: idem + nenhum log do 2-pass no disco ao final.
  - fonte 24 fps, CRF: `nb_frames == 30`.
  - todo comando FFmpeg que recebe o pipe contém `-vf` + `_CINEON_RGB_TO_YUV709_VF` (capturar via
    wrapper de `subprocess.Popen` que registra os args e delega ao original).

### BD5 — o CI passa a rodar os testes que dependem de FFmpeg

- `.github/workflows/ci.yml`, job `tests`: step `Install FFmpeg (Linux)` com
  `if: runner.os == 'Linux'`, rodando `sudo apt-get update && sudo apt-get install -y
  --no-install-recommends ffmpeg` e depois `ffmpeg -version`, antes de `Run tests`. Windows segue
  sem FFmpeg (esses testes pulam lá).

### BD6 — item 3 (`BDF6`)

- Remover `bt2390` de `TONEMAP_ALGORITHMS`, do `choices` do `--tonemap`, de `ui/config.py` e da lista
  do `ask_select` em `ui/launcher.py`.
- `build_scene_referred_hdr_pipeline`: algoritmo desconhecido → `ValueError` (remover o fallback
  para mobius).
- Testes: `bt2390` rejeitado pela CLI (`SystemExit`) e pelo `EncodeConfig`; `set(TONEMAP_ALGORITHMS)
  == choices da CLI == choices do `EncodeConfig` == algoritmos do builder`; builder levanta em
  algoritmo desconhecido.

### BD7 — item 5 (`BDF7`)

- `--enhance-ai` e `--mctf` com default `"off"` (argparse e textos de help); `EncodeConfig.enhance_ai`
  e `EncodeConfig.mctf` = `"off"`.
- `ui/test_config.py:39-40` atualizado. Teste novo: `build_parser().parse_args(["x.mp4"])` →
  `enhance == "on"`, `enhance_ai == "off"`, `mctf == "off"`.

### BD8 — item 6 (`BDF8`)

- Fonte única da versão da LUT: constante de módulo derivada de `_HOLLYWOOD_LUT_FILENAME` pela regex
  que `_build_metadata_args` já usa; o `pipeline_tag` passa a usar a constante (comportamento
  idêntico — os testes dos Ciclos AG/AH guardam). Toda string de console, help, epílogo e docstring
  que cita versão da LUT usa a constante ou texto sem versão.
- Dither descrito como é, sem mudar comportamento: help do `--dither`, prints de console
  (`Reels_Encoder_v2_FINAL.py:2217, 2341, 4073-4080`), label do launcher (`ui/launcher.py:224`),
  docstring e comentário de seção de `_build_dither` (`enhance/ffmpeg_filters.py:75, 133-158`) e a
  frase "mesma técnica" em `cineon_pipeline.py::quantize_uint8_dithered`. Texto: ruído uniforme
  temporal no luma (±2 códigos), aplicado depois da conversão para 8-bit; `auto` equivale a `on`.
  A menção ao upgrade futuro (FASE 30B) pode ficar, sem a palavra "blue-noise" descrevendo o atual.
- Docstrings obsoletas: cabeçalho do módulo (linha 40), `run_ffmpeg` ("Confia 100% na LUT v6.6"),
  `build_sdr_float_pipeline` (estágio "CAS 0.30" que não existe), `build_video_filter_auto` e
  `build_scene_referred_hdr_pipeline` (v6.6).
- README: linhas 48, 290, 294, 302, 373; tabela de defaults (`--enhance-ai`, `--mctf` → `off`;
  `--tonemap` sem `bt2390`); linha do PyAV (`17.0.0+`); nota de que `--mode 2pass` no Cineon
  renderiza o pipeline duas vezes.
- Teste de guarda novo `ui/test_docs_consistency.py` (ler com `encoding="utf-8"`): README e
  `build_parser().format_help()` sem `v6.6`, `v6.7`, `bt2390` nem "Blue-noise"; README contém a
  versão derivada de `_HOLLYWOOD_LUT_FILENAME`.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| BD1 | § BD1 | executor-pesado | `Reels_Encoder_v2_FINAL.py`, `enhance/test_color_matrix.py` | com `PATH=$SP/ff70:$PATH` e com `$SP/ff60`: 3 passed; com `env PATH=/usr/bin:/bin`: 3 skipped; trocar `bt709` por `bt601` na constante (local, sem commit) faz `test_cineon_output_vf_is_bt709` reprovar |
| BD2 | § BD2 | executor-pesado | `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `enhance/test_cineon_color_io.py` | passa com o PyAV do venv (18.1) e com `PYTHONPATH=$SP/av_17.0.0`; com `PYTHONPATH=$SP/av_16.0.0` o teste full-range reprova (prova do piso — registrar no STATE, não commitar nada disso) |
| BD3 | § BD3 | executor-pesado | `Reels_Encoder_v2_FINAL.py`, `enhance/test_cineon_cfr.py` | testes passam; o loop do Cineon consome `_cfr_resample` |
| BD4 | § BD4 | executor-pesado | `Reels_Encoder_v2_FINAL.py`, `enhance/test_cineon_e2e.py` | antes da mudança o e2e reprova (registrar a saída no STATE); depois passa com `$SP/ff70` e `$SP/ff60`; suíte completa (`test_render_queue.py enhance/ ui/ tools/`) sem falha com e sem FFmpeg no PATH; `ruff check .` limpo (ruff 0.14.10) |
| BD5 | § BD5 | executor-pesado | `.github/workflows/ci.yml` | `actionlint` sem erro (via `pip install actionlint-py`; se indisponível, `yaml.safe_load` + revisão manual e registrar isso); prova real = run do CI no PR |
| BD6 | § BD6 | executor | `Reels_Encoder_v2_FINAL.py`, `ui/config.py`, `ui/launcher.py`, `enhance/test_hdr_pipeline.py`, `ui/test_config.py` | `grep -rn bt2390 --include=*.py .` fora de `.claude/memory` e `docs/superpowers` → 0; testes novos passam |
| BD7 | § BD7 | executor | `Reels_Encoder_v2_FINAL.py`, `ui/config.py`, `ui/test_config.py` | testes passam; `--help` mostra os dois defaults como off |
| BD8 | § BD8 | executor | `Reels_Encoder_v2_FINAL.py`, `enhance/ffmpeg_filters.py`, `cineon_pipeline.py`, `ui/launcher.py`, `README.md`, `ui/test_docs_consistency.py` | `grep -nE "v6\.6|v6\.7|bt2390|[Bb]lue-noise" Reels_Encoder_v2_FINAL.py README.md ui/launcher.py ui/config.py enhance/ffmpeg_filters.py` → 0; `npx --yes markdownlint-cli2@0.23.1 README.md` → 0 issues; suíte completa verde |
| BD9 | auditoria do wizard após BD6–BD8 | ui-flow-reviewer | `ui/launcher.py` | veredito sem achado bloqueante |
| BD10 | encodes reais + validação | Orquestrador (encodes) + validador | `.claude/memory/VALIDATION.md` | ver § "Validação" |
| BD11 | fechamento: STATE/FINDINGS, push, PR | Orquestrador | `.claude/memory/*` | — |

Ordem: BD1→BD5 (`executor-pesado`, um commit por ID) → BD6→BD8 (`executor`, um commit por ID) →
BD9 → BD10 → BD11. Nada em paralelo: BD1–BD8 editam `Reels_Encoder_v2_FINAL.py`.

## Validação (BD10)

Fonte sintética 1080×1920, 60 fps, 3 s, `testsrc2` + `sine`, tags BT.709. Dois encodes pela CLI, com
FFmpeg 7.0.2 no PATH e `--ebu-meter off`: (a) padrão (FFmpeg, CRF, defaults novos); (b)
`--cineon-pipeline on --mode 2pass`. O `validador` roda `validate_encode.sh` nos dois e sobrescreve
`VALIDATION.md` (fecha a parte de `BDF8` sobre o VALIDATION.md desatualizado). VMAF não se aplica
(grade deliberado sobre fonte sintética).

## Critérios de aceite do ciclo

1. CI verde nos jobs `lint`, `tests` (4 pernas), `pester` (2) e `pester-winps51` no PR.
2. Cineon: carta sai BT.709 na entrada e na saída; 60→30 e 24→30 com duração de vídeo = áudio;
   2-pass completa em Linux com Python 3.11/3.12; logs do 2-pass nunca sobram.
3. Caminhos FFmpeg SDR/HDR: bytes idênticos aos de antes (só ganham teste de guarda).
4. `bt2390` não existe mais em código de produto; `--enhance-ai`/`--mctf` opt-in.
5. Nenhuma mudança de imagem nos caminhos FFmpeg (dither, tonemap e enhance intocados — `BDF11`–`13`
   ficam para A/B).

## Notas de execução

- **Branch:** `claude/peaceful-noether-h2y27d` (já em checkout, a partir de `main` `07d14d3`). Não
  trocar de branch. Não fazer push — o Orquestrador faz na BD11.
- **Ambiente** (`SP=/tmp/claude-0/-home-user-encoder-ai-instagram/4aeaaaef-0120-5a84-a847-5e0691be4410/scratchpad`):
  - venv Python 3.11 com o projeto instalado: `$SP/venv/bin/python` (`pip install -e ".[opencv,dev]"`
    já feito; instalar `ruff==0.14.10` nele se precisar).
  - FFmpeg + ffprobe estáticos: `$SP/ff70/` (7.0.2) e `$SP/ff60/` (6.0.1). O container não tem FFmpeg
    no PATH por padrão; `ui.binaries` resolve `./bin` → PATH.
  - PyAV alternativos para `PYTHONPATH`: `$SP/av_13.0.0`, `$SP/av_16.0.0`, `$SP/av_17.0.0`.
  - Suíte canônica: `$SP/venv/bin/python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`.
- **Commits:** um por ID, mensagem convencional em português, terminando com:

  ```text
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011d7qoEQho76K2EPCw3rDhv
  ```

- **Nunca `git add -A` nem `git add .`** — adicionar por caminho explícito. Não commitar
  `*.egg-info`, `__pycache__`, `enhance_maps/` nem nada de `$SP`.
- Sem `[skip ci]` em nenhum commit deste ciclo (armadilha do Ciclo BB).
- STATE.md: anexar `## Ciclo BD` ao fim, uma linha por ID; saída de comando relevante (a reprovação
  pré-fix do e2e, a prova do piso do PyAV) em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
