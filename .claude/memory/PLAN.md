<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo S: corrigir QF1 (stderr do pip promovido a erro terminante) em launcher.ps1

Data: 2026-08-14 | Ciclo: fix | Origem: `FINDINGS.md` § "Ciclo Q" (QF1),
repro detalhado em `.claude/memory/STATE.md` linhas ~510-547 (Task 9, Step 3,
1ª tentativa).

## Diagnóstico (já confirmado por controle A/B na Task 9, não repetir a
## investigação — só aplicar a correção)

`launcher.ps1` define `$ErrorActionPreference = "Stop"` no topo (linha 17).
Em PowerShell 7+, quando o stream de erro de um comando nativo é fundido ao
de saída (`2>&1`/`*>&1` — algo que o **chamador** do script pode fazer, ex.:
`.\launcher.ps1 *>&1 | Tee-Object ...`), a variável de sessão
`$PSNativeCommandUseErrorActionPreference` (default `$true` em pwsh 7.3+)
faz qualquer escrita em stderr de um comando nativo virar um `NativeCommandError`
**terminante** — mesmo que o processo saia com `exit 0`. `pip install` escreve
`[notice] A new release of pip is available: ...` em stderr rotineiramente,
mesmo em instalações bem-sucedidas (linha 94: `& $VenvPython -m pip install
-r $reqPath | Out-Host`).

Efeito cascata: o `catch` (linha 287) chama `Write-LauncherLog
$_.Exception.Message "Error"` (linha 288). Nesse `NativeCommandError`
específico, `$_.Exception.Message` vem vazio/nulo, e como `Write-LauncherLog`
declara `[Parameter(Mandatory)][string]$Message`, a própria chamada de log
falha — mascarando completamente o erro original com um stack trace de
parameter-binding do PowerShell, **depois que o setup já tinha dado certo**
(falso negativo: usuário vê "falha", terminal `-Debug` mostra erro de
binding, não o real motivo).

Não afeta uso normal (duplo clique / shell interativo sem fusão de stream) —
só chamadores que fundem `*>&1`/`2>&1` (CI, wrappers de automação, harness de
teste). Mas é uma falha real e plausível fora do laboratório (qualquer
pipeline de CI que capture a saída do launcher cai nisso).

## S1 — neutralizar o gatilho na raiz (defesa primária)

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| S1a | Logo após `$ErrorActionPreference = "Stop"` (linha 17), adicionar `$PSNativeCommandUseErrorActionPreference = $false` com um comentário de 1-2 linhas citando QF1: essa variável só existe em pwsh 7.3+ (é um no-op inofensivo em Windows PowerShell 5.1, que não a lê); desliga a promoção de stderr-de-comando-nativo a erro terminante, deixando o script continuar confiando só em `$LASTEXITCODE` (já checado explicitamente após `venv`/`pip install`/`pip freeze`) pra detectar falha real. | `executor` | `launcher.ps1` | linha presente logo abaixo de `$ErrorActionPreference` |

## S2 — blindar o `catch` contra mensagem vazia (defesa secundária, cinto e suspensório)

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| S2a | No bloco `catch` (linha ~287-291), trocar a chamada direta `Write-LauncherLog $_.Exception.Message "Error"` por uma variável intermediária que cai pra uma mensagem padrão quando `$_.Exception.Message` é vazio/nulo — ex.: `$errMsg = if ($_.Exception.Message) { $_.Exception.Message } else { "Erro sem mensagem (possível stderr de comando nativo promovido a erro terminante). Rode com -Debug para ver o stack trace completo." }`, depois `Write-LauncherLog $errMsg "Error"`. Sintaxe compatível com PowerShell 5.1 (nada de `??`). | `executor` | `launcher.ps1` | catch nunca mais pode quebrar por Message vazio, mesmo que uma causa futura diferente produza esse cenário |

## Verificação (reproduzir o mesmo controle A/B da Task 9, agora com o fix)

| ID | tarefa | agente alvo | critério de done |
|----|--------|-------------|-------------------|
| S3a | Reproduzir o repro sintético descrito em `STATE.md` linhas 531-547: um comando nativo que escreve em stderr e sai com código 0 (ex.: `powershell -Command "[Console]::Error.WriteLine('[notice] fake'); exit 0"` chamado de dentro de um script de teste com `$ErrorActionPreference='Stop'`), **sem** o fix (`$PSNativeCommandUseErrorActionPreference` no default) e **com** `*>&1` fundindo os streams — confirmar que reproduz `NativeCommandError` (replica o "COM *>&1" da Task 9). | `executor` | saída real colada no `STATE.md` |
| S3b | Mesmo repro, agora **com** `$PSNativeCommandUseErrorActionPreference = $false` setado antes da chamada nativa — confirmar que `*>&1` já não promove o stderr a erro terminante e o script sobrevive (replica o "SEM *>&1" da Task 9, mas agora com `*>&1` presente e o fix aplicado). | `executor` | saída real colada no `STATE.md` |
| S3c | Rodar `pip install` de verdade uma vez via `Install-Requirements` (venv já existe de sessões anteriores — reaproveitar, não recriar do zero) com o `launcher.ps1` corrigido, invocado com `*>&1 \| Tee-Object` (reproduzindo a invocação exata que quebrou na Task 9), confirmar que sobrevive e loga "Dependencias instaladas." normalmente. | `executor` | saída real colada no `STATE.md`, sem `NativeCommandError` |
| S3d | `powershell -NoProfile -Command "$null = Get-Content .\launcher.ps1 -Raw \| [System.Management.Automation.PSParser]::Tokenize([ref]$null)"` (ou equivalente parse-check já usado nas Tasks anteriores) pra garantir que a sintaxe do arquivo inteiro continua válida. | `executor` | `PARSE_OK` ou equivalente, sem erro |

## Notas de execução

- Não tocar em nenhuma outra função/linha além das listadas em S1a e S2a.
- Não remover os `if ($LASTEXITCODE -ne 0) { throw ... }` existentes — eles
  continuam sendo a fonte real de verdade pra falha de `venv`/`pip`.
- Carregar `superpowers:verification-before-completion` antes de marcar
  qualquer ID como done — colar saída real no `STATE.md`, nunca parafrasear.
- Ao terminar: atualizar a entrada `QF1` em `FINDINGS.md` (linha de status,
  mesmo padrão de A3/H1/H2/QF2) pra "corrigido — ciclo S", citando o sha do
  commit. Commit único: `git add launcher.ps1 .claude/memory/FINDINGS.md
  .claude/memory/STATE.md .claude/memory/PLAN.md` com mensagem no padrão do
  repo (ex.: `fix(launcher): parar de promover stderr de comando nativo a
  erro terminante (QF1)`).
- Retorno: uma linha (S1+S2+S3 feito, sha do commit).
