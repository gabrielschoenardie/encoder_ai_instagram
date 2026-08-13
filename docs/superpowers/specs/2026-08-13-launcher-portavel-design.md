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
- **Sem URL inventada.** A fonte exata do build "portátil" do Windows
  Terminal não é definida neste spec — é pesquisada e fixada (versão +
  checksum) na implementação. Se nenhuma fonte confiável existir, o achado é
  reportado, não inventado.
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
3. **"Windows Terminal Portable"** não é um artefato oficial da Microsoft
   (WT é distribuído via MSIX/Store, com dependência do Windows App SDK
   runtime — não é um `.exe` solto). O fetch script vai depender de um
   repack de terceiros, com risco de manutenção/segurança maior que o
   `fetch_ffmpeg.ps1` (que usa winget, canal oficial). Ver "Riscos" abaixo.

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
└── bin/wt.exe                    ← criado em runtime (já coberto por bin/.gitignore)
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
   - `bin/wt.exe` — opcional; ausência não é erro, só desvia pro fallback do
     passo 6.
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
  `wt.exe`) + defaults.
- **`tools/fetch_wt_portable.ps1`** — baixa e valida um build portátil do
  Windows Terminal pra `./bin/wt.exe` (+ arquivos de suporte que a
  implementação real exigir). Segue o padrão de
  `tools/fetch_ffmpeg.ps1` (raiz do projeto = pai de `tools/`, mensagens
  color-coded, validação pós-install).

### Falhas tratadas

| Cenário | Ação |
| --- | --- |
| Python não encontrado | Mensagem clara, instrui instalar Python 3.11+ |
| Criação do venv falha | Sugere `-SkipEnvSetup` pra reusar venv existente; diagnóstico |
| `requirements.txt` ausente | Erro claro com o path esperado |
| `pip install` falha | Mostra stderr do pip, sugere causas comuns (disco, permissão) |
| FFmpeg/FFprobe ausentes | Hard fail, instrui `.\tools\fetch_ffmpeg.ps1` |
| Windows Terminal ausente | Fallback silencioso pra janelas PowerShell separadas, não é erro |

## Riscos

**Windows Terminal "portátil" depende de um repack de terceiros.** Não há
artefato zero-instalação oficial da Microsoft equivalente ao FFmpeg estático.
A implementação de `fetch_wt_portable.ps1` precisa:

1. Pesquisar uma fonte real, mantida, com histórico de releases —
   documentar a URL exata + versão + SHA256 no próprio script e em
   `bin/README.md`.
2. Se nenhuma fonte confiável for encontrada, reportar o achado em vez de
   inventar uma URL ou usar um mirror não verificável.

Mesmo que essa etapa falhe ou o binário baixado não rode fora do MSIX
sandbox (dependência do Windows App SDK runtime), o `launcher.ps1` continua
funcional: o fallback do passo 6 (duas janelas PowerShell) não depende de
`wt.exe` existir.

## Documentação

Atualização aditiva, sem reescrever texto existente:

- `README.md` — nova subseção curta ("Uso portátil / `launcher.ps1`").
- `MANUAL_INSTALACAO.txt` — nota apontando pro novo fluxo, sem alterar os
  passos de instalação via `pip` já documentados.
- `bin/README.md` — parágrafo sobre `wt.exe` ao lado do existente sobre
  FFmpeg (mesmo padrão: como obter, onde fica, o que acontece se faltar).

## Validação

Sem framework de teste novo (não há convenção de Pester no repo). Execução
real numa máquina Windows: venv novo (timing), reuso de venv existente,
validação de binários (incluindo o hard-fail esperado hoje, já que `bin/`
não tem `ffmpeg.exe` commitado), os 5 perfis montando o comando certo, o
caminho com `wt.exe` presente e o fallback sem `wt.exe`, cada falha tratada
da tabela acima disparada de propósito, e cada flag (`-Debug`,
`-SkipValidation`, `-SkipEnvSetup`) isolada. Checklist pass/fail por etapa
documentado em `.claude/memory/STATE.md`, evidência real colada (não
parafraseada), seguindo `superpowers:verification-before-completion`.
