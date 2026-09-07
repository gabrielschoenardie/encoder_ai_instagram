<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AX: `launcher.ps1` vira bootstrap puro do Instagram Encoder AI

Data: 2026-09-06 | Ciclo: AX | Revisão 2 (correção de arquitetura do usuário, 2026-09-06). Origem: auditoria do Orquestrador sobre `launcher.ps1` + `launch-config.json`. Ciclo anterior: AW. A revisão 1 deste arquivo foi merjada no PR #57 e está **superada por este documento**.

## A correção que muda o eixo do ciclo

Decisão do usuário: **a aba Encode deve somente abrir e executar `Reels_Encoder_v2_FINAL.py`.** O
`launcher.ps1` deixa de montar comandos de encode e passa a ser o que o nome diz — o *start*
correto do Instagram Encoder AI: prepara o ambiente, valida, e entrega o controle ao software.

Isso não é preferência de estilo. O wizard do próprio encoder (`ui/launcher.py:47-53`) já
oferece:

```
PRESETS = ["Encode rápido (FFmpeg)", "Film look (Cineon)", "Batch de pasta",
           "Tools (utilitários)", "Configurar avançado…"]
```

— exatamente os cinco perfis que o `launch-config.json` duplica, e mais: `ask_path` valida o
arquivo na entrada, `settings_preview` mostra as configurações com probe de aspect do source
(`ui/launcher.py:105`), há loop de confirmação, as 5 seções tabuladas (`SECTIONS`,
`ui/launcher.py:45`) e as 4 ferramentas (`TOOLS`, `:55-60`). Os perfis do JSON são **uma segunda
CLI, mais pobre, competindo com a UI real.**

E é dessa duplicação que nascem quatro dos achados da auditoria. Some a duplicação, some o bug:
não há o que consertar em `Build-ProfileArgs` quando `Build-ProfileArgs` deixa de existir.

**Decisões confirmadas pelo usuário em 2026-09-06:**

1. **Remover tudo** — `profiles` e `defaultProfile` saem do JSON; `-InputFile` e `-Profile` saem
   do launcher; `Build-ProfileArgs` é deletada. Quem quiser linha de comando chama o encoder
   direto dentro do venv, que é onde a CLI dele já vive (`build_parser()`, `:4198-4380`).
2. **Manter as duas abas** — aba 1 roda `--hardware-info` como diagnóstico paralelo; aba 2 é o
   encoder.

**NVENC continua fora do gate** (decisão da revisão 1, inalterada): `grep -il nvenc` sobre todo
`.py` do repo retorna zero arquivos — o pipeline é libx264 puro. No lugar entra validação de
capacidade real do FFmpeg (`libx264`, `lut3d`, `zscale`); `zscale` aparece 13× em
`Reels_Encoder_v2_FINAL.py` + `cineon_pipeline.py` e exige `libzimg`, ausente em muitos builds.

## Diagnóstico — o que sobra dos 16 achados

Medidos por leitura em 2026-09-06 (não há `pwsh` no container do Orquestrador; toda âncora
`arquivo:linha` é conferível). A coluna **destino** diz se o achado vira código ou evapora com
a remoção dos perfis.

### Resolvidos por remoção — nenhuma linha de correção é escrita

| ID | âncora | defeito | por que evapora |
|----|--------|---------|-----------------|
| AXF2 | `launcher.ps1:213` | `--batch <pasta>` injetado sem aspas: qualquer pasta com espaço (`D:\Meus Reels\clipes`) vira dois argumentos e o encoder morre em `Reels_Encoder_v2_FINAL.py:4463` | o launcher não monta mais `--batch`; o wizard recebe a pasta por `ask_path` |
| AXF4 | `launcher.ps1:237-249` + `:4440,4446` | `-Profile X` sem `-InputFile` monta comando sem posicional; o encoder abre a UI e faz `args = launched`, descartando as flags do perfil em silêncio | não há mais `-Profile` a descartar |
| AXF5 | ausência | `-InputFile` nunca passa por `Test-Path`; `batch` não checa `-PathType Container` | não há mais `-InputFile`; `ask_path` valida |
| AXF10 | `launcher.ps1:10` | `[string]$Profile` sombreia a variável automática `$PROFILE` | o parâmetro deixa de existir |
| AXC1 | `launch-config.json:6` | `fast` declara `--enhance off` mas herda `--enhance-ai on`/`--mctf on` → aviso amarelo em todo preview | o perfil deixa de existir |
| AXC2 | `launch-config.json:14` | `quality` herda `--enhance-ai on`/`--mctf on` implicitamente | idem |
| AXC3 | `launch-config.json:18` | `cinematic` herda `--performance balanced` num pipeline PyAV de 5-15 fps | idem |

### Viram código

| ID | sev | âncora | defeito |
|----|-----|--------|---------|
| AXF1 | **S1** | `launcher.ps1:252-268` | `Open-LauncherTabs` abre `wt`/`Start-Process` **sem** diretório de trabalho. `Reels_Encoder_v2_FINAL.py:4058` e `enhance_visualizer.py:36,155,276,408` escrevem `enhance_maps` como caminho relativo → máscaras MCTF e mapas de preflight caem no CWD da aba. **Fica mais crítico com a nova arquitetura**, porque agora a aba hospeda a sessão interativa inteira |
| AXF3 | **S3** | `launcher.ps1:225,244` | caminhos interpolados em aspas simples sem escapar. Superfície reduzida (só caminhos do repo), mas real: um repo em `C:\Users\Gabriel's PC\encoder` quebra o comando das duas abas |
| AXF6 | **S3** | `launcher.ps1:148,119-134` | `Install-Requirements` roda em todo lançamento; `Write-VenvLock` roda `pip freeze` cujo arquivo ninguém lê. O `throw` em `:114` derruba o launch se a rede cair, com o venv já correto |
| AXF7 | **S3** | `launcher.ps1:66-72` | `Resolve-SystemPython` devolve o primeiro `py`/`python` do PATH sem checar versão; `pyproject.toml:10` exige `>=3.11` |
| AXF8 | **S4** | `launcher.ps1:48-59` | `launch-config.json` é parseado, nunca validado. Sem `paths.venv`, o `Join-Path` de `:280` estoura com erro de binding |
| AXF9 | **S4** | `launcher.ps1:174-180` vs `ui/binaries.py:37-52` | binário validado (`bin/ffmpeg.exe`) não é o binário usado: o filho resolve sozinho. É o `QF2` do `FINDINGS.md` ainda vivo |
| AXF11 | **S4** | `launcher.ps1:261,265,266` | `powershell` hardcoded (nunca pwsh 7) e sem `-NoProfile` |
| AXC4 | **S4** | `launcher.ps1:100` | `paths.requirements` é configuração morta — `Install-Requirements` hardcoda o literal |
| AXD1 | **S4** | `README.md:101-102` | o README documenta `.\launcher.ps1 -InputFile "video.mp4" -Profile "cinematic"`, que deixa de existir |

### Verificado e descartado — não vira tarefa

Com a UI interativa passando a ser o conteúdo da aba, checei se o console precisava de setup de
UTF-8 (acentos + box-drawing do banner Rich em Windows PowerShell 5.1). **Não precisa:**
`ui/theme.py:143` chama `_ensure_utf8_streams()` em `get_console()`, e `:113` degrada a tabela
de glifos para ASCII quando o encoding não aguenta. Python usa a API Unicode do console para um
tty real, então a codepage não interfere. **Não adicionar `chcp` nem `[Console]::OutputEncoding`
ao comando das abas** — seria ruído sobre um problema que não existe.

## Desenho

### O contrato novo do launcher

```
launcher.ps1                       (sem -InputFile, sem -Profile)
  ├─ Read-LauncherConfig          → Test-LauncherConfig          [AX5]
  ├─ Resolve-SystemPython -MinVersion                            [AX9]
  ├─ Initialize-Environment       → venv + stamp de dependências [AX7]
  ├─ Resolve-Binaries             → Test-FfmpegCapabilities      [AX10]
  ├─ Build-HardwareCommand / Build-AppCommand                    [AX1·2·3·11]
  └─ Open-LauncherTabs            → aba Hardware | aba Encode    [AX6]
```

O comando da aba Encode, na íntegra e sem mais nada:

```powershell
Set-Location '<root>'; $env:REELS_FFMPEG='<root>\bin\ffmpeg.exe'; $env:REELS_FFPROBE='<root>\bin\ffprobe.exe'; & '<root>\venv\Scripts\python.exe' '<root>\Reels_Encoder_v2_FINAL.py' --ui
```

**Sobre o `--ui`.** Sem argumento nenhum o encoder já cai na UI (`:4440`,
`args.input is None and args.batch is None`), então o `--ui` não muda o caminho feliz. Ele muda
o **caminho de erro**: com `--ui` explícito, um pacote `ui` ausente dá
`pacote 'ui' indisponível (instale 'pydantic>=2')` (`:4451-4457`); sem ele, cai no erro genérico
de input obrigatório, que não diz o que fazer. É a única flag que o launcher passa, e ela existe
para produzir a mensagem certa. Se o usuário preferir a invocação nua, é remover uma palavra.

### Parâmetros do script depois do ciclo

```powershell
param(
    [switch]$Debug,
    [switch]$SkipValidation,
    [switch]$SkipEnvSetup,
    [switch]$ForceEnvSetup      # AX7: escape hatch do cache de dependências
)
```

`-ForceEnvSetup` e `-SkipEnvSetup` são mutuamente exclusivos → `throw` claro se ambos.

### Funções

**Deletadas:** `Build-ProfileArgs`, `Build-EncodeCommand`.

**Novas:**

```
Protect-PSLiteral       -Value <string>          → string entre aspas simples, com '' escapado
Test-LauncherConfig     -Config                  → throw nomeando a chave, ou $null
Test-VenvHealthy        -VenvPython              → bool
Get-RequirementsStamp   -RepoRoot -Config        → string (SHA256 concatenado)
Read-VenvStamp          -VenvPath                → string ou $null
Write-VenvStamp         -VenvPath -Stamp         → void
Test-FfmpegCapabilities -Ffmpeg -Config          → throw nomeando o que falta, ou $null
Resolve-LauncherShell   -Config                  → 'pwsh' | 'powershell'
Build-AppCommand        -VenvPython -RepoRoot -Config [-WorkingDirectory] [-Ffmpeg] [-Ffprobe]
```

**Alteradas:** `Resolve-SystemPython` ganha `-MinVersion`; `Initialize-Environment` ganha
`-Force`; `Build-SetupCommand` ganha `-WorkingDirectory`/`-Ffmpeg`/`-Ffprobe`;
`Open-LauncherTabs` ganha `-WorkingDirectory`/`-Shell`.

> **Compatibilidade obrigatória:** `-WorkingDirectory`, `-Ffmpeg`, `-Ffprobe` e `-Shell` são
> **opcionais com default**, nunca `[Parameter(Mandatory)]`. Os 5 testes de
> `Describe 'Open-LauncherTabs — fallback…'` (`tests/launcher.Tests.ps1:430-476`) e os 4 de
> `Build-SetupCommand` (`:117-142`) chamam essas funções sem os parâmetros novos; torná-los
> mandatórios reprova a suíte sem que haja bug. Defaults: `-Shell` = `'powershell'`, os demais
> `''` (comportamento antigo). O bloco principal sempre passa todos.

### Armadilha do ciclo — `QF1` (regressão de stderr nativo)

O ciclo adiciona três invocações nativas novas: probe de versão do Python (`AX9`), capacidades do
FFmpeg (`AX10`) e sanidade do venv (`AX7`). Em pwsh 7.3+ com `$ErrorActionPreference = "Stop"`,
stderr de comando nativo vira `NativeCommandError` terminante — foi o `QF1` do Ciclo Q
(`FINDINGS.md:187`). **Toda** invocação nativa nova DEVE usar o padrão de `New-ProjectVenv:81-88`:

```powershell
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try   { $out = & $exe @args 2>&1 }
finally { $ErrorActionPreference = $prevEap }
```

O `$PSNativeCommandUseErrorActionPreference = $false` do topo não basta: é escopo de script, e o
`launcher.ps1` é dot-sourced pelos testes, onde o escopo é o do chamador.

### `launch-config.json` alvo

```json
{
  "configVersion": 2,
  "minPythonVersion": "3.11",
  "terminal": {
    "preferPwsh": true,
    "noProfile": true
  },
  "validation": {
    "requiredEncoders": ["libx264"],
    "requiredFilters": ["lut3d", "zscale"]
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

`profiles` e `defaultProfile` **saem inteiros**. O arquivo cai de 34 para ~20 linhas e passa a
descrever só ambiente — nenhuma decisão de encode. Toda decisão de encode passa a viver num
lugar só: o wizard e a análise adaptativa do encoder.

Restrições, não negociáveis:

- **Nenhum parâmetro de encode volta ao JSON.** Nem perfil, nem flag, nem `--crf`, `--maxrate`,
  `--bufsize`, `--preset`, `--x264-params`. Regra de Ouro (skill `instagram-reels-encoder`
  § "Regras de Ouro — Nunca Violar"): rate control é derivado da análise adaptativa, nunca
  fixado. Com os perfis removidos isso passa a ser estrutural, não uma convenção a fiscalizar —
  e a Task `AX12` troca o guarda de teste antigo por um que assere a **ausência** da chave.
- O arquivo é **UTF-8 sem BOM**. Não adicionar BOM.

## Tarefas

Ordem obrigatória. `AX1`-`AX6` não tocam Python; `AX7`-`AX11` tocam; `AX12` fecha testes;
`AX13` fecha memória e docs.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| **AX1** | **Working dir (AXF1).** `-WorkingDirectory` (opcional, default `''`) em `Build-SetupCommand`, `Build-AppCommand` e `Open-LauncherTabs`. Quando não-vazio: as duas `Build-*` prefixam `Set-Location <literal protegido>; ` na string; `Open-LauncherTabs` passa `--startingDirectory <path>` em **cada** `new-tab` do ramo wt e `-WorkingDirectory <path>` em **cada** `Start-Process` do fallback. Bloco principal passa `$Script:RepoRoot`. Cinto **e** suspensório de propósito: `wt` reaproveita processo existente e pode ignorar o CWD do chamador; o `Set-Location` na string é o que garante — e é o que dá para assertar em Pester | executor-pesado | `launcher.ps1` | `Build-AppCommand -WorkingDirectory 'ROOT'` devolve string começando em `Set-Location 'ROOT'; ` |
| **AX2** | **Quoting central (AXF3).** Criar `Protect-PSLiteral` (dobra `'`, envolve em aspas simples, `[AllowEmptyString()]`). Passar por ele todo caminho que entra em string de comando: `$VenvPython`, `$script`, `$WorkingDirectory`, `$Ffmpeg`, `$Ffprobe`. Nenhum caminho continua interpolado à mão | executor-pesado | `launcher.ps1` | `Protect-PSLiteral "Gabriel's"` → `'Gabriel''s'`; nenhum `"'$" ` sobra no arquivo |
| **AX3** | **Handoff (a correção do ciclo).** (a) Deletar `Build-ProfileArgs` e `Build-EncodeCommand`. (b) Criar `Build-AppCommand` que monta **apenas** `& '<venvPython>' '<encoderScript>' --ui`, mais os prefixos de `AX1`/`AX11`. Sem perfil, sem input, sem `--batch`, sem ramo condicional. (c) Remover `-InputFile` e `-Profile` do `param()`, e as variáveis `$wantsDirectRun`/`$effectiveProfile` do bloco principal (`:275-278`). (d) A aba 2 passa a chamar `Build-AppCommand`; a aba 1 segue em `Build-SetupCommand` (`--hardware-info`), inalterada em intenção | executor-pesado | `launcher.ps1` | `Select-String -Pattern 'Profile|InputFile|--batch|requiresBatchDir' launcher.ps1` não retorna nada; `Build-AppCommand` termina em `--ui` |
| **AX4** | **Config sem encode.** Reescrever `launch-config.json` conforme o § Desenho: remover `profiles` e `defaultProfile`, adicionar `configVersion`, `minPythonVersion`, `terminal`, `validation`. Manter os 6 `paths` com os mesmos valores | executor-pesado | `launch-config.json` | JSON válido, sem as chaves `profiles`/`defaultProfile`, UTF-8 sem BOM |
| **AX5** | **Validar config (AXF8).** `Test-LauncherConfig`: exige `paths` com as 6 chaves presentes e strings não-vazias; `minPythonVersion` parseável como `[version]`; `terminal` e `validation`, quando presentes, com os tipos certos. Mensagem de erro **nomeia a chave**. Chamar no bloco principal logo após `Read-LauncherConfig`. **Não** mesclar dentro de `Read-LauncherConfig` — os 4 testes de `Describe 'Read-LauncherConfig'` (`:360-385`) exercitam parse isolado e devem passar sem edição | executor-pesado | `launcher.ps1` | `paths.venv` ausente → mensagem contendo `paths.venv`; os 4 testes de `Read-LauncherConfig` passam sem edição |
| **AX6** | **Shell (AXF11).** `Resolve-LauncherShell -Config`: `'pwsh'` se `terminal.preferPwsh` ≠ `false` **e** `Get-Command pwsh` acha; senão `'powershell'`. `Open-LauncherTabs` ganha `-Shell` (opcional, default `'powershell'`) e usa no lugar do literal em `:261,265,266`. Quando `terminal.noProfile` ≠ `false`, incluir `-NoProfile` **antes** de `-NoExit` nos dois ramos. `-NoExit` permanece nos dois: a aba Encode agora hospeda uma sessão interativa e não pode fechar quando o wizard retorna | executor-pesado | `launcher.ps1` | teste novo prova `-NoProfile` no `ArgumentList` do fallback; os 5 testes existentes de fallback passam **sem edição** |
| **AX7** | **Cache de deps (AXF6).** `Get-RequirementsStamp`: `Get-FileHash -Algorithm SHA256` de `$Config.paths.requirements` **e** de `pyproject.toml` (os dois — `requirements.txt` é só `-e .[opencv]`, o conteúdo real vive no pyproject), concatenados. Ler/gravar em `<venv>/.launcher-stamp` (dentro do venv: some com ele, e `venv/` já está no `.gitignore:24`). `Test-VenvHealthy`: `& $VenvPython -c "import sys"` sob o guard de stderr do § Armadilha, exigindo exit 0 — pega venv órfão de repo movido (`pyvenv.cfg` com `home` obsoleto), caso em que pular o pip esconderia o problema. `Initialize-Environment`: cria venv se ausente → `Test-VenvHealthy` → se saudável **e** stamp bate **e** não `-Force`: pular `Install-Requirements` **e** `Write-VenvLock`, logando `Dependências já instaladas (stamp confere) — pulando pip. Use -ForceEnvSetup para reinstalar.`; senão instalar, regravar lock e gravar o stamp **só depois do pip sair com 0**. `-ForceEnvSetup` → `-Force`. **Ordem importa:** gravar o stamp antes do pip terminar marcaria um venv meio-instalado como bom | executor-pesado | `launcher.ps1` | stamp batendo + venv saudável → `Install-Requirements` 0×; stamp diferente → 1×; pip falhando → `.launcher-stamp` não gravado |
| **AX8** | **Cadastrar `paths.requirements` (AXC4).** `Install-Requirements` recebe `-Config` e usa `Join-Path $RepoRoot $Config.paths.requirements` em vez do literal de `:100` | executor-pesado | `launcher.ps1` | o literal `"requirements.txt"` não aparece mais em `Install-Requirements` |
| **AX9** | **Python do sistema (AXF7).** `Resolve-SystemPython` ganha `-MinVersion` (default `'3.11'`, alimentado por `$Config.minPythonVersion`). Para cada candidato em `@('py','python','python3')` que `Get-Command` ache: rodar `& $src -c "import sys;print('%d.%d'%sys.version_info[:2])"` sob o guard do § Armadilha; ignorar se exit ≠ 0 ou saída vazia; aceitar o primeiro com `[version]$v -ge [version]$MinVersion`. **Sem caso especial para `WindowsApps`** — o stub da Store falha a probe sozinho, e um Python de Store legítimo passa; hard-code de caminho reprovaria instalação válida. `throw` final lista os rejeitados **com a versão medida** e sugere `py -3.13 -m venv venv` | executor-pesado | `launcher.ps1` | só um Python 3.9 no PATH → mensagem contendo `3.11` e a versão medida |
| **AX10** | **Capacidade do FFmpeg.** `Test-FfmpegCapabilities -Ffmpeg -Config`: se `validation.requiredEncoders`/`requiredFilters` ausentes ou vazios, **no-op**. Senão rodar `& $Ffmpeg -hide_banner -encoders` e `-filters` (guard do § Armadilha) e exigir cada nome como palavra na saída. `throw` nomeia o que falta e sugere `.\tools\fetch_ffmpeg.ps1`. Chamar de dentro de `Resolve-Binaries`, **depois** dos `Test-Path`, e **não** chamar sob `-SkipValidation`. **Não adicionar encoder/filtro que não esteja provado por grep no repo** | executor-pesado | `launcher.ps1` | `requiredFilters: ["naoexiste"]` → `Resolve-Binaries` lança citando `naoexiste`; listas vazias → zero invocações de ffmpeg |
| **AX11** | **Binário validado = binário usado (AXF9 / `QF2`).** (a) `Build-SetupCommand`/`Build-AppCommand` ganham `-Ffmpeg`/`-Ffprobe` (opcionais, default `''`) e, quando não-vazios, prefixam `$env:REELS_FFMPEG=<literal>; $env:REELS_FFPROBE=<literal>; ` **dentro da string** — não via `$env:` do processo, porque `wt.exe` reaproveita processo existente e o filho herdaria o ambiente do wt antigo. (b) `ui/binaries.py`: `resolve_binary` ganha `env: Mapping[str,str] = os.environ` (injetável, para teste hermético) e consulta `REELS_<NOME>` **antes** de `bin/`, aceitando só se `os.path.isfile`. Ordem final: **env → bin/ → PATH → nome nu**. `available()`/`find_missing_binaries()` propagam `env`. `FFPLAY` segue opcional e o launcher não seta `REELS_FFPLAY` | executor-pesado | `launcher.ps1`, `ui/binaries.py` | `resolve_binary("ffmpeg", env={"REELS_FFMPEG": <arquivo real>})` devolve esse caminho mesmo com `bin/ffmpeg.exe` presente; env apontando para arquivo inexistente é ignorado |
| **AX12** | **Testes.** Ver § "Mudanças na suíte" — especificação completa, seguir à risca | executor-pesado | `tests/launcher.Tests.ps1`, `tests/launch-config.Tests.ps1`, `ui/test_binaries.py` | suíte verde nos 3 jobs Pester + `tests`/`lint` |
| **AX13** | **Docs (AXD1).** No `README.md`: remover a linha 102 (`-InputFile`/`-Profile`) e ajustar as linhas 87-114 para descrever o launcher como bootstrap que abre o wizard. `MANUAL_INSTALACAO.txt:311-318` já mostra só `.\launcher.ps1` — **não tocar**. Depois, registrar `AXF1..AXF11`, `AXC1..AXC4` e `AXD1` no `FINDINGS.md` com a coluna de fechamento (marcando os 7 "resolvidos por remoção") e anexar `## Ciclo AX` ao `STATE.md` | executor-pesado (README) + Orquestrador (memória) | `README.md`, `.claude/memory/FINDINGS.md`, `.claude/memory/STATE.md` | `grep -n '\-Profile' README.md` não retorna nada |

## Mudanças na suíte (especificação da `AX12`)

### `tests/launcher.Tests.ps1` — 476 linhas hoje

**Deletar inteiros** (as funções que testam deixam de existir):

- `Describe 'Build-ProfileArgs'` (`:73-116`) — 5 testes.
- `Describe 'Build-EncodeCommand'` (`:143-198`) — 6 testes.

Isso derruba 11 testes. **É a única redução de contagem autorizada no ciclo**, e é honesta:
código deletado não fica sem cobertura, fica sem existir. A contagem final tem que subir mesmo
assim, pelos Describes novos abaixo.

**Contrato de dot-source (`:42-72`).** Remover `Build-ProfileArgs` e `Build-EncodeCommand` da
lista `-ForEach`; acrescentar os 9 nomes novos (`Protect-PSLiteral`, `Test-LauncherConfig`,
`Test-VenvHealthy`, `Get-RequirementsStamp`, `Read-VenvStamp`, `Write-VenvStamp`,
`Test-FfmpegCapabilities`, `Resolve-LauncherShell`, `Build-AppCommand`).

**Duas asserções sobre o config real, órfãs da `AX4` (achado da execução da `AX5`, sem tarefa
própria até esta revisão — fechar aqui).** `It 'carrega o launch-config.json real do
repositorio'` dentro de `Describe 'Contrato de dot-source'` (`:64-66`) faz
`$script:Config.defaultProfile | Should -Be 'balanced'`; a homônima dentro de `Describe
'Read-LauncherConfig'` (`:379-383`) faz o mesmo mais `@($real.profiles.PSObject.Properties.Name).Count
| Should -Be 5`. As duas leem o `launch-config.json` real do repo, e as duas chaves saíram no
`AX4`. Substituir pelo schema novo, sem citar `profiles`/`defaultProfile`:
`:64-66` → `$script:Config.configVersion | Should -Be 2`;
`:379-383` → `$real.configVersion | Should -Be 2` mais
`@($real.paths.PSObject.Properties.Name).Count | Should -Be 6`. Não contam para os "16 testes
que saem" do critério de aceite 2 — são asserção trocada, não teste deletado.

**`Describe 'Build-SetupCommand'` (`:117-142`) — 4 testes passam sem edição.** Asseveram
`Should -Match` sobre `--hardware-info`, o nome do script e o interpretador; nem o prefixo do
`Set-Location` nem o export de env afetam. **Se algum reprovar, é bug do `AX1`/`AX2`/`AX11`,
não do teste: parar e reportar, não relaxar a asserção.**

**`Describe 'Resolve-Binaries'` (`:281-358`) — os 9 testes ganham 1 mock a mais nos dois
`BeforeAll`, sem tocar asserção nenhuma (achado da execução da `AX10`, sem tarefa própria até
esta revisão — fechar aqui).** A `AX10` faz `Resolve-Binaries` chamar `Test-FfmpegCapabilities`
de verdade; os dois Contexts (`'todos os binarios presentes'` `:285-295` e `'Windows Terminal
ausente'` `:330-334`) passam `$script:Config` real (com `validation.requiredEncoders`/
`requiredFilters`) e um `-RepoRoot 'ROOT'` fictício, então a chamada tenta rodar
`'ROOT\bin\ffmpeg.exe' -encoders` e os 9 testes reprovam com `CommandNotFoundException`.
Acrescentar `Mock Test-FfmpegCapabilities { }` a cada um dos dois `BeforeAll` (junto de
`Mock Test-RequiredBinary`/`Mock Test-Path`/`Mock Write-LauncherLog`, mesmo bloco). Nenhuma
`It` muda.

**`Describe 'Initialize-Environment'` (`:199-280`) — reestruturar em 5 Contexts.** O Context
`'quando o venv ja existe'` tem hoje 5 testes, dois dos quais (`'ainda assim instala as
dependencias (idempotente)'`, `:221`, e `'ainda assim regrava o venv.lock (diagnostico)'`,
`:226`) codificam exatamente o comportamento que o `AX7` remove. Não apagar: **mover e
especializar**.

- `Context 'venv existe, saudavel, stamp confere'` — mocks `Test-VenvExists`→`$true`,
  `Test-VenvHealthy`→`$true`, `Get-RequirementsStamp`→`'S'`, `Read-VenvStamp`→`'S'`.
  Asserções: `New-ProjectVenv` 0×, **`Install-Requirements` 0×**, **`Write-VenvLock` 0×**,
  retorno casa `python` e `VENV`.
- `Context 'venv existe, saudavel, stamp difere'` — `Read-VenvStamp`→`'OUTRO'`.
  `Install-Requirements` 1×, `Write-VenvLock` 1×, `Write-VenvStamp` 1×; o
  `-ParameterFilter { $VenvPython -match 'python' }` do teste `:239` migra para cá **intacto**.
- `Context 'venv existe mas nao esta saudavel'` — `Test-VenvHealthy`→`$false`, stamp batendo.
  `Install-Requirements` 1× — prova que o stamp não sobrepõe a checagem de saúde.
- `Context 'quando o venv nao existe'` (`:247-280`) — acrescentar `Mock Test-VenvHealthy
  { $true }` e `Mock Read-VenvStamp { $null }` ao `BeforeAll`; as 4 asserções seguem válidas.
- `Context 'com -Force'` — stamp batendo + saudável + `-Force` → `Install-Requirements` 1×.

**Describes novos:**

- `Build-AppCommand`: termina em `--ui`; **não** contém `--performance`, `--batch`, `--mode`
  nem nome de perfil nenhum; com `-WorkingDirectory` começa em `Set-Location`; com
  `-Ffmpeg`/`-Ffprobe` traz os dois `$env:REELS_*` na ordem `Set-Location` → `$env:` → `&`.
- `Protect-PSLiteral`: string simples; com `'`; com espaço; vazia.
- `Test-LauncherConfig`: config real do repo não lança; `paths` sem `venv` lança nomeando a
  chave; `minPythonVersion` não-parseável lança.
- `Resolve-LauncherShell`: `preferPwsh:false` → `'powershell'` sem consultar o PATH.
- `Open-LauncherTabs`: fallback com `-Shell 'pwsh'` invoca `Start-Process` com `pwsh`;
  `-NoProfile` chega no `ArgumentList`; `-WorkingDirectory` chega no `Start-Process`.

**Superfícies que continuam NÃO cobertas, de propósito** (`Test-FfmpegCapabilities`,
`Test-VenvHealthy` real, `Resolve-SystemPython` real, ramo `wt.exe` de `Open-LauncherTabs`):
todas invocam `& $variavelComCaminho`, que o Mock do Pester não engancha — limitação já
documentada no cabeçalho do arquivo (`:1-16`). **Manter esse comentário e estender a lista.**
Não refatorar `launcher.ps1` para torná-las mockáveis: fora de escopo.

### `tests/launch-config.Tests.ps1` — 121 linhas hoje

**Deletar** `Describe 'launch-config.json — perfis'` (`:35-94`) inteiro — 5 testes, incluindo
`'nenhum perfil define --crf'` (`:69-81`).

**Substituir o guarda do `--crf` por um mais forte**, em `Describe 'launch-config.json —
estrutura'`: o JSON **não contém** as chaves `profiles` nem `defaultProfile`, e o texto cru do
arquivo não casa `--crf|--maxrate|--bufsize|--preset|--x264-params|--performance|--mode`.
Antes o teste garantia que nenhum perfil fixava rate control; agora garante que **não há onde
fixar**. `-Because` citando a skill `instagram-reels-encoder` § Regras de Ouro.

Ajustar `'declara as tres chaves de topo'` (`:27`) para as chaves novas. Manter os dois testes
de `paths` (`:96-120`) intactos. **Testes novos:** `minPythonVersion` parseável como
`[version]`; `terminal.preferPwsh`/`noProfile` booleanos; `validation.requiredEncoders` contém
`libx264`; `validation.requiredFilters` contém `lut3d` e `zscale`; `configVersion` inteiro ≥ 2.

**Não** assertar valor de `description` em lugar nenhum — o arquivo é UTF-8 sem BOM e WinPS 5.1
o lê como ANSI, entregando mojibake (razão documentada em `:61-66`, que sai junto com o bloco).

### `ui/test_binaries.py` — 54 linhas hoje

Os 8 testes existentes (`:14-54`) passam `which=`/`proj_dir=` mas não `env=`; como o default é
`os.environ`, um `REELS_FFMPEG` no ambiente do runner poluiria. Para manter hermético: passar
`env={}` nos 8 existentes e `env={...}` explícito nos novos. Testes novos: env vence `bin/`; env
apontando para arquivo inexistente é ignorado (cai em `bin/`); env ausente preserva a ordem
antiga; `available()` e `find_missing_binaries()` enxergam o env.

## Critérios de aceite

1. **Suíte verde nos 3 jobs Pester** — `pester (ubuntu-latest)`, `pester (windows-latest)`
   (pwsh 7) e `Pester (Windows PowerShell 5.1)` — mais `lint` e `tests`.
2. **Contagem líquida sobe.** Saem 16 testes (11 de perfil no launcher + 5 no config); os
   Describes novos têm que mais que compensar.
3. **Nenhuma construção só-pwsh-7** em `launcher.ps1` nem nos testes: `??`, ternário `? :`,
   `&&`/`||`, `ForEach-Object -Parallel`, `ConvertFrom-Json -AsHashtable`. O grep do Ciclo AV
   dava zero — tem que continuar zero. `Get-FileHash -Path -Algorithm SHA256` existe em 5.1. ✔
4. **`QF1` não volta:** toda invocação nativa nova dentro do guard com `finally`.
5. **A aba Encode abre o wizard e nada mais** — verificação manual do usuário no Windows:
   duplo-clique no launcher, aba 2 mostra o banner `REELS ENCODER · Premiere Workspace` e o
   menu de 5 fluxos, sem nenhuma flag de encode ter sido pré-decidida pelo launcher.
6. **`enhance_maps/` nasce na raiz do repo**, não na home. Verificação manual, não testável em CI.
7. **Repo em caminho com apóstrofo funciona** (`C:\Users\Gabriel's PC\encoder`). Manual.
8. **Segundo lançamento não roda pip** e loga a linha do stamp; `-ForceEnvSetup` roda; após
   editar `pyproject.toml`, roda de novo.
9. **`git diff main --stat` toca exatamente 7 arquivos:** `launcher.ps1`, `launch-config.json`,
   `tests/launcher.Tests.ps1`, `tests/launch-config.Tests.ps1`, `ui/binaries.py`,
   `ui/test_binaries.py`, `README.md`. `.claude/memory/*` em commit próprio.
10. **`Reels_Encoder_v2_FINAL.py`, `cineon_pipeline.py`, `enhance/`, `enhance_visualizer.py`,
    `ebu_meter.py`, `ui/launcher.py` e os `.cube` NÃO são tocados.** Zero mudança no pipeline de
    encode e zero mudança no wizard — o ciclo só muda quem o chama.

## O que NÃO fazer

- **Não** deixar resto de perfil: nem `Build-ProfileArgs` "por compatibilidade", nem
  `-Profile` como alias morto, nem a chave `profiles` vazia no JSON. A remoção é o ponto.
- **Não** fazer o launcher passar qualquer flag de encode ao encoder. `--ui` é a única flag, e
  existe pela mensagem de erro (§ Desenho). Nada de `--performance`, `--mode`, `--enhance`.
- **Não** mexer em `ui/launcher.py`, `ui/config.py` nem em nada do wizard. Ele já faz o
  trabalho; o ciclo só corrige quem o inicia.
- **Não** tocar no pipeline de encode. Nenhum parâmetro de FFmpeg, x264, VBV, LUT, color,
  loudness ou VMAF muda. Se um teste do pipeline reprovar, o ciclo saiu do escopo — **parar**.
- **Não** adicionar `chcp` ou `[Console]::OutputEncoding` ao comando das abas — verificado como
  desnecessário (§ "Verificado e descartado").
- **Não** adicionar validação de NVENC.
- **Não** tornar `-WorkingDirectory`, `-Ffmpeg`, `-Ffprobe` ou `-Shell` mandatórios.
- **Não** mudar `Read-LauncherConfig` para validar por dentro — quebra os 4 testes de `:360-385`
  sem necessidade.
- **Não** relaxar nem apagar asserção para ficar verde. As únicas remoções autorizadas são os
  dois Describes de perfil e o bloco de perfis do config, listados na `AX12`. Qualquer outra
  reprovação é **achado novo**: registrar no `FINDINGS.md` e parar.
- **Não** refatorar `launcher.ps1` para tornar mockável o ramo `wt.exe` nem as probes nativas.
- **Não** mexer em `.github/workflows/ci.yml`, nos jobs, nem em `tools/*.ps1`.
- **Não** criar abstração nem "sistema de validadores". São 9 funções planas num script plano.

## Notas de execução

- Carregar a skill `instagram-reels-encoder` antes de tocar em `launch-config.json`, para
  conferir as Regras de Ouro na fonte. **Não** transcrever a skill para cá nem para o código.
- `Reels_Encoder_v2_FINAL.py` e `ui/launcher.py` são **referência de leitura** neste ciclo
  (conferir que `--ui` existe, que os PRESETS cobrem os perfis). Read-only.
- Sem `pwsh` no container do Orquestrador: **quem valida PowerShell é o CI**. Rodar
  `python -m pytest ui/ -v` localmente para a parte `AX11`.
- **A branch `claude/launcher-encoder-architecture-jzyyu8` já teve o PR #57 merjado.** Recriar a
  partir do `main` atual (`git fetch origin main && git checkout -B <branch> origin/main`) antes
  do primeiro commit; o trabalho vai num PR **novo**, nunca empilhado sobre a história merjada.
- Commits por bloco, nesta ordem: `AX1-AX6` (launcher + config, sem Python) → `AX7-AX10`
  (ambiente) → `AX11` (launcher + `ui/binaries.py`) → `AX12` (testes) → `AX13` (docs + memória,
  `[skip ci]` só no commit de memória). Bisect fica utilizável.
- **Nunca `git add -A` nem `git add .`** — há arquivos não rastreados (`961576A_*.qc.*`,
  `docs/*.md`, `testResults.xml`, `videos/`, `venv.lock`). Adicionar por caminho explícito.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AX` e cabeçalho de tabela.
- Retorno ao Orquestrador: **ponteiro + veredito**, uma linha por ID + SHA.
