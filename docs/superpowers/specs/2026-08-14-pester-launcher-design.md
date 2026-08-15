# Testes Pester para o Launcher Portátil — design

**Date:** 2026-08-14
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

Cobertura automatizada para `launcher.ps1` — o único artefato do projeto que
hoje tem **zero teste** e é, ao mesmo tempo, a **primeira coisa que um usuário
pagante toca**. O spec do launcher
(`docs/superpowers/specs/2026-08-13-launcher-portavel-design.md` § Goal) define
o objetivo de negócio como "viabilizar a distribuição/comercialização do
produto sem exigir que o usuário final saiba configurar um ambiente Python":
se o bootstrap quebra, o produto não existe para esse usuário — não importa o
quanto o encoder por trás esteja correto.

A evidência de que a cobertura falta é empírica, não hipotética: os **dois**
bugs conhecidos do launcher (`QF1` — stderr de comando nativo promovido a erro
terminante; `QF2` — isolamento portátil incompleto de `-SkipValidation`) foram
achados por **execução manual** numa máquina Windows, nos ciclos Q/R/S/T, e não
por nenhum teste. `QF1` em particular precisou de três ciclos (S, T) e um repro
sintético escrito à mão para ser fechado. Validação manual acha bug uma vez;
não protege contra regressão na segunda vez.

O escopo é o que é testável de verdade: as funções puras de montagem de
comando, os orquestradores (via mock das próprias funções do script), o
contrato do `launch-config.json`, e o fallback de lançamento sem Windows
Terminal. O que não é testável está nomeado explicitamente abaixo, com o
motivo técnico — não é omissão.

## Supersedes

Este spec **reverte duas restrições explícitas** de documentos anteriores deste
mesmo repo. A reversão é deliberada e precisa ficar registrada, porque quem ler
os documentos antigos vai encontrar o oposto do que está aqui:

1. `docs/superpowers/specs/2026-08-13-launcher-portavel-design.md`
   § "Non-goals / constraints":

   > **Sem framework de teste novo.** Validação é execução real + checklist
   > manual, documentada em `STATE.md` (segue o padrão de
   > `superpowers:verification-before-completion`, não Pester).

2. `docs/superpowers/plans/2026-08-13-launcher-portavel.md`
   § "Global Constraints":

   > Sem introduzir Pester ou qualquer outro framework de teste PowerShell.

**Por que a decisão mudou.** As duas restrições eram corretas *no contexto em
que foram escritas*: em 2026-08-13 o `launcher.ps1` não existia. Introduzir um
framework de teste ao mesmo tempo que se escreve o artefato do zero significa
testar um design que ainda vai mudar — custo alto, valor baixo, e um vetor a
mais de erro num ciclo que já tinha 9 tasks. Três coisas mudaram desde então:

- **O script existe, está estável e foi validado de verdade.** Ciclos Q, R, S e
  T fecharam a implementação, a integração ponta-a-ponta numa máquina Windows
  real, e os dois findings abertos. A superfície pública (14 funções, nomes e
  assinaturas) parou de mudar — é isso que torna um teste um ativo em vez de um
  passivo.
- **O guard de dot-source foi projetado exatamente para isto.** `launcher.ps1`
  linha 270 já separa "carregar as funções" de "rodar o bootstrap" (ver
  Architecture). A validação manual dos ciclos Q-T já usava `. .\launcher.ps1` +
  chamada direta de função — o Pester é a mesma técnica, só que executável por
  uma máquina, repetidamente, em duas versões de PowerShell.
- **Validação manual não escala para regressão.** O ciclo T mudou três funções
  de bootstrap para corrigir `QF1`. Nada além da leitura do Orquestrador
  garantiu que `Build-*`, `Resolve-Binaries` e `Open-LauncherTabs` continuaram
  intactos — a nota "Não tocar em ..." do `PLAN.md` do ciclo T é uma instrução,
  não uma verificação.

O que **não** muda: a política de evidência real continua valendo. Pester
substitui a *repetição* da validação manual, não a validação de integração de
ponta a ponta (venv real, pip real, janelas reais), que continua sendo
execução real registrada em `STATE.md`.

## Non-goals / constraints

- **Zero refatoração de `launcher.ps1`.** O script não é editado — nem para
  "facilitar o teste". Isso é `CLAUDE.md` § Anti-escopo, e é possível porque o
  guard de dot-source já existe. Se um teste for difícil de escrever, o teste é
  ajustado ou a superfície é declarada não-testável; o script de produção não.
- **`tools/fetch_wt_portable.ps1` e `tools/fetch_ffmpeg.ps1` ficam de fora.**
  Nenhum dos dois define funções — são scripts lineares de cima a baixo, sem
  guard de dot-source. Testá-los exigiria exatamente a refatoração que o item
  anterior proíbe, em scripts que já foram validados manualmente por execução
  real (ciclo Q, Tasks 7 e 9). Custo alto, risco de quebrar algo que funciona,
  ganho marginal.
- **Zero código Python tocado.** `Reels_Encoder_v2_FINAL.py`, `enhance/`, `ui/`
  (incluindo `ui/test_launcher.py`, que testa o *wizard* Python e não tem
  relação com este spec) ficam intocados. A suíte pytest atual continua com o
  mesmo número de testes.
- **Pester não vira dependência de runtime.** É dev/CI-only: instalado pelo job
  do GitHub Actions e (opcionalmente) pela máquina do desenvolvedor. Um usuário
  final que roda `.\launcher.ps1` nunca precisa de Pester. Nada é acrescentado a
  `requirements.txt` ou `pyproject.toml`.
- **Nenhuma tentativa de testar as três chamadas nativas `& $variablePath`.**
  Ver "Superfícies não-testáveis" — é uma limitação real do Pester, não uma
  escolha de escopo, e fingir cobertura ali seria pior que não ter.
- **Nenhuma asserção sobre texto acentuado.** Ver "Riscos conhecidos" §
  encoding.

## Architecture

### O que torna isto possível

`launcher.ps1:270`:

```powershell
if ($MyInvocation.InvocationName -ne '.') {
```

Todo o corpo de bootstrap (venv, pip, validação, lançamento de janelas) vive
dentro desse guard. Quando o arquivo é carregado por dot-source
(`. ./launcher.ps1`), `$MyInvocation.InvocationName` é literalmente `.`, a
condição é falsa, e o resultado é: **as 14 funções são definidas na sessão e
nada é executado**. É exatamente o contrato que um teste unitário precisa, e ele
já está no código desde a Task 2 do ciclo Q — nenhuma mudança necessária.

### Layout dos testes

```text
encoder_ai_instagram/
├── launcher.ps1                    ← intocado
├── launch-config.json              ← intocado
└── tests/                          ← novo
    ├── launch-config.Tests.ps1     ← contrato do JSON (100% OS-independente)
    └── launcher.Tests.ps1          ← funções do launcher
```

`tests/` na raiz, sufixo `*.Tests.ps1`: é a convenção universal do Pester
(`Invoke-Pester -Path ./tests` acha tudo sem configuração). Deliberadamente
**não** fica em `ui/` — `ui/test_launcher.py` já existe ali e testa o wizard
Python `ui/launcher.py`, que não tem nenhuma relação com `launcher.ps1`. Dois
"launchers" com propósitos diferentes no mesmo diretório seria uma armadilha
de leitura permanente.

`.gitignore` foi conferido: não engole `tests/` nem `*.Tests.ps1`.

### O que é testado (por função)

As 14 funções de `launcher.ps1`, classificadas por como (e se) são testáveis:

| função | o que é asseverado | OS-independente |
| --- | --- | --- |
| `Build-ProfileArgs` | array de flags exato dos 5 perfis; perfil desconhecido lança listando os nomes válidos; `batch` sem `-BatchDir` lança; `batch` com `-BatchDir` prefixa `--batch <dir> --output-dir <dir>`; **nenhum perfil produz `--crf`** | sim |
| `Build-SetupCommand` | contém `--hardware-info`; o path casa com `Reels_Encoder_v2_FINAL\.py` (via `-match`) | sim |
| `Build-EncodeCommand` | sem perfil → `--ui`; com perfil + input → contém o input e as flags do perfil; perfil `batch` → **omite** o arquivo de entrada | sim |
| `Read-LauncherConfig` | path ausente lança `nao encontrado`; JSON malformado lança `invalido`; JSON válido parseia | sim |
| `Write-LauncherLog` | prefixos `[OK]`/`[ERRO]`/`[AVISO]` corretos por nível; nível `Debug` suprimido quando `$Debug` é falso | sim |
| `Initialize-Environment` | venv existente → `New-ProjectVenv` **não** é chamado, `Install-Requirements`/`Write-VenvLock` são; venv ausente → `New-ProjectVenv` chamado 1×; retorno casa `python` | sim (via mock) |
| `Resolve-Binaries` | retorna os 5 membros (`VenvPython`, `Ffmpeg`, `Ffprobe`, `WtPath`, `WtAvailable`); `wt.exe` ausente → `WtAvailable = $false` **sem lançar** (binário opcional) | sim (via mock) |
| `Open-LauncherTabs` | ramo `$WtAvailable = $false` → `Start-Process` chamado 2× | sim (via mock) |
| `Test-VenvExists` | coberto indiretamente como mock alvo em `Initialize-Environment` | — |
| `Test-RequiredBinary` | coberto indiretamente como mock alvo em `Resolve-Binaries` | — |
| `Resolve-SystemPython` | **não testado** — depende do PATH real da máquina | — |
| `New-ProjectVenv` | **não testado** — `& $pythonCmd` (ver abaixo) | — |
| `Install-Requirements` | **não testado** — `& $VenvPython` (ver abaixo) | — |
| `Write-VenvLock` | **não testado** — `& $VenvPython` (ver abaixo) | — |

### Estratégia de mock

Duas camadas, escolhidas pelo tipo da função:

- **Orquestradores → mockar as próprias funções do script.** Pester 5 consegue
  interceptar funções definidas por dot-source na mesma sessão. `Mock
  Test-VenvExists { $true }` + `Should -Invoke New-ProjectVenv -Times 0` testa
  a *decisão* de `Initialize-Environment` (criar vs. reaproveitar venv) sem
  criar venv nenhum. Mesmo padrão para `Resolve-Binaries` sobre
  `Test-RequiredBinary`. É aqui que está o valor real: a lógica de decisão é o
  que quebra em regressão, e é o que a validação manual mais cansa de repetir.
- **Near-pure → mockar cmdlets do PowerShell.** `Test-Path`, `Start-Process`,
  `Write-Host` são nomes de comando, então `Mock` funciona normalmente. Para
  I/O de arquivo real (JSON malformado), usar `$TestDrive` — o drive temporário
  que o Pester cria e limpa sozinho por container, sem tocar em nada do repo.
- **Puras → sem mock nenhum.** As três `Build-*` recebem o `$Config` real
  carregado do `launch-config.json` do repo e devolvem string/array. Zero
  ambiente, zero cleanup.

### Superfícies não-testáveis (e por quê)

Três chamadas de `launcher.ps1` invocam um executável **através de uma
variável**:

```powershell
& $pythonCmd -m venv $VenvPath          # New-ProjectVenv, linha 84
& $VenvPython -m pip install -r $reqPath # Install-Requirements, linha 108
& $WtPath new-tab --title "Setup" ...    # Open-LauncherTabs, linha 261
```

O `Mock` do Pester engancha em **nomes de comando** (funções, cmdlets, aliases,
applications resolvidas pelo nome). `& $variavel` resolve o conteúdo da
variável como um caminho de Application em tempo de execução — não há nome para
enganchar, e o mock simplesmente nunca dispara. Isso não é contornável sem
refatorar `launcher.ps1` (ex.: injetar um invocador), o que este spec proíbe.

Consequência, dita sem eufemismo: **criação real de venv, `pip install` real e
o ramo `wt.exe` de `Open-LauncherTabs` não têm cobertura unitária.** Só o
fallback (`$WtAvailable = $false`, via `Mock Start-Process`) é coberto.

A evidência para essas três superfícies já existe e **não é re-derivada aqui**:
execução real numa máquina Windows, registrada em `.claude/memory/STATE.md`
§ "Ciclo Q — launcher portátil (launcher.ps1) — validação de integração"
(venv novo, venv reaproveitado, `pip install` completo, 2 abas reais do Windows
Terminal e o fallback de 2 janelas PowerShell), § "Ciclo S" (repro sintético do
stderr nativo nos dois motores) e § "Ciclo T" (`Install-Requirements` real sob
Windows PowerShell 5.1 com `*>&1`). Pester cobre o que a execução manual é ruim
em repetir; a execução manual cobre o que o Pester não alcança.

### CI

Job novo em `.github/workflows/ci.yml`, seguindo o estilo dos dois jobs
existentes (`actions/checkout@v4`, `fail-fast: false`, versão pinada):

- matriz `os: [ubuntu-latest, windows-latest]`, `fail-fast: false`;
- `Install-Module Pester -MinimumVersion 5.5.0` (mínimo pinado, mesmo hábito de
  `ruff==0.14.10`);
- `Invoke-Pester -Path ./tests -CI`, `shell: pwsh` nos dois runners — ambos
  trazem PowerShell Core de fábrica;
- um passo que imprime `$PSVersionTable`, para diagnóstico quando os dois legs
  divergirem.

**Por que `windows-latest` importa.** Não é redundância. O ciclo T provou que o
bug `QF1` (`$ErrorActionPreference` + stderr de comando nativo) **só reproduz em
Windows PowerShell 5.1** — em pwsh 7.5.1 o repro passava limpo. Uma matriz só
Linux testaria um motor que nenhum usuário final usa. O runner windows dá
`pwsh` (Core) e também tem `powershell` (5.1) disponível, deixando a porta
aberta para um leg 5.1 futuro sem mudar a estrutura.

## Riscos conhecidos

- **Separador de path.** `Join-Path` produz `/` no Linux e `\` no Windows, e as
  três `Build-*` montam strings com `Join-Path`. Qualquer asserção de igualdade
  literal de comando falharia num dos dois legs da matriz. Mitigação: toda
  asserção de path usa `-match 'Reels_Encoder_v2_FINAL\.py'` (ou `-like`),
  nunca `-eq` contra um caminho montado à mão.
- **Encoding / BOM.** Os `.ps1` e o JSON do repo são UTF-8 **sem BOM**, LF.
  Windows PowerShell 5.1 lê arquivo sem BOM como ANSI, então
  `"Preview rápido"` chega mojibake. Mitigação: os testes só asseveram sobre
  campos ASCII (flags, paths, chaves, nomes de perfil). O campo `description`
  de `launch-config.json` **nunca** é comparado por valor — só por presença e
  por ser não-vazio.
- **`$IsWindows` não existe em PS 5.1.** É uma variável automática exclusiva do
  PowerShell Core; em 5.1 ela é `$null` (e 5.1 só roda em Windows). Mitigação:
  `$script:OnWindows = if ($null -eq $IsWindows) { $true } else { $IsWindows }`.
- **Vazamento de escopo do dot-source.** Carregar `launcher.ps1` na sessão do
  Pester injeta `$ErrorActionPreference = "Stop"`,
  `$PSNativeCommandUseErrorActionPreference = $false` e `$Script:RepoRoot` no
  contexto do teste. `"Stop"` transforma qualquer erro não-terminante do Pester
  em falha e pode mascarar a causa real. Mitigação: `BeforeAll` salva o
  `$ErrorActionPreference` anterior e um `AfterAll` restaura.
- **`launcher.ps1` não tem `[CmdletBinding()]`** (deliberado — evita colisão do
  `-Debug` automático com o `[switch]$Debug` explícito, ver Task 2 do plano do
  ciclo Q). Consequência para os testes: `$Debug` é uma variável comum e, sob
  dot-source sem argumentos, é falsa — que é justamente o cenário do teste de
  supressão do nível `Debug` em `Write-LauncherLog`.
- **Divergência entre os legs da matriz.** Se um teste passar no ubuntu e
  falhar no windows (ou vice-versa), a hipótese padrão é que é um achado real
  sobre `launcher.ps1` — não um teste mal escrito. Investigar antes de
  "consertar" o teste. Foi exatamente esse tipo de divergência entre motores
  que produziu `QF1`.

## Validação

**Honestidade sobre o ambiente:** não há `pwsh` no sandbox de desenvolvimento
onde este spec e o plano foram escritos (`pwsh: command not found`; não
disponível via apt). A PSGallery é alcançável pela rede, mas não há PowerShell
para instalar o Pester dentro. Consequência direta: **é impossível colar saída
local real por task** durante a implementação deste plano.

Isto é um **desvio documentado** do hábito de
`superpowers:verification-before-completion` (colar saída real, nunca
parafrasear) seguido em todos os ciclos anteriores deste repo. O desvio é do
ambiente, não da política, e a política continua valendo — só muda de onde a
evidência vem:

- **Fonte primária:** a execução do CI. A task final do plano faz push, lê o
  run do GitHub Actions nos **dois** legs da matriz, e cola a saída real do
  `Invoke-Pester` (contagem de testes, passed/failed, `$PSVersionTable`) mais a
  URL do run em `.claude/memory/STATE.md` § "Ciclo U". A URL é o que torna a
  evidência auditável depois.
- **Fonte secundária (opcional):** a máquina Windows do usuário, onde
  `Invoke-Pester -Path .\tests` roda em pwsh 7 e em `powershell` 5.1. É a única
  forma de exercitar o motor 5.1 de produção hoje.
- **Regressão não-negociável:** a suíte pytest existente continua verde e com o
  mesmo número de testes. Nenhum arquivo Python é tocado por este ciclo, então
  qualquer variação ali é sinal de que algo saiu do escopo.

Nenhuma task pode ser marcada como concluída com base em "o código parece
certo". Enquanto o CI não rodar, o estado correto do ciclo é *implementado, não
verificado* — e é assim que deve ser reportado.
