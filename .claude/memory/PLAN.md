<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — CI: instalar do pyproject e rodar a suíte inteira

Data: 2026-07-25 | Ciclo: infra/CI | Origem: auditoria do `ci.yml` pós-ciclo I

**Objetivo:** hoje o CI roda 4 arquivos de teste dos ~20 existentes. Os seis
`test_cineon_*.py` — incluindo o `test_cineon_constants_guard.py` construído nos ciclos
G e H para impedir regressão silenciosa das constantes Cineon — **nunca rodam no CI**.
Um PR que adultere `CINEON_REF_WHITE` passa verde hoje.

A causa não é a lista de testes: é a lista de dependências. O `ci.yml:54` instala 8
pacotes à mão e faltam `av`, `colour-science`, `pydantic` e `pymediainfo`. Sem
`colour-science` o guard nem importa; sem `av` o `Reels_Encoder_v2_FINAL` não carrega.
A lista de testes é curta porque foi recortada até caber no que instalava.

É o mesmo defeito do ciclo I com outra roupa: **configuração duplicada à mão diverge da
fonte de verdade e ninguém percebe até quebrar.** Lá era a versão do ruff; aqui é a
lista de dependências.

**Escopo fechado (arquivos permitidos):**
- `pyproject.toml` — só acrescentar o extra `dev` em `[project.optional-dependencies]`
- `.github/workflows/ci.yml` — só as linhas 47 (cache key), 51-54 (install) e 57 (pytest)

**Fora de escopo:** o job `lint` (segue checando só `enhance/` — ampliá-lo exporia os 58
erros do `FINDINGS.md` I-a, que é decisão de outro ciclo), consolidar
`requirements.txt` com `pyproject.toml`, corrigir teste que falhe, mexer na matriz de
versões. Bug fora do escopo → uma linha em `FINDINGS.md`, sem investigar.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| J1 | Acrescentar em `[project.optional-dependencies]` do `pyproject.toml`: `dev = ["pytest>=7", "pytest-timeout"]`. O extra `opencv` já existe — não mexer nele. | `executor` | `pyproject.toml` | `pip install --dry-run -e ".[opencv,dev]"` resolve sem erro |
| J2 | Substituir o `pip install` manual (linha 54) por `pip install -e ".[opencv,dev]"`, mantendo o `python -m pip install --upgrade pip` da linha 53. | `executor` | `.github/workflows/ci.yml` | linha 54 não lista mais pacote individual algum |
| J3 | Cache key (linha 47): trocar `hashFiles('requirements.txt')` por `hashFiles('pyproject.toml')` — passa a ser o arquivo que o install de fato lê. | `executor` | `.github/workflows/ci.yml` | linha 47 referencia `pyproject.toml` |
| J4 | Step "Run tests" (linha 57): trocar a lista de 4 arquivos por `python -m pytest enhance/ ui/ -v --timeout=60`. | `executor` | `.github/workflows/ci.yml` | comando roda os diretórios, sem enumerar arquivo |
| J5 | Validar que o YAML continua parseável: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`. | `executor` | — | comando sai 0 |

## Notas de execução

- **Você não consegue verificar esta mudança de verdade.** O CI roda em `ubuntu-latest`
  e você está no Windows; `pip install -e .` na sua máquina não prova nada sobre o
  runner. Seu critério de done para de propósito no nível de sintaxe e resolução de
  dependência. **A verificação real é do Orquestrador, depois do push, assistindo o
  run.** Não invente um teste que simule o CI, e não marque nada além do que os
  critérios da tabela pedem.
- **Rodar a suíte inteira no CI vai expor coisas.** Localmente há 4 falhas conhecidas —
  2 em `enhance/test_ebu_meter.py` (assertam `cmd[0] == "ffmpeg"` mas o código resolve o
  caminho absoluto do binário) e 2 de encoding de console em `ui/`. As 4 são suposições
  de plataforma Windows e devem ficar **verdes** no Linux. Isso é previsão, não
  garantia: se o CI acusar qualquer coisa depois do push, o conserto é ciclo novo.
  **Nunca** adicione `skip`, `xfail` ou `--ignore` para fazer o CI passar.
- **Risco na perna Python 3.9** (a matriz é `["3.9", "3.11"]`): pode não haver wheel de
  `av` ou `colour-science` para 3.9. Se `pip install --dry-run` falhar em 3.9, registre
  `blocked` em J1 com o erro exato. **Não** remova 3.9 da matriz — estreitar a matriz é
  decisão de escopo, que é do Orquestrador.
- **Carregue `superpowers:verification-before-completion`** antes de marcar qualquer ID
  como `done` e cole no STATE.md a saída real do comando.
- Retorno: uma linha por ID. Detalhe no STATE.md.

## Achado a registrar em FINDINGS.md (não é tarefa deste ciclo)

`requirements.txt` e `[project] dependencies` do `pyproject.toml` listam os mesmos 9
pacotes — duplicação mantida à mão, terceira cópia da mesma informação. Depois de J2 o
CI deixa de ler `requirements.txt`, então ele passa a ser documentação que ninguém
executa: exatamente a condição em que uma lista diverge sem ninguém notar. Consolidar
(gerar de um só lado, ou apontar `requirements.txt` para `-e .`) em ciclo próprio.
