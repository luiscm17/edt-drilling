# ODD — Bounded WP-1.2 completion
Objective: Implement the agreed Newtonian, viscometer fitting, and gel extensions only where independently specified and verifiable; do not claim WellPlan parity or close unsupported normative scope.
Branch: `feat/wp-1-2-bounded-completion` | Delivery: feature-branch-chain; forecast >400 authored lines | Runner: backend tests, frontend tests/build, applicable functional smoke.

## Specs
S1 (user request, verbatim): "ok, de acuerdo, crear la rama y realiza ese odd e implemnta".
S2 (accepted grouped scope, verbatim): "pero diria implementar en un solo odd el 1, 2y 3, es posible?".
S3 (prior recommendation, verbatim): "Newtoniano + ajuste HB convencional + ampliación de geles basada en evidencia".
S4 (boundary, verbatim): "Si la presión anular o el ajuste generalizado siguen sin fundamento suficiente, no marcaría el WP-1.2 actual como completo".
S5 (boundary, verbatim): "no llamarla paridad con WellPlan".

## Tasks
T1 [S1-S5] Establish source evidence, numerical contracts, and explicit unsupported boundaries — parent inline; done; commit: pending tracker slice.
T2 [S2-S3,S5] Newtonian Fann derivation with public API/UI, tests and docs — bounded implementation; done; commit: pending Newtonian slice.
T3 [S2-S3,S5] Conventional HB fitting with documented independent method, diagnostics, tests and UI — bounded implementation; pending; commit: pending.
T4 [S2-S5] Evidence-backed timed gels and annular break-gel behavior, or record specific unavailable evidence and decision — bounded implementation; pending; commit: pending.
T5 [S1-S5] Full regression, functional verification, coverage audit, review assessment and ODD closure — parent inline; pending; commit: pending.

## Log
L1 (original request, verbatim): ok, de acuerdo, crear la rama y realiza ese odd e implemnta
L2: Created feature branch from clean main at 1bb5d76. Existing `research/rheology/wp-1.2-coverage.md` identifies the current partial workflows. Do not infer a proprietary fitting algorithm or annular equation from a feature name. No source edits yet.
L3: Inspected current Bingham, HB and gel domains and research boundaries: Bingham establishes Fann SI conversion, HB establishes τ=τ₀+Kγⁿ but not fitting objective; zero-second gel/interior formula is specified, timed/annular semantics are not established in repository. Conventional HB fit will be explicitly OpenOil-defined, not WellPlan parity. User selected `feature-branch-chain` for reviewable delivery; no push/PR authorization.
L4: Newtonian worker observed RED domain import/API 404/UI missing, GREEN focused domain 3/3, API 1/1 and UI 24/24. Parent found oversized-int OverflowError, observed RED 2 subcases and fixed to ValueError; backend focused 3/3 and API 16/16, full backend 86/86, frontend 48/48 and production build passed; build warns 625.28 kB bundle. One-shot differential on 10 existing public routes with new payload matched previous HEAD exactly (exit/status/body/stdout/stderr). No vendor parity or field validity claimed. Feature-level functional browser smoke remains T5.
