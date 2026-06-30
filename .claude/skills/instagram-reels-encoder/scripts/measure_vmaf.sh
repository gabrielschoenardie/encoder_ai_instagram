#!/usr/bin/env bash
# =================================================================
#  measure_vmaf.sh — Medição VMAF pós-encode Instagram Reels
#  Metodologia Gabriel
#  Uso: ./measure_vmaf.sh <source.mp4> <encoded.mp4> [subsample=5]
#
#  subsample 1 = todo frame (preciso, mais lento)
#  subsample 5 = 1 a cada 5 frames (padrão — 5x mais rápido)
#  subsample 10 = verificação rápida durante iteração
# =================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; NC='\033[0m'

SOURCE="${1:-}"; ENCODED="${2:-}"; SUBSAMPLE="${3:-5}"
# Modelo VMAF: NEG (No Enhancement Gain) por padrão — não premia sharpening/
# contraste/denoise, então o score reflete fidelidade real e não pode ser inflado.
# Override: VMAF_MODEL=vmaf_v0.6.1 ./measure_vmaf.sh ... (se o build não tiver o NEG)
VMAF_MODEL="${VMAF_MODEL:-vmaf_v0.6.1neg}"

if [[ -z "$SOURCE" || -z "$ENCODED" ]]; then
  echo ""
  echo "  Uso: $0 <source.mp4> <encoded.mp4> [subsample]"
  echo ""
  echo "  subsample 1  → todo frame, mais preciso"
  echo "  subsample 5  → padrão (5x rápido, suficiente para produção)"
  echo "  subsample 10 → rascunho rápido"
  echo ""
  exit 1
fi

for f in "$SOURCE" "$ENCODED"; do
  [[ ! -f "$f" ]] && { echo -e "${RED}Arquivo não encontrado: $f${NC}"; exit 1; }
done

# Verificar se libvmaf está disponível
if ! ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
  echo ""
  echo -e "${RED}${BOLD}ERRO: libvmaf não encontrado no FFmpeg${NC}"
  echo ""
  echo "  Instalar FFmpeg com suporte a libvmaf:"
  echo "  Ubuntu/Debian: sudo apt install ffmpeg libvmaf-dev"
  echo "  macOS:         brew install ffmpeg"
  echo "  Ou compilar FFmpeg com --enable-libvmaf"
  echo ""
  exit 1
fi

# Detectar duração do encoded para selecionar perfil
DURATION=$(ffprobe -v quiet -show_entries format=duration \
    -of csv=p=0 "$ENCODED" 2>/dev/null || echo "0")
DURATION_INT=$(python3 -c "print(round(float('${DURATION:-0}')))" 2>/dev/null || echo "0")

if   (( DURATION_INT <= 30 )); then TARGET=93; PROFILE="Maximum Quality (≤30s)"
elif (( DURATION_INT >= 40 )); then TARGET=90; PROFILE="Safe Premium (≥40s)"
else                               TARGET=90; PROFILE="Zona de Transição (30–40s)"; fi

# Arquivo de log com timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOGFILE="/tmp/vmaf_${TIMESTAMP}.json"

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  VMAF — Metodologia Gabriel${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "  Source:    ${BOLD}$(basename "$SOURCE")${NC}"
echo -e "  Encoded:   ${BOLD}$(basename "$ENCODED")${NC}"
echo -e "  Duração:   ${BOLD}${DURATION_INT}s${NC} → perfil: ${BOLD}${PROFILE}${NC}"
echo -e "  Target:    ${BOLD}VMAF ≥ ${TARGET}${NC}"
echo -e "  Subsample: 1 a cada ${BOLD}${SUBSAMPLE}${NC} frame(s)"
echo -e "  Modelo:    ${VMAF_MODEL}  (NEG = sem ganho por sharpening/denoise)"
echo ""
echo -e "  ${YELLOW}Calculando... (pode levar alguns minutos)${NC}"
echo ""

# VMAF: encoded = distorted (input 0), source = reference (input 1)
# Ambos escalados para 1080:1920 para garantir mesma resolução.
# Nota: vmaf_v0.6.1 foi treinado em conteúdo 1920x1080; scores em 1080x1920
# são comparativamente válidos mas podem diferir ~0.5–1.5 pontos absolutos.
FFMPEG_LOG=$(ffmpeg -y \
  -i "$ENCODED" \
  -i "$SOURCE" \
  -lavfi "[0:v]setpts=PTS-STARTPTS,scale=1080:1920:flags=lanczos[dist];\
[1:v]setpts=PTS-STARTPTS,scale=1080:1920:flags=lanczos[ref];\
[dist][ref]libvmaf=model=version=${VMAF_MODEL}:\
log_fmt=json:\
log_path=${LOGFILE}:\
n_subsample=${SUBSAMPLE}:\
n_threads=4" \
  -f null - 2>&1)

# Verificar se o log foi gerado
if [[ ! -f "$LOGFILE" ]]; then
  echo -e "${RED}${BOLD}ERRO: VMAF não calculado.${NC}"
  echo ""
  echo "  Possíveis causas:"
  echo "  → libvmaf instalado mas modelo ${VMAF_MODEL} não encontrado (tente VMAF_MODEL=vmaf_v0.6.1)"
  echo "  → Resolução incompatível entre source e encoded"
  echo "  → Duração diferente entre os arquivos"
  echo ""
  echo "  Saída FFmpeg:"
  echo "$FFMPEG_LOG" | tail -10
  exit 1
fi

# Parse do JSON de resultado
RESULT=$(python3 - "$LOGFILE" << 'PYEOF'
import json, sys

path = sys.argv[1]
with open(path) as f:
    d = json.load(f)

# Suporta múltiplos formatos de output do libvmaf
try:
    m = d['pooled_metrics']['vmaf']
    mean = m['mean']
    vmin = m.get('min', mean)
    vmax = m.get('max', mean)
    hm   = m.get('harmonic_mean', mean)
except (KeyError, TypeError):
    # Formato legado
    mean = d.get('VMAF score', d.get('vmaf', 0))
    vmin = mean; vmax = mean; hm = mean

# Score mínimo do pior frame (identifica cenas problemáticas)
try:
    frames = d.get('frames', [])
    frame_scores = [fr['metrics']['vmaf'] for fr in frames if 'metrics' in fr and 'vmaf' in fr['metrics']]
    if frame_scores:
        vmin = min(frame_scores)
        vmax = max(frame_scores)
        # Identificar frames mais críticos
        worst_frames = sorted(
            [(i, fr['metrics']['vmaf']) for i, fr in enumerate(frames) if 'metrics' in fr and 'vmaf' in fr['metrics']],
            key=lambda x: x[1]
        )[:3]
        worst_str = ', '.join([f"frame {i} ({s:.1f})" for i, s in worst_frames])
    else:
        worst_str = 'N/A'
except Exception:
    worst_str = 'N/A'

print(f"{mean:.2f}|{vmin:.2f}|{vmax:.2f}|{hm:.2f}|{worst_str}")
PYEOF
)

IFS='|' read -r VMAF_MEAN VMAF_MIN VMAF_MAX VMAF_HM WORST_FRAMES <<< "$RESULT"
VMAF_INT=$(python3 -c "print(round(float('${VMAF_MEAN:-0}')))" 2>/dev/null || echo "0")
DIFF=$((VMAF_INT - TARGET))

# ── RESULTADOS ───────────────────────────────────────────────────
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESULTADOS VMAF${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "  Score médio:     ${BOLD}${VMAF_MEAN}${NC}"
echo -e "  Score mínimo:    ${BOLD}${VMAF_MIN}${NC}  ← frame mais crítico"
echo -e "  Score máximo:    ${BOLD}${VMAF_MAX}${NC}"
echo -e "  Harmonic mean:   ${BOLD}${VMAF_HM}${NC}  ← penaliza quedas pontuais"
echo ""
echo -e "  Target (${PROFILE}): ${BOLD}≥ ${TARGET}${NC}"
echo ""

if   (( VMAF_INT >= TARGET    )); then
  echo -e "  ${GREEN}${BOLD}✅  QUALIDADE: APROVADA${NC}"
  echo -e "  ${GREEN}VMAF ${VMAF_MEAN} ≥ ${TARGET} — encode preserva qualidade perceptual${NC}"
elif (( VMAF_INT >= TARGET - 3 )); then
  echo -e "  ${YELLOW}${BOLD}⚠️   QUALIDADE: MARGINAL${NC}"
  echo -e "  ${YELLOW}VMAF ${VMAF_MEAN} — ${DIFF#-} ponto(s) abaixo do target${NC}"
else
  echo -e "  ${RED}${BOLD}❌  QUALIDADE: REPROVADA${NC}"
  echo -e "  ${RED}VMAF ${VMAF_MEAN} — perda perceptual significativa${NC}"
fi

# Diagnóstico automático se abaixo do target
if (( VMAF_INT < TARGET )); then
  echo ""
  echo -e "${BOLD}  Diagnóstico:${NC}"
  if (( VMAF_INT < 85 )); then
    echo "  → Bitrate insuficiente para complexidade da cena"
    echo "  → Ou denoise excessivo (BM3D sigma muito alto)"
    echo "  → Ou clipping de highlights no color pipeline"
    echo "  → Ação: aumentar target bitrate ou reduzir sigma BM3D"
  elif (( VMAF_INT < TARGET - 1 )); then
    echo "  → aq-strength pode estar baixo para a cena"
    echo "  → Tentar aq-strength 0.9–1.0 (atual: 0.8)"
    echo "  → Ou considerar 2-pass para redistribuição de bits"
    echo "  → Verificar se denoise removeu detalhe de pele/textura"
  fi
  echo ""
  echo -e "  ${YELLOW}Frames mais críticos: ${WORST_FRAMES}${NC}"
fi

echo ""
echo -e "  Log completo: ${BOLD}${LOGFILE}${NC}"

# ── VMAF por segundo (timeline) ──────────────────────────────────
SEGMENT_DATA=$(python3 - "$LOGFILE" "$ENCODED_DUR" << 'PYEOF'
import json, sys

try:
    path = sys.argv[1]
    dur  = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    with open(path) as f:
        d = json.load(f)

    frames = d.get('frames', [])
    if not frames:
        sys.exit(0)

    fps = len(frames) / dur if dur > 0 else 30.0
    by_sec: dict = {}
    for i, fr in enumerate(frames):
        v = fr.get('metrics', {}).get('vmaf')
        if v is not None:
            sec = int(i / fps)
            by_sec.setdefault(sec, []).append(v)

    for sec in sorted(by_sec):
        mean = sum(by_sec[sec]) / len(by_sec[sec])
        print(f"{sec}:{mean:.1f}")
except Exception:
    pass
PYEOF
)

if [[ -n "$SEGMENT_DATA" ]]; then
  echo ""
  echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  VMAF POR SEGUNDO${NC}"
  echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"

  while IFS=':' read -r seg score; do
    [[ -z "$seg" || -z "$score" ]] && continue

    score_int=$(python3 -c "print(round(float('$score')))" 2>/dev/null || echo "0")
    bar_len=$(( score_int / 5 ))
    bar=$(python3 -c "
n = $bar_len
print('█' * min(n, 20) + '░' * max(0, 20 - n))
" 2>/dev/null || printf '░%.0s' {1..20})

    if   (( score_int >= TARGET     )); then color="$GREEN"
    elif (( score_int >= TARGET - 3 )); then color="$YELLOW"
    else                                    color="$RED"; fi

    printf "  %3ds  ${color}%s${NC}  %s\n" "$seg" "$bar" "$score"
  done <<< "$SEGMENT_DATA"

  # Identificar segmentos críticos abaixo do target
  CRITICAL=$(python3 -c "
data = '''$SEGMENT_DATA'''.strip().split()
critical = []
for line in data:
    if ':' in line:
        sec, score = line.split(':')
        if float(score) < $TARGET:
            critical.append(f'{sec}s ({score})')
if critical:
    print('Segmentos abaixo do target: ' + ', '.join(critical))
" 2>/dev/null)

  if [[ -n "$CRITICAL" ]]; then
    echo ""
    echo -e "  ${YELLOW}${CRITICAL}${NC}"
  fi
fi

echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo ""

# Exit code reflete aprovação
(( VMAF_INT >= TARGET )) && exit 0 || exit 1
