<#
.SYNOPSIS
    Baixa a distribuicao portatil OFICIAL do Windows Terminal (ZIP
    "unpackaged" publicado em github.com/microsoft/terminal/releases) e
    extrai para ./bin/WindowsTerminal.

.DESCRIPTION
    Documentado oficialmente em
    https://learn.microsoft.com/en-us/windows/terminal/distributions
    como a distribuicao "Unpackaged/ZIP" (estavel desde 1.17), com
    variante "Portable" ativada por um marker ".portable". Sem MSIX, sem
    dependencia do Windows App SDK runtime, sem repack de terceiros.

    Versao e SHA256 fixados abaixo (nao "latest" dinamico) - mesmo padrao
    de pin usado em ruff==0.14.10 no CI deste projeto.
#>

$ErrorActionPreference = "Stop"

$WtVersion = "1.24.11911.0"
$WtAssetName = "Microsoft.WindowsTerminal_${WtVersion}_x64.zip"
$WtUrl = "https://github.com/microsoft/terminal/releases/download/v$WtVersion/$WtAssetName"
$WtSha256 = "7691EFEB71C8DD0B95536C84E366FA4CF809A42C534912F9CEFA1056534383BD"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $ProjectRoot "bin"
$DestDir = Join-Path $BinDir "WindowsTerminal"
$TempZip = Join-Path $env:TEMP $WtAssetName

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

Write-Host "Baixando Windows Terminal $WtVersion (distribuicao portatil oficial) ..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $WtUrl -OutFile $TempZip

Write-Host "Verificando SHA256 ..." -ForegroundColor Cyan
$actualHash = (Get-FileHash -Path $TempZip -Algorithm SHA256).Hash
if ($actualHash -ne $WtSha256) {
    Remove-Item $TempZip -Force
    Write-Host "ERRO checksum nao confere:" -ForegroundColor Red
    Write-Host "  esperado: $WtSha256" -ForegroundColor Red
    Write-Host "  obtido:   $actualHash" -ForegroundColor Red
    throw "Download corrompido ou adulterado - abortando (arquivo removido)."
}
Write-Host "OK    checksum confere ($actualHash)" -ForegroundColor Green

$extractTemp = Join-Path $env:TEMP "wt_portable_extract_$([guid]::NewGuid().ToString('N'))"
try {
    Write-Host "Extraindo para $extractTemp ..." -ForegroundColor Cyan
    Expand-Archive -Path $TempZip -DestinationPath $extractTemp -Force

    $innerFolder = Get-ChildItem -Path $extractTemp -Directory | Select-Object -First 1
    if (-not $innerFolder) {
        throw "ZIP extraido nao contem a pasta esperada (formato do release mudou?)."
    }

    $extractedWtExe = Join-Path $innerFolder.FullName "wt.exe"
    if (-not (Test-Path $extractedWtExe)) {
        throw "wt.exe nao encontrado no ZIP extraido - conteudo do release pode ter mudado."
    }

    if (Test-Path $DestDir) {
        Write-Host "Removendo instalacao portatil anterior em $DestDir ..." -ForegroundColor Yellow
        Remove-Item $DestDir -Recurse -Force
    }
    Move-Item -Path $innerFolder.FullName -Destination $DestDir
}
finally {
    Remove-Item $extractTemp -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $TempZip -Force -ErrorAction SilentlyContinue
}

$wtExe = Join-Path $DestDir "wt.exe"
if (-not (Test-Path $wtExe)) {
    throw "wt.exe nao encontrado apos extracao em $DestDir - conteudo do ZIP pode ter mudado."
}

New-Item -ItemType File -Path (Join-Path $DestDir ".portable") -Force | Out-Null

Write-Host "OK    Windows Terminal portatil instalado em: $DestDir" -ForegroundColor Green
Write-Host "      wt.exe: $wtExe" -ForegroundColor Green
