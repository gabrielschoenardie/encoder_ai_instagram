# VBV Rate Control — Parâmetros e Decisão CRF vs 2-Pass

---

## Arquitetura VBV para Instagram

O VBV (Video Buffering Verifier) é o mecanismo central de controle de bitrate para
garantir conformidade com o ingestor Instagram sem picos que forcem recompressão.

### Parâmetros VBV explicados

```
-b:v <target>k      → bitrate médio alvo (ABR target)
-maxrate <max>k     → pico máximo permitido em qualquer janela VBV
-bufsize <buf>k     → tamanho do buffer VBV (janela de suavização)
```

> **vbv-init** NÃO é flag FFmpeg — é parâmetro x264, sempre dentro de `-x264-params "...:vbv-init=0.90"`

**Relação maxrate/bufsize:** define a janela temporal de controle.
- bufsize = maxrate × 1s → controle muito rígido (1 segundo de janela)
- bufsize = maxrate × 1.5s → recomendado para Reels (equilíbrio)
- bufsize > maxrate × 2s → muita liberdade → risco de pico

**vbv-init = 0.90** → buffer começa 90% cheio. Previne pico imediato no primeiro frame
(cold start). Valor padrão Gabriel.

---

## Perfis Gabriel — Valores Exatos

### Maximum Quality (≤ 30s)
```
-b:v 10000k -maxrate 11200k -bufsize 15000k \
-x264-params "ref=4:bframes=2:aq-mode=3:aq-strength=0.8:me=umh:subme=8:rc-lookahead=60:vbv-init=0.90"
```
- Razão maxrate/target: 1.12 (12% headroom)
- Razão bufsize/maxrate: 1.34s de janela
- VMAF target: ≥ 93

### Safe Premium (≥ 40s)
```
-b:v 8000k -maxrate 9000k -bufsize 12500k \
-x264-params "ref=4:bframes=2:aq-mode=3:aq-strength=0.8:me=umh:subme=8:rc-lookahead=60:vbv-init=0.90"
```
- Razão maxrate/target: 1.125
- Razão bufsize/maxrate: 1.39s de janela
- VMAF target: ≥ 90

### Zona de Transição (30–40s)
```
-b:v 9000k -maxrate 10000k -bufsize 13500k \
-x264-params "ref=4:bframes=2:aq-mode=3:aq-strength=0.8:me=umh:subme=8:rc-lookahead=60:vbv-init=0.90"
```

---

## Quando Usar CRF vs 2-Pass vs ABR+VBV

### ABR + VBV (padrão Gabriel — Reels de produção)
```bash
-b:v 10000k -maxrate 11200k -bufsize 15000k
```
**Usar quando:**
- Produção final para Instagram
- Controle de bitrate máximo é crítico
- Conformidade com ceiling de ingestão

**Vantagem:** bitrate previsível, conformidade garantida, encode em single-pass rápido.
**Desvantagem:** não garante qualidade uniforme em cenas de complexidade variável.

---

### 2-Pass + VBV (qualidade máxima em conteúdo longo)
```bash
# Pass 1
ffmpeg -i input.mp4 -c:v libx264 -b:v 8000k -maxrate 9000k -bufsize 12500k \
  -pass 1 -an -f null /dev/null

# Pass 2
ffmpeg -i input.mp4 -c:v libx264 -b:v 8000k -maxrate 9000k -bufsize 12500k \
  -pass 2 [demais parâmetros] output.mp4
```
**Usar quando:**
- Reel ≥ 40s com cenas de complexidade muito variável (corte rápido + cena estática)
- Orçamento de bits precisa ser redistribuído com inteligência
- Tempo de encode não é crítico

**Vantagem:** distribuição de bits muito mais eficiente, VMAF mais uniforme ao longo do vídeo.
**Desvantagem:** 2× tempo de encode.

---

### CRF (sem VBV) — apenas para masters / intermediários
```bash
-crf 18 -preset slow
```
**Usar quando:**
- Gerando master para arquivo, não para upload direto
- Source precisará ser re-encoded depois com perfil VBV
- Teste de qualidade base (VMAF comparison)

**NUNCA usar CRF puro para output final Instagram** — bitrate pode explodir em cenas
complexas e ultrapassar o ceiling de ingestão.

---

## Parâmetros x264-params Recomendados

```
-x264-params "ref=4:bframes=2:b-adapt=2:trellis=2:mixed-refs=1:aq-mode=3:aq-strength=0.8:me=umh:subme=8:rc-lookahead=60:vbv-init=0.90"
```

| Parâmetro | Valor | Justificativa |
|---|---|---|
| ref | 4 | Max para Level 4.0 — melhor compressão sem violar limite |
| bframes | 2 | Equilíbrio compressão/compatibilidade |
| **b-adapt** | **2** | Placement ótimo de B-frames (busca exaustiva) — stack premium |
| **trellis** | **2** | RD trellis em todos os MBs — menos banding, melhor quantização |
| **mixed-refs** | **1** | Seleção de referência por partição 8×8 — ganho marginal, custo baixo |
| aq-mode | 3 | AQ com variância — preserva detalhes em skin tones |
| aq-strength | 0.8 | Moderado — agressivo demais introduz banding (derivado adaptativamente) |
| me | umh | Melhor motion estimation sem custo proibitivo |
| subme | 8 | Sub-pixel ME de alta qualidade (derivado: 7–9) |
| rc-lookahead | 60 | 2 segundos de lookahead a 30fps — melhora alocação de bits |
| vbv-init | 0.90 | Previne cold-start burst |

> **Stack premium** (`b-adapt=2:trellis=2:mixed-refs=1`): justificado nos bitrates
> 8–11 Mbps onde o alvo é qualidade perceptual máxima, não velocidade. Custo: encode
> ~10–20% mais lento. Sintaxe e contrato de serialização: `references/x264-param-syntax.md`.

> **Alocação de bits por shot:** quando o source tem cortes (não single-take), o
> encoder injeta `:zones=...` automaticamente para dar mais bits aos shots complexos
> e menos aos estáticos, preservando o orçamento global. Ver
> `references/segment-bit-allocation.md`.

---

## Diagnóstico de Problemas de Rate Control

### Bitrate real muito abaixo do target
- Source simples (pouco movimento, fundo sólido) — normal
- Verificar se `rc-lookahead` está alto o suficiente
- Se problemático: aumentar `aq-strength` para forçar uso de bits

### Picos acima do maxrate
- Reduzir `vbv-init` para 0.7
- Aumentar `bufsize` em 10%
- Verificar se `rc-lookahead` é proporcional ao GOP

### VMAF abaixo do target com bitrate OK
- Problema de aq-mode — tentar aq-mode=2
- Verificar denoise excessivo (BM3D muito agressivo pode baixar VMAF)
- Revisar color pipeline — clipping de highlights reduz VMAF artificialmente

---

## GOP Structure — Otimização Adaptativa de Keyframes

O GOP (Group of Pictures) define a frequência de I-frames. Para Instagram Reels,
é um parâmetro crítico: GOP longo = melhor compressão mas pior seeking e mais
risco de propagação de erro pós-recompressão.

> **A partir da Metodologia Gabriel:** o GOP não é mais fixo. `analyze_source.py`
> executa um **Pass-1 leve** via `ffprobe` antes do encode, mede a estrutura real
> de cortes do source e deriva `keyint`, `scenecut` e `force_key_frames`
> automaticamente via `derive_gop()`. Nunca definir GOP manualmente sem antes
> rodar a análise.

### Regras Instagram para GOP

| Parâmetro | Valor obrigatório | Impacto |
|---|---|---|
| Keyframe interval máximo | 60 frames (2s a 30fps) | Seeking e recompressão |
| Keyframe interval mínimo | 1 frame (I-only) | Ineficiente, apenas em looping |
| Hard cap do derive_gop() | 60 frames | Nunca viola a regra, mesmo em single_take |

---

### Pass-1: analyze_cut_structure()

Antes de derivar qualquer parâmetro, `analyze_source.py` chama `ffprobe` para
extrair os timestamps reais de todos os I-frames do source:

```python
# O que analyze_cut_structure() mede:
{
    "cut_count":          12,      # cortes reais detectados
    "mean_cut_interval":  1.83,    # intervalo médio entre I-frames (s)
    "min_cut_interval":   0.73,    # menor intervalo — anchor do keyint
    "max_cut_interval":   4.10,    # maior intervalo
    "cut_regularity_cv":  0.42,    # coeficiente de variação (0=regular, >0.5=irregular)
    "rhythm":             "irregular",  # "regular" | "irregular" | "single_take"
}
```

**Por que isso importa:** o `scenecut` do x264 detecta cortes reativamente, frame
a frame. Com a estrutura de cortes medida antes, o encoder entra no Pass-2 já
sabendo o ritmo real do material — keyint calibrado, sem heurística genérica.

---

### derive_gop() — Três camadas de decisão

```
Camada 1: ritmo medido
  single_take        → keyint=60 (máxima eficiência)
  regular (CV<0.35)  → keyint = mean_interval arredondado (≤60)
  irregular (CV≥0.35)→ keyint = min_interval × 1.2 com headroom

Camada 2: motion + complexidade
  motion > 20 px/frame → comprimir GOP para ≤1.5s
  motion < 3 + single_take → GOP máximo 2.0s

Camada 3: tipo de conteúdo
  skin_ratio > 0.30 + spatial_complexity < 30 → GOP moderado (protege textura de pele)
```

---

### Três estratégias de aplicação

| Estratégia | Quando | Parâmetros gerados |
|---|---|---|
| `fixed` | Cortes regulares (CV < 0.20) | `keyint=N:scenecut=40` (sem force_key_frames) |
| `scenecut_only` | Single take ou ffprobe indisponível | `keyint=60:scenecut=40` |
| `dual_coverage` | Cortes irregulares (CV ≥ 0.20) | `keyint=N:scenecut=50` + `-force_key_frames "t1,t2,t3,..."` (timestamps do Pass-1) |

**Dual coverage** é a mais robusta: o `scenecut=50` do x264 detecta cortes
internamente, e o `-force_key_frames` injeta os **timestamps reais dos I-frames**
medidos no Pass-1 — garantia determinística de I-frame em cada corte detectado.
A lista é filtrada para excluir bordas (< 0.5s do início/fim) e limitada a 20
timestamps (limite prático do FFmpeg).

> **Por que não `expr:gte(scene,X)`:** essa expressão depende da variável `scene`
> exposta pelo filtro `scdet` ou `select`, o que cria acoplamento entre `-vf` e
> `-force_key_frames`. Timestamps explícitos do Pass-1 são determinísticos,
> não dependem de filtros auxiliares e usam a evidência real do source.

---

### Exemplos de saída por tipo de conteúdo

**Highlight film de casamento (cortes rápidos, irregulares):**
```bash
# CV=0.68, mean_interval=1.2s, motion=18px → dual_coverage
-force_key_frames "1.250,2.500,3.750,5.000,6.250,7.500" \
-x264-params "...keyint=36:min-keyint=1:scenecut=50:vbv-init=0.90"
```

**Cerimônia com planos longos:**
```bash
# CV=0.12, mean_interval=8.5s, motion=2px → scenecut_only
-x264-params "...keyint=60:min-keyint=1:scenecut=40:vbv-init=0.90"
```

**Dança (cortes regulares a cada ~1s):**
```bash
# CV=0.18, mean_interval=1.0s, motion=22px → fixed
-x264-params "...keyint=30:min-keyint=1:scenecut=40:vbv-init=0.90"
```

---

### Verificar GOP após encode

```bash
# Já coberto pelo validate_encode.sh (check GOP)
bash scripts/validate_encode.sh output.mp4

# Manual — intervalo entre I-frames nos primeiros 30s
ffprobe -v quiet -select_streams v:0 \
  -read_intervals "%+00:00:30" \
  -show_entries frame=pict_type,pts_time \
  -of csv=p=0 "$FILE" 2>/dev/null | \
  awk -F',' '$1=="I" {if(NR>1) print pts-last_pts" s"; last_pts=$2; pts=$2}'
```

### scenecut — referência de valores

```
scenecut=0   → desativado (GOP fixo, ignora cortes)
scenecut=40  → padrão (scenecut_only e fixed)
scenecut=50  → sensível (dual_coverage — cortes irregulares)
scenecut=60  → muito sensível — pode I-frame em pan rápido
```
