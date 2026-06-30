# x264-params — Sintaxe Canônica de Serialização

Referência única para montar a string `-x264-params` sem o bug recorrente de
**colon vs. vírgula**. Sempre que derivar parâmetros manualmente, conferir aqui.

---

## A regra em uma frase

Dentro de `-x264-params "..."`:

- O separador **entre parâmetros** é **dois-pontos** `:`
- Alguns valores carregam **sub-argumentos separados por vírgula** `,`
- `zones` ainda usa **barra** `/` para separar zonas distintas
- **Nenhum valor pode conter `:`** (senão o parser quebra o token)

```
chave1=valor : chave2=val_a,val_b : zones=s,e,b=m/s,e,b=m
        └ ':' separa params   └ ',' sub-args   └ '/' separa zonas
```

---

## Tabela canônica dos parâmetros usados

| Parâmetro | Forma correta | Sub-args | Armadilha |
|---|---|---|---|
| `ref` | `ref=4` | — | — |
| `bframes` | `bframes=2` | — | — |
| `b-adapt` | `b-adapt=2` | — | precisa `bframes>0` |
| `trellis` | `trellis=2` | — | — |
| `mixed-refs` | `mixed-refs=1` | — | precisa `ref>1` |
| `aq-mode` | `aq-mode=3` | — | — |
| `aq-strength` | `aq-strength=0.8` | — | — |
| `me` | `me=umh` | — | — |
| `subme` | `subme=8` | — | — |
| `rc-lookahead` | `rc-lookahead=60` | — | — |
| `keyint` | `keyint=60` | — | hard cap Instagram = 60 |
| `min-keyint` | `min-keyint=1` | — | — |
| `scenecut` | `scenecut=40` | — | — |
| `vbv-init` | `vbv-init=0.90` | — | **é param x264**, nunca flag FFmpeg |
| **`deblock`** | `deblock=-1,-1` | **vírgula** (alpha,beta) | ❌ `deblock=-1:-1` quebra o parse |
| **`psy-rd`** | `psy-rd=1.0,0` | **vírgula** (rd,trellis) | ❌ `psy-rd=1.0:0` quebra o parse |
| **`zones`** | `zones=0,89,b=1.30/90,200,b=0.80` | **vírgula** dentro + **barra** entre | ranges ascendentes, sem overlap |

> Os três últimos (`deblock`, `psy-rd`, `zones`) são as **únicas exceções** que
> carregam vírgula. Todo o resto é só `chave=valor` colado com `:`.

---

## Contrato de serialização (referência)

`build_ffmpeg_cmd()` em `scripts/analyze_source.py` já implementa isto. Forma
canônica do stack premium + GOP + (opcional) zones:

```python
x264_opts = (
    "ref=4:bframes=2:b-adapt=2:trellis=2:mixed-refs=1"
    f":aq-mode=3:aq-strength={aq}"
    f":me=umh:subme={subme}:rc-lookahead={rcla}"
    f":deblock={deblock}"              # deblock já vem como "-1,-1" (vírgula)
    f":keyint={keyint}:min-keyint=1:scenecut={scenecut}"
    f":vbv-init={vbv_init}"
)
if psy_rd > 0:
    x264_opts += f":psy-rd={psy_rd},0"           # sub-arg vírgula
if zones:
    x264_opts += f":zones={zones}"               # vírgula interna + barra
```

---

## Auto-checagem antes de emitir

Heurística de sanidade (com a ressalva de que `zones` legitimamente quebra a
regra "um `=` por token", por conter `b=` internos):

```python
def assert_x264_sane(opts: str) -> None:
    for tok in opts.split(":"):
        assert ":" not in tok, f"valor com ':' proibido: {tok}"
        key = tok.split("=", 1)[0]
        if key in ("deblock", "psy-rd", "zones"):
            continue                      # exceções que carregam vírgula/barra
        assert tok.count("=") == 1, f"token malformado: {tok}"
        assert "," not in tok, f"vírgula inesperada em {key}: {tok}"
```

---

## Stack x264 premium — justificativa

Os três parâmetros novos do stack premium (ativos por padrão nos perfis Gabriel,
bitrate 8–11 Mbps onde o alvo é qualidade perceptual, não velocidade):

| Parâmetro | Ganho | Custo |
|---|---|---|
| `trellis=2` | RD trellis em todos os MBs — melhor quantização, menos banding | encode ~10–20% mais lento |
| `b-adapt=2` | placement ótimo de B-frames (busca exaustiva) | análise de B um pouco mais cara |
| `mixed-refs=1` | seleção de referência por partição 8×8 | marginal |

Manter `aq-mode=3:aq-strength=0.8` como base; `aq-strength` continua derivado
adaptativamente (ver `references/adaptive-analysis.md`).
