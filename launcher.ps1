<#
.SYNOPSIS
    Bootstrap portatil do Reels Encoder AI: cria/valida o venv local,
    valida os binarios (Python/FFmpeg/Windows Terminal), monta o comando
    certo e lanca em abas do Windows Terminal (com fallback).
#>

param(
    [switch]$Debug,
    # Pula só a checagem local (Test-Path) de bin/ffmpeg.exe e bin/ffprobe.exe feita por Resolve-Binaries; não impede o encoder de usar FFmpeg do PATH via ui/binaries.py::resolve_binary (que prefere bin/ e cai pro PATH como fallback).
    [switch]$SkipValidation,
    [switch]$SkipEnvSetup
)

$ErrorActionPreference = "Stop"
# QF1: em pwsh 7.3+, stderr de comando nativo (ex.: "[notice] new pip
# release" do pip install) vira NativeCommandError terminante quando o
# chamador funde streams (*>&1). No-op inofensivo em Windows PowerShell 5.1.
$PSNativeCommandUseErrorActionPreference = $false
$Script:RepoRoot = $PSScriptRoot

function Write-LauncherLog {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet("Info", "Success", "Warn", "Error", "Debug")]
        [string]$Level = "Info"
    )
    if ($Level -eq "Debug" -and -not $Debug) { return }
    $color = switch ($Level) {
        "Success" { "Green" }
        "Warn"    { "Yellow" }
        "Error"   { "Red" }
        "Debug"   { "Cyan" }
        default   { "White" }
    }
    $prefix = switch ($Level) {
        "Success" { "[OK]   " }
        "Warn"    { "[AVISO]" }
        "Error"   { "[ERRO] " }
        "Debug"   { "[DEBUG]" }
        default   { "[INFO] " }
    }
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Read-LauncherConfig {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path $Path)) {
        throw "launch-config.json nao encontrado em: $Path"
    }
    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        throw "launch-config.json invalido (JSON malformado): $($_.Exception.Message)"
    }
}

function Test-LauncherConfig {
    param([Parameter(Mandatory)]$Config)

    if ($null -eq $Config) {
        throw "launch-config.json invalido: conteudo vazio."
    }

    $pathsProp = $Config.PSObject.Properties["paths"]
    if ($null -eq $pathsProp -or $null -eq $pathsProp.Value) {
        throw "launch-config.json invalido: chave 'paths' ausente."
    }
    foreach ($key in @("venv", "ffmpegExe", "ffprobeExe", "windowsTerminalExe", "requirements", "encoderScript")) {
        $keyProp = $pathsProp.Value.PSObject.Properties[$key]
        if ($null -eq $keyProp) {
            throw "launch-config.json invalido: chave 'paths.$key' ausente."
        }
        if (($keyProp.Value -isnot [string]) -or [string]::IsNullOrWhiteSpace($keyProp.Value)) {
            throw "launch-config.json invalido: 'paths.$key' deve ser uma string nao-vazia."
        }
    }

    $minPyProp = $Config.PSObject.Properties["minPythonVersion"]
    if ($null -ne $minPyProp -and $null -ne $minPyProp.Value) {
        $parsed = $null
        if (-not [version]::TryParse([string]$minPyProp.Value, [ref]$parsed)) {
            throw "launch-config.json invalido: 'minPythonVersion' nao e uma versao valida (recebido: '$($minPyProp.Value)'). Use algo como '3.11'."
        }
    }

    $terminalProp = $Config.PSObject.Properties["terminal"]
    if ($null -ne $terminalProp -and $null -ne $terminalProp.Value) {
        foreach ($flag in @("preferPwsh", "noProfile")) {
            $flagProp = $terminalProp.Value.PSObject.Properties[$flag]
            if ($null -ne $flagProp -and $flagProp.Value -isnot [bool]) {
                throw "launch-config.json invalido: 'terminal.$flag' deve ser booleano (true/false)."
            }
        }
    }

    $validationProp = $Config.PSObject.Properties["validation"]
    if ($null -ne $validationProp -and $null -ne $validationProp.Value) {
        foreach ($listName in @("requiredEncoders", "requiredFilters")) {
            $listProp = $validationProp.Value.PSObject.Properties[$listName]
            if ($null -eq $listProp -or $null -eq $listProp.Value) { continue }
            foreach ($item in @($listProp.Value)) {
                if (($item -isnot [string]) -or [string]::IsNullOrWhiteSpace($item)) {
                    throw "launch-config.json invalido: 'validation.$listName' deve conter apenas strings nao-vazias."
                }
            }
        }
    }
}

function Test-VenvExists {
    param([Parameter(Mandatory)][string]$VenvPath)
    return Test-Path (Join-Path $VenvPath "Scripts\python.exe")
}

function Resolve-SystemPython {
    foreach ($cmd in @("py", "python")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }
    throw "Python nao encontrado no PATH. Instale Python 3.11+ (https://python.org) e tente novamente."
}

function New-ProjectVenv {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPath
    )
    $pythonCmd = Resolve-SystemPython
    Write-LauncherLog "Criando venv em $VenvPath ..." "Info"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $pythonCmd -m venv $VenvPath | Out-Host
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o venv (python -m venv retornou $LASTEXITCODE). Se ja existir um venv valido, tente -SkipEnvSetup."
    }
    Write-LauncherLog "Venv criado." "Success"
}

function Install-Requirements {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPython
    )
    $reqPath = Join-Path $RepoRoot "requirements.txt"
    if (-not (Test-Path $reqPath)) {
        throw "requirements.txt nao encontrado em: $reqPath"
    }
    Write-LauncherLog "Instalando dependencias (pip install -r requirements.txt) ..." "Info"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython -m pip install -r $reqPath | Out-Host
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        throw "pip install falhou (exit $LASTEXITCODE). Verifique espaco em disco, permissoes e conexao."
    }
    Write-LauncherLog "Dependencias instaladas." "Success"
}

function Write-VenvLock {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPython
    )
    $lockPath = Join-Path $RepoRoot "venv.lock"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython -m pip freeze | Out-File -FilePath $lockPath -Encoding utf8
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    Write-LauncherLog "venv.lock atualizado (diagnostico, nao versionado)." "Debug"
}

function Initialize-Environment {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPath
    )
    if (-not (Test-VenvExists -VenvPath $VenvPath)) {
        New-ProjectVenv -RepoRoot $RepoRoot -VenvPath $VenvPath
    }
    else {
        Write-LauncherLog "Venv existente reaproveitado ($VenvPath)." "Info"
    }
    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    Install-Requirements -RepoRoot $RepoRoot -VenvPython $venvPython
    Write-VenvLock -RepoRoot $RepoRoot -VenvPython $venvPython
    return $venvPython
}

function Test-RequiredBinary {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$FixHint
    )
    if (-not (Test-Path $Path)) {
        throw "$Name nao encontrado em: $Path`n$FixHint"
    }
    return $Path
}

function Resolve-Binaries {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)]$Config
    )
    Test-RequiredBinary -Path $VenvPython -Name "Python (venv)" `
        -FixHint "Rode o launcher sem -SkipEnvSetup para recriar o venv." | Out-Null

    $ffmpeg = Join-Path $RepoRoot $Config.paths.ffmpegExe
    Test-RequiredBinary -Path $ffmpeg -Name "ffmpeg.exe" `
        -FixHint "Rode .\tools\fetch_ffmpeg.ps1 para baixar o FFmpeg." | Out-Null

    $ffprobe = Join-Path $RepoRoot $Config.paths.ffprobeExe
    Test-RequiredBinary -Path $ffprobe -Name "ffprobe.exe" `
        -FixHint "Rode .\tools\fetch_ffmpeg.ps1 para baixar o FFmpeg." | Out-Null

    $wtPath = Join-Path $RepoRoot $Config.paths.windowsTerminalExe
    $wtAvailable = Test-Path $wtPath
    if (-not $wtAvailable) {
        Write-LauncherLog "Windows Terminal portatil nao encontrado ($wtPath) - vai usar janelas PowerShell separadas. Rode .\tools\fetch_wt_portable.ps1 para instalar (opcional)." "Warn"
    }

    return [PSCustomObject]@{
        VenvPython  = $VenvPython
        Ffmpeg      = $ffmpeg
        Ffprobe     = $ffprobe
        WtPath      = $wtPath
        WtAvailable = $wtAvailable
    }
}

function Protect-PSLiteral {
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Value
    )
    return "'" + $Value.Replace("'", "''") + "'"
}

function Build-SetupCommand {
    param(
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config,
        [AllowEmptyString()][string]$WorkingDirectory = ''
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    $prefix = ''
    if ($WorkingDirectory) {
        $prefix = "Set-Location $(Protect-PSLiteral -Value $WorkingDirectory); "
    }
    return "$prefix& $(Protect-PSLiteral -Value $VenvPython) $(Protect-PSLiteral -Value $script) --hardware-info"
}

function Build-AppCommand {
    param(
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config,
        [AllowEmptyString()][string]$WorkingDirectory = ''
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    $prefix = ''
    if ($WorkingDirectory) {
        $prefix = "Set-Location $(Protect-PSLiteral -Value $WorkingDirectory); "
    }
    return "$prefix& $(Protect-PSLiteral -Value $VenvPython) $(Protect-PSLiteral -Value $script) --ui"
}

function Resolve-LauncherShell {
    param([Parameter(Mandatory)]$Config)
    $prefer = $true
    if ($null -ne $Config) {
        $terminalProp = $Config.PSObject.Properties["terminal"]
        if ($null -ne $terminalProp -and $null -ne $terminalProp.Value) {
            $preferProp = $terminalProp.Value.PSObject.Properties["preferPwsh"]
            if ($null -ne $preferProp -and $preferProp.Value -eq $false) { $prefer = $false }
        }
    }
    if (-not $prefer) { return "powershell" }
    if (Get-Command pwsh -ErrorAction SilentlyContinue) { return "pwsh" }
    return "powershell"
}

function Open-LauncherTabs {
    param(
        [Parameter(Mandatory)][string]$SetupCmd,
        [Parameter(Mandatory)][string]$EncodeCmd,
        [Parameter(Mandatory)][string]$WtPath,
        [Parameter(Mandatory)][bool]$WtAvailable,
        [AllowEmptyString()][string]$WorkingDirectory = '',
        [string]$Shell = 'powershell',
        [bool]$NoProfile = $true
    )
    $shellArgs = @()
    if ($NoProfile) { $shellArgs += "-NoProfile" }
    $shellArgs += "-NoExit"
    $shellArgs += "-Command"

    if ($WtAvailable) {
        Write-LauncherLog "Abrindo Windows Terminal (2 abas: Setup, Encode) ..." "Info"
        $setupTab = @("new-tab", "--title", "Setup")
        $encodeTab = @("new-tab", "--title", "Encode")
        if ($WorkingDirectory) {
            $setupTab += @("--startingDirectory", $WorkingDirectory)
            $encodeTab += @("--startingDirectory", $WorkingDirectory)
        }
        $setupTab += @($Shell) + $shellArgs + @($SetupCmd)
        $encodeTab += @($Shell) + $shellArgs + @($EncodeCmd)
        $wtArgs = $setupTab + @(";") + $encodeTab
        & $WtPath @wtArgs
    }
    else {
        Write-LauncherLog "Abrindo janelas PowerShell separadas (fallback) ..." "Info"
        $extra = @{}
        if ($WorkingDirectory) { $extra["WorkingDirectory"] = $WorkingDirectory }
        Start-Process -FilePath $Shell -ArgumentList ($shellArgs + @($SetupCmd)) @extra
        Start-Process -FilePath $Shell -ArgumentList ($shellArgs + @($EncodeCmd)) @extra
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $configPath = Join-Path $Script:RepoRoot "launch-config.json"
        $config = Read-LauncherConfig -Path $configPath
        Test-LauncherConfig -Config $config

        $venvPath = Join-Path $Script:RepoRoot $config.paths.venv

        if ($SkipEnvSetup) {
            Write-LauncherLog "Setup do venv pulado (-SkipEnvSetup)." "Warn"
            $venvPython = Join-Path $venvPath "Scripts\python.exe"
            if (-not (Test-Path $venvPython)) {
                throw "-SkipEnvSetup exige um venv existente em $venvPath, mas Scripts\python.exe nao foi encontrado."
            }
        }
        else {
            $venvPython = Initialize-Environment -RepoRoot $Script:RepoRoot -VenvPath $venvPath
        }

        if ($SkipValidation) {
            # QF2: se houver FFmpeg no PATH global (ex.: instalado via tools/fetch_ffmpeg.ps1/winget), o encoder ainda vai encontrar e usar esse binário mesmo sem o bin/ffmpeg.exe local — -SkipValidation não força isolamento estrito.
            Write-LauncherLog "Validacao de binarios pulada (-SkipValidation)." "Warn"
            $wtPath = Join-Path $Script:RepoRoot $config.paths.windowsTerminalExe
            $binaries = [PSCustomObject]@{
                VenvPython  = $venvPython
                WtPath      = $wtPath
                WtAvailable = (Test-Path $wtPath)
            }
        }
        else {
            $binaries = Resolve-Binaries -RepoRoot $Script:RepoRoot -VenvPython $venvPython -Config $config
        }

        $setupCmd = Build-SetupCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config `
            -WorkingDirectory $Script:RepoRoot
        $encodeCmd = Build-AppCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config `
            -WorkingDirectory $Script:RepoRoot

        $launcherShell = Resolve-LauncherShell -Config $config
        $useNoProfile = $true
        if ($null -ne $config.terminal -and $config.terminal.noProfile -eq $false) { $useNoProfile = $false }

        Open-LauncherTabs -SetupCmd $setupCmd -EncodeCmd $encodeCmd -WtPath $binaries.WtPath `
            -WtAvailable $binaries.WtAvailable -WorkingDirectory $Script:RepoRoot `
            -Shell $launcherShell -NoProfile $useNoProfile
    }
    catch {
        $errMsg = if ($_.Exception.Message) { $_.Exception.Message } else { "Erro sem mensagem (possivel stderr de comando nativo promovido a erro terminante). Rode com -Debug para ver o stack trace completo." }
        Write-LauncherLog $errMsg "Error"
        if ($Debug) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
        exit 1
    }
}
