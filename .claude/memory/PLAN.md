<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BA: `Test-VenvHealthy` passa a rodar `pip check`

Data: 2026-09-07 | Ciclo: BA | Origem: pedido direto do usuário, pós-Ciclo AZ. Ciclo anterior: AZ (fechado, `04eb4ff`).

## Diagnóstico

`Test-VenvHealthy` (`launcher.ps1:221-233`, introduzida na `AX7`) hoje só confere se o
interpretador liga: `& $VenvPython -c "import sys"`. Isso pega um venv órfão (repo movido,
`pyvenv.cfg` com `home` obsoleto — o caso que a `AX7` documentou), mas **não pega** um venv onde
`python.exe` inicia normalmente só que os pacotes instalados estão inconsistentes entre si
(dependência quebrada por instalação parcial, versões conflitantes, um `pip install` anterior
interrompido no meio). Nesse caso, `Initialize-Environment` vê "saudável + stamp confere" e
**pula** `Install-Requirements`, deixando o ambiente quebrado sem chance de auto-correção — só
descoberto quando o encoder falhar em runtime, por um erro que não aponta para a causa raiz.

`pip check` (`python -m pip check`) verifica se as distribuições instaladas têm dependências
compatíveis entre si — exatamente a classe de defeito que `import sys` sozinho não detecta.
Pedido do usuário: usar isso como segundo sinal de saúde, além do `import sys` já existente.

## Desenho

Uma mudança, um arquivo: `Test-VenvHealthy` roda `import sys` como já faz (ainda o primeiro
guard — se o interpretador nem liga, nem vale a pena tentar `pip check`) e, só se isso passar,
roda `& $VenvPython -m pip check` sob o mesmo guard de stderr do § Armadilha (padrão já usado em
toda invocação nativa do ciclo AX: `$ErrorActionPreference = "Continue"` + `finally` restaura).
Retorna `$true` só se **as duas** saírem com exit 0.

```powershell
function Test-VenvHealthy {
    param([Parameter(Mandatory)][string]$VenvPython)
    if (-not (Test-Path $VenvPython)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython -c "import sys" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { return $false }
        & $VenvPython -m pip check 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    return ($LASTEXITCODE -eq 0)
}
```

Nenhuma outra função muda. `Initialize-Environment` já sabe o que fazer quando
`Test-VenvHealthy` devolve `$false` (reinstala via `Install-Requirements` + `Write-VenvLock`,
lógica da `AX7` — inalterada): um `pip check` quebrado agora **aciona a mesma reparação
automática** que um venv órfão já acionava, o que resolve o problema do usuário sem precisar
tocar em `Initialize-Environment`.

## O que NÃO fazer

- Não adicionar flag nova (`-SkipPipCheck` ou similar) — não foi pedido, e `-SkipEnvSetup`
  já cobre "pular a checagem inteira" para quem quiser.
- Não tocar em `Initialize-Environment`, `Get-RequirementsStamp`, `Install-Requirements` nem em
  `launch-config.json` — a reação a `Test-VenvHealthy -eq $false` já existe e já é a certa.
- Não adicionar teste Pester novo para a chamada real de `pip check` — `Test-VenvHealthy` já é
  superfície não-testável por mock (`& $variavelComCaminho`, mesma limitação documentada no
  cabeçalho de `tests/launcher.Tests.ps1`); os testes de `Describe 'Initialize-Environment'`
  mockam `Test-VenvHealthy` inteira e não são afetados pela mudança interna.
- Não trocar a ordem (`pip check` antes de `import sys`) — se o interpretador não liga, rodar
  `pip check` é desperdício e pode gerar um erro mais confuso que o atual.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| BA1 | Em `launcher.ps1`, função `Test-VenvHealthy` (linhas ~221-233): adicionar a chamada `& $VenvPython -m pip check 2>&1 \| Out-Null` dentro do mesmo bloco `try`, só executada se `import sys` já tiver saído com exit 0 (`if ($LASTEXITCODE -ne 0) { return $false }` logo após a primeira chamada); o `return` final passa a refletir o exit code do `pip check` | executor | `launcher.ps1` | `Select-String -Pattern 'pip check' launcher.ps1` retorna 1 linha; `Parser::ParseFile` sem erros; suíte Pester (`tests/`) continua 110/110 sem edição de teste |

## Critérios de aceite

- Venv saudável e com pacotes consistentes → `Test-VenvHealthy` `$true` (comportamento
  observável idêntico ao de hoje no caminho feliz).
- Venv onde `import sys` já falha → `Test-VenvHealthy` `$false` sem nunca chamar `pip check`
  (guard de curto-circuito).
- Venv onde `import sys` funciona mas `pip check` acusa inconsistência → `Test-VenvHealthy`
  `$false` (comportamento novo — antes seria `$true`).
- `Initialize-Environment` não muda de código, mas herda o comportamento novo: um `pip check`
  quebrado agora aciona reinstalação automática na próxima execução do launcher.
- Suíte Pester (`Invoke-Pester -Path tests/ -CI`) continua 110/110, sem tocar nenhum arquivo de
  teste.

## Notas de execução

- Verificação real (rodar contra um venv de verdade com um `pip check` quebrado de propósito)
  fica a critério de quem implementa, se tiver como simular sem afetar o venv real do projeto
  (ex.: copiar o venv para uma pasta temporária e desinstalar uma dependência transitiva antes
  de testar) — não é obrigatório; sintaxe + suíte verde bastam para o `done`.
- Ao anexar ao `STATE.md`, começar com `## Ciclo BA` e cabeçalho de tabela.
- Retorno ao Orquestrador: ponteiro + veredito, uma linha por ID + confirmação de sintaxe.
