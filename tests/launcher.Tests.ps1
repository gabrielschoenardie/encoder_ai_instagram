<#
    Testes das funcoes de launcher.ps1.

    O arquivo e carregado por dot-source. launcher.ps1:513 tem o guard
    "if ($MyInvocation.InvocationName -ne '.')": sob dot-source a condicao e
    falsa, entao as 21 funcoes sao definidas e NADA do bootstrap roda (nenhum
    venv criado, nenhum pip, nenhuma janela aberta).

    Superficies deliberadamente NAO cobertas aqui (ver o spec
    docs/superpowers/specs/2026-08-14-pester-launcher-design.md
    § "Superficies nao-testaveis"): New-ProjectVenv, Install-Requirements,
    Write-VenvLock, Test-FfmpegCapabilities, Test-VenvHealthy real,
    Resolve-SystemPython real e o ramo wt.exe de Open-LauncherTabs usam
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
        'Test-LauncherConfig'
        'Test-VenvExists'
        'Resolve-SystemPython'
        'New-ProjectVenv'
        'Install-Requirements'
        'Write-VenvLock'
        'Test-VenvHealthy'
        'Get-RequirementsStamp'
        'Read-VenvStamp'
        'Write-VenvStamp'
        'Initialize-Environment'
        'Test-RequiredBinary'
        'Test-FfmpegCapabilities'
        'Resolve-Binaries'
        'Protect-PSLiteral'
        'Build-SetupCommand'
        'Build-AppCommand'
        'Resolve-LauncherShell'
        'Open-LauncherTabs'
    ) {
        Get-Command $_ -CommandType Function -ErrorAction SilentlyContinue |
            Should -Not -BeNullOrEmpty -Because "dot-source de launcher.ps1 deveria definir $_"
    }

    It 'carrega o launch-config.json real do repositorio' {
        $script:Config.configVersion | Should -Be 2
    }

    It 'sabe em qual SO esta rodando' {
        $script:OnWindows | Should -BeOfType [bool]
    }
}

Describe 'Protect-PSLiteral' {

    It 'envolve uma string simples em aspas simples' {
        Protect-PSLiteral -Value 'abc' | Should -Be "'abc'"
    }

    It 'dobra a aspa simples embutida' {
        # O caso real: um repo em "C:\Users\Gabriel's PC\encoder" fecharia o
        # literal no meio do caminho e quebraria o comando das duas abas.
        Protect-PSLiteral -Value "Gabriel's" | Should -Be "'Gabriel''s'"
    }

    It 'preserva espacos sem escapar nada mais' {
        Protect-PSLiteral -Value 'C:\Meus Reels\clipes' | Should -Be "'C:\Meus Reels\clipes'"
    }

    It 'aceita string vazia e devolve um literal vazio' {
        Protect-PSLiteral -Value '' | Should -Be "''"
    }
}

Describe 'Test-LauncherConfig' {

    It 'aceita o launch-config.json real do repositorio' {
        { Test-LauncherConfig -Config $script:Config } | Should -Not -Throw
    }

    It 'lanca nomeando a chave quando paths.venv esta ausente' {
        $cfg = '{ "paths": { "ffmpegExe": "a", "ffprobeExe": "b", "windowsTerminalExe": "c", "requirements": "d", "encoderScript": "e" } }' |
            ConvertFrom-Json
        { Test-LauncherConfig -Config $cfg } | Should -Throw -ExpectedMessage '*paths.venv*'
    }

    It 'lanca nomeando a chave quando paths.venv e uma string vazia' {
        $cfg = '{ "paths": { "venv": "", "ffmpegExe": "a", "ffprobeExe": "b", "windowsTerminalExe": "c", "requirements": "d", "encoderScript": "e" } }' |
            ConvertFrom-Json
        { Test-LauncherConfig -Config $cfg } | Should -Throw -ExpectedMessage '*paths.venv*'
    }

    It 'lanca quando minPythonVersion nao e parseavel como [version]' {
        $cfg = '{ "minPythonVersion": "tres-ponto-onze", "paths": { "venv": "venv", "ffmpegExe": "a", "ffprobeExe": "b", "windowsTerminalExe": "c", "requirements": "d", "encoderScript": "e" } }' |
            ConvertFrom-Json
        { Test-LauncherConfig -Config $cfg } | Should -Throw -ExpectedMessage '*minPythonVersion*'
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

Describe 'Build-AppCommand' {

    It 'entrega o wizard e nada mais (termina em --ui)' {
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Match '--ui$'
    }

    It 'referencia o script do encoder e o interpretador recebido' {
        $cmd = Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config
        $cmd | Should -Match 'Reels_Encoder_v2_FINAL\.py'
        $cmd | Should -Match 'PY'
    }

    It 'nao pre-decide nenhum parametro de encode (<_>)' -ForEach @(
        '--performance'
        '--batch'
        '--mode'
        '--enhance'
        '--cineon-pipeline'
        '--crf'
    ) {
        # Regra de Ouro (skill instagram-reels-encoder): rate control e decisao
        # de pipeline vem da analise adaptativa do encoder, nunca do launcher.
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Not -Match $_
    }

    It 'nao cita nome de perfil nenhum' {
        $cmd = Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config
        foreach ($n in @('fast', 'balanced', 'quality', 'cinematic')) {
            $cmd | Should -Not -Match $n
        }
    }

    It 'prefixa Set-Location quando recebe -WorkingDirectory' {
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config -WorkingDirectory 'WD' |
            Should -Match '^Set-Location ''WD''; '
    }

    It 'nao prefixa Set-Location quando -WorkingDirectory fica vazio' {
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config |
            Should -Not -Match 'Set-Location'
    }

    It 'exporta REELS_FFMPEG e REELS_FFPROBE dentro da string' {
        $cmd = Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -Ffmpeg 'FF' -Ffprobe 'FP'
        $cmd | Should -Match '\$env:REELS_FFMPEG=''FF'''
        $cmd | Should -Match '\$env:REELS_FFPROBE=''FP'''
    }

    It 'monta na ordem Set-Location -> $env: -> &' {
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config `
            -WorkingDirectory 'WD' -Ffmpeg 'FF' -Ffprobe 'FP' |
            Should -Match '^Set-Location ''WD''; \$env:REELS_FFMPEG=''FF''; \$env:REELS_FFPROBE=''FP''; & '
    }

    It 'protege caminho com aspa simples' {
        Build-AppCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $script:Config -WorkingDirectory "Gabriel's" |
            Should -Match '^Set-Location ''Gabriel''''s''; '
    }
}

Describe 'Resolve-LauncherShell' {

    It 'devolve powershell quando terminal.preferPwsh e false' {
        # Sem consultar o PATH: o proprio runner desta suite tem pwsh instalado
        # (o CI roda em pwsh 7 no leg ubuntu), entao "powershell" so pode sair
        # do curto-circuito da preferencia.
        $cfg = '{ "terminal": { "preferPwsh": false } }' | ConvertFrom-Json
        Resolve-LauncherShell -Config $cfg | Should -Be 'powershell'
    }

    It 'devolve um shell valido quando preferPwsh e true' {
        $cfg = '{ "terminal": { "preferPwsh": true } }' | ConvertFrom-Json
        Resolve-LauncherShell -Config $cfg | Should -BeIn @('pwsh', 'powershell')
    }
}

Describe 'Initialize-Environment' {

    # Pester 5 consegue mockar funcoes definidas por dot-source na mesma
    # sessao. E isso que permite testar a DECISAO do orquestrador (criar venv
    # vs. reaproveitar, rodar pip vs. pular pelo stamp) sem criar venv nenhum,
    # sem rede e sem pip - as funcoes que de fato invocam "& $python" ficam
    # substituidas por no-ops.

    Context 'venv existe, saudavel, stamp confere' {

        BeforeAll {
            Mock Test-VenvExists      { return $true }
            Mock Test-VenvHealthy     { return $true }
            Mock Get-RequirementsStamp { return 'S' }
            Mock Read-VenvStamp       { return 'S' }
            Mock Write-VenvStamp      { }
            Mock New-ProjectVenv      { }
            Mock Install-Requirements { }
            Mock Write-VenvLock       { }
            Mock Write-LauncherLog    { }
        }

        It 'nao recria o venv' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke New-ProjectVenv -Times 0 -Exactly
        }

        It 'nao roda pip (o stamp confere)' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Install-Requirements -Times 0 -Exactly
        }

        It 'nao regrava o venv.lock (pip nao rodou)' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Write-VenvLock -Times 0 -Exactly
        }

        It 'retorna o caminho do python dentro do venv informado' {
            $py = Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config
            # Join-Path 'VENV' 'Scripts\python.exe' muda de forma entre SOs;
            # asseveramos os dois pedacos estaveis, nunca o caminho inteiro.
            $py | Should -Match 'python'
            $py | Should -Match 'VENV'
        }
    }

    Context 'venv existe, saudavel, stamp difere' {

        BeforeAll {
            Mock Test-VenvExists      { return $true }
            Mock Test-VenvHealthy     { return $true }
            Mock Get-RequirementsStamp { return 'S' }
            Mock Read-VenvStamp       { return 'OUTRO' }
            Mock Write-VenvStamp      { }
            Mock New-ProjectVenv      { }
            Mock Install-Requirements { }
            Mock Write-VenvLock       { }
            Mock Write-LauncherLog    { }
        }

        It 'reinstala as dependencias' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly
        }

        It 'regrava o venv.lock (diagnostico)' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Write-VenvLock -Times 1 -Exactly
        }

        It 'grava o stamp novo depois do pip' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Write-VenvStamp -Times 1 -Exactly
        }

        It 'passa adiante o mesmo interpretador para install e lock' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly -ParameterFilter {
                $VenvPython -match 'python'
            }
        }
    }

    Context 'venv existe mas nao esta saudavel' {

        BeforeAll {
            Mock Test-VenvExists      { return $true }
            Mock Test-VenvHealthy     { return $false }
            Mock Get-RequirementsStamp { return 'S' }
            Mock Read-VenvStamp       { return 'S' }
            Mock Write-VenvStamp      { }
            Mock New-ProjectVenv      { }
            Mock Install-Requirements { }
            Mock Write-VenvLock       { }
            Mock Write-LauncherLog    { }
        }

        It 'reinstala mesmo com o stamp conferindo' {
            # Venv orfao de repo movido (pyvenv.cfg com "home" obsoleto): pular
            # o pip pelo stamp esconderia o problema.
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly
        }
    }

    Context 'quando o venv nao existe' {

        BeforeAll {
            Mock Test-VenvExists      { return $false }
            Mock Test-VenvHealthy     { return $true }
            Mock Read-VenvStamp       { return $null }
            Mock Get-RequirementsStamp { return 'S' }
            Mock Write-VenvStamp      { }
            Mock New-ProjectVenv      { }
            Mock Install-Requirements { }
            Mock Write-VenvLock       { }
            Mock Write-LauncherLog    { }
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

    Context 'com -Force' {

        BeforeAll {
            Mock Test-VenvExists      { return $true }
            Mock Test-VenvHealthy     { return $true }
            Mock Get-RequirementsStamp { return 'S' }
            Mock Read-VenvStamp       { return 'S' }
            Mock Write-VenvStamp      { }
            Mock New-ProjectVenv      { }
            Mock Install-Requirements { }
            Mock Write-VenvLock       { }
            Mock Write-LauncherLog    { }
        }

        It 'reinstala mesmo com venv saudavel e stamp conferindo' {
            Initialize-Environment -RepoRoot 'ROOT' -VenvPath 'VENV' -Config $script:Config -Force | Out-Null
            Should -Invoke Install-Requirements -Times 1 -Exactly
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
            # Test-FfmpegCapabilities real invocaria "& 'ROOT\bin\ffmpeg.exe'
            # -encoders" com um -RepoRoot ficticio; mockado, e no-op. A prova
            # dessa funcao e execucao real, nao Pester (ver cabecalho).
            Mock Test-FfmpegCapabilities { }
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
            Mock Test-FfmpegCapabilities { }
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
        $real.configVersion | Should -Be 2
        @($real.paths.PSObject.Properties.Name).Count | Should -Be 6
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

    It 'usa o shell recebido em -Shell' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false -Shell 'pwsh'
        Should -Invoke Start-Process -Times 2 -Exactly -ParameterFilter {
            $FilePath -eq 'pwsh'
        }
    }

    It 'passa -NoProfile no ArgumentList por padrao' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false
        Should -Invoke Start-Process -Times 2 -Exactly -ParameterFilter {
            $ArgumentList -contains '-NoProfile'
        }
    }

    It 'omite -NoProfile quando -NoProfile e false' {
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false -NoProfile $false
        Should -Invoke Start-Process -Times 0 -Exactly -ParameterFilter {
            $ArgumentList -contains '-NoProfile'
        }
    }

    It 'passa o diretorio de trabalho ao Start-Process' {
        # AXF1: sem isso, enhance_maps/ (caminho relativo em
        # Reels_Encoder_v2_FINAL.py e enhance_visualizer.py) nasce no CWD da aba.
        Open-LauncherTabs -SetupCmd 'SETUP' -EncodeCmd 'ENCODE' -WtPath 'WT' -WtAvailable $false -WorkingDirectory 'ROOT'
        Should -Invoke Start-Process -Times 2 -Exactly -ParameterFilter {
            $WorkingDirectory -eq 'ROOT'
        }
    }
}
