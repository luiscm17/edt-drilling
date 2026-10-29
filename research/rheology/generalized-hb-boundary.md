# Generalized Herschel–Bulkley parametric study boundary

This original OpenOil calculate-only study evaluates **supplied parameters** of a documented generalized rheology relation in SI. It does not derive parameters from Fann readings, model foam quality or circulation, persist cases, or claim numerical parity with installed software.

## Documented model and limits of inspection

The installed *Generalized Herschel-Bulkley Rheology Calculation (API units)* topic (`c_gen_hb_rheology_calcs.html`) gives the dimensionless relation `(τ/τ_ref)^m = (τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n`. It names τ (viscometric shear stress), τ_ref (reference fluid shear stress), τ_z (zero-shear stress), μ_h (finite high-shear limiting viscosity), γ (viscometric shear rate), m (stress exponent), and n (rate exponent). Its foam-fluid recommendation does not provide a Fann-data fit algorithm, pressure solver or numerical convergence/domain contract. The conventional HB topic `c_hb_rheol_calc.html` instead specifies `τ = τ_0 + K γ^n` and is **not** interchangeable with this generalized equation.

REA read-only static inspection of installed `WellPlan/plugins/DSWE.Shared/EDK.Rheology.dll` (SHA-256 `316820f79378c708a41c0c180aa19082f72641cffab32e5a5dcebde6b32ddbe2`) identified `GeneralHerschelBulkleyInputs` containing Fann observations, rheometer factors, temperature, foam flag and density/quality fields; `GeneralHerschelBulkleyOutputs` names K/M/N, yield point, plastic viscosity and shear points. These names do not establish the reference parameter fit, runtime behavior or numerical parity. Nothing installed was run or changed.

## Independent SI evaluation contract

Input τ_ref is in Pa (>0), τ_z in Pa (>=0), μ_h in Pa·s (>=0), m and n dimensionless (>0), and each finite unique γ in s⁻¹ (>=0). Return `τ(γ) = τ_ref * [(τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n]^(1/m)` in Pa at every requested γ sorted ascending. γ=0 gives τ_z, including zero. Do not silently infer values, fit a curve, add measured points or use this model inside hydraulics. Reject nonfinite inputs, numerical overflow/underflow when a nonzero output is not representable, and duplicate rates. Evaluate logarithmic terms with a stable log-sum-exp technique so exponentiating an intermediate is not required merely to cancel scales.

Independent arithmetic fixtures (from the displayed algebra, not reference software): τ_ref=10 Pa, τ_z=3 Pa, μ_h=0.2 Pa·s, m=n=2, γ=[0, 40] s⁻¹ yields τ=[3, sqrt(73)] Pa. For m=n=1, τ=τ_z+μ_h γ. A zero μ_h produces constant τ_z. These are behavior checks of the chosen SI contract only; their match does not validate foam rheology or field suitability.
