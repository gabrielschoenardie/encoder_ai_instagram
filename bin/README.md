# bin/ — FFmpeg embarcado (portabilidade)

Este projeto **não exige um FFmpeg instalado no sistema**. Se você colocar os
binários do FFmpeg aqui em `./bin`, o encoder os usa automaticamente. O resolver
(`ui/binaries.py`) segue esta ordem:

1. `./bin` (binários embarcados) — **vence**
2. `PATH` do sistema
3. nome puro (`ffmpeg`), como último recurso, só para mensagens de erro legíveis

Versão recomendada: **FFmpeg 6.1**.

## Arquivos esperados

- **Windows:** `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
- **macOS / Linux:** `ffmpeg`, `ffprobe`, `ffplay` (com permissão de execução, `chmod +x`)

`ffmpeg` e `ffprobe` são **obrigatórios**. `ffplay` é **opcional** (apenas para o
monitor visual EBU); sua ausência nunca quebra um encode.

## Como obter os binários

### Windows — automático (recomendado)

```powershell
./tools/fetch_ffmpeg.ps1
```

O script instala o FFmpeg 6.1 via `winget` e copia os três `.exe` para cá.

### Windows — manual

```powershell
winget install -e --id BtbN.FFmpeg.GPL.6.1
```

Depois copie `ffmpeg.exe`, `ffprobe.exe` e `ffplay.exe` do diretório instalado
para esta pasta `./bin`.

### macOS

```bash
brew install ffmpeg
```

Isso instala no `PATH` (o resolver encontra automaticamente). Se preferir
embarcar, copie os binários `ffmpeg`, `ffprobe`, `ffplay` para cá e rode
`chmod +x ./bin/*`.

### Linux

```bash
sudo apt install ffmpeg
```

Ou baixe um build estático (ex.: johnvansickle.com) e copie `ffmpeg`,
`ffprobe`, `ffplay` para esta pasta com `chmod +x ./bin/*`.

## Versionamento

Os binários **não são versionados** no git (veja `bin/.gitignore`) — cada
máquina traz os seus. Apenas este `README.md` e o `.gitignore` ficam no repo.

## Windows Terminal portátil (opcional)

`launcher.ps1` abre 2 abas (Setup + Encode) usando o Windows Terminal se
`./bin/WindowsTerminal/wt.exe` existir. Sem ele, cai automaticamente em
duas janelas PowerShell separadas — não é obrigatório.

### Como obter

```powershell
./tools/fetch_wt_portable.ps1
```

Baixa a distribuição portátil **oficial** do Windows Terminal (ZIP
"unpackaged" publicado em
[`github.com/microsoft/terminal/releases`](https://github.com/microsoft/terminal/releases),
documentado em
[Microsoft Learn](https://learn.microsoft.com/en-us/windows/terminal/distributions)),
confere o SHA256 antes de extrair, e extrai a pasta inteira (não é só um
`.exe` — `wt.exe` precisa dos DLLs/recursos ao lado) para
`./bin/WindowsTerminal/`.

Requer Windows 10 19041+ ou Windows 11.
