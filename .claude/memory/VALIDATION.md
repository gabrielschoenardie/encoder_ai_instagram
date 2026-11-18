# Validação de Encodes — Ciclo BF (Audio Async, MCTF, Cineon -async 1)

**Data:** 2026-09-28 | **Validador:** agente `validador` | **FFmpeg:** n6.1.3-20250831 estático | **Fonte principal:** `fixture_mono.mp4` (1080×1920, 60fps, 3s, mono senoide 1kHz, 48kHz, AAC)

---

## Tarefas BF4

Tarefa de medição: validar 3 encodes (a, c, d) conforme planejado em PLAN.md § "Validação (BF4)". Contexto: BF1 adicionou `-async 1` ao comando Cineon para eliminar cauda de áudio ≈0,09s em Dynamic mode.

**Configurações de ambiente:**
- Python venv: `$SP/venv-be`
- FFmpeg: `$REPO/bin/ffmpeg.exe` (precedência sobre PATH)
- Diretório de trabalho: `$W = $SP/bf4`
- Correção de 2ª rodada: LUT com caminho ABSOLUTO, cwd em `$W` (não em subdiretório)

---

## Encode (a): FFmpeg CRF Defaults

**Comando:**
```bash
cd $W/in_a && "$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$W/in_a/fixture_mono.mp4" --ebu-meter off
```

**Tempo de execução:** 17.596 s

**Arquivo de saída:** `fixture_mono_Hollywood_CRF18.mp4`

**Timing (medido via ffprobe packets, último frame/áudio):**
- Fim do vídeo: 3.066667 s (pts 3.033333 + duration 0.033333)
- Fim do áudio: 3.008 s (pts 2.986667 + duration 0.021333)

**Validação (validate_encode.sh):**

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 12819 kbps | ❌ |
| GOP (keyframe) | máx ~60 frames = 2s | máx 29 frames = 0.97s @ 30.00 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 188 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3 s | 3 s | ✓ |
| Faststart (moov) | moov antes de mdat | moov antes de mdat ✓ | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.0 LUFS | ✓ |
| True Peak | ≤ -1 dBTP | -13.2 dBTP | ✓ |

**Veredito (a):** CONTROLE OK — sem cauda de áudio (3.008 s conforme esperado); bitrate em 12819 kbps é limitação aceita do CRF com vbv_init 0.9 (Ciclo BE, mesmo resultado).

---

## Encode (c): Cineon CRF — fixture_mono (BF1: -async 1)

**Comando:**
```bash
cd $W && "$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$W/in_c/fixture_mono.mp4" --cineon-pipeline on --cineon-lut "$REPO/FilmLook_Portra400_SkinPriority_D65.cube" --ebu-meter off
```

**Tempo de execução:** 00:04:09 (249 s)

**Arquivo de saída:** `fixture_mono_Cineon_Film.mp4`

**Timing (medido via ffprobe packets):**
- Fim do vídeo: 3.0 s (pts 2.966667 + duration 0.033333)
- Fim do áudio: 3.008 s (pts 2.986667 + duration 0.021333)
- Duração total: 3.008 s

**Validação (validate_encode.sh):**

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 12888 kbps | ❌ |
| GOP (keyframe) | máx ~60 frames = 2s | máx 30 frames = 1.00s @ 30.00 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 188 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3 s | 3 s | ✓ |
| Faststart (moov) | moov antes de mdat | moov antes de mdat ✓ | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.0 LUFS | ✓ |
| True Peak | ≤ -1 dBTP | -13.2 dBTP | ✓ |

**Cauda de áudio:** 3.008 - 3.008 = **0 s** (sem cauda) ✓  
**Vs. esperado:** ≤ 3.008 + 0.05 = 3.058 s → **DENTRO DA TOLERÂNCIA**

**Veredito (c):** Cauda de áudio RESOLVIDA — o encode Cineon da mesma fixture antes da BF1 (BE4, `in_c`) terminava o áudio em 3,100 s; agora termina em 3,008 s (medido também pelo Orquestrador). Bitrate 12888 kbps é limitação aceita (mesma do Cineon no BE4).

---

## Encode (d): Cineon CRF — r3_4s.mov (recorte dinâmico, BF1: -async 1)

**Fonte de entrada:**
```bash
ffmpeg -y -ss 0 -t 4 -i "$SP/be4_diag3/r3.mov" -c copy "$W/in_d/r3_4s.mov"
```

**Confirmação de Dynamic Mode (da 1ª rodada):**
```
Análise de loudness:
  input_i: -17.92 LUFS
  input_tp: -1.24 dBTP
  normalization_type: dynamic  ✓
  Ganho esperado: -14 - (-17.92) = 3.92 dB
  TP_pós: -1.24 + 3.92 = 2.68 dBTP > -1.5 → dinâmico ✓
```

**Timing da fonte (r3_4s.mov):**
- Fim do vídeo: 4.016 s
- Fim do áudio: 4.001 s

**Comando:**
```bash
cd $W && "$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$W/in_d/r3_4s.mov" --cineon-pipeline on --cineon-lut "$REPO/FilmLook_Portra400_SkinPriority_D65.cube" --ebu-meter off
```

**Tempo de execução:** 00:05:09 (309 s)

**Arquivo de saída:** `r3_4s_Cineon_Film.mp4`

**Timing (medido via ffprobe packets):**
- Fim do vídeo: 3.966667 s (pts 3.933333 + duration 0.033333)
- Fim do áudio: 4.0 s (pts 3.989333 + duration 0.010667)
- Duração total: 4.0 s

**Validação (validate_encode.sh):**

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 12309 kbps | ❌ |
| GOP (keyframe) | máx ~60 frames = 2s | máx 30 frames = 1.00s @ 30.00 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 192 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 4 s | 4 s | ✓ |
| Faststart (moov) | moov antes de mdat | moov antes de mdat ✓ | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.1 LUFS | ✓ |
| True Peak | ≤ -1 dBTP | -1.5 dBTP | ✓ |

**Cauda de áudio:** 4.0 - 4.001 = **-0.001 s** (sem cauda; coincide com a fonte) ✓  
**Vs. esperado:** ≤ 4.001 + 0.05 = 4.051 s → **DENTRO DA TOLERÂNCIA**

**Informativo:** MD5 do stream de vídeo de (c):  
- BF4 (esta rodada): `2555f1b2ec848ace067d13259bfb5233`
- BE4 (referência): `f54139dd710ed4d516823bb066910092`  
→ Diferem. **Nota do Orquestrador (2026-09-28):** a BF1 não altera o vídeo. Num teste controlado (encode Cineon de 1 s, 90×160, mesmo processo Python) o md5 do stream de vídeo foi idêntico (`0bb5286cd37964048f3d25a723fd4e74`) em duas execuções COM a correção e em uma SEM ela (worktree com só a linha `-async 1` revertida): o encoder é determinístico nesse cenário e o áudio não afeta o stream de vídeo. A origem da diferença entre este encode e o do BE4 (bitrate 12888 × 12905 kbps) não foi isolada e não é da BF1. A explicação anterior deste relatório ("mudança de LUT e pipeline") não tinha base: não houve mudança de LUT nem de pipeline de vídeo entre o BE4 e o BF4.

**Veredito (d):** Sem cauda de áudio — o áudio da saída termina em 4,000 s e o da fonte em 4,001 s (medido também pelo Orquestrador). **O pré-fix deste recorte de 4 s NÃO foi medido**; o recorte de 10 s do mesmo vídeo mediu +0,086 s sem `-async 1` (diagnóstico do Orquestrador, rodada 3). Bitrate 12309 kbps é limitação aceita.

---

## Consolidação — Status dos Critérios de Aceite

| Encode | Tipo | Esperado | Medido | Cauda | Status |
|--------|------|----------|--------|-------|--------|
| **(a)** FFmpeg CRF | Fixture 3s | Fim áudio ≈ 3,008s | **3,008 s** ✓ | 0 s | ✓ Controle OK |
| **(c)** Cineon CRF | Fixture 3s | Sem cauda (≤ +0,05s) | **3,008 s** ✓ | 0 s | ✓ Resolvido |
| **(d)** Cineon CRF | r3_4s 4s real | Fim áudio ≤ 4,001 + 0,05 = 4,051s | **4,0 s** ✓ | 0 s | ✓ Resolvido |

---

## Veredito Final do Ciclo BF (2ª rodada)

**Status:** `ok` — BDF17 validado; o único ❌ (bitrate médio no CRF de clipes curtos) é limitação aceita do Ciclo BE.

**BDF17 (cauda de áudio no Cineon):** ✅ **RESOLVIDO**
- Fixture (c): 3,008 s; o encode do BE4 (mesmo pipeline, antes da BF1) terminava em 3,100 s → **cauda eliminada** (medido).
- Áudio real (d): 4,000 s com fonte em 4,001 s → **sem cauda** (medido; pré-fix deste recorte não medido, ver acima).

**Critérios de aceite (PLAN.md § "Critérios do ciclo"):**
1. ✅ Cineon com `loudnorm` em Dynamic: |áudio − vídeo| ≤ 1/30 s no e2e; cauda ≤ 0,05 s → **PASSOU**
2. ✅ Nenhuma mudança de imagem pela BF1 → **CONFIRMADO em teste controlado do Orquestrador** (md5 do vídeo idêntico com e sem a correção; ver nota no encode (c)). O md5 do (c) difere do encode do BE4 por causa não isolada, que não é da BF1.
3. ⚠️ Bitrate: ambos encodes > 12000 kbps → limitação aceita (Ciclo BE, Ciclo BF, vbv_init 0.9)

**Observações:**
- (c) e (d) rodados de `$W` com LUT em caminho absoluto (correção de 2ª rodada)
- Nenhum ❌ NOVO além do bitrate aceito
- Loudness e True Peak conformes
- (c) e (d) reprovam só no bitrate médio (12888 e 12309 kbps), limitação aceita (`FINDINGS.md` § "Decisão — 2026-09-27")

**Síntese para o Orquestrador:**
BF1 (`-async 1` no comando de saída do Cineon) está validada: a cauda de áudio foi eliminada na fixture (modo Dynamic medido: `measured_LRA` 0,00) e em áudio real. BF2 e BF3 (wizard e aviso do MCTF) foram validadas por testes e por uma execução real da CLI, não por estes encodes.

---

## Log de Execução

- **Timestamp início:** 2026-09-28T13:02 UTC
- **Timestamp fim:** 2026-09-28T13:25 UTC (após validações)
- **Duração total:** Encode (c) 249s + Encode (d) 309s + validações ~10min = ~25 min

**Comandos exatos rodados:**
1. Encode (c): `cd "$W" && "$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$W/in_c/fixture_mono.mp4" --cineon-pipeline on --cineon-lut "$REPO/FilmLook_Portra400_SkinPriority_D65.cube" --ebu-meter off` → ✓ OK
2. Encode (d): `cd "$W" && "$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$W/in_d/r3_4s.mov" --cineon-pipeline on --cineon-lut "$REPO/FilmLook_Portra400_SkinPriority_D65.cube" --ebu-meter off` → ✓ OK
3. Validação (c): `bash "$REPO/.claude/skills/instagram-reels-encoder/scripts/validate_encode.sh" "$W/in_c/fixture_mono_Cineon_Film.mp4"` → ✓ OK (1 ❌ aceita: bitrate)
4. Validação (d): `bash "$REPO/.claude/skills/instagram-reels-encoder/scripts/validate_encode.sh" "$W/in_d/r3_4s_Cineon_Film.mp4"` → ✓ OK (1 ❌ aceita: bitrate)

**FFmpeg utilizado:** `n6.1.3-20250831` (via `$REPO/bin/ffmpeg.exe`)

---

**Relatório preparado por:** Validador (haiku) — 2ª rodada | **Metodologia:** Sequencial: encode → validate_encode.sh → medir timing → compilar tabela | **Critério:** Cauda de áudio ≤ +0,05 s → ✅ PASSOU
---

# Validação manual — Ciclo P3A (canal Encoder → TUI, Task 9)

**Data:** 2026-10-01 | **Executor do teste:** usuário, Windows Terminal (PowerShell) | **Script:** `scratchpad\b4\b4_driver_probe.py` (fora do repo) sobre `ui.tui_driver.run_single` + `ConsoleCapture` + leitor `msvcrt` | **Fonte:** cópia isolada de `videos\copy_2B208774-…​.mov` (34 MB)

| T | ação | log | eventos-chave | exit | ffmpeg órfão | terminal |
|---|------|-----|---------------|------|--------------|----------|
| T1 | Ctrl+C (caiu em PROBING) | b4_005311 | Cancel requested → terminated → cleaned(False) | 130 | não | ok |
| T2 | tecla `c` em PROBING | b4_005851 | `C_REQUEST -> True`; abortou no Stage seguinte (ANALYZING·loudness), PASS 1 não iniciou | 130 | não | ok |
| T3 | MCTF on, `c` em mctf_mask, depois Ctrl+C | b4_010343 | `C_REQUEST -> False` (D-22); Ctrl+C → requested/terminated/cleaned; Info "MCTF falhou: [Errno 22]" (sinal atingiu os ffmpeg da máscara) | 130 | não | ok |
| T4 | crf até o fim (QC rápido demais para Ctrl+C manual) | b4_010656 | QC → DELIVERY READY → Qc → DONE → Done, certificado gerado | 0 | não | ok |
| T5 | Ctrl+C ×2 | b4_011033 | requested; Info "Loudnorm Pass 1 falhou" (sinal no ffmpeg de análise); abortou no Stage PASS 1 | 130 | não | ok |

**Veredito:** PASSA. Ctrl+C e `C` preservam o comportamento (exit 130, sem órfão, sem traceback, terminal utilizável); `C` recusado na máscara MCTF; caminho feliz completo (exit 0) pelo condutor. **Não cobertos manualmente:** Ctrl+C durante PASS 1 em andamento e durante QC — cobertos por `ui/test_tui_driver.py` (`test_ctrl_c_during_qc_*`, `test_ctrl_c_wait_keeps_ticking_*`). Observação: no Windows o Ctrl+C também chega aos processos de análise do mesmo console (ffprobe/loudnorm/MCTF); o encoder registra como aviso e o resultado continua 130.

---

# Validação manual — Ciclo P3B (casca da TUI, Task 8)

**Data:** 2026-10-05 | **Executor do teste:** usuário | **Terminal:** Windows Terminal portátil (`bin/WindowsTerminal/wt.exe`), `vt=True truecolor=True`, 120×40 | **Entrada:** `python -m ui.tui` | **Fonte:** cópia isolada em `C:\Users\Usuario\p3b_teste`

| T | cenário | resultado |
|---|---------|-----------|
| T1 | native 2-pass até o fim; VER QC / VER LOG / SAIR | exit 0; Pass 1 ✓ visível no Pass 2; selo; COMPLETED; linha "✓ entregue: …"; sem ffmpeg órfão |
| T2 | Cineon CRF até o fim | exit 0 |
| T3–T9 | D/L/ESC/filtros; `C`→ESC e `C`→CANCELAR; `░[C]` no mctf_mask; Ctrl+C no PASS 1; resize < 40 linhas; janela de 30 linhas → modo clássico; `quebrado.mov` → ERROR | "tudo funciona como deveria" (relato do usuário) |

**Achado de ambiente:** a janela avulsa do `powershell.exe` (conhost, `vt=False`, `legacy_windows=True`, largura reportada 119) é recusada pela guarda — comportamento correto; a mensagem deveria orientar a abrir no Windows Terminal (pendência P3BF2).

**Veredito:** PASSA.

# Validação manual — Ciclo P3C (telas de configuração, Task 11)

**Data:** 2026-10-05 | **Executor do teste:** usuário | **Terminal:** Windows Terminal portátil | **Entrada:** `python -m ui.tui` | **Fonte:** `C:\Users\Usuario\p3c_teste` | **Roteiro:** `C:\Users\Usuario\p3c_teste\ROTEIRO_P3C.md`

| T | cenário | resultado |
|---|---------|-----------|
| T1 | preset 1 cover/24/2pass até COMPLETED | exit 0 — **falha visual**: no PREVIEW o texto "preenche · crop" do PROGRAM quebra a moldura 9:16 (print `Desktop\T1.png`) |
| T2 | preset 2, exposição/saturação, erro "Máximo é 2.", ESC até sair | exit 0 |
| T3–T9 | abas do ADVANCED, condicionais, REVISAR, arrastar, NOT FOUND, Tools, preset 3 | OK (relato do usuário) |
| T10 | Ctrl+C na CONFIGURATION | exit 130 |
| T11 | ENTER segurado ~2 s no PREVIEW | **falha**: a repetição do ENTER passou pelo READY e iniciou o encode; `C` cancelou corretamente |

**Veredito:** REPROVA (2 itens) — correção em andamento no P3C.

**Reteste (2026-10-05, após `5e9c14a`, `b834ef3`, `8b343eb`):**

| T | resultado |
|---|-----------|
| T1 | moldura 9:16 com `cover` íntegra ("crop"); "funcionando perfeitamente" (usuário) |
| T11 | ENTER segurado ~3 s no PREVIEW: para no READY, nenhum encode. Medido com `C:\Users\Usuario\p3c_teste\diag_enter.py` (TUI real, encode falso): 1ª rodada ~50 ENTERs rejeitados, 2ª rodada 39 rejeitados, nenhum aceito no READY. Repetições chegam a cada 50–115 ms (`KeyboardDelay=1`, `KeyboardSpeed=31`). A 1ª falha relatada no reteste não se reproduziu. |

**Veredito final:** PASSA.

# Validação manual — Ciclo P3D (batch de pasta, Task 9)

**Data:** 2026-10-06 | **Executor do teste:** usuário | **Terminal:** Windows Terminal portátil | **Entrada:** `python -m ui.tui` | **Fonte:** `C:\Users\Usuario\p3d_teste\lote` (3 clipes de 4 s, 1 com saída existente, 1 quebrado) e `C:\Users\Usuario\p3d_teste\vazia` | **Roteiro:** `C:\Users\Usuario\p3d_teste\ROTEIRO_P3D.md`

| D | cenário | resultado |
|---|---------|-----------|
| D1–D7 | preset 3 fila completa; preset 5-Pasta com pasta de saída separada; pasta vazia bloqueando; `C` no meio da fila; Ctrl+C no meio da fila; volta ao arquivo único; arrastar a pasta | "tudo funciona como deveria" (relato do usuário) |

**Veredito:** PASSA.

---

## Ciclo P3E (TUI polish) — sem validação de encode

O P3E não altera nenhum encode, filtro, nem o pipeline de vídeo. Nenhum `validate_encode.sh` ou `measure_vmaf.sh` foi executado. A verificação do ciclo é a suíte do CI (988 passed, 4 skipped no último relato, ver `STATE.md`), ruff limpo e checagem manual do usuário no Windows Terminal e no conhost (setas, `à` em ABNT2, Ctrl+C com LOG aberto, `-Tui`).

---

## Ciclo P3H (tela limpa R-06/R-07/R-10) — sem validação de encode

O P3H não altera encode, filtro nem pipeline (motor intocado). Verificação automatizada em `STATE.md` § Ciclo P3H.

- R-06 — verificação manual no Windows (FFplay + MCTF + preflight enhance-ai) PENDENTE

| item | roteiro |
|------|---------|
| R-06 | rodar na TUI real (Windows Terminal) um encode com `ebu_meter on` (janelas FFplay abrem e nada do ffplay aparece na tela da TUI), um com `--enhance on --enhance-ai on --mctf on` (preflight e máscara MCTF sem texto/barra vazando sobre a TUI; mensagens aparecem no LOG) e conferir que a tela não fica em branco nem pisca. Depois, NOVO ENCODE (N) a partir de CANCELLED/COMPLETED e de REPORT, e saída pela HOME imprimindo uma linha por encode |

## P3H ui-flow (ui-flow-reviewer, 2026-11-16)

Veredito: FLOW OK com ressalvas, sem bloqueante. Rota, renderer e overlays da ação "new" estão corretos. `new_session` não deixa vazar nenhum campo de encode.
- UF1 (baixa-média, latente) `state.py:740-745`: `action_focus` não é reclampado quando `worker_stuck` encolhe `final_actions`. Com o foco em NOVO ENCODE, o ENTER lança `IndexError`, que vira WARNING, e a tecla é perdida. Hoje não é alcançável no fluxo single.
- UF2 (baixa) `app.py:182-200`: o laço interno de `_session` não trata "new" (cairia em start). Hoje não é alcançável.
- UF3 (baixa, teórica) `app.py:404-405`: se o usuário apertar N no REPORT antes de `run_batch` retornar, os eventos que chegarem depois do `QueueDone` são descartados.
- UF4 (info): o REPORT mostra NOVO ENCODE só como dica no rodapé, e o rodapé de COMPLETED/ERROR/CANCELLED não cita `[N]`.
- Lacunas de teste: UF1, N ignorado em QC/LOG, cancelamento do 2º encode.

### Adendo P3H-7 — resolução (2026-11-16)

- UF1 **resolvido** (`state.py`: ENTER indexa com `min(action_focus, len-1)`; Info de stuck reclampa o foco). Testes em `test_state.py`.
- UF4 **resolvido** (`screens.py`: rodapé de COMPLETED/ERROR/CANCELLED/REPORT cita `[N] Novo encode` só com NOVO ENCODE em `final_actions`). Teste em `test_screens.py`.
- Lacunas de teste fechadas: N ignorado em QC/LOG vindos de tela final; cancelamento no 2º encode da mesma App (`test_app.py`).
- UF2, UF3: latentes, não tratados (FINDINGS P3HF6/P3HF7).

## P3H manual Windows (usuário, 2026-11-16)

A1–A4 ✓ (preflight enhance-ai, MCTF, FFplay e teclas sem sujar a tela) · B1 ✓ · B3 ✓ · C1 ✓ · **B2 ✗**: no 2º encode, o C foi confirmado no modal e o encode não parou. Decisão do usuário: remover o cancelamento por C da TUI (adendo P3H-8). Interrupção só por Ctrl+C.

## P3H-8 ui-flow (ui-flow-reviewer, 2026-11-16)

Veredito: FLOW OK. Nenhum modal preso, nenhuma transição morta, nenhuma dica `[C]` no código de produção e a ação "cancel" não é mais produzida. NOVO ENCODE e o caminho do Ctrl+C estão intactos.
- Baixa: os campos `modal`/`modal_focus` em `state.py:115-116` ficaram sem função (mantidos de propósito, ver STATE P3H-8a).
- Info: em produção, nada chama mais `reporter.CancelControl.request_cancel` (o driver usa `force_cancel`).
- Info: `docs/Phase_2_TUI_Specification.md` (não rastreado) e os planos antigos em `docs/superpowers/` ainda descrevem o modal CANCEL e o `[C]`.

## Ciclo L2 (2026-11-17)

- Pester 5.7.1: pwsh 7 com 156 passed / 0 failed e Windows PowerShell 5.1 com 156 passed / 0 failed, conferidos pelo Orquestrador. ruff e `git diff --check` limpos. Zero tabs em `launcher.ps1`, `launcher.cmd` e `tools/*.ps1`.
- RESOLVIDO em 2026-11-18, com evidência dos dois modos: S2 (modo padrão) e S3 (`-NoDownload`), ambos com FFmpeg/FFprobe só no PATH e sem eles em `bin\` (§ Smokes do launcher (L2)). Execução automatizada pelo Orquestrador em cópia isolada, com `PSModulePath` limpo no processo filho; não é relato manual do usuário. Original: smoke manual do `launcher.cmd`, no modo padrão e com `-NoDownload`, tendo o FFmpeg só no PATH.
- PENDENTE (CI): leg ubuntu do Pester, que não foi verificado localmente. Os 4 testes que executam o fetch falso dependem de `tools\fetch_*.ps1` com `\` resolver no pwsh/Linux.
- CI (PR #81, head `fa26f8f`, squash `7920e07`): 8 checks SUCCESS — run 44013773672 (Lint ruff; Tests windows 3.11/3.12; Pester ubuntu-latest, windows-latest e Windows PowerShell 5.1) e run 44013767509 (build 3.11/3.12). Resolve o PENDENTE (CI) acima.
- Manual (relato do usuário, mensagem de 2026-11-17 ~00:59, com o CI do PR #81 verde e antes do merge): "o CI ficou verde e ja fiz o teste manual aqui e funcionou" — relato genérico, **não especifica o modo** (padrão ou `-NoDownload`). A execução do `launcher.cmd` no modo padrão foi confirmada explicitamente depois, no M0 do R-03 (relato do usuário, 2026-11-17).
- RESOLVIDO em 2026-11-18 (S1 com binários locais; S1b sem binários, com controle sem a flag): `launcher.cmd -NoDownload` executado e observado. Condição: `PSModulePath` limpo no processo filho. Com `PSModulePath` herdado de uma sessão pwsh 7 o launcher falha antes de qualquer verificação de binário (L2F5, achado separado, reproduzido na rodada seguinte; corrigido na branch `fix/l2f5-psmodulepath`, não publicada — § 6).
- RESOLVIDO em 2026-11-18 (S2 modo padrão; S3 `-NoDownload`): smoke com FFmpeg/FFprobe **somente no PATH** (sem os binários em `bin\`), em pasta com espaços; `PSModulePath` limpo no processo filho. Contexto original: `bin\ffmpeg.exe` e `bin\ffprobe.exe` existem neste checkout e o launcher os prefere ao PATH; o M0 do R-03 não cobria esse cenário.

## R-03 — layout compacto 80×24 (2026-11-17, branch `fix/tui-review-r03-polish`) — resolvido

- Suíte completa **anterior ao último ajuste** (sobre R03-10, antes do R03-11): 1459 passed / 4 skipped. Os 4 skips: goldens `enhance/test_classic_golden.py:176` (numpy gravado 2.5.3, atual 2.5.2).
- Verificação **posterior aos ajustes finais** (R03-11 tocou só `ui/tui/screens.py` + `ui/tui/test_screens_compact.py`): `pytest ui` 1012 passed; `enhance/test_output_dir_and_pipeline_tag.py` (único teste fora de `ui/` que importa `ui.tui`) 17 passed; `ruff check .` e `git diff --check` limpos. Suíte completa não repetida.
- Captura real via ConPTY (`tests/screens/capture.py`, clipes de `videos/` copiados para pasta descartável; valida fluxo, não qualidade): ✓ HOME 80×24/100×30/119×39/120×40; ✓ 70×20 na entrada sai com mensagem 80×24; ✓ resize 80×24→70×20→80×24 com a TUI aberta; ✓ HOME→SOURCE→CONFIGURATION→PREVIEW→READY→ENCODING→LOG→DETAILS→QC→COMPLETED; ✓ ADVANCED 5 abas + CONTINUAR; ✓ NOVO ENCODE + 2ª sessão até COMPLETED; ✓ ERROR (saída ocupada por diretório) com rolagem do STDERR até a causa, VER LOG, resize 120×40 e volta com rolagem preservada; ✓ batch 2 e 16 jobs até REPORT, rolagem e resize compacto↔cheio.
- Só estado simulado: READY com erro longo (R03-10a).
- Não exercitado pelo harness: Ctrl+C no PASS e no QC — o ConPTY não entrega o sinal (R03F6); coberto pela validação manual abaixo. Cobertura determinística: `ui/test_tui_driver.py::test_ctrl_c_during_qc_keeps_new_master`.
- Validação manual (relato do usuário, 2026-11-17, Windows Terminal real; sem logs, hashes ou horários fornecidos): M0 launcher em 120×40 ✓; M1 80×24 medido + resize abaixo do mínimo durante encode ✓; M2 Ctrl+C no PASS ✓; M3 Ctrl+C no QC ✓; M4 Ctrl+C no QC com relatórios preexistentes ✓. Roteiro: master mantido e certificados novos removidos no QC, parcial novo removido no PASS, relatórios preexistentes preservados, sem subprocessos remanescentes.
- Veredito: R-03 resolvido (automatizado + harness + manual do usuário).

## Smokes do launcher (L2) — 2026-11-18, base `ab478cf`

Resolvem os PENDENTE (usuário) do § Ciclo L2. Executados pelo Orquestrador no PC do usuário, a pedido dele, em duas rodadas; sem alteração de código de produção, sem download, sem encode. Código testado = arquivos rastreados de `ab478cf`.

**Método.** Cópia temporária fora do repositório (arquivos rastreados do working tree, mais `venv/` e `bin/` copiados do checkout). O `launcher.cmd` real rodou via `cmd.exe /c … < NUL` em processo filho; `REELS_FFMPEG`/`REELS_FFPROBE` foram removidos e o PATH foi ajustado **só nesse processo** (PATH global, registro e configurações do Windows não foram tocados). Antes de cada rodada: stamp do venv conferido (nenhum `pip` possível), `ui` e motor importados da cópia, `ffmpeg.exe`/`ffprobe.exe` idênticos aos do checkout (SHA-256). A janela aberta pelo launcher foi observada lendo o buffer do console e enviando teclas via `AttachConsole` (técnica do `tests/screens/capture.py`) e inspecionando a árvore de processos. Ao final de cada rodada: só os processos e o diretório temporário foram removidos; checkout principal inalterado (`main` em `ab478cf`, árvore limpa, hashes de `ffmpeg`/`ffprobe`/`ffplay` e `wt.exe` iguais).

### 1. Execuções e condição de `PSModulePath`

| ID | Cenário | `PSModulePath` | Veredito | Evidência observada |
|---|---|---|---|---|
| S1 | `launcher.cmd -NoDownload`, `bin\ffmpeg.exe`/`ffprobe.exe` presentes, PATH real | **limpo** (só no filho) | aprovado | Exit 0. Log: venv reaproveitado (stamp confere, pip pulado), WT portátil encontrado, `FFmpeg encontrado (bin)`, `FFprobe encontrado (bin)`, ambos executáveis, `libx264`/`lut3d`/`zscale` ok, WT com 2 abas. Nenhuma linha de download nem processo `fetch_*`/`winget`. `REELS_FFMPEG`/`REELS_FFPROBE` pinados em `bin\`. Aba Encode: `python -m ui.tui` vivo após 10 s, HOME real lida do console (`v2.1.0`, FLUXOS, SYSTEM, `[ESC] Sair`); ESC: "Cancelado pelo usuário.", `$LASTEXITCODE` = 0, processo encerrado. No mesmo shell, `resolve_binary` → `bin\ffmpeg.exe`/`bin\ffprobe.exe`, ambos imprimem `n6.1.3-20250831`. Repetido 2×. |
| S1b | `-NoDownload` sem binários em `bin\` nem no PATH e sem WT | **limpo** | aprovado | Exit 1 com a mensagem prevista ("FFmpeg ou FFprobe nao encontrado em bin\ nem no PATH, e -NoDownload desliga o download automatico…") e aviso do WT ("download automatico desligado"). Salvaguarda: `tools\fetch_ffmpeg.ps1` e `fetch_wt_portable.ps1` trocados por sentinelas **na cópia**; nenhum foi chamado. Controle sem a flag: "Baixando FFmpeg 6.1 via winget…", os 2 sentinelas dispararam, exit 1. |
| S2 | Modo padrão; FFmpeg/FFprobe **só no PATH** (pasta com espaços), sem eles em `bin\`, sem `REELS_*` | **limpo** | aprovado | Exit 0. `FFmpeg encontrado (PATH: …\pasta ff com espacos\ffmpeg.exe)` e `FFprobe encontrado (PATH: …)`, ambos executáveis, WT com 2 abas; nenhuma linha de download. `REELS_FFMPEG`/`REELS_FFPROBE` pinados nesses caminhos (espaços preservados). TUI viva após 10 s, HOME lida do console, ESC → exit 0. No mesmo shell, `resolve_binary` e `-version` usam esses caminhos. PATH do processo = pasta de teste + PowerShell 7 + diretórios do sistema (FFmpeg global do WinGet fora). |
| S3 | **`-NoDownload` + FFmpeg/FFprobe só no PATH** (pasta com espaços), sem eles em `bin\`, sem `REELS_*` | **limpo** | aprovado | Exit 0. `FFmpeg encontrado (PATH: …\pasta ff com espacos\ffmpeg.exe)` e `FFprobe encontrado (PATH: …)`, ambos executáveis, `libx264`/`lut3d`/`zscale` ok, WT com 2 abas; nenhuma linha de download. Pinos `REELS_*` nesses caminhos. TUI viva após 10 s, HOME lida do console, ESC: "Cancelado pelo usuário.", `$LASTEXITCODE` = 0, processo encerrado. No mesmo shell, `resolve_binary` e `-version` (n6.1.3-20250831) usam esses caminhos. |
| L2F5-a | `launcher.cmd -NoDownload`, `bin\` local, a partir de uma sessão **pwsh 7.5.1** (cadeia pwsh → cmd → `powershell.exe -File`) | **herdado, NÃO limpo** (5 entradas, incl. `…\PowerShell\7\Modules`) | **reprovado** | Exit 1. Saída: `[INFO] Venv existente reaproveitado` e então `[ERRO] O termo 'Get-FileHash' não é reconhecido como nome de cmdlet…`. Com `-DebugMode`: `Get-RequirementsStamp` (`launcher.ps1:300`) ← `Initialize-Environment` (`:347`) ← bloco principal (`:758`). Nenhuma janela aberta. |
| L2F5-b | Equivalente exato de L2F5-a | **limpo** só no processo filho | aprovado | Exit 0, mesma saída do S1, TUI na HOME, ESC → `$LASTEXITCODE` = 0. |

Todas as execuções S1, S1b, S2, S3 e L2F5-b usaram `PSModulePath` limpo no processo filho; só L2F5-a (e a repetição com `-DebugMode`) o manteve herdado. **Os smokes aprovados valem para essa condição**; não foram executados com `PSModulePath` herdado, exceto L2F5-a.

### 2. L2F5 — causa

**Executado.**
- Reprodução no launcher completo (L2F5-a vs L2F5-b): mesma base, mesmos binários, mesmo `-NoDownload`; única diferença = `PSModulePath` herdado vs limpo no filho. A falha ocorre em `Get-RequirementsStamp`, antes de qualquer verificação de binário ou WT.
- Sondas na cadeia (pwsh 7.5.1, Windows PowerShell 5.1.19041.5129), com `PSModulePath` herdado: `pwsh → powershell.exe` direto → o 5.1 vê 3 entradas e `Get-FileHash` existe; `pwsh → cmd.exe → powershell.exe` (também com `-File`, como no `launcher.cmd`) → o 5.1 vê as 5 entradas herdadas e `Get-FileHash` **não** existe; com a variável removida no filho, existe. Na cadeia com cmd, `Get-Module -ListAvailable` passa de 83 módulos (baseline limpo) para 96: +14 módulos do PS7 (incl. `Microsoft.PowerShell.Utility` 7.0.0.0, edição Core, ao lado da 3.1.0.0 Desktop) e −1 (`PSScriptAnalyzer`, da pasta de usuário do 5.1, que a variável herdada não lista). `Write-Host`/`ConvertFrom-Json` continuaram funcionando nesse ambiente (o launcher os usou antes de falhar).
- Escopos lidos (somente leitura): `PSModulePath` Machine = `C:\Program Files\WindowsPowerShell\Modules;C:\Windows\system32\WindowsPowerShell\v1.0\Modules`; User = não definido. Nada foi alterado.

**Inferência (não verificada diretamente).**
- Por que só `Get-FileHash` falha: provavelmente é cmdlet que o 5.1 resolve por autoload de módulo (preferindo a 7.0.0.0), enquanto `Write-Host`/`ConvertFrom-Json` vêm do snap-in embutido. Os dados são compatíveis, mas o mecanismo interno não foi inspecionado.
- Exposição real do usuário: qualquer `launcher.cmd` iniciado de um terminal pwsh 7 (ou de outro processo com essa variável no ambiente). Foi executado a partir da sessão pwsh 7 desta ferramenta; **não** a partir de uma aba pwsh do Windows Terminal do usuário, nem por atalho/Explorer.
- `tools\fetch_wt_portable.ps1:76` também usa `Get-FileHash` (e `:89` `Expand-Archive`): mesma exposição possível; não executado (fetch não deve rodar).

### 3. Correções avaliadas (experimento isolado; nada aplicado em produção)

Cada candidata foi aplicada na cadeia que falha (pwsh → cmd → `powershell.exe -File`), comparando com o baseline limpo (83 módulos). Executado.

| Caso | `Get-FileHash` | Módulos vs baseline | Entrada custom herdada |
|---|---|---|---|
| 0 baseline limpo | ok | 83 | — |
| 1 herdado, sem correção | **falha** | 96 (+14, −1) | — |
| A: `set "PSModulePath="` no `launcher.cmd` antes do `powershell.exe` | ok | 83, idêntico (0 faltando, 0 extras) | descartada |
| B: remover só as entradas do PS7 (regex) | ok | 82: **perde** `PSScriptAnalyzer` (pasta de usuário do 5.1) | mantida |
| B+: B + garantir a pasta de usuário do 5.1 | ok | 83, idêntico | mantida |

Avaliação. B sozinho é insuficiente (perde descoberta). A e B+ preservam a descoberta de módulos de um 5.1 iniciado limpo. A é a mais simples e não depende de onde o PS7 está instalado; descarta entradas custom herdadas pelo processo (o launcher não usa módulos próprios; as entradas dos escopos Machine/User são recomputadas pelo 5.1). B+ mantém entradas custom, mas depende de reconhecer o caminho do PS7 por padrão de nome (inferência: instalações MSIX/dotnet tool podem diferir) e propaga ao `pwsh` das abas uma variável já filtrada (não testado; com a variável removida, como em A, as abas funcionaram nas execuções 'limpas'). **Recomendação a decidir pelo usuário: A** (com teste Pester que simule a cadeia pwsh → cmd com a variável herdada); B+ só se preservar entradas custom for requisito. Nenhuma das duas foi aplicada.

### 4. Limites

Observação por leitura do buffer do console, não por inspeção visual humana. O WT usado foi o portátil da cópia (`.portable`; configuração ficou na cópia, `LocalAppData` não mudou). `launcher.cmd` rodou com stdin em NUL (o `pause` do erro não bloqueia). Sem encode; aba Setup só nas primeiras linhas. Não coberto: início do launcher por atalho/Explorer e por aba pwsh do Windows Terminal do usuário.

### 5. Veredito dos PENDENTE do Ciclo L2

- Smoke modo padrão **e** `-NoDownload` com FFmpeg só no PATH → S2 + S3: **resolvido**.
- `launcher.cmd -NoDownload` → S1 + S1b: **resolvido**, na condição de `PSModulePath` limpo; com `PSModulePath` herdado de pwsh 7 o launcher falha (L2F5, aberto, fora do critério original).
- Smoke com FFmpeg/FFprobe somente no PATH → S2 + S3: **resolvido**.

### 6. L2F5 — correção A aplicada e validada (branch `fix/l2f5-psmodulepath`, base `ab478cf`; não publicada)

**Mudança.** `launcher.cmd`: `set "PSModulePath="` entre `cd /d "%~dp0"` e a chamada `powershell.exe`, mais 3 linhas `REM`. O `setlocal` já existente no topo escopa a mudança ao `cmd.exe` do launcher e aos seus filhos; `%*`, `RC`, `pause`, `exit /b` e a linha do `powershell.exe` ficaram inalterados. Nenhuma variável permanente do Windows foi alterada. `launcher.ps1` e `tools\` não foram tocados.

**Executado** (Orquestrador, cópia isolada refeita sobre a branch). Em **nenhuma** destas execuções o runner limpou `PSModulePath`: a limpeza é responsabilidade do `launcher.cmd`. A sonda trocou o `launcher.ps1` por um script de diagnóstico **apenas nas pastas de controle**, mantendo o `launcher.cmd` sob teste.

| Execução | `PSModulePath` | Resultado |
|---|---|---|
| Sonda do 5.1 pela cadeia pwsh 7 → `cmd.exe` → `launcher.cmd` **ORIGINAL** (`ab478cf`); valor herdado (5 entradas) + entrada customizada de teste | herdado (6 entradas) | `Get-FileHash` **ausente**, `Expand-Archive` presente; 96 módulos (hash ≠ baseline); `Microsoft.PowerShell.Utility` 7.0.0.0/Core além da 3.1.0.0/Desktop; entrada customizada e caminho `\PowerShell\7\` propagados |
| Mesma sonda com `launcher.cmd` **CORRIGIDO** | herdado (idêntico) | `Get-FileHash` e `Expand-Archive` presentes; 3 entradas; 83 módulos com hash **idêntico** ao baseline; só `Utility` 3.1.0.0/Desktop; entrada customizada e caminho do PS7 **não** propagados |
| Baseline: 5.1 direto, `PSModulePath` removido | limpo | 83 módulos |
| `launcher.cmd -NoDownload` **completo**, corrigido, PATH real, `bin\` local, a partir de sessão pwsh 7.5.1 | herdado, **não limpo** (5 entradas) | Exit 0; log idêntico ao do S1 (FFmpeg e FFprobe de `bin`, ambos executáveis, `libx264`/`lut3d`/`zscale`, WT com 2 abas, nenhuma linha de download); `REELS_FFMPEG`/`REELS_FFPROBE` pinados em `bin\`; TUI viva após 10 s e HOME lida do console (`v2.1.0`, FLUXOS, SYSTEM, `[ESC] Sair`); ESC: "Cancelado pelo usuário.", `$LASTEXITCODE` = 0, processo encerrado; `resolve_binary` e `-version` (n6.1.3-20250831) ok no mesmo shell |

- **Ambiente do chamador.** O hash do `PSModulePath` do runner (processo chamador do `cmd.exe`) e o da sessão observadora ficaram iguais antes e depois (`unchanged=True`), assim como o da sessão da ferramenta nas sondas.
- **Aba pwsh aberta pelo launcher.** Recompôs o próprio valor padrão do pwsh 7 (6 entradas), sem a entrada customizada herdada.
- **Pester** (`tests/launcher-cmd.Tests.ps1`, 8 testes; os 7 que usam `cmd.exe` só rodam no Windows, com `-Skip` nas demais plataformas; o estático roda em todas). **RED** verificado pelo Orquestrador contra o `launcher.cmd` do HEAD numa estrutura temporária: 4 falham (entrada customizada propagada, `Get-FileHash` ausente, módulos ≠ baseline, ausência do `set`) e 4 passam (argumentos e diretório de trabalho, exit 0, exit 7, preservação no chamador). **GREEN**: 8/8 em pwsh 7 e em Windows PowerShell 5.1. Suíte `./tests` completa: 164 passed, 0 failed, 0 skipped em pwsh 7 e em 5.1 (o 5.1 foi lançado como filho direto do pwsh). `git diff --check` rc=0.
- **Ressalva sobre o teste do chamador.** Ele passa também sem a correção, porque o `setlocal` já restaurava o valor do chamador: é teste de regressão, não prova da correção. Usa `cmd /d /v:on` e `!PSModulePath!`, pois `%PSModulePath%` seria expandido antes do `call`.

**Efeito colateral documentado.** Com a correção, **entradas customizadas herdadas de `PSModulePath` deixam de ser propagadas** ao `powershell.exe` do launcher e aos processos que ele abre (as abas pwsh recompõem o padrão do pwsh 7). Entradas dos escopos Machine e User continuam sendo recompostas pelo próprio PowerShell (nesta máquina: Machine = só caminhos do Windows PowerShell; User não definido). O launcher não usa módulos próprios.

**Inferência / não verificado.** `tools\fetch_wt_portable.ps1:76` (`Get-FileHash`) e `:89` (`Expand-Archive`): mesma exposição possível pela cadeia pwsh → cmd, não executada e não testada especificamente. Não testado: início por atalho/Explorer ou por aba pwsh do Windows Terminal do usuário; os novos testes na CI (a leg ubuntu deve pular os 7 que usam `cmd.exe`); `launcher.cmd` completo com FFmpeg só no PATH depois da correção.

**Condições preservadas.** S1, S1b, S2, S3 e L2F5-b continuam valendo para `PSModulePath` limpo no processo filho; L2F5-a permanece como evidência da falha antes da correção. As execuções deste § 6 são as únicas pós-correção e usaram `PSModulePath` herdado.
