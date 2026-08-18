# Windows no CI e Interrupção Robusta (Ciclos AC + AD) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Delegação (política deste repo, `CLAUDE.md`):** cada task lista um **Agent** — despache via Task para esse agente exato (`executor` ou `executor-pesado`), não para um subagente genérico.
>
> **Este arquivo cobre DOIS ciclos.** O Ciclo AD depende de evidência produzida pelo Ciclo AC. **Não inicie o AD antes do AC estar fechado e mergeado.**

**Goal:** Fechar o ponto cego de Windows do projeto. O produto roda em Windows; a automação só observa Linux. Disso decorrem três problemas: (ABF1) 4 testes falham em Windows e nenhum job de CI os executa; (ABF2) o `test_render_queue.py` está fora do escopo do job `tests`, então os 23 testes da fila — incluindo os 9 do Ciclo Y — nunca rodaram no CI em plataforma alguma; (YF1) uma interrupção durante a escrita do `.mp4` deixa um arquivo de aparência íntegra, sem remux do átomo `colr` e sem artefatos `.qc`, que a execução seguinte promove a `○ pulado`.

**Architecture:** O Ciclo AC é só configuração de CI e correção do que ele expuser — nenhuma mudança de comportamento do produto. A perna Windows entra primeiro como **não-bloqueante** (`continue-on-error: true`), para colher a lista real de falhas sem deixar `main` vermelha; só depois de verde ela vira bloqueante. O Ciclo AD ataca o YF1 com um registro do `Popen` do ffmpeg ativo no engine (onde o subprocesso nasce) mais um `discard_partial_output` com retentativa, seguindo o idioma de injeção por argumento default que o repo já usa em `ui/binaries.py` (`resolve_binary(name, which=shutil.which, ...)`) — o que torna a lógica testável sem `monkeypatch`.

**Tech Stack:** GitHub Actions, Python 3.11/3.12, `pytest`, `rich` (já no projeto).

**Spec:** `docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md` (criado na Task 1) + `.claude/memory/FINDINGS.md` § achados `ABF1`/`ABF2`/`ABF3` e `YF1`

## Global Constraints

- **`main` nunca fica vermelha.** A perna Windows só vira bloqueante na Task 5, depois de comprovadamente verde. Enquanto isso, `continue-on-error: true`.
- **Não "consertar" teste mascarando o sintoma.** Se um teste falha em Windows porque o *código* assume separador ou encoding de POSIX, corrige-se o código. `pytest.mark.skipif(sys.platform == "win32")` só é aceitável para um teste que valide algo genuinamente específico de POSIX, e exige uma linha de justificativa no `FINDINGS.md`.
- **Não alargar o `ruff` neste ciclo.** Fica registrado como `ABF3` e adiado — o escopo atual (`enhance/`) permanece intocado.
- **Ciclo AD não altera o caminho feliz.** Nenhuma mudança observável num encode que termina normalmente. O `terminate()` só dispara sob `KeyboardInterrupt`.
- **`discard_partial_output` continua sem levantar.** O `except OSError: return False` foi decisão do Ciclo Y e permanece correta; o que falta é o `terminate()` antes e o aviso visível depois.
- **Localizar por âncora, não por número de linha.** Os números citados são do commit `c161ce1` e vão deslocar.
- **Baseline a preservar:** `python -m pytest test_render_queue.py enhance/ ui/ -q` → `392 passed` em Linux. Ao final do AD, esperado `392 + <novos> passed`.
- Estilo de teste da casa: sem fixtures (exceto `tmp_path`), sem `monkeypatch`, sem classes. Funções `def test_*()` planas, `io.StringIO()` + `Console(file=...)` para render, `pytest.approx` para números.

---

## File Structure

```text
.github/workflows/ci.yml                       ← modificado (AC: Tasks 2, 3, 5)
render_queue.py                                ← modificado (AD: Task 7)
test_render_queue.py                            ← modificado (AD: Task 7)
Reels_Encoder_v2_FINAL.py                      ← modificado (AD: Tasks 6, 8)
docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md   ← novo (Task 1)
docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md          ← novo (Task 1, este arquivo)
.claude/memory/FINDINGS.md                     ← modificado (Tasks 1, 4)
.claude/memory/PLAN.md                         ← reescrito p/ Ciclo AC, depois AD (Tasks 1, 6)
.claude/memory/STATE.md                        ← append (Tasks 3, 5, 9)
```

---

# CICLO AC — Windows e a fila entram no CI

### Task 1: Registrar os achados e abrir o Ciclo AC

**Agent:** `executor`

**Files:**
- Create: `docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md`
- Create: `docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md` (salvar este plano na íntegra)
- Modify: `.claude/memory/FINDINGS.md`
- Modify: `.claude/memory/PLAN.md`

**Interfaces:**
- Produces: os IDs `ABF1`/`ABF2`/`ABF3`, referenciados pelas tasks seguintes e pelas mensagens de commit.

- [ ] **Step 1: Confirmar os achados antes de escrevê-los**

Não registrar de ouvido. Colar a evidência de cada um:

```bash
# ABF2 — o job tests não alcança test_render_queue.py
grep -n "pytest" .github/workflows/ci.yml
ls test_render_queue.py enhance/ ui/ -d

# ABF1 — nenhum job de Python roda em Windows
grep -n "runs-on\|matrix\|os:" .github/workflows/ci.yml

# ABF3 — ruff só cobre enhance/
grep -n "ruff" .github/workflows/ci.yml
```

Se qualquer um dos três **não** se confirmar, registre o achado com a redação corrigida e ajuste as tasks correspondentes — não force o plano contra a evidência.

- [ ] **Step 2: Anexar os achados ao `FINDINGS.md`**

Manter o formato vigente (`## Achado — <data> (ciclo <L>, <descrição>)`, tabela, depois parágrafos por ID). Usar o prefixo `AB` (achados encontrados após o Ciclo AB); **não** reutilizar IDs de ciclos anteriores.

```markdown
## Achado — 2026-08-18 (ciclo AB, auditoria de cobertura de CI) — corrigindo no ciclo AC

Evidência: leitura de `.github/workflows/ci.yml`; comparação entre o comando do job `tests` e a localização real dos arquivos de teste; contraste entre a suíte verde em Linux (`392 passed`) e a nota do `STATE.md` § AB7 ("4 falhas nominais pré-existentes"), registrada em execução Windows.

| ID | categoria | arquivo:linha | descrição ≤20 palavras | severidade | esperado vs medido |
|----|-----------|----------------|------------------------|------------|--------------------|
| ABF1 | ponto cego de CI | `.github/workflows/ci.yml` (job `tests`) | Nenhum job de Python roda em Windows; 4 falhas conhecidas nunca são observadas | S2 | esperado: suíte verde na plataforma de produção; medido: 4 falhas registradas só à mão, invisíveis ao CI |
| ABF2 | cobertura ausente | `.github/workflows/ci.yml` (job `tests`) | `pytest enhance/ ui/` não alcança `test_render_queue.py`, na raiz | S2 | esperado: 23 testes da fila no CI; medido: zero — nunca executados em plataforma alguma |
| ABF3 | débito de lint | `.github/workflows/ci.yml` (job `lint`) | `ruff check enhance/` deixa engine, `ui/`, `render_queue.py` e `tools/` sem lint | S3 | esperado: lint no repo; medido: 1 de 5 áreas coberta |

- **ABF1:** O produto é distribuído para Windows (`launcher.ps1` é o caminho canônico de entrada desde o Ciclo AA), e o job `pester` já roda em `windows-latest`. O job `tests`, porém, é `runs-on: ubuntu-latest` com matriz só de versão de Python. As 4 falhas de Windows são conhecidas por relato manual e vinham sendo normalizadas como "baseline nominal" — o padrão de fadiga de alarme que o Ciclo Y eliminou em Linux e que segue vivo em Windows. **Os nomes dos 4 testes não estão confirmados**: a lista que circulou veio de uma execução obsoleta. Descobrir a lista real é a Task 3.
- **ABF2:** O job `tests` executa `pytest enhance/ ui/ -v --timeout=60`. O `test_render_queue.py` mora na raiz do repo, fora dos dois diretórios. Consequência: os 23 testes da fila de render — 14 do Ciclo X mais os 9 do Ciclo Y — nunca rodaram no CI. Toda a validação do modo `--batch` depende hoje de execução manual. É o achado mais barato de corrigir e o de maior retorno.
- **ABF3:** Registrado e **adiado deliberadamente**. Alargar o `ruff` para o repo inteiro num arquivo de 4453 linhas que nunca foi lintado produz um volume de erros que exige ciclo próprio; misturá-lo aqui inviabilizaria a revisão do Ciclo AC.
```

- [ ] **Step 3: Escrever o spec**

`docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md`, no esqueleto da casa (`# Título` / `**Date:** / **Status:** / **Author:**` / `## Goal` / `## Non-goals / constraints` / `## Architecture` / `## Riscos conhecidos` / `## Validação`). Conteúdo obrigatório em `## Architecture`:

- Por que a perna Windows entra **não-bloqueante** primeiro: a lista de falhas é desconhecida; entrar bloqueante deixaria `main` vermelha por tempo indeterminado, recriando exatamente a normalização de falha que o projeto vinha combatendo.
- Por que o AD depende do AC: o YF1 é um bug de subprocesso **específico de Windows**. Sem um job de Python em Windows não há como provar a correção no CI, e a evidência ficaria presa na máquina do desenvolvedor — o mesmo problema que gerou o ABF1.
- Em `## Riscos conhecidos`: (a) os runners `windows-latest` não têm ffmpeg — testes que dependam de binário real vão falhar por motivo diferente do investigado, e precisam ser distinguidos; (b) o encoding padrão do console em Windows (cp1252) quebra asserções sobre glifos Unicode; (c) `os.path.sep` e `\r\n` quebram asserções sobre caminhos e texto multi-linha.

- [ ] **Step 4: Reescrever `.claude/memory/PLAN.md` para o Ciclo AC**

Formato vigente: cabeçalho HTML, `# PLAN — Ciclo AC: Windows e a fila de render entram no CI (ABF1/ABF2)`, linha `Data: 2026-08-18 | Ciclo: AC | Origem: ...`, `## Diagnóstico`, tabela `| ID | tarefa | agente alvo | arquivos | critério de done |` com AC1..AC5 espelhando as Tasks 1–5, e `## Notas de execução`. Citar este plano, não transcrevê-lo.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-08-18-windows-ci-e-interrupcao-robusta-design.md \
        docs/superpowers/plans/2026-08-18-windows-ci-e-interrupcao-robusta.md \
        .claude/memory/FINDINGS.md .claude/memory/PLAN.md
git commit -m "docs: registrar ABF1/ABF2/ABF3 e abrir o Ciclo AC (cobertura de CI)"
```

---

### Task 2: Colocar `test_render_queue.py` no CI (ABF2)

**Agent:** `executor`

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: o job `tests` passa a executar os 23 testes da fila de render.

- [ ] **Step 1: Ler o bloco atual antes de editar**

```bash
sed -n '/^  tests:/,/^  [a-z]/p' .github/workflows/ci.yml
```

Colar a saída no corpo do commit ou no `STATE.md` — as chaves exatas (`name`, `run`, indentação) precisam ser preservadas.

- [ ] **Step 2: Ampliar o alvo do pytest**

Localizar o step que roda o pytest dentro do job `tests` (âncora: a string `pytest enhance/ ui/`). Trocar o alvo:

```yaml
        run: pytest test_render_queue.py enhance/ ui/ -v --timeout=60
```

Manter `-v` e `--timeout=60` exatamente como estão. Não alterar mais nada do job nesta task.

- [ ] **Step 3: Verificar localmente que o alvo novo coleta o esperado**

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q --collect-only 2>&1 | tail -3`
Expected: a contagem coletada inclui os 23 do `test_render_queue.py`. Comparar com `python -m pytest enhance/ ui/ -q --collect-only 2>&1 | tail -3` — a diferença entre as duas deve ser exatamente **23**. Colar as duas saídas.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: incluir test_render_queue.py no job tests (ABF2)"
```

- [ ] **Step 5: Confirmar verde no CI antes de seguir**

Após o push, verificar que o job `tests` (3.11 e 3.12) continua `success` com o alvo ampliado. Se ficar vermelho, **os 23 testes da fila estão quebrados em CI** — algo que ninguém sabia. Nesse caso, pare, registre como achado novo (`ACF1`) e trate antes da Task 3.

---

### Task 3: Adicionar a perna Windows como não-bloqueante e colher a lista real de falhas (ABF1)

**Agent:** `executor`

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.claude/memory/STATE.md`

**Interfaces:**
- Produces: a lista **real e verificada** dos testes que falham em Windows — consumida pela Task 4.

- [ ] **Step 1: Converter o job `tests` para matriz de SO**

Substituir o cabeçalho do job pelo abaixo, preservando as chaves já existentes (`name`, `steps`, versões de action) e adaptando os nomes se divergirem do lido na Task 2:

```yaml
  tests:
    name: Tests (${{ matrix.os }}, Python ${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    # A perna Windows entra nao-bloqueante ate a lista real de falhas ser
    # corrigida (ABF1). Vira bloqueante na task AC5.
    continue-on-error: ${{ matrix.os == 'windows-latest' }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ['3.11', '3.12']
```

`fail-fast: false` é obrigatório: sem ele, a primeira falha em Windows cancela as pernas de Linux e a gente perde o sinal bom junto com o ruim.

- [ ] **Step 2: Verificar se algum step do job é específico de shell POSIX**

```bash
sed -n '/^  tests:/,/^  [a-z]/p' .github/workflows/ci.yml | grep -n "run:"
```

Qualquer step usando sintaxe de `bash` (pipes, `&&`, `[ -f ... ]`, `$(...)`) vai quebrar no shell padrão do runner Windows (`pwsh`) por motivo **não relacionado** ao ABF1. Para esses, adicionar `shell: bash` no step — os runners Windows do GitHub têm bash disponível. Em especial, checar o step de validação do `requirements.txt`.

- [ ] **Step 3: Commit e push**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: rodar o job tests tambem em windows-latest, nao-bloqueante (ABF1)"
```

- [ ] **Step 4: Colher a lista real — esta é a entrega da task**

Após o CI rodar, abrir os logs das duas pernas Windows (3.11 e 3.12) e extrair as linhas `FAILED`. Registrar no `STATE.md`, seção `## Ciclo AC — Windows no CI — 2026-08-18`, com a saída **colada literalmente**, contendo:

- a lista completa de `FAILED <arquivo>::<teste> - <exceção>`;
- se 3.11 e 3.12 falham nos **mesmos** testes (se divergirem, é achado separado);
- se a contagem bate com as "4 falhas nominais" relatadas à mão, ou se são mais/menos/outras.

**Não corrigir nada nesta task.** A entrega é a lista verificada. Se o número real divergir de 4, isso por si só é o achado mais importante do ciclo — significa que o "baseline" manual estava errado.

---

### Task 4: Corrigir as falhas de Windows

**Agent:** `executor-pesado`

**Files:**
- A determinar pela Task 3. Provavelmente `enhance/`, `ui/`, e possivelmente `ui/binaries.py`.
- Modify: `.claude/memory/FINDINGS.md`

**Interfaces:**
- Consumes: a lista de falhas registrada no `STATE.md` pela Task 3.

> **Esta task é deliberadamente não-especificada em detalhe.** A lista real de falhas só existe depois da Task 3, e inventar correções antes disso seria adivinhação. Abaixo estão as hipóteses a testar primeiro — **hipóteses, não fatos**.

- [ ] **Step 1: Classificar cada falha antes de tocar em código**

Para cada `FAILED`, decidir a que categoria pertence e anotar no `STATE.md`:

| Categoria | Sintoma típico | Ação |
|---|---|---|
| **Bug real do produto em Windows** | O código assume `/`, ou UTF-8, ou nome de binário sem `.exe` | Corrigir o **código**, não o teste |
| **Teste acoplado a detalhe POSIX** | O teste afirma sobre uma string de caminho que é legitimamente diferente | Afrouxar a asserção (ex.: `os.path.basename`) |
| **Ausência de ffmpeg no runner** | `FileNotFoundError` ao invocar binário | `skipif` justificado, com linha no `FINDINGS.md` |
| **Genuinamente só-POSIX** | Testa comportamento que não existe em Windows | `skipif` justificado, com linha no `FINDINGS.md` |

Hipóteses a checar primeiro, na ordem: (a) `resolve_binary` devolve `ffmpeg.exe` ou um caminho de `bin\` em Windows, quebrando asserções sobre a forma do comando; (b) glifos Unicode do tema não sobrevivem ao console cp1252; (c) `\r\n` quebra asserções sobre texto multi-linha; (d) separador de caminho em asserções de string.

- [ ] **Step 2: Corrigir, uma categoria por commit**

Um commit por grupo coerente, mensagem citando `ABF1` e o teste. Após cada correção: `python -m pytest test_render_queue.py enhance/ ui/ -q` em Linux **precisa continuar em `392 passed`** — nenhuma correção de Windows pode custar uma regressão em Linux.

- [ ] **Step 3: Registrar cada `skipif` concedido**

Todo `skipif` adicionado ganha uma linha no `FINDINGS.md` com a justificativa. `skipif` sem justificativa escrita é dívida silenciosa — exatamente o padrão que este ciclo existe para acabar.

- [ ] **Step 4: Verificar**

Run: `python -m pytest test_render_queue.py enhance/ ui/ -q 2>&1 | tail -5`
Expected: `392 passed` (ou mais, se testes foram adicionados; nunca menos). Colar literal.
E: as duas pernas Windows do CI em `success`.

---

### Task 5: Tornar a perna Windows bloqueante e fechar o Ciclo AC

**Agent:** `executor`

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`

- [ ] **Step 1: Só prosseguir com as duas pernas Windows verdes**

Confirmar no CI que `Tests (windows-latest, Python 3.11)` e `(… 3.12)` estão `success`. Se ainda houver `skipif` pendente de justificativa, voltar à Task 4.

- [ ] **Step 2: Remover o escape**

Apagar a linha `continue-on-error:` e o comentário de duas linhas acima dela. Manter `fail-fast: false`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: tornar a perna windows bloqueante no job tests (fecha ABF1)"
```

- [ ] **Step 4: Registrar evidência e fechar**

`STATE.md`: anexar a saída real do CI mostrando os **6 jobs** do workflow CI verdes (lint, tests ×4, pester ×2 — confirmar a contagem real, que muda com a matriz). `PLAN.md`: marcar AC1..AC5 `done` com sha. `FINDINGS.md`: marcar ABF1 e ABF2 como corrigidos; ABF3 permanece **aberto e adiado**.

```bash
git add .claude/memory/STATE.md .claude/memory/PLAN.md .claude/memory/FINDINGS.md
git commit -m "docs(state): evidência real do Ciclo AC (ABF1/ABF2)"
```

---

# CICLO AD — Interrupção robusta (YF1)

> **Pré-requisito:** Ciclo AC fechado e mergeado. Sem a perna Windows no CI, a correção do YF1 não pode ser provada onde o bug existe.

### Task 6: Abrir o Ciclo AD e registrar o desenho

**Agent:** `executor`

**Files:**
- Modify: `.claude/memory/PLAN.md`

- [ ] **Step 1: Reescrever o `PLAN.md` para o Ciclo AD**

`# PLAN — Ciclo AD: interrupção robusta, encerrar o ffmpeg órfão (YF1)`, com a tabela AD1..AD4 espelhando as Tasks 6–9. Em `## Diagnóstico`, resumir o mecanismo em três linhas: o handler de `KeyboardInterrupt` remove o arquivo mas não encerra o subprocesso; o ffmpeg segura o handle (Windows), o `os.remove` falha com `OSError`, o `return False` é silencioso; o ffmpeg sobrevive à saída do Python e **termina de escrever**, produzindo um `.mp4` de tamanho normal que nunca passou pelo pós-encode.

- [ ] **Step 2: Commit**

```bash
git add .claude/memory/PLAN.md
git commit -m "docs(plan): abrir o Ciclo AD (YF1)"
```

---

### Task 7: `render_queue.py` — descarte com retentativa e injeção

**Agent:** `executor`

**Files:**
- Modify: `render_queue.py`
- Modify: `test_render_queue.py`

**Interfaces:**
- Produces (assinatura nova, substitui a do Ciclo Y):
  `discard_partial_output(job, *, remove=os.remove, exists=os.path.exists, sleep=time.sleep, attempts=3, delay=0.5) -> bool`
- Os parâmetros injetáveis seguem o idioma já usado em `ui/binaries.py` (`resolve_binary(name, which=shutil.which, ...)`) e existem para tornar a retentativa testável sem `monkeypatch`.

- [ ] **Step 1: Substituir `discard_partial_output`**

```python
def discard_partial_output(
    job: QueueJob,
    *,
    remove=os.remove,
    exists=os.path.exists,
    sleep=time.sleep,
    attempts: int = 3,
    delay: float = 0.5,
) -> bool:
    """Remove o output parcial de um job interrompido.

    Retorna True se removeu de fato. Tenta `attempts` vezes: no Windows o
    subprocesso do ffmpeg pode ainda estar soltando o handle do arquivo logo
    apos o terminate(), e a primeira tentativa falha com OSError. Nunca levanta
    — quem chama decide o que dizer ao usuario quando o retorno e False.

    Os argumentos injetaveis existem para o teste; producao usa os defaults.
    """
    path = job.output_path
    if not path:
        return False
    for attempt in range(attempts):
        if not exists(path):
            return False
        try:
            remove(path)
            return True
        except OSError:
            if attempt < attempts - 1:
                sleep(delay)
    return False
```

- [ ] **Step 2: Confirmar que os testes do Ciclo Y ainda passam**

Run: `python -m pytest test_render_queue.py -q -k discard 2>&1 | tail -5`
Expected: `test_discard_partial_output_removes_existing_file` e `..._returns_false_when_absent` continuam verdes — os defaults preservam o comportamento anterior. Se falharem, a assinatura foi alterada de forma incompatível.

- [ ] **Step 3: Testes novos da retentativa**

```python
def test_discard_partial_output_retries_until_handle_is_released():
    # Simula o ffmpeg do Windows soltando o arquivo so na terceira tentativa.
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    calls = {"remove": 0, "sleep": 0}

    def fake_remove(path):
        calls["remove"] += 1
        if calls["remove"] < 3:
            raise OSError(13, "Permission denied")

    def fake_sleep(seconds):
        calls["sleep"] += 1

    ok = discard_partial_output(
        job,
        remove=fake_remove,
        exists=lambda path: True,
        sleep=fake_sleep,
        attempts=3,
        delay=0.0,
    )

    assert ok is True
    assert calls["remove"] == 3
    assert calls["sleep"] == 2


def test_discard_partial_output_gives_up_after_attempts():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")

    def always_locked(path):
        raise OSError(13, "Permission denied")

    ok = discard_partial_output(
        job,
        remove=always_locked,
        exists=lambda path: True,
        sleep=lambda seconds: None,
        attempts=3,
        delay=0.0,
    )

    assert ok is False


def test_discard_partial_output_does_not_sleep_when_first_try_wins():
    job = QueueJob(input_path="a.mp4", output_path="a_out.mp4")
    slept = []

    ok = discard_partial_output(
        job,
        remove=lambda path: None,
        exists=lambda path: True,
        sleep=lambda seconds: slept.append(seconds),
        delay=0.0,
    )

    assert ok is True
    assert slept == []
```

- [ ] **Step 4: Verificar**

Run: `python -m pytest test_render_queue.py -v 2>&1 | tail -10`
Expected: **26 passed** (23 + 3 novos).

- [ ] **Step 5: Commit**

```bash
git add render_queue.py test_render_queue.py
git commit -m "fix(batch): retentativa no descarte de output parcial (YF1)"
```

---

### Task 8: Engine — encerrar o ffmpeg ativo e tornar a falha visível

**Agent:** `executor-pesado`

**Files:**
- Modify: `Reels_Encoder_v2_FINAL.py`

**Interfaces:**
- Produces: `terminate_active_ffmpeg(timeout: float = 5.0) -> bool` — encerra o subprocesso de ffmpeg em curso, se houver.
- Consumes (da Task 7): `render_queue.discard_partial_output(job)`.

- [ ] **Step 1: Localizar o ponto onde o ffmpeg é lançado**

```bash
grep -n "Popen\|subprocess.run\|subprocess.call" Reels_Encoder_v2_FINAL.py
```

Colar a saída. Se o encode usa `subprocess.run` (bloqueante) em vez de `Popen`, o registro precisa envolver a chamada de outra forma — **pare e relate** antes de improvisar, porque muda o desenho.

- [ ] **Step 2: Registrar o processo ativo**

Adicionar, próximo ao topo do módulo (junto às outras globais):

```python
_ACTIVE_FFMPEG = None
_ACTIVE_FFMPEG_LOCK = threading.Lock()


def _register_ffmpeg(proc):
    global _ACTIVE_FFMPEG
    with _ACTIVE_FFMPEG_LOCK:
        _ACTIVE_FFMPEG = proc


def terminate_active_ffmpeg(timeout: float = 5.0) -> bool:
    """Encerra o ffmpeg em curso, se houver. True se havia um para encerrar.

    Chamado do handler de KeyboardInterrupt: sem isto o subprocesso sobrevive a
    saida do Python e termina de escrever o .mp4 sozinho, produzindo um arquivo
    de tamanho normal que nunca passou pelo pos-encode (YF1).
    """
    with _ACTIVE_FFMPEG_LOCK:
        proc = _ACTIVE_FFMPEG
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    return True
```

Confirmar que `threading` já está importado no módulo; se não, adicionar.

- [ ] **Step 3: Alimentar o registro em `run_ffmpeg`**

No ponto do `Popen`, registrar logo após a criação e limpar num `finally`:

```python
        _register_ffmpeg(proc)
        try:
            ...  # corpo existente, INALTERADO
        finally:
            _register_ffmpeg(None)
```

**Não reescrever o corpo de `run_ffmpeg`.** A única mudança é envolver o trecho já existente. Se o `finally` já existir, adicionar a linha ao final dele.

- [ ] **Step 4: Chamar o terminate no handler do batch**

Localizar pelo comentário `# ─── BATCH MODE ───` e depois pelo `except KeyboardInterrupt:` do `run_job`. Trocar:

```python
                    if render_queue.discard_partial_output(job):
                        console.print(
                            f"[dim]  ● output parcial removido: "
                            f"{os.path.basename(job.output_path)}[/dim]"
                        )
```

por:

```python
                    terminate_active_ffmpeg()
                    if render_queue.discard_partial_output(job):
                        console.print(
                            f"[dim]  ● output parcial removido: "
                            f"{os.path.basename(job.output_path)}[/dim]"
                        )
                    elif os.path.exists(job.output_path):
                        # YF1: falha silenciosa aqui deixava um arquivo de aparencia
                        # integra que a execucao seguinte marcava como pronto.
                        console.print(
                            f"[bold red]  ✗ NÃO foi possível remover "
                            f"{os.path.basename(job.output_path)}[/bold red]"
                        )
                        console.print(
                            "[yellow]    Este arquivo está incompleto e NÃO passou "
                            "pelo controle de qualidade. Apague-o à mão antes de "
                            "rodar a fila de novo, ou ele será tratado como "
                            "pronto.[/yellow]"
                        )
```

- [ ] **Step 5: Aplicar o mesmo tratamento ao caminho single-file**

Localizar o handler de `KeyboardInterrupt` do caminho single-file (âncora: o bloco com `output_preexisted` e `except OSError: pass`). Ele tem a mesma janela, não medida. Adicionar `terminate_active_ffmpeg()` antes da remoção e substituir o `except OSError: pass` mudo pelo mesmo aviso em vermelho. Manter o `sys.exit(130)` existente.

- [ ] **Step 6: Verificar**

Run: `python -m py_compile Reels_Encoder_v2_FINAL.py && python -m pytest test_render_queue.py enhance/ ui/ -q 2>&1 | tail -5`
Expected: compila limpo; `395 passed` (392 + 3 da Task 7). Colar literal.

- [ ] **Step 7: Commit**

```bash
git add Reels_Encoder_v2_FINAL.py
git commit -m "fix(batch): encerrar ffmpeg órfão e avisar quando o parcial sobrevive (YF1)"
```

---

### Task 9: Smoke test na janela do YF1 e evidência

**Agent:** `executor-pesado`

**Files:**
- Modify: `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md`

> Esta task **precisa** rodar em Windows para valer. O YF1 é um bug de handle de arquivo do Windows; reproduzi-lo em Linux não prova nada.

- [ ] **Step 1: Reproduzir na janela medida**

Reusar o arranjo do Ciclo Y (`runpy.run_path` + `_thread.interrupt_main()` de uma thread-timer — o mesmo caminho de entrega do Ctrl+C do console). O `STATE.md` do Ciclo Y registra a janela crítica em t≈113 s–135 s de um job de ~140 s: **disparar a interrupção dentro dela**, não antes.

- [ ] **Step 2: Verificar os três sintomas do YF1**

| # | Critério | Esperado |
|---|---|---|
| 1 | Processo ffmpeg após a saída do Python | Nenhum órfão (`tasklist \| findstr ffmpeg` vazio) |
| 2 | Arquivo parcial | Removido; ou, se não, **aviso vermelho impresso** |
| 3 | Execução seguinte | Job **refeito** (`✓`), nunca `○ pulado` |

- [ ] **Step 3: Provar o caminho do aviso**

Se o `terminate()` resolver o caso e a remoção sempre funcionar, o ramo do aviso vermelho fica sem cobertura real. Forçá-lo à mão: com a fila parada, abrir o `.mp4` de saída num processo que segure o handle e disparar a interrupção. Confirmar que a mensagem em vermelho aparece e que o `exit` continua 130. Colar a saída.

- [ ] **Step 4: Registrar a evidência**

`STATE.md`, seção `## Ciclo AD — interrupção robusta (YF1) — <data>`, com saída real colada, **nunca parafraseada** (`superpowers:verification-before-completion`). Divergência vira achado novo (`ADF1`, …), nunca ajuste de teste para passar.

- [ ] **Step 5: Fechar**

`PLAN.md`: AD1..AD4 `done` com sha. `FINDINGS.md`: YF1 corrigido, com a linha de evidência. Confirmar que `ABF3` segue registrado como **aberto e adiado** — ele é o candidato natural ao próximo ciclo.

```bash
git add .claude/memory/STATE.md .claude/memory/PLAN.md .claude/memory/FINDINGS.md
git commit -m "docs(state): evidência real do Ciclo AD (YF1)"
```

---

## Self-Review

- **Cobertura:** ABF2 → Task 2 (uma linha de YAML, o item de maior retorno do plano). ABF1 → Tasks 3 (colher), 4 (corrigir), 5 (tornar bloqueante). YF1 → Task 7 (retentativa), Task 8 (terminate + aviso, nos dois caminhos), Task 9 (prova em Windows, na janela medida). ABF3 → registrado na Task 1 e **deliberadamente adiado**, reconfirmado na Task 9 Step 5.
- **Placeholder scan:** um único ponto intencionalmente não especificado — a Task 4, cujas correções dependem de uma lista que só existe após a Task 3. Isso está declarado no corpo da task, com uma tabela de classificação e hipóteses ordenadas em lugar de código inventado. Todo o resto está literal.
- **Consistência de tipos:** `discard_partial_output` ganha parâmetros **keyword-only com defaults** na Task 7, então as duas chamadas existentes (batch e single-file) seguem válidas sem alteração — verificado contra o Step 4 da Task 8. `terminate_active_ffmpeg() -> bool` é definida na Task 8 Step 2 e chamada pelo efeito nos Steps 4 e 5; o retorno é ignorado de propósito, e isso está dito. `_register_ffmpeg(None)` no `finally` garante que o registro nunca aponte para processo morto entre jobs.
- **Risco residual conhecido:** a Task 9 depende de acesso a uma máquina Windows real. Se o smoke test não puder rodar lá, o YF1 fica com prova apenas unitária (Task 7) — nesse caso, **não** marcar YF1 como corrigido; registrar como "corrigido com prova parcial" e manter aberto. Fechar um S2 sem evidência na plataforma onde ele existe seria repetir o ABF1.
