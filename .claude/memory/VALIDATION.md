# Validação de Encodes — Ciclo BD10

**Data:** 2026-09-27 | **Validador:** agente `validador` | **FFmpeg:** 6.0.1 estático | **Fonte:** `testsrc2` 1080×1920, 60 fps, 3 s, áudio mono (`sine`)

---

## Arquivo 1: src_1080x1920_60fps_Hollywood_CRF18.mp4

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p | ✓ |
| Resolução | 1080×1920 | 1080×1920 | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 13656 kbps | ✗ |
| GOP (keyframe) | máx ~29-30 | 29 frames | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 191 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3s | 3s | ✓ |
| Faststart (moov) | moov antes de mdat | sim | ✓ |
| True Peak | ≤ -1 dBTP | -15.9 dBTP | ✓ |
| Loudness integrado | -14 LUFS (±1) | -17.0 LUFS | ⚠ |

**Veredito:** REPROVADO — 1 check falhou (bitrate vídeo 13656 kbps > 12000 kbps) + 1 aviso

---

## Arquivo 2: src_1080x1920_60fps_Cineon_Film.mp4

| check | esperado | medido | status |
|-------|----------|--------|--------|
| Codec | H.264 | H.264 | ✓ |
| Profile | High | High | ✓ |
| Level | 4.1 | 4.1 | ✓ |
| Pixel format | yuv420p | yuv420p | ✓ |
| Resolução | 1080×1920 | 1080×1920 | ✓ |
| FPS | 30 fps | 30 fps | ✓ |
| Frame rate mode | CFR | CFR | ✓ |
| Bitrate vídeo | ≤ 12000 kbps | 11874 kbps | ✓ |
| GOP (keyframe) | máx ~29-30 | 30 frames | ✓ |
| color_primaries | bt709 | bt709 | ✓ |
| color_transfer | bt709 | bt709 | ✓ |
| color_space | bt709 | bt709 | ✓ |
| Codec áudio | AAC-LC | AAC-LC | ✓ |
| Bitrate áudio | ~128-192 kbps | 186 kbps | ✓ |
| Sample rate | 48000 Hz | 48000 Hz | ✓ |
| Canais | Stereo | Stereo | ✓ |
| Duração | 3s | 3s | ✓ |
| Faststart (moov) | moov antes de mdat | sim | ✓ |
| True Peak | ≤ -1 dBTP | -15.9 dBTP | ✓ |
| Loudness integrado | -14 LUFS (±1) | -17.0 LUFS | ⚠ |

**Veredito:** APROVADO COM RESSALVAS — 0 falhas críticas, 1 aviso

---

## Veredito Consolidado

**Arquivo 1 (Hollywood CRF18):** REPROVADO — 1 check falhou
**Arquivo 2 (Cineon Film):** APROVADO COM RESSALVAS — 0 checks falharam
