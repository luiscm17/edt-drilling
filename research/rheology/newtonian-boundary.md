# Newtonian Fann study boundary

## What this study establishes

This is an independent, calculate-only OpenOil derivation under the Newtonian
constitutive assumption `τ = μγ`: zero yield stress and constant dynamic viscosity.
One observation can derive μ under that assumption but cannot establish that a
fluid is Newtonian. Multiple observations are a consistency check, not regression
or automatic fluid classification. No WellPlan/vendor parity or field validation
is claimed. This does not complete the broader WP-1.2 scope.

## Numerical contract

Reuse `bingham_rheology` conversion constants and its immutable `FannReading`:

- `γ = 1.70333 × RPM` in s⁻¹.
- `τ = 0.01065 × 47.88025898033584 × dial` in Pa.
- `μ = τ/γ` in Pa·s, taken from the lowest-RPM observation.

These are the repository's existing Fann conversion convention, not a newly
calibrated instrument model. See [the prior Fann boundary](boundary.md).
At least one reading is required; RPM must be unique, positive and finite;
dial must be nonnegative and finite. Zero dial yields zero viscosity; all-zero
dials are accepted. This mathematical zero limit is not a usable zero-viscosity
hydraulic fluid and is not automatically transferred to hydraulics.

Every other observation's μ must satisfy Python `math.isclose` against the
lowest-RPM μ with relative tolerance `1e-9`, absolute tolerance `0`. This is an
OpenOil-defined numerical allowance, **not** instrument uncertainty or an
engineering fit tolerance. A zero/nonzero mixture therefore fails. Input order
does not affect the result. No average conceals inconsistent observations.

For RPM/dial `(100,10)` and `(600,60)`, the transformed rates are 170.333 and
1021.998 s⁻¹; stresses approximately 5.0992475814 and 30.5954854884 Pa;
μ approximately 0.0299369333 Pa·s. `(300,50)` and `(600,75)` fail because
stress/rate is not constant. These examples are independent arithmetic, not
observed vendor output.

## Rejection and state boundaries

HTTP malformed shape/types, booleans, strings, missing/extra fields and nonfinite
values return 422 `{"detail":"invalid request body"}`. Empty readings are rejected.
Duplicate RPM returns `rpm readings must be unique`; inconsistent ratios return
`readings are inconsistent with a Newtonian model`. Nonfinite or unrepresentable
positive derived quantities return `calculation outside finite numerical range`.
Python callers receive `ValueError`; invalid RPM/dial messages are
`rpm must be positive and finite` / `dial must be nonnegative and finite`.

The study neither prints nor modifies inputs, stores cases, consumes IDs or
couples to hydraulic calculations. The browser clears results on edits,
add/remove, recalculation and failures; disables editing while a request is
pending; and retains drafts while navigating between mounted study views.
Accessible SI observation data and explicit assumptions accompany viscosity.
No time/temperature dependence, yield behavior, shear-thinning/thickening,
gels, noise fitting, pressure prediction or operational suitability is inferred.
Display precision is not engineering accuracy.
