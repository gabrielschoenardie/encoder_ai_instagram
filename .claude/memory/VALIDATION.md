# Validação de Encodes — Ciclo BE (loudness mono, bitrate ≤15s, skill × código)

**Data:** 2026-09-27 | **Validador:** agente `validador` | **FFmpeg:** n6.1.3-20250831 estático | **Fonte:** `testsrc2` 1080×1920, 60 fps, 3 s, áudio mono (`sine`)

---

## Fixture

Comando de criação:
```bash
ffmpeg -y -f lavfi -i "testsrc2=size=1080x1920:rate=60:duration=3" \
  -f lavfi -i "sine=frequency=1000:duration=3:sample_rate=48000" \
  -c:v libx264 -pix_fmt yuv420p -crf 10 -colorspace bt709 \
  -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -ac 1 -shortest "$WORK/fixture_mono.mp4"
```

**Confirmado:** Vídeo 1080×1920 @ 60 fps (60/1), áudio mono 1 canal, 48 kHz.

---

## Encode (a): FFmpeg CRF Defaults

**Comando:**
```bash
"$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$WORK/in_a/fixture_mono.mp4" --ebu-meter off
```

**Tempo:** 17.757 s

**Arquivo:** `fixture_mono_Hollywood_CRF18.mp4`

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 12777 kbps | ✗ |
| GOP (keyframe) | máx ~60 frames = 2s | 29 frames = 0.97s @ 30 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 188 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3 s | 3 s | ✓ |
| Faststart (moov) | moov antes de mdat | sim | ✓ |
| True Peak | ≤ -1 dBTP | -13.2 dBTP | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.0 LUFS | ✓ |

**Veredito:** REPROVADO — 1 check falhou (bitrate vídeo 12777 kbps > 12000 kbps)

---

## Encode (b): FFmpeg 2-Pass

**Comando:**
```bash
"$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$WORK/in_b/fixture_mono.mp4" --mode 2pass --ebu-meter off
```

**Tempo:** 24.399 s

**Arquivo:** `fixture_mono_Hollywood_2Pass.mp4`

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 9574 kbps (zona segura) | ✓ |
| GOP (keyframe) | máx ~60 frames = 2s | 29 frames = 0.97s @ 30 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 188 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3 s | 3 s | ✓ |
| Faststart (moov) | moov antes de mdat | sim | ✓ |
| True Peak | ≤ -1 dBTP | -13.2 dBTP | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.0 LUFS | ✓ |

**Veredito:** APROVADO — conformidade total (0 falhas)

---

## Encode (c): Cineon Pipeline CRF

**Comando:**
```bash
"$PY" "$REPO/Reels_Encoder_v2_FINAL.py" "$WORK/in_c/fixture_mono.mp4" --cineon-pipeline on --ebu-meter off
```

**Tempo:** 239.522 s

**Arquivo:** `fixture_mono_Cineon_Film.mp4`

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p (4:2:0, 8-bit) | ✓ |
| Resolução | 1080×1920 | 1080×1920 (9:16) | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 12905 kbps | ✗ |
| GOP (keyframe) | máx ~60 frames = 2s | 30 frames = 1.00s @ 30 fps | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 183 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3 s | 3 s | ✓ |
| Faststart (moov) | moov antes de mdat | sim | ✓ |
| True Peak | ≤ -1 dBTP | -13.2 dBTP | ✓ |
| Loudness integrado | -14 ±1 LUFS | -14.0 LUFS | ✓ |

**Veredito:** REPROVADO — 1 check falhou (bitrate vídeo 12905 kbps > 12000 kbps)

---

## Veredito Consolidado

| Encode | Tipo | Bitrate (kbps) | LUFS | TP (dBTP) | Resultado |
|--------|------|----------------|------|-----------|-----------|
| (a) CRF Defaults | FFmpeg | 12777 ✗ | -14.0 ✓ | -13.2 ✓ | REPROVADO |
| (b) 2-Pass | FFmpeg | 9574 ✓ | -14.0 ✓ | -13.2 ✓ | APROVADO |
| (c) Cineon | Cineon | 12905 ✗ | -14.0 ✓ | -13.2 ✓ | REPROVADO |

**Status do Ciclo BE:** `blocked` no momento da medição — (a) e (c) reprovaram no bitrate médio. **Desfecho (Orquestrador, 2026-09-27):** o usuário decidiu manter `vbv_init` 0,9 e aceitar o estouro do CRF ≤15s como limitação; ver `FINDINGS.md` § "Decisão — 2026-09-27 (Ciclo BE)". Os reprovados (a) e (c) são esperados; BDF16 e BDF9 (2-pass) estão provados por (a)/(b)/(c).

**Observações:**
- Loudness mono (fonte −21.08 LUFS) convertida para estéreo dentro da pipeline: saída −14.0 LUFS em ambos os pipelines (FFmpeg e Cineon), confirmando BE1 `BDF16`.
- Encode (b) 2-pass prova BDF9: bitrate 9574 kbps dentro do teto de 12000 kbps com tier ultra_short (10000 target, 11200 maxrate, 15000 bufsize).
- Encodes (a) e (c): 12777 e 12905 kbps, 6,5% e 7,5% acima do teto de 12000 e ≈14% acima do próprio `maxrate` de 11200. **Correção do Orquestrador:** a versão anterior desta linha dizia "sobre o teto estimado em 2%" — era a estimativa do plano (11200 × 1,05 ≈ 11760), não a medição. O excesso vem do buffer VBV inicial (`vbv_init` 0,9 × `bufsize` 15000), que escala com a duração do clipe; ver `FINDINGS.md`.
- GOPs validados em 30 fps (0.97–1.00 s), bem dentro do limite de 2 s = 60 frames.
