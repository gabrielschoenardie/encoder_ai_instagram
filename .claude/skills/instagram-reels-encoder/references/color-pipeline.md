# Color Pipeline — LUT 3D, BT.709, Highlights

Referência de cor para o `Reels_Encoder_v2_FINAL.py`.
O color pipeline varia por modo — **usar `analyze_source.py` para derivar
automaticamente** qual modo, qual LUT e se rolloff é necessário.

---

## Dois modos, dois pipelines de cor

| | FFmpeg Mode | Cineon Mode |
|---|---|---|
| Processamento | 8-bit YUV, filtros FFmpeg | float32 RGB, PyAV + NumPy |
| LUT padrão | `HollywoodCinema_Ultimate_v6.7B_`<br>`1.5IRE_Instagram8bit_NeutralShadows.cube` | `FilmLook_Portra400_`<br>`SkinPriority_D65.cube` |
| Pipeline | `denoise → rolloff? → lut3d → scale → fps` | 5 nós: DWG → tone map → gamut → Cineon log → LUT |
| Rolloff | `curves` filter adaptativo (derivado de `highlight_load`) | Nó 2 — S-curve Hable adaptativa |
| Referência técnica | Este arquivo | `references/cineon-pipeline.md` |

> Para o Cineon Mode completo (fórmulas, colour-science API, código por nó):
> ver **`references/cineon-pipeline.md`**.

---

## Seleção automática via analyze_source.py

```bash
python scripts/analyze_source.py input.mp4
```

O script deriva automaticamente:
- Modo recomendado (FFmpeg ou Cineon) com razões
- LUT a usar
- Rolloff (knee point e knee output calculados de `highlight_load`)
- Chain `-vf` completo pronto para copiar

**Nunca definir o pipeline de cor manualmente** sem antes rodar a análise —
a seleção de rolloff em particular depende de `highlight_load` medido.

---

## Fundamentos: Color Space no Instagram

Instagram ingere e exibe em **BT.709**. O arquivo entregue deve ter as três
tags de colorimetria corretas, caso contrário o player aplica conversão implícita.

### Tags obrigatórias no output (ambos os modos)

```bash
-color_primaries bt709 \
-color_trc bt709 \
-colorspace bt709
```

Estas tags são metadados — não convertem cor. A conversão real ocorre via
filtros ou LUT.

### Source fora de BT.709

```
Source em BT.601 (NTSC/PAL legado)
    → -vf "colormatrix=bt601:bt709,..."

Source com tags erradas (tagueado como bt601 mas é bt709)
    → -vf "colorspace=all=bt709:iall=bt601:fast=1,..."

Source em Log (S-Log, C-Log, V-Log)
    → Cineon Mode recomendado (analyze_source.py escalará automaticamente)
    → No FFmpeg Mode: LUT de conversão log→BT.709 antes de qualquer denoise
```

---

## LUT 3D — FFmpeg Mode

### HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube

- **1.5 IRE**: ponto de negro neutro — sem crushing de sombras, detalhe preservado
- **Instagram8bit**: calibrada para o pipeline de ingestão do Instagram; a curva
  tonal sobrevive à recompressão sem perda de saturação percetível
- **NeutralShadows**: sem lift artificial de sombras — o que se exporta é o que aparece

```bash
# Aplicação padrão no FFmpeg Mode
-vf "...,lut3d=HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube:interp=tetrahedral,..."
```

### Interpolação de LUT

| Método | Uso |
|---|---|
| `tetrahedral` | **sempre** — mais preciso, custo mínimo |
| `trilinear` | nunca em produção — erro visível em LUTs com curvas agressivas |
| `pyramid` | apenas para debug/comparação |

---

## Rolloff de Highlights — FFmpeg Mode

O `analyze_source.py` deriva o rolloff automaticamente de `highlight_load`.
Se precisar ajustar manualmente, a fórmula é:

```python
# De derive_rolloff() em analyze_source.py
kp = max(0.75, 0.92 - highlight_load * 0.8)   # knee point
ko = max(0.90, 0.97 - highlight_load * 0.15)   # knee output
```

```bash
# Rolloff derivado (exemplo com highlight_load=0.12)
# kp=0.824  ko=0.952
-vf "curves=r='0/0 0.824/0.824 1.0/0.952':\
g='0/0 0.824/0.824 1.0/0.952':\
b='0/0 0.824/0.824 1.0/0.952',..."
```

**Quando NÃO aplicar rolloff:** `highlight_load < 0.05` — o `analyze_source.py`
retorna `None` nesse caso e o filtro não é inserido no chain.

---

## Validação de Gamut — signalstats

```bash
# Verificar distribuição de luma no source ANTES do encode
ffprobe -f lavfi -i "movie=input.mp4,signalstats" \
  -show_entries frame_tags=lavfi.signalstats.YHIGH,lavfi.signalstats.YLOW \
  -of csv=p=0 2>/dev/null | \
  awk -F',' '{
    if($1>235) hi++
    if($2<16)  lo++
    total++
  } END {
    printf "Highlight clipping: %.1f%% dos frames\n", hi/total*100
    printf "Shadow crush:       %.1f%% dos frames\n", lo/total*100
  }'
```

- `YHIGH > 235` em mais de 5% dos frames → rolloff obrigatório antes do encode
- `YLOW < 16` em mais de 20% dos frames → shadow lift no Cineon Mode Nó 2

---

## Validação de Cor Pós-Encode

```bash
# Verificar tags de colorimetria — já coberto pelo validate_encode.sh
bash scripts/validate_encode.sh output.mp4   # inclui check das 3 tags BT.709

# Manual (se necessário fora do validador)
ffprobe -v quiet -select_streams v:0 \
  -show_entries stream=color_primaries,color_transfer,color_space \
  -of csv=p=0 output.mp4
# Esperado: bt709,bt709,bt709
# Qualquer "unknown" → risco de conversão implícita no Instagram
```

---

## Referência cruzada rápida

| Necessidade | Ir para |
|---|---|
| Pipeline completo automatizado | `scripts/analyze_source.py` |
| Cineon Mode — 5 nós, fórmulas, colour-science | `references/cineon-pipeline.md` |
| Selecionar FFmpeg vs Cineon Mode | `references/encoder-modes.md` |
| Blocking, banding, color shift pós-upload | `references/artifact-diagnosis.md` |
| LUFS, conformidade Instagram | `references/instagram-ingest-rules.md` |
