# ODD — Zero-second gel and string-interior break-gel pressure
Objective: Deliver an evidence-bounded Fann gel derivation and drillstring-interior break-gel study, with API, UI, tests and documentation.
Branch: `feat/gel-break-pressure` | Delivery: single-pr (user-selected oversized exception; no push/PR authorized) | Runner: backend pytest, frontend vitest/build, browser smoke if available | Forecast: ~500 authored lines, review slices to decide before oversized commit.

## Specs
S1 (user authorization, verbatim): "ahhh bueno, es mas de lo que sugeri y estoy de acuerdo, dale con la rama y odd". This accepts the immediately preceding proposed scope.
S2 (accepted scope, verbatim): "Gel de 0 segundos desde Fann: lectura a 3 rpm, conversión a la unidad de salida, validación de entradas y resultado que identifique su origen."
S3 (accepted scope, verbatim): "Presión para romper gel dentro de la sarta: geometría por componentes, aplicación de `p_gel = 4 τ_g Σ(L_c/d_i)`, unidades y validación de longitudes y diámetros. El resultado debe decir expresamente que corresponde al **interior de la sarta**."
S4 (accepted scope, verbatim): "API y UI del estudio: entradas claras, resultado y desglose por componente; una tabla accesible basta. No agregaría un gráfico si no aporta información que la tabla no muestre."
S5 (accepted scope, verbatim): "Pruebas y documentación: casos numéricos con conversiones verificables, entradas inválidas y límites del modelo; actualizar la nota de cobertura sin marcar WP-1.2 como cerrado."
S6 (exclusions, verbatim): "Dejaría fuera otros tiempos de gel, presión anular, pérdidas por tool joints, el gráfico/análisis completo de WellPlan y el ajuste Herschel–Bulkley. Son alcances distintos y la evidencia reunida no justifica mezclarlos con esta ecuación."

## Tasks
T1 [S1-S6] Reconcile evidence, branch and feature contract — parent inline; done; commit: `4b9c357`.
T2 [S2-S3,S5-S6] Standalone pure-domain calculation and public API, with tests and documentation — bounded writer; done; commit: `4b9c357` (backend 82/82 local unittest; behavioral RED unavailable because Docker runner failed before test discovery).
T3 [S4-S6] RED/GREEN accessible UI and table, with tests and documentation — parent inline; done; commit: pending (frontend RED 3/3 missing navigation, GREEN 3/3 focused; full suite/build pending T4).
T4 [S1-S6] Run suites and functional checks, update coverage, assess review and close evidence — parent inline; pending; commit: pending.

## Log
L1 (original request, verbatim): ahhh bueno, es mas de lo que sugeri y estoy de acuerdo, dale con la rama y odd
L2: Created branch from main preserving existing untracked `research/rheology/wp-1.2-coverage.md` and `research/ui/`. WebHelp specifies zero-second gel = 3-rpm Fann dial and p=4 tau_g sum(component length / internal diameter). Assumption: independent stateless SI study, stress converted using documented 0.01065 lb/ft² per dial and 47.88025898033584 Pa per lb/ft²; positive component geometry; no hydraulics coupling or engineering parity. No proprietary binary code copied. Existing untracked coverage note belongs to earlier work; update only the relevant note when appropriate, without sweeping unrelated `research/ui/` into commits.
L3: Bounded writer delivered backend domain/API/tests/docs. Docker-based RED and GREEN attempts exited 1 before test discovery (Linux engine pipe absent). Parent found local `backend/.venv/Scripts/python.exe`; focused 6/6 and full 82/82 tests passed (exit 0). Behavioral RED not observed; no claim of RED. Source verification and coverage update remain for later tasks.
L4: User selected "Una sola PR — menos recomendado" from oversized-delivery choices; `delivery_strategy=single-pr`. This selects review shape, not push or PR creation. First backend work unit `4b9c357` has 430 authored lines, including tests, boundary documentation and tracker; later UI unit stays a separate commit within the user-selected single-PR shape.
L5: Frontend test-first RED exited 1 with three missing-navigation failures, before UI implementation; after adding study and routing, focused GREEN exited 0 (3/3). UI validates input/response, displays SI values and accessible component table, clears stale results. Updated README and pre-existing untracked coverage note (which remains uncommitted by prior user preference). Backend full local suite repeated 82/82. Frontend full suite/build running separately for T4.
