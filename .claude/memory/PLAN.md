<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Fechar J-a: `requirements.txt` aponta para o `pyproject`

Data: 2026-07-25 | Ciclo: infra | Origem: `FINDINGS.md` J-a, reclassificado

**Objetivo:** `MANUAL_INSTALACAO.txt:119` manda o usuário final rodar
`pip install -r requirements.txt`. No commit `7dfdb08` (14:14) o CI passou a instalar
com `pip install -e ".[opencv,dev]"` e **deixou de tocar o `requirements.txt`**. O
caminho de instalação que o manual manda seguir não é mais exercitado por nada.

O `requirements.txt` está correto hoje — tem os mesmos 9 pacotes do `pyproject`. O
problema não é o estado, é que nada avisa quando ele divergir. É a mesma classe de
defeito dos ciclos I, J e K (lista mantida à mão divergindo em silêncio), e desta vez
foi introduzida pelo próprio ciclo J.

**Correção:** o `requirements.txt` deixa de ser uma segunda lista e passa a apontar para
a primeira. Depois disso `pip install -r requirements.txt` e `pip install -e .` são
literalmente a mesma resolução.

**Escopo fechado (arquivos permitidos):**
- `requirements.txt` — substituição integral do conteúdo
- `.github/workflows/ci.yml` — só acrescentar um step no job `tests`

**Fora de escopo:** `MANUAL_INSTALACAO.txt` (ver L3 — é verificação, não edição),
`pyproject.toml`, as 4 falhas locais de plataforma, o achado I-a. Bug fora do escopo →
uma linha em `FINDINGS.md`, sem investigar.

## Tabela de tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|------------------|
| L1 | Substituir todo o conteúdo do `requirements.txt` por um cabeçalho curto de comentário + a linha `-e .[opencv]`. O comentário deve dizer que a lista de dependências vive em `pyproject.toml` e que este arquivo existe só porque `MANUAL_INSTALACAO.txt` o referencia — para ninguém "consertar" reexpandindo a lista. | `executor` | `requirements.txt` | `pip install --dry-run -r requirements.txt` resolve sem erro e instala o mesmo conjunto que `pip install --dry-run -e ".[opencv]"` |
| L2 | No job `tests` do `ci.yml`, acrescentar um step logo após "Install dependencies": `pip install --dry-run -r requirements.txt`, nomeado de forma a deixar claro que valida o caminho do usuário final. Não substituir o install existente. | `executor` | `.github/workflows/ci.yml` | step novo presente; o step "Install dependencies" intacto |
| L3 | **Verificação, não edição.** Ler `MANUAL_INSTALACAO.txt` linhas ~100-125 e ~250 e confirmar que as instruções continuam verdadeiras com o novo `requirements.txt` (o arquivo continua existindo; `pip install -r requirements.txt` continua funcionando). Reportar no STATE.md o que dizem essas linhas. Se alguma ficou falsa, **não corrija** — registre `blocked` com o texto exato. | `executor` | — (só leitura) | STATE.md com o veredito e as linhas citadas |
| L4 | Validar `yaml.safe_load` no `ci.yml` e rodar `python -m pytest enhance/ ui/ -q`. | `executor` | — | YAML sai 0; suíte no baseline `4 failed, 342 passed` |

## Notas de execução

- **Por que L2 existe.** Sem ele, o `requirements.txt` volta a ser um arquivo que
  ninguém executa — que é exatamente o defeito que este ciclo fecha. Um `--dry-run` é
  barato (não instala nada) e garante que o arquivo continua parseável e resolvível nas
  duas versões da matriz. Se alguém reexpandir a lista à mão no futuro com um pacote
  inexistente, o CI acusa.
- **A sintaxe `-e .[opencv]` num requirements file não leva aspas.** Aspas são
  necessidade do shell, não do formato. Não copie o `".[opencv,dev]"` do `ci.yml`.
- **Não inclua o extra `dev`** no `requirements.txt`: `pytest` e `pytest-timeout` são
  ferramenta de desenvolvimento, não dependência de quem só quer rodar o encoder.
- **Carregue `superpowers:verification-before-completion`** antes de marcar qualquer ID
  como `done` e cole no STATE.md a saída real do comando. Em L1, cole a comparação dos
  dois `--dry-run` — é o critério inteiro do item.
- Retorno: uma linha por ID. Detalhe no STATE.md.
