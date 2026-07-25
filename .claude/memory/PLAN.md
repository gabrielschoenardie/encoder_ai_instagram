<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Assumir Python >= 3.11 em todo lugar que declara versão

Data: 2026-07-25 | Ciclo: infra | Origem: CI run 30167293830 (perna 3.9 vermelha)

**Objetivo:** o projeto declara suportar Python 3.9 e não suporta. `colour-science 0.4.7`
— dependência obrigatória do pipeline Cineon — declara `requires_python: >=3.11,<3.15`.
A perna 3.9 do CI morreu em `Install dependencies` com
`No matching distribution found for colour-science>=0.4.7`. Não é só 3.9: **3.10 também
não serve.**

Ninguém tinha percebido porque a perna 3.9 nunca instalava a lista real de dependências
— o `ci.yml` instalava 8 pacotes recortados à mão, sem `colour-science`. Foi abrir o CI
(commit `7dfdb08`) que revelou.

**A perna 3.11 passou com `346 passed`, suíte inteira, zero falhas** — inclusive os seis
`test_cineon_*.py`. Isso não está em questão neste ciclo; só a declaração de versão está.

**Escopo fechado (arquivos permitidos):**
- `pyproject.toml` — `requires-python` e `classifiers`
- `.github/workflows/ci.yml` — só a linha 33 (matriz)
- `.github/workflows/pylint.yml` — só a linha 11 (matriz)
- `README.md` — só o badge (linha 5) e a linha da tabela (133)

**Fora de escopo:** `requirements.txt` (achado J-a, ciclo próprio), o
`actions/setup-python@v3` desatualizado do `pylint.yml` (o `ci.yml` já usa `@v5` — mas
não é deste ciclo), a lista de dependências, qualquer teste. Bug fora do escopo → uma
linha em `FINDINGS.md`, sem investigar.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| K1 | `requires-python = ">=3.9"` → `">=3.11"`. | `executor` | `pyproject.toml` | linha 10 com `>=3.11` |
| K2 | Nos `classifiers`: remover as linhas de 3.9 e 3.10, manter 3.11, acrescentar 3.12. | `executor` | `pyproject.toml` | nenhum classifier de 3.9/3.10; presentes 3.11 e 3.12 |
| K3 | Matriz do CI (linha 33): `["3.9", "3.11"]` → `["3.11", "3.12"]`. | `executor` | `.github/workflows/ci.yml` | linha 33 com as duas versões novas |
| K4 | Matriz do pylint (linha 11): `["3.8", "3.9", "3.10"]` → `["3.11", "3.12"]`. Ver nota. | `executor` | `.github/workflows/pylint.yml` | linha 11 com as duas versões novas |
| K5 | README: badge da linha 5 (`Python-3.9%2B` → `Python-3.11%2B`) e a célula `3.9+` da linha 133 da tabela de dependências → `3.11+`. | `executor` | `README.md` | `grep -n "3\.9" README.md` sem match referente a Python |
| K6 | `MANUAL_INSTALACAO.txt` linha 8: `Versão Python: 3.8+` → `3.11+`. Só essa linha; o resto do manual (instruções de download, PATH, troubleshooting) não é deste ciclo. | `executor` | `MANUAL_INSTALACAO.txt` | linha 8 com `3.11+`; nenhuma outra linha alterada |
| K7 | Validar que os dois YAML continuam parseáveis: `yaml.safe_load` em `ci.yml` e `pylint.yml`. | `executor` | — | ambos saem 0 |

## Notas de execução

- **Por que o `pylint.yml` entra (K4).** Ele roda hoje em 3.8/3.9/3.10 e passa verde
  porque instala **só** o pylint e desliga `import-error` — nunca toca uma dependência
  real. Não é cosmético: o pylint parseia o fonte com a gramática da versão-alvo, então
  uma versão antiga na matriz pode reclamar de sintaxe legítima em 3.11. Deixar
  3.8–3.10 lá enquanto o `pyproject` diz `>=3.11` é a mesma divergência que este ciclo
  existe para eliminar.
- **3.12 é perna nova em ambos os workflows — nunca rodou.** `colour-science` permite
  `<3.15`, então em teoria resolve, mas isso é teoria. Se o CI ficar vermelho em 3.12
  depois do push, **é decisão do Orquestrador** o que fazer (corrigir ou estreitar a
  matriz para só 3.11). Você não decide isso e não remove nada da matriz por conta
  própria.
- **Você não consegue verificar isso de verdade** — a validação real é o run depois do
  push, que é do Orquestrador. Seus critérios param em sintaxe e conteúdo de linha. Não
  invente teste que simule o CI.
- **A suíte local não deve mudar.** Rode `python -m pytest enhance/ ui/ -q` e confirme
  o baseline conhecido: `4 failed, 342 passed` (as 4 são de plataforma Windows e já
  provamos que ficam verdes no Linux). Qualquer coisa além disso é regressão sua.
- **Carregue `superpowers:verification-before-completion`** antes de marcar qualquer ID
  como `done` e cole no STATE.md a saída real do comando.
- Retorno: uma linha por ID. Detalhe no STATE.md.
