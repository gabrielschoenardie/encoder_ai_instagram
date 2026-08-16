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
