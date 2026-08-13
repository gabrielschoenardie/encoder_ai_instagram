# Launcher Portátil — Bootstrap PowerShell para Reels Encoder AI

**Date:** 2026-08-13
**Status:** Approved
**Author:** gabrielschoenardie (with Claude)

## Goal

Um bootstrap PowerShell (`launcher.ps1`) que torna o encoder utilizável em
qualquer máquina Windows sem setup manual: cria um venv local, instala as
dependências, valida os binários (Python/FFmpeg/Windows Terminal) e abre o
encoder pronto pra uso — em 2 abas de terminal quando possível. Objetivo de
negócio: viabilizar a distribuição/comercialização do produto sem exigir que
o usuário final saiba configurar um ambiente Python.

Baseado no rascunho em `docs/launcher-portavel-reels-encoder.md`, revisado
contra o codebase real durante o brainstorming (ver "Divergências do rascunho
original" abaixo).

## Non-goals / constraints

- **Zero mudança em código Python existente.** `Reels_Encoder_v2_FINAL.py`,
  `ui/` (incluindo o wizard `ui/launcher.py`), `ebu_meter.py`,
  `cineon_pipeline.py` — nenhum é editado. O bootstrap é uma camada na frente,
  não uma reescrita.
- **Uma única fonte de verdade para dependências.** A instalação do venv usa
  `requirements.txt` → `pyproject.toml`, o mesmo caminho que já existe hoje
  (ver ciclo J-a em `.claude/memory/FINDINGS.md`, que fechou exatamente esse
  tipo de duplicação). Nenhum arquivo novo de lista de pacotes.
- **Nunca fixar CRF ou qualquer preset de qualidade.** O encoder decide isso
  internamente de forma adaptativa — é regra de ouro do projeto (skill
  `instagram-reels-encoder` § "Regras de Ouro — Nunca Violar"). Os perfis do
  `launch-config.json` só selecionam combinações de flags reais que já
  existem no `argparse` do encoder.
- **Sem URL inventada.** A fonte do build portátil do Windows Terminal foi
  pesquisada e verificada pelo Orquestrador durante o brainstorming (baixada,
  checksum conferido, conteúdo inspecionado) — não é um placeholder. Ver
  "Windows Terminal — distribuição portátil oficial" abaixo.
- **Sem framework de teste novo.** Validação é execução real + checklist
  manual, documentada em `STATE.md` (segue o padrão de
  `superpowers:verification-before-completion`, não Pester).

## Divergências do rascunho original

O rascunho (`docs/launcher-portavel-reels-encoder.md`) foi escrito sem
conferir contra o codebase. Três pontos não se sustentavam e foram corrigidos
durante o brainstorming:

1. **`--crf 18/23/28` não existe.** Não há flag `--crf` no `argparse` de
   `Reels_Encoder_v2_FINAL.py`; CRF é decidido internamente. Usar essa flag
   quebraria o encode (`unrecognized argument`) e violaria a regra de ouro de
   análise adaptativa sem preset fixo. Os perfis abaixo usam só flags reais.
2. **`ebu_meter.py --live` não existe.** `ebu_meter.py` é um módulo
   biblioteca (builders/parsers puros + runners, ver
   `docs/superpowers/specs/2026-06-17-ebu-meter-post-encode-qc-design.md`),
   sem `argparse` nem bloco `if __name__ == "__main__"` — não pode ser
   invocado como script. O monitor visual EBU R128 (janelas FFplay) já abre
   sozinho durante o encode via `--ebu-meter on` (default). A 3ª aba
   "Monitor" foi removida — não há comando real para ela rodar.
3. **"Windows Terminal Portable"** — o rascunho supunha um `.exe` solto
   baixado de terceiros. Pesquisa durante o brainstorming (confirmada
   baixando e inspecionando o artefato real) achou algo melhor: a Microsoft
   publica oficialmente uma distribuição "unpackaged/portable" em ZIP nos
   releases do GitHub (`microsoft/terminal`), desde a stable 1.17 — sem
   MSIX, sem Windows App SDK runtime, sem repack de terceiros. Ver "Windows
   Terminal — distribuição portátil oficial" abaixo.

`venv.lock` (do rascunho original) também mudou de papel: deixou de ser um
artefato versionado e virou puramente diagnóstico (ver "Componentes").

## Architecture

Três arquivos novos, nenhuma edição em arquivo Python rastreado:

```text
encoder_ai_instagram/
├── launcher.ps1                  ← novo — bootstrap
├── launch-config.json            ← novo — perfis/config declarativa
├── tools/
│   └── fetch_wt_portable.ps1     ← novo — setup do Windows Terminal
├── venv/                         ← criado em runtime (já no .gitignore)
├── venv.lock                     ← criado em runtime (novo padrão no .gitignore)
└── bin/WindowsTerminal/          ← criado em runtime (já coberto por bin/.gitignore)
    ├── wt.exe
    ├── WindowsTerminal.exe
    ├── *.dll, resources.pri, fontes  (todo o conteúdo do ZIP oficial — wt.exe
    │                                  não roda sozinho, precisa dos vizinhos)
    └── .portable                 ← marker que ativa o modo portátil oficial
```

### Fluxo de execução (`launcher.ps1`)

1. Resolve raiz do projeto; parseia `-InputFile`, `-Profile`, `-Debug`,
   `-SkipValidation`, `-SkipEnvSetup`.
2. Carrega `launch-config.json`.
3. **Venv** (pulado se `-SkipEnvSetup`): cria `./venv` se não existir, senão
   reaproveita. `pip install -r requirements.txt` (idempotente — mesma fonte
   de verdade de hoje). Em seguida `pip freeze > venv.lock`.
4. **Validação de binários** (pulado se `-SkipValidation`):
   - Python do venv — obrigatório, hard fail.
   - `bin/ffmpeg.exe` + `bin/ffprobe.exe` — obrigatório, hard fail, mensagem
     aponta para `.\tools\fetch_ffmpeg.ps1`.
   - `bin/WindowsTerminal/wt.exe` — opcional; ausência não é erro, só desvia
     pro fallback do passo 6.
5. **Monta comando(s):**
   - Sem `-InputFile`/`-Profile`: aba Setup = `--hardware-info`; aba Encode =
     `--ui` (abre o wizard existente, `ui/launcher.py`).
   - Com `-InputFile`/`-Profile`: aba Encode monta o comando direto do
     perfil (tabela abaixo), sem passar pelo wizard.
6. **Lança:** 2 abas (Setup, Encode) via `wt.exe` se disponível; senão, duas
   janelas PowerShell separadas via `Start-Process` (fallback automático,
   não é erro).

### Perfis (`launch-config.json`) — só flags reais do `argparse` atual

| Perfil | Flags |
| --- | --- |
| fast | `--performance speed --enhance off` |
| balanced *(default)* | `--performance balanced --enhance on --enhance-ai on` |
| quality | `--performance quality --mode 2pass --enhance on` |
| cinematic | `--cineon-pipeline on --exposure-offset +0.2 --saturation 1.05 --mode 2pass` |
| batch | `--batch <pasta> --output-dir <pasta> --enhance on` |

Nenhum perfil define `--crf` ou qualquer parâmetro de qualidade fixo.

### Componentes

- **`launcher.ps1`** — funções pequenas (venv, validação, config, montagem
  de comando, lançamento), `try`/`catch`/`finally`, output color-coded,
  log verboso em `-Debug`. `venv.lock` é escrito a cada execução mas nunca
  lido de volta para instalar nada — puramente diagnóstico, no
  `.gitignore` (evita reintroduzir a classe de bug do ciclo J-a: duas
  listas de pacotes mantidas à mão que divergem sem detecção).
- **`launch-config.json`** — os 5 perfis acima + paths (`venv`, `bin`,
  `WindowsTerminal/wt.exe`) + defaults.
- **`tools/fetch_wt_portable.ps1`** — baixa o ZIP oficial (versão e SHA256
  fixados no script, ver seção seguinte), confere o checksum antes de
  extrair, descompacta a pasta inteira para `./bin/WindowsTerminal/` e cria
  o marker `.portable`. Segue o padrão de `tools/fetch_ffmpeg.ps1` (raiz do
  projeto = pai de `tools/`, mensagens color-coded, validação pós-install).

### Falhas tratadas

| Cenário | Ação |
| --- | --- |
| Python não encontrado | Mensagem clara, instrui instalar Python 3.11+ |
| Criação do venv falha | Sugere `-SkipEnvSetup` pra reusar venv existente; diagnóstico |
| `requirements.txt` ausente | Erro claro com o path esperado |
| `pip install` falha | Mostra stderr do pip, sugere causas comuns (disco, permissão) |
| FFmpeg/FFprobe ausentes | Hard fail, instrui `.\tools\fetch_ffmpeg.ps1` |
| Windows Terminal ausente | Fallback silencioso pra janelas PowerShell separadas, não é erro |

## Windows Terminal — distribuição portátil oficial

Verificado durante o brainstorming (não é dedução — baixado e inspecionado
de verdade):

- Fonte: [`github.com/microsoft/terminal/releases`](https://github.com/microsoft/terminal/releases),
  asset `Microsoft.WindowsTerminal_<versão>_x64.zip` (existe também
  `_x86.zip`/`_arm64.zip`). Documentado oficialmente em
  [Microsoft Learn — Windows Terminal Distribution Types](https://learn.microsoft.com/en-us/windows/terminal/distributions)
  como a distribuição "Unpackaged/ZIP" (estável desde a 1.17), com variante
  "Portable" que guarda configurações do lado do `WindowsTerminal.exe` em
  vez de `%LOCALAPPDATA%`.
- Testado com a release `v1.24.11911.0`: baixado
  `Microsoft.WindowsTerminal_1.24.11911.0_x64.zip` via
  `https://github.com/microsoft/terminal/releases/download/v1.24.11911.0/Microsoft.WindowsTerminal_1.24.11911.0_x64.zip`,
  SHA256 `7691efeb71c8dd0b95536c84e366fa4cf809a42c534912f9cefa1056534383b`.
  Conteúdo confirmado por `unzip -l`: pasta única
  `terminal-1.24.11911.0/` com `wt.exe` + `WindowsTerminal.exe` +
  DLLs/resources/fontes necessários lado a lado — **não é um único `.exe`
  solto**, é a pasta inteira que precisa ir para `./bin/WindowsTerminal/`.
- Modo portátil: oficialmente suportado, ativado criando um arquivo vazio
  chamado `.portable` ao lado de `WindowsTerminal.exe` (sem essa marca, ele
  ainda funciona standalone, só grava config em `%LOCALAPPDATA%` em vez de
  local). Requer Windows 10 19041+ ou Windows 11.
- A implementação (`tools/fetch_wt_portable.ps1`) fixa uma versão e SHA256
  concretos como constantes no script (não "latest" dinâmico — mesmo
  espírito do pin de `ruff==0.14.10` no CI, ver ciclo I em
  `.claude/memory/STATE.md`), baixa, **confere o checksum antes de
  extrair**, descompacta para `./bin/WindowsTerminal/` e cria o `.portable`.

Sem repack de terceiros, sem dependência do Windows App SDK/MSIX. Mesmo
assim, se o download falhar (rede, asset renomeado numa versão futura) ou o
checksum não bater, o `launcher.ps1` continua funcional: o fallback do
passo 6 (duas janelas PowerShell separadas) não depende de `wt.exe` existir.

## Documentação

Atualização aditiva, sem reescrever texto existente:

- `README.md` — nova subseção curta ("Uso portátil / `launcher.ps1`").
- `MANUAL_INSTALACAO.txt` — nota apontando pro novo fluxo, sem alterar os
  passos de instalação via `pip` já documentados.
- `bin/README.md` — parágrafo sobre `WindowsTerminal/` ao lado do existente
  sobre FFmpeg (mesmo padrão: como obter, onde fica, o que acontece se
  faltar; cita a fonte oficial verificada acima).

## Validação

Sem framework de teste novo (não há convenção de Pester no repo). Execução
real numa máquina Windows: venv novo (timing), reuso de venv existente,
validação de binários (incluindo o hard-fail esperado hoje, já que `bin/`
não tem `ffmpeg.exe` commitado), os 5 perfis montando o comando certo, o
caminho com `WindowsTerminal/wt.exe` presente e o fallback sem ele, cada
falha tratada da tabela acima disparada de propósito, e cada flag (`-Debug`,
`-SkipValidation`, `-SkipEnvSetup`) isolada. Checklist pass/fail por etapa
documentado em `.claude/memory/STATE.md`, evidência real colada (não
parafraseada), seguindo `superpowers:verification-before-completion`.
