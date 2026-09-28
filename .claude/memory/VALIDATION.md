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