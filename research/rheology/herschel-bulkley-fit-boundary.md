# Conventional HB fit — independent bounded numerical contract

## What this study does

This is an **OpenOil-defined** fit, not an inferred vendor algorithm. It fits
`τ = τ₀ + K γⁿ` to every supplied Fann observation. It does not change the
existing supplied-parameter conventional or generalized-HB studies. There is
no WellPlan/vendor parity, generalized-HB fitting, hydraulic coupling,
extrapolation recommendation, uncertainty certification or field validation.

The equation and Fann conversions already exist in the repository; the fitting
objective and solver below are independently specified here. No installed help
or vendor runtime is evidence for this optimization policy. Only Python's
standard library is needed. This bounded calculation does not complete the
unsupported portions of WP-1.2.

## Input and numerical rejection boundary

Supply 3–1000 readings, each with a distinct positive finite RPM and nonnegative
finite dimensionless dial. The upper count bounds CPU work; it is not an
instrument capability. Booleans and strings are not numbers. Sort by RPM before
arithmetic, without mutating caller input. Reuse the existing Fann constants:

- `γ = 1.70333 × RPM` in s⁻¹.
- `τ = (0.01065 × 47.88025898033584) × dial` in Pa.

Reject nonfinite/unrepresentable derived results and positive consistency
underflow, including overflow in physical squared residuals. Reject RPM spread
`(γmax − γmin)/γmax ≤ 10⁻⁶`; reject zero stress scale or stress spread
`(τmax − τmin)/τmax ≤ 10⁻¹⁰`. These are declared numerical identifiability
cutoffs, not instrument tolerances or fluid-acceptance limits. Constant/all-zero
data leave n and K unidentified; they must not produce fabricated parameters.
If the winning normalized consistency coefficient is ≤ 10⁻¹⁰, reject it as
unidentified as well (this includes nonincreasing observations). Nonmonotonic
noisy data are otherwise allowed; residuals, not monotonicity filtering, show
model mismatch. No automatic quality/pass threshold is inferred from residuals.

## Objective, constraints and complete-search policy

Minimize unweighted SI stress SSE `Σ(τ₀ + K γᵢⁿ − τᵢ)²`, with `τ₀ ≥ 0`,
`K ≥ 0`, over the **discrete** set `n = (10+j)/200`, `j = 0,…,390`.
Thus `0.05 ≤ n ≤ 2`, resolution `0.005`. This is deliberately not a claim to
solve the continuous positive-n problem. Bounds/resolution are policy choices,
not measured limits of HB behavior. A true exponent may lie outside the range
or between grid values.

For stable profiling, let `S = max(τᵢ)`, `G = max(γᵢ)`, `yᵢ = τᵢ/S`,
`zᵢ = exp(n (ln γᵢ − ln G))`. At fixed n, solve nonnegative least squares
`min Σ(a + b zᵢ − yᵢ)²`, where `τ₀ = aS`, `K = bS/Gⁿ`:

1. Interior candidate: `b = Σ(zᵢ−z̄)(yᵢ−ȳ)/Σ(zᵢ−z̄)²`, `a = ȳ−bz̄`;
   include only if both are nonnegative.
2. Zero-yield boundary: `a=0`, `b=max(0, Σzᵢyᵢ/Σzᵢ²)`.
3. Zero-consistency boundary: `b=0`, `a=ȳ`.
4. Choose the candidate with the smallest normalized mean squared residual;
   exact candidate ties use smaller a, then smaller b. Compare all 391 profiles;
   exact exponent ties use smaller n. Use compensated sums (`math.fsum`).

The convex quadratic at fixed n attains its constrained minimum in this
candidate set. Comparing every exponent therefore completes the declared finite
optimization: no local-search convergence guess, random seed, iterative early
exit, SciPy dependency or continuous global-optimality claim is needed.
Only return success after all profiles and physical diagnostics are finite.
Compute K with logarithms to avoid an unnecessary intermediate power overflow.

## Diagnostics and non-uniqueness

Return sorted measured and predicted stresses at the entered shear rates,
residual `predicted − measured` (Pa), SSE (Pa²), RMSE `sqrt(SSE/N)` (Pa),
maximum absolute residual (Pa), profile count, grid bounds/step, and whether the
selected n is at either bound. These are descriptive diagnostics, not a
statistical noise model. Three points give no residual degrees of freedom.

The near-optimal set includes every grid exponent whose **profiled normalized
MSE** is at most the minimum plus `10⁻⁶`. Return its minimum, maximum and count;
this span may contain gaps. It is a sensitivity warning, **not a confidence
interval**. Its tolerance is a numerical reporting policy, not measurement
uncertainty. Multiple near-optimal profiles show ambiguity; even a single grid
winner does not establish continuous uniqueness or justify fitted digits.
Always communicate that non-uniqueness remains possible. Bound solutions can
be truncated, even with a small residual. API floating-point digits and UI
rounding do not certify parameter accuracy.

## Independent hand check

Choose `γ = [1,4,9] s⁻¹`, `τ = [5,8,11] Pa`. Enter RPM `γ/1.70333` and dial
`τ/(0.01065 × 47.88025898033584)`. With `n=0.5`, square roots are `[1,2,3]`;
`τ = 2 + 3 sqrt(γ)` gives exactly `[5,8,11]`. Therefore `τ₀=2 Pa`,
`K=3 Pa·s^0.5`, `n=0.5` is a grid candidate with zero SSE (up to floating-point
roundoff), a global minimum because SSE cannot be negative. This independent
arithmetic is not a vendor-runtime oracle and does not prove uniqueness for
noisy field data.
