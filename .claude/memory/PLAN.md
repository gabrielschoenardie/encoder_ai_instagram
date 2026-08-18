<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AB: remover toda referência a "FASE 27"

Data: 2026-08-18 | Ciclo: AB | Origem: pedido direto do usuário.

## Diagnóstico

Agente `leitor` mapeou (grep case-insensitive por "FASE 27"/"Fase27"/variações)
15+ ocorrências em `README.md` (4) e 10 arquivos `.py` de `enhance/`. É rótulo
de fase de desenvolvimento interna, sem significado pra quem lê o código/doc
hoje — remover, não substituir por outro rótulo. Cuidado: remover só o texto
"FASE 27"/variação e a pontuação/travessão que dependia dele, sem deixar
frase quebrada (parênteses vazios, travessão solto, dois-pontos sem conteúdo
antes).

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AB1 | `README.md`, 4 ocorrências: (a) linha 29 TOC `- [🤖 Módulo de IA — FASE 27](#-módulo-de-ia--fase-27)` → `- [🤖 Módulo de IA](#-módulo-de-ia)`; (b) linha 297 tabela CLI `Ativa Enhancement Engine (FASE 27)` → `Ativa Enhancement Engine`; (c) linha 443 diagrama `# Módulo de IA (FASE 27)` → `# Módulo de IA`; (d) linha 490 heading `## 🤖 Módulo de IA — FASE 27` → `## 🤖 Módulo de IA`. Âncora do TOC (a) tem que bater com o novo slug do heading (d) depois da mudança. | `executor` | `README.md` | grep `-i "fase 27"` em `README.md` sem match; TOC (a) e heading (d) com âncora idêntica |
| AB2 | `enhance/ffmpeg_filters.py:4`, `enhance/processor.py:5`: docstring de módulo começa com `FASE 27D — <descrição>` → remover só o prefixo `FASE 27D — `, manter a descrição intacta (ex.: `FFmpeg filter string generator for Mode 1 (FFmpeg pipeline).`). | `executor` | `enhance/ffmpeg_filters.py`, `enhance/processor.py` | grep `-i "fase 27"` nos 2 arquivos sem match; docstring lê natural sem o prefixo |
| AB3 | `enhance/ai/interface.py:6`, `enhance/ai/mock_cnn.py:4`, `enhance/ai/__init__.py:4`, `enhance/profile.py:233,451`, `enhance/test_mock_cnn.py:4`: remover a referência `(Fase 27F)`/`Fase 27F —`/`Fase 27F:` mantendo o resto da frase gramatical (ex.: `Mock CNN model for enhancement decisions (Fase 27F).` → `Mock CNN model for enhancement decisions.`). | `executor` | `enhance/ai/interface.py`, `enhance/ai/mock_cnn.py`, `enhance/ai/__init__.py`, `enhance/profile.py`, `enhance/test_mock_cnn.py` | grep `-i "fase 27"` nos 5 arquivos sem match; nenhuma frase com pontuação quebrada |
| AB4 | `enhance/sampler.py:2`, `enhance/profile.py:267`: comentário de seção `# FASE 27A: ...` / `# ── ... (Fase 27F) ──...` → remover a referência à fase mantendo o resto do comentário; se a linha 267 for separador com `─` até uma largura fixa, preencher os `─` que sobrarem pra manter a largura original da linha (não encurtar o separador visualmente). | `executor` | `enhance/sampler.py`, `enhance/profile.py` | grep `-i "fase 27"` nos 2 arquivos sem match; separador de `profile.py:267` com a mesma largura de antes |
| AB5 | `enhance/__init__.py:4`, `enhance/test_processors.py:4`: docstring `... Enhancement Engine (FASE 27)` / `FASE 27D — Testes de validação ...` → remover a referência mantendo o resto. | `executor` | `enhance/__init__.py`, `enhance/test_processors.py` | grep `-i "fase 27"` nos 2 arquivos sem match |
| AB6 | Strings de output em runtime (prints de banner de teste, não afetam asserts): `enhance/test_mock_cnn.py:231` `print("  MockCNN Unit Tests — FASE 27F-C")` → `print("  MockCNN Unit Tests")`; `enhance/test_processors.py:956` `print("  FASE 27D — Processor & FFmpeg Filters — Test Suite")` → `print("  Processor & FFmpeg Filters — Test Suite")`; `enhance/test_processors.py:992` `print(f"  ✅ {total_passed}/{total_passed} PASSED — FASE 27D VÁLIDA")` → `print(f"  ✅ {total_passed}/{total_passed} PASSED")`. Se essas linhas fizerem parte de um banner com bordas de largura fixa (ex.: linha de `=` acima/abaixo), não precisa realinhar a borda — só o texto do meio. | `executor` | `enhance/test_mock_cnn.py`, `enhance/test_processors.py` | grep `-i "fase 27"` nos 2 arquivos sem match |
| AB7 | Verificação final: grep `-ri "fase 27\|fase27"` no repositório inteiro (fora de `.git/`) — cobre qualquer ocorrência fora da lista do `leitor` (outros `.md`, `.txt`, `.json`, etc.). Rodar `python -m pytest enhance/ ui/ -q` pra confirmar zero regressão (baseline: só as 2 falhas nominais pré-existentes de `ui/`, ver Notas). Commit final. | `executor` | (verificação, sem arquivo fixo) | grep repo-wide sem match nenhum; suite bate no baseline; commit feito — **done**, commit `7422051` (grep repo-wide zero match; suite sem regressão nova, 2 falhas extras em `test_ebu_meter.py` confirmadas pré-existentes via `git stash`) |

## Notas de execução

- Baseline de regressão a preservar: `python -m pytest enhance/ ui/ -q` →
  falhas nominais pré-existentes de `ui/` (`test_readme_assets.py::test_anchor_strings_present`,
  `test_theme.py::test_idle_glyphs_wired_unicode_and_ascii`) — nenhuma
  falha nova permitida. `enhance/` deve ficar 100% verde (as mudanças
  são só docstring/comentário/print, não lógica).
- Não trocar "FASE 27" por outro nome de fase — é remoção, não rebranding.
- Não tocar em nenhuma lógica de código, só texto (docstring/comentário/
  string literal de print/heading markdown).
- AB1 pode rodar em paralelo com AB2-AB6 (arquivos disjuntos); AB7 é o
  fechamento e depende de todos os anteriores.
- Retorno do agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
