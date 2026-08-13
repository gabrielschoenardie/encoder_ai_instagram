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

if ($MyInvocation.InvocationName -ne '.') {
    # (corpo principal vem nas proximas tasks)
}
