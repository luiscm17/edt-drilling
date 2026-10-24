# Bingham rheology study boundary

This note records the source equations, SI interpretation, and limits for the bounded calculate-only rheology study. It is an independent implementation basis, not a claim of reference-software parity or engineering validation.

## Source evidence

The installed help topics `c_deriv_pv_yp_0sec_gel_fann_data_calc.html` and `c_shear_rate_stress_calc.html` document plastic-viscosity/yield-point derivations and Fann dial conversion. `c_fluid_plot.html` describes plotting converted rheology observations; `c_fluid_rheol_test.html` and `c_bingham_plastic_rheology_model.html` describe the Bingham workflow. The plotted example labels stress in psi, while the shear-stress equation page gives lb/ft². OpenOil therefore uses explicit SI labels rather than copying the inconsistent presentation units.

Read-only REA inspection of installed metadata found separate Fann-data and Bingham calculation types and fluid-plot/rheology presentation types. Only static metadata/CIL was inspected; no installed calculation or application was loaded or executed. This confirms the separation of workflow concerns, not a numerical implementation, user interaction, or runtime result.

## Independent SI derivation

Let `θ_r` be the nonnegative dial reading at rotational speed `r` RPM. The documented transforms are:

```text
γ_r (s⁻¹) = 1.70333 × r
τ_r (lb/ft²) = 0.01065 × θ_r
1 lbf/ft² = 47.88025898033584 Pa
τ_r (Pa) = 0.01065 × θ_r × 47.88025898033584
```

The 300 and 600 RPM observations define a two-point Bingham relation:

```text
PV (Pa·s) = (τ_600 − τ_300) / (γ_600 − γ_300)
YP (Pa) = τ_300 − PV × γ_300
         = (2 × θ_300 − θ_600) × 0.01065 × 47.88025898033584
τ_model (Pa) = YP + PV × γ
```

For an independent arithmetic check, readings `θ_300 = 50` and `θ_600 = 75` give `PV ≈ 0.024947444 Pa·s` and `YP ≈ 12.748119 Pa`. These values follow the stated transformations; they are not observations from the installed software.

Other entered RPM readings are transformed and plotted as observations. They do not alter the two-point PV/YP derivation or feed a regression. A zero PV or zero YP is permitted in this standalone study; negative derived values are rejected.

## Limits

This slice does not derive gel strengths, fit Power Law/Herschel–Bulkley/generalized models, integrate with hydraulic calculations, persist cases, or correct for temperature/pressure. It makes no field-use recommendation. Static metadata and help documentation do not establish numerical parity, validated limits, or exact reference UI behavior.
