<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo U: Pester para o launcher.ps1

Data: 2026-08-14 | Ciclo: U | Origem: decisão do usuário após o fechamento do
Ciclo T (`97090ee`). Spec:
`docs/superpowers/specs/2026-08-14-pester-launcher-design.md`. Plano detalhado
(com o código literal dos testes):
`docs/superpowers/plans/2026-08-14-pester-launcher.md`.

## Diagnóstico

`launcher.ps1` é o caminho de entrada comercial do produto — a primeira coisa
que um usuário pagante toca — e é o único artefato do repo com **zero teste
automatizado**. Os dois bugs conhecidos dele (`QF1`, `QF2`, ver `FINDINGS.md`)
foram achados por **execução manual** nos ciclos Q/R/S/T; `QF1` precisou de
três ciclos e um repro sintético escrito à mão. Validação manual acha bug uma
vez, não protege contra regressão — o Ciclo T mudou três funções de bootstrap e
nada além da leitura do Orquestrador garantiu que `Build-*`, `Resolve-Binaries`
e `Open-LauncherTabs` continuaram intactos.

O spec e o plano do launcher (2026-08-13) **proibiam** Pester por escrito. O
spec novo abre revertendo isso explicitamente (§ Supersedes): a restrição fazia
sentido quando o script ainda não existia; hoje ele está estável, validado, e o
guard de dot-source (`launcher.ps1:270`) já foi projetado exatamente para isto.

`launcher.ps1` e `launch-config.json` são **read-only** neste ciclo
(`CLAUDE.md` § Anti-escopo). Nenhum arquivo Python é tocado.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| U1 | Contrato do `launch-config.json`: JSON válido, `defaultProfile` existente, exatamente 5 perfis, `flags` não-vazias + `description` presente por perfil, **nenhum `--crf`** (Regra de Ouro), só `batch` com `requiresBatchDir`, todo `paths` string não-vazia, `encoderScript`/`requirements` existem no disco. Só campos ASCII. Código literal: plano § Task 1. | `executor` | `tests/launch-config.Tests.ps1` | arquivo criado como no plano; `git check-ignore` confirma que não é ignorado; nenhum `.py`/`launcher.ps1` modificado |
| U2 | `BeforeAll` de topo (save/restore de `$ErrorActionPreference`, dot-source via `$PSScriptRoot`, `$script:OnWindows`, `$script:Config`) + contrato de dot-source (14 funções) + testes puros de `Build-ProfileArgs`/`Build-SetupCommand`/`Build-EncodeCommand`. Path sempre por `-match`, nunca `-eq`. Código literal: plano § Task 2. | `executor` | `tests/launcher.Tests.ps1` | arquivo criado como no plano; `git diff --stat -- launcher.ps1 launch-config.json` vazio |
| U3 | Orquestradores por mock das próprias funções do script: `Initialize-Environment` (`Mock Test-VenvExists` → `Should -Invoke New-ProjectVenv -Times 0/1`) e `Resolve-Binaries` (`Mock Test-RequiredBinary` + `Mock Test-Path -ParameterFilter wt.exe` → 5 membros, `WtAvailable` falso sem throw). Código literal: plano § Task 3. | `executor` | `tests/launcher.Tests.ps1` (append) | `grep` confirma que os 8 nomes mockados existem em `launcher.ps1`; `git diff --stat -- launcher.ps1` vazio |
| U4 | `Read-LauncherConfig` (ausente → `nao encontrado`, malformado em `$TestDrive` → `invalido`, válido parseia), `Write-LauncherLog` (prefixos `[OK]`/`[ERRO]`/`[AVISO]`/`[INFO]` via `Mock Write-Host`, `Debug` suprimido) e o fallback de `Open-LauncherTabs` (`Mock Start-Process`, 2 invocações). Ramo `wt.exe` não coberto — comentar por quê. Código literal: plano § Task 4. | `executor` | `tests/launcher.Tests.ps1` (append) | arquivo completo; nenhuma fixture em disco do repo (tudo em `$TestDrive`) |
| U5 | Job `pester` no CI: matriz `os: [ubuntu-latest, windows-latest]`, `fail-fast: false`, `actions/checkout@v4`, passo de `$PSVersionTable`, `Install-Module Pester -MinimumVersion 5.5.0`, `Invoke-Pester -Path ./tests -CI`, tudo em `shell: pwsh`. Append puro — não tocar nos jobs `lint`/`tests`. YAML literal: plano § Task 5. | `executor` | `.github/workflows/ci.yml` | `git diff` do arquivo só tem linhas `+`; parse YAML lista `['lint','pester','tests']` |
| U6 | Push, ler o run do CI nos **dois** legs da matriz, colar saída real (`Invoke-Pester` + `$PSVersionTable` + URL do run) em `STATE.md` § `## Ciclo U — Pester para o launcher — 2026-08-14`. Divergência entre legs = achado real sobre o script → `FINDINGS.md` como `UF1`, `UF2`, … antes de qualquer "conserto". Confirmar suíte pytest inalterada. | `executor-pesado` | `.claude/memory/STATE.md`, `.claude/memory/FINDINGS.md` | CI verde nos dois legs com saída bruta colada, ou BLOCKED com a evidência da falha |

## Notas de execução

- **Não há `pwsh` neste sandbox** (`pwsh: command not found`, não disponível
  via apt; PSGallery é alcançável mas não há motor para instalar o Pester).
  Consequência: U1-U5 **não conseguem** colar saída local real. Isso é um desvio
  documentado de `superpowers:verification-before-completion` — do ambiente, não
  da política. A evidência do ciclo vem do CI (U6) e, opcionalmente, da máquina
  Windows do usuário. Até U6 rodar, o estado correto é *implementado, não
  verificado*; reportar assim, sem arredondar.
- `launcher.ps1` e `launch-config.json` são read-only. U2, U3, U4 e U6 têm step
  explícito de `git diff --stat` esperando vazio. Se um teste for difícil de
  escrever, ajusta-se o teste — nunca o script de produção.
- Superfícies declaradas não-testáveis (não tentar): `& $pythonCmd`,
  `& $VenvPython`, `& $WtPath`. `Mock` engancha em nomes de comando; caminho
  vindo de variável resolve como Application em runtime. Evidência dessas
  superfícies já existe em `STATE.md` §§ Ciclo Q/S/T — citar, não re-derivar.
- Gotchas que o código do plano já mitiga (não "corrigir" de novo):
  separador de path (`-match`, nunca `-eq`), encoding sem BOM lido como ANSI em
  PS 5.1 (nunca assertar em `description`), `$IsWindows` inexistente em 5.1,
  vazamento de `$ErrorActionPreference = "Stop"` pelo dot-source.
- U2-U4 escrevem no **mesmo arquivo** `tests/launcher.Tests.ps1`, sempre por
  append no fim. Não editar o `BeforeAll`/`AfterAll` de topo depois de U2.
- Retorno de cada agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
