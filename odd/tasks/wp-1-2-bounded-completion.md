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
T2 [S2-S3,S5] Newtonian Fann derivation with public API/UI, tests and docs — bounded implementation; done; commit: `efa2e2a`.
T3 [S2-S3,S5] Conventional HB fitting with documented independent method, diagnostics, tests and UI — bounded implementation; done; commit: `2701366`.
T4 [S2-S5] Evidence-backed timed gels and annular break-gel behavior, or record specific unavailable evidence and decision — parent evidence review; blocked: waiting for authoritative timed-gel and annular calculation semantics or user's bounded-scope decision; commit: pending.
T5 [S1-S5] Full regression, functional verification, coverage audit, review assessment and ODD closure — parent inline; pending; commit: pending.

## Log
L1 (original request, verbatim): ok, de acuerdo, crear la rama y realiza ese odd e implemnta
L2: Created feature branch from clean main at 1bb5d76. Existing `research/rheology/wp-1.2-coverage.md` identifies the current partial workflows. Do not infer a proprietary fitting algorithm or annular equation from a feature name. No source edits yet.
L3: Inspected current Bingham, HB and gel domains and research boundaries: Bingham establishes Fann SI conversion, HB establishes τ=τ₀+Kγⁿ but not fitting objective; zero-second gel/interior formula is specified, timed/annular semantics are not established in repository. Conventional HB fit will be explicitly OpenOil-defined, not WellPlan parity. User selected `feature-branch-chain` for reviewable delivery; no push/PR authorization.
L4: Newtonian worker observed RED domain import/API 404/UI missing, GREEN focused domain 3/3, API 1/1 and UI 24/24. Parent found oversized-int OverflowError, observed RED 2 subcases and fixed to ValueError; backend focused 3/3 and API 16/16, full backend 86/86, frontend 48/48 and production build passed; build warns 625.28 kB bundle. One-shot differential on 10 existing public routes with new payload matched previous HEAD exactly (exit/status/body/stdout/stderr). No vendor parity or field validity claimed. Feature-level functional browser smoke remains T5.
L5: Newtonian coherent work-unit commit `efa2e2a` contains 565 authored lines including tracker, over advisory ~400 without code golf; first chain slice boundary is `1bb5d76..efa2e2a`. Native committed-range ASSESS returned medium, reviewDue=false (`under_budget`), no independent verifier, candidate unconsumed; no review START. Continue second slice from `efa2e2a`; no push/PR.
L6: User authorized read-only inspection of `C:\Landmark\EDT` for this ODD. Installed help `r_analysis_hydraulics_defs.html` names 0 s, 10 s, 10 min and 30 min fields but ambiguously describes them as pressure; `c_press_brk_gel_calc.html` specifies only `4*tau_g*sum(L_c/d_i)` using drillstring inside diameter. `c_plot_press_break_gel_calcs.html` links to those topics but supplies no annular equation. Do not infer timed Fann measurement protocol or annular solver from these sources. User asked to save continuity and prepare a pause because remaining context is limited.
L7: T3 worker `mvtn5eu2-2-37gw` delivered separate OpenOil-defined conventional HB fit (391-point discrete n grid, constrained profile, diagnostics) with RED module/API/UI and focused GREEN domain 4/4, API 1/1, frontend 26/26. Its 11-route differential against HEAD matched stdout/stderr/status/body. Parent inspected algorithm/boundary; full backend 91/91 and frontend 55/55 passed, production build passed with 633.57 kB chunk advisory. No parity/field validation; browser smoke stays T5.
L8: T3 committed as `2701366` (639 authored lines including tracker); second chain slice `efa2e2a..2701366`, independently coherent but over advisory 400. Native committed-range ASSESS medium, reviewDue=false (`under_budget`), no independent verifier or review START. T4 evidence remains insufficient for timed-gel input semantics or an annular pressure equation. Do not silently implement or close WP-1.2; request exact scope/evidence decision. T5 browser/API functional smoke and coverage audit not yet performed. User requested Engram continuity and preparation to pause.
