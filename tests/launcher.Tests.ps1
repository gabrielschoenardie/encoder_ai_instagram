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
