<#
.SYNOPSIS
    Bootstrap portatil do Reels Encoder AI: cria/valida o venv local,
    valida os binarios (Python/FFmpeg/Windows Terminal), monta o comando
    certo e lanca em abas do Windows Terminal (com fallback).
#>

param(
    [string]$InputFile,
    [string]$Profile,
    [switch]$Debug,
    [switch]$SkipValidation,
    [switch]$SkipEnvSetup
)

$ErrorActionPreference = "Stop"
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
    & $pythonCmd -m venv $VenvPath | Out-Host
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
    & $VenvPython -m pip install -r $reqPath | Out-Host
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
    & $VenvPython -m pip freeze | Out-File -FilePath $lockPath -Encoding utf8
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

function Build-ProfileArgs {
    param(
        [Parameter(Mandatory)][string]$ProfileName,
        [Parameter(Mandatory)]$Config,
        [string]$BatchDir
    )
    if (-not ($Config.profiles.PSObject.Properties.Name -contains $ProfileName)) {
        $known = ($Config.profiles.PSObject.Properties.Name) -join ", "
        throw "Perfil '$ProfileName' nao existe em launch-config.json. Perfis disponiveis: $known"
    }
    $profileDef = $Config.profiles.$ProfileName
    $profileArgs = @($profileDef.flags)
    if ($profileDef.requiresBatchDir) {
        if (-not $BatchDir) {
            throw "Perfil '$ProfileName' exige uma pasta de entrada: use -InputFile <pasta>."
        }
        $profileArgs = @("--batch", $BatchDir, "--output-dir", $BatchDir) + $profileArgs
    }
    return $profileArgs
}

function Build-SetupCommand {
    param(
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    return "& '$VenvPython' '$script' --hardware-info"
}

function Build-EncodeCommand {
    param(
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config,
        [string]$InputFile,
        [string]$ProfileName
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    if (-not $ProfileName) {
        return "& '$VenvPython' '$script' --ui"
    }
    $isBatch = [bool]$Config.profiles.$ProfileName.requiresBatchDir
    $batchDir = if ($isBatch) { $InputFile } else { $null }
    $profileArgs = Build-ProfileArgs -ProfileName $ProfileName -Config $Config -BatchDir $batchDir

    $cmdParts = @("& '$VenvPython'", "'$script'")
    if (-not $isBatch -and $InputFile) {
        $cmdParts += "'$InputFile'"
    }
    $cmdParts += $profileArgs
    return ($cmdParts -join " ")
}

function Open-LauncherTabs {
    param(
        [Parameter(Mandatory)][string]$SetupCmd,
        [Parameter(Mandatory)][string]$EncodeCmd,
        [Parameter(Mandatory)][string]$WtPath,
        [Parameter(Mandatory)][bool]$WtAvailable
    )
    if ($WtAvailable) {
        Write-LauncherLog "Abrindo Windows Terminal (2 abas: Setup, Encode) ..." "Info"
        & $WtPath new-tab --title "Setup" powershell -NoExit -Command $SetupCmd `; new-tab --title "Encode" powershell -NoExit -Command $EncodeCmd
    }
    else {
        Write-LauncherLog "Abrindo janelas PowerShell separadas (fallback) ..." "Info"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $SetupCmd
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $EncodeCmd
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $configPath = Join-Path $Script:RepoRoot "launch-config.json"
        $config = Read-LauncherConfig -Path $configPath

        $wantsDirectRun = $PSBoundParameters.ContainsKey('InputFile') -or $PSBoundParameters.ContainsKey('Profile')
        $effectiveProfile = if ($wantsDirectRun) {
            if ($Profile) { $Profile } else { $config.defaultProfile }
        } else { $null }

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

        $setupCmd = Build-SetupCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config
        $encodeCmd = Build-EncodeCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config -InputFile $InputFile -ProfileName $effectiveProfile

        Open-LauncherTabs -SetupCmd $setupCmd -EncodeCmd $encodeCmd -WtPath $binaries.WtPath -WtAvailable $binaries.WtAvailable
    }
    catch {
        Write-LauncherLog $_.Exception.Message "Error"
        if ($Debug) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
        exit 1
    }
}
