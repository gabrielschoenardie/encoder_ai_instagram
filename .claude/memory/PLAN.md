<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AY: `fetch_ffmpeg.ps1` trata "já instalado" do winget como falha fatal

Data: 2026-09-07 | Ciclo: AY | Origem: verificação manual do usuário pós-merge do Ciclo AX (PR #59). Ciclo anterior: AX (fechado, `bd43bc1`).

## Diagnóstico (root cause, `superpowers:systematic-debugging` Fase 1-2)

Repro relatado pelo usuário:

```
> .\launcher.ps1
[ERRO]  ffmpeg.exe nao encontrado em: ...\bin\ffmpeg.exe
Rode .\tools\fetch_ffmpeg.ps1 para baixar o FFmpeg.

> .\tools\fetch_ffmpeg.ps1
Instalando FFmpeg 6.1 via winget...
Foi encontrado um pacote existente já instalado. Tentando atualizar...
Nenhuma atualização disponível foi encontrada.
Exception: ...\tools\fetch_ffmpeg.ps1:32
Falha ao instalar FFmpeg via winget. Codigo de saida: -1978335189
```

O primeiro erro é **comportamento correto**: `bin/ffmpeg.exe` não existe nesta árvore (`bin/`
é gitignored) e o launcher aponta certo para o script de bootstrap — não é bug do Ciclo AX,
não toca nenhum arquivo do ciclo.

O segundo é bug real, pré-existente, só descoberto agora pela verificação manual. Em
`tools/fetch_ffmpeg.ps1:24-32`:

```powershell
& winget install -e --id BtbN.FFmpeg.GPL.6.1 --source winget `
    --accept-source-agreements --accept-package-agreements

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar FFmpeg via winget. Codigo de saida: $LASTEXITCODE"
}
```

`-1978335189` como `UInt32` é `0x8A15002B` — código documentado do WinGet
`APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE` ("nenhuma atualização aplicável encontrada"),
devolvido quando o pacote **já está instalado** e não há versão mais nova. Bate exatamente com
a mensagem que o próprio winget imprimiu ("Nenhuma atualização disponível foi encontrada") —
não é falha de instalação, é "nada a fazer, já está instalado". O `throw` na linha 31-32 trata
qualquer saída não-zero como fatal e aborta **antes** do script chegar ao bloco de busca e
cópia dos binários (linhas 41-95), que é o que realmente resolveria o problema: encontrar o
`ffmpeg.exe` já instalado (por este mesmo script, em sessão anterior — ver `STATE.md` § Ciclo Q,
`Q9.2`) e copiá-lo para `./bin`.

**Padrão de referência dentro do próprio arquivo:** o script já tem, nas linhas 97-99, o
verificador de sucesso correto — `if ($foundCount -ne $exes.Count) { throw ... }` — que confere
se os 3 binários foram *de fato* encontrados e copiados, independente do que o winget quis dizer
com seu código de saída. Esse é o sinal de verdade certo; o `throw` da linha 31-32 é redundante
e, neste caso, ativamente incorreto.

## Desenho

Fix mínimo, uma mudança: trocar o `throw` incondicional de `$LASTEXITCODE -ne 0` por um aviso
não-fatal (`Write-Host ... -ForegroundColor Yellow`), e deixar o script sempre prosseguir para o
bloco de busca/cópia. O verificador de sucesso real (`$foundCount -ne $exes.Count`, linha
97-99, **não muda**) continua sendo quem decide se o script falhou de verdade — se o winget
falhou por um motivo real (rede, pacote não existe), os binários não serão encontrados em
lugar nenhum e esse `throw` já existente pega o caso.

Sem refactor, sem função nova, sem teste novo (o arquivo é um script top-level sem guard de
dot-source e sem separação em funções — dar cobertura Pester a ele exigiria refatorá-lo em
funções primeiro, fora do escopo deste bugfix pontual).

## O que NÃO fazer

- Não hardcodar o número mágico `-1978335189`/`0x8A15002B` numa comparação — códigos de saída
  do winget podem variar por versão/locale; a estratégia é **não confiar no exit code do winget
  para decidir sucesso**, e sim no que o script já verifica depois (binários presentes).
- Não tocar no bloco de busca/cópia (linhas 35-95) nem no verificador final (97-99).
- Não adicionar retry, `winget list` prévio, nem lógica de detecção de "já instalado" —
  desnecessário: o bloco de busca já resolve isso.
- Não criar teste Pester novo para este arquivo (ver Desenho).
- Não tocar `launcher.ps1` nem nada do Ciclo AX — já mesclado e fechado.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AY1 | Em `tools/fetch_ffmpeg.ps1:31-32`: trocar `if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar FFmpeg via winget. Codigo de saida: $LASTEXITCODE" }` por um aviso não-fatal (`Write-Host` amarelo citando o `$LASTEXITCODE`) que não interrompe o script; nenhuma outra linha muda | executor | `tools/fetch_ffmpeg.ps1` | `Select-String -Pattern 'throw' tools/fetch_ffmpeg.ps1` só retorna a linha 98 (o `throw` do `$foundCount`, intacto); `git diff --stat` toca só este arquivo, poucas linhas |

## Critérios de aceite

- `winget install` retornando `0x8A15002B`/`-1978335189` (já instalado) não aborta o script;
  ele prossegue, encontra os binários já instalados no disco e copia para `./bin`.
- `winget install` falhando de verdade (ex.: sem rede, id inexistente) ainda resulta em erro
  claro — via o `throw` já existente do `$foundCount` (linha 97-99), citando quais binários
  não foram encontrados.
- `python -m py_compile` não se aplica (arquivo `.ps1`); `Parser::ParseFile` do PowerShell sem
  erros de sintaxe.
- Nenhuma outra linha do arquivo muda além do bloco `if ($LASTEXITCODE -ne 0)`.

## Notas de execução

- Verificação real (rodar `.\tools\fetch_ffmpeg.ps1` de fato) fica para o usuário — não há
  winget disponível no ambiente do executor. Documentar no STATE.md a limitação.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AY` e cabeçalho de tabela.
- Retorno ao Orquestrador: ponteiro + veredito, uma linha por ID + confirmação de sintaxe.
