<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AV: fechar UF2 (CI não roda Windows PowerShell 5.1, o motor de produção do launcher)

Data: 2026-09-04 | Ciclo: AV | Origem: `.claude/memory/FINDINGS.md` § `UF2` (Ciclo U, 2026-08-15). Último item em aberto da fila; `AUF1` foi descartado pelo usuário em 2026-09-04.

## Diagnóstico

Remedido hoje contra o `ci.yml` atual. `UF2` continua valendo: o job `pester`
(`.github/workflows/ci.yml:63-91`) tem matriz `os: [ubuntu-latest, windows-latest]` e
**todos os steps usam `shell: pwsh`** (linhas 75, 81, 87) — PowerShell 7 Core nas duas
pernas. Nenhuma perna roda **Windows PowerShell 5.1 (Desktop)**, que é:

- o motor de produção do `launcher.ps1` (duplo-clique / atalho no Windows do usuário final);
- o único motor onde o `QF1` reproduzia (ver `FINDINGS.md` § Ciclo Q).

Consequência: uma regressão específica de 5.1 no `launcher.ps1` passaria verde no CI hoje. A
única evidência de que a suíte passa em 5.1 é local (máquina do usuário, Ciclo U).

### Risco medido antes de planejar

- **Sintaxe: baixo.** `grep` de construções só-pwsh-7 (`??`, ternário `? :`, `&&`/`||`,
  `#Requires -PSEdition Core`, `ForEach-Object -Parallel`, `ConvertFrom-Json -AsHashtable`)
  em `launcher.ps1` e nos dois arquivos de teste (`tests/launcher.Tests.ps1`,
  `tests/launch-config.Tests.ps1`) = **zero ocorrências**. O launcher foi escrito para 5.1;
  os testes devem passar nele. Se algum falhar em 5.1, é **achado novo** (incompatibilidade
  real 5.1), não algo a mascarar — parar e reportar, não editar teste/launcher.
- **Mecânica de instalar Pester em 5.1: este é o risco.** WinPS 5.1 traz PowerShellGet
  antigo; `Install-Module Pester -RequiredVersion 5.7.1` num runner pode exigir bootstrap
  de TLS 1.2 + provider NuGet + repo confiável, coisas que o `pwsh` 7 já resolve sozinho.
  É onde a primeira run pode falhar; o step de instalação da perna 5.1 precisa do bootstrap.
- **Pester 5.7.1 roda em 5.1: sim.** Pester 5.x suporta Windows PowerShell 5.1 (não é a
  incompatibilidade da 6.x que o `UF3` discutiu). `-RequiredVersion 5.7.1` e `-CI` são
  válidos nos dois motores.

## Desenho

> **Correção de desenho (2026-09-04, após 1ª run falhar).** A 1ª tentativa (commit `8b61ed4`)
> pôs `shell: ${{ matrix.shell }}` numa matriz `include`. **GitHub Actions rejeita expressão
> na chave `shell`** — `shell` em step/defaults não aceita contexto `matrix`/`job` (schema
> `non-empty-string`, ver actions/runner#444). Resultado: "workflow file issue", 0 jobs, run
> `failure` em 0s. Matriz-com-shell é impossível na plataforma. Desenho corrigido: **job
> separado** com `shell: powershell` fixo (constante, sem expressão).

Manter o job `pester` **byte-idêntico ao `main`** (matriz `os: [ubuntu-latest,
windows-latest]`, `shell: pwsh` — as duas pernas Core, intocadas) e **adicionar um job irmão**
`pester-winps51`, só em `windows-latest`, com `shell: powershell` (Windows PowerShell 5.1
Desktop) fixo em cada step. Um pouco de duplicação de corpo de job é o preço idiomático de ter
shells diferentes por perna, já que `shell:` não pode ser templatizado.

```yaml
  pester-winps51:
    name: Pester (Windows PowerShell 5.1)   # motor de producao do launcher.ps1 — fecha UF2
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v5

      - name: PowerShell version (diagnostico)
        shell: powershell
        run: |
          $PSVersionTable | Format-List
          Write-Host "Engine: Windows PowerShell 5.1 Desktop (motor de producao do launcher.ps1)"

      - name: Install Pester
        shell: powershell
        run: |
          # bootstrap WinPS 5.1: TLS 1.2 + provider NuGet antes do Install-Module (pwsh 7 nao precisa)
          [Net.ServicePointManager]::SecurityProtocol = `
            [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
          Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force | Out-Null
          Install-Module Pester -RequiredVersion 5.7.1 -Force -Scope CurrentUser -SkipPublisherCheck
          Get-Module Pester -ListAvailable | Select-Object Name, Version | Format-Table

      - name: Run Pester
        shell: powershell
        run: |
          Import-Module Pester -RequiredVersion 5.7.1
          Invoke-Pester -Path ./tests -CI
```

Cada step usa a constante `shell: powershell` — sem expressão, schema válido. Na hospedeira
`windows-latest`, `powershell` é o Windows PowerShell 5.1 Desktop; `pwsh` seria o 7 Core (já
coberto pelo job `pester`). O bootstrap TLS+NuGet fica só neste job, onde é necessário.

### O que NÃO fazer

- **Não** tocar no job `pester` — se a 1ª tentativa o alterou, **reverter para o estado do
  `main`**. `UF2` é *adicionar* um job de 5.1, não mudar o `pester` existente.
- **Não** tocar em `launcher.ps1` nem em `tests/*.Tests.ps1`. Se a perna 5.1 reprovar, é
  achado novo — registrar em `FINDINGS.md` e parar, não editar o alvo para ficar verde.
- **Não** mexer no `UF1` (filtro de branch/worktree) nem em `workflow_dispatch` — é outro
  achado, fora deste ciclo.
- **Não** tocar nos jobs `lint`, `tests`, nem no gatilho `on:`.
- **Não** bump de versão de action (checkout@v5 etc. já estão certos do Ciclo AQ).

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AV1 | No `ci.yml`: (a) garantir que o job `pester` está **byte-idêntico ao `main`** — se a tentativa anterior o converteu para matriz `include`, revertê-lo; (b) **adicionar** o job irmão `pester-winps51` (bloco YAML do § Desenho), `runs-on: windows-latest`, `shell: powershell` fixo nos 3 steps, com o bootstrap TLS 1.2 + `Install-PackageProvider NuGet`. Nada fora disso. | executor | `.github/workflows/ci.yml` | `git diff main` mostra **só** um job `pester-winps51` adicionado, `pester` intocado; nenhuma expressão em nenhuma chave `shell:` |
| AV2 | Fechar `UF2` no `FINDINGS.md` com a evidência real da run (as 3 pernas verdes, e a diagnostic da perna `powershell` provando `PSVersion 5.1.x` / `PSEdition Desktop`). | Orquestrador | `.claude/memory/FINDINGS.md` | — |

## Critérios de aceite

- Só `.github/workflows/ci.yml` muda — **só um job novo** (`pester-winps51`); o job `pester` fica idêntico ao `main`. Nenhum `.ps1`, nenhum outro job. **Nenhuma chave `shell:` com expressão** (a causa da falha da 1ª tentativa).
- **A prova do fecho não é "CI verde" genérico — é o job 5.1 nomeado e visível.** A aba Checks
  passa a mostrar o job **`Pester (Windows PowerShell 5.1)`** além das duas pernas Core do
  job `pester` (`pester (ubuntu-latest)`, `pester (windows-latest)`, ambas pwsh 7).
- No job `Pester (Windows PowerShell 5.1)`, o step "PowerShell version (diagnostico)" imprime
  `PSVersion` começando em `5.1` **e** `PSEdition Desktop` — prova de que é Windows
  PowerShell 5.1 real, não pwsh 7 disfarçado. (Analogia do "verde não é prova": um job verde
  cuja diagnostic confirma o motor certo.)
- Esse job instala Pester 5.7.1 e roda `Invoke-Pester` **verde** — mesma contagem da perna
  `pester (windows-latest)` (`Tests Passed: 91`, ou o que a suíte tiver no dia; o número tem
  que bater entre os dois jobs Windows).
- Suíte Python inalterada (o ciclo não toca Python) — os jobs `tests` seguem verdes por
  ausência de regressão, não é prova do fix.

## Notas de execução

- Ciclo de infra/CI: a prova vive na run, não localmente. O executor edita, faz o PR e a
  run dispara; **o Orquestrador** observa as 3 pernas e a diagnostic 5.1. Se a perna 5.1
  falhar na instalação do Pester (TLS/NuGet), o executor recebe instrução precisa a partir
  do log e ajusta o bootstrap — não é falha do desenho, é o risco previsto.
- Se a perna 5.1 falhar **no `Invoke-Pester`** (não na instalação) — teste reprovando em
  5.1 — **parar**: é incompatibilidade real 5.1 do launcher/teste, achado novo, não algo a
  contornar editando o alvo.
- **Nunca `git add -A` nem `git add .`** — há arquivos não rastreados (`961576A_*.qc.*`,
  `docs/*.md`, `testResults.xml`, `videos/`). Adicionar por caminho explícito.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AV` e cabeçalho de tabela.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
