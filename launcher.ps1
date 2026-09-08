<#
.SYNOPSIS
    Bootstrap portatil do Reels Encoder AI: cria/valida o venv local,
    valida os binarios (Python/FFmpeg/Windows Terminal), monta o comando
    certo e lanca em abas do Windows Terminal (com fallback).
#>

param(
    [switch]$DebugMode,
    # Pula só a checagem local (Test-Path) de bin/ffmpeg.exe e bin/ffprobe.exe feita por Resolve-Binaries; não impede o encoder de usar FFmpeg do PATH via ui/binaries.py::resolve_binary (que prefere bin/ e cai pro PATH como fallback).
    [switch]$SkipValidation,
    [switch]$SkipEnvSetup,
    # Reinstala as dependencias mesmo quando o stamp de requirements/pyproject confere.
    [switch]$ForceEnvSetup
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
    if ($Level -eq "Debug" -and -not $DebugMode) { return }
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
    param([string]$MinVersion = '3.11')
    $minimum = [version]$MinVersion
    $rejected = @()
    foreach ($cmd in @("py", "python", "python3")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if (-not $found) { continue }
        $source = $found.Source
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $probe = & $source -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>&1
        }
        finally {
            $ErrorActionPreference = $prevEap
        }
        $reported = (@($probe) -join "`n").Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($reported)) {
            $rejected += "$source (nao respondeu a probe de versao)"
            continue
        }
        $parsed = $null
        if (-not [version]::TryParse($reported, [ref]$parsed)) {
            $rejected += "$source (versao ilegivel: '$reported')"
            continue
        }
        if ($parsed -ge $minimum) { return $source }
        $rejected += "$source (versao $reported)"
    }
    $detalhe = if ($rejected.Count -gt 0) {
        "Rejeitados: " + ($rejected -join "; ") + "."
    }
    else {
        "Nenhum executavel py/python/python3 foi encontrado no PATH."
    }
    throw "Nenhum Python >= $MinVersion encontrado no PATH. $detalhe Instale Python $MinVersion+ (https://python.org) e crie o ambiente com 'py -3.13 -m venv venv'."
}

function New-ProjectVenv {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPath,
        [string]$MinVersion = '3.11'
    )
    $pythonCmd = Resolve-SystemPython -MinVersion $MinVersion
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
        [Parameter(Mandatory)][string]$VenvPython,
        $Config = $null
    )
    $reqPath = Join-Path $RepoRoot $Config.paths.requirements
    if (-not (Test-Path $reqPath)) {
        throw "Arquivo de dependencias nao encontrado em: $reqPath (chave 'paths.requirements' do launch-config.json)."
    }
    Write-LauncherLog "Instalando dependencias (pip install -r $reqPath) ..." "Info"
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

function Test-VenvHealthy {
    param([Parameter(Mandatory)][string]$VenvPython)
    if (-not (Test-Path $VenvPython)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython -c "import sys" 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    return ($LASTEXITCODE -eq 0)
}

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

function Test-VenvConsistent {
    param([Parameter(Mandatory)][string]$VenvPython)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $VenvPython -m pip check 2>&1
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    return [PSCustomObject]@{
        Ok     = ($LASTEXITCODE -eq 0)
        Report = (@($out) -join "`n").Trim()
    }
}

function Get-RequirementsStamp {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config
    )
    $parts = @()
    foreach ($relative in @($Config.paths.requirements, "pyproject.toml")) {
        $full = Join-Path $RepoRoot $relative
        if (Test-Path $full) {
            $parts += (Get-FileHash -Path $full -Algorithm SHA256).Hash
        }
        else {
            $parts += "ausente"
        }
    }
    return ($parts -join ":")
}

function Read-VenvStamp {
    param([Parameter(Mandatory)][string]$VenvPath)
    $stampFile = Join-Path $VenvPath ".launcher-stamp"
    if (-not (Test-Path $stampFile)) { return $null }
    $raw = Get-Content -Path $stampFile -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    return $raw.Trim()
}

function Write-VenvStamp {
    param(
        [Parameter(Mandatory)][string]$VenvPath,
        [Parameter(Mandatory)][string]$Stamp
    )
    Set-Content -Path (Join-Path $VenvPath ".launcher-stamp") -Value $Stamp -Encoding ascii
}

function Initialize-Environment {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$VenvPath,
        $Config = $null,
        [switch]$Force
    )
    $minVersion = '3.11'
    if ($null -ne $Config -and $Config.minPythonVersion) {
        $minVersion = [string]$Config.minPythonVersion
    }
    if (-not (Test-VenvExists -VenvPath $VenvPath)) {
        New-ProjectVenv -RepoRoot $RepoRoot -VenvPath $VenvPath -MinVersion $minVersion
    }
    else {
        Write-LauncherLog "Venv existente reaproveitado ($VenvPath)." "Info"
    }
    $venvPython = Join-Path $VenvPath "Scripts\python.exe"

    $stamp = $null
    if ($null -ne $Config) {
        $stamp = Get-RequirementsStamp -RepoRoot $RepoRoot -Config $Config
    }
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

    Install-Requirements -RepoRoot $RepoRoot -VenvPython $venvPython -Config $Config
    Write-VenvLock -RepoRoot $RepoRoot -VenvPython $venvPython
    if ($stamp) {
        Write-VenvStamp -VenvPath $VenvPath -Stamp $stamp
    }
    $consistency = Test-VenvConsistent -VenvPython $venvPython
    if (-not $consistency.Ok) {
        Write-LauncherLog "pip check encontrou dependencias inconsistentes (o encoder pode falhar em runtime). Use -ForceEnvSetup depois de ajustar o pyproject.toml:`n$($consistency.Report)" "Warn"
    }
    else {
        Write-LauncherLog "pip check: ambiente consistente." "Success"
    }
    return $venvPython
}

function Test-RequiredBinary {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$FixHint
    )
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "$Name nao encontrado em: $Path`n$FixHint"
    }
    return $Path
}

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

function Test-FfmpegCapabilities {
    param(
        [Parameter(Mandatory)][string]$Ffmpeg,
        [Parameter(Mandatory)]$Config
    )
    $encoders = @()
    $filters = @()
    if ($null -ne $Config) {
        $validationProp = $Config.PSObject.Properties["validation"]
        if ($null -ne $validationProp -and $null -ne $validationProp.Value) {
            $encodersProp = $validationProp.Value.PSObject.Properties["requiredEncoders"]
            if ($null -ne $encodersProp -and $null -ne $encodersProp.Value) { $encoders = @($encodersProp.Value) }
            $filtersProp = $validationProp.Value.PSObject.Properties["requiredFilters"]
            if ($null -ne $filtersProp -and $null -ne $filtersProp.Value) { $filters = @($filtersProp.Value) }
        }
    }
    if ($encoders.Count -eq 0 -and $filters.Count -eq 0) { return }

    $missing = @()
    if ($encoders.Count -gt 0) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $encoderList = & $Ffmpeg -hide_banner -encoders 2>&1
        }
        finally {
            $ErrorActionPreference = $prevEap
        }
        $encoderText = (@($encoderList) -join "`n")
        foreach ($name in $encoders) {
            if ($encoderText -notmatch ("\b" + [regex]::Escape($name) + "\b")) { $missing += "encoder '$name'" }
            else { Write-LauncherLog "Encoder '$name' disponivel." "Success" }
        }
    }
    if ($filters.Count -gt 0) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $filterList = & $Ffmpeg -hide_banner -filters 2>&1
        }
        finally {
            $ErrorActionPreference = $prevEap
        }
        $filterText = (@($filterList) -join "`n")
        foreach ($name in $filters) {
            if ($filterText -notmatch ("\b" + [regex]::Escape($name) + "\b")) { $missing += "filtro '$name'" }
            else { Write-LauncherLog "Filtro '$name' disponivel." "Success" }
        }
    }
    if ($missing.Count -gt 0) {
        throw "FFmpeg em '$Ffmpeg' nao tem: $($missing -join ', '). Rode .\tools\fetch_ffmpeg.ps1 para baixar um build completo."
    }
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
    Write-LauncherLog "FFmpeg encontrado." "Success"
    Test-ExecutableRuns -Path $ffmpeg -Name "FFmpeg"

    $ffprobe = Join-Path $RepoRoot $Config.paths.ffprobeExe
    Test-RequiredBinary -Path $ffprobe -Name "ffprobe.exe" `
        -FixHint "Rode .\tools\fetch_ffmpeg.ps1 para baixar o FFmpeg." | Out-Null
    Write-LauncherLog "FFprobe encontrado." "Success"
    Test-ExecutableRuns -Path $ffprobe -Name "FFprobe"

    Test-FfmpegCapabilities -Ffmpeg $ffmpeg -Config $Config

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
        [AllowEmptyString()][string]$WorkingDirectory = '',
        [AllowEmptyString()][string]$Ffmpeg = '',
        [AllowEmptyString()][string]$Ffprobe = ''
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    $prefix = ''
    if ($WorkingDirectory) {
        $prefix = "Set-Location $(Protect-PSLiteral -Value $WorkingDirectory); "
    }
    if ($Ffmpeg) {
        $prefix += "`$env:REELS_FFMPEG=$(Protect-PSLiteral -Value $Ffmpeg); "
    }
    if ($Ffprobe) {
        $prefix += "`$env:REELS_FFPROBE=$(Protect-PSLiteral -Value $Ffprobe); "
    }
    return "$prefix& $(Protect-PSLiteral -Value $VenvPython) $(Protect-PSLiteral -Value $script) --hardware-info"
}

function Build-AppCommand {
    param(
        [Parameter(Mandatory)][string]$VenvPython,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)]$Config,
        [AllowEmptyString()][string]$WorkingDirectory = '',
        [AllowEmptyString()][string]$Ffmpeg = '',
        [AllowEmptyString()][string]$Ffprobe = ''
    )
    $script = Join-Path $RepoRoot $Config.paths.encoderScript
    $prefix = ''
    if ($WorkingDirectory) {
        $prefix = "Set-Location $(Protect-PSLiteral -Value $WorkingDirectory); "
    }
    if ($Ffmpeg) {
        $prefix += "`$env:REELS_FFMPEG=$(Protect-PSLiteral -Value $Ffmpeg); "
    }
    if ($Ffprobe) {
        $prefix += "`$env:REELS_FFPROBE=$(Protect-PSLiteral -Value $Ffprobe); "
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
        $setupCmdForWt = $SetupCmd -replace ';', '\;'
        $encodeCmdForWt = $EncodeCmd -replace ';', '\;'
        $setupTab += @($Shell) + $shellArgs + @($setupCmdForWt)
        $encodeTab += @($Shell) + $shellArgs + @($encodeCmdForWt)
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
        if ($SkipEnvSetup -and $ForceEnvSetup) {
            throw "-SkipEnvSetup e -ForceEnvSetup sao mutuamente exclusivos: escolha pular o setup do venv ou forcar a reinstalacao."
        }

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
            $venvPython = Initialize-Environment -RepoRoot $Script:RepoRoot -VenvPath $venvPath `
                -Config $config -Force:$ForceEnvSetup
        }

        if ($SkipValidation) {
            # QF2: se houver FFmpeg no PATH global (ex.: instalado via tools/fetch_ffmpeg.ps1/winget), o encoder ainda vai encontrar e usar esse binário mesmo sem o bin/ffmpeg.exe local — -SkipValidation não força isolamento estrito.
            Write-LauncherLog "Validacao de binarios pulada (-SkipValidation)." "Warn"
            $wtPath = Join-Path $Script:RepoRoot $config.paths.windowsTerminalExe
            $binaries = [PSCustomObject]@{
                VenvPython  = $venvPython
                Ffmpeg      = ''
                Ffprobe     = ''
                WtPath      = $wtPath
                WtAvailable = (Test-Path $wtPath)
            }
        }
        else {
            $binaries = Resolve-Binaries -RepoRoot $Script:RepoRoot -VenvPython $venvPython -Config $config
        }

        $setupCmd = Build-SetupCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config `
            -WorkingDirectory $Script:RepoRoot -Ffmpeg $binaries.Ffmpeg -Ffprobe $binaries.Ffprobe
        $encodeCmd = Build-AppCommand -VenvPython $binaries.VenvPython -RepoRoot $Script:RepoRoot -Config $config `
            -WorkingDirectory $Script:RepoRoot -Ffmpeg $binaries.Ffmpeg -Ffprobe $binaries.Ffprobe

        $launcherShell = Resolve-LauncherShell -Config $config
        $useNoProfile = $true
        if ($null -ne $config.terminal -and $config.terminal.noProfile -eq $false) { $useNoProfile = $false }

        Open-LauncherTabs -SetupCmd $setupCmd -EncodeCmd $encodeCmd -WtPath $binaries.WtPath `
            -WtAvailable $binaries.WtAvailable -WorkingDirectory $Script:RepoRoot `
            -Shell $launcherShell -NoProfile $useNoProfile
    }
    catch {
        $errMsg = if ($_.Exception.Message) { $_.Exception.Message } else { "Erro sem mensagem (possivel stderr de comando nativo promovido a erro terminante). Rode com -DebugMode para ver o stack trace completo." }
        Write-LauncherLog $errMsg "Error"
        if ($DebugMode) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
        exit 1
    }
}
