# Zero-second gel / string-interior break-gel pressure boundary

This independent stateless SI study derives zero-second gel from a 3-rpm Fann
dial and estimates pressure to break that gel **inside the string only**.
It is a bounded addition to rheology coverage, not closure of WP-1.2, a
WellPlan parity claim or a validated field-design tool.

## Model and hand check

```text
tau_g (Pa) = dial_3_rpm * 0.01065 (lb/ft² per dial) * 47.88025898033584 (Pa per lb/ft²)
p_component (Pa) = 4 * tau_g * length_m / inner_diameter_m
p_interior (Pa) = sum(p_component) = 4 * tau_g * sum(length_m / inner_diameter_m)
```

For dial 10, `tau_g = 5.099247581405767 Pa`. Components `(100 m, 0.1 m)`
and `(50 m, 0.05 m)` each have L/ID = 1000. Each contributes approximately
`20396.99032562307 Pa`; total is approximately `40793.98065124614 Pa`.
These are independent arithmetic checks, not executed vendor-software results.
The returned ordered table identifies each contribution in Pa; it is not a
pressure profile or annular calculation. A uniform stress applies to all
constant circular interiors. Full precision is retained; display digits do not
certify engineering accuracy.

## Evidence and limits

The installed engineering-help topic
`c_deriv_pv_yp_0sec_gel_fann_data_calc.html` identifies zero-second gel with the
3-rpm Fann dial. The Fann stress transform is documented in
`c_shear_rate_stress_calc.html` and recorded in the existing
[Bingham boundary](boundary.md). The parent task's reconciled WebHelp evidence
supplies `p_gel = 4*tau_g*sum(component length / internal diameter)` for the
string interior. This slice uses those documented equations and explicit SI
conversions; it does not execute or reproduce proprietary implementation code.
No new runtime oracle or independent operational validation is available.

Excluded: other/timed gels, annular pressure, tool-joint losses, full WellPlan
plots/analysis, Herschel–Bulkley fitting, hydraulic coupling and persistence.
The study does not infer temperature/pressure dependence, gel evolution or
restart transients. Do not use it as a standpipe-pressure prediction, safety
limit or field recommendation without independent engineering validation.

## Public contract and rejection

`POST /api/v1/rheology/gel-break-pressure/calculate` accepts only `dial_3_rpm`
and a nonempty ordered `components` list of `length_m` and `inner_diameter_m`.
Dial is finite/nonnegative; geometries are finite/positive. Zero dial yields
zero stress and pressure for representable geometry ratios. Nonfinite ratios,
contributions or total pressure are rejected, including an overflowing ratio
with zero dial. Malformed/extra/missing fields, wrong types, booleans and
nonfinite numbers are rejected. Rejection and success are silent and neither
change saved hydraulic cases nor allocate IDs. Startup retains the existing
hydraulic database initialization, but this use case has no repository access.

Result metadata names the 3-rpm source, conversion constants, SI quantities,
model/schema versions, applicability limits and `string interior only` scope.
See [the API guide](../../backend/README.md#zero-second-gel--string-interior-break-gel-pressure)
for the request, example and exact HTTP errors. Backend tests observe the API
and saved-case routes using fresh system-temporary databases.
