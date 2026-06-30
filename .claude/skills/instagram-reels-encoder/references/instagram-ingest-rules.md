# Instagram Ingest Rules — Especificação Completa

Referência técnica definitiva para conformidade com as regras de ingestão do Instagram/Meta
para Reels 9:16. Dados consolidados de engenharia reversa e documentação Meta.

---

## Especificações de Vídeo

| Parâmetro | Valor obrigatório / aceito | Observação |
|---|---|---|
| Codec | H.264 (AVC) | HEVC aceito mas provoca recompressão |
| Profile | High | Main aceito; Baseline evitar |
| Level | 4.0 ou 4.1 | Level 4.2+ pode causar rejeição |
| Bit depth | 8-bit (yuv420p) | 10-bit → recompressão garantida |
| Chroma | 4:2:0 | 4:2:2 e 4:4:4 → rejeição |
| Resolução | 1080×1920 (9:16) | Obrigatório para Reels |
| FPS | 30 fps (recomendado) | 24/25/60 aceitos; 60fps reduz qualidade percebida pós-upload |
| Bitrate máximo | ~11200 kbps (prático) | Ceiling documentado: ~10 Mbps; headroom de 12% |
| Bitrate mínimo | 3500 kbps | Abaixo disso → artifact severo pós-upload |
| Keyframe interval | ≤ 2s (max 60 frames a 30fps) | GOP aberto com keyframes frequentes |
| B-frames | 2 (recomendado) | Até 4 aceito; acima → risco de artefato |
| Reference frames | 4 | Alinhado com Level 4.0 |

---

## Especificações de Áudio

| Parâmetro | Valor obrigatório / aceito |
|---|---|
| Codec | AAC-LC |
| Bitrate | 128 kbps (recomendado); 192 kbps aceito |
| Sample rate | 44100 Hz ou 48000 Hz |
| Canais | Stereo (2ch) — mono aceito mas não recomendado |

---

## Container e Metadados

| Parâmetro | Valor |
|---|---|
| Container | MP4 (MPEG-4 Part 12) |
| moov atom | Início do arquivo (`-movflags +faststart` obrigatório) |
| Color primaries | BT.709 |
| Transfer characteristic | BT.709 (gamma 2.2) |
| Matrix coefficients | BT.709 |

> **Atenção:** Instagram lê e respeita os metadados de colorimetria. Arquivos tagueados como
> BT.601 ou sem tag podem sofrer shift de cor após upload.

---

## Limites de Duração

| Tipo | Duração |
|---|---|
| Reels mínimo | 3 segundos |
| Reels máximo | 90 segundos |
| Sweet spot algoritmo | 15–30 segundos (maior alcance orgânico) |

---

## Thresholds Críticos de Recompressão

O Instagram recomprime o vídeo quando detecta qualquer violação. Também recomprime
com base em bitrate e complexidade mesmo dentro das specs.

### Gatilhos garantidos de recompressão:
- Bit depth ≠ 8-bit
- Chroma ≠ 4:2:0
- Codec ≠ H.264
- Resolução ≠ 1080×1920
- moov atom no final do arquivo (sem faststart)
- FPS > 60 ou FPS com frações (ex.: 29.97 em alguns casos)

### Gatilhos de recompressão provável (bitrate-based):
- Bitrate > 11200 kbps → Instagram limita ativamente
- Bitrate < 5000 kbps com cena de alta complexidade → artefato pós-recompressão
- Variação de bitrate extrema em janelas curtas → buffering → recompressão adaptativa

### Indicadores de upload sem recompressão:
Verificar após upload via inspeção do arquivo (download do Instagram):
- `ffprobe` no arquivo baixado mostra bitrate próximo ao enviado (±5%)
- Profile e level preservados
- Duração idêntica ao original

---

## Checklist de Conformidade Pré-Upload

```
[ ] Codec: H.264 High Profile Level 4.0
[ ] Resolução: 1080×1920
[ ] FPS: 30 (ou 24/25 se intencional)
[ ] Bit depth: 8-bit yuv420p
[ ] Bitrate: ≤ 11200 kbps (target ≤ 10000 kbps)
[ ] Áudio: AAC 128kbps 44100Hz stereo
[ ] Container: MP4 com faststart
[ ] Color: BT.709 tagueado corretamente
[ ] Duração: 3s–90s
[ ] GOP: keyframe ≤ 60 frames
[ ] Loudness: -14 LUFS integrated (±1 LU)
```

---

## Audio Loudness — LUFS para Instagram

O Instagram aplica **normalização de loudness automática** no upload. Se o arquivo
for entregue fora do target, o algoritmo deles ajusta o ganho, podendo introduzir
distorção em picos e alterar a percepção de dinâmica da música.

### Target Instagram

| Métrica | Valor alvo | Tolerância |
|---|---|---|
| Integrated loudness | -14 LUFS | ±1 LU |
| True peak | -1 dBTP | máximo |
| Loudness range (LRA) | ≤ 14 LU | recomendado |

> **Prática:** entregar entre -14 e -13 LUFS integrated. Instagram normaliza para -14,
> então entregar exatamente em -14 garante que o áudio chegue sem ganho adicional.

### Medir loudness com FFmpeg (ebur128)

```bash
# Medir loudness do arquivo antes de encodar
ffmpeg -i input.mp4 \
  -af "ebur128=peak=true" \
  -f null - 2>&1 | grep -E "I:|True peak|LRA"

# Output esperado:
#   I:      -14.2 LUFS   ← integrated (deve estar entre -15 e -13)
#   True peak: -0.8 dBTP ← deve ser ≤ -1 dBTP
#   LRA:     8.5 LU      ← deve ser ≤ 14 LU
```

### Normalizar loudness automaticamente

```bash
# Passo 1: medir loudness atual
STATS=$(ffmpeg -i input.mp4 -af "ebur128=peak=true" -f null - 2>&1)
I_LUFS=$(echo "$STATS" | grep "I:" | tail -1 | awk '{print $2}')
TP=$(echo "$STATS" | grep "True peak" | tail -1 | awk '{print $2}')

# Passo 2: calcular ganho necessário
GAIN=$(python3 -c "print(round(-14.0 - float('$I_LUFS'), 1))")

echo "Loudness atual: ${I_LUFS} LUFS | Ganho necessário: ${GAIN} dB"

# Passo 3: aplicar no encode (adicionar ao -af chain)
ffmpeg -i input.mp4 \
  [parâmetros de vídeo] \
  -af "volume=${GAIN}dB,alimiter=limit=-1dB:attack=5:release=50" \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  [demais parâmetros] output.mp4
# alimiter garante que o peak não ultrapasse -1 dBTP após o ganho
```

### One-shot: normalizar e limitar em um único comando

```bash
# loudnorm filter — normalização em 2-pass integrada no FFmpeg
# Pass 1: medir
LOUDNORM_STATS=$(ffmpeg -i input.mp4 \
  -af "loudnorm=I=-14:TP=-1:LRA=11:print_format=json" \
  -f null - 2>&1 | tail -12)

# Extrair parâmetros medidos
INPUT_I=$(echo  "$LOUDNORM_STATS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_i'])")
INPUT_TP=$(echo "$LOUDNORM_STATS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_tp'])")
INPUT_LRA=$(echo "$LOUDNORM_STATS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_lra'])")
INPUT_THRESH=$(echo "$LOUDNORM_STATS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_thresh'])")

# Pass 2: encode com normalização precisa
ffmpeg -i input.mp4 \
  [parâmetros de vídeo] \
  -af "loudnorm=I=-14:TP=-1:LRA=11:\
measured_I=${INPUT_I}:\
measured_TP=${INPUT_TP}:\
measured_LRA=${INPUT_LRA}:\
measured_thresh=${INPUT_THRESH}:\
linear=true:print_format=summary" \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  [demais parâmetros] output.mp4
```

> **Quando usar 2-pass loudnorm:** sempre que o áudio tem dinâmica variável
> (música ao vivo, cerimônia com silêncio + aplauso). A normalização linear
> do 2-pass evita pumping e distorção.
>
> **Quando usar `volume + alimiter`:** áudio já processado e homogêneo
> (trilha musical de estúdio). Mais rápido, sem risco de artifact de normalização.
