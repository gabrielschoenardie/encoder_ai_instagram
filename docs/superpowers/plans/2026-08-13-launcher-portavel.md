# Launcher Portátil (PowerShell Bootstrap) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Delegação (política deste repo, `CLAUDE.md`):** cada task abaixo lista um
> **Agent** — despache via Task para esse agente exato (`executor` ou
> `executor-pesado`), não para um subagente genérico. Nenhuma task edita
> `Reels_Encoder_v2_FINAL.py`, `ui/`, `ebu_meter.py` ou `cineon_pipeline.py`.

**Goal:** Um bootstrap PowerShell (`launcher.ps1`) que cria/reaproveita um
venv local, valida os binários (Python/FFmpeg/Windows Terminal), monta o
comando certo (wizard existente ou preset direto) e lança em 2 abas do
Windows Terminal (com fallback pra janelas separadas) — zero mudança em
código Python existente.

**Architecture:** 3 arquivos novos na raiz/tools + atualização aditiva de 3
docs. `launcher.ps1` é uma cadeia de funções pequenas e puras onde possível
(constroem strings/args) mais alguns runners finos (venv, pip, download,
lançamento de processo), seguindo o mesmo padrão builder/runner já usado em
`ebu_meter.py` neste repo. `launch-config.json` é dado puro consumido pelo
script. `tools/fetch_wt_portable.ps1` segue o padrão de
`tools/fetch_ffmpeg.ps1` (raiz = pai de `tools/`, mensagens color-coded).

**Tech Stack:** PowerShell 5.1+, JSON (config), Python venv/pip (já
presentes no projeto). Sem framework de teste novo — verificação via
dot-source (`. .\launcher.ps1`) + chamada direta de função, e execução real
completa no task final.

## Global Constraints

- Nenhum arquivo Python rastreado é editado (`Reels_Encoder_v2_FINAL.py`,
  `ui/*`, `ebu_meter.py`, `cineon_pipeline.py` ficam intocados).
- Instalação de dependências do venv usa exclusivamente
  `requirements.txt` → `pyproject.toml` — nenhuma segunda lista de pacotes.
- Nenhum perfil de `launch-config.json` define `--crf` ou qualquer preset de
  qualidade fixo — só flags reais já existentes no `argparse` do encoder.
- `venv.lock` é escrito a cada execução, nunca lido de volta, e vai para o
  `.gitignore` — puramente diagnóstico.
- `tools/fetch_wt_portable.ps1` baixa a distribuição portátil **oficial**
  do Windows Terminal (`microsoft/terminal` GitHub releases, asset
  `Microsoft.WindowsTerminal_<versão>_x64.zip`), versão e SHA256 fixados
  como constantes no script, checksum verificado **antes** de extrair.
- Ausência de `bin/WindowsTerminal/wt.exe` nunca é erro — só ativa o
  fallback de janelas PowerShell separadas.
- Sem introduzir Pester ou qualquer outro framework de teste PowerShell.
- Spec completo: `docs/superpowers/specs/2026-08-13-launcher-portavel-design.md`.

---

## File Structure

```text
encoder_ai_instagram/
├── launcher.ps1                  ← novo (Tasks 2-6)
├── launch-config.json            ← novo (Task 1)
├── .gitignore                    ← +1 linha, `venv.lock` (Task 3)
├── tools/
│   └── fetch_wt_portable.ps1     ← novo (Task 7)
├── README.md                     ← +1 subseção (Task 8)
├── MANUAL_INSTALACAO.txt         ← +1 nota (Task 8)
└── bin/README.md                 ← +1 parágrafo (Task 8)
```

---

### Task 1: `launch-config.json`

**Agent:** `executor`

**Files:**
- Create: `launch-config.json` (repo root)

**Interfaces:**
- Produces: um objeto JSON com `defaultProfile` (string), `profiles`
  (dict de `{description, flags[], requiresBatchDir?}`), `paths` (dict de
  paths relativos à raiz do repo: `venv`, `ffmpegExe`, `ffprobeExe`,
  `windowsTerminalExe`, `requirements`, `encoderScript`). Task 2 (`Read-LauncherConfig`) consome exatamente esse shape.

- [ ] **Step 1: Escrever `launch-config.json` com o conteúdo exato abaixo**

```json
{
  "defaultProfile": "balanced",
  "profiles": {
    "fast": {
      "description": "Preview rápido",
      "flags": ["--performance", "speed", "--enhance", "off"]
    },
    "balanced": {
      "description": "Padrão recomendado",
      "flags": ["--performance", "balanced", "--enhance", "on", "--enhance-ai", "on"]
    },
    "quality": {
      "description": "Máxima qualidade",
      "flags": ["--performance", "quality", "--mode", "2pass", "--enhance", "on"]
    },
    "cinematic": {
      "description": "Film emulation (Cineon + Portra 400)",
      "flags": ["--cineon-pipeline", "on", "--exposure-offset", "+0.2", "--saturation", "1.05", "--mode", "2pass"]
    },
    "batch": {
      "description": "Processar pasta inteira (-InputFile aponta pra pasta)",
      "flags": ["--enhance", "on"],
      "requiresBatchDir": true
    }
  },
  "paths": {
    "venv": "venv",
    "ffmpegExe": "bin/ffmpeg.exe",
    "ffprobeExe": "bin/ffprobe.exe",
    "windowsTerminalExe": "bin/WindowsTerminal/wt.exe",
    "requirements": "requirements.txt",
    "encoderScript": "Reels_Encoder_v2_FINAL.py"
  }
}
```

- [ ] **Step 2: Validar que é JSON válido**

Run: `powershell -NoProfile -Command "Get-Content launch-config.json -Raw | ConvertFrom-Json | Out-Null; Write-Host EXIT $LASTEXITCODE"`
Expected: nenhuma exceção impressa (se `ConvertFrom-Json` falhar, o
PowerShell lança um erro terminante e o `Write-Host` final não roda —
nesse caso o JSON está malformado e deve ser corrigido antes de prosseguir).

- [ ] **Step 3: Commit**

```bash
git add launch-config.json
git commit -m "feat(launcher): adicionar launch-config.json com os 5 perfis"
```

---

### Task 2: `launcher.ps1` — skeleton, logging, config loader

**Agent:** `executor`

**Files:**
- Create: `launcher.ps1` (repo root)

**Interfaces:**
- Consumes: `launch-config.json` shape produzido na Task 1.
- Produces: `Write-LauncherLog($Message, $Level)`, `Read-LauncherConfig($Path)`
  (retorna o objeto parseado ou lança exceção com mensagem clara). Guard
  `if ($MyInvocation.InvocationName -ne '.')` no fim do arquivo, ainda vazio
  nesta task — só um comentário `# (corpo principal vem nas próximas tasks)`
  dentro do bloco, pra permitir dot-source seguro já a partir desta task.
  Tasks 3-6 acrescentam funções entre o topo e esse guard, sem tocar nele
  até a Task 6.

**Correção pós-dispatch (achado real do implementador, não do plano
original):** o Step 1 abaixo **não** declara `[CmdletBinding()]` no topo do
`param()`. Uma versão anterior deste plano incluía essa linha; o
implementador do Task 2 encontrou que `[CmdletBinding()]` injeta
automaticamente um parâmetro comum `-Debug`, que colide com o `[switch]$Debug`
explícito do brief (`ParameterNameAlreadyExistsForCommand`, falha já no
dot-source, antes de qualquer função rodar). Sem `[CmdletBinding()]`, essa
colisão não existe e `$PSBoundParameters` (usado na Task 6) continua
funcionando normalmente — não depende de CmdletBinding.

- [ ] **Step 1: Escrever o skeleton inicial**

```powershell
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

if ($MyInvocation.InvocationName -ne '.') {
    # (corpo principal vem nas proximas tasks)
}
```

- [ ] **Step 2: Verificar que dot-source funciona e as funções ficam disponíveis, sem executar o corpo principal**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; Write-LauncherLog -Message 'teste' -Level Success; Write-Host (Get-Command Read-LauncherConfig).Name"
```
Expected: imprime `[OK]    teste` em verde e depois `Read-LauncherConfig` —
prova que dot-source carrega as funções sem tentar rodar o bloco principal
(que ficaria vazio mesmo se rodasse, então esta verificação também confirma
que o guard `$MyInvocation.InvocationName -ne '.'` não lança erro).

- [ ] **Step 3: Verificar erro claro quando `launch-config.json` está ausente**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; try { Read-LauncherConfig -Path 'nao-existe.json' } catch { Write-Host \"CAPTURED: $($_.Exception.Message)\" }"
```
Expected: `CAPTURED: launch-config.json nao encontrado em: nao-existe.json`

- [ ] **Step 4: Verificar carregamento real do `launch-config.json` da Task 1**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); Write-Host $c.defaultProfile"
```
Expected: `balanced`

- [ ] **Step 5: Commit**

```bash
git add launcher.ps1
git commit -m "feat(launcher): skeleton de launcher.ps1 com logging e config loader"
```

---

### Task 3: `launcher.ps1` — gestão de venv

**Agent:** `executor`

**Files:**
- Modify: `launcher.ps1` (acrescentar funções antes do guard `if ($MyInvocation.InvocationName -ne '.')` escrito na Task 2)
- Modify: `.gitignore` (+1 linha)

**Interfaces:**
- Consumes: `Write-LauncherLog` (Task 2).
- Produces: `Test-VenvExists($VenvPath) -> bool`,
  `Resolve-SystemPython() -> string` (path do python.exe do sistema),
  `New-ProjectVenv($RepoRoot, $VenvPath)`,
  `Install-Requirements($RepoRoot, $VenvPython)`,
  `Write-VenvLock($RepoRoot, $VenvPython)`,
  `Initialize-Environment($RepoRoot, $VenvPath) -> string` (path do
  `python.exe` do venv — é isso que a Task 5/6 usam pra tudo depois).

**Correção pós-dispatch (achado real do implementador, não do plano
original):** as chamadas `& $pythonCmd -m venv $VenvPath` (em
`New-ProjectVenv`) e `& $VenvPython -m pip install -r $reqPath` (em
`Install-Requirements`) abaixo terminam em `| Out-Host`. Sem isso, o
stdout do processo externo (verboso no `pip install`) não é consumido por
nada — em PowerShell, saída não capturada de um comando dentro de uma
função vira parte do *return* da função. Como nenhuma das duas chamadas
tinha seu resultado atribuído a uma variável, esse texto vazava e se
concatenava com o `return $venvPython` de `Initialize-Environment`,
corrompendo o path retornado (o implementador do Task 3 pegou isso ao
rodar o Step 4 de verdade: `$py` virou o log inteiro do pip + o path, não
só o path). `Out-Host` mostra a saída em tempo real no console (mesmo
efeito visual pretendido) sem poluir o stream de retorno da função —
`$LASTEXITCODE` continua populado normalmente depois do pipe.

- [ ] **Step 1: Acrescentar a linha do `.gitignore`**

Em `.gitignore`, logo após o bloco `# Virtual environments` (linhas 23-28
hoje: `venv/`, `env/`, `ENV/`, `env.bak/`, `venv.bak/`), acrescentar:

```gitignore
venv.lock
```

- [ ] **Step 2: Acrescentar as funções de venv em `launcher.ps1`, antes do guard final**

```powershell
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
```

- [ ] **Step 3: Verificar `Test-VenvExists` com um venv falso (sem criar venv de verdade ainda)**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; New-Item -ItemType Directory -Force -Path 'C:\Windows\Temp\lt_fake_venv\Scripts' | Out-Null; New-Item -ItemType File -Force -Path 'C:\Windows\Temp\lt_fake_venv\Scripts\python.exe' | Out-Null; Write-Host (Test-VenvExists -VenvPath 'C:\Windows\Temp\lt_fake_venv'); Write-Host (Test-VenvExists -VenvPath 'C:\Windows\Temp\lt_venv_que_nao_existe')"
```
Expected: `True` na primeira linha, `False` na segunda.

- [ ] **Step 4: Verificar `Initialize-Environment` de ponta a ponta, criando um venv real de teste**

Run (usa uma pasta de teste isolada, não o `./venv` real do projeto):
```powershell
Remove-Item -Recurse -Force 'C:\Windows\Temp\lt_real_venv' -ErrorAction SilentlyContinue
powershell -NoProfile -Command ". .\launcher.ps1; $py = Initialize-Environment -RepoRoot (Get-Location) -VenvPath 'C:\Windows\Temp\lt_real_venv'; Write-Host \"PYTHON: $py\"; & $py -c 'import rich, pydantic, numpy; print(\"IMPORTS OK\")'"
```
Expected: cria o venv, instala as dependências reais de `requirements.txt`,
imprime `PYTHON: C:\Windows\Temp\lt_real_venv\Scripts\python.exe` e depois
`IMPORTS OK`. Confirma também que `C:\Windows\Temp\lt_real_venv\venv.lock`
existe (`venv.lock` é escrito relativo a `$RepoRoot`, que aqui é a raiz do
repo — então na prática o arquivo aparece em `./venv.lock` do repo; isso é
esperado e é o comportamento real que a Task 10 valida).

Depois de confirmar, limpar:
```bash
rm -rf /c/Windows/Temp/lt_real_venv /c/Windows/Temp/lt_fake_venv
```

- [ ] **Step 5: Commit**

```bash
git add launcher.ps1 .gitignore
git commit -m "feat(launcher): gestao de venv (criar/reaproveitar, instalar deps, venv.lock)"
```

---

### Task 4: `launcher.ps1` — validação de binários

**Agent:** `executor`

**Files:**
- Modify: `launcher.ps1` (acrescentar funções antes do guard final)

**Interfaces:**
- Consumes: `Write-LauncherLog` (Task 2), shape de `Config.paths` (Task 1).
- Produces: `Test-RequiredBinary($Path, $Name, $FixHint)` (lança exceção
  se ausente), `Resolve-Binaries($RepoRoot, $VenvPython, $Config)` →
  `[PSCustomObject]@{ VenvPython; Ffmpeg; Ffprobe; WtPath; WtAvailable }`
  — Task 6 consome exatamente esse shape (`.WtPath`, `.WtAvailable`,
  `.VenvPython`).

- [ ] **Step 1: Acrescentar as funções de validação**

```powershell
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
```

- [ ] **Step 2: Verificar hard-fail com mensagem clara quando ffmpeg está ausente (caso real hoje — `bin/` não tem ffmpeg.exe commitado)**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); try { Resolve-Binaries -RepoRoot $Script:RepoRoot -VenvPython 'C:\Windows\System32\cmd.exe' -Config $c } catch { Write-Host \"CAPTURED: $($_.Exception.Message)\" }"
```
Expected: `CAPTURED: ffmpeg.exe nao encontrado em: <repo>\bin\ffmpeg.exe` +
a dica `Rode .\tools\fetch_ffmpeg.ps1 ...` na linha seguinte (mensagem
multi-linha via `` `n ``). Usamos `cmd.exe` como stand-in de "Python válido"
só pra isolar o teste no binário que falta (ffmpeg) sem depender de venv
real.

- [ ] **Step 3: Verificar `WtAvailable = $false` quando `bin/WindowsTerminal/wt.exe` não existe (caso real hoje) e que isso NÃO lança exceção**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); New-Item -ItemType Directory -Force -Path 'C:\Windows\Temp\lt_bin\bin' | Out-Null; 'x' | Out-File 'C:\Windows\Temp\lt_bin\bin\ffmpeg.exe'; 'x' | Out-File 'C:\Windows\Temp\lt_bin\bin\ffprobe.exe'; $c.paths.ffmpegExe='bin/ffmpeg.exe'; $r = Resolve-Binaries -RepoRoot 'C:\Windows\Temp\lt_bin' -VenvPython 'C:\Windows\System32\cmd.exe' -Config $c; Write-Host \"WtAvailable=$($r.WtAvailable)\""
```
Expected: imprime o aviso amarelo `[AVISO] Windows Terminal portatil nao
encontrado ...` seguido de `WtAvailable=False` — sem lançar exceção.
Limpar depois: `rm -rf /c/Windows/Temp/lt_bin`.

- [ ] **Step 4: Commit**

```bash
git add launcher.ps1
git commit -m "feat(launcher): validacao de binarios (python/ffmpeg/ffprobe obrigatorios, wt.exe opcional)"
```

---

### Task 5: `launcher.ps1` — montagem de comandos

**Agent:** `executor`

**Files:**
- Modify: `launcher.ps1` (acrescentar funções antes do guard final)

**Interfaces:**
- Consumes: shape de `Config.profiles`/`Config.paths` (Task 1).
- Produces: `Build-ProfileArgs($ProfileName, $Config, $BatchDir) -> string[]`,
  `Build-SetupCommand($VenvPython, $RepoRoot, $Config) -> string`,
  `Build-EncodeCommand($VenvPython, $RepoRoot, $Config, $InputFile, $ProfileName) -> string`
  — Task 6 chama essas três com `$ProfileName = $null` para o caso
  "sem flags → wizard".

- [ ] **Step 1: Acrescentar as funções de montagem de comando**

```powershell
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
    $args = @($profileDef.flags)
    if ($profileDef.requiresBatchDir) {
        if (-not $BatchDir) {
            throw "Perfil '$ProfileName' exige uma pasta de entrada: use -InputFile <pasta>."
        }
        $args = @("--batch", $BatchDir, "--output-dir", $BatchDir) + $args
    }
    return $args
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
```

- [ ] **Step 2: Verificar `Build-ProfileArgs` para o perfil `cinematic` e o erro de perfil desconhecido**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); Write-Host (Build-ProfileArgs -ProfileName 'cinematic' -Config $c -join ' '); try { Build-ProfileArgs -ProfileName 'inexistente' -Config $c } catch { Write-Host \"CAPTURED: $($_.Exception.Message)\" }"
```
Expected: `--cineon-pipeline on --exposure-offset +0.2 --saturation 1.05 --mode 2pass`
na primeira linha; `CAPTURED: Perfil 'inexistente' nao existe em
launch-config.json. Perfis disponiveis: fast, balanced, quality, cinematic, batch`
na segunda.

- [ ] **Step 3: Verificar `Build-ProfileArgs` do perfil `batch` sem `-InputFile` (deve falhar) e com (deve montar `--batch`/`--output-dir`)**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); try { Build-ProfileArgs -ProfileName 'batch' -Config $c } catch { Write-Host \"CAPTURED: $($_.Exception.Message)\" }; Write-Host (Build-ProfileArgs -ProfileName 'batch' -Config $c -BatchDir 'C:\clips' -join ' ')"
```
Expected: `CAPTURED: Perfil 'batch' exige uma pasta de entrada: use -InputFile <pasta>.`
na primeira linha; `--batch C:\clips --output-dir C:\clips --enhance on` na
segunda.

- [ ] **Step 4: Verificar `Build-SetupCommand` e `Build-EncodeCommand` (caso wizard e caso preset direto)**

Run:
```powershell
powershell -NoProfile -Command ". .\launcher.ps1; $c = Read-LauncherConfig -Path (Join-Path $Script:RepoRoot 'launch-config.json'); Write-Host (Build-SetupCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $c); Write-Host (Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $c -InputFile '' -ProfileName $null); Write-Host (Build-EncodeCommand -VenvPython 'PY' -RepoRoot 'ROOT' -Config $c -InputFile 'video.mp4' -ProfileName 'fast')"
```
Expected (paths relativos a `ROOT`, montados via `Join-Path`, então em
Windows aparecem com `\`):
```
& 'PY' 'ROOT\Reels_Encoder_v2_FINAL.py' --hardware-info
& 'PY' 'ROOT\Reels_Encoder_v2_FINAL.py' --ui
& 'PY' 'ROOT\Reels_Encoder_v2_FINAL.py' 'video.mp4' --performance speed --enhance off
```

- [ ] **Step 5: Commit**

```bash
git add launcher.ps1
git commit -m "feat(launcher): montagem de comandos (setup, wizard, preset direto por perfil)"
```

---

### Task 6: `launcher.ps1` — lançamento de abas + orquestração principal

**Agent:** `executor`

**Files:**
- Modify: `launcher.ps1` (acrescenta `Open-LauncherTabs` e preenche o corpo do guard final escrito na Task 2)

**Interfaces:**
- Consumes: tudo das Tasks 2-5 (`Read-LauncherConfig`, `Initialize-Environment`,
  `Resolve-Binaries`, `Build-SetupCommand`, `Build-EncodeCommand`).
- Produces: `Open-LauncherTabs($SetupCmd, $EncodeCmd, $WtPath, $WtAvailable)`;
  o script completo, executável via `.\launcher.ps1 [-InputFile ...] [-Profile ...] [-Debug] [-SkipValidation] [-SkipEnvSetup]`.

- [ ] **Step 1: Acrescentar `Open-LauncherTabs` antes do guard final**

```powershell
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
```

- [ ] **Step 2: Preencher o corpo do guard final (substituir o comentário-placeholder da Task 2)**

Substituir:
```powershell
if ($MyInvocation.InvocationName -ne '.') {
    # (corpo principal vem nas proximas tasks)
}
```
por:
```powershell
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
```

- [ ] **Step 3: Verificar sintaxe do arquivo inteiro (parse, sem executar)**

Run: `powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content .\launcher.ps1 -Raw), [ref]$null); Write-Host 'PARSE OK'"`
Expected: `PARSE OK`, sem erros de parser.

- [ ] **Step 4: Verificar dot-source continua funcionando após o preenchimento do guard (não deve rodar o corpo principal)**

Run: `powershell -NoProfile -Command ". .\launcher.ps1; Write-Host 'DOT-SOURCE OK'"`
Expected: `DOT-SOURCE OK`, sem tentar criar venv nem abrir nenhuma janela
(dot-source nunca satisfaz `$MyInvocation.InvocationName -ne '.'`).

- [ ] **Step 5: Verificar `-SkipEnvSetup` sem venv existente falha com mensagem clara (sem tentar criar nada)**

Run: `powershell -NoProfile -File .\launcher.ps1 -InputFile x.mp4 -Profile fast -SkipEnvSetup -SkipValidation`
(rodar numa cópia do repo ou confirmar antes que `./venv` não existe;
se `./venv` já existir de execuções anteriores desta mesma task, mover
temporariamente antes do teste e devolver depois)
Expected: `[ERRO] -SkipEnvSetup exige um venv existente em <repo>\venv, mas Scripts\python.exe nao foi encontrado.`, exit code 1.

- [ ] **Step 6: Commit**

```bash
git add launcher.ps1
git commit -m "feat(launcher): lancamento de abas (WT + fallback) e orquestracao principal"
```

---

### Task 7: `tools/fetch_wt_portable.ps1`

**Agent:** `executor`

**Files:**
- Create: `tools/fetch_wt_portable.ps1`

**Interfaces:**
- Produces: `bin/WindowsTerminal/wt.exe` (+ arquivos irmãos) em disco quando
  executado — é exatamente o path que `launch-config.json.paths.windowsTerminalExe`
  (Task 1) e `Resolve-Binaries` (Task 4) esperam.

**Correção pós-dispatch (achado real do implementador, não do plano
original — erro de transcrição do próprio Orquestrador):** o `$WtSha256`
abaixo termina em `...4383BD`. Uma versão anterior deste plano (e do spec)
tinha `...4383B`, faltando o último dígito hex — 63 caracteres em vez dos
64 de um SHA256 válido. O implementador do Task 7 rodou o download de
verdade, mediu o hash real do ZIP oficial (`Get-FileHash`), viu que batia
com o valor do plano exceto por esse `D` final faltando, e corretamente
abortou em vez de aceitar um binário "quase verificado" — o script em si
já aborta e apaga o ZIP quando o checksum não bate (essa é a garantia de
segurança do Task 7, e ela funcionou como projetado).

- [ ] **Step 1: Escrever o script com o conteúdo exato abaixo**

Versão e SHA256 verificados de verdade durante o brainstorming (baixado +
`sha256sum` conferido + `unzip -l` inspecionado) — não são placeholder.

```powershell
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

if (Test-Path $DestDir) {
    Write-Host "Removendo instalacao portatil anterior em $DestDir ..." -ForegroundColor Yellow
    Remove-Item $DestDir -Recurse -Force
}

$extractTemp = Join-Path $env:TEMP "wt_portable_extract_$([guid]::NewGuid().ToString('N'))"
Write-Host "Extraindo para $DestDir ..." -ForegroundColor Cyan
Expand-Archive -Path $TempZip -DestinationPath $extractTemp -Force

$innerFolder = Get-ChildItem -Path $extractTemp -Directory | Select-Object -First 1
if (-not $innerFolder) {
    throw "ZIP extraido nao contem a pasta esperada (formato do release mudou?)."
}
Move-Item -Path $innerFolder.FullName -Destination $DestDir
Remove-Item $extractTemp -Recurse -Force
Remove-Item $TempZip -Force

$wtExe = Join-Path $DestDir "wt.exe"
if (-not (Test-Path $wtExe)) {
    throw "wt.exe nao encontrado apos extracao em $DestDir - conteudo do ZIP pode ter mudado."
}

New-Item -ItemType File -Path (Join-Path $DestDir ".portable") -Force | Out-Null

Write-Host "OK    Windows Terminal portatil instalado em: $DestDir" -ForegroundColor Green
Write-Host "      wt.exe: $wtExe" -ForegroundColor Green
```

- [ ] **Step 2: Rodar de verdade e confirmar a instalação**

Run: `.\tools\fetch_wt_portable.ps1`
Expected: baixa, confere o checksum (`OK    checksum confere
(7691EFEB71C8DD0B95536C84E366FA4CF809A42C534912F9CEFA1056534383BD)`),
extrai, e termina com `OK    Windows Terminal portatil instalado em:
<repo>\bin\WindowsTerminal`.

- [ ] **Step 3: Confirmar os arquivos no disco e que `wt.exe` roda**

Run:
```powershell
Test-Path .\bin\WindowsTerminal\wt.exe
Test-Path .\bin\WindowsTerminal\.portable
& .\bin\WindowsTerminal\wt.exe --version
```
Expected: `True`, `True`, e a versão impressa bate com `1.24.11911.0`
(confirma que `wt.exe` roda standalone com os arquivos irmãos extraídos —
não depende de MSIX/Windows App SDK instalado no sistema).

- [ ] **Step 4: Commit**

```bash
git add tools/fetch_wt_portable.ps1
git commit -m "feat(tools): fetch_wt_portable.ps1 - baixa a distribuicao portatil oficial do Windows Terminal"
```

---

### Task 8: Documentação (README.md, MANUAL_INSTALACAO.txt, bin/README.md)

**Agent:** `executor`

**Files:**
- Modify: `README.md`
- Modify: `MANUAL_INSTALACAO.txt`
- Modify: `bin/README.md`

**Interfaces:** nenhuma (só texto).

- [ ] **Step 1: `README.md` — inserir nova subseção dentro de "## 📦 Portabilidade — FFmpeg embarcado"**

Localizar a linha `## 🚀 Instalação Completa` (comando:
`grep -n "^## 🚀 Instalação Completa" README.md`) e inserir o bloco
abaixo **imediatamente antes** dela (ou seja, como última subseção de
"## 📦 Portabilidade — FFmpeg embarcado"):

```markdown
### Launcher portátil (`launcher.ps1`)

Pra rodar em qualquer máquina Windows sem configurar Python manualmente:

```powershell
.\launcher.ps1                                    # cria venv + abre o wizard interativo
.\launcher.ps1 -InputFile "video.mp4" -Profile "cinematic"   # preset direto, sem wizard
```

Cria um venv local em `./venv` (instala via `requirements.txt`, mesma fonte
de sempre), valida `bin/ffmpeg.exe`/`bin/ffprobe.exe` e abre 2 abas
(Setup + Encode) no Windows Terminal — se `.\tools\fetch_wt_portable.ps1`
não tiver sido rodado ainda, cai automaticamente em duas janelas
PowerShell separadas. Perfis disponíveis: `fast`, `balanced` (padrão),
`quality`, `cinematic`, `batch`. Nenhum perfil fixa CRF — a análise
adaptativa do encoder continua decidindo isso.
```

- [ ] **Step 2: `MANUAL_INSTALACAO.txt` — inserir nota antes do "APÊNDICE B"**

Localizar a linha `APÊNDICE B: GUIA RÁPIDO DE COMANDOS` (comando:
`grep -n "APÊNDICE B: GUIA RÁPIDO DE COMANDOS" MANUAL_INSTALACAO.txt`) —
essa linha é precedida por um `================...` (divisor) e seguida
por outro. Inserir o bloco abaixo **antes** do divisor que precede essa
linha (ou seja, como último conteúdo antes do APÊNDICE B):

```text
================================================================================
USO PORTÁTIL (OPCIONAL): launcher.ps1
================================================================================

Se preferir não instalar nada manualmente, use o launcher.ps1 na raiz do
projeto: ele cria um venv local (./venv), instala as dependências, valida
o FFmpeg e abre o encoder pronto pra uso.

  .\launcher.ps1

Isso é um caminho alternativo ao PASSO 1-3 acima, não uma substituição -
os passos manuais continuam funcionando normalmente.

```

- [ ] **Step 3: `bin/README.md` — acrescentar seção sobre o Windows Terminal portátil, ao final do arquivo**

Acrescentar ao final de `bin/README.md` (após a seção "## Versionamento"):

```markdown

## Windows Terminal portátil (opcional)

`launcher.ps1` abre 2 abas (Setup + Encode) usando o Windows Terminal se
`./bin/WindowsTerminal/wt.exe` existir. Sem ele, cai automaticamente em
duas janelas PowerShell separadas — não é obrigatório.

### Como obter

```powershell
./tools/fetch_wt_portable.ps1
```

Baixa a distribuição portátil **oficial** do Windows Terminal (ZIP
"unpackaged" publicado em
[`github.com/microsoft/terminal/releases`](https://github.com/microsoft/terminal/releases),
documentado em
[Microsoft Learn](https://learn.microsoft.com/en-us/windows/terminal/distributions)),
confere o SHA256 antes de extrair, e extrai a pasta inteira (não é só um
`.exe` — `wt.exe` precisa dos DLLs/recursos ao lado) para
`./bin/WindowsTerminal/`.

Requer Windows 10 19041+ ou Windows 11.
```

- [ ] **Step 4: Verificar que o markdown novo não quebra o lint do README (mesma regra do resto do repo)**

Run: `npx --yes markdownlint-cli2@0.23.1 README.md`
Expected: `Summary: 0 issues in 0 files` (mesmo padrão de saída já
documentado no ciclo P de `.claude/memory/STATE.md`). Se aparecerem
avisos novos (ex. `MD040` no fence do bloco de comando), corrigir o
bloco recém-inserido no mesmo padrão do resto do arquivo antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add README.md MANUAL_INSTALACAO.txt bin/README.md
git commit -m "docs: documentar launcher.ps1 (README, MANUAL_INSTALACAO, bin/README) - aditivo"
```

---

### Task 9: Validação de integração completa (execução real)

**Agent:** `executor-pesado`

**Files:**
- Nenhum arquivo novo. Escreve o checklist de evidência em `.claude/memory/STATE.md`
  (append — nunca reescrever linhas existentes, conforme o cabeçalho do
  arquivo).

**Interfaces:**
- Consumes: todos os artefatos das Tasks 1-8 já commitados.

Esta é a única task "sem supervisão" do ciclo (roda o bootstrap completo de
verdade, incluindo rede/pip/lançamento de janelas) — por isso vai pra
`executor-pesado`, conforme a tabela de delegação do `CLAUDE.md`.

- [ ] **Step 0 (correção pós-Task 7/8 — plano original não previa isso): preparar baseline de verdade**

A Task 7 já baixou e validou `bin/WindowsTerminal/wt.exe` de verdade nesta
mesma worktree (commit `e06fd12`/`cc72648`). Se o Step 3 rodar com o WT já
presente, o caminho de fallback (2 janelas PowerShell) nunca é exercitado de
verdade — o launcher iria direto para o caminho de 2 abas, colidindo com o
"Expected" do Step 3. Correção: mover `bin/WindowsTerminal` para fora da
árvore do repo *antes* do Step 1, para que o Step 4 dispare um
`fetch_wt_portable.ps1` real (download+checksum+extração de verdade, não um
no-op) — mesma cobertura de rede que a Task 7 já provou, mas agora como parte
do fluxo de integração ponta-a-ponta. Também: `teste.mp4` não existe nesta
worktree (só existe na raiz do repo principal) — copiar de lá antes do Step 4.

Run:
```powershell
Move-Item .\bin\WindowsTerminal ..\..\..\..\_task9_wt_backup -ErrorAction SilentlyContinue
Copy-Item ..\..\..\..\teste.mp4 .\teste.mp4
```
(ajustar os `..` conforme a profundidade real da worktree até a raiz do repo
principal `encoder_ai_instagram`; confirmar com `git rev-parse
--show-toplevel` antes de montar o caminho relativo, ou usar caminho absoluto
`C:\Users\Usuario\Documents\GitHub\encoder_ai_instagram\teste.mp4`.)
Documentar no `STATE.md` que essa preparação foi necessária e por quê (plan
defect: Task 9 assumia máquina totalmente limpa, mas roda na mesma worktree
onde a Task 7 já teve efeito colateral real).

- [ ] **Step 1: Baseline — confirmar que `./venv`, `./bin/ffmpeg.exe` e `./bin/WindowsTerminal/wt.exe` não existem antes do teste (devem estar todos `False` após o Step 0)**

Run: `Test-Path .\venv; Test-Path .\bin\ffmpeg.exe; Test-Path .\bin\WindowsTerminal\wt.exe`
Documentar os 3 resultados no `STATE.md` como estado inicial.

- [ ] **Step 2: Rodar `.\tools\fetch_ffmpeg.ps1` (pré-requisito real do encoder, fora do escopo deste plano mas necessário pro launcher passar da validação)**

Run: `.\tools\fetch_ffmpeg.ps1`
Expected: `ffmpeg.exe`/`ffprobe.exe`/`ffplay.exe` copiados para `./bin`.
Colar a saída real no `STATE.md`.

- [ ] **Step 3: Rodar `.\launcher.ps1` sem argumentos (caminho: venv novo + WT ausente ainda → fallback + wizard)**

Run: `.\launcher.ps1 -Debug`
Expected: cria `./venv`, instala requirements, gera `./venv.lock`, avisa
que `WindowsTerminal` está ausente, abre 2 janelas PowerShell separadas
(Setup rodando `--hardware-info`, Encode rodando `--ui`). Colar a saída
completa (incluindo os logs `[DEBUG]`) no `STATE.md`. Fechar as janelas
manualmente depois de confirmar que abriram e não deram erro.

- [ ] **Step 4: Rodar `.\tools\fetch_wt_portable.ps1`, depois `.\launcher.ps1` de novo (caminho: venv reaproveitado + WT disponível → 2 abas reais)**

Run: `.\tools\fetch_wt_portable.ps1; .\launcher.ps1 -InputFile "teste.mp4" -Profile "fast" -Debug`
Expected: pula a criação do venv (reaproveita, log `[INFO] Venv existente
reaproveitado`), abre o Windows Terminal de verdade com 2 abas ("Setup" e
"Encode"), aba Encode roda o comando `--performance speed --enhance off`
sobre `teste.mp4` (copiado no Step 0). Colar a saída no `STATE.md`. Fechar a
janela do WT depois de confirmar. Depois de confirmado, remover o backup
`_task9_wt_backup` (não é mais necessário — o WT real já foi re-obtido pelo
fetch script nesta task).

- [ ] **Step 5: Disparar cada falha tratada de propósito, uma de cada vez, e confirmar a mensagem exata**

Para cada cenário, rodar o comando, colar a mensagem de erro real no
`STATE.md`, e confirmar que bate com a tabela "Falhas tratadas" do spec
(`docs/superpowers/specs/2026-08-13-launcher-portavel-design.md`):

- `requirements.txt` ausente: renomear temporariamente, rodar
  `.\launcher.ps1`, confirmar erro, devolver o nome original.
- `-SkipEnvSetup` sem venv: mover `./venv` temporariamente, rodar
  `.\launcher.ps1 -SkipEnvSetup`, confirmar erro, devolver `./venv`.
- Perfil inválido: `.\launcher.ps1 -InputFile teste.mp4 -Profile "inexistente"`,
  confirmar erro com a lista de perfis válidos.
- `-SkipValidation`: `.\launcher.ps1 -SkipValidation` com `./bin/ffmpeg.exe`
  temporariamente renomeado — confirmar que a validação é pulada e o
  launcher tenta abrir mesmo assim (o erro, se houver, vem de dentro do
  encoder, não do launcher).

- [ ] **Step 6: Registrar o checklist final no `STATE.md`**

Formato (append, seguindo o padrão de tabela já usado no arquivo):

```markdown
## Ciclo Q — launcher portátil (launcher.ps1) — validação de integração — 2026-08-13

| ID | status | arquivo tocado | resultado |
|----|--------|----------------|-----------|
| Q9.1 | done | — | baseline: venv=False, ffmpeg=False, wt=False antes do teste |
| Q9.2 | done | bin/ffmpeg.exe, bin/ffprobe.exe, bin/ffplay.exe | fetch_ffmpeg.ps1 OK |
| Q9.3 | done | venv/, venv.lock | launcher.ps1 sem args: venv novo + fallback 2 janelas — OK |
| Q9.4 | done | bin/WindowsTerminal/ | fetch_wt_portable.ps1 + launcher.ps1 -Profile fast: venv reaproveitado + 2 abas WT reais — OK |
| Q9.5 | done | — | 4 falhas tratadas disparadas de proposito, mensagens conferem com o spec |
```

(colar as saídas reais completas de cada step acima como texto, não
parafrasear — conforme `superpowers:verification-before-completion`)

- [ ] **Step 7: Commit**

```bash
git add .claude/memory/STATE.md
git commit -m "docs(state): registrar validacao de integracao do launcher portatil (ciclo Q)"
```

---

## Self-Review (Orquestrador)

- **Cobertura do spec:** Architecture (Tasks 1-7), Fluxo de execução
  (Tasks 3-6), Perfis (Task 1/5), Componentes (Tasks 1,3-7), Falhas
  tratadas (Tasks 3-6, verificadas na Task 9), seção "Windows Terminal —
  distribuição portátil oficial" (Task 7, com versão/checksum reais),
  Documentação (Task 8), Validação (Task 9). Nenhuma seção do spec ficou
  sem task correspondente.
- **Placeholders:** nenhum "TBD"/"implementar depois" — inclusive a parte
  mais arriscada (fonte do WT) tem URL, versão e SHA256 reais, verificados
  por download de verdade nesta sessão.
- **Consistência de tipos/nomes:** `Resolve-Binaries` (Task 4) retorna
  `.VenvPython/.WtPath/.WtAvailable`, usados com esses nomes exatos em
  `Open-LauncherTabs` (Task 6). `Build-EncodeCommand` (Task 5) usa
  `$ProfileName` (não `$Profile` — evita colidir com o parâmetro global
  `$Profile` do script), consistente entre definição e chamada na Task 6.
  `Config.paths.windowsTerminalExe` (Task 1) é o mesmo path lido em
  `Resolve-Binaries` (Task 4) e documentado em `bin/README.md` (Task 8).
