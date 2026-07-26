<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo P: zerar os 112 avisos markdownlint do README.md

Data: 2026-07-25 | Ciclo: docs | Origem: `FINDINGS.md` ciclo P (P-a)

Ciclo O (README.md, contagem de testes + nota opencv) já fechado e commitado
(sha 6a9e12f / 064f4e7). Este plano é independente, só toca `README.md` + config nova.

**Já validado pelo Orquestrador numa cópia isolada em scratchpad** (não no repo real):
`npx markdownlint-cli2@0.23.1 --fix README.md` com o `.markdownlint.jsonc` abaixo já
presente resolve 92 dos 112 avisos automaticamente (`MD060` 88, `MD032` 3, `MD034` 1),
sem alterar conteúdo/render — só normaliza espaçamento de pipe de tabela (`|---|` →
`| --- |`), acrescenta linha em branco antes/depois de lista, e envolve o e-mail solto em
`<gschoenardie@gmail.com>`. Sobram exatamente 6 avisos (`MD040`×5, `MD045`×1) que exigem
conteúdo real e são cobertos pelo item P2 abaixo.

## P1 — criar `.markdownlint.jsonc` e rodar o auto-fix

**Objetivo:** suprimir só as 3 regras que conflitam com convenções deliberadas de README
no GitHub (HTML bruto pra centralizar banner/badges/capturas — não existe alternativa em
markdown puro; ênfase que não é heading — viraria heading no TOC do GitHub), e alinhar
`MD013` com o que o VS Code markdownlint extension já mostra (off). Depois, rodar o
fixer automático para os 92 avisos mecânicos.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| P1a | Criar `.markdownlint.jsonc` na raiz do repo com o conteúdo abaixo (copiar exatamente — cada `//` é a justificativa da supressão, mesmo padrão do `per-file-ignores` do ruff em `pyproject.toml`). | `executor` | `.markdownlint.jsonc` (novo) | arquivo existe com o conteúdo exato abaixo |
| P1b | Rodar `npx --yes markdownlint-cli2@0.23.1 --fix README.md` a partir da raiz do repo. | `executor` | `README.md` | comando reporta "Attempted: 92 fixes"; `git diff README.md` só mostra separadores de tabela ganhando espaço em volta do traço, 3 linhas em branco novas antes de listas, e `<gschoenardie@gmail.com>` no lugar do e-mail solto — nenhuma outra mudança de conteúdo |

Conteúdo de `.markdownlint.jsonc`:

```jsonc
{
  "default": true,
  // MD013 (line-length): off — o VS Code markdownlint extension ja roda com essa
  // regra desligada por padrao; alinhar a config do repo com o que o editor mostra.
  "MD013": false,
  // MD033 (no-inline-html): README usa div/p/img para centralizar banner, badges e
  // capturas — padrao comum em READMEs do GitHub (nao ha alternativa em markdown puro
  // para centralizar). Permitir so os elementos realmente usados.
  "MD033": { "allowed_elements": ["div", "img", "p"] },
  // MD036 (no-emphasis-as-heading): "**Gabriel Schoenardie**" (nome sob "## Autor") e
  // "*Feito com...*" (tagline final dentro de <div align="center">) sao enfase
  // intencional, nao heading — vira-los heading poluiria o indice/TOC do GitHub.
  "MD036": false,
  // MD041 (first-line-heading): README abre com banner centralizado (<div><img>...),
  // nao com "# H1" — o titulo ja esta no banner. Padrao comum, sem impacto na
  // renderizacao do GitHub.
  "MD041": false
}
```

## P2 — corrigir os 6 avisos restantes (conteúdo real)

**Objetivo:** `MD045` (banner sem `alt=`) e `MD040`×5 (blocos ASCII sem linguagem no
fence) são falta de conteúdo de verdade, não convenção — corrigir direto, sem exceção
via config.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| P2a | `README.md:3` — no `<img src="https://capsule-render.vercel.app/...">` do banner, adicionar `alt="Reels Encoder AI"` (a tag já tem `width="100%"`; inserir o atributo antes de `/>`). | `executor` | `README.md` | `MD045` não aparece mais na linha do banner |
| P2b | Adicionar `text` como linguagem nos 5 fences ASCII sem linguagem: `README.md:235` (bloco de uso `python Reels_Encoder_v2_FINAL.py [input] [opções]`), `:330` (diagrama dos 2 pipelines), `:361` (fluxo de decisão da IA), `:392` (árvore de arquivos `encoder_ai_instagram/`), `:540` (diagrama do pipeline Cineon `Rec.709 (camera)...`). Trocar cada ```` ``` ```` de abertura por ```` ```text ````; fence de fechamento continua ```` ``` ```` puro, sem mudar o conteúdo do bloco. | `executor` | `README.md` | `MD040` não aparece mais nessas 5 linhas |

## Verificação final

| ID | tarefa | agente alvo | critério de done |
|----|--------|-------------|------------------|
| P3 | `npx --yes markdownlint-cli2@0.23.1 README.md` (raiz do repo, após P1+P2) | `executor` | saída "Summary: 0 issues in 1 file"; colar a saída completa no `STATE.md` |

## Notas de execução

- Não editar `requirements.txt`, `pyproject.toml`, `FINDINGS.md` ou qualquer `.py`.
  Escopo é `README.md` + `.markdownlint.jsonc` (novo).
- Não reformatar nada além do que o `--fix` mecânico faz (P1b) + os 6 pontos exatos de
  P2. Não tocar espaçamento/quebra de linha fora do que os comandos acima produzem.
- Carregar `superpowers:verification-before-completion` antes de marcar qualquer ID como
  `done`; colar a saída real dos comandos no `STATE.md`, não parafrasear.
- Retorno: uma linha por ID (P1a, P1b, P2a, P2b, P3). Detalhe completo no `STATE.md`.
