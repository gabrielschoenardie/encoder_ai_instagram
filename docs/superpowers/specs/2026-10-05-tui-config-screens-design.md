# P3C — Telas de configuração da TUI — Design

Data: 2026-10-05 · Status: aprovado em conversa, aguardando revisão do arquivo
Ciclo: P3C (Phase 3, sub-projeto 2 de 4: P3B casca+encode ✓ → **P3C configuração** → P3D batch → P3E acabamento).
Referências obrigatórias: `docs/Phase_2_TUI_Specification.md` §E (teclado), §F (foco), §H HOME, §I SOURCE, §J CONFIGURATION,
§K ADVANCED, §L PREVIEW, §AD (Tools); `docs/superpowers/specs/2026-10-01-tui-shell-encode-design.md` (casca P3B);
`.claude/memory/FINDINGS.md` § "Ciclo P3A" e § "Ciclo P3B". `RE` = `Reels_Encoder_v2_FINAL.py`.

## 1. Objetivo e critério de sucesso

`python -m ui.tui` deixa de usar o wizard de linha: HOME → SOURCE → CONFIGURATION | ADVANCED → PREVIEW → READY → encode
(P3B), tudo em tela cheia.

Pronto quando:

1. **Paridade**: para as mesmas escolhas, o formulário da TUI produz exatamente o mesmo `Namespace` (`EncodeConfig.to_namespace()`) que o wizard de linha (`ui/launcher.py`) com respostas simuladas — teste automático (§7.4).
2. Testes automáticos verdes no CI Windows e Linux; suíte completa sem regressão.
3. Manual no Windows Terminal (§7.7) passa.
4. `ui/launcher.py`, `ui/config.py`, encoder e condutor P3A inalterados; o wizard de linha continua acessível via `--ui` do CLI clássico.

## 2. Decisões fechadas

| ID | Decisão |
|----|---------|
| C-1 | Presets 1, 2 e 5 (arquivo único) completos. Preset 3 e o ramo batch do preset 5 aparecem **desativados** ("chega no P3D"). Preset 4 (Tools) suspende a tela cheia, roda o `_flow_tools` atual e volta à HOME. |
| C-2 | Campos definidos por lista declarativa nova em `ui/tui/forms.py`, espelhando o wizard; wizard não muda; paridade garantida por teste. |
| C-3 | Preflight de binários sobe para **antes** da TUI (como `main()`); `run_launcher` sai do caminho TUI. |
| C-4 | ESC numa tela de configuração volta à anterior mantendo o rascunho; cada preset lembra o próprio rascunho na sessão. Sem "descartar edições" (NB-3). |
| C-5 | READY revalida a existência do input antes do START. |
| C-6 | Ctrl+C em HOME/SOURCE/CONFIGURATION/ADVANCED/PREVIEW → código 130 (consistente com P3B fora do encode). ESC na HOME → 0 + "Cancelado pelo usuário.". |

## 3. Fluxo

```text
python -m ui.tui
  guarda do terminal (P3B) → preflight de binários (código 1 + dependency_error_card) → App(...).run()
     HOME ─1/2/5─▶ SOURCE ─▶ CONFIGURATION (1, 2) | ADVANCED (5) ─▶ PREVIEW ─▶ READY ─▶ ENCODING … (P3B)
       │ 4 → Tools (suspende/retoma) → HOME
       │ 3 → desativado
       └ ESC → sai 0
     PREVIEW ─REVISAR─▶ ADVANCED (base = rascunho atual)
     ESC (SOURCE/CONFIGURATION/ADVANCED/PREVIEW/READY) → tela anterior, rascunho mantido
```

Origem do ESC no PREVIEW/READY: volta para a tela de onde veio (CONFIGURATION ou ADVANCED / PREVIEW).

## 4. Módulos (`ui/tui/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| `forms.py` (novo) | `Field(name, kind, label, options, default_from, lo, hi, step, integer, visible_if, enabled_if)`; formulários `QUICK`, `CINEON`, `ADVANCED` (abas `Source`, `Color/LUT`, `Audio`, `Enhance`, `Export`); rótulos verbatim de `PRESETS`; fábrica do rascunho por preset; regras derivadas (MCTF→off). |
| `widgets.py` (novo) | lógica pura de edição: `choice` (←→ circula opções), `toggle` (SPACE/←→ on↔off), `number` (←→ ± `step` dentro de `[lo, hi]`; dígitos, `.`, `-`, BACKSPACE editam; ENTER/troca de foco confirma), `path` (texto com cursor; imprimíveis inserem, BACKSPACE/DELETE, ←→ cursor; colar = sequência de caracteres; aspas das pontas removidas ao validar). Sem I/O. |
| `state.py` | telas HOME, SOURCE, CONFIGURATION, ADVANCED, PREVIEW; `draft: EncodeConfig` por preset; `focus` por tela; nível de foco do ADVANCED (abas | campos); erros por campo; ação `tools`. |
| `keys.py` | novas teclas: `SPACE`, `BACKSPACE`, `DELETE`, dígitos e caracteres imprimíveis como `Char(c)`. |
| `screens.py` | renderers das 5 telas novas; reutiliza `banner`, `viewer_frame`, `settings_preview`, `quality_row`. |
| `app.py` | inicia na HOME; executa `tools` (suspender/retomar); probe de dimensões no SOURCE fora do reducer. |
| `__main__.py` | guarda → preflight → `App`; sem `run_launcher`. |

## 5. Formulários (espelho do wizard)

Fonte: `ui/launcher.py` (`_flow_quick` 122–128, `_flow_cineon` 131–138, `_flow_advanced` 170–235), `ui/config.py`.

| Form | Campos (ordem do wizard) |
|------|--------------------------|
| QUICK (preset 1; base `preset_quick_ffmpeg`) | Enquadramento `fit` [contain, cover] · FPS `fps` [auto, 24, 25, 30, 60] · Modo `mode` [crf, 2pass] |
| CINEON (preset 2; base `preset_film_cineon`) | Exposure offset `exposure_offset` (−2..+2, passo 0,1) · Saturação `saturation` (0..2, passo 0,05) · Enquadramento `fit` |
| ADVANCED (preset 5; base `EncodeConfig()` ou rascunho atual no REVISAR) | **Source**: Pipeline Cineon `cineon_pipeline` · Enquadramento `fit` · FPS `fps` · Downscale 4K→1080p `scale` [auto, off] · Modo `mode` · Performance `performance` [quality, balanced, speed] — **Color/LUT**: Exposure `exposure_offset` *(se Cineon on)* · Saturação `saturation` *(se Cineon on)* · Hollywood LUT `lut` *(se Cineon off)* · HDR→SDR `hdr` [auto, off] · Tonemap `tonemap` [mobius, reinhard, hable] — **Audio**: Loudnorm `loudnorm` · Monitor EBU `ebu_meter` — **Enhance**: Enhancement `enhance` · AI `enhance_ai` *(se enhance on)* · MCTF `mctf` *(se enhance on e AI on)* · Dither `dither` [auto, on, off] — **Export**: Exibir perfil de hardware `show_hardware` · Threads `threads` (≥ 0, inteiro, passo 1) |

O input (`input`) vem do SOURCE em todos os presets. Rótulos dos campos = textos do wizard sem o "?" final.

Regras: (a) desligar `enhance` ou `enhance_ai` força `mctf = "off"` (igual a `launcher.py:225`); (b) campos de visibilidade condicional ficam fora da navegação quando ocultos e mantêm o valor do rascunho; (c) nunca expostos: `report`, `cineon_lut`, `debug`, `hardware_info`, `ui`, `batch`, `output_dir` (D-07; batch no P3D); (d) cada mudança → `draft.model_copy(update=…)` validado por `EncodeConfig.model_validate`; erro → mensagem inline vermelha, valor anterior mantido.

## 6. Telas

- **HOME (§H)**: `banner` existente · menu com os 5 rótulos verbatim de `PRESETS` (3 em cinza com "chega no P3D", fora da navegação) · painel do fluxo selecionado · faixa SYSTEM (FFmpeg/ffprobe encontrados; `⚠ ffplay` se ausente; "hardware detectado no início do encode"). Teclas ↑↓ ENTER 1–5 ESC. Foco inicial: preset 1 (ou o último usado na sessão).
- **SOURCE (§I)**: no preset 5, seletor "É um batch de pasta?" desativado ("chega no P3D"). Campo de caminho (foco inicial). Status: `VALID` (arquivo existe), `NOT FOUND`, `INVALID` (vazio ou pasta). Metadados: dimensões via `ui.probe.probe_source_dims` (best-effort; falha = `—`) e saída via `EncodeConfig.output_path`. PROGRAM via `viewer_frame` com as dimensões. ENTER com VALID → CONFIGURATION (1, 2) ou ADVANCED (5); ESC → HOME.
- **CONFIGURATION (§J)**: faixa de resumo · formulário do preset · painel PADRÕES (somente leitura: valores do preset que o formulário não pergunta) · ação CONTINUAR. ENTER no último campo ou em CONTINUAR → PREVIEW.
- **ADVANCED (§K)**: barra de abas focável (dois níveis: ↑ no primeiro campo vai às abas; ↓ das abas entra no primeiro campo habilitado; ←→ nas abas troca de aba) · campos da aba · painel SETTINGS (resumo somente leitura do rascunho) · ação CONTINUAR → PREVIEW.
- **PREVIEW (§L)**: `settings_preview` + `quality_row` existentes · ações CONTINUAR (padrão) → READY, REVISAR → ADVANCED com o rascunho atual; ESC → tela de origem.
- Rodapé de cada tela lista só as teclas válidas (regra §E). Foco `▎▸` + `tab.active` (§F); campo desativado mostra o motivo e é pulado.

Tools: `App` para a thread de teclado, restaura `sys.stderr`, sai da captura e fecha o `Live`, restaura o terminal; chama `ui.launcher._flow_tools(console)` inalterado; ao retornar, reabre captura/stderr/`Live`/teclado e volta à HOME. Exceção dentro do Tools → mesma política do P3B (terminal restaurado, código 1).

## 7. Testes

1. `widgets`: cada tipo de campo (choice, toggle, number com limites/passo/digitação, path com cursor, backspace, colar, aspas).
2. `forms`: todo `Field.name` existe em `EncodeConfig`; opções válidas pelo validador; condições de visibilidade; MCTF→off; campos ocultos ausentes.
3. Reducer: navegação completa e volta com ESC; foco restaurado; campos desativados pulados; dois níveis de foco nas abas; preset 3 recusado; REVISAR com rascunho atual; rascunho por preset na sessão; READY recusando START com input sumido.
4. **Paridade com o wizard** (`ui/tui/test_parity_wizard.py`): para cada cenário, (a) `run_launcher` com `ask_*`/`Confirm.ask` monkeypatchados por respostas roteirizadas; (b) a TUI dirigida por teclas no reducer; exigir `to_namespace()` igual. Cenários: preset 1 (cover/24/2pass), preset 2 (−0,5 EV/1,2 sat/cover), preset 5 com Cineon on, preset 5 com enhance+AI+MCTF on, preset 5 com enhance off.
5. Snapshots 120×40: HOME, SOURCE (VALID/NOT FOUND/INVALID), CONFIGURATION (1 e 2), ADVANCED (cada aba), PREVIEW — textos-chave, ≤ 120 colunas, sem emoji.
6. App: ida e volta do Tools (Live fechado/reaberto, terminal restaurado), HOME+ESC → 0, Ctrl+C em CONFIGURATION → 130, ponta a ponta HOME → READY → encode falso → COMPLETED.
7. Manual no Windows Terminal: preset 1 completo; preset 2 com exposição/saturação; preset 5 pelas 5 abas (Cineon on/off; enhance/AI/MCTF); REVISAR no PREVIEW; arrastar arquivo para o campo; caminho inexistente; Tools e volta; preset 3 desativado; ESC na HOME.

## 8. Fora de escopo

Batch (P3D); aba no `launcher.ps1`, mensagem "abra no Windows Terminal", dívida visual do P3B (P3E); descartar edições (NB-3); qualquer mudança em `ui/launcher.py`, `ui/config.py`, encoder, `reporter.py`, `ui/tui_driver.py`, `ui/tui_capture.py`.
