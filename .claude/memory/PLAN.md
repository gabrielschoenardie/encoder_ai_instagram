<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AT: caminho da UI passa pela mesma validação de args (fecha ALF1)

Data: 2026-09-03 | Ciclo: AT | Origem: `.claude/memory/FINDINGS.md` § `ALF1` (Ciclo AL, 2026-08-25), aberto desde então. Último da fila do usuário.

## Diagnóstico

Lido no código, não presumido do achado. Há **duas** fontes de `args` em
`Reels_Encoder_v2_FINAL.py`, e só uma é validada:

- **CLI:** `parse_cli()` (`:4381`) chama `build_parser().parse_args()` e então roda uma
  checagem de consistência (`:4385`): se `args.output_dir` está setado mas `args.batch is
  None`, `parser.error(...)` aborta com exit 2.
- **UI:** o bloco de UI de `main()` (`:4431`) faz `args = run_launcher(...)` (`:4437`),
  substituindo `args` por um `argparse.Namespace` que `EncodeConfig.to_namespace()`
  (`ui/config.py:109`) constrói via `argparse.Namespace(**model_dump())` — **puro, sem
  passar por `parse_cli()` nem por qualquer validação de consistência.**

É aquisição de argumentos contornando a validação de argumentos. As duas fontes deveriam
convergir para a mesma checagem; hoje a checagem mora dentro de `parse_cli()`, que o
caminho da UI nunca toca.

### Confirmado inalcançável hoje — mas latente por construção

Varredura de `ui/launcher.py`: `cfg.output_dir` só é atribuído em contexto de batch —
`_flow_batch:146` e `_flow_advanced:182`, ambas sob `preset_batch`/`is_batch`. O launcher
**não consegue** montar hoje a combinação `output_dir` sem `batch`, então o `parser.error`
nunca dispararia mesmo se fosse chamado. Não é bug alcançável; é assimetria estrutural: a
validação e a construção do Namespace vivem em lugares diferentes, e nada obriga um fluxo
futuro do launcher a respeitar a regra. Um `_flow_*` novo que setasse `output_dir` fora de
batch entregaria um Namespace inválido direto ao dispatch, sem aviso.

Severidade S4 pela inalcançabilidade — o valor do ciclo é fechar a assimetria antes que um
fluxo novo a torne alcançável, não consertar um crash de hoje.

## Desenho

Uma única função de validação, compartilhada pelas duas fontes. Extrair a checagem inline
de `parse_cli()` para `_validate_args_consistency(args) -> Optional[str]`, que devolve a
mensagem de erro ou `None` — sem depender do objeto `parser`, para poder ser chamada dos
dois lados.

```python
def _validate_args_consistency(args) -> Optional[str]:
    """Checagens de consistência partilhadas pela CLI e pelo caminho do launcher.
    Devolve a mensagem de erro, ou None se args é consistente."""
    if args.output_dir and args.batch is None:
        return (
            "--output-dir só se aplica a --batch. Em modo single-file, a saída "
            "vai sempre para a pasta do input; use --batch <pasta> se quiser "
            "redirecionar o destino."
        )
    return None
```

- `parse_cli()`: substitui o `if` inline por `msg = _validate_args_consistency(args); if
  msg: parser.error(msg)`. Comportamento idêntico ao de hoje (exit 2, mesma mensagem) —
  os testes existentes de `parse_cli` provam que não regride.
- Caminho da UI (`main()`, logo após `args = launched`): `msg =
  _validate_args_consistency(args); if msg: console.print(f"[red]Erro:[/red] {msg}");
  sys.exit(2)`. Mesmo exit 2, mensagem consistente.

**Por que não validar no `EncodeConfig` (pydantic):** poria a regra em dois lugares
(pydantic para UI, `parse_cli` para CLI) — que é exatamente a duplicação de fonte de
verdade que o achado denuncia. Uma função só, chamada pelos dois caminhos, é o mínimo que
fecha a assimetria em vez de trocá-la de forma.

`Optional` já está importado (`:86`). Nenhuma dependência nova.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AT1 | Extrair `_validate_args_consistency(args)`; `parse_cli()` passa a chamá-la; o caminho da UI em `main()` (após `args = launched`) passa a chamá-la e `sys.exit(2)` com mensagem se ela retornar erro. Só `Reels_Encoder_v2_FINAL.py`. | executor | `Reels_Encoder_v2_FINAL.py` | função extraída, dois call sites, comportamento da CLI idêntico |
| AT2 | Testes, todos por chamada direta — sem invocar encode, sem ffmpeg (lição do `AIF1`): (a) `_validate_args_consistency` devolve `None` para `input` só, `batch` só, `batch`+`output_dir`; (b) devolve msg com `--batch` para `output_dir` sem `batch`; (c) **teste-ponte**: `EncodeConfig(input="x.mp4", output_dir="/d", batch=None).to_namespace()` passado à função é pego — prova que o Namespace que o launcher produz está sujeito à mesma validação; (d) **teste de wiring**: `main()` com `parse_cli` monkeypatchado para devolver `EncodeConfig(ui=True).to_namespace()`, `ui.preflight.missing_ffmpeg_binaries` → `[]`, e `ui.launcher.run_launcher` → Namespace inválido (`output_dir` sem `batch`), afirma `SystemExit` code 2. | executor | `enhance/test_output_dir_and_pipeline_tag.py` (ou arquivo de teste próprio do ALF1) | 4 grupos verdes; os testes existentes de `parse_cli` seguem verdes |
| AT3 | Matriz de mutação: M1 = deletar a chamada no caminho da UI → o teste de wiring (d) fica vermelho, os de `parse_cli` seguem verdes. M2 = deletar a chamada em `parse_cli` → `test_output_dir_without_batch_exits_with_usage_error` fica vermelho. Aplicar, medir, **reverter** cada um. Tabela em `STATE.md`. | executor | `.claude/memory/STATE.md` | 2/2 mutantes mortos por testes distintos; `git diff --stat -- Reels_Encoder_v2_FINAL.py` só a mudança do AT1 ao fim |
| AT4 | Fechar `ALF1` com CI real verde. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI |

## Por que o AT3 existe — a lição do AJF3

O perigo específico deste ciclo: extrair a função, chamá-la em `parse_cli`, e **esquecer**
de ligá-la no caminho da UI. Todos os testes de função (a,b,c) ficariam verdes mesmo assim,
porque exercitam a função direto — e o bug (caminho da UI sem validação) continuaria
exatamente igual. Só o teste de wiring (d) prova a ligação, e o mutante M1 prova que (d)
de fato falha quando a ligação some. Sem M1, o ciclo poderia entregar "verde pelo motivo
errado" — a doença que o `AJF3` denunciou.

## Critérios de aceite

- Só `Reels_Encoder_v2_FINAL.py` (produto) e o arquivo de teste mudam. `ui/launcher.py`,
  `ui/config.py` **não** são tocados — a correção é a validação convergir, não mexer em
  como o launcher monta o Namespace.
- Comportamento da CLI idêntico: mesma mensagem, mesmo exit 2 para `output_dir` sem
  `batch`. Os três testes existentes de `parse_cli` seguem verdes sem alteração.
- Teste de wiring (d) verde, e vermelho sob o mutante M1 (validação da UI removida).
- Os 2 mutantes mortos por testes **distintos** — M1 pelo teste de wiring, M2 pelo teste
  de CLI. Se um único teste mata os dois, a cobertura não distingue os dois call sites.
- Nenhum teste chama `main()` de um jeito que exija ffmpeg no PATH — o teste (d) usa
  monkeypatch de `missing_ffmpeg_binaries` para passar o preflight sem binário real.
- Suíte Python: `461 passed` + os testes novos, sem regressão.
- CI real verde nos jobs de `ci.yml` e `pylint.yml`.

## Notas de execução

- Não tocar em `ui/launcher.py` nem `ui/config.py`. `to_namespace()` continua puro; a
  validação é responsabilidade de quem consome o Namespace, e o ponto do ciclo é que os
  dois consumidores usem a mesma.
- O teste de wiring (d) precisa passar pelo preflight de `main()` (`:4408`) sem ffmpeg:
  monkeypatch `ui.preflight.missing_ffmpeg_binaries` para devolver `[]`. O
  `dependency_error_card` não é chamado quando a lista é vazia.
- `EncodeConfig` tem os campos `ui` e `hardware_info` (`ui/config.py:93-94`), então
  `EncodeConfig(ui=True).to_namespace()` produz um Namespace que dispara o bloco de UI com
  `hardware_info=False` — não precisa construir o Namespace à mão.
- Reverter cada mutante do AT3 antes do próximo; `git diff --stat --
  Reels_Encoder_v2_FINAL.py` ao fim deve mostrar só a mudança do AT1.
- Checar o exit code real do `pytest`, nunca o de um `| tail` — armadilha registrada em
  `STATE.md` § "Ciclo AP", repetida no `AR3`.
- Ao anexar ao `STATE.md`, começar com `## Ciclo AT` e cabeçalho de tabela.
- **Nunca `git add -A` nem `git add .`** — há arquivos não rastreados
  (`961576A_Hollywood_2Pass.qc.html`, `961576A_Hollywood_2Pass.qc.json`, `docs/*.md` novos,
  `testResults.xml`, `videos/`). Adicionar por caminho explícito.
- Não fechar com base em execução local. A prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
