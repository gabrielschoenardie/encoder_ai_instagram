# PHASE 2 SIGN-OFF / REVIEW RESPONSE
## TUI — encoder_ai_instagram

> **Documento histórico (Fase 2, 30/09/2026).** Apesar do título, este arquivo é o **pedido** (prompt) que encomendou o sign-off da Fase 2 — não a resposta. As decisões D-01…D-21 refletem o plano da época. Superadas pela implementação: D-02 (somente 120×40 → mínimo **80×24**, layout completo em **120×40**), D-09/D-10/D-11 (tecla `C` com confirmação → **Ctrl+C** é a única interrupção), D-19 (sem "Novo encode" → **NOVO ENCODE** existe) e a preservação do wizard de linha como fallback da TUI (o menu clássico foi retirado). **A implementação atual prevalece** — guia de uso em [`tui.md`](tui.md).

Você está trabalhando LOCALMENTE no repositório `encoder_ai_instagram` dentro do VS Code.

A especificação da Phase 2 já foi produzida:

`Phase_2_TUI_Specification.md`

Ela é o documento de referência para o design da TUI.

---

# 0. OBJETIVO DESTA TAREFA

Agora NÃO vamos implementar a TUI.

Precisamos concluir formalmente a **Phase 2 — Design / Specification** antes de autorizar qualquer trabalho da Phase 3.

Sua tarefa nesta etapa é produzir uma revisão técnica chamada:

**Phase 2 Sign-off / Review Response**

Essa revisão deve:

1. registrar as decisões de UX/arquitetura que já estão fechadas;
2. verificar no código existente os pontos marcados como `NEEDS REVIEW`;
3. separar claramente:
   - decisões que já podemos tomar;
   - comportamentos que precisam ser confirmados pelo código;
   - itens que ainda precisam de decisão humana;
4. identificar qualquer inconsistência entre a especificação e o comportamento atual do encoder;
5. definir objetivamente o que precisa estar resolvido para a Phase 3 poder começar;
6. NÃO implementar absolutamente nada.

---

# 1. REGRA MAIS IMPORTANTE: ZERO IMPLEMENTAÇÃO

Esta tarefa é exclusivamente de:

- auditoria;
- leitura;
- verificação;
- comparação;
- documentação;
- tomada de decisão de design quando explicitamente definida abaixo.

NÃO faça:

- alterações no código;
- criação de módulos;
- refatoração;
- criação de `ui/state.py`;
- criação de `ui/events.py`;
- criação de `ui/keys.py`;
- alteração de `_run_encoding`;
- alteração do Cineon;
- alteração do batch;
- alteração do CLI;
- alteração do launcher;
- alteração do `Live`;
- alteração de imports;
- alteração de configurações;
- alteração de argumentos;
- criação de testes;
- execução de migração arquitetural;
- commits;
- criação de branches;
- alteração de arquivos existentes.

Você pode executar comandos de leitura/análise/teste **somente se forem read-only e não modificarem o repositório**.

Se algum teste/comando tiver possibilidade de modificar arquivos, NÃO execute.

Ao final desta tarefa, o repositório deve permanecer exatamente como estava no início.

---

# 2. DOCUMENTOS DE REFERÊNCIA

Leia primeiro:

`Phase_2_TUI_Specification.md`

Não trate memória, suposições ou boas práticas genéricas como fonte de verdade.

A ordem de autoridade é:

1. comportamento real do código existente;
2. `Phase_2_TUI_Specification.md`;
3. decisões explícitas deste prompt;
4. somente depois, inferências técnicas claramente marcadas como inferência.

Não invente comportamento que não esteja comprovado.

Quando algo não puder ser confirmado, escreva:

`NEEDS REVIEW`

e explique exatamente por quê.

---

# 3. CONTEXTO ARQUITETURAL

A arquitetura futura definida pela Phase 2 é:

```text
┌───────────────────────────────┐
│             TUI               │
│ presentation + interaction    │
│ UIState + focus + navigation  │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│      Reporter / Events        │
│ presentation boundary        │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│       EXISTING ENCODER        │
│                               │
│ FFmpeg / x264 / VBV           │
│ Cineon / filters / HDR        │
│ audio / loudnorm              │
│ QC / output / cleanup         │
└───────────────────────────────┘
```

A TUI NÃO deve possuir lógica de encoding.

O encoder existente continua sendo a fonte de verdade.

---

# 4. DECISÕES JÁ FECHADAS

Estas decisões NÃO precisam ser reabertas.

Registre-as no Sign-off como:

`CLOSED DECISION`

## D-01 — Entrada da TUI

A TUI será uma entrada separada do CLI clássico.

Preferência:

```text
python -m ui.tui
```

ou um console script equivalente futuro.

NÃO adicionar `--tui` nesta fase.

Motivo:

- preservar `--help`;
- preservar comportamento do CLI;
- manter o TUI isolado;
- reduzir risco de regressão;
- manter o classic CLI como fluxo independente.

---

## D-02 — Terminal alvo

O design é exclusivamente:

```text
120 × 40
```

Não criar layouts alternativos para:

- 80×24;
- 100×30;
- outros tamanhos.

O comportamento para terminal inadequado deve seguir a especificação existente, mas não criar uma segunda linguagem visual responsiva.

---

## D-03 — Linguagem visual

Preservar integralmente a linguagem Adobe Premiere-inspired já existente.

Não "embelezar" o terminal arbitrariamente.

Preservar:

- palette;
- rounded panels;
- double-box hero states;
- uppercase panel titles;
- active tabs;
- progress bars;
- status indicators;
- quality chips;
- program monitor;
- timeline;
- performance panel;
- log panel;
- delivery seal;
- `MASTER QC`;
- `DELIVERY READY`;
- `REVISAR ENTREGA`.

---

## D-04 — Focus model

Usar o modelo de foco definido na especificação.

Não inventar um novo paradigma de navegação.

---

## D-05 — HOME: teclas 1–5

MANTER.

No HOME:

```text
1 → Encode rápido
2 → Film look
3 → Batch de pasta
4 → Tools
5 → Configurar avançado…
```

Essas teclas preservam o hábito do menu atual.

As setas/foco também permanecem disponíveis conforme a especificação.

Não remover os atalhos numéricos.

---

## D-06 — Prompts condicionais

Prompts que hoje aparecem somente em determinadas condições devem ser representados na TUI como estados/linhas condicionais, conforme especificação.

Não inventar novos campos de configuração.

---

## D-07 — Campos internos não expostos

Não expor na TUI somente por conveniência visual:

- `report`;
- `cineon_lut`;
- `debug`;
- ou outros campos internos que a especificação explicitamente classifica como não expostos.

---

## D-08 — PREVIEW e READY

Continuam sendo telas distintas.

Fluxo:

```text
CONFIGURATION
      ↓
PREVIEW
      ↓
READY TO ENCODE
      ↓
ENCODING
```

Não fundir essas telas.

---

## D-09 — Hotkeys durante encoding

Durante encoding, somente:

```text
D = Details
L = Log
C = Cancel
Ctrl+C = comportamento de interrupt existente
```

NÃO adicionar:

```text
P = Pause
R = Resume
Q = Quit
```

Nem outros atalhos de controle do encoder.

---

## D-10 — Cancelamento

`C` sempre abre confirmação.

`Ctrl+C` NÃO abre confirmação.

`Ctrl+C` deve preservar o caminho de interrupção/cancelamento existente.

A implementação futura deve respeitar isso.

---

## D-11 — QC

O botão/ação `C` fica desabilitado durante QC conforme especificação.

O comportamento exato de `Ctrl+C` durante QC precisa ser verificado no código atual e permanece `NEEDS REVIEW` até essa verificação.

---

## D-12 — Two-pass

Não criar uma porcentagem combinada artificial:

```text
37% overall
```

quando ela não existe de forma confiável.

Mostrar os dois passes individualmente.

Pass 1 permanece visível quando Pass 2 começa.

---

## D-13 — Bitrate

Não inventar campo de bitrate no Details V1 se o dado não estiver disponível naquele momento.

---

## D-14 — Data provenance

Valores apresentados no Details devem indicar origem quando especificado:

```text
CONFIGURED
DETECTED
CALCULATED
LIVE
MEASURED
```

Nunca apresentar dado calculado/inferido como se tivesse vindo diretamente do encoder.

---

## D-15 — Stat lines

Collapse de linhas estatísticas é somente apresentação.

Não alterar os dados do encoder.

---

## D-16 — Cineon

Na TUI futura, Cineon deve ser integrado ao modelo visual unificado.

O classic CLI continua utilizando o comportamento/HUD existente.

Não alterar isso nesta Phase 2.

---

## D-17 — Batch

No TUI, batch utilizará o modelo de queue definido na especificação.

O `Live` aninhado existente NÃO deve ser removido nesta etapa.

A substituição pertence à Phase 3 e somente à TUI.

---

## D-18 — Resultado por job

Batch deve apresentar verdict por job no RESULT.

---

## D-19 — Reuso de processo

Não implementar reutilização do processo para um segundo encode na V1.

---

## D-20 — Layout

Não adicionar:

- emoji em regiões fixas;
- background animation;
- elementos que possam quebrar largura de 120 colunas.

---

## D-21 — Motion

Motion limitado a:

- spinner;
- pulse;
- delivery seal reveal.

Nada mais.

---

# 5. PRESERVAÇÃO ABSOLUTA DO ENCODER

A futura Phase 3 NÃO pode alterar semanticamente:

- output final;
- resolução;
- FPS;
- CFR;
- codec;
- profile;
- pixel format;
- color range;
- BT.709;
- HDR handling;
- LUT;
- Cineon;
- enhancement;
- AI decisions;
- dithering;
- x264;
- VBV;
- bitrate logic;
- 2-pass;
- loudnorm;
- AAC;
- audio processing;
- QC;
- QC verdict rules;
- output naming;
- cleanup;
- partial-output handling;
- stderr capture;
- stderr tail;
- cancellation;
- Ctrl+C;
- exit codes;
- batch behavior;
- `EncodeConfig`;
- defaults;
- cinco workflows;
- classic CLI;
- line wizard.

A TUI será uma nova camada de apresentação/controle.

Não é uma oportunidade para "melhorar" o encoder.

---

# 6. AGORA AUDITE OS 18 NEEDS REVIEW

Leia o código necessário para responder cada item.

Para cada item, produza:

```text
ID
Pergunta
Arquivos/funções verificadas
Comportamento atual confirmado
Evidência
Decisão para Phase 3
Status
```

Use somente estes status:

```text
VERIFIED
CLOSED
NEEDS REVIEW
```

Não use:

```text
probably
likely
I think
should be
presumably
```

sem deixar explicitamente claro que é inferência.

---

# 7. NEEDS REVIEW #1 — ENTRY POINT

Verifique o launcher atual e a arquitetura existente.

Confirmar:

- como o CLI é iniciado;
- como `--help` funciona;
- se existe `launcher.ps1`;
- como seria mais seguro adicionar uma entrada TUI separada.

A decisão de design já está fechada:

```text
SEPARATE TUI ENTRY
```

Portanto, aqui você deve apenas confirmar a forma técnica mais compatível.

Não implemente.

---

# 8. NEEDS REVIEW #2 — ask_path / ask_folder

Verifique:

- `ask_path`;
- `ask_folder`;
- validação;
- diferenciação entre arquivo e pasta;
- mensagens atuais.

Determinar exatamente:

```text
file
folder
invalid
not found
```

Não alterar essas funções.

---

# 9. NEEDS REVIEW #3 — BATCH FOLDER WITH ZERO VIDEOS

Verifique o comportamento atual quando:

```text
pasta válida
+
zero vídeos
```

Determine:

- retorno;
- mensagem;
- erro;
- exit code;
- se o fluxo continua ou termina.

Não alterar.

---

# 10. NEEDS REVIEW #4 — _flow_advanced / preset_batch

Verifique exatamente o comportamento de:

```text
_flow_advanced
preset_batch
```

Especialmente:

- quando batch entra no fluxo advanced;
- se a configuração é resetada;
- quais valores são preservados;
- quais valores são sobrescritos.

Documentar o comportamento atual.

Não decidir uma nova semântica.

---

# 11. NEEDS REVIEW #5 — DISCARDING ADVANCED EDITS

Verifique o comportamento atual quando o usuário:

```text
entra em ADVANCED
↓
edita configuração
↓
sai/volta
```

Determinar se as alterações:

- permanecem;
- são descartadas;
- são restauradas;
- são aplicadas somente no final.

Documentar exatamente.

---

# 12. NEEDS REVIEW #6 — settings_preview

Localize:

```text
settings_preview
```

Liste exatamente as rows atuais.

Não criar rows novas.

Não remover rows.

A Phase 3 deve reproduzir o conjunto atual salvo decisão explícita em contrário.

---

# 13. NEEDS REVIEW #7 — ANALYZING SUB-STEP ORDER

Verifique:

```text
run_ffmpeg
run_ffmpeg_with_cineon
```

e o fluxo real de análise.

Mapear a ordem real de:

- PREPARING;
- PROBING;
- ANALYZING;
- enhancement;
- loudness;
- MCTF;
- pass-1 log;
- adaptive parameters;
- outras etapas existentes.

Não inventar ordem.

Se Native e Cineon forem diferentes, documentar separadamente.

---

# 14. NEEDS REVIEW #8 — NATIVE PASS 1 OUTPUT TARGET

Verifique a chamada FFmpeg real do pass 1 native.

Precisamos saber exatamente:

- output target;
- `-f null`;
- arquivo temporário;
- output real;
- argumentos relevantes.

Não inferir a partir do Cineon.

A especificação explicitamente marcou isso como NEEDS REVIEW.

---

# 15. NEEDS REVIEW #9 — HardwareProfile

Localize:

```text
HardwareProfile
detect_hardware
```

Liste os campos realmente existentes.

Classifique:

```text
AVAILABLE
NOT AVAILABLE
DERIVED
```

Não inventar campos para PERFORMANCE ou DETAILS.

---

# 16. NEEDS REVIEW #10 — VBV_PRESETS

Localize:

```text
VBV_PRESETS
```

Registrar exatamente os labels e valores atuais.

Não renomear.

Não reinterpretar.

Não criar novos presets.

---

# 17. NEEDS REVIEW #11 — get_video_duration 30s fallback

Verifique:

```text
get_video_duration
```

Determinar:

- quando o fallback de 30 segundos acontece;
- se existe flag;
- qual função sabe que houve fallback;
- se esse dado está disponível para a futura UI.

Não inventar evento se ele não existe.

---

# 18. NEEDS REVIEW #12 — terminate_active_ffmpeg / Cineon

Este é um item crítico.

Localize:

```text
terminate_active_ffmpeg
```

e todos os caminhos Cineon.

Determine exatamente:

- quais processos são registrados;
- quais processos são terminados;
- se pass 1 Cineon é interrompido;
- se pass 2 Cineon é interrompido;
- se há processos filhos;
- como cleanup funciona;
- se existe algum processo que não é alcançado.

Não alterar.

A resposta deve ser factual.

---

# 19. NEEDS REVIEW #13 — Ctrl+C DURING QC

Verifique o código atual.

Precisamos saber exatamente:

```text
encoding
↓
QC
↓
Ctrl+C
```

O que acontece?

Determinar:

- handler;
- exception;
- cleanup;
- output final;
- output deletion;
- exit code;
- estado do programa.

Não projetar comportamento novo nesta etapa.

---

# 20. NEEDS REVIEW #14 — PARTIAL OUTPUT AFTER ENCODING ERROR

Verifique os caminhos de erro do encoding.

Determinar:

- quando o output parcial existe;
- se é removido;
- quem remove;
- em quais erros;
- se QC é executado;
- o que acontece após erro de FFmpeg;
- se o comportamento muda entre native/Cineon.

---

# 21. NEEDS REVIEW #15 — SINGLE FILE EXIT CODES

Verifique os códigos reais retornados por:

```text
success
error
interrupt/cancel
```

Verifique:

- `sys.exit`;
- `return`;
- `main`;
- launcher;
- exceptions.

Não definir novos códigos.

A Phase 3 deve preservar os existentes.

---

# 22. NEEDS REVIEW #16 — quality_chip(None)

Localize:

```text
quality_chip
```

e descubra exatamente qual glyph/texto aparece quando:

```text
quality_chip(None)
```

Isso é uma questão de compatibilidade visual.

Não alterar.

---

# 23. NEEDS REVIEW #17 — PROCESS REUSE

Verifique se o sistema atual reutiliza processos entre jobs.

Mesmo que exista algum mecanismo:

NÃO implementar isso na TUI V1.

A decisão é:

```text
NO PROCESS REUSE IN V1
```

O objetivo aqui é apenas registrar o comportamento atual e o risco.

---

# 24. NEEDS REVIEW #18 — WINDOWS CTRL+C / KEY READER

Verifique:

- key reader;
- Windows Terminal;
- stdin;
- console mode;
- Ctrl+C;
- `KeyboardInterrupt`;
- threads;
- signal handling.

Queremos saber se a futura arquitetura:

```text
main thread
+
key reader thread
+
worker
+
Live
```

pode preservar o comportamento atual de Ctrl+C.

NÃO implementar.

Se não puder ser comprovado sem teste manual, marque:

`NEEDS REVIEW — MANUAL WINDOWS TERMINAL TEST REQUIRED`

---

# 25. NÃO MODIFICAR O CLASSIC CLI

Confirme explicitamente na revisão que:

```text
Classic CLI
Line wizard
ResolveProgressHUD
Existing batch Live
```

continuam sendo considerados caminhos preservados.

A futura TUI não deve absorver ou substituir esses fluxos.

---

# 26. TRACEABILITY MATRIX

Depois da auditoria, produza uma tabela:

| ID | Current Code Area | Current Behavior | Future TUI Area | Future Component/Event | Risk | Phase 3 Change |
|---|---|---|---|---|---|---|

Use somente informações verificadas.

---

# 27. DECISION REGISTER

Produza uma tabela final:

| Decision | Status | Decision | Rationale | Code Support | Phase 3 Impact |
|---|---|---|---|---|---|

Inclua:

```text
D-01 → CLOSED
D-02 → CLOSED
D-03 → CLOSED
D-04 → CLOSED
D-05 → CLOSED
D-06 → CLOSED
D-07 → CLOSED
D-08 → CLOSED
D-09 → CLOSED
D-10 → CLOSED
D-11 → parcialmente fechado / comportamento Ctrl+C depende da auditoria
D-12 → CLOSED
D-13 → CLOSED
D-14 → CLOSED
D-15 → CLOSED
D-16 → CLOSED
D-17 → CLOSED
D-18 → CLOSED
D-19 → CLOSED
D-20 → CLOSED
D-21 → CLOSED
```

Se o código contradizer uma dessas decisões, NÃO altere o código.

Reporte a contradição.

---

# 28. OPEN ITEMS AFTER VERIFICATION

Ao terminar a auditoria, crie três categorias:

## CLOSED

Itens totalmente resolvidos.

## VERIFIED

Itens cujo comportamento foi confirmado no código e agora pode ser tratado como fonte de verdade.

## NEEDS REVIEW

Somente aquilo que ainda precisa de:

- decisão humana;
- teste manual;
- informação ausente;
- confirmação adicional.

Não deixe itens como NEEDS REVIEW simplesmente porque são difíceis.

Se o código permitir uma resposta factual, marque VERIFIED.

---

# 29. PHASE 3 ENTRY CRITERIA

Defina critérios objetivos para autorizar a Phase 3.

A Phase 3 só poderá começar quando:

### Architecture

- [ ] TUI entry point fechado
- [ ] TUI separada do classic CLI
- [ ] Reporter/Event boundary definida
- [ ] UIState definida
- [ ] single Live owner definido
- [ ] worker architecture definida

### Behavior

- [ ] cancellation semantics verificadas
- [ ] Cineon cancellation verificada
- [ ] Ctrl+C semantics verificadas
- [ ] QC interruption verificada
- [ ] partial-output cleanup verificado
- [ ] exit codes verificados

### UX

- [ ] 120×40 fechado
- [ ] HOME fechado
- [ ] navigation fechado
- [ ] encoding hotkeys fechado
- [ ] PREVIEW/READY fechado
- [ ] Details fechado
- [ ] Log fechado
- [ ] QC/Delivery fechado
- [ ] Batch fechado conceitualmente

### Preservation

- [ ] encoder behavior preserved
- [ ] FFmpeg semantics preserved
- [ ] VBV preserved
- [ ] x264 preserved
- [ ] Cineon preserved
- [ ] audio preserved
- [ ] QC preserved
- [ ] output naming preserved
- [ ] cleanup preserved
- [ ] classic CLI preserved
- [ ] Ctrl+C preserved
- [ ] exit codes preserved

### Technical Risk

- [ ] Windows Ctrl+C risk understood
- [ ] nested Live risk understood
- [ ] reader-thread behavior understood
- [ ] stderr handling understood
- [ ] cancellation process tree understood

---

# 30. PHASE 3 MUST NOT START IF

Não autorize implementação se existir qualquer dúvida não resolvida sobre:

- FFmpeg command semantics;
- cancellation;
- Cineon process lifecycle;
- Ctrl+C;
- partial output cleanup;
- exit codes;
- classic CLI behavior.

Se algum desses pontos não puder ser determinado pelo código:

```text
NEEDS REVIEW — BLOCKS PHASE 3
```

Se for uma questão puramente visual que não afeta encoder behavior:

```text
NEEDS REVIEW — NON-BLOCKING
```

---

# 31. FINAL OUTPUT

Ao final, produza um documento estruturado exatamente nesta ordem:

# Phase 2 Sign-off / Review Response

## 1. Executive Summary

## 2. Closed Decisions

## 3. Code-Verified Behaviors

## 4. 18 NEEDS REVIEW Audit

## 5. Traceability Matrix

## 6. Design Decision Register

## 7. Remaining NEEDS REVIEW

Separar:

- BLOCKING
- NON-BLOCKING

## 8. Preservation Confirmation

## 9. Phase 3 Entry Criteria

## 10. Phase 3 Authorization Status

O status final deve ser exatamente um destes:

```text
PHASE 3 READY
```

ou

```text
PHASE 3 BLOCKED — NEEDS REVIEW
```

Não escolha `PHASE 3 READY` se existir qualquer blocker.

---

# 32. REGRA FINAL

Depois de produzir a revisão:

**PARE.**

Não implemente nada.

Não faça commit.

Não altere arquivos.

Não crie código.

Não comece a Phase 3.

A única finalidade desta tarefa é transformar:

```text
Phase 2 Specification
+
Current Code Verification
+
Closed Decisions
```

em um **Phase 2 Sign-off tecnicamente confiável**.

Somente depois de eu revisar e aprovar explicitamente esse Sign-off será autorizada a Phase 3.

---

# PRINCÍPIO CENTRAL

> O design define a experiência.
> O código existente define o comportamento.
> A Phase 3 conecta os dois sem alterar o encoder.

Preserve esta separação rigorosamente.
