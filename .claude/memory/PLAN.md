<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo O: corrigir README.md (O-a, O-b)

Data: 2026-07-25 | Ciclo: docs | Origem: `FINDINGS.md` ciclo O (auditoria README.md)

Ciclos anteriores (M/N — J-b, I-a) fechados e commitados (sha 9b6ed26). Este plano é
independente, só toca `README.md`.

## O-a — contagem de testes da UI desatualizada

**Objetivo:** `README.md` diz "105 testes" para `ui/` em 3 lugares. `pytest ui/
--collect-only` coleta **111 testes** hoje (verificado pelo Orquestrador). Atualizar os
3 números.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| O1 | Rodar `python -m pytest ui/ -q --collect-only \| tail -1` para confirmar o número atual antes de editar (pode ter mudado desde a auditoria). Trocar "105 testes" → "`<N>` testes" nas 3 ocorrências: linha ~434 (comentário na árvore de arquivos, `test_*.py # Suíte de testes da UI (105 testes)`), linha ~626 (comentário no bloco de comando pytest, `# Só a UI interativa (105 testes)`) e linha ~637 (prosa da seção Testes, `` UI (`ui/`, 105 testes): ``). Não mudar mais nada nessas linhas. | `executor` | `README.md` | `grep -n "105 testes" README.md` não retorna nada; `grep -n "<N> testes" README.md` retorna as 3 linhas com o número atual confirmado pelo `pytest --collect-only` |

## O-b — rótulo "opcional" do opencv-python contradiz o caminho de instalação padrão

**Contexto (não corrigir o `requirements.txt` — ele está correto por decisão do ciclo
J-a/L1, ver `FINDINGS.md` O-b):** a tabela de Requisitos (linha ~144) marca
`opencv-python` como `⚪ opcional (banding detection)`. Mas tanto o Quick Start (linha
~81) quanto a Instalação Completa (linha ~202) mandam rodar `pip install -r
requirements.txt`, que hoje é `-e .[opencv]` — instala opencv **sempre**. Só a seção
separada "Instalação via pip" (linha ~216, `pip install .` puro) de fato deixa opencv de
fora. O README não explica essa diferença entre os dois caminhos "completos".

**Correção (documentação apenas, não mexer em `requirements.txt`/`pyproject.toml`):**
adicionar uma nota curta explicando que o caminho via `requirements.txt` (Quick Start e
Instalação Completa) inclui o opencv por padrão, e que quem quiser a instalação mínima
sem opencv deve usar `pip install .` (seção "Instalação via pip"). Ajustar a nota de
rodapé da tabela de Requisitos (linha ~147, `⚪ Dependências opcionais...`) para não
afirmar que o caminho padrão é sem opencv.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| O2 | Na nota de rodapé da tabela de Requisitos (linha ~147), adicionar uma frase esclarecendo que `pip install -r requirements.txt` (usado no Quick Start e na Instalação Completa) já inclui o opencv por padrão via `-e .[opencv]`; quem quiser instalar sem opencv deve usar `pip install .` (seção "Instalação via pip", linha ~216). Não reescrever a tabela nem mudar o marcador `⚪`/`✅` de nenhuma linha — só a nota de rodapé e, se necessário, uma linha extra logo abaixo dela. | `executor` | `README.md` | Nota de rodapé da tabela de Requisitos menciona explicitamente que o caminho padrão (`requirements.txt`) inclui opencv; `pip install .` continua descrito como o caminho sem opencv |

## Notas de execução

- Ambos os itens são edição de texto em `README.md`, sem risco de comportamento —
  **não precisa `executor-pesado`**.
- Não tocar `requirements.txt`, `pyproject.toml` ou qualquer `.py`. Escopo é só
  `README.md`.
- Carregar `superpowers:verification-before-completion` antes de marcar O1/O2 como
  `done`: colar no `STATE.md` a saída do `grep` pedido em cada critério de done.
- Retorno: uma linha por ID (O1, O2). Detalhe completo no `STATE.md`.
