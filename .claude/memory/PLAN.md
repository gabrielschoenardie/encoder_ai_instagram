<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AI: registrar os ffmpeg de fase de análise (ADF1)

Data: 2026-08-22 | Ciclo: AI | Origem: `.claude/memory/FINDINGS.md` § `ADF1` (aberto no Ciclo AD). Ciclo AH fechado e pushado (`097e299`).

## Diagnóstico

`terminate_active_ffmpeg()` (Ciclo AD) só encerra o processo em `_ACTIVE_FFMPEG`.
Os `ffmpeg` de fase de análise sobem por `subprocess.run()` e nunca são
registrados, logo sobrevivem ao `exit=130` até terminarem sozinhos.

**Correção ao escopo registrado.** O `ADF1` cita "loudnorm e de-rotação". São
**três**, não dois — o remux do átomo `colr` também está fora do registro.
Classificação dos 6 `subprocess.run` do módulo:

| site | comando | duração | registrar? |
| --- | --- | --- | --- |
| `:383` | `wmic cpu get name` | ms, já tem `timeout=5` | não — não é ffmpeg |
| `:605` | `ffprobe` (HDR side data) | ms | não |
| `:1271` | **`ffmpeg`** remux de-rotação | segundos | **sim** |
| `:1363` | **`ffmpeg`** loudnorm pass 1 (`-f null -`, varre o áudio inteiro) | segundos a minutos | **sim** |
| `:3783` | **`ffmpeg`** remux do átomo `colr` | segundos | **sim** — ausente do registro do achado |
| `:3860` | `ffprobe` (verificação de cor) | ms | não |

Registrar `ffprobe` seria ruído: retorna antes de o sinal alcançá-lo.

**Risco que o achado não menciona e que define o desenho.** `_register_ffmpeg`
(`:192`) guarda **um único global**, e o padrão em uso é `_register_ffmpeg(proc)`
… `_register_ffmpeg(None)`. Um helper que zere o registro ao sair apagaria o de
quem estava antes. Não é hipotético: o remux do `colr` (`:3783`) roda enquanto
`_ACTIVE_FFMPEG` ainda aponta para o processo principal do encode, desregistrado
só em `:3909`. Zerar ali tornaria o processo principal não-matável nesse
intervalo — trocaria um S4 por um S3.

**Portanto: salvar e restaurar, nunca zerar.**

## Desenho

1. `_swap_active_ffmpeg(proc) -> prev`: troca atômica sob `_ACTIVE_FFMPEG_LOCK`,
   devolve o valor anterior. `_register_ffmpeg` passa a delegar a ela (contrato
   externo inalterado — os chamadores atuais ignoram o retorno).
2. `_run_ffmpeg_tracked(cmd, ...) -> subprocess.CompletedProcess`: equivalente a
   `subprocess.run` para o subconjunto de kwargs realmente usado nos 3 sites —
   `capture_output`, `text`, `encoding`, `errors`, `check`, `stdout`, `stderr`,
   `cwd`. Internamente: `popen` → `prev = _swap_active_ffmpeg(proc)` →
   `communicate()` → **`finally: _swap_active_ffmpeg(prev)`** → monta o
   `CompletedProcess`; se `check` e `returncode != 0`, levanta
   `CalledProcessError` com stdout/stderr, como o `subprocess.run` faz.
   Parâmetro `popen=subprocess.Popen` injetável — idioma da casa
   (`resolve_binary(name, which=shutil.which, ...)`), torna testável sem `monkeypatch`.
3. Trocar `subprocess.run` por `_run_ffmpeg_tracked` em `:1271`, `:1363`, `:3783`.
   **Não** tocar em `:383`, `:605`, `:3860`.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AI1 | Escrever este `PLAN.md`. | Orquestrador | `.claude/memory/PLAN.md` | **done** |
| AI2 | Implementar `_swap_active_ffmpeg` e `_run_ffmpeg_tracked` conforme § Desenho. | `executor-pesado` | `Reels_Encoder_v2_FINAL.py` | pendente |
| AI3 | Trocar os 3 call sites. Preservar exatamente os kwargs de cada um. | `executor-pesado` | `Reels_Encoder_v2_FINAL.py` | pendente |
| AI4 | Testes, ver § "Critérios de aceite". Estilo da casa: sem fixtures salvo `tmp_path`, sem `monkeypatch`, sem classes. | `executor-pesado` | `enhance/test_ffmpeg_tracked.py` (novo) | pendente |

## Critérios de aceite (AI4)

1. Durante a execução, o processo passado ao helper está em `_ACTIVE_FFMPEG`
   (verificar de dentro do `communicate()` do fake `popen`).
2. **Ao sair, o registro anterior é restaurado** — inclusive quando o anterior
   era um processo, não `None`. Este é o assert central do ciclo.
3. O registro é restaurado **também quando o comando falha** e quando
   `check=True` levanta. Usar `finally`, não caminho feliz.
4. `CompletedProcess` devolvido tem `returncode`, `stdout` e `stderr` coerentes.
5. `check=True` levanta `CalledProcessError` em retorno não-zero; não levanta em zero.
6. `terminate_active_ffmpeg()` devolve `True` para um processo registrado pelo
   helper (fake com `poll()`/`terminate()`/`wait()`).
7. Os 3 call sites não usam mais `subprocess.run`, e `:383`, `:605`, `:3860`
   continuam usando.

## Notas de execução

- **`_run_ffmpeg_tracked` não substitui o `Popen` principal do encode** (`:2004`,
  `:3554`) — aquele tem progresso em streaming e fica como está.
- Severidade honesta: `ADF1` é **S4**. Esses processos nunca escrevem o
  entregável, então não produzem o sintoma enganoso do `YF1`. O ganho real é o
  loudnorm pass 1 em arquivo longo, onde o Ctrl-C hoje deixa ffmpeg girando.
- Anti-escopo: não tocar em áudio (`TP=-1.4` é decisão fechada), LUT, VBV, GOP,
  container, nem no handler de `KeyboardInterrupt` em si (`:4466`, `:4519`).
- Baseline: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` →
  **416 passed**. Ao final: 416 + os novos.
- Ao fim, fechar `ADF1` no `FINDINGS.md` com o SHA e **corrigir ali o escopo de
  2 para 3 processos**, registrando o risco de clobber como parte da correção.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
