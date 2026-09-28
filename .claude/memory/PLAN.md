<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo BF: cauda de áudio no Cineon e MCTF sem enhance-ai

Data: 2026-09-28 | Ciclo: BF | Origem: pedido do usuário — fechar `BDF17` e `BDF15`, que ele manteve
abertos ao fim do Ciclo BE. Design aprovado pelo usuário antes deste plano, incluindo o aviso por função
pura em vez de `parser.error()` e o `cfg.mctf = "off"` forçado no wizard. Ciclo anterior: BE (fechado, PR #67).
Evidência: `.claude/memory/FINDINGS.md` (`BDF15`, `BDF17`) e as matrizes de diagnóstico abaixo.

**Emenda de 2026-09-28, após o bloqueio da 1ª tentativa da BF1:** o teste da BF1 passou antes da correção porque
a fonte de 440 Hz deixa o `loudnorm` em modo Linear, que não tem a cauda. A causa foi refinada em duas rodadas
de medição (abaixo) e o teste da BF1 foi refeito (§ "Desenho › BF1"). A correção de código não mudou.

## Diagnóstico (medido, não presumido)

| achado | medido |
|--------|--------|
| `BDF17` áudio do Cineon mais longo que o vídeo | fonte sintética de 3 s: vídeo 3,000 s, áudio 3,100 s no Cineon CRF real; FFmpeg CRF real: áudio 3,008 s |
| **causa refinada** | a cauda de ≈0,09 s aparece **só quando o `loudnorm` do passe final cai em `Normalization Type: Dynamic` e o comando não tem `-async 1`**. Em modo Linear não há cauda. Matriz (FFmpeg 6.1.3, fim real do áudio = último pacote): senoide 1 kHz (`measured_LRA` 0,00, Dynamic) 3,008 sem filtro / **3,100** com `loudnorm` / 3,008 com `loudnorm` + `-async 1`; senoide 440 Hz (LRA 0,10, Linear) 3,008 nos três; caminho FFmpeg emulado: com `-async 1` 3,008, sem `-async 1` 3,100 |
| por que a fonte cai em Dynamic | nas senoides, o único critério que difere é `measured_LRA` = 0,00 (Dynamic) contra 0,10 (Linear); o pico não é o motivo (o ganho necessário deixaria o TP em −13,2 dBTP, abaixo do alvo). Que o FFmpeg exige LRA ≠ 0 para o modo linear é recordação do código-fonte, não verificado aqui. Em áudio real o motivo é outro (linha seguinte) |
| **alcance em áudio real** | recortes de 10 s de 3 vídeos do usuário: r1 Linear (TP −2,34 dBTP) sem cauda; **r2 e r3 caem naturalmente em Dynamic** (pico alto para o ganho: r2 TP +0,12 dBTP; r3 TP −1,24 dBTP com +4,0 dB de ganho) e ganham cauda de +0,078 s e +0,086 s; com `-async 1` o áudio termina exatamente onde termina o da fonte (10,022 e 10,014). r1 forçado a Dynamic (uma variável: `measured_TP=-0.10`) também ganha a cauda (10,100). O caminho FFmpeg já tem `-async 1` (`:2743`, `:2871`) e por isso não mostra o problema |
| alternativas medidas | `-shortest` → 3,057 (não resolve); `-t 3` → 3,000 (resolve, mas corta áudio legítimo e exige a duração exata) |
| `BDF15` no wizard | `ui/launcher.py:217-224`: `enhance_ai` e `mctf` estão sob `enhance == "on"`, mas o `mctf` não está sob `enhance_ai == "on"` |
| `BDF15` no motor | `Reels_Encoder_v2_FINAL.py:3999-4005` avisa quando `--enhance-ai on` vem sem `--enhance on`; `:4029` só roda o MCTF se `enhance_ai` for verdadeiro e **não avisa nada** quando ele é descartado |
| cobertura | `_build_pipe_cmd` é função aninhada em `run_ffmpeg_with_cineon` (sem teste unitário possível sem refatorar); os e2e do BD4 (`enhance/test_cineon_e2e.py`) chamam o Cineon com `loudnorm_enabled=False`, por isso nunca viram o `BDF17`; nenhum teste cobre o fluxo do MCTF no wizard |

## Decisões (Orquestrador, aprovadas pelo usuário)

1. **`BDF17`: paridade com o caminho FFmpeg** — `"-async", "1"` no comando de saída do Cineon. Sem `-t` nem
   `-shortest`. Pass 1 (`-an`) não muda.
2. **`BDF15`, wizard:** o toggle de MCTF só é perguntado quando `enhance_ai == "on"`; no ramo `enhance ==
   "on"` com `enhance_ai` off, `cfg.mctf = "off"` (o config reflete o que o usuário vê). Com `enhance` off o
   bloco inteiro continua pulado, como hoje.
3. **`BDF15`, motor:** aviso, não `parser.error()` — segue o precedente do `enhance-ai` (`:4000`) e cobre o
   wizard, que monta o `Namespace` direto e não passa pelo parser. Uma **função pura mínima nova**
   (`_mctf_ignored_reason`) só para o aviso novo, porque `_encode_single_file` tem ~140 linhas e roda FFmpeg,
   e testar o aviso por ali exigiria stub pesado. O bloco existente do `enhance-ai` não é tocado.
4. **Fora do ciclo:** `BDF11`/`12`/`13` (exigem A/B com o usuário). O `vbv_init` 0,9 é deliberado do usuário e
   não entra (memória `project_vbv_init_09_deliberate`). Também fora: o fato de o `loudnorm` cair em Dynamic em
   2 de 3 clipes reais (README descreve o Pass 2 como linear) — o Orquestrador registra como observação no
   `FINDINGS.md` na BF5; não é tarefa do executor.
5. **Teste da BF1 força o modo Dynamic de forma determinística** (não depende da frequência da fonte nem da
   versão do FFmpeg): ver § BF1.

Conhecimento de encoder: `skill: instagram-reels-encoder` § "Regras de Ouro" (áudio, loudnorm) e
`references/instagram-ingest-rules.md` § áudio. Não transcrever — carregar a skill.

## Desenho

### BF1 — cauda de áudio no Cineon (`BDF17`)

- **Mudança de código (só esta):** em `_build_pipe_cmd` (aninhada em `run_ffmpeg_with_cineon`,
  `Reels_Encoder_v2_FINAL.py`, localizar por nome), no bloco `if pass_number != 1:` (o que adiciona
  `-i input_file` e os dois `-map`), acrescentar `"-async", "1"` depois dos `-map`. É opção de saída (vem depois
  dos dois `-i` e antes do arquivo de saída), como no caminho FFmpeg. Não mexer em `_audio_output_args` (o
  docstring diz "idênticos nos 3 pipelines", e no caminho FFmpeg o `-async 1` também mora fora dela). Pass 1
  (`-an`) intocado.
- **Estado do working tree ao começar:** a 1ª tentativa deixou **sem commit** uma alteração em
  `enhance/test_cineon_e2e.py` (parâmetro `loudnorm` no `_encode` e um teste com a fonte de 440 Hz que passa
  antes da correção) e uma linha `BF1 blocked` no `STATE.md`. Reaproveite e ajuste; não recomece do zero.
- **Teste revisado (TDD com prova vermelha).** Em `enhance/test_cineon_e2e.py`, reusar `_source`, `_streams`,
  `_assert_av_in_sync`, o fixture `popen_calls` e o parâmetro `loudnorm` do `_encode` (default `False`, para os
  testes atuais não mudarem). Parametrizar o teste em dois modos:
  - `"linear"`: análise natural da fonte de 440 Hz (o `loudnorm` fica em Linear). Passa antes e depois — é o
    controle de que o modo Linear não tem cauda.
  - `"dynamic"`: envolver `R.analyze_audio_loudness` (`monkeypatch`): chama a original e substitui
    `stats["input_tp"]` por `"-0.10"`. Com a fonte em ≈−22 LUFS, o ganho necessário deixa o TP acima do alvo de
    −1,5 dBTP, a normalização linear fica impossível pelo pico e o FFmpeg cai em Dynamic — comportamento
    documentado do `loudnorm`, independente da frequência da fonte. **Este é o caso que reprova antes.**
  Em ambos: `_encode(..., loudnorm=True)` e `_assert_av_in_sync(out, 30)` (tolerância existente de 1/30 s; o
  esperado pós-fix é ≈0,008 s e a cauda pré-fix ≈0,09 s).
- **Blindagem contra verde vazio (obrigatória):** o teste afirma, pelo `popen_calls`, que o comando de saída do
  Cineon (o que tem `-map "1:a:0?"`) leva `-af` cujo valor contém `loudnorm`; no modo `"dynamic"`, também que
  esse valor contém `measured_TP=-0.10` (prova de que o caminho forçado foi aplicado). Se a fonte de 1 s do
  `_source` não deixar o `loudnorm` ligar, usar uma fonte de 3 s só para este teste. O caso `"dynamic"` **tem** que
  reprovar antes da mudança de código; registrar a saída vermelha no STATE. Se não reprovar, `blocked` com a
  medição (o `Normalization Type` do passe final aparece no stderr do FFmpeg com `print_format=summary`; se
  precisar dele para depurar, capture-o fora do teste, sem commitar).

### BF2 — wizard: MCTF só sob enhance-ai (`BDF15`)

- `ui/launcher.py` (localizar por `"MCTF mask video"`, ~`:222`): dentro de `if cfg.enhance == "on":`, depois
  do toggle de `enhance_ai`, perguntar o MCTF só `if cfg.enhance_ai == "on":`; `else: cfg.mctf = "off"`.
- Teste em `ui/test_launcher.py` no padrão do `test_advanced_flow_tonemap_options_match_tonemap_algorithms`
  (grava as chamadas de `ask_toggle`): com `enhance` on e `enhance_ai` off → o prompt de MCTF **não** é feito e
  `cfg.mctf == "off"`; com `enhance_ai` on → o prompt é feito e a resposta vai para `cfg.mctf`. Reprova antes.
- Depois da BF2: `ui-flow-reviewer` audita o wizard (CLAUDE.md: mexeu em seção de `ui/launcher.py`).

### BF3 — aviso do MCTF no motor (`BDF15`)

- Função de módulo em `Reels_Encoder_v2_FINAL.py`, perto de `_encode_single_file`:
  `_mctf_ignored_reason(mctf: str, enhance_ai: bool) -> Optional[str]` — devolve a mensagem quando
  `mctf == "on"` e não `enhance_ai`, senão `None`. Texto no estilo do aviso vizinho:
  `"[yellow]⚠ --mctf on requer --enhance on e --enhance-ai on. Ignorando --mctf.[/yellow]"`.
- Chamada logo antes do bloco `# ── MCTF mask video` (~`:4028`), com o `enhance_ai` local (já rebaixado a
  `False` quando `--enhance` está off): `if (msg := _mctf_ignored_reason(getattr(args, "mctf", "off"),
  enhance_ai)): console.print(msg)`. Não alterar a condição do bloco MCTF nem o bloco do `enhance-ai`.
- Testes novos em `enhance/test_mctf_requires_enhance_ai.py`, puros, sem FFmpeg: `("on", False)` → mensagem
  que cita `--mctf` e `--enhance-ai`; `("on", True)`, `("off", False)`, `("off", True)` → `None`. Reprovam antes
  (a função não existe).
- Se `Optional` não estiver importado no módulo, usar o que o arquivo já usa para anotações; não adicionar
  dependência.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| BF1 | § BF1 (teste revisado) | executor | `Reels_Encoder_v2_FINAL.py`, `enhance/test_cineon_e2e.py` | caso `"dynamic"` reprova antes e passa depois; caso `"linear"` e os e2e existentes seguem verdes; `ruff check .` limpo (0.14.10) |
| BF2 | § BF2 | executor | `ui/launcher.py`, `ui/test_launcher.py` | teste novo reprova antes e passa depois; `pytest ui/` verde |
| BF2r | auditoria do wizard após BF2 | ui-flow-reviewer | `ui/launcher.py` | veredito sem achado bloqueante |
| BF3 | § BF3 | executor | `Reels_Encoder_v2_FINAL.py`, `enhance/test_mctf_requires_enhance_ai.py` (novo) | testes reprovam antes e passam depois; suíte completa verde; `ruff check .` limpo |
| BF4 | encodes reais + validação | validador | `.claude/memory/VALIDATION.md` | ver § "Validação" |
| BF5 | fechamento: STATE/FINDINGS, memória do usuário, push, PR | Orquestrador | `.claude/memory/*` | — |

Ordem: BF1 → BF2 → BF2r → BF3 → BF4 → BF5. Nada em paralelo: BF1 e BF3 editam `Reels_Encoder_v2_FINAL.py`.
Um commit por ID.

## Validação (BF4)

Encodes pela CLI, cada um com a fonte copiada para uma pasta própria, `cwd` no scratchpad e `--ebu-meter off`.
Fim real da trilha = `pts_time + duration_time` do último pacote (`ffprobe -show_entries packet=...`).

| # | encode | fonte | o que prova |
|---|--------|-------|-------------|
| a | FFmpeg CRF, defaults | `$SP/be4/fixture_mono.mp4` | controle: o caminho FFmpeg não mudou (áudio termina em 3,008 s, como no BE4) |
| c | `--cineon-pipeline on` (CRF) | `$SP/be4/fixture_mono.mp4` (senoide 1 kHz: cai em Dynamic) | `BDF17`: áudio termina em ≤ 3,008 + 0,05 s (era 3,100) |
| d | `--cineon-pipeline on` (CRF) | recorte de **~4 s** de `$SP/be4_diag3/r3.mov` (áudio real que cai naturalmente em Dynamic) | `BDF17` em áudio real: fim do áudio ≤ fim do áudio da fonte + 0,05 s (pré-fix ≈ +0,086 s). Confirmar antes que a análise dá modo Dynamic para o recorte (`measured_TP + (−14 − measured_I) > −1,5`); se o recorte de 4 s cair em Linear, usar o de 10 s inteiro |

O Cineon é lento (a fixture de 3 s levou ~240 s no BE4): rodar (c) e (d) em background e não reiniciar encode em
andamento. Em (c) e (d), `validate_encode.sh` sem ❌ novo além do bitrate médio que já é limitação aceita
(`FINDINGS.md` § "Decisão — 2026-09-27"). Informativo, sem veredito: comparar o md5 do stream de vídeo de (c) com o
do encode Cineon do BE4 (`$SP/be4/in_c/fixture_mono_Cineon_Film.mp4`) via `ffmpeg -i <f> -map 0:v -c copy -f md5 -`;
se diferir, só reportar (a mudança é só de áudio, mas x264 com threads pode variar).

## Critérios de aceite do ciclo

1. CI verde nos jobs `lint`, `tests` (4 pernas), `pester` (2) e `pester-winps51` no PR.
2. Cineon com `loudnorm` em modo Dynamic: |áudio − vídeo| ≤ 1/30 s no e2e; nos encodes reais (c) e (d), cauda
   ≤ 0,05 s; caminho FFmpeg inalterado.
3. Wizard: sem prompt de MCTF quando `enhance_ai` está off; `cfg.mctf == "off"` nesse caso.
4. `--mctf on` sem `--enhance-ai on` (ou sem `--enhance on`) imprime o aviso e segue.
5. Nenhuma mudança de imagem nem de bitrate: BF1 mexe só em áudio; BF2/BF3 só em fluxo de opções.

## Notas de execução

- **Branch:** `claude/ciclo-bf-audio-async-mctf` (já em checkout; commit do plano `5926917` a partir de `main`
  `03cf386`). Não trocar de branch. Não fazer push — o Orquestrador faz na BF5.
- **Ambiente:** Windows local. **Usar o venv do scratchpad** (Python 3.13.3, PyAV 18.1.0, pytest,
  pytest-timeout, `ruff==0.14.10`, projeto instalado em modo editável):
  `C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-Documents-GitHub-encoder-ai-instagram\8689ce49-9161-4059-9952-44798e5cb700\scratchpad\venv-be\Scripts\python.exe`.
  Não usar o Python de sistema (PyAV 16.1.0, abaixo do piso `av>=17.0.0`) nem o `venv/` do projeto (sem pytest;
  é o venv do launcher do usuário). FFmpeg: `./bin/ffmpeg.exe` resolve antes do PATH (winget 6.1.3).
  Suíte canônica: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q --timeout=120`. Baseline no
  HEAD: **579 passed** com FFmpeg. A rodada "sem FFmpeg" (worktree descartável sem `bin/` + PATH sem FFmpeg) é do
  Orquestrador na BF5; o executor não precisa simulá-la e **não deve** renomear nem mover nada em `./bin/`.
- **Nada na raiz do repo:** testes usam `tmp_path`; qualquer log/arquivo gerado por FFmpeg vai para o
  scratchpad ou `tmp_path` (o Ciclo BE deixou um arquivo `C` na raiz por um `log_path` do libvmaf com
  `C:/...`). Conferir `git status` no fim.
- **Commits:** um por ID, mensagem convencional em português, terminando com os trailers
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` e
  `Claude-Session: https://claude.ai/code/session_01VZwxJYrv8iQgzUjZcgjEgk`.
- **Nunca `git add -A` nem `git add .`** — adicionar por caminho explícito. Não commitar `__pycache__`,
  `enhance_maps/`, `videos/`, `testResults.xml` nem os `docs/*.md` não rastreados que já estão no working
  tree. Não commitar fixtures geradas.
- Sem `[skip ci]` em nenhum commit deste ciclo (armadilha do Ciclo BB).
- STATE.md (260 KB+ — não ler inteiro): a seção `## Ciclo BF` já existe (com a linha `BF1 blocked` da 1ª
  tentativa, sem commit); atualize a linha da BF1 e anexe uma linha por ID; saída de comando relevante (o e2e
  vermelho da BF1 no caso `"dynamic"`, os testes vermelhos da BF2/BF3) em subseção curta.
- Plano ambíguo ou em conflito com o código → `blocked` com a pergunta exata; não improvisar.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
