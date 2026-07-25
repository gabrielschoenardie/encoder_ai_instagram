# CLAUDE.md — Política de Orquestração

Camada de política. Conhecimento de encoder vive na skill `instagram-reels-encoder`; estado de trabalho vive em `.claude/memory/` (roteamento em `.claude/memory/README.md`).

## Contrato de papéis

- **Orquestrador** (sessão principal): planeja, decide escopo e arquitetura, escreve `.claude/memory/PLAN.md`, revisa STATE/VALIDATION. Nunca implementa.
- **Executor** (`executor` sonnet / `executor-pesado` opus): implementa apenas o que está em `.claude/memory/PLAN.md`. Nunca decide escopo.
- **Validador** (`validador` haiku): só mede e reporta. Nunca corrige.
- **Leitor** (`leitor` haiku): só extrai trechos. Nunca interpreta.

## Delegação obrigatória

Qualquer tarefa abaixo DEVE ser delegada via Task ao agente correspondente. O Orquestrador não usa Edit/Write em código-fonte; escreve apenas em `.claude/memory/` e configuração de `.claude/`.

| tarefa | agente |
| --- | --- |
| escrever/editar código | `executor` |
| refactor multi-arquivo, mudança cruzando `enhance/` + pipeline, execução sem supervisão | `executor-pesado` |
| rodar `validate_encode.sh` / `measure_vmaf.sh`, veredito de encode | `validador` |
| QC de entrega final, veredito + flag a corrigir | `encode-validator` |
| mudou menu/preset/seção em `ui/launcher.py` | `ui-flow-reviewer` |
| ler logs, saída de ffprobe, stack traces, grep no codebase | `leitor` |

A escolha entre `executor` e `executor-pesado` é do Orquestrador, registrada na coluna `agente alvo` do PLAN.md.

## Handoff

Nenhum papel lê o histórico de conversa do outro. Todo estado passa por markdown em `.claude/memory/`: PLAN.md → STATE.md → VALIDATION.md, mais FINDINGS.md para bugs fora do escopo atual.

## Economia de contexto

Agente devolve **ponteiro + veredito**, nunca o conteúdo: detalhe vai para `.claude/memory/`, o retorno traz status por ID e uma linha. Orquestrador lê o arquivo se precisar do detalhe.

PLAN.md **não transcreve** conteúdo de skill ou de reference. Cita a origem — `skill: instagram-reels-encoder § Cineon 5 nós` — e o executor carrega a skill sozinho. Transcrever gasta contexto Opus para poupar contexto Sonnet, que é o inverso do que se quer.

Skills nos agentes são nomeadas explicitamente com gatilho no próprio agent file (`executor`, `executor-pesado`). Não há camada de descoberta em subagente: `superpowers:using-superpowers` se auto-desliga quando despachada como subagente.

## Anti-escopo

Não refatorar. Não adicionar features. Não criar abstrações. Não escrever comentários narrativos. Só o que o PLAN.md pede.

## Regras de Ouro do encoder

Toda decisão de encode obedece `.claude/skills/instagram-reels-encoder/SKILL.md` § "Regras de Ouro — Nunca Violar". Não copiar o conteúdo para cá — carregar a skill quando a tarefa tocar o pipeline. Metodologia Gabriel: validação passo a passo, análise adaptativa sem presets fixos, zero recompressão.
