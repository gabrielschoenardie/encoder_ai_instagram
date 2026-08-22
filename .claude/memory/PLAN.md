<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AF: teto da LUT para 96 IRE, piso intocado

Data: 2026-08-22 | Ciclo: AF | Origem: pedido direto do usuário (bounded). Sucede o Ciclo AE (LUT W80), que fica **fechado e aprovado** — ver `STATE.md`.

## Diagnóstico

Medição do output real (13 frames, plano Y sem conversão de range) contra os
dois diagnósticos de `references/artifact-diagnosis.md`:

| diagnóstico | limiar | fonte | com W80 |
| --- | --- | --- | --- |
| shadow crush (`YLOW < 16`) | qualquer | `0.043%` | `0.006%` |
| highlight clipping (`YHIGH > 235`) | >10% frames | `0.137%` | `0.003%` |

Nenhum dos dois é problema hoje. O piso está em `22` cod (2.74 IRE medido,
3.14 IRE teórico) — **6 níveis de colchão** sobre o preto legal, dimensionado
certo. O teto está em `220` cod (93.15 IRE) — **15 níveis** abaixo de 235, mais
que o dobro do necessário, custando ~7 IRE de range de highlight sem benefício
protetivo.

Decisão do usuário: **subir o teto para 0.96 (96 IRE), não mexer no piso.**

`instagram-ingest-rules.md` não documenta nada sobre IRE, piso ou teto — as 193
linhas foram verificadas. Nível de luma **não** é gatilho de recompressão. Esta
mudança é sobre sobreviver melhor à recompressão, não sobre evitá-la.

## Transformação (especificação exata, não reinterpretar)

Duas etapas, **nesta ordem**. A ordem importa: expandir depois de atenuar
reaqueceria as altas e desfaria o invariante 7 do Ciclo AE.

```
# etapa 1 — expansao de teto, lift ADITIVO guiado pela luma
P, HIo, HIn = 0.75, 0.921569, 0.96
k  = (HIo - P) / (HIn - P)
L  = 0.2126*R + 0.7152*G + 0.0722*B          # luma do cube v6.7B
t  = clip((L - P) / (HIo - P), 0, None)
L' = P + (HIn - P)*(k*t + (1-k)*t*t)   se L > P;   L' = L caso contrario
E  = v + (L' - L)                             # somado IGUALMENTE aos 3 canais

# etapa 2 — atenuacao warm 20%, um lado so (identica ao Ciclo AE)
dw = (E - i) · w                              # w = (1,0,-1)/sqrt(2)
F  = clip(E - 0.20*max(dw,0)*w, 0.031373, 0.96)
```

**O lift é aditivo e igual nos três canais — não é curva por canal.** Uma curva
por canal expande croma junto com luma: medido, deixaria 11.593 nós mais quentes
que a W80 (até +9.2 níveis) e 5.655 mais quentes que a própria v6.7B, além de
subir green-magenta de `0.7146` para `0.7267`. O lift aditivo preserva **todas**
as diferenças de croma exatamente. A quadrática tem `g(0)=0`, `g(1)=1`,
`g'(0)=k` — derivada contínua no pivô, monotônica.

**Pivô `P = 0.75`:** é o mais baixo com efeito exatamente zero abaixo dele, e
espalha os +3.84 IRE por ~17 IRE de range. Pivôs altos concentram o mesmo ganho
numa faixa estreita — rampa íngreme, banding em gradiente de céu e pele em
8-bit. Não trocar por um pivô mais alto "para reaquecer menos": com lift aditivo
não há reaquecimento a evitar.

**Valores medidos e verificados pelo Orquestrador. Os testes casam com estes
números; se a medição divergir, PARAR e reportar — não recalibrar.**

| métrica | valor |
| --- | --- |
| teto | `0.960000` (96.00 IRE) |
| piso | `0.031373` (3.14 IRE) — idêntico à v6.7B |
| nós no clamp | `0` |
| nós mais quentes que a v6.7B | `0` |
| ganho warm-cool | `0.790686` (W80: `0.790588`) |
| ganho green-magenta | `0.714632` — idêntico à v6.7B |
| saturação média acima do pivô | `0.43519` (W80: `0.43511`) |
| eixo neutro | `R=G=B` em todos os 33 degraus; topo `96.00` IRE |

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AF1 | Escrever este `PLAN.md`. | Orquestrador | `.claude/memory/PLAN.md` | **done** |
| AF2 | Estender `tools/generate_hollywood_lut_cooler.py` com a etapa 1 (constantes `PIVO=0.75`, `TETO_NOVO=0.96` no topo, parametrizáveis) e assar `HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube`. TDD: asserts da AF3 primeiro. | `executor-pesado` | gerador + cube novo | pendente |
| AF3 | Testes: os 8 asserts atuais adaptados ao envelope novo, mais **INV 9** (nós com `L <= 0.75` intocados pela etapa 1, tolerância zero), **INV 10** (curva de expansão estritamente monotônica no eixo neutro) e **INV 11** (nenhum nó mais quente que a v6.7B — agora `0`, não mais "relativo à base expandida"). | `executor-pesado` | `tools/test_generate_hollywood_lut_cooler.py` | pendente |
| AF4 | Trocar referências do filename W80 para o v6.8 nos 5 arquivos de produto + 4 da skill. **Rodar sozinha, sem agente concorrente** (ver lição do Ciclo AE). | `executor` | `Reels_Encoder_v2_FINAL.py`, `pyproject.toml`, `README.md`, `tools/verificador_instalacao.py`, `.claude/skills/**` | pendente |
| AF5 | A/B próprio com `Captions_C32BA2.mp4`. **Esta mudança mexe em luma** — ao contrário do Ciclo AE, VMAF vai se mover e tem de ser medido, não presumido. Medir também `YHIGH>235` no output novo: o colchão cai de 15 para ~9 níveis e isso precisa de evidência, não de aposta. | `encode-validator` | `.claude/memory/STATE.md` | **done** — 19 ✅ / 1 ⚠ / 0 ❌; `Y>235` pico por-frame `0.08275%` contra gatilho de `>10%` — clipping **não** se materializou, teto mantido em 0.96; piso intocado (`0.00634%` vs `0.00644%`); VMAF `94.90` mas ver correção de leitura em `STATE.md`; achado `AFF1` |

## Notas de execução

- **Ordem é normativa.** Etapa 1 antes da etapa 2. Inverter reaquece as altas.
- **O piso não muda.** `0.031373` entra no clamp como constante e o assert de
  piso compara contra a v6.7B com tolerância zero. Decisão explícita do usuário.
- **Nome novo corrige a mentira herdada.** O filename dizia `1.5IRE` e o piso
  medido é 3.14 IRE — errado desde a v6.7B. O nome novo (`3.1-96IRE`) declara
  piso e teto reais. Se o usuário preferir outro nome, é troca de string.
- **A W80 e a v6.7B permanecem no repo** para A/B e rollback.
- **Anti-escopo:** não mexer no piso, no modo Cineon, na Portra400, em CAS,
  dither, ODT, áudio, bitrate, GOP ou container. Sem knob de CLI — `ui/launcher.py`
  não muda e o `ui-flow-reviewer` não entra.
- **Lição do Ciclo AE, respeitar:** duas tarefas de escrita concorrentes no mesmo
  checkout colidem no `git add`. AF2/AF3 juntas, depois AF4 sozinha, depois AF5.
- Baseline a preservar: `python -m pytest test_render_queue.py enhance/ ui/ -q`
  → `395 passed`.
- Retorno do agente: ponteiro + veredito, uma linha por ID + SHA.
