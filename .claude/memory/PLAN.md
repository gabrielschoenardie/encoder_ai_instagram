<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo L2: Launcher (R-08, R-09, R-17, R-18, R-19, R-20 + UF1)

Data: 2026-11-17 | Branch: `chore/l2-launcher-hardening` (base `3c16e56` = `origin/main`). Agente alvo: **`executor-pesado`**.

Decisão do usuário: o launcher é o "START" do encoder — **automático, sem nenhum prompt interativo** (nada de `Read-Host`, `-Yes`, `-AutoInstall`). Downloads automáticos continuam por padrão, mas deixam de ser silenciosos (log antes) e respeitam `-NoDownload` / `-SkipValidation`.

## Regras

- **Sem commit/push/merge/`git add`.** Sem `reset --hard`, `clean`, `stash`, `checkout --`/`restore` em arquivo que você não criou.
- Pendências preexistentes não são suas: `docs/terminal-ui-masterplan.md` (D), `Reels_Encoder_AI.ico`, `docs/*.md` não rastreados, `*.qc.html`/`*.qc.json` na raiz, `videos/`.
- Não tocar `CLAUDE.md`, `.claude/agents/*`, código Python.
- **Não executar o launcher de verdade** (abre venv/pip/janelas) nem os `tools/fetch_*.ps1` (rede). Tudo por Pester com repositório temporário (`TestDrive:`) e mocks.
- Testes sem rede e sem `Start-Sleep`. Ambíguo → `blocked` com a pergunta exata em STATE.md.
- Linhas citadas são de `3c16e56`; reconfirme antes de editar.

## Comportamento alvo

| situação | FFmpeg/FFprobe | Windows Terminal |
| --- | --- | --- |
| padrão | `bin\` → PATH → baixa automático (log `Info` antes: o quê, ~tamanho, destino) | baixa automático com o mesmo log |
| `-NoDownload` | `bin\` → PATH → faltando: `throw` com orientação (`winget install --id BtbN.FFmpeg.GPL.6.1` ou `.\tools\fetch_ffmpeg.ps1`, ou rodar sem `-NoDownload`) → catch do bloco principal → **exit 1** (`launcher.cmd` pausa) | não baixa; `Warn` com como instalar (`.\tools\fetch_wt_portable.ps1`) e segue com janelas PowerShell |
| `-SkipValidation` | sem validação nem download (como hoje, `launcher.ps1:713-724`) | **não baixa** (novo); `Warn` e segue |

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| L2-1 | `launcher.ps1` | **R-09.** Nova função `Find-FfmpegBinary -LocalPath -Name`: `LocalPath` se `Test-Path -LiteralPath -PathType Leaf`; senão `(Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue \| Select-Object -First 1).Source`; senão `$null`. `Resolve-Binaries` (`:446-524`) usa-a para `ffmpeg`/`ffprobe` (nomes sem `.exe` no `Get-Command`); fetch só se algum for `$null`; depois do fetch, resolver de novo. Caminhos resolvidos seguem para `Test-RequiredBinary`/`Test-ExecutableRuns`/`Test-FfmpegCapabilities` e para o objeto de retorno (→ `REELS_FFMPEG`/`REELS_FFPROBE`). Log da origem (`bin` ou `PATH: <caminho>`). |
| L2-2 | `launcher.ps1` | **R-08.** `param` ganha `[switch]$NoDownload`. `Resolve-Binaries` e `Ensure-WindowsTerminalPortable` (`:526`) ganham `[switch]$NoDownload`. No bloco principal (`:709-712`): chamar `Ensure-WindowsTerminalPortable -NoDownload:($NoDownload -or $SkipValidation)`; `Resolve-Binaries ... -NoDownload:$NoDownload`. Log `Info` antes de cada fetch: WT "~90 MB → bin\WindowsTerminal"; FFmpeg "via winget (BtbN.FFmpeg.GPL.6.1) → bin\". |
| L2-3 | `tools/fetch_wt_portable.ps1`, `tools/fetch_ffmpeg.ps1` | **R-17.** `$ProgressPreference = 'SilentlyContinue'` logo após `$ErrorActionPreference`. |
| L2-4 | `tools/fetch_wt_portable.ps1` | **R-18.** Função `Set-WtDefaultSettings -SettingsDir`: cria a pasta, grava o JSON padrão atual (fonte 10) **só se `settings.json` não existir**; se existir, não toca e loga "settings.json existente preservado". Na reinstalação: antes do `Remove-Item $DestDir`, copiar `settings\settings.json` existente para temp; depois do `Move-Item`, restaurar; então `Set-WtDefaultSettings`. Envolver o corpo executável no guard `if ($MyInvocation.InvocationName -ne '.') { ... }` (mesmo padrão do `launcher.ps1`) para o Pester fazer dot-source sem rede. |
| L2-5 | `launcher.ps1`, `launcher.cmd` | **R-19.** Help por comentário no topo do `launcher.ps1`: `.SYNOPSIS` atual + `.PARAMETER` para `DebugMode`, `SkipValidation` (mover o comentário longo da `:10` para cá), `SkipEnvSetup`, `ForceEnvSetup`, `NoDownload` + `.EXAMPLE` (`launcher.cmd`, `launcher.cmd -NoDownload`, `launcher.cmd -SkipValidation`). `launcher.cmd`: um bloco `REM` listando os flags aceitos (repassados por `%*`). Sem `--ui`, sem `launcher-classic.cmd`. |
| L2-6 | `launcher.ps1` | **R-20.** Tabs → espaços em `:709-712`, alinhado ao bloco (8 espaços). |
| L2-7 | `.github/workflows/ci.yml` | **UF1.** `on.push.branches` ganha `"worktree-**"`. Validar: `actionlint` se existir; senão `python -c "import yaml; ..."` + checagem manual do schema (memória: CI YAML schema — `on.push.branches` é lista de strings glob). |
| L2-8 | `tests/launcher.Tests.ps1` | **Pester (TDD).** `Find-FfmpegBinary` (local / PATH via `Mock Get-Command` / `$null`). `Resolve-Binaries`: só no PATH (repo temp sem `bin\`, `Get-Command` mockado) → sem fetch, retorna caminhos do PATH; ausente + `-NoDownload` (repo temp com `tools\fetch_ffmpeg.ps1` falso que grava marcador) → `throw` com a orientação e marcador **ausente**; ausente sem `-NoDownload` → marcador presente. **Mockar `Get-Command` nos casos "ausente"** (runner ubuntu pode ter ffmpeg no PATH). Atenção: `Test-ExecutableRuns`/`Test-FfmpegCapabilities` usam `& $caminho` (não mockável) — mockar as **funções** `Test-ExecutableRuns`/`Test-FfmpegCapabilities` nos casos de sucesso. `Ensure-WindowsTerminalPortable -NoDownload` → `$false` e sem fetch (marcador). `Set-WtDefaultSettings` (dot-source de `tools/fetch_wt_portable.ps1`): existente intacto byte a byte; ausente → criado com `"size": 10`. Parâmetro `NoDownload` presente no `launcher.ps1` (`(Get-Command <path>).Parameters`). Zero `\t` em `launcher.ps1`, `launcher.cmd`, `tools/*.ps1`. Atualizar o comentário de cabeçalho do teste se a contagem de funções/linha do guard mudar. |
| L2-9 | — | Rodar `Invoke-Pester -Path ./tests -CI` no **pwsh 7** e no **Windows PowerShell 5.1** (`powershell.exe`; Pester 5.7.1 — se não instalado no 5.1, registrar em STATE.md sem instalar nada globalmente sem dizer); `venv\Scripts\python.exe -m ruff check .`; `git diff --check`. Números reais em STATE.md (§ Ciclo L2); VALIDATION.md com "smoke manual do launcher.cmd (padrão e `-NoDownload` com FFmpeg só no PATH) PENDENTE — usuário". Fora do escopo → FINDINGS.md. |
