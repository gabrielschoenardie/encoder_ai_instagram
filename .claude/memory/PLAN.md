<!-- Escreve: Orquestrador. Lê: executor, executor-pesado. -->
# PLAN — Ciclo AP: fixar a versão do Pester no CI (fecha UF3)

Data: 2026-09-03 | Ciclo: AP | Origem: `.claude/memory/FINDINGS.md` § `UF3` (Ciclo U, 2026-08-15), adiado desde então.

## Diagnóstico

`.github/workflows/ci.yml` (job `pester`) instala e importa com
`-MinimumVersion 5.5.0`, sem teto. `Install-Module`/`Import-Module` com
`-MinimumVersion` resolvem para a **mais alta disponível** no runner, então o CI segue
silenciosamente o major mais novo que o GitHub decidir empacotar.

### Remedido hoje — os números do `UF3` ainda valem

Ao contrário do `I-a` (cujo débito de 58 violações já não existia quando o Ciclo AO foi
medir), aqui a medição de 2026-09-03 confirma o registro do Ciclo U:

| onde | Pester disponíveis | carregado | banner |
|---|---|---|---|
| CI, leg ubuntu | 6.1.0, 5.9.0 | **6.1.0** | `Running tests from 2 files.` |
| CI, leg windows | 6.1.0, 5.9.0, 3.4.0 | **6.1.0** | `Running tests from 2 files.` |
| máquina do usuário | **só 5.7.1** | 5.7.1 | `Starting discovery in 2 files.` |

Evidência: run `33758949898`, step `Install Pester` (saída do
`Get-Module Pester -ListAvailable`) e step `Run Pester`. O banner é o discriminante entre
os majors — 5.x imprime `Starting discovery in`, 6.x imprime `Running tests from`.

**91 testes passam nos dois majors.** Contagem idêntica local e CI, o que descarta a
hipótese de o major 6 estar deixando de coletar algo em silêncio — se estivesse, a
contagem divergiria. O problema do `UF3` não é a suíte estar quebrada; é ninguém ter
escolhido sob o que ela roda.

É a mesma classe de defeito que o Ciclo AJ chamou de "verde pelo motivo errado", só que em
versão de dependência em vez de caminho de código: local e CI ficam verdes sob frameworks
diferentes, e uma quebra de compatibilidade futura do Pester chegaria como falha surpresa
num run que não mudou nada do repo.

## Desenho

**Decisão do usuário: fixar `5.7.1`** — a versão que a máquina de desenvolvimento já tem.
O CI passa a rodar exatamente o que o desenvolvedor roda, eliminando o split sem exigir
instalação nova. Escolher `6.1.0` teria mantido o split invertido, a menos que o local
fosse atualizado junto.

Trocar `-MinimumVersion 5.5.0` por `-RequiredVersion 5.7.1` nos **dois** pontos:
`Install-Module` e `Import-Module`. Trocar só um deixaria o `Import-Module` livre para
pegar a 6.1.0 pré-instalada no runner — o pin do install não vincula o import.

O pin é auto-verificável por construção: os runners **não** trazem a 5.7.1 (têm 6.1.0,
5.9.0 e, no Windows, 3.4.0), então `Import-Module -RequiredVersion 5.7.1` falha alto se o
install não tiver trazido a versão certa. Não é preciso step de asserção separado.

Manter o `Get-Module Pester -ListAvailable` do step de install: é o que deixa no log o
registro do que havia no runner, e é a evidência que tornou esta medição possível.

## Tarefas

| ID | tarefa | agente alvo | arquivos | critério de done |
|----|--------|-------------|----------|-------------------|
| AP1 | No job `pester` do `ci.yml`: `Install-Module Pester -MinimumVersion 5.5.0` → `-RequiredVersion 5.7.1`, e `Import-Module Pester -MinimumVersion 5.5.0` → `-RequiredVersion 5.7.1`. Duas linhas. Não tocar em `-Force`, `-Scope`, `-SkipPublisherCheck`, no `Get-Module`, no `Invoke-Pester`, nem nos outros jobs. | executor | `.github/workflows/ci.yml` | `git diff --stat` mostra 1 arquivo, 2 linhas |
| AP2 | Provar que `-RequiredVersion` vincula de fato, localmente: (a) `Import-Module Pester -RequiredVersion 5.7.1` carrega 5.7.1; (b) `Import-Module Pester -RequiredVersion 9.9.9` falha alto em vez de cair para outra versão; (c) a suíte roda sob o pin com `91 passed`. Registrar em `STATE.md`. | executor | `.claude/memory/STATE.md` | 3/3 medidos, com a saída real de cada um |
| AP3 | Fechar `UF3` com CI real verde, confirmando no log que o banner virou o de 5.x e que a contagem seguiu 91. | Orquestrador | `.claude/memory/FINDINGS.md` | log real do CI |

## Por que o AP2 existe

Mesma razão do AO2: CI verde depois da mudança não prova nada — já estava verde antes, sob
a 6.1.0. O que precisa ser provado é que o **flag vincula**, ou seja, que
`-RequiredVersion` falha em vez de degradar para outra versão quando a pedida não está lá.
Sem o item (b), um pin escrito errado ficaria verde por o runner ter alguma versão
utilizável, que é a doença que o ciclo veio curar.

## Critério de aceite decisivo — o banner

A prova de que o pin pegou **não** é o CI ficar verde: é o log do job `Run Pester` mudar
de `Running tests from 2 files.` (6.x) para `Starting discovery in 2 files.` (5.x), com a
contagem seguindo em `Tests Passed: 91`. Verde com o banner de 6.x significa que o pin não
vinculou e o ciclo falhou, mesmo com todos os jobs `success`.

## Critérios de aceite

- `.github/workflows/ci.yml` muda em **exatamente duas linhas**, ambas no job `pester`.
- Nenhum `.py`, nenhum `.ps1`, nenhum arquivo de teste alterado. Este ciclo não corrige
  teste — se algum quebrar sob a 5.7.1, isso é achado novo e o ciclo para para eu decidir.
- Suíte Python: `461 passed`, inalterada (este ciclo não a toca).
- CI real verde nos 7 jobs, **com o banner de 5.x nas duas pernas do `pester`** e
  `Tests Passed: 91` em cada uma.

## Notas de execução

- Se `Install-Module Pester -RequiredVersion 5.7.1` falhar em algum runner por a versão
  não estar na PSGallery, **pare e reporte**. Não afrouxar o pin para `-MinimumVersion`
  nem trocar de versão por conta própria — a escolha da versão é decisão registrada do
  usuário neste plano.
- O item (b) do AP2 vai gerar erro no console de propósito. É o resultado esperado;
  capture a mensagem, não a trate como falha do ciclo.
- Não adicionar matriz de versões de Pester. Foi oferecida ao usuário e recusada em favor
  do pin único.
- Não fechar o ciclo com base em execução local. A prova é log real do CI, e
  especificamente o banner.
- Retorno: ponteiro + veredito, uma linha por ID + SHA.
