<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BB: `pip check` sai do gate do cache e vira pós-condição do install

Data: 2026-09-07 | Ciclo: BB | Origem: auditoria do Orquestrador sobre o `main` pós-Ciclo BA (`982d8f8`), a pedido do usuário. Ciclo anterior: BA (fechado, PR #62). Achados novos: `BAF1`, `BAF2`, `BAF3` (registrados na Task `BB3`).

## Diagnóstico

O Ciclo BA acrescentou `& $VenvPython -m pip check` dentro de `Test-VenvHealthy`
(`launcher.ps1:229`). A intenção — detectar venv com pacotes inconsistentes — é correta. A
**posição** é o problema: `Test-VenvHealthy` é o gate do cache de dependências da `AX7`, e é
chamada incondicionalmente em `Initialize-Environment:295`, **antes** da comparação de stamp
em `:299`. Três consequências, medidas por leitura do `main`:

| ID | sev | âncora | defeito |
|----|-----|--------|---------|
| BAF1 | S3 | `launcher.ps1:295` | `pip check` roda em **todo** lançamento, inclusive no caminho rápido cujo objetivo era ~2 s. Num venv com numpy, scipy, opencv, matplotlib e av, `pip check` custa tipicamente 0,5–2 s no Windows (estimativa; não medido). Boa parte do ganho da `AX7` foi gasta aí |
| BAF2 | **S2** | `launcher.ps1:295-308` | Se `pip check` reporta um conflito que `pip install -r requirements.txt` **não resolve**, `$healthy` é `$false` em todo lançamento → o `if` da `:299` nunca entra → `Install-Requirements` + `Write-VenvLock` rodam **eternamente**, e o stamp gravado na `:307` nunca é consultado. O cache fica desligado para sempre, e o único sinal é uma linha amarela. Não é hipotético com estas dependências: `opencv-python` + `numpy>=1.24` + `matplotlib>=3.9,<4` + `scipy` é exatamente a família onde o pip instala com aviso de resolução (exit 0) e o `pip check` passa a reclamar para sempre |
| BAF3 | S4 | `launcher.ps1:297` | A mensagem `Venv nao respondeu a 'python -c import sys' - reinstalando dependencias.` nomeia só uma das duas causas possíveis de `$healthy = $false`. Quando a causa é o `pip check`, ela aponta o diagnóstico errado e promete uma correção (reinstalar) que não funciona |

### Por que a intenção do BA já estava parcialmente coberta

O caso "pip anterior interrompido no meio" que o BA citou **já é coberto pela ordem do
stamp** (`AX7`): `Install-Requirements` lança em exit ≠ 0 (`:198-200`), então `Write-VenvStamp`
(`:307`) nunca roda, e o próximo lançamento vê stamp ausente/diferente e reinstala. `pip check`
não é necessário para esse caso.

O caso que `pip check` **realmente** acrescenta é outro: `pip install` sai com **exit 0** mas
deixa um conflito de versão (pip faz isso, com aviso). Aí o stamp é gravado e o cache engata
sobre um venv inconsistente. Para esse caso, **reinstalar não resolve** — o mesmo
`requirements.txt` produz o mesmo conflito. A resposta certa é **avisar, com o texto do
conflito**, e não forçar reinstalação. É por isso que `pip check` não pode ser gate: ele
detecta uma condição que o gate não tem como corrigir.

## Desenho

Separar as duas intenções que o BA fundiu numa variável só.

**`Test-VenvHealthy` volta ao formato da `AX7`** — só `import sys`. Barato, e cobre o caso
que a motivou (venv órfão de repo movido). Continua sendo o gate do cache.

**Nova `Test-VenvConsistent`** — só `pip check`. Devolve o resultado **e o relatório**, para a
mensagem poder dizer *o que* está inconsistente. Chamada **uma vez, depois de
`Install-Requirements`**, como pós-condição. Nunca no caminho rápido; nunca decide reinstalar.

```powershell
function Test-VenvHealthy {
    param([Parameter(Mandatory)][string]$VenvPython)
    if (-not (Test-Path $VenvPython)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython -c "import sys" 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    return ($LASTEXITCODE -eq 0)
}

function Test-VenvConsistent {
    param([Parameter(Mandatory)][string]$VenvPython)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $VenvPython -m pip check 2>&1
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    return [PSCustomObject]@{
        Ok     = ($LASTEXITCODE -eq 0)
        Report = (@($out) -join "`n").Trim()
    }
}
```

**`Initialize-Environment`** — o trecho de `:295` em diante fica:

```powershell
    $healthy = Test-VenvHealthy -VenvPython $venvPython
    if (-not $healthy) {
        Write-LauncherLog "Venv nao respondeu a 'python -c import sys' (orfao ou corrompido) - reinstalando dependencias." "Warn"
    }
    if ((-not $Force) -and $healthy -and $stamp -and ((Read-VenvStamp -VenvPath $VenvPath) -eq $stamp)) {
        Write-LauncherLog "Dependencias ja instaladas (stamp confere) - pulando pip. Use -ForceEnvSetup para reinstalar." "Info"
        return $venvPython
    }

    Install-Requirements -RepoRoot $RepoRoot -VenvPython $venvPython -Config $Config
    Write-VenvLock -RepoRoot $RepoRoot -VenvPython $venvPython
    if ($stamp) {
        Write-VenvStamp -VenvPath $VenvPath -Stamp $stamp
    }
    $consistency = Test-VenvConsistent -VenvPython $venvPython
    if (-not $consistency.Ok) {
        Write-LauncherLog "pip check encontrou dependencias inconsistentes (o encoder pode falhar em runtime). Use -ForceEnvSetup depois de ajustar o pyproject.toml:`n$($consistency.Report)" "Warn"
    }
    return $venvPython
```

### Decisão registrada: o stamp é gravado mesmo se `pip check` reprovar

Ordem: `Install-Requirements` → `Write-VenvLock` → `Write-VenvStamp` → `Test-VenvConsistent`.
O stamp depende só do contrato "pip saiu com 0" — que é o que ele sempre significou desde a
`AX7`. Se o `pip check` reprovar, o aviso sai **no momento em que o conflito é criado**, que é
o mais útil, e o próximo lançamento engata o cache normalmente. Adiar o stamp para depois do
`pip check` recriaria o laço da `BAF2` por outro caminho. Quem quiser ver o aviso de novo roda
`-ForceEnvSetup`.

Consequência aceita: um conflito criado por `pip install`/`uninstall` **manual** dentro do
venv, depois do stamp, não é reportado no caminho rápido. É ação deliberada do usuário, e
`-ForceEnvSetup` existe para isso.

### Armadilha — `QF1`

As duas funções invocam comando nativo. Ambas usam o guard `$ErrorActionPreference =
"Continue"` + `finally`, como toda invocação nativa desde o Ciclo AX. `Test-VenvConsistent`
**captura** a saída (`$out = & ...`) em vez de descartar — é o relatório que a `BAF3` pede.

## O que NÃO fazer

- **Não** rodar `Test-VenvConsistent` no caminho rápido (antes do `return` da linha do stamp).
  É exatamente a `BAF1`.
- **Não** deixar `Test-VenvConsistent` influenciar `$healthy`, o stamp ou a decisão de
  reinstalar. É exatamente a `BAF2`.
- **Não** tornar a reprovação do `pip check` fatal (`throw`). O encoder pode funcionar
  perfeitamente com um conflito de versão que só afeta um pacote não usado; `Warn` é o nível
  certo.
- **Não** mexer em `$Config = $null` de `Install-Requirements:183` / `Initialize-Environment:276`.
  Parece design frágil, mas os 4 testes de `Context 'quando o venv nao existe'`
  (`tests/launcher.Tests.ps1:351-372`) chamam `Initialize-Environment` **sem** `-Config` e
  dependem disso. Fora de escopo.
- **Não** tocar em nada além de `Test-VenvHealthy`, `Test-VenvConsistent` (nova) e o trecho
  de `Initialize-Environment` mostrado. `Test-FfmpegCapabilities`, `Resolve-SystemPython`,
  `Open-LauncherTabs`, o escape do `wt` (AZ1) — intocados.
- **Não** relaxar asserção para ficar verde. As mudanças de teste autorizadas estão na `BB2`.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| **BB1** | (a) `Test-VenvHealthy` volta a rodar **só** `import sys` (remover as linhas `:229` e o segundo `$LASTEXITCODE`; o `return` passa a ler o exit do `import sys`). (b) Criar `Test-VenvConsistent` logo abaixo, conforme § Desenho, devolvendo `[PSCustomObject]@{Ok; Report}`. (c) Em `Initialize-Environment`: ajustar a mensagem da `:297` para `... (orfao ou corrompido) - reinstalando dependencias.`; depois de `Write-VenvStamp`, chamar `Test-VenvConsistent` e emitir o `Warn` com `$consistency.Report` quando `Ok` for `$false` | executor | `launcher.ps1` | `Select-String 'pip check' launcher.ps1` retorna **1** linha, dentro de `Test-VenvConsistent`; `Test-VenvHealthy` não contém `pip`; `Parser::ParseFile` sem erros |
| **BB2** | Testes — ver § "Mudanças na suíte" | executor | `tests/launcher.Tests.ps1` | suíte verde nos 3 jobs Pester; contagem sobe de 110 para ≥ 116 |
| **BB3** | Registrar `BAF1..BAF3` no `FINDINGS.md` com fechamento apontando para este ciclo, e anexar `## Ciclo BB` ao `STATE.md` | Orquestrador | `.claude/memory/FINDINGS.md`, `.claude/memory/STATE.md` | — |

## Mudanças na suíte (especificação da `BB2`)

Todas em `tests/launcher.Tests.ps1`. Nenhuma asserção existente muda; só se **acrescenta**.

**Contrato de dot-source (`:43-67`).** Acrescentar `Test-VenvConsistent` à lista `-ForEach`.

**`Describe 'Initialize-Environment'` (`:232-394`).** Acrescentar
`Mock Test-VenvConsistent { return [PSCustomObject]@{ Ok = $true; Report = '' } }` ao
`BeforeAll` dos **5 Contexts existentes** (`:242`, `:280`, `:317`, `:339`, `:376`). Sem esse
mock, a função real tentaria `& 'VENV\Scripts\python.exe' -m pip check` num caminho que não
existe. Os 14 testes existentes seguem verdes sem outra edição.

**Asserções novas nos Contexts existentes:**

- `Context 'venv existe, saudavel, stamp confere'` (`:240`) — **`It 'nao roda pip check no
  caminho rapido'`**: `Should -Invoke Test-VenvConsistent -Times 0 -Exactly`. **É a asserção
  que fecha a `BAF1`.**
- `Context 'venv existe, saudavel, stamp difere'` (`:278`) — `It 'roda pip check uma vez
  depois do install'`: `Should -Invoke Test-VenvConsistent -Times 1 -Exactly`.
- `Context 'venv existe mas nao esta saudavel'` (`:315`) — `It 'roda pip check depois de
  reinstalar'`: `Test-VenvConsistent` 1×.
- `Context 'quando o venv nao existe'` (`:337`) — `It 'roda pip check depois da primeira
  instalacao'`: `Test-VenvConsistent` 1×.

**Context novo — `'pip check reprova depois do install'`:** mocks iguais ao Context
`'stamp difere'`, mas `Mock Test-VenvConsistent { return [PSCustomObject]@{ Ok = $false;
Report = 'foo 1.0 requires bar>=2, but you have bar 1.5.' } }`. Quatro asserções:

1. `It 'instala exatamente uma vez (sem laco)'` — `Install-Requirements` 1× **`-Exactly`**.
   **É a asserção que fecha a `BAF2`.**
2. `It 'grava o stamp mesmo assim'` — `Write-VenvStamp` 1×.
3. `It 'avisa com o relatorio do pip check'` — `Should -Invoke Write-LauncherLog -Times 1
   -Exactly -ParameterFilter { $Level -eq 'Warn' -and $Message -match 'pip check' -and
   $Message -match 'bar>=2' }`. **É a asserção que fecha a `BAF3`.**
4. `It 'ainda devolve o interpretador'` — retorno casa `python`.

**Superfícies que continuam NÃO cobertas, de propósito:** `Test-VenvHealthy` e
`Test-VenvConsistent` reais invocam `& $variavelComCaminho`, que o Mock do Pester não
engancha — limitação documentada no cabeçalho do arquivo (`:1-16`). **Acrescentar
`Test-VenvConsistent` à lista desse comentário.**

## Critérios de aceite

1. **Suíte verde nos 3 jobs Pester** (`ubuntu-latest`, `windows-latest` pwsh 7, `Windows
   PowerShell 5.1`) + `lint` + `tests`. Contagem ≥ 116.
2. **`Select-String 'pip check' launcher.ps1` retorna uma linha**, em `Test-VenvConsistent`.
3. **`QF1` não volta:** as duas funções têm o guard com `finally`.
4. **Nenhuma construção só-pwsh-7** (`??`, ternário, `&&`, `||`, `-Parallel`, `-AsHashtable`).
5. **`git diff main --stat` toca exatamente 2 arquivos:** `launcher.ps1`,
   `tests/launcher.Tests.ps1`. `.claude/memory/*` em commit próprio.
6. **Verificação manual do usuário**, não testável em CI: segundo lançamento consecutivo
   volta a ser rápido (sem `pip check` no log); depois de `-ForceEnvSetup`, o log mostra o
   install e, se houver conflito no venv real, uma linha amarela com o texto do `pip check`.

## Notas de execução

- **Branch:** `claude/launcher-encoder-architecture-jzyyu8` já teve os PRs #57, #58 e #59
  merjados. Recriar a partir do `main` (`git fetch origin main && git checkout -B <branch>
  origin/main`) antes do primeiro commit; PR **novo**.
- Sem `pwsh` no container do Orquestrador: **quem valida é o CI**. O executor roda
  `Invoke-Pester -Path ./tests` localmente se tiver PowerShell; senão, confia nos 3 jobs.
- Commits: `BB1` → `BB2` → `BB3` (`[skip ci]` só no de memória).
- **Nunca `git add -A` nem `git add .`.** Adicionar por caminho explícito.
- Ao anexar ao `STATE.md`, começar com `## Ciclo BB` e cabeçalho de tabela.
- Retorno: **ponteiro + veredito**, uma linha por ID + SHA.
