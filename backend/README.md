# Independent simplified hydraulics core

This is an **independent, simplified steady incompressible single-phase
Newtonian vertical-well model**, not WellPlan numerical equivalence or a
validated operational well-design tool. Do not use it for safety-critical
pressure limits or field decisions without independent engineering validation.

## Reference boundary

The bounded REA managed-assembly inspection recorded in
`odd/tasks/wellplan-hydraulics.md`, Log L5, identified
`DSWE.Hydraulics.Calculation.dll` as a managed assembly. That observation
**does not establish its formulas or execution**. The formulas below are
independent engineering assumptions; no proprietary implementation is copied.

## Python interface and SI units

Import `Section` and `calculate` from `wellplan_hydraulics.physics` with
`backend/src` on `PYTHONPATH`. The core uses only the Python standard library.

```python
from wellplan_hydraulics.physics import Section, calculate

result = calculate(
    sections=[Section(length_m=100, pipe_id_m=0.08,
                      pipe_od_m=0.10, hole_id_m=0.20)],
    density_kg_m3=1000, viscosity_pa_s=0.1, flow_m3_s=0.001,
)
print(round(result.ecd_kg_m3, 1))  # display rounding, not accuracy certification
```

Each section is a constant concentric circular geometry. Lengths and diameters
are metres; every length equals its vertical depth increment. Density is kg/m³,
dynamic viscosity Pa·s, and volumetric flow m³/s (positive circulation only).
`result.sections` preserves input order and supplies `pipe` and `annulus`
results with velocity m/s, dimensionless Reynolds number, regime label,
dimensionless **Darcy** friction factor (not Fanning), and friction loss Pa.
Totals are `depth_m`, `pipe_friction_pa`, `annular_friction_pa`,
`hydrostatic_pa`, `bottomhole_annular_pa` and `ecd_kg_m3`. Results are frozen
records with an immutable section tuple; the function neither prints nor
changes inputs or stored state.

## Equations and applicability boundary

For flow Q, area A, density rho, viscosity mu and hydraulic diameter Dh:
`v = Q/A`, `Re = rho*v*Dh/mu`, `dp = f*(L/Dh)*rho*v²/2`.
Pipe area is `pi*ID²/4`, Dh is ID; annular area is
`pi*(hole_ID²-pipe_OD²)/4`, Dh is `hole_ID-pipe_OD`.

- **Re < 2300:** fully developed laminar pipe flow uses `f = 64/Re`.
  The concentric annulus uses the exact Newtonian laminar expression
  `dp = 128*mu*L*Q / (pi*K)`, where
  `K = Do⁴-Di⁴-(Do²-Di²)²/ln(Do/Di)` and Do/Di are hole ID/pipe OD.
  Its reported effective Darcy factor is recovered from the pressure loss.
- **4000 <= Re <= 100000:** smooth-wall Blasius `f = 0.3164/Re^0.25`.
  Applying it with annular hydraulic diameter is a **rough approximation**,
  not an exact annular correlation or an accuracy guarantee.
- **2300 <= Re < 4000 or Re > 100000:** rejected, in either passage.
  These thresholds are model cutoffs, not universal annular transition criteria.
- All sections require `0 < pipe_ID < pipe_OD < hole_ID` and
  `pipe_OD/hole_ID <= 0.8`. The latter is a conservative model restriction,
  including avoidance of thin-gap numerical cancellation, not a validation claim.

With `g = 9.80665 m/s²`, depth H is the sum of section lengths,
`hydrostatic = rho*g*H`, `bottomhole_annular = hydrostatic + sum(annular_dp)`,
and `ECD = bottomhole_annular/(g*H)`. Surface annular gauge pressure is zero.
Pipe losses are friction magnitudes; they are **not** a standpipe-pressure
prediction. Bit/nozzle, surface equipment, entrance, junction and acceleration
losses are excluded. Properties and flow are constant throughout both passages.
Roughness, eccentricity, inclination, rotation, non-Newtonian rheology, cuttings,
compressibility, temperature effects, transients and swab/surge are unsupported.

Inputs must be positive finite Python numbers (bools are rejected), with at least
one section. Validation raises `ValueError` without output or input mutation;
unrepresentable positive finite derived quantities are also rejected. Floating
point digits are not engineering accuracy; present suitably rounded results.

## Container-only tests

From the repository root in Windows Git Bash, no host packages are needed:

```bash
MSYS_NO_PATHCONV=1 docker run --rm --network none --read-only --mount "type=bind,source=D:/Documents/GitHub/edt-drilling/backend,target=/work,readonly" --workdir /work --env PYTHONPATH=/work/src --env PYTHONDONTWRITEBYTECODE=1 python:3.13-slim-bookworm python -m unittest discover -s tests -p test_physics.py -v
```

Run with a 120-second execution timeout. The workspace mount is read-only;
bytecode generation and network access are disabled. Tests cover numerical
formulas, section additivity, hydrostatic pressure/ECD, geometry, properties,
regime endpoints and numerical-range rejection, including rejection silence and
unchanged inputs. They establish behavior of this model, not real-well accuracy.
