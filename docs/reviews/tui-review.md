# Revisão da TUI — Reels Encoder

> **Como ler este documento.** O corpo é o *snapshot* da auditoria feita sobre `7920e07` em 17/11/2026. Depois dele houve uma única atualização: o **fechamento do R-03**, integrado na `main` pelo PR #82 (`9e30b8b`), que alterou a linha do R-03, a contagem da seção 1, a linha 3 da seção 6 e o histórico. Os demais itens **não foram re-auditados** contra a `main` atual. Para o uso atual da TUI, veja [`../tui.md`](../tui.md).

| Campo | Referência |
|---|---|
| Repositório | [gabrielschoenardie/encoder_ai_instagram](https://github.com/gabrielschoenardie/encoder_ai_instagram) |
| Branch consultada | `main` |
| Commit revisado | [`7920e0713a7c3e958a76cf014b667744b742f853`](https://github.com/gabrielschoenardie/encoder_ai_instagram/commit/7920e0713a7c3e958a76cf014b667744b742f853) |
| Data da revisão | 17/11/2026 |
| Comparação com a revisão anexada | A consulta à `main` retornou o mesmo commit: zero commits de diferença. As mudanças de classificação abaixo resultam da conferência das evidências, não de novas implementações. |
| Método | Leitura do código e dos testes, confronto de `STATE.md`, `FINDINGS.md`, `PLAN.md` e `VALIDATION.md`; duas verificações isoladas de funções extraídas do código. |
| Não executado nesta revisão | Encoder, FFmpeg, launcher real, suíte completa e testes manuais no Windows. |
| Alterações no repositório | Nenhuma durante a auditoria. Este documento atualiza o diagnóstico. |
| Atualização posterior | Fechamento do R-03 (PR #82, `9e30b8b`): implementação, testes automatizados, capturas do harness e validação manual M0–M4 relatada pelo usuário. |

## 1. Resultado consolidado

Dos **20 itens originais**, **15 estão corrigidos, 0 parcialmente corrigidos e 5 permanecem pendentes** (contagem atualizada com o fechamento do R-03; no snapshot de `7920e07` eram 14/1/5).

| Estado | Quantidade | IDs |
|---|---:|---|
| Corrigido no código consultado | 15 | R-01, R-02, R-03, R-04, R-05, R-06, R-07, R-08, R-09, R-10, R-11, R-17, R-18, R-19, R-20 |
| Parcial | 0 | — |
| Pendente | 5 | R-12, R-13, R-14, R-15, R-16 |
| **Total** | **20** | **R-01 a R-20, sem duplicações** |

**“Corrigido” indica implementação presente e evidência consultada. Não significa que todos os cenários foram validados manualmente nesta versão no Windows.** As confirmações manuais são registradas separadamente na seção 6 e não entram como novos IDs nessa contagem.

### Correções importantes em relação ao documento anterior

- **R-03: resolvido → parcial.** A entrada aceita 80×24, mas o renderer e o redutor de teclas ainda exigem 120×40. Não existe suporte compacto funcional demonstrado por essa alteração.
- **R-06: parcial → corrigido, com aprovação manual histórica.** `VALIDATION.md` registra A1–A4 aprovados pelo usuário em 16/11, incluindo FFplay, MCTF e preflight. A anotação anterior de “PENDENTE” no mesmo arquivo foi superada por esse registro. Recomenda-se smoke de regressão após a limpeza subsequente.
- **ABF3, ACF1 e ACF2 já estão corrigidos.** O documento anterior os listava como abertos, embora existam fechamentos posteriores e implementações correspondentes no código atual.
- **N-3: a limpeza P3H já está incorporada na `main`.** C-1 a C-5 têm resultados finais registrados e as mudanças estão presentes no código consultado.
- **N-1 afeta o motor e o helper da TUI.** A substituição frágil do caminho temporário não está restrita ao aviso de recuperação.
- A contagem anterior de “16 resolvidos + 1 parcial + 5 abertos” somava 22. A tabela anterior enumerava 14 resolvidos. A contagem desta versão usa exatamente os 20 IDs originais.

## 2. Ordem recomendada de correção

A ordem abaixo considera impacto na entrega, bloqueio de uso, portabilidade e clareza de diagnóstico. É uma recomendação desta revisão, não uma alteração das severidades históricas de `FINDINGS.md`.

| Ordem | Item | Justificativa | Ação recomendada |
|---|---|---|---|
| **1** | **N-1 — temporário do remux** (adiado por decisão do usuário) | O caminho calculado pode alterar nomes de pastas ou coincidir com a saída quando a extensão é `.MP4`. Afeta o remux e a identificação do arquivo de recuperação. | Substituir a regra nos dois pontos por uma construção consistente baseada em `os.path.splitext`, preferencialmente compartilhada. |
| **2** | **R-03 — mínimo real do terminal** | A entrada aceita uma dimensão em que a HOME não pode ser operada. | Como correção imediata, alinhar a guarda e a ajuda a 120×40. Se 80×24 continuar sendo requisito, implementar layout e navegação compactos antes de anunciá-lo como suportado. |
| **3** | **P3HF2 — FFmpeg da máscara MCTF** | A máscara pode falhar ou usar outro build com instalação portátil ou binário configurado. | Usar o resolvedor de binários adotado pelo motor/TUI, respeitando o caminho configurado. |
| **4** | **P3HF3 — motivo de falha na fila** | O fallback pode transformar um aviso interno da TUI na causa de falha de um job. | Priorizar erro estruturado do job; usar motivo neutro quando não houver causa disponível. |
| **5** | **R-15 — argumentos ignorados** | A entrada da TUI aceita argumentos sem informar que foram descartados. | Rejeitar explicitamente argumentos não suportados, com ajuda e código de erro; pré-preenchimento pode ser um recurso futuro deliberado. |
| **6** | **Acabamento** | Melhorias de comunicação e manutenção com menor impacto funcional. | R-12, R-13, R-14, R-16, P3HF4, contrato de P3HF5, L2F1, L2F2 e descrição de `SkipValidation`. |
| **7** | **Registros e decisões de produto** | Evita retrabalho sobre itens já concluídos e separa decisões de produto de defeitos reproduzíveis. | Consolidar a revisão e os registros; conferir N-2 localmente; definir P3EF2; manter P3BF1 em observação. |

Os testes manuais da seção 6 devem acompanhar o ciclo de correção, com atenção à preservação do master. Eles não devem ser apresentados como já executados.

### Critérios de aceite das cinco primeiras correções

| Item | Aceite mínimo recomendado |
|---|---|
| N-1 | Testar pasta chamada `clips.mp4`, saída `.MP4`, espaços e caminho normal. O temporário permanece ao lado da saída; motor e TUI calculam o mesmo caminho. Simular falha de remux e conferir preservação do master/temporário e aviso com o caminho correto. |
| R-03 | Conferir 80×24, 119×39 e 120×40. Nenhuma dimensão aceita pode abrir uma HOME sem navegação. Resize durante encode preserva execução e Ctrl+C. A ajuda descreve o mínimo efetivamente implementado. |
| P3HF2 | Com PATH sem FFmpeg e binário portátil disponível, a máscara usa o executável resolvido. Cobrir também `REELS_FFMPEG` e a resolução pelo PATH. |
| P3HF3 | Intercalar erro do encoder e WARNING interno antes de `Finished(1)`; o REPORT deve manter a causa real. Cobrir também o caminho normal com `JobDone`, que já usa `ev.error`. |
| R-15 | `--help` explica a entrada. `--input x` e argumento desconhecido não são ignorados silenciosamente. Sem argumentos, a HOME continua abrindo. |

## 3. Situação dos 20 itens originais

| ID | Estado | Resultado da conferência | Evidência principal |
|---|---|---|---|
| R-01 | **Corrigido** | `_cancel_cleanup` consulta `cancel_stage`; em QC/FINALIZING/DONE mantém o master quando presente e seguro. Em QC/FINALIZING remove somente certificados novos. Há testes de conteúdo do master; confirmação específica no Windows ainda necessária. | [Driver, `_cancel_cleanup`][driver]; `ui/test_tui_driver.py::test_ctrl_c_during_qc_keeps_new_master` |
| R-02 | **Corrigido** | Single e batch chamam `_failure_cleanup`. Remove parcial novo após falha, preserva saída preexistente, mantém master em QC/DONE e não apaga arquivos se o temporário for encontrado. Remoção impossível gera aviso. A identificação do temporário continua sujeita a N-1. | [Driver, `_failure_cleanup`][driver]; testes de falha em `ui/test_tui_driver.py` |
| R-03 | **Corrigido — atualização posterior: PR #82 (`9e30b8b`)** | Em `7920e07`: `terminal_ok` aceitava 80×24, mas `MIN_SIZE` era 120×40. Na branch: `MIN_SIZE=(80,24)`, `FULL_SIZE=(120,40)`, layout compacto nas 15 telas abaixo de 120×40 (header/rodapé de 1 linha, rolagem de REPORT/ERROR pela altura), aviso abaixo de 80×24. **Testes automatizados:** suíte completa 1459 passed / 4 skipped antes do último ajuste (LOG/DETAILS); após esse ajuste, `pytest ui` 1012 passed e 17 testes relacionados passed. **Capturas do harness ConPTY (`tests/screens/`):** 80×24, 100×30, 119×39, 120×40, 70×20, resize e fluxos single, ADVANCED, QC, COMPLETED, NOVO ENCODE, ERROR, batch/REPORT. **Validação manual (relato do usuário, 17/11/2026):** M0–M4 aprovados no Windows Terminal real — launcher em 120×40, 80×24 medido com resize durante encode, Ctrl+C no PASS, Ctrl+C no QC e Ctrl+C no QC com relatórios preexistentes. | [Entrada da TUI][entry]; [Estado][state]; [Renderer][screens] |
| R-04 | **Corrigido** | `_check_source` dispara `_source_worker` em thread; o estado PROBING e o resultado chegam pela fila. A latência do probe pode continuar existindo, mas não fica nesse fluxo síncrono da tela. | [App, `_check_source` / `_source_worker`][app] |
| R-05 | **Corrigido** | A checagem publica o resultado quando termina, sem a antiga espera curta. O redutor descarta eventos de caminho ou tipo antigos. | [App][app]; [Estado, `apply(SourceChecked)`][state] |
| R-06 | **Corrigido** | stdout/stderr passam por `_Sink`; MCTF desliga a barra sob reporter; FFplay usa stdio DEVNULL e processo separado no Windows. A1–A4 aprovados manualmente em 16/11. Smoke após a limpeza seguinte é recomendado. | [FFplay, `launch_meter_window`][ebu]; [Validação manual P3H][validation] |
| R-07 | **Corrigido** | NOVO ENCODE cria novo estado de sessão, esvazia a fila e recria `CancelControl`. Testes cobrem segundo encode, batch→single e eventos tardios. | [App, `_session`][app]; `ui/tui/test_app.py` |
| R-08 | **Corrigido** | `-NoDownload` impede os downloads automáticos de binários. `-SkipValidation` também impede download do WT. No padrão, downloads continuam automáticos com log anterior. | [Launcher][launcher]; `tests/launcher.Tests.ps1` |
| R-09 | **Corrigido** | `Find-FfmpegBinary` procura em `bin/` e depois no PATH. Os caminhos resolvidos seguem para validação e variáveis `REELS_FFMPEG`/`REELS_FFPROBE`. Falta smoke real com FFmpeg apenas no PATH. | [Launcher, `Find-FfmpegBinary` / `Resolve-Binaries`][launcher] |
| R-10 | **Corrigido** | Exceções de `_tick` e `_drain` viram WARNING, deduplicadas por exceção. A deduplicação por App, em vez de sessão, é a pendência P3HF4. | [App, `_tick` / `_internal_error`][app] |
| R-11 | **Corrigido** | `CancelRequested` herda de `BaseException`; o laço Cineon encerra o FFmpeg e propaga cancelamento. Há teste com subprocesso simulado. | [Reporter][reporter]; `enhance/test_cineon_cancel.py::test_cancel_in_frame_loop_terminates_ffmpeg_then_propagates` |
| R-12 | **Pendente** | Sair da HOME antes de qualquer encode imprime “Cancelado pelo usuário.” com código 0. O teste atual fixa esse texto e precisa acompanhar a mudança. | [App, `_summary`][app]; `test_home_esc_exits_zero_and_prints_cancel` |
| R-13 | **Pendente** | Os rodapés combinam Choose/Start encode/Start queue/Details/Interrupt com Sair/Voltar/Confirmar. Recomenda-se português para os textos de ação. | [Renderer, `FOOTER_KEYS` e troca para Start queue][screens] |
| R-14 | **Pendente** | O ramo “— chega no P3D” continua em `_home`. Com presets 1–5 habilitados, esse texto é inalcançável no estado atual. | [Renderer, `_home`][screens]; `ui/tui/forms.py::ENABLED_PRESETS` |
| R-15 | **Pendente** | `main()` não lê `sys.argv` nem faz parse; argumentos adicionais são ignorados. Recomenda-se rejeição explícita como ajuste de menor escopo. | [Entrada da TUI, `main`][entry] |
| R-16 | **Pendente** | P3AF1 segue aberto no registro. O caminho de impressão de diagnóstico ainda usa string formatada sem `emoji=False`; a correção deve preservar texto bruto e formatação externa, sem exibir tags de estilo literalmente. | [Motor, `ffmpeg_live_reader`][engine]; [FINDINGS, P3AF1][findings] |
| R-17 | **Corrigido** | Ambos os fetch scripts definem `$ProgressPreference = 'SilentlyContinue'`. | `tools/fetch_ffmpeg.ps1:13`; `tools/fetch_wt_portable.ps1:19` |
| R-18 | **Corrigido** | `Set-WtDefaultSettings` mantém arquivo existente; a reinstalação salva `settings.json` antes de remover a pasta e restaura depois. Há cobertura Pester. | `tools/fetch_wt_portable.ps1:21–130`; `tests/launcher.Tests.ps1` |
| R-19 | **Corrigido** | Help `.PARAMETER`/`.EXAMPLE` e comentários do `.cmd` documentam os flags atuais. Não há modo clássico a expor. O help ainda tem os ajustes descritos em L2F2/SkipValidation. | [Launcher, cabeçalho][launcher]; `launcher.cmd` |
| R-20 | **Corrigido** | Tabs foram substituídos por espaços. O Pester contém verificação de ausência de TAB no escopo dos scripts. | [STATE, ciclo L2][history]; `tests/launcher.Tests.ps1` |

## 4. Achados relacionados: abertos, corrigidos e decisões

### 4.1 Pendências confirmadas

| ID | Estado atual | Descrição e encaminhamento |
|---|---|---|
| **N-1** | **Aberto — adiado por decisão do usuário (17/11/2026); era a prioridade 1 desta revisão** | `ui/tui_driver.py::_temp_path` e o remux Cineon em `Reels_Encoder_v2_FINAL.py:3897` usam `replace(".mp4", "_temp.mp4")`. Corrigir os dois pontos de forma consistente. |
| P3HF2 | Corrigido na branch (aguarda merge) | `enhance_visualizer.py:463–479` executa o literal `ffmpeg` na máscara MCTF. Adotar resolvedor comum. |
| P3HF3 | Aberto | `state.py::_fail_active` usa a última WARNING. A fragilidade está no fallback de `Finished` com falha; o fluxo normal de `JobDone` já usa `ev.error`. |
| P3HF4 | Aberto, baixo impacto | `_internal_seen` é criado por App e não é zerado ao iniciar nova sessão. O mesmo erro pode não aparecer no novo LOG. |
| P3HF5 | Decisão de contrato | Ctrl+C na HOME após um encode retorna 130; ESC retorna o código do último encode. 130 é coerente com interrupção. Recomenda-se documentar e testar antes de mudar. |
| P3EF2 | Decisão de produto pendente | O registro não define qual campo deve aparecer desativado nem o motivo. Definir comportamento antes de implementar. |
| P3BF1 | Em observação | Falha isolada de `test_red_bt709_full_range`, sem reprodução em 300 execuções segundo o registro. Evitar correção especulativa; investigar com log reproduzível. |
| L2F1 | Aberto, baixo impacto | WT ausente com `-NoDownload` pode produzir avisos duplicados em `Ensure-WindowsTerminalPortable` e `Resolve-Binaries`. Consolidar em um aviso útil. |
| L2F2 | Aberto no registro | Help com acentos em UTF-8 sem BOM pode apresentar mojibake no Windows PowerShell 5.1. Corrigir a estratégia de texto/encoding e conferir `Get-Help` no 5.1. |
| SkipValidation | Ajuda imprecisa | O texto diz “Pula só a checagem local”, mas o bloco pula `Resolve-Binaries`, incluindo validações e download do FFmpeg. O encoder continua resolvendo seu binário; o WT também não é baixado. Atualizar a descrição. |
| L2F3 | Administrativo | A nota do executor diz que a pendência ficou em STATE por restrição de escrita. O `VALIDATION.md` atual já contém as pendências do launcher. Harmonizar o fechamento; não é defeito funcional. |
| N-2 | Conferência local necessária | `VALIDATION.md` descreve `docs/Phase_2_TUI_Specification.md` como não rastreado. Seu conteúdo integral não foi confirmado no GitHub. Conferir Ctrl+C, retirada do modo clássico e mínimo real; marcar planos antigos como históricos quando adequado. |

### 4.2 Itens incorretamente mantidos como abertos na revisão anterior

| ID | Estado correto | Evidência |
|---|---|---|
| **ABF3** | **Corrigido — Ciclo AO** | `.github/workflows/ci.yml:25` roda `ruff check . --output-format=github`. FINDINGS registra fechamento com `9f895b7`/`c721496` e CI histórico. |
| **ACF1** | **Corrigido — Ciclo AN** | `cineon_pipeline.py:810` usa `encoding="utf-8-sig", errors="replace"`; FINDINGS registra fechamento com `e880918`, `46578f4` e `db2f91f`. Não aplicar a antiga sugestão de apenas `utf-8` sem considerar compatibilidade. |
| **ACF2** | **Corrigido — Ciclo AS** | Os consoles dos testes de fila usam `force_terminal=False`. FINDINGS registra fechamento com `09243ba`/`878047a` e resultados equivalentes em ambiente limpo e com `FORCE_COLOR`/`COLORTERM`. |
| **N-3 / P3HF1 / P3HF6 / P3HF7** | **Limpeza P3H incorporada** | C-1 a C-5 registrados em STATE e implementações presentes na main: `-nostdin`/DEVNULL nos caminhos sem pipe de dados; `new` interno como no-op; drenagem de eventos tardios; bloqueio de nova sessão com `worker_stuck`; remoção de `modal`/`modal_focus`. |

As notas antigas de “sem commit” nos registros descrevem o momento de execução. A presença das mudanças no commit consultado é a evidência utilizada para classificá-las como incorporadas.

### 4.3 Pequenas dívidas adicionais registradas em P3G

Itens abaixo foram encontrados ao conferir os registros relacionados. Não foram promovidos acima das prioridades da seção 2.

| ID | Situação |
|---|---|
| P3GF2 | `EncodeConfig.ui` permanece no modelo, embora a opção tenha saído do parser. Campo morto, de baixo impacto. |
| P3GF3 | Ramo de erro de entrada e docstring antigos no motor continuam registrados como obsoletos. Limpeza de manutenção. |
| P3GF4 | A entrada direta do script pode carregar o motor como `__main__` e como módulo importado pela TUI. O launcher usa `python -m ui.tui`. O impacto em um encode completo pela entrada direta não foi validado nesta revisão. |
| P3GF7 | Referências históricas de documentação no README e em planos antigos permanecem registradas. |
| P3GF8 | Cobertura das opções de tonemap não garante, por si só, que nenhuma opção tenha sido omitida. Dívida de teste registrada. |

Fonte: [FINDINGS, ciclos P3G/P3H/L2][findings].

## 5. Verificações isoladas executadas nesta revisão

Foram executadas somente funções extraídas por AST, sem importar ou executar o motor completo.

### 5.1 Caminho temporário — N-1

| Entrada | Resultado atual de `_temp_path` | Caminho esperado pela regra proposta |
|---|---|---|
| `C:/clips.mp4/video.mp4` | `C:/clips_temp.mp4/video_temp.mp4` | `C:/clips.mp4/video_temp.mp4` |
| `C:/clips/video.MP4` | `C:/clips/video.MP4` | `C:/clips/video_temp.mp4` |
| `C:/clips/video.mp4` | `C:/clips/video_temp.mp4` | `C:/clips/video_temp.mp4` |

A mesma expressão de substituição também está no motor. O teste demonstra a formação incorreta do caminho; **não demonstra, por si só, perda efetiva de arquivo em um encode real**.

### 5.2 Mínimo de terminal — R-03

| Dimensão | Resultado de `too_small` | Consequência confirmada pela leitura do código |
|---|---|---|
| 80×24 | `True` | Aviso para ampliar; navegação por `Key` ignorada quando não há encode rodando. |
| 119×39 | `True` | Mesmo bloqueio. |
| 120×40 | `False` | Passa pela verificação de tamanho do estado. |

Esses resultados confirmam a divergência com a guarda de entrada baseada em `FALLBACK_SIZE=(80,24)`. Não constituem teste visual manual do Windows Terminal.

## 6. Validação manual e CI ainda necessários

| Ordem de validação | Cenário | Resultado esperado | Estado da evidência |
|---|---|---|---|
| 1 | Ctrl+C especificamente durante QC, no Windows | Master mantido, apenas certificados novos incompletos removidos quando aplicável; terminal restaurado e nenhum processo órfão. | Testes automatizados presentes; confirmação manual específica ainda necessária. |
| 2 | Falha durante encode em single e batch | Parcial novo removido quando seguro; saída preexistente e temporário de recuperação preservados; aviso claro quando não for possível limpar. | Testes automatizados presentes; confirmação manual específica ainda necessária. |
| 3 | Janela 80×24, 119×39, 120×40 e resize | Comportamento coerente com o mínimo anunciado; execução preservada ao reduzir e Ctrl+C funcional. | Atualização posterior — corrigido no PR #82 (`9e30b8b`). Capturas do harness aprovadas (80×24, 100×30, 119×39, 120×40, 70×20, resize). Relato do usuário 17/11/2026: launcher em 120×40 e 80×24 medido, resize durante encode e Ctrl+C aprovados no Windows Terminal real (roteiro M0–M4). |
| 4 | `launcher.cmd` padrão e `-NoDownload`, com FFmpeg/FFprobe apenas no PATH | Usa os binários do PATH, informa origem e não faz fetch desnecessário; abre a TUI. | Pendente no `VALIDATION.md` atual. |
| 5 | Smoke FFplay/MCTF/preflight e segundo encode | TUI íntegra, LOG capturado, nova sessão sem cancelamento herdado. | Manual de 16/11 aprovado; repetir como regressão após a limpeza/correções atuais. |
| 6 | Pester em `ubuntu-latest` | Job e quatro testes de fetch falso aprovados com log real. | Sem confirmação atual nesta revisão; não presumir falha de caminhos com `\`. |

### Resultados históricos consultados — não reexecutados nesta revisão

| Registro | Resultado documentado |
|---|---|
| Limpeza P3H — suíte canônica | **1053 passed, 4 skipped, 0 failed**; os quatro skips eram goldens por diferença de ambiente NumPy. |
| Limpeza P3H — goldens em rodada separada | **4/4 aprovados** com FFmpeg real e verificação de impressão digital de ambiente dispensada nessa rodada. Essa condição deve acompanhar o resultado. |
| Limpeza P3H — lint | `ruff check .`: limpo segundo STATE. |
| L2 — Pester pwsh 7 | **156 passed, 0 failed**, conforme STATE/VALIDATION. |
| L2 — Pester Windows PowerShell 5.1 | **156 passed, 0 failed**, conforme STATE/VALIDATION. |
| P3H manual — 16/11 | A1–A4 aprovados, incluindo FFplay/MCTF/preflight. B2 falhou no cancelamento por C do segundo encode; decisão posterior removeu esse cancelamento. A interrupção da TUI permanece por Ctrl+C. |

**Limite da consulta ao CI:** os endpoints disponíveis retornaram listas vazias de statuses e de execuções disparadas por pull request para o commit. Isso não comprova CI verde, falha, nem ausência de execuções disparadas por push. A confirmação do job Pester Ubuntu permanece pendente nesta revisão.

Fontes: [STATE][history], [VALIDATION][validation] e [workflow CI][ci].

## 7. Mudanças do launcher e da interface já incorporadas

- A TUI é a interface interativa de encode. A CLI por argumentos do script do encoder continua existindo; a remoção do menu clássico não eliminou esse caminho.
- `ui/launcher.py` e o teste de paridade do wizard foram removidos no ciclo correspondente.
- `launcher.cmd` repassa os argumentos; os flags atuais incluem `-NoDownload`, `-SkipValidation`, `-SkipEnvSetup`, `-ForceEnvSetup` e `-DebugMode`.
- O venv usa stamp de requisitos e `pip check`.
- O launcher transmite os caminhos resolvidos por `REELS_FFMPEG` e `REELS_FFPROBE` quando passa por `Resolve-Binaries`.
- Os fetch scripts suprimem a barra de progresso; a configuração existente do Windows Terminal é preservada.
- O workflow contém `worktree-**` nos gatilhos de push, lint do repositório, testes Python no Windows e Pester no pwsh/Windows PowerShell 5.1.

Esses pontos não eliminam as pendências pontuais de help, aviso duplicado e smoke real descritas acima.

## 8. Limites e interpretação

- A revisão está fixada no commit informado. Não representa auditoria de todas as branches/PRs nem do motor completo.
- Afirmações de correção usam implementação atual e evidências históricas consultadas; resultados históricos não foram tratados como execuções realizadas nesta sessão.
- N-2 depende de arquivo local descrito como não rastreado. Não foi fechado por inferência a partir de seu nome ou de versões antigas.
- P3EF2 é uma decisão de produto; P3BF1 está sem reprodução atual. Nenhum dos dois justifica implementação especulativa.
- As severidades S3/S4 citadas no histórico não foram convertidas em “crítico” sem demonstração. A ordem proposta organiza o próximo trabalho pelo efeito prático observado.

## 9. Histórico

- **17/11/2026 — atualização posterior: R-03 resolvido e integrado na `main` pelo PR #82 (`9e30b8b`), via branch `fix/tui-review-r03-polish`:** layout compacto 80×24 implementado; suíte completa 1459/4 skipped antes do último ajuste, `pytest ui` 1012 + 17 relacionados após; capturas do harness aprovadas; usuário relatou M0–M4 aprovados no Windows Terminal real. Contagem passa a 15/0/5.

- **17/11/2026 — revisão corrigida deste documento:** main permanece em `7920e0713a7c`. Corrigida a contagem para 14/1/5; R-03 reclassificado como parcial; R-06 reconhecido como corrigido com aprovação manual histórica; ABF3/ACF1/ACF2 fechados; limpeza P3H confirmada; N-1 ampliado ao motor e helper; adicionadas prioridades e critérios de aceite. Nenhuma implementação realizada nesta revisão.
- **17/11/2026 — ciclo L2, `7920e0713a7c`:** incorporados os ajustes de launcher R-08/R-09/R-17/R-18/R-19/R-20 e gatilho de CI. Permanecem os acabamentos e confirmações descritos nesta versão.
- **17/11/2026 — revisão de `3c16e56032f9`:** etapa anterior de conferência de TUI e entrega segura. As classificações daquela revisão são substituídas pela tabela atual quando divergirem.
- **18/10/2026:** documento organizado em R-01 a R-20.
- **12/10/2026 — `cb30f3a07f29`:** etapa de launcher com WT portátil.
- **10/10/2026 — `20fc1e07854e`:** primeira revisão da TUI após P3E.

## Fontes do snapshot

Os links abaixo apontam para o commit revisado, evitando que alterações futuras na `main` mudem a referência deste documento.

[driver]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ui/tui_driver.py
[state]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ui/tui/state.py
[screens]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ui/tui/screens.py
[app]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ui/tui/app.py
[entry]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ui/tui/__main__.py
[engine]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/Reels_Encoder_v2_FINAL.py
[reporter]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/reporter.py
[ebu]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/ebu_meter.py
[launcher]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/launcher.ps1
[ci]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/.github/workflows/ci.yml
[history]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/.claude/memory/STATE.md
[findings]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/.claude/memory/FINDINGS.md
[validation]: https://github.com/gabrielschoenardie/encoder_ai_instagram/blob/7920e0713a7c3e958a76cf014b667744b742f853/.claude/memory/VALIDATION.md
