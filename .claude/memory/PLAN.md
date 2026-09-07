<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AZ: `wt.exe` fragmenta o comando da aba por causa dos `;` que AX1/AX11 injetaram

Data: 2026-09-07 | Ciclo: AZ | Origem: verificação manual do usuário pós-merge do Ciclo AY. Ciclo anterior: AY (fechado, `5728701`).

## Diagnóstico (root cause, `superpowers:systematic-debugging` Fase 1-2)

Repro relatado pelo usuário — `.\launcher.ps1` chegou até abrir o Windows Terminal, mas as duas
abas erraram assim (6 mensagens, 3 por aba):

```
[erro 2147942402 (0x80070002) ao iniciar "" $env:REELS_FFMPEG='...'""]
O sistema não pode encontrar o arquivo especificado.
[erro ... ao iniciar "" $env:REELS_FFPROBE='...'""]
[erro ... ao iniciar "" & 'venv\Scripts\python.exe' 'Reels_Encoder_v2_FINAL.py' --hardware-info""]
(repete para a aba Encode, com --ui)
```

`wt.exe` está tratando cada pedaço separado por `;` do comando como se fosse, ele próprio, um
executável a iniciar — daí "sistema não pode encontrar o arquivo especificado" para um texto
que começa com `$env:...` ou `&`.

**Comparação com o código pré-AX** (`git show 2fb7fd7:launcher.ps1`, função antiga
`Build-EncodeCommand`/`Open-LauncherTabs`): o `$SetupCmd`/`$EncodeCmd` de antes era **uma
instrução só** — `& '$VenvPython' '$script' --ui` (ou com args de perfil), nunca continha `;`.
O único `;` de toda a invocação do `wt` era o separador explícito entre os dois `new-tab`,
escrito inline com escape de crase (`` `; ``) — esse escape é só para o **parser do PowerShell**
não interpretar a linha de código como duas instruções; nunca precisou lidar com `;` real
sobrevivendo dentro do valor de `$SetupCmd`.

`AX1` e `AX11` (Ciclo anterior, já mesclado) mudaram isso: `Build-SetupCommand`/`Build-AppCommand`
(`launcher.ps1:415-459`) agora prefixam `Set-Location $(Protect-PSLiteral ...); ` (`AX1`) e
`` `$env:REELS_FFMPEG=...; `` + `` `$env:REELS_FFPROBE=...; `` (`AX11`) — **3 `;` literais** a
mais dentro da própria string de `$SetupCmd`/`$EncodeCmd`, nenhum deles existia antes.

`Open-LauncherTabs` (`:476-511`) monta `$wtArgs = $setupTab + @(";") + $encodeTab` e chama
`& $WtPath @wtArgs` — o `@(";")` é o separador **intencional** entre as duas abas (funciona: é
um elemento de array próprio, exatamente como o wt espera para encadear `new-tab ; new-tab`).
O problema são os `;` que **vivem dentro do valor** de `$SetupCmd`/`$EncodeCmd`: o parser de
linha de comando do próprio `wt.exe` re-escaneia o texto reconstruído procurando por `;` para
decidir onde uma "ação" termina e a próxima começa — e, por design documentado da Microsoft,
**qualquer `;` sem escape é um separador de ação para o wt**, mesmo vivendo dentro do que
`-Command` deveria receber como um valor único. O jeito documentado de fazer um `;` sobreviver
até o comando filho é escapá-lo como `\;` (barra invertida) especificamente para o `wt`.

Isso bate exatamente com a contagem observada: `Set-Location 'ROOT'; $env:REELS_FFMPEG='...';
$env:REELS_FFPROBE='...'; & 'venv...' 'script.py' --hardware-info` tem 3 `;` internos → o wt
tenta iniciar os pedaços entre eles como comandos separados.

## Desenho

Fix cirúrgico, escopado só ao ramo `$WtAvailable` de `Open-LauncherTabs` — o ramo de fallback
(`Start-Process ... -ArgumentList`) não passa pelo parser do `wt` e **precisa continuar** com
`;` reais (são estatuтos PowerShell de verdade para `powershell.exe -Command`).

Em `Open-LauncherTabs`, dentro do bloco `if ($WtAvailable) { ... }`, antes de colocar
`$SetupCmd`/`$EncodeCmd` nos arrays `$setupTab`/`$encodeTab`: escapar todo `;` literal do
**valor** da string para `\;` (`$SetupCmd -replace ';', '\;'` / idem para `$EncodeCmd`) — só
para o texto que vai para o `wt`. O `wt` desfaz o escape ao montar a linha de comando real do
processo filho, então `powershell -Command "..."` recebe os `;` de volta como separadores de
instrução PowerShell normais. O separador entre as duas abas (`@(";")`, elemento de array
próprio, sem escape) **não muda** — é o único `;` que deve continuar sendo interpretado pelo
`wt` como delimitador de ação.

## O que NÃO fazer

- Não tocar no ramo de fallback (`Start-Process`, linhas ~504-510) — ele não tem esse problema
  e usar `\;` ali quebraria a sintaxe real do PowerShell.
- Não tocar em `Build-SetupCommand`/`Build-AppCommand` — elas continuam devolvendo `;` reais;
  o escape é responsabilidade de quem entrega a string ao `wt`, não de quem a constrói (o
  fallback usa a mesma string sem escape nenhum).
- Não escapar o separador `@(";")` entre `$setupTab` e `$encodeTab` — esse tem que continuar
  sendo um `;` puro, é o que faz o `wt` abrir duas abas.
- Não adicionar teste Pester novo para o ramo `$WtAvailable` — já documentado no cabeçalho de
  `tests/launcher.Tests.ps1` como superfície não-testável (`& $variavelComCaminho` não passa
  pelo `Mock`); verificação real fica para o usuário, como no Ciclo AY.
- Não refatorar `Open-LauncherTabs` além desse ponto.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AZ1 | Em `launcher.ps1`, função `Open-LauncherTabs`, dentro do `if ($WtAvailable) { ... }` (linhas ~491-503): antes de `$setupTab += @($Shell) + $shellArgs + @($SetupCmd)` e `$encodeTab += @($Shell) + $shellArgs + @($EncodeCmd)`, criar `$setupCmdForWt = $SetupCmd -replace ';', '\;'` e `$encodeCmdForWt = $EncodeCmd -replace ';', '\;'`, e usar essas duas variáveis (não `$SetupCmd`/`$EncodeCmd` originais) nos dois `+=`. O separador `@(";")` entre `$setupTab` e `$encodeTab` (linha ~501) e o ramo `else` (fallback, linhas ~504-510) não mudam | executor | `launcher.ps1` | `Select-String -Pattern 'SetupCmd -replace' launcher.ps1` e `Select-String -Pattern 'EncodeCmd -replace' launcher.ps1` retornam 1 linha cada; o ramo fallback (`Start-Process`) continua usando `$SetupCmd`/`$EncodeCmd` sem `-replace` |

## Critérios de aceite

- Dentro do ramo `$WtAvailable`, `$setupTab`/`$encodeTab` recebem a versão com `\;` no lugar de
  `;`; o ramo fallback recebe a string original, intocada.
- `Parser::ParseFile` sem erros de sintaxe.
- `git diff --stat` toca só `launcher.ps1`, poucas linhas.
- Suíte Pester dos 110 testes existentes **continua verde sem nenhuma edição de teste** — o
  ramo `$WtAvailable` já era não-testável antes desta mudança (ver nota acima), então nada que
  já rodava sob `Mock` deveria mudar de comportamento.

## Notas de execução

- Verificação real (abrir o `wt` de fato e confirmar que as duas abas rodam o comando inteiro,
  sem fragmentação) fica para o usuário — não há Windows Terminal disponível no ambiente do
  executor. Documentar essa limitação no STATE.md, como nos Ciclos AY.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AZ` e cabeçalho de tabela.
- Retorno ao Orquestrador: ponteiro + veredito, uma linha por ID + confirmação de sintaxe.
