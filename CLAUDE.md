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
| ler logs, saída de ffprobe, stack traces, grep no codebase | `leitor` |

A escolha entre `executor` e `executor-pesado` é do Orquestrador, registrada na coluna `agente alvo` do PLAN.md.

## Handoff

Nenhum papel lê o histórico de conversa do outro. Todo estado passa por markdown em `.claude/memory/`: PLAN.md → STATE.md → VALIDATION.md, mais FINDINGS.md para bugs fora do escopo atual.

## Anti-escopo

Não refatorar. Não adicionar features. Não criar abstrações. Não escrever comentários narrativos. Só o que o PLAN.md pede.

## Regras de Ouro do encoder

Toda decisão de encode obedece `.claude/skills/instagram-reels-encoder/SKILL.md` § "Regras de Ouro — Nunca Violar". Não copiar o conteúdo para cá — carregar a skill quando a tarefa tocar o pipeline. Metodologia Gabriel: validação passo a passo, análise adaptativa sem presets fixos, zero recompressão.
