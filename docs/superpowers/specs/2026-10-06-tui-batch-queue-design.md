# P3D — Batch de pasta na TUI — Design

Data: 2026-10-06 · Status: aprovado em conversa, aguardando revisão do arquivo
Ciclo: P3D (Phase 3, sub-projeto 3 de 4: P3B casca+encode ✓ → P3C configuração ✓ → **P3D batch** → P3E acabamento). Inclui o achado **P3CF1** (ffprobe sem timeout).
Referências: `docs/Phase_2_TUI_Specification.md` §C, §D.3, §I, §J, §L, §M, §S, §T, §V; `docs/superpowers/specs/2026-10-05-tui-config-screens-design.md` (P3C); `docs/superpowers/specs/2026-10-01-tui-shell-encode-design.md` (P3B); `.claude/memory/FINDINGS.md` § "Ciclo P3C". `RE` = `Reels_Encoder_v2_FINAL.py`, `D` = `ui/tui_driver.py`, `R` = `reporter.py`.

## 1. Objetivo e critério de sucesso

`python -m ui.tui` passa a rodar batch de pasta: preset 3 e o ramo "Pasta" do preset 5, de HOME até um relatório final da fila, em tela cheia. O ffprobe usado no SOURCE deixa de poder congelar a TUI.

Pronto quando:

1. **Paridade**: para as mesmas escolhas, a TUI produz o mesmo `Namespace` (`EncodeConfig.to_namespace()`) que o wizard de linha nos cenários batch (§7.4).
2. Testes automáticos verdes no CI Windows e Linux; suíte completa sem regressão.
3. Manual no Windows Terminal (§7.6) passa.
4. Motor (`RE`), `D.run_batch`, `reporter.py`, `ui/launcher.py`, `ui/config.py` inalterados. Única mudança fora de `ui/tui/`: timeout em `ui/probe.py` (P3CF1).

## 2. Decisões fechadas

| ID | Decisão |
|----|---------|
| B-1 | A TUI executa a fila chamando `D.run_batch` (já existente desde o P3A) e consumindo seus eventos. Nada de laço próprio sobre `run_single`. |
| B-2 | Tela QUEUE **reduzida** (opção B): tabela da fila em cima + painel do job ativo reaproveitando a tela ENCODING do P3B embaixo. Sem ↑↓/D/L por job. |
| B-3 | Pasta existente sem vídeos **bloqueia** no SOURCE ("⚠ nenhum vídeo encontrado"; ENTER não avança). READY revalida antes do START. |
| B-4 | Relatório final = contadores + tabela final com o motivo resumido de cada falha. ENTER sai. Sem abrir log por job. |
| B-5 | Cancelar (`C`, modal do P3B, mesma trava em MCTF/QC) cancela a **fila inteira**; Ctrl+C → 130. Sem pular job individual. |
| B-6 | P3CF1: `probe_source_dims` com `timeout=10` s; estouro → `None` ("—"). Vale também para o wizard (mesma função). |
| B-7 | Códigos de saída do motor: 0 ok, 1 se algum job falhou, 2 validação, 130 interrompido. |

## 3. Fluxo

```text
HOME ─3─▶ SOURCE (pasta) ─▶ CONFIGURATION (BATCH) ─▶ PREVIEW ─▶ READY ─▶ QUEUE ─▶ REPORT
HOME ─5─▶ SOURCE [Arquivo | Pasta] ─▶ ADVANCED (+ pasta de saída se Pasta) ─▶ PREVIEW ─▶ READY ─▶ QUEUE | ENCODING (P3B)
ESC: mesmas regras do P3C (rascunho mantido, sem ciclos); REVISAR do PREVIEW vale também em batch.
```

Trilho em batch: `HOME › SOURCE › CONFIG › PREVIEW › READY › QUEUE › REPORT` (Phase 2 §C).

## 4. Módulos

| Arquivo | Mudança |
|---------|---------|
| `ui/tui/forms.py` | `ENABLED_PRESETS = (1, 2, 3, 4, 5)`; formulário `BATCH` (preset 3); campos de pasta de saída na aba Source do ADVANCED visíveis só com Pasta; `new_draft(3)` = `EncodeConfig.preset_batch(...)` (difere dos padrões só em `batch`). |
| `ui/tui/state.py` | SOURCE com tipo Pasta; seletor TIPO no preset 5; novos estados QUEUE e REPORT; tabela de jobs; consumo de `QueueInit/JobStart/JobSkip/JobDone/QueueDone`. |
| `ui/tui/screens.py` | SOURCE (pasta), CONFIGURATION BATCH, PREVIEW/READY com "pasta · N vídeos", QUEUE, REPORT. |
| `ui/tui/app.py` | `check_source` aceita pasta; `arm` batch; `start` chama `run_batch` (injetável); resumo de saída da fila. |
| `ui/probe.py` | `timeout=10` no `check_output` (P3CF1). |

## 5. Formulários (espelho do wizard)

Fonte: `ui/launcher.py` `_flow_batch` 141–148 e `_flow_advanced` 172–186.

| Form | Campos (ordem do wizard; rótulos verbatim sem "?" final) |
|------|---------------------------|
| BATCH (preset 3; base `EncodeConfig.preset_batch(pasta)`) | Definir pasta de saída separada (toggle, padrão off) · Pasta de saída `output_dir` (caminho; visível só com o toggle on; não precisa existir) · Usar film look (Cineon) `cineon_pipeline` (padrão off) |
| ADVANCED com Pasta (preset 5) | Aba Source ganha, antes dos campos atuais: Pasta de saída separada (toggle) · Pasta de saída `output_dir` (visível só com o toggle on). Demais abas inalteradas. |

Regras:
- (a) O toggle "pasta de saída separada" é estado de formulário, não campo de `EncodeConfig`: off ⇒ `output_dir = None`; on ⇒ `output_dir` = caminho digitado (aspas removidas como no SOURCE). On com caminho vazio ⇒ erro inline "Informe a pasta de saída." e não avança.
- (b) SOURCE preset 5: seletor TIPO "Arquivo único / Pasta (batch)" (←→). A troca só alterna entre `input` e `batch` no rascunho (o outro vira `None`) e revalida o caminho; nenhuma outra edição é perdida. Como `preset_batch` é igual aos padrões salvo `batch`, isso mantém a paridade com o wizard.
- (c) Em arquivo único, `output_dir` fica sempre `None` (o motor rejeita `--output-dir` sem `--batch`).
- (d) Validação por `EncodeConfig.model_validate` como no P3C.

## 6. Telas

- **HOME**: preset 3 ativo, sem "chega no P3D"; rodapé com `[1-5]`.
- **SOURCE (§I)**: rótulo PASTA quando o tipo é Pasta. Status:
  - `VALID` — "✓ pasta encontrada · N vídeos" (contagem via `RE.find_video_files`, não recursivo, mesmas extensões e exclusões do motor).
  - `EMPTY` — "⚠ nenhum vídeo encontrado" (bloqueia).
  - `NOT_FOUND` / `INVALID` (vazio ou arquivo quando se espera pasta, e vice-versa) — como hoje.
  - PROGRAM: moldura padrão com "pasta · N vídeos" (sem probe de dimensões).
  - Preset 5: linha TIPO focável no topo do SOURCE.
- **CONFIGURATION BATCH (§J)**: mesma estrutura do P3C (faixa de resumo, formulário, PADRÕES somente leitura, CONTINUAR).
- **PREVIEW / READY (§L, §M)**: "pasta · N vídeos" e saída ("mesma pasta" ou o caminho). READY revalida pasta existente e com vídeos (C-5 do P3C) antes do START.
- **QUEUE (nova; §T reduzida)**:
  - Faixa: `BATCH <pasta> · N arquivos ▸ saída: <mesma pasta|caminho>`.
  - Tabela RENDER QUEUE (título `Job n de N · ETA mm:ss`): JOB · ARQUIVO (elidido) · STATUS (mapa D.3) · ETA/DURAÇÃO (ativo: "…"; concluído: duração; aguardando: —) · RESULTADO (ok: "ok"; pulado: "saída já existe"; falha: 1ª linha do erro; interrompido: "interrompido"). Rola para manter o job ativo visível quando N passa das linhas disponíveis.
  - ETA da fila: média das durações concluídas × jobs restantes; "—" antes do primeiro concluído.
  - Painel inferior: corpo da tela ENCODING do P3B para o job ativo (estágio, passes, progresso, log), zerado a cada `JobStart`. Medidor EBU suprimido (motor).
  - Teclas: `C` cancelar fila (modal P3B), `Ctrl+C`, mais as que a tela ENCODING já oferece para o job ativo e que não exigem seleção de job.
- **REPORT (nova; §V reduzida)**: contadores — Sucesso N/T · Pulados · Falhas · Interrompidos · Tempo total · Código de saída — e a tabela final da fila. ENTER sai.
- Mapa de status (Phase 2 §D.3): aguardando `· QUEUED` · processando `ENCODING` (spinner) · ok `✓ COMPLETED` · pulado `○ SKIPPED` · falha `✗ FAILED` · interrompido `⚡ CANCELLED`.
- Regras do P3B/P3C valem: 120×40, nenhuma linha > 120 colunas, sem emoji nas regiões fixas (D-20), rodapé só com teclas válidas.

## 7. Estado, eventos, App

1. **Estado**: `UIState` ganha `queue: tuple[Job, ...]` (`input`, `output`, `status`, `started`, `finished`, `reason`), `active_job: int | None`, `queue_started`, `is_batch`.
2. **Eventos** (`R`, já emitidos por `run_batch`):
   - `QueueInit(jobs)` → monta a tabela, tela QUEUE.
   - `JobStart(i)` → job *i* ENCODING; zera campos do job ativo (estágio, passes, progresso, log, QC, erro).
   - `JobSkip(i, reason)` / `JobDone(i, status, error)` → atualiza a linha (status, duração, motivo).
   - Eventos de motor do job ativo continuam alimentando o painel inferior.
   - `Error` durante a fila → só motivo da linha; não vai para ERROR.
   - `Error` antes do `QueueInit` (validação → 2, pasta sumiu → 1) → tela ERROR do P3B.
   - `QueueDone(code)` / `Finished(code)` em batch → REPORT (0, 1 ou 130).
3. **App**:
   - `check_source`: pasta → `VALID` com contagem / `EMPTY` / `NOT_FOUND` / `INVALID`; arquivo → como hoje.
   - `arm`: com Pasta monta `batch` + `output_dir`; sem saída de arquivo único.
   - `start`: com Pasta revalida (existe e tem vídeos; senão `ReadyBlocked`), depois `run_batch(ns, queue, control, tick)` (injetável como `run_single`).
   - Proteção do ENTER isolado no READY (P3C) vale igual.
   - Resumo impresso ao sair: `✓ fila: 9 ok · 2 pulados · 1 falha (código 1)`; interrompida: `⚠ fila interrompida: …`.
4. **P3CF1**: `subprocess.check_output(..., timeout=10)`; `TimeoutExpired` → `None` (o `check_output` encerra o processo filho).

## 8. Testes

1. Reducer: cada evento da fila e o mapa de status; job ativo zerado a cada `JobStart`; erro de job não vai para ERROR; erro antes da fila vai; cancelamento → REPORT com ⚡; navegação presets 3 e 5-Pasta (TIPO, bloqueio `EMPTY`, toggle de pasta de saída e erro de caminho vazio).
2. Telas 120×40: SOURCE pasta (VALID/EMPTY/NOT_FOUND), CONFIGURATION BATCH (pasta de saída visível/oculta), QUEUE com 3 e 20 jobs (rolagem), REPORT com falha e com interrompidos; ≤ 120 colunas; sem emoji.
3. App: ponta a ponta com `run_batch` falso (HOME → preset 3 → REPORT) com códigos 0, 1 e 130; READY bloqueia pasta esvaziada; resumo impresso.
4. **Paridade com o wizard** (`ui/tui/test_parity_wizard.py`): preset 3 só pasta; preset 3 com pasta de saída e Cineon; preset 5-Pasta com pasta de saída.
5. P3CF1: ffprobe falso que demora mais que o timeout → `None` rápido.
6. Manual no Windows Terminal (pasta de teste: 3 clipes curtos, 1 com saída já existente, 1 arquivo quebrado): preset 3 até o REPORT; preset 5-Pasta com pasta de saída separada; pasta sem vídeos bloqueando; `C` no meio da fila; Ctrl+C → 130, sem ffmpeg órfão.

## 9. Fora de escopo

↑↓/D/L por job e log de falha no REPORT (B-2, B-4); veredito de QC na coluna RESULTADO e barra de progresso por linha (exigem seam do motor); subpastas; pular job individual; demais achados P3E; qualquer mudança no motor, `run_batch`, `reporter.py`, `ui/launcher.py`, `ui/config.py`.
