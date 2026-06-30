# Artifact Diagnosis — Diagnóstico de Artefatos Pós-Encode

Guia sistemático de causa → diagnóstico → solução para artefatos visuais
que aparecem após encode ou após recompressão do Instagram.

---

## Como usar este guia

1. Identificar o artefato visualmente (tabela rápida abaixo)
2. Ir à seção correspondente
3. Confirmar causa com o comando de diagnóstico
4. Aplicar a correção no próximo encode

---

## Tabela rápida de identificação

| O que você vê | Artefato | Seção |
|---|---|---|
| Blocos quadrados visíveis em movimento | Blocking | [→ Blocking](#blocking) |
| Faixas de cor em gradientes (céu, bokeh, skin) | Banding | [→ Banding](#banding) |
| Ruído em zigue-zague nas bordas | Mosquito noise | [→ Mosquito noise](#mosquito-noise) |
| Cintilação entre frames em zonas estáticas | Temporal shimmer | [→ Temporal shimmer](#temporal-shimmer) |
| Highlights brancos viram cinza ou cortam abruptamente | Highlight clipping | [→ Clipping](#highlight-clipping) |
| Pele com aspecto plástico / sem textura | Waxy skin | [→ Waxy skin](#waxy-skin) |
| Sombras com ruído amplificado | Shadow noise amp | [→ Shadow noise](#shadow-noise-amplificado) |
| Vídeo escurece / ilumina visivelmente entre cuts | Color inconsistency | [→ Color shift](#color-shift-pós-upload) |
| Lip sync fora ou drift acumulado | A/V sync drift | [→ Sync drift](#av-sync-drift) |

---

## Blocking

**Aparência:** blocos 8×8 ou 16×16 pixels visíveis, especialmente em movimento rápido
ou fundos com gradiente. Piora muito pós-recompressão Instagram.

**Diagnóstico:**
```bash
# Medir bitrate real frame a frame nos primeiros 30s
ffprobe -v quiet -select_streams v:0 \
  -read_intervals "%+00:00:30" \
  -show_entries frame=pkt_size,pict_type \
  -of csv=p=0 "$FILE" 2>/dev/null | \
  awk -F',' '{size+=$1; frames++} END {printf "Bitrate médio: %.0f kbps\n", (size*8/30)/1000}'
```

**Causas e soluções:**

| Causa | Diagnóstico | Solução |
|---|---|---|
| Bitrate insuficiente para complexidade | bitrate médio real < 70% do target | Aumentar `-b:v` ou usar 2-pass |
| GOP muito longo (P-frames acumulando erro) | MAX_GOP > 60 no validate_encode.sh | Reduzir `keyint` para 60 |
| AQ-mode inadequado | aq-mode=0 ou aq-strength muito baixo | `aq-mode=3:aq-strength=0.8–1.0` |
| rc-lookahead curto demais | rc-lookahead < 40 | Aumentar para 60 |

**Correção típica:**
```bash
# Se blocking em fundos (fundo desfocado, céu)
-x264-params "aq-mode=3:aq-strength=1.0:rc-lookahead=60"

# Se blocking em movimento (dança, véu)
-b:v 10000k -maxrate 11200k  # verificar se estava sub-alocado
```

---

## Banding

**Aparência:** faixas de cor discretas em gradientes suaves — céu, bokeh de fundo,
skin tone em iluminação difusa. Mais visível em telas OLED.

**Diagnóstico:**
```bash
# Verificar profundidade de bits e range de luma
ffprobe -v quiet -select_streams v:0 \
  -show_entries stream=pix_fmt,bits_per_raw_sample \
  -of csv=p=0 "$FILE"
# yuv420p,8 → 8-bit, banding é esperado em gradientes se compressão for alta
```

**Causas e soluções:**

| Causa | Solução |
|---|---|
| Compressão agressiva em zona de gradiente | Aumentar `aq-strength` para 0.9–1.0 |
| LUT com curva muito abrupta em meias-tonalidades | Suavizar a curva da LUT nos midtones |
| `deblock` padrão muito agressivo | `-x264-params "deblock=-1,-1"` |
| Source já com banding (8-bit LUT aplicada em edição) | Adicionar dithering no export do NLE antes do encode |

**Correção para skin banding (gradiente de pele):**
```bash
# Dithering via noise mínimo antes do encode (quebra os planos de cor)
-vf "...,noise=alls=2:allf=t+u,scale=1080:1920:flags=lanczos,fps=30"
# noise=2 é imperceptível mas quebra o banding
```

**Correção para banding em céu / bokeh:**
```bash
-x264-params "aq-mode=3:aq-strength=1.0:psy-rd=1.0,0"
```

---

## Mosquito Noise

**Aparência:** ruído em "zigue-zague" ou halo vibratório ao redor de bordas nítidas
(texto, anel de aliança, sobrancelhas). Piora muito em cabelo contra fundo claro.

**Diagnóstico visual:** pausar o vídeo em frame com borda nítida e zoom 200%. Se
houver pixels alternando em 1–2 pixels ao redor da borda, é mosquito noise.

**Causa:** o encoder x264 alocou bits insuficientes para bordas de alta frequência.

**Soluções:**
```bash
# Aumentar subme para melhor análise de bordas
-x264-params "subme=9:me=umh"

# psy-rd ajuda em bordas (aumentar levemente)
-x264-params "psy-rd=1.1,0"

# Se mosquito persiste: leve blur nas bordas de alta frequência via unsharp (paradoxal mas funciona)
-vf "unsharp=lx=3:ly=3:la=-0.3,..."  # la negativo = leve suavização de bordas
```

---

## Temporal Shimmer

**Aparência:** cintilação ou "pulsação" em zonas estáticas entre frames — fundos
sólidos, paredes, céu. Especialmente visível em slow playback.

**Diagnóstico:**
```bash
# Medir variância temporal entre frames consecutivos
ffmpeg -i "$FILE" \
  -vf "tblend=all_mode=difference,signalstats=stat=tout" \
  -f null - 2>&1 | grep "TAVG" | head -10
# TAVG alto em zonas que deveriam ser estáticas = temporal noise
```

**Causas e soluções:**

| Causa | Solução |
|---|---|
| Noise temporal no source (luz AC pulsante) | `hqdn3d` com temporal alto: `hqdn3d=1.5:1.5:3.5:2.5` |
| AQ-mode redistribuindo bits entre frames | Reduzir `aq-strength` para 0.7 |
| Flickering de fonte de luz no set | `deflicker=size=5:mode=am` antes do hqdn3d |
| rc-lookahead curto (encoder não "vê" o shimmer) | `rc-lookahead=60` |

**Correção padrão para recepção noturna com shimmer:**
```bash
-vf "deflicker=size=5:mode=am,hqdn3d=1.5:2.5:3.5:2.5,..."
```

---

## Highlight Clipping

**Aparência:** vestido branco, véu, janelas abertas ou spots de luz viram cinza
neutro sem detalhe, ou têm borda abrupta (cliff) sem rolloff.

**Diagnóstico:**
```bash
# Verificar YHIGH no source antes do encode
ffprobe -f lavfi \
  -i "movie=${SOURCE},signalstats" \
  -show_entries frame_tags=lavfi.signalstats.YHIGH \
  -of csv=p=0 2>/dev/null | \
  awk '{if($1>235) count++; total++} END {printf "Frames com clipping: %d/%d (%.1f%%)\n", count, total, count/total*100}'
```

- `YHIGH > 235` em mais de 10% dos frames → rolloff obrigatório antes do encode

**Soluções:**
```bash
# Rolloff suave (cerimônia, luz difusa)
-vf "curves=r='0/0 0.87/0.85 1.0/0.96':g='0/0 0.87/0.85 1.0/0.96':b='0/0 0.87/0.85 1.0/0.96',..."

# Knee agressivo (luz direta, flash, janela aberta)
-vf "curves=master='0/0 0.75/0.75 0.85/0.83 1.0/0.95',..."

# Se clipping vem do source já clipado (LUT exportou acima de 235):
# Verificar color pipeline no NLE — LUT deve ser aplicada antes do export
```

---

## Waxy Skin

**Aparência:** pele com aspecto plástico, sem poro ou textura, como se fosse
uma máscara. Resultado direto de denoise excessivo.

**Diagnóstico:**
```bash
# Medir VMAF com e sem denoise num clipe de 5s com close de rosto
# Se VMAF sem denoise > VMAF com denoise → denoise está removendo detalhe real
bash scripts/measure_vmaf.sh source_5s.mp4 encoded_with_denoise_5s.mp4 1
bash scripts/measure_vmaf.sh source_5s.mp4 encoded_without_denoise_5s.mp4 1
```

**Causas e soluções:**

| Causa | Solução |
|---|---|
| BM3D sigma muito alto (>0.07 em cena com close) | Reduzir para 0.04–0.05 |
| hqdn3d luma_spatial > 4 com pessoa em close | Reduzir para ≤ 2.5 |
| vaguedenoiser threshold > 3.0 em skin | Reduzir para 1.5–2.0; usar `method=hard` |
| Dois filtros de denoise em série excessivos | Usar apenas um filtro |

**Regra para close de rosto:** VMAF com denoise deve ser ≥ VMAF sem denoise.
Se cair, o denoise está removendo textura real — reduzir parâmetros.

---

## Shadow Noise Amplificado

**Aparência:** ruído aumentado nas sombras pós-encode ou pós-upload Instagram.
O encoder aloca poucos bits em zonas escuras, o ruído "explode" na recompressão.

**Diagnóstico:**
```bash
# Verificar YLOW no source
ffprobe -f lavfi \
  -i "movie=${SOURCE},signalstats" \
  -show_entries frame_tags=lavfi.signalstats.YLOW \
  -of csv=p=0 2>/dev/null | \
  awk '{if($1<16) count++; total++} END {printf "Frames com crush: %d/%d\n", count, total}'
```

**Soluções:**
```bash
# Levantar levemente as sombras antes do encode (evita zona de bits escassos)
-vf "curves=master='0/0 0.05/0.07 1.0/1.0',..."
# 0.05 IRE → 0.07 IRE: levanta sombras ~2% — imperceptível mas evita shadow crush

# aq-strength mais alto força bits nas sombras também
-x264-params "aq-mode=3:aq-strength=0.9"
```

---

## Color Shift Pós-Upload

**Aparência:** vídeo no Instagram tem cor diferente do preview local — shift de
saturação, hue levemente diferente, ou contraste alterado.

**Diagnóstico:**
```bash
# Verificar tags de colorimetria no arquivo enviado
ffprobe -v quiet -select_streams v:0 \
  -show_entries stream=color_primaries,color_transfer,color_space \
  -of csv=p=0 "$FILE"
# Qualquer "unknown" → Instagram aplica conversão implícita
```

**Causas e soluções:**

| Causa | Solução |
|---|---|
| Tags de cor ausentes | Adicionar `-color_primaries bt709 -color_trc bt709 -colorspace bt709` |
| Source tagueado como BT.601 | `-vf "colormatrix=bt601:bt709,..."` antes de qualquer outro filtro |
| LUT fora de gamut (saída além de [0,1]) | Adicionar `lutrgb=r='clip(val,0,1)':g='clip(val,0,1)':b='clip(val,0,1)'` após a LUT |
| Export do NLE em color space errado | Verificar configuração de export: deve ser BT.709 / sRGB |

---

## A/V Sync Drift

**Aparência:** áudio e vídeo começam sincronizados mas derivam progressivamente.
Em Reels longos (≥60s) pode chegar a 0.5s de drift.

**Diagnóstico:**
```bash
# Verificar se source tem timebase inconsistente
ffprobe -v quiet -select_streams v:0,a:0 \
  -show_entries stream=codec_type,time_base,r_frame_rate,start_time \
  -of csv=p=0 "$FILE"
# start_time diferentes entre audio e video → causa de sync drift
```

**Soluções:**
```bash
# Forçar sync no início do encode
ffmpeg -i input.mp4 -vsync cfr -async 1 [demais parâmetros] output.mp4
# -vsync cfr: força frame rate constante (elimina VFR drift)
# -async 1: corrige sync de áudio de forma suave

# Se source tem VFR (variable frame rate — comum em footage de smartphone):
ffmpeg -i input.mp4 -vf "fps=30" [demais] output.mp4
# fps=30 no início do vf chain garante CFR antes do encode
```

---

## Checklist de diagnóstico pós-encode

```bash
# 1. Rodar validador técnico
bash scripts/validate_encode.sh output.mp4

# 2. Medir VMAF
bash scripts/measure_vmaf.sh source.mp4 output.mp4 5

# 3. Verificar signalstats (highlights e sombras)
ffprobe -f lavfi -i "movie=output.mp4,signalstats" \
  -show_entries frame_tags=lavfi.signalstats.YHIGH,lavfi.signalstats.YLOW \
  -of csv=p=0 2>/dev/null | \
  awk -F',' '{
    if($1>235) hi++
    if($2<16) lo++
    total++
  } END {
    printf "Highlight clipping: %.1f%% dos frames\n", hi/total*100
    printf "Shadow crush:       %.1f%% dos frames\n", lo/total*100
  }'
```
