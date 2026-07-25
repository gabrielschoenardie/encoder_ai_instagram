| arquivo | escreve | lê |
|---------------|------------------------------------|---------------------------|
| PLAN.md | Orquestrador | executor, executor-pesado |
| STATE.md | executor, executor-pesado (append) | Orquestrador |
| VALIDATION.md | validador (sobrescreve) | Orquestrador |
| FINDINGS.md | executor, executor-pesado, validador | Orquestrador |

`leitor` é read-only: reporta o achado no retorno; o Orquestrador registra.
