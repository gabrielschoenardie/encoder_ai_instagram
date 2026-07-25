<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Fechar J-b e I-a

Data: 2026-07-25 | Ciclo: infra/docs | Origem: `FINDINGS.md` J-b, I-a

## Parte 1 — J-b (doc: fallback desatualizado)

**Objetivo:** `MANUAL_INSTALACAO.txt` APÊNDICE A (linhas 295-314) instrui o usuário a
criar manualmente um `requirements.txt` com 8 pacotes fixos, caso o arquivo não exista.
Já faltavam `pydantic`/`scipy` antes deste ciclo; agora diverge mais porque o
`requirements.txt` real (desde L1) é uma linha só: `-e .[opencv]`. Mesma família de
defeito dos ciclos I/J/K/L: lista mantida à mão. Caminho é raro (o arquivo real nunca
falta), mas o conteúdo do apêndice está errado hoje.

**Correção:** trocar o apêndice de "cole esta lista de 8 pacotes" para "rode
`pip install -e .[opencv]` direto" — mesmo padrão de L1 (ponteiro, não lista duplicada).
Não recriar `requirements.txt` manualmente resolve o mesmo problema sem reintroduzir a
lista.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| M1 | Reescrever APÊNDICE A (linhas 295-314): título pode continuar "APÊNDICE A", mas o corpo passa a dizer que `requirements.txt` normalmente já vem com o projeto e aponta para `pyproject.toml`; se por algum motivo faltar, a instrução é rodar `pip install -e .[opencv]` a partir da pasta do projeto (não recriar o arquivo à mão). Remover a lista de 8 pacotes fixos e os passos "abra o bloco de notas / cole / salve como .txt". | `executor` | `MANUAL_INSTALACAO.txt` | Nenhuma lista de pacotes hardcoded restante no apêndice; `grep -n "pymediainfo\|colour-science" MANUAL_INSTALACAO.txt` não bate mais na região do apêndice A |

## Parte 2 — I-a (débito de lint pré-existente fora de `enhance/`)

**Contexto (do `leitor`, não corrigir nada além do listado):** 58 erros E4/E7/E9/F,
CI não olha essas pastas hoje. Composição real:

| regra | qtd | fixável automaticamente | risco de mudar comportamento |
|-------|-----|--------------------------|-------------------------------|
| E701 (multi-statement `:`) | 13 | não, mas é só quebrar linha | nenhum |
| F401 (import não usado) | 12 | 6 sim / 6 não | **alto em parte** — ver nota abaixo |
| F541 (f-string sem placeholder) | 11 | sim | nenhum |
| E402 (import fora do topo) | 6 | não | possível — pode ser proposital |
| E731 (lambda assignment) | 6 | sim | nenhum |
| E722 (bare except) | 5 | não | baixo, mas muda o que é capturado |
| E702 (multi-statement `;`) | 2 | não, mas é só quebrar linha | nenhum |
| E741 (nome ambíguo l/I/O) | 2 | não, precisa renomear no escopo | nenhum se renomear todas as ocorrências |

**Nota de risco F401 (`Reels_Encoder_v2_FINAL.py:105-131`):** por `STATE.md` (ciclo I3),
este arquivo tem blocos `try/except ImportError` que definem `PSUTIL_AVAILABLE`,
`CINEON_AVAILABLE`, `ENHANCE_AVAILABLE` — imports de probe de dependência opcional.
**Antes de apagar qualquer F401 nesse arquivo**, ler o bloco ao redor da linha; se o
import é o probe de um desses três flags, ele NÃO é lixo morto — ignorar via
`per-file-ignores`, não apagar. Mesmo cuidado para `ebu_meter.py:33`,
`tools/verificador_instalacao.py:293`, `ui/test_dashboard.py:5`,
`ui/test_packaging.py:10` — ler antes de decidir.

**Nota E402 (`tools/gen_readme_assets.py:19-24`):** ler o arquivo inteiro antes de mexer.
Se o import tardio existe por causa de `sys.path.insert(...)` ou de um guard que roda
antes (padrão comum em scripts standalone de `tools/`), a ordem é proposital — ignorar
via `per-file-ignores` com comentário, não reordenar às cegas.

**Fora de escopo:** `enhance/` (não tem esses erros — não tocar); qualquer refactor além
de dividir linha / renomear variável / apagar import morto / trocar `except:` por
`except Exception:`. Não introduzir type hints, docstrings ou reformatação não pedida.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| N1 | `python -m ruff check . --select E731,F541,F841 --fix` (raiz do repo). Sem risco semântico — cosmético puro. | `executor-pesado` | (o que o ruff tocar, fora de `enhance/`) | `ruff check . --select E731,F541,F841` limpo; suíte de teste no baseline (ver N7) |
| N2 | Para cada um dos 12 F401: ler o contexto da linha. Se for import morto de verdade, apagar. Se for probe de dependência opcional (ver nota de risco acima) ou re-export intencional, manter o import e adicionar entrada em `[tool.ruff.lint.per-file-ignores]` no `pyproject.toml` restrita a `F401` **naquele arquivo específico**, com comentário de 1 linha explicando por quê. | `executor-pesado` | arquivos listados pelo leitor + `pyproject.toml` | cada um dos 12 F401 originais está endereçado: apagado OU coberto por ignore nomeado — nenhum "esquecido" |
| N3 | E701 (13) + E702 (2): quebrar cada `if x: y` / `a; b` em linhas separadas, mantendo a lógica idêntica. | `executor-pesado` | `analyze_source.py`, `tools/compare_frames.py`, `ui/test_binaries.py` | `ruff check . --select E701,E702` limpo nesses arquivos |
| N4 | E741 (2): renomear a variável ambígua (`l`/`I`/`O`) em `Reels_Encoder_v2_FINAL.py:348` e `ui/test_components.py:49` para um nome descritivo, atualizando todas as ocorrências no mesmo escopo. | `executor-pesado` | `Reels_Encoder_v2_FINAL.py`, `ui/test_components.py` | `ruff check . --select E741` limpo; nenhuma referência solta ao nome antigo no escopo |
| N5 | E722 (5, todas em `tools/compare_frames.py`): trocar `except:` por `except Exception:`. | `executor-pesado` | `tools/compare_frames.py` | `ruff check . --select E722` limpo |
| N6 | E402 (6, `tools/gen_readme_assets.py:19-24`): ler o arquivo antes de decidir (ver nota de risco). Se a ordem for proposital, `per-file-ignores` com comentário; senão, mover os imports para o topo. | `executor-pesado` | `tools/gen_readme_assets.py` + possivelmente `pyproject.toml` | E402 endereçado (fixado ou ignorado com justificativa) |
| N7 | Verificação final: `python -m ruff check . --select E4,E7,E9,F` (repo inteiro) → cada um dos 58 originais está fixado ou coberto por `per-file-ignores` nomeado (nenhum "sobrando" sem explicação); `python -m pytest enhance/ ui/ -q` → baseline `4 failed, 342 passed`, zero regressão nova. | `executor-pesado` | — | ambos os comandos com saída colada no STATE.md |

## Notas de execução

- **Carregue `superpowers:verification-before-completion`** antes de marcar qualquer ID
  como `done`; cole a saída real dos comandos no STATE.md, não parafraseie.
- Se qualquer F401/E402 exigir mais contexto do que uma leitura local (ex: import usado
  em outro módulo via `from Reels_Encoder_v2_FINAL import X`), documentar isso no STATE.md
  e preferir `per-file-ignores` a apagar — reversível, não quebra nada.
- Retorno: uma linha por ID (M1, N1-N7). Detalhe completo no STATE.md.
