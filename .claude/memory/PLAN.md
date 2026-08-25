<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AK: pinar os `.cube` e colocar `tools/` no CI (AJF1)

Data: 2026-08-25 | Ciclo: AK | Origem: `.claude/memory/FINDINGS.md` § `AJF1` (aberto no Ciclo AJ pela revisão final do branch).

## Diagnóstico

`AJF1` foi registrado como "`tools/` está fora da seleção de testes do CI".
A investigação do Orquestrador mostrou que a causa é mais funda e que a
correção óbvia (só acrescentar `tools/` à linha do `ci.yml`) **deixaria os
dois jobs ubuntu vermelhos na hora**.

Medido nesta sessão, no commit `92ae2e6`:

| arquivo `.cube` (tracked) | blob | worktree | delta |
|---|---|---|---|
| `FilmLook_Portra400_SkinPriority_D65.cube` | 980725 | 1016677 | 35952 |
| `HollywoodCinema_Ultimate_v6.7B-W80_1.5IRE_Instagram8bit_NeutralShadows.cube` | 970412 | 1006351 | 35939 |
| `HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube` | 970401 | 1006340 | 35939 |
| `HollywoodCinema_Ultimate_v6.8_3.1-96IRE_Instagram8bit_NeutralShadows.cube` | 970414 | 1006353 | 35939 |

O delta de cada arquivo é exatamente a contagem de `\r` — o blob guarda
**LF**, o worktree Windows mostra **CRLF**. Não existe `.gitattributes` no
repo e `core.autocrlf=true` na máquina local, então a conversão é feita
por git no checkout, por plataforma.

`tools/generate_hollywood_lut_cooler.py:162` escreve o LUT com
`newline="\r\n"` — **CRLF é a intenção declarada do gerador**, não um
acidente. E `tools/test_generate_hollywood_lut_cooler.py::test_structure`
afirma `raw.count(b"\r\n") == DATA_LINES + 2`, ou seja, testa exatamente
essa intenção.

Consequência: num runner Linux (autocrlf desligado, sem `.gitattributes`)
o arquivo é entregue em LF, `test_structure` mede 0 e falha. O defeito não
é o teste — é o artefato versionado ter sido normalizado para LF na hora
do commit, divergindo do que o gerador produz.

**Por que isso também explica o "artefato de CRLF local" do Ciclo AJ:** era
a mesma dependência de plataforma, vista do outro lado.

## Desenho

Ordem importa. Pinar os bytes **antes** de ligar `tools/` no CI:

1. `.gitattributes` com `*.cube -text` desliga qualquer conversão de EOL
   para esses arquivos. Como o worktree local já está em CRLF, re-adicionar
   os quatro arquivos faz o blob passar a guardar CRLF verbatim — que é o
   que o gerador emite e o que o teste espera, em qualquer plataforma.
2. Só então `tools/` entra na seleção do `ci.yml`.

Fazer na ordem inversa deixa o CI vermelho. Pinar sem re-adicionar congela o
LF de hoje e quebra o teste no **Windows** em vez do Linux.

Efeito colateral desejável: `test_generator_is_deterministic` roda o gerador
e **sobrescreve o `.cube` versionado**. Com blob e saída do gerador
byte-idênticos, rodar a suíte deixa de sujar a árvore de trabalho.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AK1 | Criar `.gitattributes` com `*.cube -text` e renormalizar os 4 `.cube` para que o blob guarde CRLF. Atualizar `AJF1` no `FINDINGS.md` com a causa raiz medida. | executor | `.gitattributes`, os 4 `*.cube`, `.claude/memory/FINDINGS.md` | pendente |
| AK2 | Incluir `tools/` na seleção de testes do `ci.yml`. | executor | `.github/workflows/ci.yml` | pendente |
| AK3 | Confirmar verde no CI real nos 4 jobs `Tests` (ubuntu **e** windows) e fechar o ciclo. | executor | `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md` | pendente |

## Critérios de aceite

- Para os 4 arquivos: `git cat-file -s HEAD:<arquivo>` **igual** ao tamanho
  do arquivo no worktree. Hoje diferem pelo número de `\r`.
- `python -m pytest tools/ -q` → `10 passed`, e `git status --short` limpo
  depois de rodar (nenhum `.cube` modificado).
- Seleção nova do CI local: `python -m pytest test_render_queue.py enhance/ ui/ tools/ -q` → `435 passed`.
- CI real: os 4 jobs `Tests` `success`, com `435 passed` no sumário — os
  425 de hoje + os 10 de `tools/`.

## Notas de execução

- **Não tocar em `Reels_Encoder_v2_FINAL.py`.** Nada neste ciclo é de produto
  de encode; é versionamento de artefato e configuração de CI.
- **Não alterar a lógica de `tools/test_generate_hollywood_lut_cooler.py`.**
  O teste está certo; quem estava errado era o byte versionado.
- `-text` (e não `binary`): mantém o diff legível, só desliga conversão de EOL.
- **Não fechar o ciclo com base em execução local.** Vale a mesma regra do
  Ciclo AJ: a prova é log real do CI. Aqui com um requisito a mais — o job
  **ubuntu** é o que reprovaria hoje, então é ele que precisa aparecer verde.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
