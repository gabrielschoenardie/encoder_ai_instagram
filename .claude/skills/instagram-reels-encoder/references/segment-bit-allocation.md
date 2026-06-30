# Alocação de Bits por Shot — x264 zones (Módulo Cinema)

Distribui o orçamento de bits de forma desigual entre os shots de um Reel: mais
bits onde a complexidade exige (movimento, textura, detalhe), menos onde o plano
é estático. É o equivalente single-pass do **encode por cena** do cinema —
"premium bit allocation" alinhado ao ritmo real do material, sem custar um pass
adicional, porque a estrutura de cortes **já foi medida** no Pass-1 do GOP.

> Pré-requisito: `analyze_cut_structure()` (Pass-1). Ver
> `references/vbv-rate-control.md` e `references/adaptive-analysis.md` (Etapa 2b/2c).

---

## Princípio

O `-b:v`/VBV define o orçamento **médio**. Sem zones, o x264 distribui esse
orçamento reativamente. Com a estrutura de cortes medida, sabemos onde estão os
shots e podemos **enviesar a alocação por shot antecipadamente**, mantendo o
orçamento global intacto:

```
budget global (–b:v)  ──fixo──►  redistribuído entre shots por demanda
maxrate / bufsize     ──teto rígido──►  conformidade Instagram preservada
```

Zones **não** elevam o pico: o `maxrate`/`bufsize` continua sendo o limite
absoluto de qualquer janela VBV. Zones só move bits *dentro* do orçamento.

---

## Sintaxe x264 zones

```
zones=<start>,<end>,<opção>[/<start>,<end>,<opção>]...
```

- `start`, `end`: números de **frame** (inteiros), inclusivos
- `opção`: usamos `b=<float>` — multiplicador de bitrate do range
  - `b=1.30` → +30% de bits naquele shot
  - `b=0.80` → −20% de bits naquele shot
- Zonas separadas por `/`; dentro da zona, campos por `,`
- **Regras estritas do x264:** ranges ascendentes, sem overlap, dentro de
  `[0, total_frames-1]`. Violar → erro de encode.

Exemplo (Reel 25s @30fps, 750 frames):
```
zones=0,89,b=0.92/90,125,b=1.40/126,269,b=0.85/270,374,b=1.40
```

Dentro do `-x264-params`, é um token colon-level cujo valor carrega `,` e `/`:
```
-x264-params "...:scenecut=50:vbv-init=0.90:zones=0,89,b=0.92/90,125,b=1.40"
```
Ver `references/x264-param-syntax.md`.

---

## Derivação — `derive_zones()`

Implementado em `scripts/analyze_source.py`. Fluxo:

1. **Gate.** Se `single_take`, `fallback`, ou `< 2` cortes → retorna `None`
   (não há shots para diferenciar).
2. **Segmentação.** Constrói segmentos a partir de `cut_timestamps` (Pass-1),
   descartando micro-segmentos `< 0.3s`. Cap em 16 shots para manter a string
   compacta.
3. **Demanda por shot.** Amostra 1 frame no meio de cada segmento e mede
   complexidade espacial (Sobel mean) — barato: 1 seek + 1 decode por shot.
4. **Multiplicadores.** `b` escala com o desvio da demanda em relação à média:
   ```
   mult = 1 + sensitivity * (demanda - média) / média      (sensitivity = 0.55)
   ```
   clampado a **[0.70, 1.40]**.
5. **Preservação de budget.** Duas passagens de normalização ponderada por
   frames garantem que a média ponderada dos multiplicadores ≈ 1.0 — o `-b:v`
   global continua válido. O campo `budget_effective` reporta o valor final
   (alvo ~1.00; ±poucos % é esperado por causa do clamp).
6. **Compactação.** Shots dentro de ±0.04 de 1.0 são omitidos (usam alocação
   default).

### Saída

```python
result.zones_profile
# {
#   "zones": "0,89,b=0.92/90,125,b=1.40/126,269,b=0.85/...",
#   "zone_count": 5,
#   "budget_effective": 0.99,
# }
# ou None quando não aplicável
```

`build_ffmpeg_cmd()` injeta `:zones=...` automaticamente quando
`zones_profile` não é `None`.

---

## Quando NÃO usar zones

| Situação | Motivo |
|---|---|
| `single_take` | um plano só — nada a redistribuir |
| Demanda uniforme entre shots | núcleo retorna `None` (todos ~neutros) |
| `ffprobe` falhou (fallback) | sem estrutura de cortes confiável |
| Reel muito curto com 1–2 cortes | ganho desprezível, string ruidosa |

---

## Interação com outros subsistemas

- **GOP / `force_key_frames`:** independentes. `zones` controla *bits*;
  `force_key_frames` controla *posição de I-frames*. Coexistem sem conflito.
- **VBV:** `maxrate`/`bufsize` continuam o teto. Zones nunca os ultrapassa.
- **2-pass:** com 2-pass, zones fica ainda mais preciso (o pass 1 já conhece a
  complexidade real). Em single-pass + VBV (padrão Gabriel), zones usa a demanda
  amostrada como proxy.

---

## Validação pós-encode

```bash
# Conferir que o bitrate seguiu a intenção: shots complexos devem ter pkt_size
# médio maior. Inspeção por janela:
ffprobe -v quiet -select_streams v:0 \
  -show_entries frame=pkt_size,pict_type,pts_time \
  -of csv=p=0 output.mp4 2>/dev/null | \
  awk -F',' '{w=int($3/1); sz[w]+=$1; n[w]++}
    END{for(s in sz) printf "%3ds  %.0f kbps\n", s, (sz[s]*8/1000)/(n[s]/30)}' | sort -n
```

VMAF por segundo (`measure_vmaf.sh`) deve ficar **mais uniforme** com zones — os
shots que antes despencavam recebem mais bits. Delta entre mean e harmonic mean
deve cair.
