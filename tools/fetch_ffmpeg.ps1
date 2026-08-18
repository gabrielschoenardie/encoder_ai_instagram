<#
.SYNOPSIS
    Instala o FFmpeg 6.1 via WinGet e copia ffmpeg.exe,
    ffprobe.exe e ffplay.exe para ./bin.

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

& winget install `
    -e `
    --id BtbN.FFmpeg.GPL.6.1 `
    --source winget `
    --accept-source-agreements `
    --accept-package-agreements

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar FFmpeg via winget. Codigo de saida: $LASTEXITCODE"
}

$exes = @(
    "ffmpeg.exe",
    "ffprobe.exe",
    "ffplay.exe"
)

$searchRoots = @(
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"),
    (Join-Path $env:ProgramFiles "FFmpeg")
) | Where-Object {
    $_ -and (Test-Path $_)
}

$foundCount = 0

foreach ($exe in $exes) {

    $found = $null

    # 1. Procurar nos diretorios conhecidos
    foreach ($root in $searchRoots) {

        $hit = Get-ChildItem `
            -Path $root `
            -Filter $exe `
            -Recurse `
            -ErrorAction SilentlyContinue |
            Select-Object -First 1

        if ($hit) {
            $found = $hit.FullName
            break
        }
    }

    # 2. Procurar no PATH
    if (-not $found) {

        $cmd = Get-Command $exe -ErrorAction SilentlyContinue

        if ($cmd) {
            $found = $cmd.Source
        }
    }

    if ($found) {

        Copy-Item `
            -Path $found `
            -Destination (Join-Path $BinDir $exe) `
            -Force

        Write-Host "OK    $exe -> ./bin" -ForegroundColor Green

        $foundCount++
    }
    else {

        Write-Host "ERRO  $exe nao encontrado." -ForegroundColor Red
    }
}

if ($foundCount -ne $exes.Count) {
    throw "FFmpeg foi instalado, mas nem todos os binarios foram encontrados."
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " FFmpeg instalado com sucesso!" -ForegroundColor Green
Write-Host " Binarios: $BinDir" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green