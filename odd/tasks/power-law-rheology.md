# ODD — Power Law rheology study
Objective: Add one independent, calculate-only Power Law Fann study to OpenOil.
Branch: `feat/power-law-rheology` from main `80b03f2`; local work-unit commits only, no push or PR authorized.

## Specs

S1 (user request, verbatim): "ok, estoy de acuerdo, entonces toca crear otra rama, e implementar wp-1.2; eso incluye investigar los binarios y la documentacion no es cierto? todo mediante odd. asi q dale,". The user selected "Solo Power Law (recomendado)" from the clarification choices. Deliver only this Power Law slice of WP-1.2, not all of WP-1.2.
S2 (authorization): The user selected "Sí, lectura estática solamente" for `C:\Landmark\EDT`: consult documentation and binary metadata via REA; do not run or modify installed software or its data. Static metadata is not numerical parity evidence.
S3 (prior recommendation accepted by user): "Estudio independiente con API, UI, gráfica, investigación de documentación y binarios; los otros gaps quedan pendientes." No hydraulic coupling or case persistence; make quantities, units, model, errors and applicability explicit.
S4 (roadmap exact text): "OpenOil SHALL support documented Newtonian, Bingham plastic, power-law, Herschel–Bulkley, and generalized Herschel–Bulkley workflows." This task covers only the power-law workflow. Preserve existing Bingham and other API behaviors.
S5 (source equations): Installed WebHelp `c_pwr_law_rheol_calc.html` documents `τ = K γ^n` and `n = 3.32192809 log(θ_N2/θ_N1)`; its `K = 510 θ_N/(1.703 N)^n` uses source API conventions. `c_shear_rate_stress_calc.html` documents `γ = 1.70333 r` s⁻¹ and `τ = 0.01065 θ` lbf/ft². Define standalone SI K from the transformed 300/600 RPM data as `τ_300 / γ_300^n`, with `n = ln(θ_600/θ_300)/ln(2)`; `K` unit Pa·s^n. Two strictly positive readings are required for logarithms; additional positive unique-RPM readings are display observations, not a regression. Validate finite inputs/outputs and reject unsupported non-positive or non-increasing readings if the selected supported domain is shear thinning/linear. Document exact boundaries and independent arithmetic examples before implementation. This is an OpenOil SI interpretation, not a reproduction of undocumented reference behavior.

## Tasks

T1 [S1-S5] Inspect repository seams, installed documentation and static binary metadata; record bounded equations/uncertainties — parent; done; evidence note commit `c5069ab`.
T2 [S1-S5] Create branch and tracker/mirror before source writes — parent; done; Engram mirror observation 145.
T3 [S3-S5] RED/GREEN implement pure domain calculation, additive versioned API, exact validation tests and backend guide — parent inline; done; domain RED import failure, API RED 404; focused GREEN and backend suite 67/67; commit `c5069ab`.
T4 [S3-S5] RED/GREEN implement accessible independent UI graph/table and navigation tests — parent inline; done; UI RED 2/2 missing navigation, focused GREEN 2/2 and production build; commit pending.
T5 [S1-S5] Run full checks, differential sibling-route tests, assess/review if due, record evidence and commits — parent; pending.

## Log

L1 (original request, verbatim): ok, estoy de acuerdo, entonces toca crear otra rama, e implementar wp-1.2; eso incluye investigar los binarios y la documentacion no es cierto? todo mediante odd. asi q dale,
L2: Clarification selected "Solo Power Law (recomendado)" rather than the entire WP-1.2. User separately authorized static read-only inspection of `C:\Landmark\EDT` for this task, without execution or writing.
L3: Main was clean at `80b03f2` (PR #11 merged). Created `feat/power-law-rheology`. Installed help `c_power_law_rheology_model.html` and `c_pwr_law_rheol_calc.html` document the model and API conventions. Static REA `inspect_managed_members` on `WellPlan/plugins/DSWE.Shared/EDK.Rheology.dll` (SHA-256 `316820f79378c708a41c0c180aa19082f72641cffab32e5a5dcebde6b32ddbe2`) reports FannData and PowerLawRheologyCalculationParameter types; it does not establish solver arithmetic or runtime results. The Fann75 prediction help concerns a different coupled workflow and is excluded. No installed application executed.
