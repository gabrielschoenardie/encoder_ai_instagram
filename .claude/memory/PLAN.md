<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — P3HF2: máscara MCTF usa o FFmpeg resolvido pelo projeto

Data: 2026-11-18 | Branch: `fix/p3hf2-mctf-ffmpeg` (base `3632131` = `origin/main`). Agente alvo: **`executor`**.

Origem: `FINDINGS.md` P3HF2; `docs/reviews/tui-review.md` § 3 prioridade 3, § 4 critério P3HF2, § 5.2. Autorizado pelo usuário em 2026-11-18.

## Regras

- **Sem commit/push/`git add`/merge.** Sem `reset --hard`, `clean`, `stash`, `restore` em arquivo que você não criou. Não mexer na `main`.
- Arquivos permitidos: `enhance_visualizer.py`, `enhance/test_mctf_ffmpeg_resolution.py` (novo), e os registros: `.claude/memory/STATE.md` (append § P3HF2), `.claude/memory/FINDINGS.md` (só a linha P3HF2), `docs/reviews/tui-review.md` (só a célula de status da linha P3HF2 em § 5.2).
- Fora do escopo: N-1 (`_temp_path`), launcher/smokes, `ui/binaries.py` (reusar, não alterar), `Reels_Encoder_v2_FINAL.py`, `tools/compare_frames.py`. Outro bug → FINDINGS.md.
- Sem refactor, sem abstração nova além do helper abaixo, sem comentário narrativo.

## Tarefas

| ID | arquivos | tarefa |
| --- | --- | --- |
| P3HF2-1 | `enhance/test_mctf_ffmpeg_resolution.py` (novo) | Escrever os testes **primeiro** e confirmar que falham contra o literal `"ffmpeg"` (registrar o vermelho em STATE.md). Reaproveitar o padrão de `enhance/test_mctf_tui_quiet.py` (`_Cap`, `_Proc`, `monkeypatch` de `V.cv2.VideoCapture` e `subprocess.Popen`, `show_progress=False`). Usar o **resolvedor real** (`ui.binaries`), isolando o ambiente: `monkeypatch.setattr(B, "_proj_dir", lambda: str(tmp_path))` (a pasta `bin/` fica em `tmp_path/bin`), `monkeypatch.setenv`/`delenv("REELS_FFMPEG")`, `monkeypatch.setenv("PATH", <dir tmp>)`. Binários falsos = arquivos vazios criados com o nome de `B._exe_name("ffmpeg")` (com `chmod 0o755`); nunca executar FFmpeg real, sem download, sem depender do FFmpeg global. Casos: (a) só `bin/` (PATH vazio/sem ffmpeg, sem env) → `args[0]` é o `bin/ffmpeg(.exe)`; (b) `REELS_FFMPEG` aponta arquivo fora de `bin/` e `bin/` também tem um → vence o env; (c) só PATH (sem `bin/`, sem env) → `args[0]` é o do PATH; (d) caminho contendo espaços (via `REELS_FFMPEG` e via `bin/` em `tmp_path/"pasta com espaço"`) → `args[0]` é a string exata, **um único elemento** da lista, sem `shell=True`; (e) nada disponível → `args[0]` é o fallback do resolvedor (`B.resolve_binary` sem nada = `ffmpeg.exe` no Windows / `ffmpeg`); (f) preservação: para ambos os writers (`deband` e `sharpen`), `args[1:]` é exatamente `["-y","-f","rawvideo","-pix_fmt","gray","-video_size","16x16","-r","30.0","-i","pipe:0","-c:v","libx264","-pix_fmt","yuv420p","-crf","0","-preset","ultrafast",<out_path>]` e os kwargs `stdin=PIPE, stdout=DEVNULL, stderr=DEVNULL` seguem iguais; (g) env alterado **depois** do import de `enhance_visualizer` é respeitado (resolução em tempo de chamada, não de import). |
| P3HF2-2 | `enhance_visualizer.py` | Correção mínima: helper de módulo `_ffmpeg_bin() -> str` que faz `from ui.binaries import resolve_binary` **dentro** da função (import local; sem importar `Reels_Encoder_v2_FINAL` nem o motor; `ui.binaries` é stdlib pura, sem ciclo) e retorna `resolve_binary("ffmpeg")`; em `ImportError` retorna `"ffmpeg"` (mesmo padrão tolerante de `ebu_meter.py:35-40`). Em `generate_mctf_mask_video`, chamar `_ffmpeg_bin()` **uma vez por chamada** (antes de `_open_ffmpeg_writer`) e usar o resultado no lugar do literal `"ffmpeg"` na linha ~467. Não alterar nenhum outro argumento, o pipe, `stdin/stdout/stderr`, nem o fluxo. Não usar `ui.binaries.FFMPEG` (constante fixada no import quebraria (g)). |
| P3HF2-3 | — | Rodar em foreground com o venv do projeto: `venv\Scripts\python.exe -m pytest enhance/test_mctf_ffmpeg_resolution.py enhance/test_mctf_tui_quiet.py ui/test_binaries.py -q`, depois `venv\Scripts\python.exe -m pytest -q` (suíte inteira), `venv\Scripts\python.exe -m ruff check .`, `git diff --check`. Números reais em STATE.md § P3HF2. |
| P3HF2-4 | registros | `FINDINGS.md`: status da linha P3HF2 → `corrigido (fix/p3hf2-mctf-ffmpeg, pendente de merge)`. `tui-review.md` § 5.2: célula de status da linha P3HF2 → `Corrigido na branch (aguarda merge)`. Nenhuma outra linha/arquivo. |

## Retorno

Ponteiro + veredito: status por ID, uma linha cada; detalhe em `.claude/memory/STATE.md` § P3HF2. Listar arquivos tocados e qualquer limitação encontrada.
