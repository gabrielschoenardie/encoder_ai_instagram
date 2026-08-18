<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AA: README — launcher.ps1 como caminho canônico de entrada

Data: 2026-08-17 | Ciclo: AA | Origem: pedido direto do usuário, via
`superpowers:brainstorming` (path bounded, aprovado em chat — sem spec
file, conforme a skill).

## Diagnóstico

`README.md` hoje descreve **três** histórias de entrada sem hierarquia
clara: (1) "Início Rápido" (linhas 77-129) destaca `git clone` + `pip
install -r requirements.txt` + `python Reels_Encoder_v2_FINAL.py`; (2)
"Instalação Completa" + "Instalação via pip" (linhas 210-250) repete o
venv manual e acrescenta `pip install .` → comando `reels-encoder`; (3)
`launcher.ps1` (linhas 191-206) fica enterrado dentro da seção
"Portabilidade", depois de Requisitos — mas é o único caminho com **zero
configuração manual** (cria venv local, valida FFmpeg, abre o wizard).

Decisão do usuário (brainstorming, aprovada): `launcher.ps1` é O
caminho canônico divulgado no Início Rápido — não "canônico só no
Windows com pip como alternativa igual", e sim o único destaque, com
`pip install`/`reels-encoder` reenquadrado como seção secundária
explícita ("Instalação Alternativa") para outros SOs ou uso avançado.
Escopo fechado: só a reestruturação do caminho de entrada + fix de
número — nenhuma feature nova (interrupção/progresso do batch, Ciclos
X/Y) entra nesta passada.

Achado de acurácia (fora da reestruturação, mas no mesmo arquivo):
`ui/` tem hoje **130** testes (`python -m pytest ui/ -q --collect-only`
→ `130 tests collected`), README diz "111 testes" em 3 lugares.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AA1 | Reescrever "⚡ Início Rápido" (linhas ~77-129): `launcher.ps1` como único passo 1/2 (`git clone` + `.\launcher.ps1`), com 1 frase do que ele faz (venv local, valida FFmpeg, abre wizard) + exemplo direto por perfil (`-InputFile ... -Profile cinematic`). Manter os blocos de exemplo de flags CLI existentes como referência (não como passo concorrente), com 1 linha de saída apontando para "Instalação Alternativa". Atualizar a Tabela de Conteúdo (linha ~19-35) para nomear a seção alternativa como "Instalação Alternativa". | `executor` | `README.md` | seção reescrita conforme design aprovado; nenhum conteúdo técnico perdido (flags, exemplos) — só reordenado/reenquadrado |
| AA2 | Em "📦 Portabilidade — FFmpeg embarcado" (linhas ~170-206): remover a sub-seção "Launcher portátil (`launcher.ps1`)" do final (linhas ~191-206, redundante com AA1) e substituir por 1 linha de cross-link para o Início Rápido. Manter intocado o resto da seção (resolvedor de 3 níveis, tabela por plataforma). | `executor` | `README.md` | sub-seção "Launcher portátil" não duplica mais o conteúdo de AA1; resto da seção idêntico |
| AA3 | Renomear "🚀 Instalação Completa" (linha ~210) para "🚀 Instalação Alternativa (Python puro / outros SOs)"; manter os dois blocos técnicos existentes (venv manual + `pip install .` → `reels-encoder`) como estão, só reenquadrados como caminho secundário — ajustar a frase de abertura da seção para deixar claro que é a rota pra quem não está no Windows ou não quer o wrapper PowerShell. | `executor` | `README.md` | heading + frase de abertura mudados; conteúdo técnico dos dois blocos preservado (comandos idênticos) |
| AA4 | Fix de número: "111 testes" → "130 testes" nas 3 ocorrências (estrutura de arquivos ~linha 456, seção Testes ~linhas 650/663). Confirmar a contagem rodando `python -m pytest ui/ -q --collect-only` antes de commitar (o número pode ter mudado desde o diagnóstico deste PLAN). | `executor` | `README.md` | grep por `111 testes` sem match; grep pelo número real confirmado bate nas 3 ocorrências |
| AA5 | Commit final + verificação de que o README renderiza sem link quebrado no sumário (âncoras batem com os headings renomeados). | `executor` | `README.md` | commit feito; `grep -n "^#\{2,3\} "` headings batem 1:1 com as âncoras da Tabela de Conteúdo tocadas em AA1/AA3 — **done**, commit `d9ca99d`; fix-round `22eb7e3` (Orquestrador achou conteúdo técnico do `launcher.ps1` — venv/2 abas WT/fallback/nota CRF — perdido na AA2 durante revisão; restaurado no Início Rápido) |

## Notas de execução

- Escopo estrito: só `README.md`. Não tocar `launcher.ps1`,
  `docs/launcher-portavel-reels-encoder.md`, `pyproject.toml` ou
  qualquer `.py`.
- Não remover nenhum comando/flag/exemplo técnico já documentado — a
  tarefa é reordenar e reenquadrar hierarquia, não cortar conteúdo.
- Ordem: AA1 → AA2 → AA3 podem ser feitos na mesma passada (mesmo
  arquivo, seções distintas e não sobrepostas); AA4 é independente;
  AA5 fecha e commita.
- Path bounded do brainstorming: sem spec file em
  `docs/superpowers/specs/`; design foi aprovado diretamente em chat.
- Retorno do agente: ponteiro + veredito (uma linha por ID + sha do
  commit). Detalhe vai para `STATE.md`.
