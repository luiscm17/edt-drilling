# Power Law Fann study boundary

This independent calculate-only OpenOil study derives a two-point Power Law curve from positive 300 and 600 RPM dial readings. It does not reproduce or validate the installed application's calculation, predict field behavior, alter saved cases, or feed the hydraulic engine.

## Documented basis and static inspection

Installed WebHelp topics *Power Law Rheology Model* (`c_power_law_rheology_model.html`) and *Power Law Rheology Calculations (API units)* (`c_pwr_law_rheol_calc.html`) identify `τ = K γ^n` and a logarithmic dial-ratio expression with multiplier 3.32192809 (the reciprocal of log10 2, appropriate to a 2:1 speed ratio). The *Shear Rate and Shear Stress Calculations (API units)* topic (`c_shear_rate_stress_calc.html`) gives `γ = 1.70333 × RPM` s⁻¹ and `τ = 0.01065 × dial` lbf/ft². The source's `510 × dial / (1.703 × RPM)^n` consistency factor is in its API convention and is **not** substituted for SI K. The help for Fann75 downhole prediction describes another, coupled workflow; it is excluded.

Read-only static inspection of installed `WellPlan/plugins/DSWE.Shared/EDK.Rheology.dll` (SHA-256 `316820f79378c708a41c0c180aa19082f72641cffab32e5a5dcebde6b32ddbe2`) identified `FannData` RPM/dial accessors and `PowerLawRheologyCalculationParameter`; metadata does not establish the vendor solver's formulas, operational behavior or numerical parity. Nothing installed was executed or modified.

## Explicit SI contract

For 300/600 RPM observations `θ300`, `θ600`, convert each observation by `γ_r = 1.70333 r` s⁻¹ and `τ_r = 0.01065 θ_r × 47.88025898033584` Pa. Then derive `n = ln(θ600/θ300)/ln(2)` (dimensionless), `K = τ300 / γ300^n` (Pa·s^n), and the plotted `τ_model(γ) = K γ^n` for positive shear rates. The line is evaluated at the observed minimum and maximum positive speeds and at 300 and 600 RPM; extra readings are observations only, never regression data. The two parameter-defining readings must be strictly positive, with `θ600 > θ300` so `n > 0`; this deliberately excludes zero/negative exponents, constant readings and shear-thickening/descending dials as an initial supported domain, not a statement about all Power Law fluids. Other readings may be nonnegative (zero shear stress observations are allowed); each RPM must be finite, positive and unique. Reject any unrepresentable intermediate or output. Both the measured points and model line retain explicit SI units and provenance.

Arithmetic fixture, derived independently from the above equations (not a reference-software output): `θ300 = 50`, `θ600 = 75` gives `n = 0.5849625007211562`, `K = 0.6639753206166239 Pa·s^n`, `τ300 = 25.49623790702883 Pa`, `τ600 = 38.244356860543256 Pa`. Other example readings do not change n or K. Tests must check all these observable values, invalid-input errors and statelessness.

The curve is a two-point parametric study, not a whole-fluid fit, hydraulic pressure-loss model, gel-strength estimate, temperature/pressure prediction, or field validation. Its numerical contract and any later integration need independent engineering review.
