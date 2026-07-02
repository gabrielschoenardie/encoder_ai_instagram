<#
.SYNOPSIS
    Baixa o FFmpeg 6.1 (via winget) e copia ffmpeg/ffprobe/ffplay para ./bin.

.DESCRIPTION
    Portabilidade no Windows: instala o FFmpeg 6.1 (BtbN.FFmpeg.GPL.6.1) com o
    winget e copia os tres executaveis para a pasta ./bin do projeto, onde o
    resolver (ui/binaries.py) os encontra automaticamente — sem depender do PATH.
#>

$ErrorActionPreference = "Stop"

# Raiz do projeto = pasta pai do diretorio deste script (tools/ -> raiz).
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $ProjectRoot "bin"

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

Write-Host "Instalando FFmpeg 6.1 via winget..." -ForegroundColor Cyan
winget install -e --id BtbN.FFmpeg.GPL.6.1 `
    --accept-source-agreements --accept-package-agreements

$exes = @("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")

# Locais provaveis onde o winget/FFmpeg deposita os binarios.
$searchRoots = @(
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"),
    (Join-Path $env:ProgramFiles "FFmpeg")
) | Where-Object { $_ -and (Test-Path $_) }

foreach ($exe in $exes) {
    $found = $null

    # 1) Procura recursivamente nos diretorios conhecidos.
    foreach ($root in $searchRoots) {
        $hit = Get-ChildItem -Path $root -Filter $exe -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { $found = $hit.FullName; break }
    }

    # 2) Fallback: o executavel ja pode estar no PATH desta sessao.
    if (-not $found) {
        $cmd = Get-Command $exe -ErrorAction SilentlyContinue
        if ($cmd) { $found = $cmd.Source }
    }

    if ($found) {
        Copy-Item -Path $found -Destination (Join-Path $BinDir $exe) -Force
        Write-Host "OK    $exe -> ./bin" -ForegroundColor Green
    }
    else {
        Write-Host "AVISO $exe nao encontrado (copie manualmente para ./bin)" -ForegroundColor Yellow
    }
}

Write-Host "Concluido. Binarios em: $BinDir" -ForegroundColor Cyan
