<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo R: esclarecer QF2 (fallback ffmpeg PATH) em launcher.ps1

Data: 2026-08-14 | Ciclo: docs | Origem: `FINDINGS.md` § "Ciclo Q" (QF2)

**Decisão do usuário:** QF2 não é bug de comportamento — o fallback
`bin/ffmpeg.exe` → PATH do sistema (`ui/binaries.py::resolve_binary`) já é o
comportamento desejado de resiliência/portabilidade. `-SkipValidation` só
pula a checagem local (`Test-Path`) feita por `Resolve-Binaries` em
`launcher.ps1`; não desativa o fallback do encoder ao FFmpeg do PATH. Sem
mudança de comportamento — só comentários/documentação esclarecendo o
escopo real da flag, pra não reabrir essa confusão numa próxima validação.

## R1 — comentário no parâmetro e no bloco de skip em `launcher.ps1`

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| R1a | No bloco `param()` (linha ~12), acrescentar comentário de uma linha acima de `[switch]$SkipValidation` explicando que a flag só pula a checagem local de `bin/ffmpeg.exe`/`bin/ffprobe.exe` feita por `Resolve-Binaries` — não impede o encoder de achar FFmpeg no PATH do sistema via `ui/binaries.py::resolve_binary` (que já prefere `bin/` e cai pro PATH como fallback). | `executor` | `launcher.ps1` | comentário presente, sem mudança de código/lógica |
| R1b | No bloco `if ($SkipValidation) { ... }` (linha ~267-274), acrescentar comentário de uma linha citando o achado QF2: se houver FFmpeg no PATH global (ex.: instalado via `tools/fetch_ffmpeg.ps1`/winget), o encoder ainda vai encontrar e usar esse binário mesmo sem o `bin/ffmpeg.exe` local — `-SkipValidation` não força isolamento estrito. | `executor` | `launcher.ps1` | comentário presente, sem mudança de código/lógica |

## Verificação final

| ID | tarefa | agente alvo | critério de done |
|----|--------|-------------|-------------------|
| R2 | `git diff launcher.ps1` mostra só as 2 linhas de comentário adicionadas (nenhuma linha de código executável tocada) | `executor` | diff conferido, colado no `STATE.md` |

## Notas de execução

- Não alterar `ui/binaries.py`, `tools/fetch_ffmpeg.ps1` ou qualquer lógica de
  resolução de binário — essas opções foram descartadas pelo usuário.
- Não tocar em nenhum outro arquivo além de `launcher.ps1`.
- Ao terminar, atualizar a entrada `QF2` em `FINDINGS.md` para
  "esclarecido — sem mudança de comportamento" (linha de status, mesmo
  padrão usado para A3/H1/H2 no topo do arquivo), citando o commit.
- Retorno: uma linha (R1a+R1b+R2 feito, sha do commit).
