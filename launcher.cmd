@echo off
setlocal

REM Sempre iniciar na pasta deste arquivo
cd /d "%~dp0"

REM Executar o launcher PowerShell sem alterar
REM permanentemente a politica de execucao do Windows
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" -Tui %*

set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo O Reels Encoder AI terminou com codigo %RC%.
    echo Verifique as mensagens de erro acima.
    pause
)

exit /b %RC%