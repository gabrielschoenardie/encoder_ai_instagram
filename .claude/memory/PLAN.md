<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AL: extrair `build_parser()` / `parse_cli()` de `main()` (R8, fecha AJF2)

Data: 2026-08-25 | Ciclo: AL | Origem: ruling R8 da revisão final do Ciclo AJ (PR #43) + `.claude/memory/FINDINGS.md` § `AJF2`.

## Diagnóstico

O Ciclo AJ deixou os dois testes de `--output-dir` passando em CI, mas ao
custo de um andaime: `monkeypatch` de `ui.preflight.missing_ffmpeg_binaries`,
mais `monkeypatch` de `R.shutil.which` para tapar o branch de fallback, mais
um comentário avisando que tudo isso só funciona enquanto o
`from ui.preflight import ...` continuar **local dentro de `main()`**.

A causa de todo esse andaime é estrutural: `main()`
(`Reels_Encoder_v2_FINAL.py:4161`) constrói o parser inline nas linhas
4162-4377, chama `parse_args()` em 4378 e faz a validação de consistência
em 4380-4385. Não existe seam para testar argparse sem executar `main()`
inteiro — e `main()` inteiro passa por preflight de ffmpeg, hardware info,
launcher de UI e dispatch.

Consequências medidas:

- Os testes de parser exercitam ffmpeg sem ter nada a ver com ffmpeg (`AIF1`,
  Ciclo AJ).
- `AJF2`: `test_batch_without_output_dir_does_not_trigger_usage_error` é
  tautológico — no argv dele `args.output_dir` é `None`, então o guard nunca
  pode disparar. Verificado por mutação na revisão final do AJ: o teste
  continua verde com o guard deletado.
- O patch de `ui.preflight` só intercepta por acidente feliz de o import ser
  local; o Pylint não desabilita `import-outside-toplevel`, então uma
  limpeza futura quebra o teste sem ninguém ligar os pontos.

## Desenho

Extrair dois seams do `main()`, sem renomear nada que exista hoje:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)   # corpo atual, 4162-4377, verbatim
    ...
    return parser


def parse_cli(argv=None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.output_dir and args.batch is None:
        parser.error(...)                   # mensagem atual, verbatim
    return args


def main():
    args = parse_cli()
    # daqui para baixo, main() segue idêntico (hardware info, preflight, UI, dispatch)
```

**Fronteira, e por que é aqui:** `parse_cli()` termina na validação de
consistência de argumentos. O bloco `--hardware-info` **fica em `main()`** —
ele imprime perfil de hardware e chama `sys.exit(0)`, é efeito colateral, não
parsing. Preflight de ffmpeg idem.

Com esse seam, os dois testes viram unit tests de argparse de verdade:
chamam `parse_cli([...])` direto, sem `main()`, sem ffmpeg, sem `monkeypatch`.
O andaime inteiro do Ciclo AJ é **deletado**, não adaptado.

E `AJF2` fecha de graça: o teste novo afirma os valores parseados
(`args.batch`, `args.output_dir`), então passa a morrer se o guard for
removido — deixa de ser tautológico.

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AL1 | TDD RED: reescrever os 3 testes de `--output-dir` para chamar `parse_cli()`, sem `monkeypatch`. Devem falhar por `parse_cli` não existir. | executor-pesado | `enhance/test_output_dir_and_pipeline_tag.py` | pendente |
| AL2 | Extrair `build_parser()` e `parse_cli()`; `main()` passa a chamar `parse_cli()`. Suite verde. | executor-pesado | `Reels_Encoder_v2_FINAL.py` | pendente |
| AL3 | Confirmar verde no CI real e fechar o ciclo (`AJF2` corrigido, R8 cumprido). | executor | `.claude/memory/STATE.md`, `.claude/memory/PLAN.md`, `.claude/memory/FINDINGS.md` | pendente |

## Critérios de aceite

- **`--help` byte-idêntico.** Baseline capturado em `def5ac2`: 139 linhas,
  md5 `7dd773cde1f068982e6d97554bacda99`. Um parser extraído que mude o
  `--help` mudou o contrato de CLI — é regressão, não refactor.
- `main` continua exportado com o mesmo nome e assinatura: é o console
  script (`pyproject.toml:37`, `reels-encoder = "Reels_Encoder_v2_FINAL:main"`)
  e `ui/test_packaging.py:32` afirma isso.
- Os testes de `--output-dir` passam **com o PATH sem ffmpeg e sem nenhum
  `monkeypatch`** — é essa a prova de que o acoplamento morreu, não a suíte
  verde na máquina local.
- `grep -c "monkeypatch" enhance/test_output_dir_and_pipeline_tag.py` → os
  patches de `missing_ffmpeg_binaries` e de `shutil.which` não existem mais,
  nem o comentário `# AIF1:` que os explicava.
- Suíte completa: `435 passed`. CI real: os 4 jobs `Tests` `success`.

## Notas de execução

- **Mover, não reescrever.** O corpo do parser (4162-4377) vai verbatim para
  `build_parser()`. Não reordenar argumentos, não reformatar help strings, não
  "melhorar" texto — qualquer um desses quebra o critério do `--help`.
- Não tocar em `.gitattributes`, nos `.cube`, nem no `ci.yml` — são do Ciclo AK.
- Não mexer no bloco de preflight nem no de UI de `main()`. O ciclo é sobre
  criar o seam, não sobre mudar comportamento de runtime.
- TDD de verdade: AL1 tem que falhar antes de AL2 existir, e o relatório
  precisa mostrar a falha.
- **Não fechar o ciclo com base em execução local** — mesma regra dos ciclos
  AJ e AK: a prova é log real do CI.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
