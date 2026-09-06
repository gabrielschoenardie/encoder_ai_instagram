<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AX: `launcher.ps1` vira bootstrap de verdade (working dir, quoting, gates, cache de deps)

Data: 2026-09-06 | Ciclo: AX | Origem: auditoria do Orquestrador sobre `launcher.ps1` + `launch-config.json` (2026-09-06), a pedido do usuário. Ciclo anterior: AW (consolidação do LUT v6.8). Nenhum finding aberto do `FINDINGS.md` é consumido aqui — os achados abaixo são **novos** e recebem IDs `AXF1..AXF11` na Task AX12.

## Contexto

O usuário desenhou a arquitetura-alvo do launcher:

```
launcher.ps1 → carregar config → VALIDAR CONFIG → VERIFICAR PYTHON DO SISTEMA
             → venv? (cria|reusa) → REQUIREMENTS MUDOU? (pip|pula)
             → validar ambiente (Python, Encoder, FFmpeg, FFprobe, Terminal)
             → VALIDAR ARGUMENTOS → montar comando → Windows Terminal (2 abas)
```

Dos 9 nós, **5 já existem e estão corretos**. Este ciclo implementa os 4 que faltam
(maiúsculas acima) e corrige 4 defeitos concretos encontrados na auditoria.

**Decisão de escopo do Orquestrador — NVENC fica de fora.** `grep -il nvenc` sobre todo `.py`
do repo retorna **zero arquivos**: o pipeline é libx264 puro. Validar NVENC seria gate sobre
capacidade que o encoder não usa, e reprovaria máquinas boas. No lugar dele entra a validação
de **capacidade real do FFmpeg** (`libx264`, `lut3d`, `zscale`), que hoje não existe em lugar
nenhum e é dependência de fato — `zscale` aparece 13× e `lut3d` 1× em
`Reels_Encoder_v2_FINAL.py` + `cineon_pipeline.py`, e `zscale` exige `libzimg`, ausente em
vários builds de FFmpeg.

## Diagnóstico — os 11 achados

Medidos por leitura em 2026-09-06. **Nada foi executado**: não há `pwsh` no container do
Orquestrador. Toda âncora `arquivo:linha` abaixo é conferível.

| ID | severidade | âncora | defeito |
|----|-----------|--------|---------|
| AXF1 | **S1** | `launcher.ps1:252-268` | `Open-LauncherTabs` abre `wt`/`Start-Process` **sem** diretório de trabalho. `Reels_Encoder_v2_FINAL.py:4058` e `enhance_visualizer.py:36,155,276,408` escrevem `enhance_maps` como caminho **relativo** → máscaras MCTF e mapas de preflight caem no CWD da aba (tipicamente a home do usuário), não na raiz do projeto. Como `--enhance-ai on` é default e está no perfil `balanced`, acontece em todo encode padrão |
| AXF2 | **S2** | `launcher.ps1:213` | `Build-ProfileArgs` injeta `@("--batch", $BatchDir, "--output-dir", $BatchDir)` **sem aspas**, e `Build-EncodeCommand:249` faz `-join " "`. Qualquer pasta com espaço (`D:\Meus Reels\clips`) vira dois argumentos e o encoder morre em `Reels_Encoder_v2_FINAL.py:4463`. Quebrado hoje para o caso comum, não só para o exótico |
| AXF3 | **S2** | `launcher.ps1:225,244-249` | Caminhos são interpolados dentro de aspas simples sem escapar (`"'$InputFile'"`). Um apóstrofo (`D:\Gabriel's Reels\clip.mp4`) fecha a string cedo e a aba recebe comando que não parseia |
| AXF4 | **S3** | `launcher.ps1:237-249` + `Reels_Encoder_v2_FINAL.py:4440,4446` | `-Profile X` **sem** `-InputFile` monta comando sem posicional; o encoder cai em `args.input is None and args.batch is None`, abre a UI e faz `args = launched`, **substituindo o Namespace inteiro**. As flags do perfil são descartadas em silêncio |
| AXF5 | **S3** | `launcher.ps1` (ausência) | `-InputFile` nunca passa por `Test-Path`. Typo só falha dentro da aba, depois de venv+pip. E o perfil `batch` não checa `-PathType Container` |
| AXF6 | **S3** | `launcher.ps1:148,119-134` | `Install-Requirements` roda em **todo** lançamento e `Write-VenvLock` roda `pip freeze` cujo arquivo **ninguém lê**. Custo por launch e, pior, `throw` em `:114` derruba o launch inteiro se a rede cair — com o venv já correto |
| AXF7 | **S3** | `launcher.ps1:66-72` | `Resolve-SystemPython` devolve o primeiro `py`/`python` do PATH sem checar versão. `pyproject.toml:10` exige `>=3.11`. Python 3.9 antigo ou o stub da Microsoft Store passam e só quebram depois, com mensagem obscura |
| AXF8 | **S4** | `launcher.ps1:48-59` | `Read-LauncherConfig` só faz `ConvertFrom-Json`. Sem `paths.venv`, o `Join-Path` de `:280` estoura com erro de binding de parâmetro; `defaultProfile` inválido só quebra depois em `Build-ProfileArgs` |
| AXF9 | **S4** | `launcher.ps1:174-180` vs `ui/binaries.py:37-52` | `Resolve-Binaries` valida `bin/ffmpeg.exe` e **descarta o caminho**; o filho resolve sozinho (bin/ → PATH → nome nu). É o `QF2` do `FINDINGS.md` ainda vivo na prática |
| AXF10 | **S4** | `launcher.ps1:10` | `[string]$Profile` sombreia a variável automática `$PROFILE` (PSScriptAnalyzer: `PSAvoidAssignmentToAutomaticVariable`) |
| AXF11 | **S4** | `launcher.ps1:261,265,266` | `powershell` hardcoded (sempre WinPS 5.1 mesmo com pwsh 7 instalado) e sem `-NoProfile` — carrega o `$PROFILE` do usuário em cada aba |

### `launch-config.json` — auditoria separada

As flags dos 5 perfis foram conferidas **uma a uma** contra `build_parser()`
(`Reels_Encoder_v2_FINAL.py:4198-4380`): **todas existem**, todos os valores estão dentro dos
`choices`/tipos, `--exposure-offset +0.2` parseia como float, e `cinematic --mode 2pass` é
honrado (`:4088`, `run_ffmpeg_with_cineon(mode=args.mode)`). Nenhum `--crf` fixo — a Regra de
Ouro está respeitada e `tests/launch-config.Tests.ps1:69` guarda isso. **Não há bug de flag.**

O que há é omissão:

| ID | achado |
|----|--------|
| AXC1 | `fast` declara `--enhance off` mas herda `--enhance-ai on` + `--mctf on`. O encoder degrada corretamente (`:4023-4029`, `enhance_ai=False`; MCTF é gated por `enhance_ai` em `:4052`), mas **imprime o aviso amarelo "⚠ --enhance-ai on requer --enhance on" em todo preview** |
| AXC2 | `quality` herda `--enhance-ai on`/`--mctf on` — é o desejado, mas implícito |
| AXC3 | `cinematic` herda `--performance balanced` num pipeline PyAV per-frame (5-15 fps CPU), e herda `--enhance on` + `--enhance-ai on` + `--mctf on` — a combinação mais cara do repo, implícita |
| AXC4 | `paths.requirements` é **configuração morta**: `Install-Requirements:100` hardcoda `Join-Path $RepoRoot "requirements.txt"`. Pior, `tests/launch-config.Tests.ps1:117` valida o arquivo, dando a impressão de que a chave é lida |
| AXC5 | Faltam as chaves que os nós novos exigem: `minPythonVersion`, `validation.*`, `terminal.*` |

## Desenho

### Princípio de segurança do ciclo

Toda mudança de comportamento observável é **declarada aqui** e tem escape hatch por flag ou
por config. Nada é "melhorado" em silêncio. Duas mudanças **intencionalmente quebram** o
comportamento anterior — `AX5` (perfil sem input vira erro) e `AX6` (pip deixa de rodar sempre)
— e cada uma ganha uma saída explícita.

### Armadilha nº 1 do ciclo — `QF1` (regressão de stderr nativo)

Este ciclo adiciona **três** novas invocações de comando nativo: a probe de versão do Python
(`AX8`), a probe de capacidades do FFmpeg (`AX9`) e a sanidade do venv (`AX6`). Em pwsh 7.3+,
com `$ErrorActionPreference = "Stop"`, stderr de comando nativo vira `NativeCommandError`
terminante quando o chamador funde streams — foi exatamente o `QF1` do Ciclo Q
(`FINDINGS.md:187`).

**Toda** invocação nativa nova DEVE seguir o padrão já usado em `New-ProjectVenv:81-88`:

```powershell
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try   { $out = & $exe @args 2>&1 }
finally { $ErrorActionPreference = $prevEap }
```

Não basta o `$PSNativeCommandUseErrorActionPreference = $false` do topo — ele é escopo de
script e o `launcher.ps1` é dot-sourced pelos testes, onde o escopo é o do chamador.

### Armadilha nº 2 — quoting é o eixo do ciclo

`AX2`/`AX3` introduzem um helper único de quoting. **Todo** caminho que entra numa string de
comando passa por ele; nenhum caminho continua sendo interpolado à mão. Isso muda a saída de
`Build-EncodeCommand` para o perfil `batch`, e o teste que asserta a saída antiga muda junto
(`AX11`) — é mudança declarada, não regressão.

### Assinaturas novas e alteradas

Funções **novas** em `launcher.ps1` (todas testáveis por dot-source, sem I/O quando mockadas):

```
Protect-PSLiteral       -Value <string>                       → string entre aspas simples, com '' escapado
Test-LauncherConfig     -Config <psobject>                     → throw com a chave nomeada, ou $null
Resolve-SystemPython    -MinVersion <string>                   → (assinatura ALTERADA: ganha -MinVersion)
Test-VenvHealthy        -VenvPython <string>                   → bool
Get-RequirementsStamp   -RepoRoot -Config                       → string (hash SHA256 concatenado)
Read-VenvStamp          -VenvPath                               → string ou $null
Write-VenvStamp         -VenvPath -Stamp                        → void
Test-FfmpegCapabilities -Ffmpeg -Config                         → throw nomeando o que falta, ou $null
Resolve-LauncherShell   -Config                                 → 'pwsh' | 'powershell'
Test-LaunchTarget       -InputFile -ProfileName -Config         → throw, ou o caminho absoluto resolvido
```

Funções **alteradas**:

```
Initialize-Environment  ganha -Force <switch>                   (AX6)
Build-SetupCommand      ganha -WorkingDirectory, -Ffmpeg, -Ffprobe   (AX1, AX10)
Build-EncodeCommand     ganha -WorkingDirectory, -Ffmpeg, -Ffprobe   (AX1, AX10)
Open-LauncherTabs       ganha -WorkingDirectory, -Shell          (AX1, AX4)
```

> **Compatibilidade obrigatória:** `-WorkingDirectory`, `-Ffmpeg`, `-Ffprobe` e `-Shell` são
> **opcionais com default**, nunca `[Parameter(Mandatory)]`. Motivo: os 5 testes de
> `Describe 'Open-LauncherTabs — fallback…'` (`tests/launcher.Tests.ps1:430-476`) e os 12 de
> `Build-*Command` chamam essas funções sem os parâmetros novos. Tornar qualquer um deles
> mandatório reprova a suíte inteira sem que haja bug. Defaults: `-Shell` = `'powershell'`,
> os demais = `''` (string vazia → o comportamento antigo, sem `Set-Location`/sem `-d`/sem
> export de env). O bloco principal **sempre** passa todos.

### Parâmetros novos do script

```powershell
param(
    [string]$InputFile,
    [Alias('Profile')][string]$ProfileName,   # AX-F10: -Profile continua funcionando
    [switch]$Debug,
    [switch]$SkipValidation,
    [switch]$SkipEnvSetup,
    [switch]$ForceEnvSetup                    # AX6: escape hatch do cache de deps
)
```

`-ForceEnvSetup` e `-SkipEnvSetup` são mutuamente exclusivos → `throw` claro se ambos.

### `launch-config.json` alvo

```json
{
  "configVersion": 2,
  "defaultProfile": "balanced",
  "minPythonVersion": "3.11",
  "terminal": {
    "preferPwsh": true,
    "noProfile": true
  },
  "validation": {
    "requiredEncoders": ["libx264"],
    "requiredFilters": ["lut3d", "zscale"]
  },
  "profiles": {
    "fast": {
      "description": "Preview rápido — sem enhance, sem AI, sem MCTF",
      "flags": ["--performance", "speed", "--enhance", "off", "--enhance-ai", "off", "--mctf", "off"]
    },
    "balanced": {
      "description": "Padrão recomendado",
      "flags": ["--performance", "balanced", "--enhance", "on", "--enhance-ai", "on"]
    },
    "quality": {
      "description": "Máxima qualidade — 2pass + enhance AI + MCTF",
      "flags": ["--performance", "quality", "--mode", "2pass", "--enhance", "on", "--enhance-ai", "on", "--mctf", "on"]
    },
    "cinematic": {
      "description": "Film emulation (Cineon + Portra 400). Aplica +0.2 EV e saturação 1.05; o mais lento (PyAV per-frame + MCTF)",
      "flags": ["--cineon-pipeline", "on", "--exposure-offset", "+0.2", "--saturation", "1.05", "--mode", "2pass", "--performance", "quality", "--enhance", "on", "--enhance-ai", "on", "--mctf", "on"]
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

Restrições sobre este JSON, **não negociáveis**:

- **Nenhuma flag nova pode ser inventada.** Toda flag acima já existe em `build_parser()`
  (`:4198-4380`) com esses `choices` exatos. Se o executor achar que precisa de outra, **para
  e reporta** — não adiciona.
- **Nenhum `--crf`, `--maxrate`, `--bufsize`, `--preset` x264 ou qualquer parâmetro de rate
  control em preset.** Regra de Ouro (skill `instagram-reels-encoder` § "Regras de Ouro —
  Nunca Violar"): esses valores são derivados pela análise adaptativa do encoder, nunca
  fixados. `tests/launch-config.Tests.ps1:69` guarda `--crf`; a Task `AX11` estende o guarda
  aos outros quatro.
- O arquivo é **UTF-8 sem BOM** e tem acentos. `tests/launch-config.Tests.ps1:61-66` documenta
  por que `description` é validado só por presença, nunca por valor (WinPS 5.1 lê sem-BOM como
  ANSI e entrega mojibake). **Manter assim**: não adicionar BOM, não assertar valor de
  `description`.

## Tarefas

Ordem de execução obrigatória. `AX1`-`AX5` não tocam Python; `AX6`-`AX10` tocam. `AX11` fecha
os testes; `AX12` fecha a memória.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| **AX1** | **Working dir (AXF1).** Adicionar `-WorkingDirectory` (opcional, default `''`) a `Build-SetupCommand`, `Build-EncodeCommand` e `Open-LauncherTabs`. Quando não-vazio: (a) as duas `Build-*` **prefixam** a string com `Set-Location <literal protegido>; `; (b) `Open-LauncherTabs` passa `--startingDirectory <path>` em **cada** `new-tab` do ramo wt e `-WorkingDirectory <path>` em **cada** `Start-Process` do fallback. Bloco principal passa `$Script:RepoRoot`. Cinto **e** suspensório de propósito: `wt` reaproveita processo existente e pode ignorar env/CWD do chamador; o `Set-Location` dentro da string é o que garante — e é o que dá pra assertar em Pester | executor-pesado | `launcher.ps1` | `Build-EncodeCommand -WorkingDirectory 'ROOT'` devolve string que começa com `Set-Location 'ROOT'; ` |
| **AX2** | **Quoting central (AXF2, AXF3).** Criar `Protect-PSLiteral` (dobra `'` e envolve em aspas simples; aceita string vazia via `[AllowEmptyString()]`). Passar por ele **todo** caminho que entra em string de comando: `$VenvPython`, `$script`, `$InputFile`, o `$WorkingDirectory` do `AX1`, e — crítico — o `$BatchDir` em `Build-ProfileArgs` (`launcher.ps1:213`), que hoje entra cru e quebra com espaço | executor-pesado | `launcher.ps1` | `Protect-PSLiteral "Gabriel's"` → `'Gabriel''s'`; `Build-ProfileArgs -BatchDir "D:\Meus Reels"` produz `--batch 'D:\Meus Reels'` |
| **AX3** | **Validar config (AXF8).** Criar `Test-LauncherConfig`: exige `defaultProfile`, `profiles`, `paths`; as 6 chaves de `paths` presentes e strings não-vazias; ≥1 perfil, cada um com `flags` array não-vazio; `defaultProfile` ∈ `profiles`; `requiresBatchDir`, quando presente, booleano. Mensagem de erro **nomeia a chave**. Chamar no bloco principal logo após `Read-LauncherConfig`. **Não** mesclar dentro de `Read-LauncherConfig` — os testes de `Describe 'Read-LauncherConfig'` (`:360-385`) exercitam parse isolado e devem seguir passando sem edição | executor-pesado | `launcher.ps1` | `Test-LauncherConfig` com `paths.venv` ausente lança mensagem contendo `paths.venv`; os 4 testes de `Read-LauncherConfig` passam sem edição |
| **AX4** | **Shell (AXF11).** Criar `Resolve-LauncherShell -Config`: devolve `'pwsh'` se `terminal.preferPwsh` ≠ `false` **e** `Get-Command pwsh` encontra; senão `'powershell'`. `Open-LauncherTabs` ganha `-Shell` (opcional, default `'powershell'`) e usa no lugar do literal em `:261,265,266`. Quando `terminal.noProfile` ≠ `false`, incluir `-NoProfile` **antes** de `-NoExit` nos dois ramos | executor-pesado | `launcher.ps1` | teste novo prova que `-NoProfile` chega no `ArgumentList` do fallback; os 5 testes existentes de fallback passam **sem edição** |
| **AX5** | **Validar argumentos (AXF4, AXF5).** Criar `Test-LaunchTarget -InputFile -ProfileName -Config`. Regras: (1) `ProfileName` vazio → não valida nada (modo wizard, comportamento atual preservado); (2) perfil com `requiresBatchDir` → `-InputFile` obrigatório, `Test-Path -PathType Container`; (3) perfil sem `requiresBatchDir` → `-InputFile` obrigatório, `Test-Path -PathType Leaf`. Devolve `(Resolve-Path).Path`. Chamar no bloco principal **antes** de `Initialize-Environment` — falhar em 200 ms, não depois do pip. **Mudança de comportamento declarada:** `-Profile quality` sozinho hoje abre a UI descartando as flags; passa a ser erro com a mensagem `Perfil 'quality' exige -InputFile <arquivo>. Sem -Profile, o launcher abre o wizard interativo.` Roda **sempre**; `-SkipValidation` segue significando só "pular checagem de binário", como documentado em `:12` | executor-pesado | `launcher.ps1` | `Test-LaunchTarget -ProfileName 'batch' -InputFile <arquivo>` lança mensagem contendo `pasta`; `-ProfileName $null` não lança nem com `-InputFile` vazio |
| **AX6** | **Cache de deps (AXF6).** `Get-RequirementsStamp`: `Get-FileHash -Algorithm SHA256` de `$Config.paths.requirements` **e** de `pyproject.toml` (os dois — `requirements.txt` é só `-e .[opencv]`, o conteúdo real está no pyproject), concatenados. Ler/gravar em `<venv>/.launcher-stamp` (dentro do venv: some junto quando o venv é apagado, e `venv/` já está no `.gitignore:24`). `Test-VenvHealthy`: roda `& $VenvPython -c "import sys"` sob o guard de stderr do § "Armadilha nº 1" e exige exit 0 — pega venv órfão de repo movido (`pyvenv.cfg` com `home` obsoleto), caso em que pular o pip esconderia o problema. `Initialize-Environment` passa a: criar venv se ausente → `Test-VenvHealthy` → se saudável **e** stamp bate **e** não `-Force`: pular `Install-Requirements` **e** `Write-VenvLock`, logando `Dependências já instaladas (stamp confere) — pulando pip. Use -ForceEnvSetup para reinstalar.`; caso contrário instalar, regravar o lock e gravar o stamp **só depois do pip sair com 0**. `-ForceEnvSetup` → `-Force`. **Ordem importa:** gravar o stamp antes do pip terminar deixaria um venv meio-instalado marcado como bom | executor-pesado | `launcher.ps1` | com stamp batendo e venv saudável, `Should -Invoke Install-Requirements -Times 0`; com stamp diferente, `-Times 1`; após `pip` falhar, `.launcher-stamp` não é gravado |
| **AX7** | **Cadastrar `paths.requirements` (AXC4).** `Install-Requirements` passa a receber `-Config` e usar `Join-Path $RepoRoot $Config.paths.requirements` em vez do literal de `:100`. Elimina a config morta e alinha com `Get-RequirementsStamp` do `AX6` | executor-pesado | `launcher.ps1` | `Install-Requirements` não contém mais o literal `"requirements.txt"` |
| **AX8** | **Python do sistema (AXF7).** `Resolve-SystemPython` ganha `-MinVersion` (default `'3.11'`, alimentado por `$Config.minPythonVersion`). Para cada candidato em `@('py','python','python3')`: se `Get-Command` acha, roda `& $src -c "import sys;print('%d.%d'%sys.version_info[:2])"` sob o guard do § "Armadilha nº 1"; ignora o candidato se exit ≠ 0 ou saída vazia; aceita o primeiro com `[version]$v -ge [version]$MinVersion`. **Sem caso especial para `WindowsApps`** — o stub da Store falha a probe sozinho, e um Python de Store legítimo passa; hard-code de caminho reprovaria instalação válida. `throw` final lista os candidatos rejeitados **com a versão medida** e sugere `py -3.13 -m venv venv` | executor-pesado | `launcher.ps1` | com só um Python 3.9 no PATH, lança mensagem contendo `3.11` e a versão medida |
| **AX9** | **Capacidade do FFmpeg (substitui NVENC).** `Test-FfmpegCapabilities -Ffmpeg -Config`: se `validation.requiredEncoders`/`requiredFilters` ausentes ou vazios, **no-op**. Senão roda `& $Ffmpeg -hide_banner -encoders` e `-filters` (guard do § "Armadilha nº 1") e exige cada nome como palavra na saída. `throw` nomeia o que falta e sugere `.\tools\fetch_ffmpeg.ps1`. Chamar de dentro de `Resolve-Binaries`, **depois** das checagens de `Test-Path`, e **não** chamar quando `-SkipValidation`. Justificativa dos defaults: `zscale` aparece 13× e `lut3d` 1× no pipeline, e `zscale` exige `libzimg` — ausente em muitos builds. **Não adicionar nenhum encoder/filtro que não esteja provado por grep no repo** | executor-pesado | `launcher.ps1` | com `requiredFilters: ["naoexiste"]`, `Resolve-Binaries` lança mensagem contendo `naoexiste`; com listas vazias, zero invocações de ffmpeg |
| **AX10** | **Binário validado = binário usado (AXF9 / `QF2`).** (a) `launcher.ps1`: `Build-SetupCommand`/`Build-EncodeCommand` ganham `-Ffmpeg`/`-Ffprobe` (opcionais, default `''`) e, quando não-vazios, prefixam `$env:REELS_FFMPEG=<literal>; $env:REELS_FFPROBE=<literal>; ` na string — **dentro da string, não via `$env:` do processo**, porque `wt.exe` reaproveita processo já existente e o filho herdaria o ambiente do wt antigo, não o nosso. (b) `ui/binaries.py`: `resolve_binary` ganha `env: Mapping[str,str] = os.environ` (injetável, para teste hermético) e passa a consultar `REELS_<NOME>` **antes** de `bin/`, aceitando só se `os.path.isfile`. Ordem final: **env → bin/ → PATH → nome nu**. `available()`/`find_missing_binaries()` propagam `env`. `FFPLAY` continua opcional e o launcher não seta `REELS_FFPLAY` — cai no fluxo antigo | executor-pesado | `launcher.ps1`, `ui/binaries.py` | `resolve_binary("ffmpeg", env={"REELS_FFMPEG": <arquivo real>})` devolve esse caminho mesmo com `bin/ffmpeg.exe` presente; env apontando pra arquivo inexistente é ignorado |
| **AX11** | **Testes.** Ver § "Mudanças na suíte" — é a especificação completa, seguir à risca | executor-pesado | `tests/launcher.Tests.ps1`, `tests/launch-config.Tests.ps1`, `ui/test_binaries.py` | suíte verde nos 3 jobs de CI; contagem de testes **sobe**, nunca desce |
| **AX12** | Registrar `AXF1..AXF11` + `AXC1..AXC5` no `FINDINGS.md` já com a coluna de fechamento apontando para este ciclo, e anexar `## Ciclo AX` ao `STATE.md` | Orquestrador | `.claude/memory/FINDINGS.md`, `.claude/memory/STATE.md` | — |

## Mudanças na suíte (especificação da `AX11`)

### `tests/launcher.Tests.ps1`

**Contrato de dot-source (`:42-72`).** Acrescentar os 10 nomes novos à lista `-ForEach`
(`Protect-PSLiteral`, `Test-LauncherConfig`, `Test-VenvHealthy`, `Get-RequirementsStamp`,
`Read-VenvStamp`, `Write-VenvStamp`, `Test-FfmpegCapabilities`, `Resolve-LauncherShell`,
`Test-LaunchTarget`) — os 14 existentes ficam.

**Único teste que MUDA de asserção** — `Describe 'Build-EncodeCommand'` › `'perfil batch usa
--batch/--output-dir e OMITE o arquivo de entrada'` (`:181-189`):

```powershell
# ANTES                              # DEPOIS (AX2: BatchDir passa a ser protegido)
$cmd | Should -Match '--batch MYCLIPS'      → $cmd | Should -Match "--batch 'MYCLIPS'"
$cmd | Should -Match '--output-dir MYCLIPS' → $cmd | Should -Match "--output-dir 'MYCLIPS'"
```

A terceira asserção do mesmo teste (`Should -Not -Match "'MYCLIPS'"`, que provava que a pasta
não vai como posicional) **deixa de discriminar** depois do quoting. Substituir por uma que
ainda prova a mesma coisa: `$cmd | Should -Not -Match "\.py' 'MYCLIPS'"` — a pasta não aparece
logo depois do script.

O mesmo vale para `Describe 'Build-ProfileArgs'` › `'prefixa --batch/--output-dir quando o
perfil batch recebe -BatchDir'` (`:100-107`): ajustar para o valor protegido.

**Os outros 12 testes de `Build-*Command` passam sem edição** — asseveram `Should -Match` sobre
substrings de flag (`'--performance speed'`, `'--cineon-pipeline on'`) que o prefixo do
`Set-Location` e o export de env não afetam. **Se algum reprovar, é bug do `AX1`/`AX2`, não do
teste: parar e reportar, não relaxar a asserção.**

**`Describe 'Initialize-Environment'` (`:199-280`) — reestruturar em 3 Contexts.** O Context
`'quando o venv ja existe'` hoje tem 5 testes, dos quais dois (`'ainda assim instala as
dependencias (idempotente)'` e `'ainda assim regrava o venv.lock (diagnostico)'`) codificam
exatamente o comportamento que o `AX6` remove. Não apagar: **mover e especializar**.

- `Context 'venv existe, saudavel, stamp confere'` — mocks: `Test-VenvExists`→`$true`,
  `Test-VenvHealthy`→`$true`, `Get-RequirementsStamp`→`'S'`, `Read-VenvStamp`→`'S'`.
  Asserções: `New-ProjectVenv` 0×, **`Install-Requirements` 0×**, **`Write-VenvLock` 0×**,
  retorno casa `python` e `VENV`.
- `Context 'venv existe, saudavel, stamp difere'` — `Read-VenvStamp`→`'OUTRO'`. Asserções:
  `Install-Requirements` 1×, `Write-VenvLock` 1×, `Write-VenvStamp` 1×, e o
  `-ParameterFilter { $VenvPython -match 'python' }` do teste `'passa adiante o mesmo
  interpretador'` (`:239-244`) migra pra cá **intacto**.
- `Context 'venv existe mas nao esta saudavel'` — `Test-VenvHealthy`→`$false`, stamp batendo.
  Asserção: `Install-Requirements` 1× — prova que o stamp **não** sobrepõe a checagem de saúde.
- `Context 'quando o venv nao existe'` (`:247-280`) — acrescentar `Mock Test-VenvHealthy
  { $true }` e `Mock Read-VenvStamp { $null }` aos mocks do `BeforeAll`; as 4 asserções
  existentes seguem válidas.
- `Context 'com -Force'` — stamp batendo + venv saudável + `-Force`: `Install-Requirements` 1×.

**Describes novos** (mínimo de asserções, sem I/O real):

- `Protect-PSLiteral`: string simples; string com `'`; string com espaço; string vazia.
- `Test-LauncherConfig`: config real do repo não lança; `paths` sem `venv` lança nomeando a
  chave; `defaultProfile` fora de `profiles` lança; `flags` vazio lança.
- `Test-LaunchTarget`: perfil `$null` não lança; perfil normal sem `-InputFile` lança citando
  `-InputFile`; perfil `batch` com arquivo lança citando `pasta`; perfil normal com arquivo
  real (`New-TemporaryFile`) devolve caminho absoluto. Limpar o temp em `AfterAll`.
- `Resolve-LauncherShell`: `preferPwsh:false` → `'powershell'` sem consultar o PATH.
- `Open-LauncherTabs`: fallback com `-Shell 'pwsh'` invoca `Start-Process` com `pwsh`;
  fallback com `-NoProfile` no `ArgumentList`; `-WorkingDirectory` chega no `Start-Process`.
- `Build-EncodeCommand` com `-WorkingDirectory`/`-Ffmpeg`/`-Ffprobe`: prefixos presentes,
  na ordem `Set-Location` → `$env:REELS_*` → `&`.

**Superfícies que continuam NÃO cobertas, de propósito** (`Test-FfmpegCapabilities`,
`Test-VenvHealthy` reais, `Resolve-SystemPython` real, ramo `wt.exe` de `Open-LauncherTabs`):
todas invocam `& $variavelComCaminho`, que o Mock do Pester não engancha — é a limitação já
documentada no cabeçalho do arquivo (`:1-16`). **Manter esse comentário e estender a lista**
com os nomes novos. Não refatorar `launcher.ps1` para torná-las mockáveis: fora de escopo.

### `tests/launch-config.Tests.ps1`

- `'define exatamente 5 perfis'` (`:42`) e a lista de `:46` — **inalterados**, o `AX` não
  cria nem remove perfil.
- `'nenhum perfil define --crf'` (`:69-81`) — estender para
  `@('--crf','--maxrate','--bufsize','--preset','--x264-params')`, mesma justificativa da
  Regra de Ouro, mensagem `-Because` citando a skill.
- **Testes novos:** `minPythonVersion` presente e parseável como `[version]`;
  `terminal.preferPwsh` e `terminal.noProfile` booleanos; `validation.requiredEncoders`
  contém `libx264`; `validation.requiredFilters` contém `lut3d` e `zscale`;
  `configVersion` é inteiro ≥ 2.
- **Teste novo de anti-regressão do `AXC1`:** para todo perfil que declara `--enhance off`,
  as flags também declaram `--enhance-ai off`. Trava o aviso amarelo do encoder.
- **Não** assertar valor de `description` (mojibake em WinPS 5.1 — ver `:61-66`).

### `ui/test_binaries.py`

Os 8 testes existentes (`:14-54`) passam `which=` e `proj_dir=` e **não** passam `env=`. Como o
default é `os.environ`, um `REELS_FFMPEG` no ambiente do runner poluiria. Para manter
hermético: nos testes novos passar `env={...}` explícito, e adicionar `env={}` aos 8
existentes. Testes novos: env vence `bin/`; env apontando pra arquivo inexistente é ignorado
(cai em `bin/`); env ausente preserva a ordem antiga; `available()` e `find_missing_binaries()`
enxergam o env.

## Critérios de aceite

1. **Suíte verde nos 3 jobs** — `pester (ubuntu-latest)`, `pester (windows-latest)` (pwsh 7) e
   `Pester (Windows PowerShell 5.1)` (job adicionado no Ciclo AV) — mais os jobs `lint` e
   `tests` (Python). Contagem de testes **maior** que a de hoje.
2. **Nenhuma construção só-pwsh-7** em `launcher.ps1` nem nos testes: `??`, ternário `? :`,
   `&&`/`||`, `ForEach-Object -Parallel`, `ConvertFrom-Json -AsHashtable`, `Get-FileHash
   -InputStream` sobre string. O `grep` do Ciclo AV dava zero — **tem que continuar zero**.
   `Get-FileHash -Path -Algorithm SHA256` existe em 5.1. ✔
3. **`QF1` não volta:** toda invocação nativa nova está dentro do guard
   `$ErrorActionPreference = "Continue"` com `finally` restaurando.
4. **`enhance_maps/` passa a nascer na raiz do repo** — verificação manual do usuário numa
   máquina Windows, com `-Profile balanced` e um clipe real. É a prova do `AXF1` e **não é
   testável em CI**.
5. **Caminho com espaço e com apóstrofo funciona ponta a ponta** — `-Profile batch -InputFile
   "D:\Meus Reels\clips"` e um arquivo com `'` no nome. Também verificação manual.
6. **`-Profile quality` sem `-InputFile` falha com a mensagem nova** em vez de abrir a UI
   descartando as flags.
7. **Segundo lançamento consecutivo não roda pip** e loga a linha do stamp; `-ForceEnvSetup`
   roda. Terceiro lançamento após editar `pyproject.toml` roda pip de novo.
8. **`git diff main --stat` toca exatamente 5 arquivos:** `launcher.ps1`,
   `launch-config.json`, `tests/launcher.Tests.ps1`, `tests/launch-config.Tests.ps1`,
   `ui/binaries.py`, `ui/test_binaries.py`. (Seis com o `test_binaries.py`; nenhum outro.)
   `.claude/memory/*` fica fora do diff de código, em commit próprio.
9. **`Reels_Encoder_v2_FINAL.py`, `cineon_pipeline.py`, `enhance/`, `enhance_visualizer.py`,
   `ebu_meter.py` e os `.cube` NÃO são tocados.** Zero mudança no pipeline de encode.

## O que NÃO fazer

- **Não** adicionar validação de NVENC — decisão registrada no § Contexto.
- **Não** tocar em nada do pipeline de encode. Nenhum parâmetro de FFmpeg, x264, VBV, LUT,
  color, loudness ou VMAF muda neste ciclo. Se um teste do pipeline reprovar, é sinal de que
  o ciclo saiu do escopo — **parar**.
- **Não** fixar `--crf`, `--maxrate`, `--bufsize`, `--preset` ou `--x264-params` em nenhum
  perfil. Regra de Ouro.
- **Não** inventar flag de CLI que não esteja em `build_parser()` (`:4198-4380`).
- **Não** tornar `-WorkingDirectory`, `-Ffmpeg`, `-Ffprobe` ou `-Shell` mandatórios — reprova
  os 15 testes existentes de `Build-*Command` e `Open-LauncherTabs` sem que haja bug.
- **Não** mudar `Read-LauncherConfig` para validar por dentro — quebra os 4 testes de
  `:360-385` sem necessidade.
- **Não** relaxar nem apagar asserção para ficar verde. O único teste com asserção alterada é
  o do perfil `batch`, e a alteração está escrita acima palavra por palavra. Qualquer outra
  reprovação é **achado novo**: registrar no `FINDINGS.md` e parar.
- **Não** refatorar `launcher.ps1` para tornar mockável o ramo `wt.exe` nem as probes nativas.
- **Não** mexer em `.github/workflows/ci.yml`, nos jobs, nem em `tools/*.ps1`.
- **Não** adicionar BOM ao `launch-config.json` nem assertar valor de `description`.
- **Não** criar abstração, camada de plugin, nem "sistema de validadores". São 10 funções
  planas num script plano.

## Notas de execução

- Carregar a skill `instagram-reels-encoder` **antes** de tocar em `launch-config.json`, para
  conferir as Regras de Ouro na fonte. **Não** transcrever a skill para cá nem para o código.
- Este PLAN cita `Reels_Encoder_v2_FINAL.py` só como **referência de leitura** (conferir que
  uma flag existe). O arquivo é read-only neste ciclo.
- Sem `pwsh` no container do Orquestrador: **quem valida em PowerShell é o CI**. Rodar
  `python -m pytest ui/ -v` localmente para a parte `AX10` (essa dá para provar local).
- Commits separados por bloco, nesta ordem: `AX1-AX5` (launcher, sem Python) → `AX6-AX9`
  (launcher, ambiente) → `AX10` (launcher + `ui/binaries.py`) → `AX11` (testes) →
  `AX12` (memória, `[skip ci]`). Bisect fica utilizável.
- **Nunca `git add -A` nem `git add .`** — há arquivos não rastreados no repo
  (`961576A_*.qc.*`, `docs/*.md`, `testResults.xml`, `videos/`, `venv.lock`). Adicionar por
  caminho explícito.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AX` e cabeçalho de tabela.
- Retorno ao Orquestrador: **ponteiro + veredito**, uma linha por ID + SHA. O detalhe vai
  para o `STATE.md`, não para o retorno.
