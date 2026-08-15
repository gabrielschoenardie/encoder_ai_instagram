<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo T: corrigir a causa real do QF1 em Windows PowerShell 5.1

Data: 2026-08-14 | Ciclo: fix | Origem: `FINDINGS.md` § QF1, continuação do
Ciclo S (commit `a9766bd`) — ver "Pergunta ao Orquestrador" em
`.claude/memory/STATE.md` § "Ciclo S" (linhas ~1051-1072). Decisão do
usuário: corrigir a causa real agora, não fechar como mitigação parcial.

## Diagnóstico corrigido (achado pelo executor no Ciclo S, empírico, não
## repetir a investigação)

O Ciclo S provou por A/B em pwsh 7.5.1 **e** Windows PowerShell 5.1 que:

- `$PSNativeCommandUseErrorActionPreference = $false` (S1a, já commitado) é
  um no-op nos dois motores desta máquina — em pwsh 7.5.1 o default já é
  `$false`; em Windows PowerShell 5.1 essa variável não existe. **Não
  resolve nada**, mas é inofensivo — não reverter, só não contar com ela.
- O crash real (`NativeCommandError`/`RemoteException` terminante a partir
  de stderr de comando nativo, quando o chamador externo funde streams via
  `*>&1`/`2>&1`) só reproduz em **Windows PowerShell 5.1**, e é o
  comportamento clássico: stderr mesclado no pipeline vira registro de erro
  no error stream, que `$ErrorActionPreference = "Stop"` promove a
  terminante — independente de qualquer feature de pwsh 7+.
- `powershell.exe -File launcher.ps1` (5.1) é o motor de produção real (é
  como o launcher é normalmente invocado num Windows sem pwsh 7 instalado),
  então este não é um edge-case a ignorar.

## Correção: isolar `$ErrorActionPreference` por chamada nativa

Padrão idiomático do PowerShell pra esse problema exato: escopar
`$ErrorActionPreference = "Continue"` só ao redor da invocação do comando
nativo (restaurando `"Stop"` logo depois via `finally`), e continuar
confiando **só** no `$LASTEXITCODE` já checado depois de cada chamada — que
já é a fonte de verdade usada em `New-ProjectVenv`/`Install-Requirements`.
Com `EAP="Continue"` durante a chamada, stderr do comando nativo vira um
erro **não-terminante** (escrito no stream de erro, não interrompe), então a
fusão de stream feita por um chamador externo (`*>&1`) deixa de ter qualquer
efeito sobre o script, nos dois motores.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| T1a | Em `New-ProjectVenv` (linha ~81), envolver `& $pythonCmd -m venv $VenvPath \| Out-Host` num bloco que seta `$ErrorActionPreference = "Continue"` antes da chamada e restaura o valor anterior num `finally` logo depois — sem mudar a lógica do `if ($LASTEXITCODE -ne 0) { throw ... }` que já vem a seguir. | `executor` | `launcher.ps1` | `git diff` mostra só a adição do wrapper try/finally em volta da linha existente |
| T1b | Mesmo padrão em `Install-Requirements` (linha ~98, `& $VenvPython -m pip install -r $reqPath \| Out-Host`) — é a chamada que causou o crash original na Task 9. | `executor` | `launcher.ps1` | idem |
| T1c | Mesmo padrão em `Write-VenvLock` (linha ~111, `& $VenvPython -m pip freeze \| Out-File ...`) — por consistência, mesmo risco em teoria (`pip freeze` também é um comando nativo que pode escrever avisos em stderr). | `executor` | `launcher.ps1` | idem |

Sugestão de forma (aplicar o mesmo padrão nos 3 pontos, adaptando a linha
interna):

```powershell
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $VenvPython -m pip install -r $reqPath | Out-Host
}
finally {
    $ErrorActionPreference = $prevEap
}
if ($LASTEXITCODE -ne 0) {
    throw "pip install falhou (exit $LASTEXITCODE). Verifique espaco em disco, permissoes e conexao."
}
```

## Verificação (reproduzir o mesmo repro do Ciclo S, agora provando que
## resolve em Windows PowerShell 5.1)

| ID | tarefa | agente alvo | critério de done |
|----|--------|-------------|-------------------|
| T2a | Reproduzir o repro sintético do Ciclo S (`STATE.md` linhas ~979-1004: comando nativo escrevendo em stderr + `exit 0`, dentro de um script que mimetiza o padrão try/finally novo, invocado com `*>&1` externo) em **Windows PowerShell 5.1** — confirmar que sobrevive (`SOBREVIVEU`), diferente do resultado "CAPTURADO_NO_SCRIPT" do Ciclo S. | `executor` | saída real colada no `STATE.md` |
| T2b | Mesmo repro em pwsh 7.5.1, confirmar que continua sobrevivendo (não deve ter regressão). | `executor` | saída real colada no `STATE.md` |
| T2c | Rodar `Install-Requirements` de verdade (pode criar um venv novo na raiz do repo principal desta vez — não há restrição de reaproveitar, e `venv/`/`venv.lock` já são gitignored) invocando o launcher (ou só a função, via dot-source) com `*>&1 \| Tee-Object` sob **powershell.exe 5.1**, confirmar que `pip install` real conclui e loga "Dependencias instaladas." sem `NativeCommandError`/`RemoteException`. Depois, remover `venv/`/`venv.lock` criados só pra este teste (a menos que o usuário queira manter). | `executor` | saída real colada no `STATE.md`, sem erro |
| T2d | Parse-check nos dois motores (mesmo comando do Ciclo S) pra garantir sintaxe válida após o try/finally. | `executor` | `PARSE_OK` nos dois |

## Notas de execução

- Não tocar em `Resolve-Binaries`, `Build-*`, `Open-LauncherTabs` — escopo é
  só as 3 funções de bootstrap de venv/pip listadas acima.
- Não reverter S1a (linha do Ciclo S) — deixar como está, é inofensiva.
- Carregar `superpowers:verification-before-completion` — colar saída real,
  nunca parafrasear.
- Ao terminar: atualizar a entrada `QF1` em `FINDINGS.md` de "corrigido —
  ciclo S (parcial, ver ciclo T)" pra "corrigido — ciclo T", citando o sha.
  Commit único: `git add launcher.ps1 .claude/memory/FINDINGS.md
  .claude/memory/STATE.md .claude/memory/PLAN.md`, mensagem no padrão do
  repo (ex.: `fix(launcher): isolar EAP por chamada nativa - resolve QF1 em
  Windows PowerShell 5.1`).
- Se a verificação real (T2a ou T2c) **não** confirmar a correção em 5.1,
  não forçar o fechamento — reportar BLOCKED com a evidência, do mesmo jeito
  honesto que o Ciclo S fez.
- Retorno: uma linha (T1+T2 feito, sha do commit, confirmação de que 5.1
  sobrevive ao repro com `*>&1`).
