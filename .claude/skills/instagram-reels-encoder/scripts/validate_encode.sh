#!/usr/bin/env bash
# =================================================================
#  validate_encode.sh — Validador pós-encode Instagram Reels
#  Metodologia Gabriel
#  Uso: ./validate_encode.sh <output.mp4>
# =================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; NC='\033[0m'

FILE="${1:-}"
[[ -z "$FILE" ]] && { echo "Uso: $0 <arquivo.mp4>"; exit 1; }
[[ ! -f "$FILE" ]] && { echo -e "${RED}Arquivo não encontrado: $FILE${NC}"; exit 1; }

PASS=0; FAIL=0; WARN=0

ok()   { echo -e "  ${GREEN}✅${NC}  ${1}: ${BOLD}${2}${NC}";                       PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}❌${NC}  ${1}: ${BOLD}${2}${NC}  → esperado: ${3}";       FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}⚠️ ${NC}  ${1}: ${BOLD}${2}${NC}  → recomendado: ${3}"; WARN=$((WARN+1)); }

sep()  { echo "────────────────────────────────────────────"; }
hdr()  { echo ""; echo -e "${BOLD}▶ ${1}${NC}"; sep; }

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  VALIDADOR INSTAGRAM REELS — Metodologia Gabriel${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "  Arquivo: ${BOLD}$(basename "$FILE")${NC}"
echo ""

# ── Extrai info do stream de vídeo ────────────────────────────────
V=$(ffprobe -v quiet -select_streams v:0 \
    -show_entries stream=codec_name,profile,level,width,height,r_frame_rate,bit_rate,pix_fmt,color_primaries,color_transfer,color_space \
    -of json "$FILE" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)['streams'][0]
fps_parts = d.get('r_frame_rate', '30/1').split('/')
fps = float(fps_parts[0]) / float(fps_parts[1]) if float(fps_parts[1]) else float(fps_parts[0])
br = int(d.get('bit_rate') or 0) // 1000
print('|'.join([
    d.get('codec_name', ''),
    d.get('profile', ''),
    str(d.get('level', '0')),
    str(d.get('width', '0')),
    str(d.get('height', '0')),
    f'{fps:.2f}',
    str(br),
    d.get('pix_fmt', ''),
    d.get('color_primaries', 'unknown'),
    d.get('color_transfer', 'unknown'),
    d.get('color_space', 'unknown'),
]))
" 2>/dev/null || echo "||||||||unknown|unknown|unknown")

IFS='|' read -r CODEC PROFILE LEVEL WIDTH HEIGHT FPS BITRATE PIX_FMT CP CT CS <<< "$V"
FPS_INT=$(python3 -c "print(round(float('${FPS:-0}')))" 2>/dev/null || echo "0")
BITRATE="${BITRATE:-0}"

# Fallback bitrate: se stream reportou 0, usa format - audio
if [[ "$BITRATE" -eq 0 ]]; then
  BITRATE=$(ffprobe -v quiet -show_entries format=bit_rate -of csv=p=0 "$FILE" 2>/dev/null | \
    python3 -c "import sys; v=sys.stdin.read().strip(); print(max(0, int(v or 0)//1000 - 128))" 2>/dev/null || echo "0")
fi

# ── Extrai info do stream de áudio ────────────────────────────────
A=$(ffprobe -v quiet -select_streams a:0 \
    -show_entries stream=codec_name,bit_rate,sample_rate,channels \
    -of json "$FILE" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)['streams'][0]
br = int(d.get('bit_rate') or 0) // 1000
print('|'.join([
    d.get('codec_name', 'N/A'),
    str(br),
    str(d.get('sample_rate', '0')),
    str(d.get('channels', '0')),
]))
" 2>/dev/null || echo "N/A|0|0|0")

IFS='|' read -r ACODEC ABITRATE ASAMPLERATE ACHANNELS <<< "$A"

# ── Duração ───────────────────────────────────────────────────────
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$FILE" 2>/dev/null || echo "0")
DURATION_INT=$(python3 -c "print(round(float('${DURATION:-0}')))" 2>/dev/null || echo "0")

# ── Faststart: moov antes de mdat ────────────────────────────────
FASTSTART=$(python3 - "$FILE" << 'PYEOF'
import struct, sys
path = sys.argv[1]
try:
    with open(path, 'rb') as f:
        seen_mdat = False
        for _ in range(30):
            header = f.read(8)
            if len(header) < 8:
                break
            size = struct.unpack('>I', header[:4])[0]
            box = header[4:8].decode('ascii', errors='replace')
            if box == 'mdat':
                seen_mdat = True
            elif box == 'moov':
                print('fail' if seen_mdat else 'pass')
                sys.exit(0)
            if size < 8:
                break
            f.seek(size - 8, 1)
    print('unknown')
except Exception as e:
    print('unknown')
PYEOF
)

# ── GOP: maior intervalo entre I-frames (primeiros 30s) ──────────
MAX_GOP=$(ffprobe -v quiet -select_streams v:0 \
    -read_intervals "%+00:00:30" \
    -show_entries frame=pict_type \
    -of csv=p=0 "$FILE" 2>/dev/null | \
  python3 -c "
import sys
frames = [l.strip() for l in sys.stdin if l.strip()]
last = 0; max_gop = 0
for i, f in enumerate(frames):
    if f == 'I':
        gop = i - last
        if gop > max_gop:
            max_gop = gop
        last = i
print(max_gop)
" 2>/dev/null || echo "0")

# ═══════ CHECKS ══════════════════════════════════════════════════

hdr "VÍDEO"

[[ "$CODEC" == "h264"  ]] && ok   "Codec"         "H.264"                        \
                           || fail "Codec"         "${CODEC:-N/A}"                "h264"

[[ "$PROFILE" == "High" ]] && ok  "Profile"       "High"                         \
                            || fail "Profile"      "${PROFILE:-N/A}"              "High"

case "$LEVEL" in
  40) ok   "Level" "4.0" ;;
  41) ok   "Level" "4.1" ;;
  42) warn "Level" "4.2" "4.0 ou 4.1 — 4.2+ pode causar rejeição" ;;
  *)  warn "Level" "${LEVEL:-N/A}" "4.0 ou 4.1" ;;
esac

[[ "$PIX_FMT" == "yuv420p" ]] && ok   "Pixel format"  "yuv420p (4:2:0, 8-bit)"  \
                               || fail "Pixel format"  "${PIX_FMT:-N/A}"         "yuv420p — 10-bit ou 4:2:2 geram recompressão"

[[ "$WIDTH" == "1080" && "$HEIGHT" == "1920" ]] \
  && ok   "Resolução" "1080×1920 (9:16)"                                          \
  || fail "Resolução" "${WIDTH:-?}×${HEIGHT:-?}"                                  "1080×1920"

if   [[ "$FPS_INT" == "30"                        ]]; then ok   "FPS" "30 fps"
elif [[ "$FPS_INT" == "24" || "$FPS_INT" == "25"  ]]; then warn "FPS" "$FPS fps" "30 fps recomendado"
elif [[ "$FPS_INT" == "60"                        ]]; then warn "FPS" "60 fps"   "30 fps — 60fps reduz qualidade pós-upload"
else                                                       fail "FPS" "$FPS fps" "30 fps"; fi

# Detecção de VFR (Variable Frame Rate) — causa raiz de A/V sync drift
VFR_STATUS=$(ffprobe -v quiet -select_streams v:0 \
    -show_entries stream=avg_frame_rate,r_frame_rate \
    -of json "$FILE" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)['streams'][0]
def parse(s):
    try:
        n, dd = s.split('/')
        return float(n) / float(dd) if float(dd) else 0.0
    except Exception:
        return 0.0
avg = parse(d.get('avg_frame_rate', '0/1'))
r   = parse(d.get('r_frame_rate',   '0/1'))
if abs(avg - r) > 0.5 and avg > 0:
    print(f'vfr:{avg:.3f}avg/{r:.3f}r')
else:
    print('cfr')
" 2>/dev/null || echo "unknown")

case "$VFR_STATUS" in
  cfr)     ok   "Frame rate mode" "CFR (Constant Frame Rate)" ;;
  unknown) warn "Frame rate mode" "não detectado"             "verificar manualmente" ;;
  vfr:*)   fail "Frame rate mode" "VFR — ${VFR_STATUS#vfr:}" "CFR obrigatório → A/V sync drift garantido" ;;
esac

if   (( BITRATE >= 3500 && BITRATE <= 10000 )); then ok   "Bitrate vídeo" "${BITRATE} kbps (zona segura)"
elif (( BITRATE > 10000 && BITRATE <= 11200 )); then warn "Bitrate vídeo" "${BITRATE} kbps" "≤ 10000 kbps (headroom ativo)"
elif (( BITRATE > 11200                     )); then fail "Bitrate vídeo" "${BITRATE} kbps" "≤ 11200 kbps → recompressão garantida"
elif (( BITRATE >= 1 && BITRATE < 3500      )); then warn "Bitrate vídeo" "${BITRATE} kbps" "≥ 3500 kbps mínimo recomendado"
else                                                 warn "Bitrate vídeo" "não detectado"   "verificar manualmente com ffprobe"; fi

if   (( MAX_GOP > 0 && MAX_GOP <= 60 )); then ok   "GOP (keyframe)" "máx ${MAX_GOP} frames a cada ~$((MAX_GOP * 33 / 1000))ms"
elif (( MAX_GOP > 60                  )); then fail "GOP (keyframe)" "${MAX_GOP} frames"   "≤ 60 frames (2s @ 30fps)"
else                                           warn "GOP (keyframe)" "não detectado"       "verificar keyint manualmente"; fi

hdr "COR"

[[ "$CP" == "bt709" ]] && ok   "color_primaries" "bt709"                       \
                        || fail "color_primaries" "${CP:-unknown}"              "bt709 — risco de color shift pós-upload"
[[ "$CT" == "bt709" ]] && ok   "color_transfer"  "bt709"                       \
                        || fail "color_transfer"  "${CT:-unknown}"              "bt709"
[[ "$CS" == "bt709" ]] && ok   "color_space"     "bt709"                       \
                        || fail "color_space"     "${CS:-unknown}"              "bt709"

hdr "ÁUDIO"

[[ "$ACODEC" == "aac" ]] && ok   "Codec áudio"  "AAC-LC"                      \
                           || fail "Codec áudio" "${ACODEC:-N/A}"              "aac"

if   (( ABITRATE >= 128 && ABITRATE <= 192 )); then ok   "Bitrate áudio"  "${ABITRATE} kbps"
elif (( ABITRATE > 192                     )); then warn "Bitrate áudio"  "${ABITRATE} kbps"  "128–192 kbps"
elif (( ABITRATE > 0 && ABITRATE < 128     )); then warn "Bitrate áudio"  "${ABITRATE} kbps"  "mín. 128 kbps"
else                                                warn "Bitrate áudio"  "não detectado"     "128 kbps"; fi

[[ "$ASAMPLERATE" == "44100" || "$ASAMPLERATE" == "48000" ]] \
  && ok   "Sample rate" "${ASAMPLERATE} Hz"                                    \
  || fail "Sample rate" "${ASAMPLERATE:-N/A}"                                  "44100 ou 48000 Hz"

[[ "$ACHANNELS" == "2" ]] && ok   "Canais" "Stereo (2ch)"                     \
                           || warn "Canais" "${ACHANNELS}ch"                   "2 (stereo)"

hdr "CONTAINER"

if   (( DURATION_INT >= 3 && DURATION_INT <= 90 )); then ok   "Duração" "${DURATION_INT}s"
elif (( DURATION_INT < 3                        )); then fail "Duração" "${DURATION_INT}s"    "mín. 3s"
else                                                    fail "Duração" "${DURATION_INT}s"    "máx. 90s"; fi

case "$FASTSTART" in
  pass)    ok   "Faststart (moov)" "moov antes de mdat ✓" ;;
  fail)    fail "Faststart (moov)" "mdat antes de moov"   "-movflags +faststart — quebra streaming" ;;
  unknown) warn "Faststart (moov)" "não detectado"        "verificar manualmente" ;;
esac

hdr "LOUDNESS"
echo "  medindo... (processa o áudio completo)"

LUFS_RAW=$(ffmpeg -i "$FILE" \
  -af "ebur128=peak=true" \
  -f null - 2>&1)

I_LUFS=$(echo "$LUFS_RAW" | awk '/I:/{val=$2} END{print val}')
TP=$(echo "$LUFS_RAW" | awk '/True peak/{val=$NF} END{print val}')

if [[ -z "$I_LUFS" || "$I_LUFS" == "0" ]]; then
  warn "Loudness integrado" "não detectado" "verificar manualmente"
else
  LUFS_CHECK=$(python3 -c "
v = float('$I_LUFS')
if -15.0 <= v <= -13.0:
    print('ok')
elif v < -15.0:
    print('low')
else:
    print('high')
" 2>/dev/null || echo "unknown")

  case "$LUFS_CHECK" in
    ok)      ok   "Loudness integrado" "${I_LUFS} LUFS" ;;
    low)     warn "Loudness integrado" "${I_LUFS} LUFS" "-14 LUFS (±1) — Instagram aplica gain → risco de distorção" ;;
    high)    warn "Loudness integrado" "${I_LUFS} LUFS" "-14 LUFS (±1) — acima do target" ;;
    unknown) warn "Loudness integrado" "${I_LUFS} LUFS" "verificar manualmente" ;;
  esac
fi

if [[ -n "$TP" && "$TP" != "0" ]]; then
  TP_OK=$(python3 -c "print('ok' if float('$TP') <= -1.0 else 'fail')" 2>/dev/null || echo "unknown")
  case "$TP_OK" in
    ok)   ok   "True Peak" "${TP} dBTP" ;;
    fail) warn "True Peak" "${TP} dBTP" "≤ -1.0 dBTP — clipping digital pós-normalização" ;;
    *)    warn "True Peak" "não detectado" "verificar manualmente" ;;
  esac
fi

# ═══════ RESUMO ══════════════════════════════════════════════════
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESUMO${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
printf "  ${GREEN}✅ OK:    %d checks${NC}\n"  "$PASS"
printf "  ${YELLOW}⚠️  Aviso: %d checks${NC}\n" "$WARN"
printf "  ${RED}❌ Falha: %d checks${NC}\n"  "$FAIL"
echo ""

if   (( FAIL > 0 )); then
  echo -e "  ${RED}${BOLD}RESULTADO: REPROVADO${NC}"
  echo -e "  ${RED}${FAIL} violação(ões) crítica(s) → recompressão garantida${NC}"
  echo ""
  exit 1
elif (( WARN > 0 )); then
  echo -e "  ${YELLOW}${BOLD}RESULTADO: APROVADO COM RESSALVAS${NC}"
  echo -e "  ${YELLOW}${WARN} aviso(s) → revisar antes do upload${NC}"
  echo ""
  exit 0
else
  echo -e "  ${GREEN}${BOLD}RESULTADO: APROVADO — conformidade total${NC}"
  echo -e "  ${GREEN}Upload seguro para Instagram${NC}"
  echo ""
  exit 0
fi
