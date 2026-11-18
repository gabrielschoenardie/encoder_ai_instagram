# TUI — guia de uso

Guia da interface de terminal (TUI) do Reels Encoder, conferido contra o código em `ui/tui/`. Quando este guia e os documentos históricos da [Fase 1](Phase_1_Technical_Audit.md) e da [Fase 2](Phase_2_TUI_Specification.md) divergirem, vale o código e este guia.

## Como iniciar

**Pelo launcher (Windows).** `launcher.cmd` valida o ambiente e abre o Windows Terminal com duas abas: *Setup* (perfil de hardware) e *Encode*, que roda a TUI. Opções aceitas, repassadas ao `launcher.ps1`:

| Opção | Efeito |
|---|---|
| `-NoDownload` | não baixa nada; FFmpeg/FFprobe ausentes em `bin\` e no PATH encerram com orientação de instalação; sem Windows Terminal, usa janelas PowerShell |
| `-SkipValidation` | pula a checagem local de `bin\ffmpeg.exe` / `bin\ffprobe.exe` e não baixa o Windows Terminal |
| `-SkipEnvSetup` | pula a criação/validação do `venv` (exige um `venv` existente) |
| `-ForceEnvSetup` | reinstala as dependências do `venv` |
| `-DebugMode` | mostra mensagens de nível Debug e o stack trace em caso de erro |

A ajuda completa está em `Get-Help .\launcher.ps1 -Full`.

**Direto pelo Python**, a partir da raiz do repositório e com o `venv` ativo:

```bash
python -m ui.tui                       # abre a TUI
python Reels_Encoder_v2_FINAL.py       # sem input e sem --batch, também abre a TUI
```

Os binários são resolvidos na ordem `REELS_FFMPEG`/`REELS_FFPROBE` → `bin\` → PATH. Se FFmpeg ou FFprobe faltar, a TUI mostra o cartão de dependência ausente e sai com código 1.

## Tamanho do terminal

| Terminal | Comportamento |
|---|---|
| a partir de 120×40 | layout completo |
| de 80×24 até abaixo de 120×40 | layout compacto: cabeçalho e rodapé de uma linha, painéis empilhados, todas as telas e ações acessíveis |
| abaixo de 80×24, na abertura | sai com "a TUI precisa de um terminal interativo com VT e pelo menos 80×24" e código 1 |
| abaixo de 80×24, com a TUI aberta | aviso "terminal pequeno — amplie para 80×24"; as teclas são ignoradas, mas um encode em andamento continua e o Ctrl+C segue valendo |

A TUI também exige um terminal interativo com suporte a VT. Para cores e glyphs completos, use o Windows Terminal.

## Navegação

O rodapé de cada tela lista as teclas válidas naquele momento. Fluxo: HOME → SOURCE → CONFIGURATION (presets 1–3) ou ADVANCED (preset 5) → PREVIEW → READY → ENCODING → QC → COMPLETED. No batch, o fluxo segue READY → QUEUE → REPORT.

| Tela | Teclas principais |
|---|---|
| HOME | `↑↓` navegar · `1`–`5` ou `ENTER` abrir fluxo · `ESC` sair |
| SOURCE | digitar o caminho · `←→` cursor · `ENTER` continuar · `ESC` voltar |
| CONFIGURATION | `↑↓` campo · `←→` valor · `0`–`9` digitar · `ENTER` próximo · `ESC` voltar |
| ADVANCED | `↑` no primeiro campo vai para as abas · `←→` aba ou valor · `SPACE` on/off · `ENTER` próximo |
| PREVIEW / READY | `←→` escolher · `ENTER` confirmar · `ESC` voltar |
| ENCODING / QC / QUEUE | `D` detalhes · `L` log · `Ctrl+C` interromper |
| LOG | `←→` filtro (TUDO, SYSTEM, INFO, WARNING, FFMPEG) · `ESC` voltar |
| ERROR | `↑↓` rolar o stderr · `←→` escolher ação · `ENTER` confirmar |

O preset 4 (Tools) suspende a TUI, roda o utilitário escolhido no terminal e volta ao menu.

### Proteção do ENTER no READY

Nos fluxos com preset, o `ENTER` que inicia o encode só é aceito se:

- a tela READY estiver visível há pelo menos 1,2 s (`READY_HOLD_S`); e
- a tecla anterior tiver sido pressionada há pelo menos 0,3 s (`KEY_GAP_S`).

Um `ENTER` fora dessas condições é ignorado sem aviso. Isso evita que o `ENTER` repetido das telas anteriores dispare o encode. Se nada acontecer, espere um instante e pressione `ENTER` de novo.

### Ctrl+C

`Ctrl+C` é a única forma de interromper um encode. Não há confirmação, e o que acontece com os arquivos depende da etapa:

| Etapa | Resultado |
|---|---|
| antes do encode ou durante o PASS | o FFmpeg é encerrado e a saída parcial nova é removida; se a remoção falhar, um aviso é exibido |
| QC (tela QC visível) | o master é mantido; só os certificados `.qc.html` / `.qc.json` criados nesta execução são removidos; certificados que já existiam são preservados |
| batch | a fila inteira é interrompida, com as mesmas regras para o job ativo |

A tela CANCELLED, ou a linha final no terminal, informa o que foi feito.

## NOVO ENCODE

As telas finais (COMPLETED, ERROR, CANCELLED e REPORT) oferecem a ação **NOVO ENCODE**, pelo botão ou pela tecla `N`. Ela volta à HOME na mesma sessão, mantendo os rascunhos de configuração. Fica indisponível se um worker anterior não tiver encerrado.

## Consulta de erros

- **ERROR** mostra um resumo da falha, limitado a 200 caracteres na primeira linha, e o painel **FFMPEG STDERR** com as linhas finais do FFmpeg (`↑↓` rola até a causa). O painel **ESTADO** mostra a etapa, o último frame e a situação da saída.
- **VER LOG** abre o log completo da sessão, com filtros por categoria.
- Ao sair, o terminal imprime uma linha de resumo, como `✗ erro (código 1): …`.
- Limitação conhecida (FINDINGS `R03F2`): linhas longas do stderr e do LOG são cortadas com "…" no ERROR e no LOG, em qualquer tamanho de terminal. O resumo de 200 caracteres também não preserva mensagens maiores. Para ler a linha inteira, rode o mesmo arquivo pela CLI (`python Reels_Encoder_v2_FINAL.py <entrada>`), que imprime o final do stderr no terminal; `--debug` acrescenta o traceback.

## Referências

- Revisão de conformidade da TUI: [`reviews/tui-review.md`](reviews/tui-review.md)
- Histórico de design: [Auditoria técnica (Fase 1)](Phase_1_Technical_Audit.md), [Especificação (Fase 2)](Phase_2_TUI_Specification.md), [Pedido de sign-off (Fase 2)](Phase_2_Signoff_Review_Response.md)
