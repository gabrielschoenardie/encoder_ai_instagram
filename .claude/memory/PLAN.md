<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AW: consolidar Hollywood LUT v6.8 como único do pipeline FFmpeg, limpar antigos

Data: 2026-09-04 | Ciclo: AW | Origem: pedido do usuário — "deixar somente o `HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube` como LUT padrão do pipeline encode FFmpeg, excluir luts antigas".

## Diagnóstico (remedido no código)

**O default do FFmpeg Mode JÁ é o v6.8.** `Reels_Encoder_v2_FINAL.py:2258`
(`_HOLLYWOOD_LUT_FILENAME`) e `.claude/skills/.../scripts/analyze_source.py:41` (`LUT_FFMPEG`)
já apontam para o v6.8. **Não há troca de default a fazer** — a tarefa é *limpeza* dos LUTs
antigos e das referências de empacotamento.

Inventário dos 4 `.cube` no root (fora do `venv`):

| LUT | papel | destino |
|---|---|---|
| `...v6.8_3.1-96IRE...cube` | default do FFmpeg Mode (já), `analyze_source`, `verificador_instalacao` | **manter** |
| `...v6.7B_1.5IRE...cube` | **fonte de bake do v6.8** (`tools/generate_hollywood_lut_cooler.py:74` SRC + `tools/test_generate_hollywood_lut_cooler.py:23`) | **manter no disco, tirar do `data-files`** |
| `...v6.7B-W80_1.5IRE...cube` | órfão (só `pyproject:49` + STATE.md; **não** é fonte do gerador) | **deletar do disco** |
| `FilmLook_Portra400_SkinPriority_D65.cube` | LUT do **Cineon Mode** (`ui/config.py:48`, `--cineon-lut` default, node5, `test_cineon_lut.py`) | **manter** (outro pipeline) |

### Decisões do usuário (2026-09-04, via AskUserQuestion)

- **Manter Portra400 → Cineon Mode segue vivo.** Deletar só as versões antigas do *Hollywood*,
  não o LUT do Cineon. Nada de `ui/config.py`, `--cineon-lut`, node5 ou testes de Cineon muda.
- **Manter v6.7B só como fonte de build.** O gerador `generate_hollywood_lut_cooler.py` segue
  funcional (assa o v6.8 a partir do v6.7B); o v6.7B **fica no disco** mas **sai do
  `data-files`** para não ser instalado no ambiente do usuário final.

## Desenho

Três mudanças mecânicas, sem tocar em lógica de encode:

1. **Deletar** o arquivo órfão `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube`
   via `git rm`. Único órfão: só referenciado em `pyproject.toml:49` e no STATE.md (histórico,
   não se edita). Não é fonte do gerador (o gerador usa o v6.7B *plain*).
2. **`pyproject.toml` § `[tool.setuptools.data-files]`** (linhas 47-52): remover as duas linhas
   do `v6.7B` (48) e do `v6.7B-W80` (49). O bloco passa a instalar em `share/reels-encoder`
   **só** o `v6.8` e o `Portra400`. Manter as linhas do v6.8 (50) e Portra400 (51) intactas.
3. **`Reels_Encoder_v2_FINAL.py:2264`**: docstring de `_get_hollywood_lut_path` diz
   "Hollywood LUT v6.7B" — defasada; a função retorna `_HOLLYWOOD_LUT_FILENAME` = v6.8.
   Trocar o texto "v6.7B" por "v6.8". Só o comentário, não o código.

### O que NÃO fazer

- **Não** tocar em `MANIFEST.in`. `include *.cube` é glob de sdist; após o `git rm` ele
  naturalmente deixa de pegar o W80 e segue pegando v6.7B/v6.8/Portra400. O v6.7B **deve**
  ficar no sdist (é insumo de build do gerador), coerente com "manter como fonte de build".
- **Não** deletar o `v6.7B` do disco, nem o `Portra400`.
- **Não** tocar em Cineon Mode: `ui/config.py`, `cineon_pipeline.py`, `--cineon-lut`,
  `enhance/test_cineon_lut.py` ficam intactos.
- **Não** tocar no gerador `tools/generate_hollywood_lut_cooler.py` nem no seu teste (ambos
  dependem do v6.7B, que fica).
- **Não** mexer no `README.md` (as listas em `:440-441` e `:570-571` já mostram só v6.8 +
  Portra400 — não citam os antigos; confirmar de passagem, mas não deve haver edição).
- Não adicionar features, não refatorar, não reescrever a lógica de seleção de LUT.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AW1 | (a) `git rm` do arquivo `...v6.7B-W80...cube`; (b) remover as 2 linhas do v6.7B e do v6.7B-W80 do bloco `[tool.setuptools.data-files]` do `pyproject.toml` (mantendo v6.8 + Portra400); (c) corrigir a docstring `Reels_Encoder_v2_FINAL.py:2264` de "v6.7B" para "v6.8". | executor | `pyproject.toml`, `Reels_Encoder_v2_FINAL.py`, deleção do `.cube` W80 | ver critérios de aceite |

## Critérios de aceite

- `git status` mostra: 1 arquivo deletado (`...v6.7B-W80...cube`), `pyproject.toml` modificado,
  `Reels_Encoder_v2_FINAL.py` modificado. Nada mais.
- `pyproject.toml` § data-files lista **exatamente** 2 `.cube`: `v6.8` e `Portra400`.
- `HollywoodCinema_Ultimate_v6.7B_1.5IRE_...cube` (plain) **continua no disco** (`ls` confirma)
  — não foi deletado.
- `FilmLook_Portra400_SkinPriority_D65.cube` intacto.
- `Reels_Encoder_v2_FINAL.py:2264` não contém mais "v6.7B"; o código (`_HOLLYWOOD_LUT_FILENAME`)
  inalterado.
- TOML válido: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` sem erro.
- Suíte Python **verde, sem regressão** (contagem igual à baseline; rodar sem `--timeout` no
  shell local se `pytest-timeout` faltar). Nenhum teste referencia o W80, então a deleção não
  deve quebrar nada — a suíte verde confirma isso.

## Notas de execução

- **Nunca `git add -A` nem `git add .`** — há untracked no repo (`961576A_*.qc.*`, `docs/*.md`,
  `testResults.xml`, `videos/`). Adicionar por caminho explícito; usar `git rm` para o W80.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AW` e cabeçalho de tabela.
- Retorno: ponteiro + veredito, uma linha por ID + SHA; confirmar a contagem da suíte.
