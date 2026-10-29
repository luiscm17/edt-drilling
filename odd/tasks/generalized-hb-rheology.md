# ODD — Generalized Herschel–Bulkley parametric study
Objective: Add a bounded independent SI evaluator and graph for documented generalized Herschel–Bulkley rheology.
Branch: `feat/generalized-hb-rheology` from main `a56c72d`; local reviewable commits; no push or PR authorized.

## Specs

S1 (user request, verbatim): "dale con 'Herschel–Bulkley generalizado', igualmente crea una rama e investiga los binarios para luego implementar". Deliver this one generalized model study, not conventional HB or complete WP-1.2.
S2 (consent): User selected "Sí, solo lectura estática" of `C:\Landmark\EDT` for this work. Inspect installed WebHelp and binarios with REA without executing the program or altering installed data. Static metadata cannot establish numerical parity.
S3 (clarified scope): User selected "Evaluador paramétrico acotado (recomendado)" — "Ingresar parámetros explícitos y graficar la curva SI; sin atribuirle ajuste Fann ni paridad con el programa instalado." No fit from Fann, foam-pressure calculation, hydraulic coupling, persistence, or operational claim.
S4 (roadmap exact text): "OpenOil SHALL support documented Newtonian, Bingham plastic, power-law, Herschel–Bulkley, and generalized Herschel–Bulkley workflows." This slice covers only the parametric generalized model; retain previously implemented public studies and saved cases.
S5 (documented equation): Installed WebHelp `c_gen_hb_rheology_calcs.html` presents `(τ/τ_ref)^m = (τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n`. For SI inputs `τ_ref > 0` Pa, `τ_z >= 0` Pa, `μ_h >= 0` Pa·s, dimensionless `m > 0`, `n > 0`, and a finite nonnegative list of shear rates γ in s⁻¹, compute `τ = τ_ref * [ (τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n ]^(1/m)` Pa. Use a numerically stable formulation, reject unrepresentable/unsupported outputs and duplicates; no hidden default. A zero-shear rate returns τ_z. Example `τ_ref=10 Pa`, `τ_z=3 Pa`, `μ_h=0.2 Pa·s`, `m=n=2`, `γ=40 s⁻¹` gives `sqrt(73) Pa`; γ=0 gives 3 Pa. Return input parameters/units, curve ordered by shear rate, model/schema versions, assumptions and limitations. API 422 errors must not alter cases/IDs; UI displays curve, accessible SI table, invalidates stale results, shows no fabricated measured points.

## Tasks

T1 [S1-S5] Inspect repo, help MathML and bounded REA metadata; distinguish observed equation from undocumented fitting — parent; done; evidence note in T3 work unit.
T2 [S1-S5] Create branch, tracker and Engram mirror before source writes — parent; done; mirror observation 146.
T3 [S3-S5] Add original engineering boundary, RED/GREEN pure evaluator, strict separate HTTP API and backend tests/docs — parent; pending.
T4 [S3-S5] Add independent UI graph and accessible data, navigation and frontend tests/docs with RED/GREEN — parent; pending.
T5 [S1-S5] Run full functional checks, differential existing routes, risk assessment/independent verification when due, record commits and close — parent; pending.

## Log

L1 (original request, verbatim): dale con 'Herschel–Bulkley generalizado', igualmente crea una rama e investiga los binarios para luego implementar
L2: User granted static read-only inspection of `C:\Landmark\EDT` and selected a parametric evaluator instead of an undocumented Fann-fitting algorithm. Main was clean at `a56c72d` (PR #12 merged); created `feat/generalized-hb-rheology`.
L3: WebHelp `c_gen_hb_rheology_calcs.html` provides the dimensionless formula and names m (stress exponent), n (rate exponent), μ_h (finite high-shear limiting viscosity), τ_z (zero-shear stress), τ_ref (reference stress), γ (shear rate), τ (shear stress). It describes foaming fluids but does not give a Fann fitting algorithm, foam-pressure solver, or explicit solver limits. The conventional HB page has a different three-parameter equation. REA static metadata of `WellPlan/plugins/DSWE.Shared/EDK.Rheology.dll` (SHA-256 `316820f79378c708a41c0c180aa19082f72641cffab32e5a5dcebde6b32ddbe2`) shows `GeneralHerschelBulkleyInputs` with FannDataPoints, temperature, rheometer geometry, IsFoamed, base/foam densities and foam quality, plus outputs K/M/N, shear points, yield point and plastic viscosity. It does not prove how parameters are fit or runtime parity. No installed application was run.
