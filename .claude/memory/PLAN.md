<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BC: hardening final do bootstrap (`launcher.ps1`)

Data: 2026-09-08 | Ciclo: BC | Origem: pedido direto do usuário (15 objetivos de hardening,
via `/superpowers:brainstorming`), não uma auditoria do Orquestrador. Ciclo anterior: BB
(fechado, PR #64, CI verde, verificação manual confirmada). Duas decisões de desenho foram
resolvidas com o usuário antes deste PLAN — ver § Decisões.

## Diagnóstico

O usuário pediu um hardening cirúrgico do `launcher.ps1` (GUI-only bootstrap) em 15 pontos.
Treze são aditivos e sem conflito com o código atual. Dois exigiram decisão do usuário porque
colidiam com trabalho já fechado ou mudavam o raio de ação de uma correção:

1. **Conflito com o Ciclo BB.** O pedido original (item 3) descrevia a ordem
   `python inicia → versão OK → pip check OK → stamp confere → pula install`, com `pip check`
   **dentro do gate**, rodando em todo lançamento. Isso reabriria `BAF1` (custo do `pip check`
   no caminho rápido de ~2s que a `AX7` existia para preservar) e `BAF2` (se `pip check`
   reprovar por algo que reinstalar não resolve, o venv fica "não-saudável" para sempre e o
   launcher reinstala em todo lançamento, indefinidamente) — os dois achados que o Ciclo BB
   fechou nesta mesma manhã (`.claude/memory/FINDINGS.md` § "Achado — 2026-09-07 ... FECHADO
   no Ciclo BB"). **Decisão do usuário: manter o fix da BB.** `pip check` nunca entra no gate
   do caminho rápido; continua rodando só como pós-condição depois de qualquer reinstalação.
2. **Python do venv abaixo do mínimo.** O pedido oferecia duas saídas ("erro claro" OU
   "recriar o ambiente, se já for a arquitetura atual"). Hoje o launcher **nunca** recria um
   venv existente automaticamente — um venv "não-saudável" só tem os pacotes reinstalados,
   nunca o interpretador substituído. Recriar seria comportamento novo (apagar diretório
   sozinho). **Decisão do usuário: erro claro, sem tocar no disco** — consistente com
   `Resolve-SystemPython`/`New-ProjectVenv`, que já falham assim (mensagem acionável, nunca
   correção automática).

## Decisões

| # | pergunta | resposta do usuário |
|---|----------|----------------------|
| 1 | ordem do gate (`pip check` dentro ou fora do caminho rápido) | **manter o fix da BB** — `pip check` nunca no caminho rápido |
| 2 | Python do venv abaixo do mínimo: erro ou recriar sozinho | **erro claro, para** — não mexe no disco |

## Desenho

### BC1 — `launcher.ps1`

**(a) `$Debug` → `$DebugMode`.** Rename mecânico. Ocorrências: `param()` (linha 9),
`Write-LauncherLog` (linha 30, condição do nível `Debug`), catch global (linha 591,
`if ($Debug) { ... }`). Nenhuma outra referência existe (confirmado por grep antes deste
PLAN). Não adicionar `[CmdletBinding()]` — fora de escopo, ninguém pediu.

**(b) `Get-VenvPythonVersion` (nova função).** Só lê a versão do Python **já existente** no
venv — não decide nada:

```powershell
function Get-VenvPythonVersion {
    param([Parameter(Mandatory)][string]$VenvPython)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $VenvPython -c "import sys;print('%d.%d.%d'%sys.version_info[:3])" 2>&1
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) { return $null }
    $reported = (@($out) -join "`n").Trim()
    $parsed = $null
    if (-not [version]::TryParse($reported, [ref]$parsed)) { return $null }
    return $parsed
}
```

Guard `$ErrorActionPreference = "Continue"` + `finally`, como toda invocação nativa desde a
`AX`. **Não** refatorar `Resolve-SystemPython` para compartilhar essa lógica — é uma pequena
duplicação (~5 linhas) aceita em troca de zero risco sobre uma função já testada e em
produção. Duas funções, dois propósitos (uma escolhe um Python do sistema; a outra só lê o
que já está no venv).

**(c) `Initialize-Environment` — novo trecho entre a checagem de saúde e a decisão do caminho
rápido** (a partir da atual linha 309):

```powershell
$healthy = Test-VenvHealthy -VenvPython $venvPython
if (-not $healthy) {
    Write-LauncherLog "Venv nao respondeu a 'python -c import sys' (orfao ou corrompido) - reinstalando dependencias." "Warn"
}
else {
    $venvVersion = Get-VenvPythonVersion -VenvPython $venvPython
    if ($null -eq $venvVersion -or $venvVersion -lt [version]$minVersion) {
        $found = if ($null -ne $venvVersion) { $venvVersion.ToString() } else { "desconhecida" }
        throw "Python do venv incompativel.`nEncontrado: $found`nMinimo exigido: $minVersion`nApague a pasta '$VenvPath' e rode o launcher novamente para recria-la com um Python compativel."
    }
    Write-LauncherLog "Python do venv: $venvVersion" "Success"
}
if ((-not $Force) -and $healthy -and $stamp -and ((Read-VenvStamp -VenvPath $VenvPath) -eq $stamp)) {
    Write-LauncherLog "Dependencias ja instaladas (stamp confere) - pulando pip. Use -ForceEnvSetup para reinstalar." "Info"
    return $venvPython
}
```

O `throw` roda **antes** da decisão do caminho rápido e **independe** de `-Force` ou do
stamp — reinstalar pacotes não conserta um interpretador abaixo da versão mínima, então não
há cenário em que vale a pena tentar. Isso fecha o Caso 5 do usuário ("não deve simplesmente
reutilizar o ambiente"). `$healthy -and (...)` continua suficiente na condição do caminho
rápido: quando `$healthy` é `$true`, ou a função já lançou (versão ruim) ou `$venvVersion` já
foi validada — não precisa de uma terceira variável.

**Depois de `Write-VenvStamp`, no trecho de pós-condição já existente da BB**, adicionar o log
de sucesso simétrico ao aviso que já existe:

```powershell
$consistency = Test-VenvConsistent -VenvPython $venvPython
if (-not $consistency.Ok) {
    Write-LauncherLog "pip check encontrou dependencias inconsistentes (o encoder pode falhar em runtime). Use -ForceEnvSetup depois de ajustar o pyproject.toml:`n$($consistency.Report)" "Warn"
}
else {
    Write-LauncherLog "pip check: ambiente consistente." "Success"
}
```

**(d) `Test-ExecutableRuns` (nova função, compartilhada ffmpeg+ffprobe).** Valida que o binário
não só existe mas também inicia:

```powershell
function Test-ExecutableRuns {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Path -hide_banner -version 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        throw "$Name foi encontrado em '$Path', mas nao conseguiu iniciar (exit $LASTEXITCODE)."
    }
    Write-LauncherLog "$Name executavel." "Success"
}
```

**(e) `Test-RequiredBinary`** — `Test-Path $Path` → `Test-Path $Path -PathType Leaf` (linha
336). Uma linha; cobre os 3 call sites (python do venv, ffmpeg, ffprobe) sem tocar nas
mensagens de erro existentes.

**(f) `Test-FfmpegCapabilities`** — dentro dos dois `foreach` existentes (encoders e filtros),
logar sucesso por item, mantendo o `throw` combinado no fim para o que faltar:

```powershell
foreach ($name in $encoders) {
    if ($encoderText -notmatch ("\b" + [regex]::Escape($name) + "\b")) { $missing += "encoder '$name'" }
    else { Write-LauncherLog "Encoder '$name' disponivel." "Success" }
}
# idem para $filters, com "Filtro '$name' disponivel."
```

**(g) `Resolve-Binaries`** — inserir `Test-ExecutableRuns` logo depois de cada
`Test-RequiredBinary` de ffmpeg/ffprobe, mais um log de sucesso na existência (hoje
`Test-RequiredBinary` é silencioso no sucesso):

```powershell
Test-RequiredBinary -Path $ffmpeg -Name "ffmpeg.exe" -FixHint "..." | Out-Null
Write-LauncherLog "FFmpeg encontrado." "Success"
Test-ExecutableRuns -Path $ffmpeg -Name "FFmpeg"

Test-RequiredBinary -Path $ffprobe -Name "ffprobe.exe" -FixHint "..." | Out-Null
Write-LauncherLog "FFprobe encontrado." "Success"
Test-ExecutableRuns -Path $ffprobe -Name "FFprobe"

Test-FfmpegCapabilities -Ffmpeg $ffmpeg -Config $Config
```

(A ordem exata dos dois `Write-LauncherLog`+`Test-ExecutableRuns` por binário fica a critério
do executor; o que importa é: existência → log → executa, para cada um, antes de
`Test-FfmpegCapabilities`.)

### O que fica igual (preservado sem mudança de código)

Itens 7–10, 12–14 do pedido do usuário são guardrails, não tarefas:

- **Não** reintroduzir `-InputFile`/`-Profile`/`batch`. Launcher continua abrindo só
  `Reels_Encoder_v2_FINAL.py --ui`.
- **Não** alterar `ui/binaries.py` nem o contrato `REELS_FFMPEG`/`REELS_FFPROBE`.
- **Não** chamar `Set-ExecutionPolicy` nem alterar política permanente.
- **Não** substituir o mecanismo de stamp (SHA-256 requirements+pyproject). Ele só deixa de
  ser suficiente sozinho — e isso já é o caso desde a BB, nada muda aqui.
- **Não** mexer em `$PSNativeCommandUseErrorActionPreference = $false` (linha 21).
- **Não** mexer em `Open-LauncherTabs`, `Resolve-LauncherShell`, `preferPwsh`/`noProfile`.
- **Não** mexer em `Protect-PSLiteral` nem em `Build-SetupCommand`/`Build-AppCommand` — as
  novas checagens invocam `&` direto (como `Test-VenvHealthy`/`Test-VenvConsistent` já fazem),
  nenhuma monta string interpolada nova.
- **Não** mexer em `$Config = $null` de `Install-Requirements`/`Initialize-Environment` — os 4
  testes de `Context 'quando o venv nao existe'` dependem disso (mesma ressalva da BB).

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| **BC1** | Implementar (a)–(g) do § Desenho | executor-pesado | `launcher.ps1` | `Select-String '\$Debug\b' launcher.ps1` → 0 linhas (só `$DebugMode` sobra); `Select-String 'PathType Leaf' launcher.ps1` → 1 linha; `Test-ExecutableRuns`/`Get-VenvPythonVersion` definidas e chamadas nos pontos do desenho; `Parser::ParseFile` sem erros |
| **BC2** | Testes — ver § "Mudanças na suíte" | executor-pesado | `tests/launcher.Tests.ps1` | suíte verde nos 3 jobs Pester; contagem sobe do valor atual (confirmar com `Invoke-Pester` antes de editar) |
| **BC3** | Anexar `## Ciclo BC` ao `STATE.md` com resultado + SHAs | Orquestrador | `.claude/memory/STATE.md` | — |

BC1 e BC2 podem ser um único commit por arquivo (como na BB) ou combinados — critério é
`git diff main --stat` tocar só os dois arquivos de código, memória em commit separado.

## Mudanças na suíte (especificação da BC2)

Todas em `tests/launcher.Tests.ps1`, seguindo a convenção já estabelecida (mock das
funções-wrapper, nunca do binário nativo — ver comentário de cabeçalho do arquivo).

**Cabeçalho do arquivo (linhas 9–18).** Acrescentar `Get-VenvPythonVersion` e
`Test-ExecutableRuns` à lista de superfícies não-testáveis diretamente (native invocation via
variável), mesma razão já documentada para `Test-VenvHealthy`/`Test-VenvConsistent`.

**Rename `-Debug` → `-DebugMode`.** No teste `It 'suprime o nivel Debug quando -Debug nao foi
passado'` (linha 601) e no comentário interno (602-604): atualizar nome do teste e do
comentário para `$DebugMode`. O comentário passa a explicar que o rename elimina a colisão —
não que ela é evitada por ausência de `[CmdletBinding()]`.

**`Describe 'Initialize-Environment'` — mock novo em todos os Contexts que passam por
`$healthy = $true`** (`'venv existe, saudavel, stamp confere'` linha 242, `'... stamp difere'`
linha 286, `'quando o venv nao existe'` linha 357, `'com -Force'` linha 400, `'pip check
reprova depois do install'` linha 421): acrescentar `Mock Get-VenvPythonVersion { return
[version]'3.12.0' }` ao `BeforeAll`. Sem esse mock a função real tentaria `& 'VENV\Scripts\
python.exe' -c ...` num caminho que não existe.

No Context `'venv existe mas nao esta saudavel'` (linha 329, `$healthy = $false`): acrescentar
o mesmo mock (inofensivo, não deve ser invocado) e uma asserção nova — **`It 'nao chama
Get-VenvPythonVersion quando o venv nao esta saudavel'`**: `Should -Invoke
Get-VenvPythonVersion -Times 0 -Exactly`. Prova que o gate de versão só roda depois de
confirmar que o Python inicia.

**Context novo — `'Python do venv abaixo do minimo'`:** mocks iguais ao Context `'stamp
confere'`, exceto `Mock Get-VenvPythonVersion { return [version]'3.9.0' }` (config real usada
pelos testes tem `minPythonVersion: "3.11"`, ver `$script:Config`). Três asserções:

1. `It 'lanca excecao'` — `{ Initialize-Environment ... } | Should -Throw`.
2. `It 'nao instala nada (nao tenta corrigir sozinho)'` — `Should -Invoke Install-Requirements
   -Times 0 -Exactly`. **Fecha o Caso 5** (não reutiliza, não corrige sozinho).
3. `It 'a mensagem de erro nomeia encontrado e minimo'` — `{ ... } | Should -Throw -ExpectedMessage
   '*3.9.0*'` e variante/segunda asserção para `'*3.11*'` (Pester só casa um padrão por
   `-ExpectedMessage`; usar `-ErrorId`/captura de exceção com `try/catch` + duas asserções
   `Should -Match`, a critério do executor).

**`Describe 'Resolve-Binaries'` — os dois Contexts existentes** (`'todos os binarios
presentes'` linha 462, `'Windows Terminal ausente'` linha 511): acrescentar `Mock
Test-ExecutableRuns { }` ao `BeforeAll`. `Should -Invoke Test-RequiredBinary -Times 3
-Exactly` continua válido (contagem não muda).

**Context novo em `Resolve-Binaries` — `'ffmpeg nao consegue iniciar'`:** mocks iguais a
`'todos os binarios presentes'`, exceto `Mock Test-ExecutableRuns { throw "FFmpeg nao
conseguiu iniciar." } -ParameterFilter { $Name -eq 'FFmpeg' }`. Asserção: `It 'propaga a
excecao'` — `{ Resolve-Binaries ... } | Should -Throw`; `It 'nao chega a checar capacidades'`
— `Should -Invoke Test-FfmpegCapabilities -Times 0 -Exactly`.

**`Describe 'Test-RequiredBinary'` (novo bloco, função hoje sem `Describe` próprio).** Usa
`TestDrive:` do Pester (filesystem real, sem mock — é lógica pura de `Test-Path`):

- `It 'aceita um arquivo existente'` — cria `TestDrive:\fake.exe` (`New-Item -ItemType File`),
  `Test-RequiredBinary -Path 'TestDrive:\fake.exe' -Name x -FixHint y` não lança.
- `It 'rejeita um diretorio com nome de executavel'` — cria `TestDrive:\fake.exe` como
  **diretório** (`New-Item -ItemType Directory`), `Test-RequiredBinary` **lança**. **Esta é a
  asserção que fecha o item 6** (`-PathType Leaf` distingue diretório de arquivo).
- `It 'rejeita caminho inexistente'` — comportamento já existente, sem regressão.

## Critérios de aceite

1. Suíte verde nos 3 jobs Pester (`ubuntu-latest`, `windows-latest` pwsh 7, `Windows
   PowerShell 5.1`) + `lint` + `tests`.
2. `.\launcher.ps1` e `.\launcher.ps1 -DebugMode` funcionam sem erro relacionado ao parâmetro
   (verificação manual do usuário, não testável em CI — mesma natureza do critério 6 da BB).
3. Casos 3–8 do pedido do usuário cobertos pelos testes da § "Mudanças na suíte" (venv
   saudável+versão+pip check+stamp → pula install; pip check falha → reinstala; versão abaixo
   do mínimo → não reutiliza; FFmpeg/FFprobe não iniciam → erro claro; capacidade FFmpeg
   ausente → aborta com mensagem clara — este já coberto por teste existente da AX, não
   recriar).
4. `git diff main --stat` toca exatamente `launcher.ps1` e `tests/launcher.Tests.ps1`; memória
   em commit próprio.
5. Nenhuma construção só-pwsh-7 (`??`, ternário, `&&`, `||`, `-Parallel`, `-AsHashtable`).
6. `QF1` não volta: toda invocação nativa nova (`Get-VenvPythonVersion`, `Test-ExecutableRuns`)
   usa o guard `$ErrorActionPreference = "Continue"` + `finally`.

## Notas de execução

- **Branch:** recriar `claude/launcher-encoder-architecture-jzyyu8` a partir do `main`
  (`git fetch origin main && git checkout -B claude/launcher-encoder-architecture-jzyyu8
  origin/main`) — mesmo nome reaproveitado nos ciclos AX–BB, apagada após o merge da BB. PR
  **novo**.
- Sem `pwsh` no container do Orquestrador: quem valida é o CI. O `executor-pesado` roda
  `Invoke-Pester -Path ./tests` localmente se tiver PowerShell; senão, confia nos 3 jobs.
- Commits: `BC1` → `BC2` → `BC3` (memória, `[skip ci]` **só se não for o commit-topo do push**
  — ver nota abaixo).
- **Armadilha do Ciclo BB a não repetir:** se o commit de memória (`[skip ci]`) for o topo do
  push, o GitHub Actions pula o workflow inteiro para esse push, inclusive no evento
  `pull_request` — o CI real não roda. Ou não usar `[skip ci]` no commit de memória, ou
  garantir que ele não seja o último commit pusheado antes de abrir/atualizar o PR.
- **Nunca `git add -A` nem `git add .`.** Adicionar por caminho explícito.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
