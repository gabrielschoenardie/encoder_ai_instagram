@echo off
setlocal

REM Flags aceitos (repassados sem alteracao ao launcher.ps1):
REM   -NoDownload      nao baixa FFmpeg nem Windows Terminal automaticamente
REM   -SkipValidation  pula a validacao do FFmpeg e o download do Windows Terminal
REM   -SkipEnvSetup    pula o setup do venv (exige venv existente)
REM   -ForceEnvSetup   reinstala as dependencias do venv
REM   -DebugMode       mostra mensagens de debug e stack trace
REM Ajuda completa: Get-Help .\launcher.ps1 -Detailed

REM Sempre iniciar na pasta deste arquivo
cd /d "%~dp0"

REM L2F5: cmd no meio da cadeia propaga o PSModulePath do pwsh 7 ao 5.1,
REM que perde o Get-FileHash. O setlocal acima restaura o valor do chamador;
REM o 5.1 recompoe os padroes. Entradas customizadas herdadas nao sao propagadas.
set "PSModulePath="

REM Executar o launcher PowerShell sem alterar
REM permanentemente a politica de execucao do Windows
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" %*

set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo O Reels Encoder AI terminou com codigo %RC%.
    echo Verifique as mensagens de erro acima.
    pause
)

exit /b %RC%