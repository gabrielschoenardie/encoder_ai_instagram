# Testes Pester para o Launcher Portátil Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Delegação (política deste repo, `CLAUDE.md`):** cada task abaixo lista um
> **Agent** — despache via Task para esse agente exato (`executor` ou
> `executor-pesado`), não para um subagente genérico. Nenhuma task edita
> `launcher.ps1`, `launch-config.json`, `Reels_Encoder_v2_FINAL.py`, `enhance/`
> ou `ui/`.

**Goal:** Cobertura automatizada para `launcher.ps1` — o caminho de entrada
comercial do produto, hoje com zero teste. Suíte Pester 5 em `tests/`, rodando
em CI nos dois sistemas operacionais, cobrindo as funções puras de montagem de
comando, os orquestradores (via mock das próprias funções do script), o
contrato do `launch-config.json` e o fallback de lançamento sem Windows
Terminal — **sem tocar em uma linha de `launcher.ps1`**.

**Architecture:** `launcher.ps1:270` (`if ($MyInvocation.InvocationName -ne '.')`)
já separa "definir as 14 funções" de "rodar o bootstrap": dot-source carrega
tudo sem executar nada. Dois arquivos novos — `tests/launch-config.Tests.ps1`
(contrato de dados, sem dot-source) e `tests/launcher.Tests.ps1` (funções, via
dot-source em `BeforeAll`) — mais um job novo no CI. Estratégia de mock em duas
camadas: mockar as **próprias funções do script** para testar orquestradores
(`Initialize-Environment`, `Resolve-Binaries`), e mockar **cmdlets**
(`Test-Path`, `Start-Process`, `Write-Host`) para as near-pure.

**Tech Stack:** Pester 5.5+ (dev/CI-only, nunca dependência de runtime),
PowerShell Core (`pwsh`) nos runners ubuntu e windows do GitHub Actions,
`$TestDrive` para I/O de arquivo temporário. Nenhum pacote Python novo.

## Global Constraints

- `launcher.ps1` e `launch-config.json` são **read-only** neste ciclo. Se um
  teste for difícil de escrever, ajusta-se o teste ou declara-se a superfície
  não-testável — nunca o script de produção (`CLAUDE.md` § Anti-escopo).
- Nenhum arquivo Python é tocado. A suíte pytest atual deve terminar o ciclo
  com **exatamente o mesmo número de testes** com que começou.
- Nenhuma asserção de igualdade literal sobre caminho montado com `Join-Path`
  — `Join-Path` produz `/` no Linux e `\` no Windows. Usar sempre `-match` no
  nome do arquivo.
- Nenhuma asserção sobre campo de texto acentuado (`description` do
  `launch-config.json`): arquivo UTF-8 sem BOM lido por Windows PowerShell 5.1
  vira ANSI, e o valor chega mojibake. Só campos ASCII.
- Nenhuma tentativa de mockar `& $pythonCmd`, `& $VenvPython` ou `& $WtPath` —
  `Mock` engancha em nomes de comando, e caminho vindo de variável resolve como
  Application em runtime. Superfície declarada não-testável no spec.
- `$IsWindows` não existe em Windows PowerShell 5.1 — todo teste que precisar
  saber o SO usa `$script:OnWindows = if ($null -eq $IsWindows) { $true } else { $IsWindows }`.
- O dot-source de `launcher.ps1` vaza `$ErrorActionPreference = "Stop"` na
  sessão de teste — salvar e restaurar em `BeforeAll`/`AfterAll`.
- Fixtures nunca usam nomes/diretórios engolidos pelo `.gitignore` (`*.log`,
  `*.csv`, `*.tmp`, `temp/`, `tmp/`, `cache/`, `output*/`) — usar `$TestDrive`.
- **Não há `pwsh` no sandbox de desenvolvimento.** Nenhuma task 1-5 consegue
  colar saída local real; a evidência vem do CI (Task 6). Ver "Notas de
  execução" no `.claude/memory/PLAN.md` deste ciclo.
- Spec completo: `docs/superpowers/specs/2026-08-14-pester-launcher-design.md`.

---

## File Structure

```text
encoder_ai_instagram/
├── launcher.ps1                        ← intocado (read-only neste ciclo)
├── launch-config.json                  ← intocado (read-only neste ciclo)
├── tests/                              ← novo (Task 1)
│   ├── launch-config.Tests.ps1         ← novo (Task 1)
│   └── launcher.Tests.ps1              ← novo (Task 2), estendido (Tasks 3, 4)
├── .github/workflows/ci.yml            ← +1 job `pester` (Task 5)
└── .claude/memory/
    ├── STATE.md                        ← +1 seção "Ciclo U" (Task 6)
    └── FINDINGS.md                      ← achados novos `UF*`, se houver (Task 6)
```

---

### Task 1: `tests/launch-config.Tests.ps1` — contrato do JSON

**Agent:** `executor`

**Files:**
- Create: `tests/launch-config.Tests.ps1`

**Interfaces:**
- Consumes: `launch-config.json` na raiz do repo (read-only).
- Produces: nenhuma API — arquivo de teste puro. 100% OS-independente: não faz
  dot-source de `launcher.ps1`, não usa mock, não toca em disco além de
  `Test-Path`.

- [ ] **Step 1: Criar o diretório `tests/` e escrever o arquivo com o conteúdo exato abaixo**

```powershell
<#
    Contrato do launch-config.json.

    Nao carrega launcher.ps1 - so le e valida o dado. Por isso e 100%
    independente de SO e do motor de PowerShell: roda igual em pwsh 7
    (ubuntu-latest) e em pwsh/5.1 (windows-latest).
#>

BeforeAll {
    $script:RepoRootDir = Split-Path -Parent $PSScriptRoot
    $script:ConfigPath  = Join-Path $script:RepoRootDir 'launch-config.json'
    $script:Raw         = Get-Content -Path $script:ConfigPath -Raw
    $script:Config      = $script:Raw | ConvertFrom-Json
    $script:ProfileNames = @($script:Config.profiles.PSObject.Properties.Name)
}

Describe 'launch-config.json — estrutura' {

    It 'existe na raiz do repositorio' {
        Test-Path $script:ConfigPath | Should -BeTrue -Because "esperado em: $($script:ConfigPath)"
    }

    It 'e JSON valido' {
        { $script:Raw | ConvertFrom-Json } | Should -Not -Throw
    }

    It 'declara as tres chaves de topo' {
        $top = @($script:Config.PSObject.Properties.Name)
        $top | Should -Contain 'defaultProfile'
        $top | Should -Contain 'profiles'
        $top | Should -Contain 'paths'
    }
}

Describe 'launch-config.json — perfis' {

    It 'defaultProfile aponta para um perfil que existe' {
        $script:Config.defaultProfile | Should -Not -BeNullOrEmpty
        $script:ProfileNames | Should -Contain $script:Config.defaultProfile
    }

    It 'define exatamente 5 perfis' {
        $script:ProfileNames.Count | Should -Be 5
    }

    It 'define o perfil <_>' -ForEach @('fast', 'balanced', 'quality', 'cinematic', 'batch') {
        $script:ProfileNames | Should -Contain $_
    }

    It 'perfil <Name> tem flags nao-vazias e um campo description' -ForEach @(
        @{ Name = 'fast' }
        @{ Name = 'balanced' }
        @{ Name = 'quality' }
        @{ Name = 'cinematic' }
        @{ Name = 'batch' }
    ) {
        $def = $script:Config.profiles.$Name
        $def | Should -Not -BeNullOrEmpty
        @($def.flags).Count | Should -BeGreaterThan 0

        # 'description' e verificado so por PRESENCA, nunca por valor. Os
        # valores tem acentos ("Preview rapido", "Padrao recomendado",
        # "Maxima qualidade") e o arquivo e UTF-8 SEM BOM; Windows PowerShell
        # 5.1 le arquivo sem BOM como ANSI e entrega o texto mojibake.
        # Comparar o valor daria falso negativo so no leg windows da matriz.
        @($def.PSObject.Properties.Name) | Should -Contain 'description'
    }

    It 'nenhum perfil define --crf' {
        # Regra de Ouro do projeto (skill instagram-reels-encoder): CRF e
        # decidido pela analise adaptativa do encoder, nunca fixado por preset.
        # Esta asseracao teria pego o bug do rascunho original do launcher, que
        # propunha "--crf 18/23/28" - flag que nem existe no argparse do
        # encoder (ver docs/superpowers/specs/2026-08-13-launcher-portavel-design.md
        # § "Divergencias do rascunho original", item 1).
        $allFlags = @()
        foreach ($n in $script:ProfileNames) {
            $allFlags += @($script:Config.profiles.$n.flags)
        }
        $allFlags | Should -Not -Contain '--crf'
    }

    It 'apenas o perfil batch declara requiresBatchDir' {
        foreach ($n in $script:ProfileNames) {
            $requires = [bool]$script:Config.profiles.$n.requiresBatchDir
            if ($n -eq 'batch') {
                $requires | Should -BeTrue -Because 'o perfil batch processa uma pasta inteira'
            }
            else {
                $requires | Should -BeFalse -Because "o perfil '$n' recebe um arquivo, nao uma pasta"
            }
        }
    }
}

Describe 'launch-config.json — paths' {

    It 'declara todas as chaves esperadas' {
        $names = @($script:Config.paths.PSObject.Properties.Name)
        foreach ($k in @('venv', 'ffmpegExe', 'ffprobeExe', 'windowsTerminalExe', 'requirements', 'encoderScript')) {
            $names | Should -Contain $k
        }
    }

    It 'todo valor de paths e uma string nao-vazia' {
        foreach ($p in $script:Config.paths.PSObject.Properties) {
            $p.Value | Should -BeOfType [string]
            [string]::IsNullOrWhiteSpace($p.Value) | Should -BeFalse -Because "paths.$($p.Name) nao pode ser vazio"
        }
    }

    It 'paths.encoderScript aponta para um arquivo que existe na raiz' {
        $target = Join-Path $script:RepoRootDir $script:Config.paths.encoderScript
        Test-Path $target | Should -BeTrue -Because "esperado em: $target"
    }

    It 'paths.requirements aponta para um arquivo que existe na raiz' {
        $target = Join-Path $script:RepoRootDir $script:Config.paths.requirements
        Test-Path $target | Should -BeTrue -Because "esperado em: $target"
    }
}
```

- [ ] **Step 2: Verificar que o arquivo não foi engolido pelo `.gitignore`**

Run: `git check-ignore -v tests/launch-config.Tests.ps1; echo "EXIT=$?"`
Expected: `EXIT=1` e nenhuma linha de regra impressa — `git check-ignore` sai
com 1 quando o caminho **não** é ignorado. Se sair `EXIT=0` com uma regra, o
arquivo está sendo ignorado e nada abaixo funcionará; parar e reportar.

- [ ] **Step 3: Verificar que nenhum arquivo Python foi tocado**

Run: `git status --short`
Expected: apenas `?? tests/` (untracked). Nenhuma linha `M` para `.py`,
`launcher.ps1`, `launch-config.json` ou `ci.yml`.

- [ ] **Step 4: Commit**

```bash
git add tests/launch-config.Tests.ps1
git commit -m "test(launcher): contrato Pester do launch-config.json (5 perfis, sem --crf)"
```

---

### Task 2: `tests/launcher.Tests.ps1` — dot-source + funções puras `Build-*`

**Agent:** `executor`

**Files:**
- Create: `tests/launcher.Tests.ps1`

**Interfaces:**
- Consumes: `launcher.ps1` via dot-source (`Build-ProfileArgs`,
  `Build-SetupCommand`, `Build-EncodeCommand`), `launch-config.json` real.
- Produces: o `BeforeAll` de topo do arquivo, que define `$script:RepoRootDir`,
  `$script:OnWindows` e `$script:Config` — as Tasks 3 e 4 acrescentam
  `Describe` novos **no mesmo arquivo**, reutilizando esse `BeforeAll` sem
  duplicá-lo e sem editá-lo.

- [ ] **Step 1: Escrever o arquivo com o conteúdo exato abaixo**

```powershell
<#
    Testes das funcoes de launcher.ps1.

    O arquivo e carregado por dot-source. launcher.ps1:270 tem o guard
    "if ($MyInvocation.InvocationName -ne '.')": sob dot-source a condicao e
    falsa, entao as 14 funcoes sao definidas e NADA do bootstrap roda (nenhum
    venv criado, nenhum pip, nenhuma janela aberta).

    Superficies deliberadamente NAO cobertas aqui (ver o spec
    docs/superpowers/specs/2026-08-14-pester-launcher-design.md
    § "Superficies nao-testaveis"): New-ProjectVenv, Install-Requirements,
    Write-VenvLock e o ramo wt.exe de Open-LauncherTabs usam
    "& $variavelComCaminho". O Mock do Pester engancha em NOMES de comando; um
    caminho vindo de variavel resolve como Application em runtime e nunca passa
    pelo mock. A evidencia dessas superficies e execucao real registrada em
    .claude/memory/STATE.md §§ "Ciclo Q", "Ciclo S", "Ciclo T".
#>

BeforeAll {
    # launcher.ps1 seta $ErrorActionPreference = "Stop" no escopo em que e
    # carregado. Sob "Stop", qualquer erro nao-terminante do proprio Pester
    # vira falha e mascara a causa real - por isso salvamos e restauramos.
    $script:PrevEap = $ErrorActionPreference

    $script:RepoRootDir = Split-Path -Parent $PSScriptRoot
    . (Join-Path $script:RepoRootDir 'launcher.ps1')

    $ErrorActionPreference = $script:PrevEap

    # $IsWindows so existe em PowerShell Core. Em Windows PowerShell 5.1 ela e
    # $null - e 5.1 so roda em Windows, entao $null implica Windows.
    $script:OnWindows = if ($null -eq $IsWindows) { $true } else { $IsWindows }

    $script:Config = Get-Content -Path (Join-Path $script:RepoRootDir 'launch-config.json') -Raw |
        ConvertFrom-Json
}

AfterAll {
    $ErrorActionPreference = $script:PrevEap
}

Describe 'Contrato de dot-source' {

    It 'define a funcao <_>' -ForEach @(
        'Write-LauncherLog'
        'Read-LauncherConfig'
        'Test-VenvExists'
        'Resolve-SystemPython'
        'New-ProjectVenv'
        'Install-Requirements'
        'Write-VenvLock'
        'Initialize-Environment'
        'Test-RequiredBinary'
        'Resolve-Binaries'
        'Build-ProfileArgs'
        'Build-SetupCommand'
        'Build-EncodeCommand'
        'Open-LauncherTabs'
    ) {
        Get-Command $_ -CommandType Function -ErrorAction SilentlyContinue |
            Should -Not -BeNullOrEmpty -Because "dot-source de launcher.ps1 deveria definir $_"
    }

    It 'carrega o launch-config.json real do repositorio' {
        $script:Config.defaultProfile | Should -Be 'balanced'
    }

    It 'sabe em qual SO esta rodando' {
        $script:OnWindows | Should -BeOfType [bool]
    }
}

Describe 'Build-ProfileArgs' {

    It 'monta as flags exatas do perfil <Name>' -ForEach @(
        @{ Name = 'fast';      Expected = '--performance speed --enhance off' }
        @{ Name = 'balanced';  Expected = '--performance balanced --enhance on --enhance-ai on' }
        @{ Name = 'quality';   Expected = '--performance quality --mode 2pass --enhance on' }
        @{ Name = 'cinematic'; Expected = '--cineon-pipeline on --exposure-offset +0.2 --saturation 1.05 --mode 2pass' }
    ) {
        $result = Build-ProfileArgs -ProfileName $Name -Config $script:Config
        ($result -join ' ') | Should -Be $Expected
    }

    It 'lanca para um perfil que nao existe' {
        { Build-ProfileArgs -ProfileName 'inexistente' -Config $script:Config } |
            Should -Throw -ExpectedMessage "*Perfil 'inexistente' nao existe*"
    }

    It 'lista os perfis validos na mensagem de erro' {
        { Build-ProfileArgs -ProfileName 'inexistente' -Config $script:Config } |
            Should -Throw -ExpectedMessage '*fast, balanced, quality, cinematic, batch*'
    }

    It 'lanca quando o perfil batch e usado sem pasta de entrada' {
        { Build-ProfileArgs -ProfileName 'batch' -Config $script:Config } |
            Should -Throw -ExpectedMessage '*exige uma pasta de entrada*'
    }

    It 'prefixa --batch/--output-dir quando o perfil batch recebe -BatchDir' {
        # MYCLIPS e um token sem separador de path de proposito: a string e
        # repassada literalmente pela funcao, entao o teste roda igual nos
        # dois SOs sem depender de "/" vs "\".
        $result = Build-ProfileArgs -ProfileName 'batch' -Config $script:Config -BatchDir 'MYCLIPS'
        ($result -join ' ') | Should -Be '--batch MYCLIPS --output-dir MYCLIPS --enhance on'
    }

    It 'nenhum perfil produz --crf' {
        foreach ($n in @('fast', 'balanced', 'quality', 'cinematic')) {
            Build-ProfileArgs -ProfileName $n -Config $script:Config | Should -Not -Contain '--crf'
        }
        Build-ProfileArgs -ProfileName 'batch' -Config $script:Config -BatchDir 'MYCLIPS' |
            Should -Not -Contain '--crf'
    }
}

Describe 'Build-SetupCommand' {

    It 'pede o diagnostico de hardware' {
        Build-SetupCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Match '--hardware-info'
    }

    It 'referencia o script do encoder' {
        # Join-Path devolve "ROOT/Reels_..." no Linux e "ROOT\Reels_..." no
        # Windows. Por isso -match no NOME do arquivo, nunca -eq no caminho
        # inteiro montado a mao.
        Build-SetupCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Match 'Reels_Encoder_v2_FINAL\.py'
    }

    It 'referencia o interpretador recebido' {
        Build-SetupCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Match 'PY'
    }

    It 'nao inclui flag de perfil nenhuma' {
        Build-SetupCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Not -Match '--performance'
    }
}

Describe 'Build-EncodeCommand' {

    It 'sem perfil, abre o wizard interativo (--ui)' {
        $cmd = Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile '' -ProfileName $null
        $cmd | Should -Match '--ui'
        $cmd | Should -Match 'Reels_Encoder_v2_FINAL\.py'
    }

    It 'sem perfil, nao inclui flags de perfil' {
        Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile '' -ProfileName $null |
            Should -Not -Match '--performance'
    }

    It 'com perfil e input, inclui o arquivo de entrada' {
        Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile 'video.mp4' -ProfileName 'fast' |
            Should -Match 'video\.mp4'
    }

    It 'com perfil e input, inclui as flags do perfil e nao abre o wizard' {
        $cmd = Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile 'video.mp4' -ProfileName 'fast'
        $cmd | Should -Match '--performance speed'
        $cmd | Should -Match '--enhance off'
        $cmd | Should -Not -Match '--ui'
    }

    It 'perfil cinematic monta a cadeia Cineon completa' {
        $cmd = Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile 'video.mp4' -ProfileName 'cinematic'
        $cmd | Should -Match '--cineon-pipeline on'
        $cmd | Should -Match '--exposure-offset \+0\.2'
        $cmd | Should -Match '--saturation 1\.05'
        $cmd | Should -Match '--mode 2pass'
    }

    It 'perfil batch usa --batch/--output-dir e OMITE o arquivo de entrada' {
        $cmd = Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -InputFile 'MYCLIPS' -ProfileName 'batch'
        $cmd | Should -Match '--batch MYCLIPS'
        $cmd | Should -Match '--output-dir MYCLIPS'
        # no modo batch a pasta vai so nas flags; nunca como argumento
        # posicional entre aspas simples logo depois do script.
        $cmd | Should -Not -Match "'MYCLIPS'"
    }

    It 'nenhum comando montado contem --crf' {
        foreach ($n in @('fast', 'balanced', 'quality', 'cinematic')) {
            Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
                -InputFile 'video.mp4' -ProfileName $n | Should -Not -Match '--crf'
        }
    }
}
```

- [ ] **Step 2: Verificar que `launcher.ps1` e `launch-config.json` continuam byte-a-byte intactos**

Run: `git diff --stat -- launcher.ps1 launch-config.json`
Expected: saída vazia. Qualquer linha aqui viola a Global Constraint de
read-only e deve ser revertida (`git checkout -- launcher.ps1 launch-config.json`)
antes de prosseguir.

- [ ] **Step 3: Verificar que não há `pwsh` disponível (registrar a limitação explicitamente, não assumir)**

Run: `command -v pwsh || echo "NO_PWSH"`
Expected: `NO_PWSH`. Se por acaso `pwsh` **existir** neste ambiente, rodar
`pwsh -c "Install-Module Pester -MinimumVersion 5.5.0 -Force -Scope CurrentUser -SkipPublisherCheck; Invoke-Pester -Path ./tests -CI"`
e colar a saída real — nesse caso a limitação documentada não se aplica e a
evidência local passa a existir. Reportar qual dos dois casos ocorreu.

- [ ] **Step 4: Commit**

```bash
git add tests/launcher.Tests.ps1
git commit -m "test(launcher): dot-source + funcoes puras Build-ProfileArgs/SetupCommand/EncodeCommand"
```

---

### Task 3: `tests/launcher.Tests.ps1` — orquestradores via mock das próprias funções

**Agent:** `executor`

**Files:**
- Modify: `tests/launcher.Tests.ps1` (acrescentar `Describe` novos **no fim do
  arquivo**; não editar o `BeforeAll`/`AfterAll` de topo nem os `Describe` da
  Task 2)

**Interfaces:**
- Consumes: `$script:Config` e as funções carregadas pelo `BeforeAll` da Task 2.
- Produces: cobertura de `Initialize-Environment` (decisão criar-vs-reaproveitar
  venv) e `Resolve-Binaries` (shape do objeto e tratamento do binário opcional).
  Os nomes mockados são exatamente os definidos em `launcher.ps1`:
  `Test-VenvExists` (l. 61), `New-ProjectVenv` (l. 74), `Install-Requirements`
  (l. 95), `Write-VenvLock` (l. 119), `Test-RequiredBinary` (l. 153),
  `Write-LauncherLog` (l. 24).

- [ ] **Step 1: Acrescentar os dois `Describe` abaixo ao final de `tests/launcher.Tests.ps1`**

```powershell

Describe 'Initialize-Environment' {

    # Pester 5 consegue mockar funcoes definidas por dot-source na mesma
    # sessao. E isso que permite testar a DECISAO do orquestrador (criar venv
    # vs. reaproveitar) sem criar venv nenhum, sem rede e sem pip - as funcoes
    # que de fato invocam "& $python" ficam substituidas por no-ops.

    Context 'quando o venv ja existe' {

        BeforeAll {
            Mock Test-VenvExists     { return $true }
            Mock New-ProjectVenv     { }
            Mock Install-Requirements { }
            Mock Write-VenvLock      { }
            Mock Write-LauncherLog   { }
        }

        It 'nao recria o venv' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke New-ProjectVenv -Times 0 -Exactly
        }

        It 'ainda assim instala as dependencias (idempotente)' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly
        }

        It 'ainda assim regrava o venv.lock (diagnostico)' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke Write-VenvLock -Times 1 -Exactly
        }

        It 'retorna o caminho do python dentro do venv informado' {
            $py = Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV'
            # Join-Path 'VENV' 'Scripts\python.exe' muda de forma entre SOs;
            # asseveramos os dois pedacos estaveis, nunca o caminho inteiro.
            $py | Should -Match 'python'
            $py | Should -Match 'VENV'
        }

        It 'passa adiante o mesmo interpretador para install e lock' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly -ParameterFilter {
                $VenvPython -match 'python'
            }
        }
    }

    Context 'quando o venv nao existe' {

        BeforeAll {
            Mock Test-VenvExists     { return $false }
            Mock New-ProjectVenv     { }
            Mock Install-Requirements { }
            Mock Write-VenvLock      { }
            Mock Write-LauncherLog   { }
        }

        It 'cria o venv exatamente uma vez' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke New-ProjectVenv -Times 1 -Exactly
        }

        It 'cria o venv no caminho recebido' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke New-ProjectVenv -Times 1 -Exactly -ParameterFilter {
                $VenvPath -eq 'VENV'
            }
        }

        It 'instala as dependencias depois de criar' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly
        }

        It 'retorna o caminho do python mesmo no caminho de criacao' {
            $py = Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV'
            $py | Should -Match 'python'
        }
    }
}

Describe 'Resolve-Binaries' {

    Context 'todos os binarios presentes' {

        BeforeAll {
            # Test-RequiredBinary real lancaria (os .exe nao existem no runner);
            # mockado, devolve o proprio caminho, como faz o original quando o
            # arquivo existe.
            Mock Test-RequiredBinary { return $Path }
            # Filtro estreito de proposito: mockar Test-Path sem filtro
            # substituiria a chamada para QUALQUER caminho, inclusive de codigo
            # que nao e o alvo do teste.
            Mock Test-Path { return $true } -ParameterFilter { $Path -match 'wt\.exe' }
            Mock Write-LauncherLog { }
        }

        It 'devolve os cinco membros do contrato' {
            $r = Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config
            $names = @($r.PSObject.Properties.Name)
            foreach ($m in @('VenvPython', 'Ffmpeg', 'Ffprobe', 'WtPath', 'WtAvailable')) {
                $names | Should -Contain $m
            }
        }

        It 'propaga o interpretador recebido' {
            (Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config).VenvPython |
                Should -Be 'PY'
        }

        It 'resolve ffmpeg, ffprobe e wt a partir do launch-config.json' {
            $r = Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config
            $r.Ffmpeg  | Should -Match 'ffmpeg\.exe'
            $r.Ffprobe | Should -Match 'ffprobe\.exe'
            $r.WtPath  | Should -Match 'wt\.exe'
        }

        It 'marca WtAvailable como verdadeiro' {
            (Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config).WtAvailable |
                Should -BeTrue
        }

        It 'valida os tres binarios obrigatorios (python, ffmpeg, ffprobe)' {
            Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config | Out-Null
            Should -Invoke Test-RequiredBinary -Times 3 -Exactly
        }
    }

    Context 'Windows Terminal ausente (binario opcional)' {

        BeforeAll {
            Mock Test-RequiredBinary { return $Path }
            Mock Test-Path { return $false } -ParameterFilter { $Path -match 'wt\.exe' }
            Mock Write-LauncherLog { }
        }

        It 'marca WtAvailable como falso' {
            (Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config).WtAvailable |
                Should -BeFalse
        }

        It 'nao lanca excecao — wt.exe e opcional, nao obrigatorio' {
            { Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config } |
                Should -Not -Throw
        }

        It 'ainda devolve o WtPath calculado (para o fallback poder logar)' {
            (Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config).WtPath |
                Should -Match 'wt\.exe'
        }

        It 'avisa o usuario em nivel Warn' {
            Resolve-Binaries -RepoRoot 'ROOT' -VenvPython 'PY' -Config $script:Config | Out-Null
            Should -Invoke Write-LauncherLog -Times 1 -Exactly -ParameterFilter {
                $Level -eq 'Warn'
            }
        }
    }
}
```

- [ ] **Step 2: Verificar que os nomes mockados existem de fato em `launcher.ps1` (um erro de digitação aqui cria um mock que nunca dispara e um teste que passa sem testar nada)**

Run:
```bash
for f in Test-VenvExists New-ProjectVenv Install-Requirements Write-VenvLock \
         Test-RequiredBinary Write-LauncherLog Initialize-Environment Resolve-Binaries; do
  grep -q "^function $f {" launcher.ps1 && echo "OK   $f" || echo "MISS $f"
done
```
Expected: oito linhas `OK`, nenhuma `MISS`.

- [ ] **Step 3: Verificar que `launcher.ps1` continua intocado**

Run: `git diff --stat -- launcher.ps1 launch-config.json`
Expected: saída vazia.

- [ ] **Step 4: Commit**

```bash
git add tests/launcher.Tests.ps1
git commit -m "test(launcher): orquestradores Initialize-Environment e Resolve-Binaries via mock"
```

---

### Task 4: `tests/launcher.Tests.ps1` — config loader, logging e fallback de lançamento

**Agent:** `executor`

**Files:**
- Modify: `tests/launcher.Tests.ps1` (acrescentar `Describe` novos **no fim do
  arquivo**; não editar nada escrito nas Tasks 2 e 3)

**Interfaces:**
- Consumes: `Read-LauncherConfig`, `Write-LauncherLog`, `Open-LauncherTabs`
  carregadas pelo `BeforeAll` da Task 2; `$TestDrive` (drive temporário que o
  Pester cria e limpa sozinho — evita qualquer fixture em disco do repo, e
  portanto qualquer colisão com o `.gitignore`).
- Produces: cobertura do último bloco testável de `launcher.ps1`. Depois desta
  task, tudo que resta sem cobertura são as três chamadas
  `& $variavelComCaminho` mais `Resolve-SystemPython`.

- [ ] **Step 1: Acrescentar os três `Describe` abaixo ao final de `tests/launcher.Tests.ps1`**

```powershell

Describe 'Read-LauncherConfig' {

    It 'lanca mensagem clara quando o arquivo nao existe' {
        { Read-LauncherConfig -Path (Join-Path $TestDrive 'nao-existe.json') } |
            Should -Throw -ExpectedMessage '*nao encontrado*'
    }

    It 'lanca mensagem clara quando o JSON esta malformado' {
        $bad = Join-Path $TestDrive 'malformado.json'
        '{ "defaultProfile": ' | Set-Content -Path $bad -Encoding utf8
        { Read-LauncherConfig -Path $bad } | Should -Throw -ExpectedMessage '*invalido*'
    }

    It 'parseia um JSON valido' {
        $good = Join-Path $TestDrive 'ok.json'
        '{ "defaultProfile": "balanced" }' | Set-Content -Path $good -Encoding utf8
        (Read-LauncherConfig -Path $good).defaultProfile | Should -Be 'balanced'
    }

    It 'carrega o launch-config.json real do repositorio' {
        $real = Read-LauncherConfig -Path (Join-Path $script:RepoRootDir 'launch-config.json')
        $real.defaultProfile | Should -Be 'balanced'
        @($real.profiles.PSObject.Properties.Name).Count | Should -Be 5
    }
}

Describe 'Write-LauncherLog' {

    BeforeAll {
        Mock Write-Host { }
    }

    It 'usa o prefixo [OK] no nivel Success' {
        Write-LauncherLog -Message 'msg' -Level 'Success'
        Should -Invoke Write-Host -Times 1 -Exactly -ParameterFilter { $Object -match '^\[OK\]' }
    }

    It 'usa o prefixo [ERRO] no nivel Error' {
        Write-LauncherLog -Message 'msg' -Level 'Error'
        Should -Invoke Write-Host -Times 1 -Exactly -ParameterFilter { $Object -match '^\[ERRO\]' }
    }

    It 'usa o prefixo [AVISO] no nivel Warn' {
        Write-LauncherLog -Message 'msg' -Level 'Warn'
        Should -Invoke Write-Host -Times 1 -Exactly -ParameterFilter { $Object -match '^\[AVISO\]' }
    }

    It 'usa o prefixo [INFO] no nivel padrao' {
        Write-LauncherLog -Message 'msg'
        Should -Invoke Write-Host -Times 1 -Exactly -ParameterFilter { $Object -match '^\[INFO\]' }
    }

    It 'inclui a mensagem recebida na saida' {
        Write-LauncherLog -Message 'CANARIO-123' -Level 'Info'
        Should -Invoke Write-Host -Times 1 -Exactly -ParameterFilter { $Object -match 'CANARIO-123' }
    }

    It 'suprime o nivel Debug quando -Debug nao foi passado' {
        # launcher.ps1 NAO declara [CmdletBinding()] (deliberado: evita colidir
        # com o [switch]$Debug explicito do param block). Logo $Debug e um
        # switch comum e, sob dot-source sem argumentos, vale $false.
        Write-LauncherLog -Message 'nao deve aparecer' -Level 'Debug'
        Should -Invoke Write-Host -Times 0 -Exactly
    }

    It 'rejeita um nivel fora do ValidateSet' {
        { Write-LauncherLog -Message 'msg' -Level 'Trace' } | Should -Throw
    }
}

Describe 'Open-LauncherTabs — fallback sem Windows Terminal' {

    # O ramo $WtAvailable = $true NAO e coberto, de proposito: ele invoca
    # "& $WtPath new-tab ...". O Mock do Pester engancha em nomes de comando;
    # um caminho vindo de variavel resolve como Application em runtime e nunca
    # passa pelo mock. Cobrir esse ramo exigiria refatorar launcher.ps1, o que
    # este ciclo proibe. Evidencia real do ramo wt.exe: .claude/memory/STATE.md
    # § "Ciclo Q" (2 abas abertas de verdade numa maquina Windows).

    BeforeAll {
        Mock Start-Process { }
        Mock Write-LauncherLog { }
    }

    It 'abre duas janelas PowerShell quando o Windows Terminal nao esta disponivel' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Start-Process -Times 2 -Exactly
    }

    It 'passa o comando de setup para uma das janelas' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Start-Process -Times 1 -Exactly -ParameterFilter {
            $ArgumentList -contains 'SETUP'
        }
    }

    It 'passa o comando de encode para a outra janela' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Start-Process -Times 1 -Exactly -ParameterFilter {
            $ArgumentList -contains 'ENCODE'
        }
    }

    It 'mantem as janelas abertas (-NoExit)' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Start-Process -Times 2 -Exactly -ParameterFilter {
            $ArgumentList -contains '-NoExit'
        }
    }

    It 'registra que entrou no caminho de fallback' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Write-LauncherLog -Times 1 -Exactly -ParameterFilter {
            $Message -match 'fallback'
        }
    }
}
```

- [ ] **Step 2: Verificar que nenhuma fixture foi criada em disco do repositório**

Run: `git status --short && ls -la tests/`
Expected: `tests/` contém apenas `launch-config.Tests.ps1` e
`launcher.Tests.ps1`. Nenhum `.json`, `.log`, `.tmp` ou diretório temporário —
tudo que é escrito em disco vai para `$TestDrive`, que o Pester limpa sozinho.

- [ ] **Step 3: Verificar que `launcher.ps1` e os arquivos Python continuam intocados**

Run: `git diff --stat -- launcher.ps1 launch-config.json '*.py'`
Expected: saída vazia.

- [ ] **Step 4: Commit**

```bash
git add tests/launcher.Tests.ps1
git commit -m "test(launcher): Read-LauncherConfig, Write-LauncherLog e fallback de Open-LauncherTabs"
```

---

### Task 5: job `pester` no CI (ubuntu + windows)

**Agent:** `executor`

**Files:**
- Modify: `.github/workflows/ci.yml` (acrescentar um terceiro job ao final; não
  editar os jobs `lint` e `tests` existentes)

**Interfaces:**
- Consumes: `tests/*.Tests.ps1` das Tasks 1-4.
- Produces: o job `pester`, com dois legs (`ubuntu-latest`, `windows-latest`).
  É a **única** fonte de evidência deste ciclo — não há `pwsh` no sandbox de
  desenvolvimento. A Task 6 lê a saída deste job.

- [ ] **Step 1: Acrescentar o bloco abaixo ao FINAL de `.github/workflows/ci.yml`, depois da linha `run: python -m pytest enhance/ ui/ -v --timeout=60` (mantendo a indentação de 2 espaços do nível `jobs:`)**

```yaml

  pester:
    name: Pester (launcher.ps1)
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]

    steps:
      - uses: actions/checkout@v4

      - name: PowerShell version (diagnostico)
        shell: pwsh
        run: |
          $PSVersionTable | Format-List
          Write-Host "OS matrix leg: ${{ matrix.os }}"

      - name: Install Pester
        shell: pwsh
        run: |
          Install-Module Pester -MinimumVersion 5.5.0 -Force -Scope CurrentUser -SkipPublisherCheck
          Get-Module Pester -ListAvailable | Select-Object Name, Version | Format-Table

      - name: Run Pester
        shell: pwsh
        run: |
          Import-Module Pester -MinimumVersion 5.5.0
          Invoke-Pester -Path ./tests -CI
```

Notas de projeto deste job (não são TODOs — são as decisões já tomadas):

- `fail-fast: false` — mesmo padrão do job `tests` existente. Se o leg windows
  quebrar, o leg ubuntu ainda precisa reportar, senão perde-se metade da
  informação exatamente quando ela é mais útil.
- `shell: pwsh` nos dois legs — ambos os runners do GitHub trazem PowerShell
  Core de fábrica. O runner windows também tem `shell: powershell` (5.1), que
  é o motor real de produção; não é adicionado agora para manter o job com um
  contrato só, mas a estrutura de matriz já permite acrescentar depois sem
  reescrever nada.
- `-MinimumVersion 5.5.0` — mínimo pinado, mesmo hábito de `ruff==0.14.10` no
  job `lint`. Pester 4 (que vem pré-instalado no runner windows) tem sintaxe
  incompatível com `Should -Invoke`/`-ForEach`; o `Import-Module` explícito com
  `-MinimumVersion` garante que a v5 é a carregada, e não a v4 pré-instalada.
- `Invoke-Pester -CI` — faz o processo sair com código != 0 quando algum teste
  falha (sem isso o job passaria verde com testes vermelhos) e liga a saída
  detalhada.

- [ ] **Step 2: Verificar que o YAML continua válido**

Run: `python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/ci.yml')); print(sorted(d['jobs'].keys())); print(d['jobs']['pester']['strategy']['matrix']['os'])"`
Expected:
```
['lint', 'pester', 'tests']
['ubuntu-latest', 'windows-latest']
```

- [ ] **Step 3: Verificar que os jobs existentes não foram alterados**

Run: `git diff .github/workflows/ci.yml`
Expected: apenas linhas `+` no final do arquivo. Nenhuma linha `-`. Se aparecer
qualquer remoção, os jobs `lint`/`tests` foram tocados — reverter e refazer só
como append.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: rodar Pester do launcher em ubuntu-latest e windows-latest"
```

---

### Task 6: execução real no CI + evidência

**Agent:** `executor-pesado`

**Files:**
- Modify: `.claude/memory/STATE.md` (append de uma seção nova — nunca reescrever
  linhas existentes, conforme o cabeçalho do arquivo)
- Modify: `.claude/memory/FINDINGS.md` (append, só se houver achado novo)

**Interfaces:**
- Consumes: tudo das Tasks 1-5 já commitado e o job `pester` do CI.

Esta é a única task "sem supervisão" do ciclo (faz push, espera o CI, lê os dois
legs da matriz e julga divergências) — por isso vai para `executor-pesado`,
conforme a tabela de delegação do `CLAUDE.md`.

- [ ] **Step 1: Push e localizar o run**

```bash
git push -u origin HEAD
gh run list --workflow=ci.yml --limit 3
```
Expected: o run mais recente corresponde ao commit recém-empurrado e lista o
job `Pester (launcher.ps1)` com dois legs.

- [ ] **Step 2: Aguardar e ler o resultado dos DOIS legs**

```bash
gh run watch
gh run view --log | sed -n '/Pester (launcher.ps1)/,$p'
```
Expected: saída real do `Invoke-Pester` em cada leg — contagem
`Tests Passed: N, Failed: 0, Skipped: 0` e o `$PSVersionTable` do passo de
diagnóstico. Guardar a URL do run (`gh run view --json url -q .url`).

- [ ] **Step 3: Interpretar divergência entre legs ANTES de mexer em qualquer coisa**

Se um teste falhar em `windows-latest` e passar em `ubuntu-latest` (ou o
inverso), a hipótese padrão é que **é um achado real sobre `launcher.ps1`, não
um defeito do teste**. Foi exatamente esse tipo de divergência entre motores de
PowerShell que produziu o `QF1` (ciclos S e T: o bug só reproduzia em Windows
PowerShell 5.1). Procedimento obrigatório, nessa ordem:

1. Registrar a falha crua em `.claude/memory/FINDINGS.md` como `UF1`, `UF2`, …,
   no formato de tabela já usado no arquivo
   (`| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |`),
   com a saída real do leg que falhou.
2. Só então investigar a causa: é comportamento diferente do `launcher.ps1`
   entre os motores, ou é uma asserção do teste que assumiu SO?
3. **Não** relaxar a asserção para "ficar verde". Se a conclusão for que o teste
   é que estava errado, corrigir o teste e dizer explicitamente no `STATE.md`
   por que não é um bug do launcher.
4. Se a conclusão for que é bug do `launcher.ps1`: **não corrigir neste ciclo**
   — `launcher.ps1` é read-only aqui. Registrar em `FINDINGS.md` e reportar ao
   Orquestrador para um ciclo próprio.

Três candidatos conhecidos a divergir (o spec já os prevê em "Riscos
conhecidos"; se algum aparecer, é confirmação e não surpresa): asserção de path
que escapou do `-match`, `Mock Write-Host` interferindo na saída do próprio
Pester, e `ConvertFrom-Json` de JSON malformado emitir erro não-terminante num
dos motores (o que faria o `catch` de `Read-LauncherConfig` não disparar e o
teste de "*invalido*" falhar — isso seria um achado real sobre a função).

- [ ] **Step 4: Registrar a evidência em `.claude/memory/STATE.md`**

Append, seguindo o padrão de seção do arquivo:

```markdown
## Ciclo U — Pester para o launcher — 2026-08-14

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| U1 | done | tests/launch-config.Tests.ps1 | contrato do JSON — N testes |
| U2 | done | tests/launcher.Tests.ps1 | dot-source + Build-* — N testes |
| U3 | done | tests/launcher.Tests.ps1 | Initialize-Environment / Resolve-Binaries — N testes |
| U4 | done | tests/launcher.Tests.ps1 | Read-LauncherConfig / Write-LauncherLog / fallback — N testes |
| U5 | done | .github/workflows/ci.yml | job `pester`, matriz ubuntu + windows |
| U6 | done | — | CI verde nos dois legs — URL do run: <colar> |
```

Abaixo da tabela, colar **a saída real completa** do `Invoke-Pester` dos dois
legs (ubuntu e windows) e o `$PSVersionTable` de cada um — texto bruto, não
parafraseado, conforme `superpowers:verification-before-completion`. Registrar
também, explicitamente, que não houve evidência local porque não há `pwsh` no
sandbox de desenvolvimento, e que a evidência deste ciclo é 100% do CI.

- [ ] **Step 5: Confirmar que a suíte Python não regrediu**

Run: `python -m pytest ui/ enhance/ -q 2>&1 | tail -3`
Expected: mesmo número de testes de antes do ciclo, todos passando. Colar a
linha final real no `STATE.md`. Nenhum arquivo Python foi tocado por este
ciclo, então qualquer variação aqui significa que algo saiu do escopo.

- [ ] **Step 6: Confirmar que `launcher.ps1` sobreviveu ao ciclo inteiro sem uma linha alterada**

Run: `git diff --stat origin/main -- launcher.ps1 launch-config.json`
Expected: saída vazia. Este é o critério que fecha a Global Constraint mais
importante do plano.

- [ ] **Step 7: Commit**

```bash
git add .claude/memory/STATE.md .claude/memory/FINDINGS.md
git commit -m "docs(state): registrar evidencia de CI dos testes Pester do launcher (ciclo U)"
```

---

## Self-Review (Orquestrador)

- **Cobertura do spec → tasks.** Architecture § "Layout dos testes" → Tasks 1-2.
  § "O que é testado (por função)": linhas `Build-ProfileArgs`,
  `Build-SetupCommand`, `Build-EncodeCommand` → Task 2; `Initialize-Environment`,
  `Resolve-Binaries`, `Test-VenvExists`, `Test-RequiredBinary` → Task 3;
  `Read-LauncherConfig`, `Write-LauncherLog`, `Open-LauncherTabs` → Task 4;
  as quatro linhas "não testado" não têm task, por desenho. § "Estratégia de
  mock" → Tasks 3 (funções do script) e 4 (cmdlets + `$TestDrive`).
  § "Superfícies não-testáveis" → comentário no cabeçalho do arquivo da Task 2
  e no `Describe` de `Open-LauncherTabs` da Task 4. § CI → Task 5.
  § "Riscos conhecidos" → mitigado em código nas Tasks 1-4 (path via `-match`,
  `description` só por presença, `$script:OnWindows`, save/restore de
  `$ErrorActionPreference`) e como procedimento no Step 3 da Task 6.
  § Validação → Task 6 inteira. O contrato do `launch-config.json` (Goal do
  spec, Regra de Ouro do `--crf`) → Task 1. Nenhuma seção do spec ficou sem
  task correspondente.
- **Placeholders:** nenhum "TBD"/"implementar depois". Os dois arquivos de teste
  e o bloco YAML estão escritos por inteiro e são coláveis como estão. Os
  únicos `N` do documento estão no *template* de tabela do Step 4 da Task 6, que
  por definição só pode ser preenchido com o número real que o CI reportar —
  preenchê-lo agora seria inventar evidência.
- **Consistência de tipos/nomes.** Os mocks da Task 3 usam exatamente os nomes
  definidos em `launcher.ps1`: `Test-VenvExists` (l. 61), `New-ProjectVenv`
  (l. 74), `Install-Requirements` (l. 95), `Write-VenvLock` (l. 119),
  `Test-RequiredBinary` (l. 153), `Write-LauncherLog` (l. 24) — conferido um a
  um, e o Step 2 da Task 3 re-verifica por `grep` na hora da execução (um mock
  com nome errado cria um teste que passa sem testar nada, que é pior que um
  teste faltando). Os `-ParameterFilter` usam os nomes reais de parâmetro:
  `$VenvPath`/`$VenvPython` (`New-ProjectVenv`/`Install-Requirements`),
  `$Path` (`Test-Path`, `Test-RequiredBinary`), `$Message`/`$Level`
  (`Write-LauncherLog`), `$Object` (`Write-Host`), `$ArgumentList`
  (`Start-Process`). O shape asseverado em `Resolve-Binaries` (Task 3) —
  `VenvPython`, `Ffmpeg`, `Ffprobe`, `WtPath`, `WtAvailable` — é o mesmo
  `[PSCustomObject]` construído em `launcher.ps1:188-194` e o mesmo consumido
  por `Open-LauncherTabs`. As flags asseveradas na Task 2 são cópia literal do
  `launch-config.json` atual, e a Task 1 valida independentemente que esse
  arquivo não ganhou um sexto perfil nem um `--crf`.
- **Read-only respeitado.** Tasks 2, 3, 4 e 6 têm um step explícito de
  `git diff --stat -- launcher.ps1 launch-config.json` esperando saída vazia —
  a constraint é verificada quatro vezes ao longo do ciclo, não só prometida no
  cabeçalho.
- **Ponto fraco assumido.** Nenhuma das Tasks 1-5 consegue provar que o código
  roda: não há `pwsh` no sandbox. Isso está dito no spec § Validação, na Global
  Constraint correspondente, e no Step 3 da Task 2 (que verifica a ausência de
  `pwsh` em vez de assumi-la). Até o CI da Task 6 rodar, o estado correto do
  ciclo é *implementado, não verificado* — e é assim que deve ser reportado ao
  usuário.
