# VALIDATION.md — Auditoria Cineon Pipeline (Correções A3, F2, E3d)

**Timestamp:** 2026-07-18 15:08 GMT-3

## Tabela de Veredito

| check | esperado | medido | status |
|-------|----------|--------|--------|
| V1 A3: função existe e é chamada | ≥ 1 def + ≥ 1 call site | 0 definições, 0 call sites (grep vazio) | ✗ |
| V2 A3: função executa sem exceção | executa, imprime OK | AttributeError: no attribute '_validate_cineon_constants' | ✗ |
| V3 F2: output LUT (0,0,0) ∈ [0, 0.05] | [0, 0.05] | -0.025428999999999997 | ✗ |
| V4 F2/regressão LUT (4 valores) | F1≤1e-2, F3≥-1e-4, F4≤5°, F5≤3.5e-2 | F1=4.44e-16, F3_min=0.00335, F4_max=-0.87°, F5=0.00164 | ✓ |
| V5: audit_cineon_math.py TODAS linhas PASS | PASS em 100% | 20/20 checks PASS | ✓ |
| V6 E3d: doc descreve dither/round ANTES clip | ordem ×255→dither→round→clip | "clip [0,1] → ×255 → dither → round → uint8" | ✗ |

**Veredito: REPROVADO**
