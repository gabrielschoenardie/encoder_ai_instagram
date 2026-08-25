# CI Vermelho — Isolar os Testes de --output-dir da Dependência de FFmpeg (Ciclo AJ) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Delegação (política deste repo, `CLAUDE.md`):** despache via Task para o agente exato listado — `executor`, não um subagente genérico.

**Goal:** `main` está com o CI vermelho desde o Ciclo AG. Confirmado no log real do job "Tests (ubuntu-latest, Python 3.11)" do run `32590519448` (SHA `3f12070`): `2 failed, 423 passed in 3.07s`, ambas `assert 1 == 0`. Os dois testes de `enhance/test_output_dir_and_pipeline_tag.py` chamam `main()` de ponta a ponta com `--batch` para validar comportamento do parser, mas o caminho atravessa a checagem de dependência do ffmpeg em `Reels_Encoder_v2_FINAL.py:4399-4414` antes de chegar lá. Nenhum runner do GitHub Actions vem com ffmpeg pré-instalado, e o `ci.yml` não o instala — confirmado lendo o job `tests` inteiro, sem nenhum step de instalação.

**Architecture:** A correção fica inteiramente no arquivo de teste. Nenhuma mudança em `Reels_Encoder_v2_FINAL.py`: a ordem atual (checar dependência antes de escanear a pasta de batch) é a certa — falhar rápido numa dependência ausente é melhor UX do que só descobrir isso depois de escanear arquivos. O que está errado é o teste depender de um binário externo presente no ambiente para validar uma decisão de parser que não tem nada a ver com ffmpeg. A correção usa `monkeypatch` — convenção já estabelecida no repo (`ui/test_launcher.py`, `enhance/test_cineon_constants_guard.py`, `enhance/test_hdr_pipeline.py`) — para neutralizar a checagem de dependência apenas nesses dois testes, sem tocar em produto.

**Tech Stack:** `pytest`, `pytest-mock` (via fixture nativa `monkeypatch`, já em uso no repo).

**Spec:** `docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md` (criado na Task 1) + `.claude/memory/FINDINGS.md` § achado `AIF1`

## Global Constraints

- **Não tocar em `Reels_Encoder_v2_FINAL.py`.** A ordem de checagem (dependência antes de escaneamento de pasta) é intencional e correta; mudar isso para acomodar um teste seria inverter causa e efeito.
- **Não instalar ffmpeg no runner do CI.** Isso mascararia o problema real (os testes não deveriam precisar de um binário externo para validar lógica de parser) e adicionaria minutos a cada execução de CI para todos os jobs.
- **Localizar por âncora, não por número de linha.** Os números citados são do commit `3f12070` e vão deslocar.
- **`.claude/memory/PLAN.md` está desatualizado** — mostra a tabela do Ciclo AI com três linhas "pendente" apesar de o `STATE.md` confirmar que foram concluídas (commit `d66887f`). A Task 1 sobrescreve o arquivo para abrir o Ciclo AJ, o que resolve essa inconsistência como efeito colateral — não é um passo à parte.
- **Baseline a preservar:** medido nesta sessão, sem ffmpeg no PATH, commit `fb870bd`: `enhance/test_output_dir_and_pipeline_tag.py` isolado dá `2 failed, 9 passed`; a suíte local completa (`test_render_queue.py enhance/ ui/ tools/`) deu `435 passed` tanto antes quanto depois da correção deste ciclo — a suposta terceira falha de CRLF/LF em `tools/test_generate_hollywood_lut_cooler.py::test_structure` não reproduziu nenhuma vez nesta sessão, e de todo modo `tools/` está fora da seleção que o CI roda (`ci.yml:61`: `test_render_queue.py enhance/ ui/`), então esse arquivo nunca é coletado nem executado em CI, independentemente de reproduzir localmente. Meta ao final: `425 passed` — a seleção exata do `ci.yml` (`test_render_queue.py enhance/ ui/`), que **não inclui `tools/`**, com a falha de CRLF ausente por não ser causada por este ciclo.

---

## File Structure

```text
enhance/test_output_dir_and_pipeline_tag.py                                  ← modificado (Task 2)
docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md     ← novo (Task 1)
docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md            ← novo (Task 1, este arquivo)
.claude/memory/FINDINGS.md                                                    ← modificado (Task 1)
.claude/memory/PLAN.md                                                        ← reescrito para Ciclo AJ (Task 1)
.claude/memory/STATE.md                                                       ← append (Task 3)
```

---

### Task 1: Registrar o achado e abrir o Ciclo AJ

**Agent:** `executor`

**Files:**
- Create: `docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md`
- Create: `docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md` (salvar este plano na íntegra)
- Modify: `.claude/memory/FINDINGS.md`
- Modify: `.claude/memory/PLAN.md`

**Interfaces:**
- Produces: o ID `AIF1` (achado após o Ciclo AI, corrigido no Ciclo AJ), referenciado pela Task 2 e pela mensagem de commit.

- [ ] **Step 1: Confirmar a evidência antes de escrever**

```bash
grep -n "ffmpeg\|choco\|apt-get" .github/workflows/ci.yml
python -m pytest enhance/test_output_dir_and_pipeline_tag.py -v 2>&1 | tail -20
```

Confirmar que nenhuma linha do `ci.yml` instala ffmpeg, e que os dois testes falham localmente com `assert 1 == 0`.

- [ ] **Step 2: Anexar o achado ao `FINDINGS.md`**

```markdown
## Achado — 2026-08-25 (ciclo AI, CI vermelho por dependência de ambiente) — corrigindo no ciclo AJ

Evidência: log real do job "Tests (ubuntu-latest, Python 3.11)", run `32590519448`, SHA `3f12070` — `2 failed, 423 passed in 3.07s`; leitura de `.github/workflows/ci.yml` confirmando ausência de step de instalação de ffmpeg em todos os jobs.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| AIF1 | teste acoplado a ambiente | `enhance/test_output_dir_and_pipeline_tag.py:41-62` | Dois testes de parser chamam `main()` inteiro e dependem de ffmpeg estar instalado | S2 | esperado: CI verde; medido: `main` com 4 jobs `Tests` vermelhos desde o Ciclo AG |

- **AIF1:** Os testes `test_output_dir_with_batch_does_not_trigger_usage_error` e `test_batch_without_output_dir_does_not_trigger_usage_error` (Ciclo AG, commit `c51516e`) validam que passar `--batch` não dispara o `parser.error()` novo do `--output-dir`. Para isso chamam `_run_main_with_argv()`, que executa `Reels_Encoder_v2_FINAL.main()` de ponta a ponta. O caminho passa pela checagem de dependência de ffmpeg (`Reels_Encoder_v2_FINAL.py:4399-4414`) antes de chegar à lógica de parser que o teste quer validar. Passaram na máquina de quem os escreveu (ffmpeg no PATH); falham em qualquer ambiente sem ffmpeg — inclusive todos os 4 jobs `Tests` do CI (nenhum runner do GitHub Actions vem com ffmpeg, e o workflow não o instala). Ninguém checou o CI após o merge do Ciclo AG; ficou vermelho em silêncio por dias.
```

- [ ] **Step 3: Escrever o spec**

`docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md`, esqueleto da casa. Em `## Architecture`, registrar a decisão central: **por que consertar o teste e não o produto** — a ordem de checagem em `main()` é intencional (falhar rápido em dependência ausente); o defeito é o teste ter escopo maior do que precisa (testa parser, mas exercita ffmpeg).

- [ ] **Step 4: Reescrever `.claude/memory/PLAN.md` para o Ciclo AJ**

Formato vigente: cabeçalho HTML, `# PLAN — Ciclo AJ: isolar os testes de --output-dir da dependência de ffmpeg (AIF1)`, linha `Data: 2026-08-25 | Ciclo: AJ | Origem: ...`, tabela `AJ1..AJ3` espelhando as Tasks 1–3. Isso substitui a tabela obsoleta do Ciclo AI (que mostrava "pendente" apesar de concluída).

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-08-25-ci-vermelho-ffmpeg-dependency-design.md \
        docs/superpowers/plans/2026-08-25-ci-vermelho-ffmpeg-dependency.md \
        .claude/memory/FINDINGS.md .claude/memory/PLAN.md
git commit -m "docs: registrar AIF1 e abrir o Ciclo AJ (CI vermelho por dependência de ffmpeg)"
```

---

### Task 2: Isolar os dois testes da dependência de ffmpeg

**Agent:** `executor`

**Files:**
- Modify: `enhance/test_output_dir_and_pipeline_tag.py`

**Interfaces:**
- Consumes: `ui.preflight.missing_ffmpeg_binaries` — alvo do `monkeypatch`, mesma função que `Reels_Encoder_v2_FINAL.py:4401` importa localmente dentro de `main()`. Patchear o atributo no módulo de origem funciona porque o `import` local em `main()` resolve o nome no namespace de `ui.preflight` no momento da chamada.

- [ ] **Step 1: Adicionar o `monkeypatch` aos dois testes falhando**

Localizar em `enhance/test_output_dir_and_pipeline_tag.py` (âncora: `def test_output_dir_with_batch_does_not_trigger_usage_error`). Substituir os dois testes:

```python
def test_output_dir_with_batch_does_not_trigger_usage_error(tmp_path):
    try:
        _run_main_with_argv(
            ["--batch", str(tmp_path), "--output-dir", str(tmp_path / "out")]
        )
        code = None
    except SystemExit as exc:
        code = exc.code

    # Pasta de batch vazia: segue até "Nenhum vídeo encontrado" (exit 0),
    # não até o parser.error() novo (exit 2).
    assert code == 0


def test_batch_without_output_dir_does_not_trigger_usage_error(tmp_path):
    try:
        _run_main_with_argv(["--batch", str(tmp_path)])
        code = None
    except SystemExit as exc:
        code = exc.code

    assert code == 0
```

por:

```python
def test_output_dir_with_batch_does_not_trigger_usage_error(tmp_path, monkeypatch):
    # AIF1: main() checa ffmpeg/ffprobe antes de chegar na logica de parser
    # que este teste valida. O teste e sobre argparse, nao sobre ffmpeg —
    # neutraliza a checagem de dependencia em vez de exigir o binario real.
    monkeypatch.setattr(
        "ui.preflight.missing_ffmpeg_binaries", lambda *a, **kw: []
    )
    try:
        _run_main_with_argv(
            ["--batch", str(tmp_path), "--output-dir", str(tmp_path / "out")]
        )
        code = None
    except SystemExit as exc:
        code = exc.code

    # Pasta de batch vazia: segue até "Nenhum vídeo encontrado" (exit 0),
    # não até o parser.error() novo (exit 2).
    assert code == 0


def test_batch_without_output_dir_does_not_trigger_usage_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ui.preflight.missing_ffmpeg_binaries", lambda *a, **kw: []
    )
    try:
        _run_main_with_argv(["--batch", str(tmp_path)])
        code = None
    except SystemExit as exc:
        code = exc.code

    assert code == 0
```

- [ ] **Step 2: Verificar em isolamento**

Run: `python -m pytest enhance/test_output_dir_and_pipeline_tag.py -v 2>&1 | tail -20`
Expected: **11 passed** (9 que já passavam + os 2 corrigidos), zero failed.

- [ ] **Step 3: Verificar que a suíte completa não regrediu**

Run: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q 2>&1 | tail -10`
Expected: nenhuma falha relacionada a `test_output_dir_and_pipeline_tag.py`. Se `tools/test_generate_hollywood_lut_cooler.py::test_structure` aparecer falhando aqui, é o artefato de CRLF/LF do ambiente local (fora de escopo — ver Global Constraints); confirmar com `git status` que o `.cube` não está modificado na árvore de trabalho antes de rodar, e se estiver, `git checkout -- <arquivo>` primeiro (não é conteúdo deste ciclo).

- [ ] **Step 4: Commit e push**

```bash
git add enhance/test_output_dir_and_pipeline_tag.py
git commit -m "test: isolar testes de --output-dir da dependência de ffmpeg (AIF1)"
git push -u origin claude/ciclo-aj-ci-ffmpeg
```

---

### Task 3: Confirmar verde no CI real e fechar o ciclo

**Agent:** `executor`

**Files:**
- Modify: `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md`

- [ ] **Step 1: Abrir PR e aguardar o CI**

Após o push, abrir PR (ou usar a existente) e aguardar os workflow runs do commit. **Não fechar o ciclo com base em execução local** — o achado inteiro nasceu de uma suíte verde localmente e vermelha no CI real; o mesmo erro de validação não pode se repetir aqui.

- [ ] **Step 2: Ler o resultado real do CI**

Confirmar que os 4 jobs `Tests` (ubuntu×windows, 3.11×3.12) do run mais recente estão `success`. Colar a linha de sumário final de pelo menos um job (ex.: `"XXX passed in Y.YYs"`) — literal, não parafraseada.

- [ ] **Step 3: Registrar a evidência**

`STATE.md`, seção `## Ciclo AJ — CI vermelho por dependência de ffmpeg (AIF1) — 2026-08-25`, com a saída real colada: contagem local (Task 2 Step 2/3) e a confirmação do CI real (Step 2 desta task). Se o CI ainda mostrar falha, **não fechar o ciclo** — registrar como divergência e investigar antes de prosseguir.

- [ ] **Step 4: Fechar**

`PLAN.md`: AJ1..AJ3 `done` com sha. `FINDINGS.md`: `AIF1` marcado corrigido, citando o commit e o run de CI verde.

```bash
git add .claude/memory/STATE.md .claude/memory/PLAN.md .claude/memory/FINDINGS.md
git commit -m "docs(state): evidência real de CI verde do Ciclo AJ (AIF1)"
git push
```

---

## Self-Review

- **Cobertura:** `AIF1` → Task 2 (a correção, mínima e local ao arquivo de teste) + Task 3 (a prova, no CI real, não local — porque a causa raiz inteira deste ciclo foi confiar em execução local que não reflete o ambiente onde o bug vive).
- **Placeholder scan:** nenhum "TBD". O único ponto condicional é o aviso da Task 2 Step 3 sobre o artefato de CRLF/LF, que está explicitamente marcado como fora de escopo e com a ação exata a tomar (`git checkout --`), não uma correção deste ciclo.
- **Consistência de tipos:** `monkeypatch.setattr("ui.preflight.missing_ffmpeg_binaries", lambda *a, **kw: [])` casa com a assinatura real de `missing_ffmpeg_binaries(required=(...), which=..., proj_dir=...)` — `*a, **kw` absorve qualquer combinação de posicionais/nomeados que `main()` passe, sem acoplar o teste aos parâmetros exatos da função de produção.
- **Risco residual:** a falha de `tools/test_generate_hollywood_lut_cooler.py::test_structure` observada localmente (contagem de `\r\n`) não é deste ciclo — é artefato de ambiente. Ela não aparece nos logs do CI, mas isso **não é confirmação de ambiente diferente**: `tools/` está fora da seleção de testes que `ci.yml:61` roda (`test_render_queue.py enhance/ ui/`), então esse arquivo nunca é coletado nem executado em CI, independente de a falha existir ou não lá. Já foi revertido na árvore de trabalho antes deste plano ser escrito. Se ela reaparecer no CI real depois que `tools/` passar a ser incluído na seleção, é achado novo, não uma regressão desta correção.
