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
