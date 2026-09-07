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
}

Describe 'launch-config.json — estrutura' {

    It 'existe na raiz do repositorio' {
        Test-Path $script:ConfigPath | Should -BeTrue -Because "esperado em: $($script:ConfigPath)"
    }

    It 'e JSON valido' {
        { $script:Raw | ConvertFrom-Json } | Should -Not -Throw
    }

    It 'declara as cinco chaves de topo' {
        $top = @($script:Config.PSObject.Properties.Name)
        foreach ($k in @('configVersion', 'minPythonVersion', 'terminal', 'validation', 'paths')) {
            $top | Should -Contain $k
        }
    }

    It 'nao declara profiles nem defaultProfile' {
        $top = @($script:Config.PSObject.Properties.Name)
        $top | Should -Not -Contain 'profiles' -Because 'o wizard do encoder (ui/launcher.py PRESETS) e a unica fonte de fluxo'
        $top | Should -Not -Contain 'defaultProfile' -Because 'nao ha perfil para ser padrao'
    }

    It 'nao contem nenhum parametro de encode no texto cru' {
        # Antes o guarda garantia que nenhum perfil fixava rate control; agora
        # garante que NAO HA ONDE fixar. Regra de Ouro (skill
        # instagram-reels-encoder § "Regras de Ouro — Nunca Violar"): CRF,
        # maxrate, bufsize e preset sao derivados da analise adaptativa do
        # encoder, nunca fixados em configuracao.
        $script:Raw |
            Should -Not -Match '--crf|--maxrate|--bufsize|--preset|--x264-params|--performance|--mode' `
                -Because 'o launcher e bootstrap de ambiente; nenhuma decisao de encode vive aqui'
    }
}

Describe 'launch-config.json — ambiente' {

    It 'configVersion e um inteiro >= 2' {
        # Windows PowerShell 5.1 desserializa o inteiro do JSON como Int32;
        # pwsh 7 como Int64. Assertar [int] reprovaria so no leg ubuntu.
        $script:Config.configVersion.GetType().Name | Should -BeIn @('Int32', 'Int64')
        $script:Config.configVersion | Should -BeGreaterOrEqual 2
    }

    It 'minPythonVersion e parseavel como [version]' {
        $parsed = $null
        [version]::TryParse([string]$script:Config.minPythonVersion, [ref]$parsed) |
            Should -BeTrue -Because "recebido: '$($script:Config.minPythonVersion)'"
    }

    It 'terminal.<_> e booleano' -ForEach @('preferPwsh', 'noProfile') {
        $script:Config.terminal.$_ | Should -BeOfType [bool]
    }

    It 'validation.requiredEncoders contem libx264' {
        # O pipeline e libx264 puro: "grep -il nvenc" sobre todo .py do repo
        # retorna zero arquivos.
        @($script:Config.validation.requiredEncoders) | Should -Contain 'libx264'
    }

    It 'validation.requiredFilters contem <_>' -ForEach @('lut3d', 'zscale') {
        # zscale aparece 13x em Reels_Encoder_v2_FINAL.py + cineon_pipeline.py e
        # exige libzimg, ausente em muitos builds de FFmpeg.
        @($script:Config.validation.requiredFilters) | Should -Contain $_
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
