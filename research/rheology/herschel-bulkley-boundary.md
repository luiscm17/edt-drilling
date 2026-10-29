# Conventional Herschel–Bulkley study boundary

This original OpenOil study evaluates explicitly supplied conventional Herschel–Bulkley parameters in SI. It is the m=1 special case of the generalized relation already implemented, not an independent Fann-fit or a claim of solver parity.

## Published basis and static inspection

Installed WebHelp topic *Herschel-Bulkley Rheology Calculations (API units)* (`c_hb_rheol_calc.html`) gives `τ = τ₀ + K γⁿ` and names τ as shear stress, τ₀ as yield point, K as consistency index, γ as shear rate and n as flow behavior index. The model topic `c_herschel_bulkley_rheology_model.html` calls Herschel–Bulkley the Yield Power Law model, states that n=1 gives Bingham with plastic viscosity K and yield point τ₀, and τ₀=0 gives Power Law. The help says parameters are calculated by nonlinear fit for three or more Fann readings and that two readings assume Power Law; it does not specify the fitting algorithm.

Read-only static REA inspection identified a `HerschelBulkleyRheologyCalculationParameter` type in the shipped managed `EDK.Rheology.dll`; its metadata shows it inherits `RheologyCalculationParameter`. The shared base names Fann data, `tauZero`, `shearExponent`, `nPrime`, and `muInf`. This is evidence of a named parameter type and workflow inputs only: static inspection did not establish equations used by the runtime solver, fitting objective, convergence, interaction, or numerical parity. No installed application or assembly was loaded or executed or changed.

## SI evaluator contract

Input τ₀ in Pa (>=0), K in Pa·sⁿ (>=0), n dimensionless (>0), and a finite nonempty set of unique shear rates γ in s⁻¹ (>=0). Return ordered points `τ(γ)=τ₀ + K γⁿ` in Pa. Use no inferred defaults or fitted parameters. Reject booleans, malformed/extra inputs, nonfinite values, duplicates, negative values outside the domain, and unrepresentable outputs. At γ=0 the stress is τ₀. K=0 yields constant τ₀.

The generalized equation `(τ/τ_ref)^m = (τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n` becomes conventional Herschel–Bulkley at m=1 with τ_z=τ₀ and `K = μ_hⁿ τ_ref^(1−n)`. This is a parameter mapping, not a claim that the two UIs, Fann fitting or foam behavior are equivalent. For n=1 the curve is Bingham; for τ₀=0 it is Power Law.

Independent arithmetic fixture: τ₀=3 Pa, K=0.2 Pa·sⁿ, n=1 and γ=[0,40] s⁻¹ yields τ=[3,11] Pa. It checks this displayed equation only; it is not a reference output or field validation.

## Scope limits

This calculate-only slice has a separate strict API route and accessible SI curve/table; it does not fit Fann readings, save cases, couple to hydraulics, calculate gels or pressure to break gel, or make operational recommendations. Display precision is not engineering accuracy.
