# OpenOil hydraulic calculation model

This is a **simplified steady incompressible single-phase Newtonian
vertical-well model**, not a validated operational well-design tool. Do not
use it for safety-critical pressure limits or field decisions without
independent engineering validation. The equations and applicability boundaries
below define this model; unsupported conditions are rejected rather than
silently extrapolated.

## Python interface and SI units

Import `Section` and `calculate` from `openoil.domain.physics` with
`backend/src` on `PYTHONPATH`. The core uses only the Python standard library.

```python
from openoil.domain.physics import Section, calculate

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

## Application and adapter boundaries

`openoil.domain.physics` is the pure engineering model. `openoil.application.hydraulics`
owns calculate/save/list/load orchestration and accepts the `CaseRepository`
protocol from `openoil.application.ports`; neither layer depends on FastAPI,
SQLAlchemy or filesystem APIs. `openoil.adapters.outbound.case_store.CaseStore`
implements the repository port with SQLAlchemy. `openoil.main.create_app` is the
composition edge: it selects the store, initializes it at startup and wires the
application. HTTP handlers validate transport shape and translate application
errors; they contain no persistence operations or engineering formulas.

For non-HTTP callers, construct `CaseInput` with an ordered tuple of `Section`
values and the three SI fluid/flow quantities, then pass it to
`HydraulicsApplication(repository).calculate(inputs)` or `.save(inputs)`.
Calculate returns a result dictionary without touching the port. Save validates
and calculates before one atomic repository save. `.list()` and `.load(id)`
return stored snapshots without recalculation. `UnsupportedInput`,
`InvalidCaseId` and `MissingCase` distinguish application errors; infrastructure
exceptions propagate rather than becoming input errors. The existing
`CalculationInput.result()` helper remains available for compatibility.

## JSON API and saved cases

The FastAPI app is `openoil.main:app`; `create_app(db_path)` allows
an isolated file database. Set `OPENOIL_DB_PATH` before startup to choose the
SQLite file (default `cases.sqlite3` in the working directory). Its parent
folder must already exist and be writable. Startup creates the schema; importing
the module alone does not open a database. Run the FastAPI CLI inside the provisioned container:

```bash
uv run --frozen fastapi run src/openoil/main.py --host 0.0.0.0 --port 8000
```

The container sets `PYTHONPATH=/work/src`. Publish to host loopback only in the
later Docker setup; this API has **no authentication or network security**.

Both hydraulic POST routes accept this exact shape (all values use the SI
units above):

```json
{
  "sections": [
    {"length_m": 100, "pipe_id_m": 0.08, "pipe_od_m": 0.10, "hole_id_m": 0.20}
  ],
  "density_kg_m3": 1000,
  "viscosity_pa_s": 0.1,
  "flow_m3_s": 0.001
}
```

| Route | Success JSON |
| --- | --- |
| `POST /api/v1/calculate` | 200: result object with section results and totals described above; never saves |
| `POST /api/v1/cases` | 201: `{"id": 1, "input": {...}, "result": {...}}`; validates and calculates before inserting |
| `GET /api/v1/cases` | 200: array of saved records ordered by increasing ID, initially `[]` |
| `GET /api/v1/cases/{id}` | 200: saved record, or 404 `{"detail":"case not found"}` |

IDs are positive SQLite signed 64-bit integers. Malformed/out-of-range IDs return
422 `{"detail":"invalid case id"}`. Missing/unknown fields, wrong types, strings
instead of numbers, booleans, malformed JSON, and nonfinite numbers return
422 `{"detail":"invalid request body"}` (without echoing input). Finite values
outside the physics model return 422 with the exact core validation message in
`detail`. Invalid requests neither save a row nor consume an ID. Handlers do not
print; a running ASGI server may independently emit access/error logs.
OpenAPI and interactive API documentation are available at `/openapi.json` and
`/docs`. Results are stored as calculated snapshots alongside normalized inputs;
GET does not recalculate them. Identical successful saves create distinct IDs.

This small local prototype is append-only: no update/delete, names, authentication,
pagination, or multi-user concurrency policy. Lists return all records; use only small trusted local datasets. SQLite
transactions commit each new record atomically and close each connection.
Filesystem/DB failures are server errors, not input-validation errors. Existing
core applicability limits still apply; table/plot presentation belongs to the UI.

### Provenance storage and snapshot compatibility

All public API endpoints use the `/api/v1` prefix. Calculate-only study routes
below are independent of hydraulic snapshots; save/list/load retain their existing
`id`, `input` and `result` contract.
The v1 responses do not expose per-case provenance. Newly saved cases still retain
model metadata internally in nullable `provenance_json`; this is an independently
defined OpenOil model identity, not an accuracy certification. It contains
`model_id` = `openoil.hydraulics.newtonian-concentric-vertical`, `model_version` =
`1.0.0`, `units` = `SI`, string `input_schema_version` and
`result_schema_version` values of `1`, applicability/correlation/exclusion
assumptions, and `created_at` (UTC ISO-8601). Timestamps are metadata, not part of
deterministic engineering values. The frontend does not infer per-case metadata
that the public contract does not return.

Startup performs an idempotent additive migration, adding nullable
`provenance_json` to `cases`. Existing IDs and input/result JSON bytes are not
rewritten; rows whose provenance was absent remain unknown internally. The
original three-column schema and migrated schema are both accepted at startup.
Back up local databases before migration; no downgrade or concurrent-migration
policy is offered for this local prototype. List/load never recalculate,
including historical inputs unsupported today. To recalculate explicitly, submit
the desired input to `/api/v1/calculate`; save again to retain a new distinct
snapshot. No operation replaces the original result or backfills provenance.

### Calculate-only torque and drag study

`POST /api/v1/torque-drag/calculate` is separate from the hydraulic case routes.
It calls `torque_drag.calculate` and never saves a case or allocates a case ID. Startup
still initializes the existing hydraulic database. There is no torque/drag save
route or schema migration. Request and response are **raw JSON objects**, without
an `input`, `result`, version or provenance envelope. All fields are required;
unknown fields at either level are rejected. Strict numeric fields accept JSON
numbers (including integers), not strings, booleans, null or nonfinite values.
The typed request/result schemas are also exposed in OpenAPI.

Request example (vertical, zero-density reference study):

```json
{
  "sections": [{"length_m": 10, "pipe_od_m": 0.1, "air_weight_n_m": 100}],
  "inclination_deg": 0,
  "density_kg_m3": 0,
  "axial_friction_coefficient": 0.2,
  "rotational_friction_coefficient": 0.3
}
```

200 response to that request:

```json
{
  "sections": [{
    "submerged_weight_n_m": 100.0,
    "axial_gravity_n": 1000.0,
    "normal_force_n": 0.0,
    "axial_friction_n": 0.0,
    "rotational_friction_n": 0.0,
    "pickup_tension_n": 1000.0,
    "slackoff_tension_n": 1000.0,
    "rotating_torque_nm": 0.0
  }],
  "pickup_tension_n": 1000.0,
  "slackoff_tension_n": 1000.0,
  "rotating_torque_nm": 0.0
}
```

Sections retain surface-to-bottom input order. Length and OD are metres, air
and submerged weight per length are N/m, density is kg/m³, inclination is degrees
from vertical, both friction coefficients are dimensionless, forces/tensions
are N and torque is N·m. Section tensions and torque are **contributions**, not
interface loads; the three top-level values are sums of those contributions.

At least one section is required, with positive length, OD and air weight.
Density and friction coefficients must be nonnegative; `0 <= inclination_deg < 90`.
Every section must have strictly positive submerged weight and nonnegative
slackoff tension. Inputs and derived results must be finite and representable.
Malformed JSON, wrong/missing/extra fields and nonfinite numbers yield exactly
422 `{"detail":"invalid request body"}`. Domain `ValueError` yields 422
`{"detail":"<exact domain message>"}`, e.g.
`{"detail":"inclination_deg must satisfy 0 <= angle < 90"}`,
`{"detail":"submerged weight must be positive in every section"}` or
`{"detail":"slackoff tension must be nonnegative in every section"}`.
Success and rejection are silent (no handler stdout/stderr), leave saved hydraulic
snapshots unchanged and consume no IDs. Server access logs are independent.
Existing hydraulic routes and errors are unchanged.

This independent quasi-static study assumes one straight uniformly inclined
well/string, constant section weights/ODs, a closed-pipe buoyancy displacement
envelope, constant fluid density and Coulomb contact, and a freely suspended
bottom. It excludes doglegs, buckling/compression, tension-dependent normal
force, bit load, internal fluid/open-end effects, axial/rotation coupling and
viscous drag. It is not vendor-runtime parity or a field-suitability prediction.
See [the engineering boundary](../research/torque-drag/boundary.md) for equations
and exclusions; independent engineering validation remains necessary.

Rebuild after source/test changes because tests are copied into the image:

```bash
docker compose build backend
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_torque_drag_api.py' -v
```

Tests use fresh system temporary databases, observe stored data through the
public HTTP routes, and check exact errors, silence, unchanged snapshots/IDs
and preservation of hydraulic validation with the new request shape.

### Calculate-only nozzle velocity

`POST /api/v1/nozzle-velocity/calculate` is independent from hydraulic
snapshots and torque/drag. It accepts only positive
finite JSON numbers, including integers, with no strings, booleans, null,
missing or extra fields. Both fields are required. The total area is the sum
of all nozzle flow areas, **not** a diameter or an individual nozzle area.

Request (flow in m³/s and total nozzle flow area in m²):

```json
{"flow_m3_s": 0.02, "total_nozzle_area_m2": 0.0004}
```

200 response (velocity in m/s, without an envelope):

```json
{"velocity_m_s": 50.01755001755002}
```

The pure Python function `openoil.domain.nozzle_velocity.calculate(flow_m3_s,
total_nozzle_area_m2)` implements the literal documented API-unit equation
with exact conversions at the SI boundary:

```text
Q_gpm = flow_m3_s * 60 / 0.003785411784
A_in2 = total_nozzle_area_m2 / 0.0254²
v_ft_s = 0.95 * Q_gpm / (2.96 * A_in2)
velocity_m_s = v_ft_s * 0.3048
```

Last floating-point digits can vary; results are not rounded by the API.
Doubling flow doubles velocity; doubling total area halves velocity. HTTP shape,
type and positivity errors, malformed JSON and nonfinite inputs return exactly
422 `{"detail":"invalid request body"}`. Positive finite inputs producing
nonpositive or nonfinite floating-point results (including conversion overflow)
return exactly
422 `{"detail":"calculation outside finite numerical range"}`. The Python
function rejects invalid inputs with `ValueError`. Neither success nor rejection
prints, saves a case, changes a hydraulic snapshot, or consumes a case ID.
The existing app still initializes its hydraulic database at startup; the new
handler itself has no storage dependency. There is no nozzle save route,
migration, provenance envelope or alteration of hydraulic or torque/drag contracts.
Request and response schemas are available in `/openapi.json` and `/docs`.

**Formula provenance and unit caveat:** the installed, read-only engineering help
at `C:\Landmark\EDT\vendor software\webhelp\Topics\c_plot_noz_vel_calcs.html`
("Nozzle Velocity Calculation", help metadata version 5000.11.0) documents
`v_n = c_d * Q / (2.96 * A_bit)` with velocity ft/s, circulation US gpm,
total bit area in² and `c_d = 0.95`. This independent implementation retains
both literal constants, 0.95 and 2.96. Exact conversions use 1 US gallon =
0.003785411784 m³, 1 inch = 0.0254 m, 1 foot = 0.3048 m and 60 seconds/minute.
Exact unit conversion alone implies a denominator of approximately 3.116883117,
not 2.96; the latter must not be silently replaced by the coherent-SI identity
`0.95 * Q_m3_s / A_m2`. The literal documented equation is about 5.30% higher
than that identity. The meaning/precision of the documented 2.96 approximation
has not been established by an independent runtime oracle; retaining it is a
documentation-fidelity choice, not an accuracy certification or calibration.
For an independent hand check, 296 US gpm through 1 in² gives exactly
`0.95 * 296 / 2.96 = 95 ft/s`, hence `95 * 0.3048 = 28.956 m/s`.
There is **no numerical parity claim about executed vendor software**. Documentation
establishes an equation, not observed vendor-native/runtime output. No
proprietary implementation or help source is copied into this project.

This is velocity at the entered flow and area with a fixed coefficient, not a
maximum achievable velocity, nozzle optimizer, pump/pressure-loss calculation
or validated operating limit. It excludes coupled hydraulics, nozzle geometry
loss modeling, erosion and transient/multiphase effects. Existing hydraulics
still excludes bit/nozzle pressure loss. Floating-point digits are not accuracy
certification; round displays appropriately and obtain independent engineering
validation before operational use.

Rebuild because tests are copied into the image, then run focused tests:

```bash
docker compose build backend
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_nozzle_velocity.py' -v
```

Tests check independent numerical values and dynamic scaling, strict rejection,
exact public HTTP results/errors, handler silence, unchanged hydraulic snapshots
and ID allocation, and sibling routes' rejection of the new input shape.

### Calculate-only hydraulic power from supplied passage loss

`POST /api/v1/bit-hydraulic-power/calculate` accepts only positive finite SI
`flow_m3_s`, positive finite `pressure_loss_pa`, and `pressure_boundary` equal
to `"pipe"` or `"annulus"`. Example:

```json
{"flow_m3_s":0.0000630901964,"pressure_loss_pa":6894.757293168,"pressure_boundary":"pipe"}
```

It converts SI to US gpm and psi before applying the documented
`Q[gpm] * P_loss[psi] / 1714` hp relation. The example returns approximately
`0.0005834305718 hp`. The versioned result includes `power` with unit `hp`,
the selected passage, model identity, and limits. The **supplied** pressure loss
is neither calculated nor replaced with bit/nozzle loss. No coupling to the
hydraulic ledger, standpipe pressure, optimization, vendor parity, or field
validation is implied. Missing/extra fields, nonpositive inputs and invalid
passage return HTTP 422 `{"detail":"invalid request body"}`; nonrepresentable
results return 422 `{"detail":"calculation outside finite numerical range"}`.
The route is stateless and never saves cases. Run its public API checks with
`PYTHONPATH=src uv run python -m unittest discover -s tests -p 'test_bit_hydraulic_power_api.py' -q`.

### Calculate-only bit/nozzle pressure-loss study

`POST /api/v1/bit-nozzle-pressure-loss/calculate` is an independent, stateless
calculation, separate from the hydraulic case routes, nozzle-velocity and
torque/drag requests; it neither saves cases nor allocates IDs. Request and
response are raw JSON objects without a versioned or saved-case envelope. The request requires exactly
three positive finite JSON numbers: `density_kg_m3`, `flow_m3_s`, and
`total_nozzle_area_m2` (the sum of effective nozzle areas, not a diameter or the
area of one nozzle). Strings, booleans, missing/extra fields and nonfinite values
are rejected. Schemas are exposed in OpenAPI.

Example request (296 US gpm, 1 in² TFA, 10 ppg):

```json
{"density_kg_m3":1198.2642731689612,"flow_m3_s":0.0186746981344,"total_nozzle_area_m2":0.00064516}
```

The response identifies `pressure_loss` as quantity `bit_nozzle_pressure_loss`
in Pa, model `openoil.hydraulics.documented-bit-nozzle-pressure-loss` version
`1.0.0`, input/result schema version `1`, fixed documented `Cd = 0.95`, and
applicability status, assumptions and limitations. The example derives approximately `556612.8 Pa` from the documented equations;
it is not a vendor-software runtime result or field validation.

The pure function `openoil.domain.bit_nozzle_pressure_loss.calculate`
reuses the documented nozzle velocity relation, retaining its literal `2.96`
coefficient and conversions from SI; it then calculates
`ΔP = ρ v² / (2 Cd²)` in Pa. Applicability is steady incompressible single-phase
flow with constant density and supplied effective total area. The route reports
one contribution only; it defines no system aggregate and never labels the value
standpipe pressure. It excludes system optimization, parasitic/tool-joint and
surface losses, erosion, non-Newtonian, compressible, transient and multiphase
effects. The three input quantities cannot detect the excluded operating
conditions, so use only within the stated assumptions and independently validate
before engineering decisions. Full precision feeds calculations; the UI may
round to four decimals, which is not accuracy.

Malformed, missing/extra, nonnumeric, nonfinite, nonpositive inputs return exact
422 `{"detail":"invalid request body"}`. Unrepresentable derived values return
422 `{"detail":"calculation outside finite numerical range"}`. Success and
rejection produce no handler output, leave hydraulic snapshots unchanged and
consume no ID. The existing hydraulic, nozzle-velocity and torque/drag routes
retain their behavior. See the [installed engineering documentation, static REA
evidence and SI derivation](../research/hydraulics/004-bit-nozzle-pressure-loss.md).

Rebuild because tests are copied into the image, then run the focused checks:

```bash
docker compose build backend
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_bit_nozzle_pressure_loss.py' -v
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_api.py' -v
```

### Generalized Herschel–Bulkley parametric study

`POST /api/v1/rheology/generalized-hb/calculate` evaluates supplied SI parameters. It neither fits Fann observations nor computes foam/circulation pressure, persists a case or changes hydraulic results. The required raw JSON input is:

```json
{"reference_stress_pa":10,"zero_shear_stress_pa":3,"high_shear_viscosity_pa_s":0.2,"stress_exponent":2,"rate_exponent":2,"shear_rates_s_inv":[0,40]}
```

The response contains those parameters and units, ordered `curve` points (`shear_rate_s_inv` in s⁻¹; `shear_stress_pa` in Pa), model/schema versions and limitations. The example yields 3 Pa at zero shear and approximately 8.544 Pa at 40 s⁻¹. `reference_stress_pa`, `stress_exponent` and `rate_exponent` must be positive finite numbers; zero-shear stress and high-shear viscosity must be nonnegative finite numbers; at least one unique nonnegative finite shear rate is required. Malformed/extra fields, booleans, strings and nonfinite inputs are rejected with 422 `{"detail":"invalid request body"}`; duplicate rates and unrepresentable derived values are rejected with a specific 422 detail. All rejections leave stored cases and IDs unchanged. The independent SI equation, limits and static-source distinction are in [the model boundary](../research/rheology/generalized-hb-boundary.md). The UI shows a modeled curve and accessible data, **not** invented observations or measured reference results. No numerical parity or field validity is claimed.

Focused tests from `backend/` with `backend/src` on `PYTHONPATH`:

```bash
python -m unittest discover -s tests -p 'test_generalized_hb_rheology.py' -v
python -m unittest discover -s tests -p 'test_api.py' -k generalized_hb -v
```

### Calculate-only Herschel–Bulkley rheology study

`POST /api/v1/rheology/herschel-bulkley/calculate` evaluates the conventional equation `τ = τ₀ + K γⁿ` from explicitly supplied SI parameters; it does not fit Fann observations. Input is `{"yield_stress_pa":3,"consistency_index_pa_s_n":0.2,"flow_behavior_index":1,"shear_rates_s_inv":[0,40]}`. The response contains parameter values/units, the ordered shear-rate/stress curve, model/schema versions and applicability limits. The example returns 3 Pa at zero shear and 11 Pa at 40 s⁻¹.

Yield stress and consistency index must be finite and nonnegative, n positive finite, and rates nonempty, unique, finite and nonnegative. Unknown fields, wrong types, booleans, malformed JSON or nonfinite input are rejected with 422 `{"detail":"invalid request body"}`; duplicate values or unrepresentable outputs are rejected with a specific 422 detail. The endpoint is stateless and does not change cases or consume IDs. The curve has no measured points, and the study does not integrate with hydraulics or calculate gel strengths/pressure to break gel. For the equation, SI contract and limits of static reference evidence, see [the study boundary](../research/rheology/herschel-bulkley-boundary.md).

Focused checks from `backend/` with `backend/src` on `PYTHONPATH`:

```bash
python -m unittest discover -s tests -p 'test_herschel_bulkley_rheology.py' -v
python -m unittest discover -s tests -p 'test_api.py' -k herschel_bulkley -v
```

### Calculate-only conventional HB multi-reading fit

`POST /api/v1/rheology/herschel-bulkley-fit/calculate` is separate from the
unchanged `/rheology/herschel-bulkley/calculate` supplied-parameter route.
The new route accepts only `{"readings":[{"rpm":1,"dial":5},{"rpm":4,"dial":8},{"rpm":9,"dial":11}]}`:
3–1000 distinct positive finite RPM readings and nonnegative finite dial values.
It uses all readings, not only 300/600 RPM. No strings, booleans, null, unknown
fields or nonfinite values are accepted. OpenAPI describes the strict schemas.

The model `openoil.rheology.fann-herschel-bulkley-fit` version `1.0.0` (input and
result schema `1`) returns `parameters` (yield stress Pa, consistency Pa·s^n,
flow index dimensionless), sorted `points` with RPM, dial, `shear_rate_s_inv`,
measured `shear_stress_pa`, `predicted_stress_pa` and `residual_pa` (predicted
minus measured), `diagnostics`, and applicability limits. Diagnostics include
SSE Pa², RMSE Pa, maximum absolute residual Pa, grid bounds/step, 391 profile
evaluations, `at_n_bound`, and near-optimal exponent span/count with an explicit
non-uniqueness warning. No extrapolated curve is supplied.

The standard-library solver minimizes unweighted stress SSE with nonnegative
τ₀/K over `n=0.05,0.055,…,2` (step 0.005), using exact constrained linear
least squares at each n. Success means the finite search completed, **not**
continuous convergence, unique parameters or statistical accuracy. Near-optimal
means normalized MSE ≤ minimum + 10⁻⁶, not a confidence interval. Constant,
zero, insufficiently separated or zero-consistency data are rejected; physical
residual overflow is rejected too. Shape errors return 422
`{"detail":"invalid request body"}`; domain errors return 422 with the exact
`ValueError` message (e.g. `rpm readings must be unique` or
`degenerate readings: insufficient stress variation`). Neither success nor
rejection prints, saves, changes existing cases or consumes IDs.

See [the independent numerical contract](../research/rheology/herschel-bulkley-fit-boundary.md)
for the full objective, bounds, tie policy, degeneracy cutoffs, complete-search
policy and hand-checkable example: shear rates `[1,4,9]`, stresses `[5,8,11]`
recover τ₀=2, K=3, n=0.5 with zero residual to roundoff. Convert those SI values
to RPM/dial as documented there; the simple raw RPM/dial request above is not
that same SI example. The accessible UI exposes all points and diagnostics,
invalidates stale results and disables edits during fitting. There is no
WellPlan/vendor parity, generalized-HB fitting, hydraulic coupling or field
validation; small residuals do not validate a fluid model.

Focused checks from `backend/`, with `src` on `PYTHONPATH` and bytecode disabled:

```bash
.venv/Scripts/python.exe -m unittest discover -s tests -p test_herschel_bulkley_fit.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -p test_api.py -k hb_fit -v
```

From `frontend/`: `npm test -- --run src/features/rheology/HerschelBulkleyFitStudy.test.tsx src/pages/WorkbenchPage.test.tsx --no-cache`.

### Calculate-only Power Law rheology study

`POST /api/v1/rheology/power-law/calculate` accepts `{"readings":[{"rpm":300,"dial":50},{"rpm":600,"dial":75}]}`. It returns transformed observations in SI, a model curve at entered RPM values, dimensionless `flow_behavior_index` (n), `consistency_index` (K) in Pa·s^n, model/schema versions and applicability limits. For this example n is approximately `0.5849625007` and K is `0.6639753206 Pa·s^n` (independent arithmetic, not an observed reference-software output). The curve uses `τ = K γ^n`, with γ in s⁻¹ and τ in Pa. The [engineering boundary](../research/rheology/power-law-boundary.md) records the installed help equations, SI interpretation, static REA limits and validation cases.

The 300/600 RPM dials must be finite, strictly positive and increasing; all RPMs must be unique positive finite numbers, and optional dial readings may be zero but not negative. Additional readings are observations, not a regression. Malformed JSON, unknown fields, strings, booleans, nonfinite inputs and missing readings return 422 `{"detail":"invalid request body"}`. Invalid model-domain input returns 422 with the explicit validation message. Unrepresentable outputs are rejected. This is a separate calculate-only study: it does not persist, consume case IDs, run hydraulic calculations, or claim runtime parity or field validity. The UI presents the SI curve and measured points with an accessible table.

Focused checks from `backend/` with `backend/src` on `PYTHONPATH`:

```bash
python -m unittest discover -s tests -p 'test_power_law_rheology.py' -v
python -m unittest discover -s tests -p 'test_api.py' -k power_law -v
```

### Zero-second gel / string-interior break-gel pressure

`POST /api/v1/rheology/gel-break-pressure/calculate` is an independent,
stateless SI study, not a hydraulic case calculation. It never saves or consumes
IDs. `/docs` and `/openapi.json` expose its strict request and result schemas.

```json
{"dial_3_rpm":10,"components":[{"length_m":100,"inner_diameter_m":0.1},{"length_m":50,"inner_diameter_m":0.05}]}
```

The 3-rpm Fann dial defines **zero-second gel**, not a timed-gel measurement.
The example returns `gel_stress.value` approximately `5.0992475814 Pa` and
`pressure.value` approximately `40793.980651 Pa`, with two ordered
`components` contributions of approximately `20396.990326 Pa` each.
Each component echoes `length_m` and `inner_diameter_m` and supplies `pressure_pa`.
The response identifies the source dial/RPM and conversion constants, quantity
names/units, model `openoil.rheology.fann-zero-second-gel-break-pressure`, model
version `1.0.0`, input/result schema version `1`, applicability and explicit
`scope: "string interior only"`.

Dial must be a finite nonnegative number (zero returns zero pressure); at least
one component with positive finite length and inner diameter in metres is
required. Missing/extra fields, strings, booleans, malformed JSON, nonfinite or
out-of-bound inputs return 422 `{"detail":"invalid request body"}`.
Unrepresentable intermediate or final values return 422
`{"detail":"calculation outside finite numerical range"}`. Success and rejection
produce no handler stdout/stderr, leave stored cases unchanged and consume no ID.

The pure `openoil.domain.gel_break_pressure.calculate(dial_3_rpm, components)`
accepts ordered `Component(length_m, inner_diameter_m)` records and raises
`ValueError` for invalid input. It reuses the existing Fann stress conversion:
`tau_g = dial_3_rpm * 0.01065 * 47.88025898033584 Pa` and
`p = 4*tau_g*sum(length_m/inner_diameter_m)`.
This is **string interior only**: no annulus, timed gels, tool-joint losses,
Herschel–Bulkley fitting, hydraulic coupling or WellPlan parity. Not validated
for field decisions. See [the source/model boundary](../research/rheology/gel-break-boundary.md).

Use the read-only Docker runner in “API and full-suite verification” below with
`-p 'test_gel_break_pressure.py'` first, then `-p 'test_api.py'` and the backend
suite. The tests cover numerical conversion, zero, geometry, finite-range
rejection, source/units, statelessness and existing-route isolation.

### Calculate-only Newtonian rheology study

`POST /api/v1/rheology/newtonian/calculate` accepts a strict raw JSON object:

```json
{"readings":[{"rpm":100,"dial":10},{"rpm":600,"dial":60}]}
```

At least one reading is required, with unique positive finite RPM and nonnegative
finite dial. The pure `openoil.domain.newtonian_rheology.calculate` accepts the
existing `bingham_rheology.FannReading` records. It reuses `γ = 1.70333 × RPM`
and `τ = 0.01065 × 47.88025898033584 × dial` in SI, and derives `μ = τ/γ`
from the lowest RPM. The example yields approximately `0.0299369333 Pa·s`.
Zero dial returns zero viscosity. Every other ratio must agree within relative
`1e-9`, absolute `0`; this is numerical tolerance, not a noisy-data fit. One
reading assumes rather than establishes Newtonian behavior.

The response contains sorted transformed `readings` (`shear_rate_s_inv`,
`shear_stress_pa`), `dynamic_viscosity` with quantity `dynamic_viscosity`, value
and unit `Pa·s`, model ID `openoil.rheology.fann-newtonian`, model version `1.0.0`,
input/result schema version `1`, and applicability assumptions/limitations.
OpenAPI exposes the request and response schemas. Unknown fields, wrong types,
strings, booleans, empty lists and nonfinite input return 422
`{"detail":"invalid request body"}`. Duplicate RPM returns 422 detail
`rpm readings must be unique`; nonconstant ratios return
`readings are inconsistent with a Newtonian model`; unrepresentable derived
values return `calculation outside finite numerical range`.

This stateless zero-yield-stress, constant-viscosity assumption has no hydraulic
coupling, case persistence, ID allocation, WellPlan/vendor parity or field
validation. All-zero readings are a mathematical limit, not a hydraulic input
recommendation. The UI provides accessible SI data, clears stale results on
edits/failures, and disables input while calculating. See [the numerical boundary](../research/rheology/newtonian-boundary.md).

Focused checks from `backend/` with `src` on `PYTHONPATH`:

```bash
.venv/Scripts/python.exe -m unittest discover -s tests -p test_newtonian_rheology.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -p test_api.py -k newtonian -v
```

From `frontend/`: `npm test -- --run src/features/rheology/NewtonianRheologyStudy.test.tsx src/pages/WorkbenchPage.test.tsx --no-cache`.

### Calculate-only Bingham rheology study

`POST /api/v1/rheology/bingham/calculate` accepts a raw JSON object and returns a
raw result object. It is separate from hydraulic case calculation and storage:
there is no save route, case snapshot, ID allocation or hydraulic coupling. The
request schema is available in OpenAPI. Every reading has a positive finite `rpm`
and a nonnegative finite `dial`; readings must have unique RPM values and include
both 300 and 600 RPM. Unknown or extra fields, strings, booleans, null, malformed
JSON, and nonfinite numbers are rejected as 422 `{"detail":"invalid request body"}`.
Negative derived plastic viscosity or yield point is rejected with its exact
model message; zero is allowed in this standalone study.

Example request:

```json
{"readings":[{"rpm":300,"dial":50},{"rpm":600,"dial":75}]}
```

The response identifies `plastic_viscosity` in Pa·s, `yield_point` in Pa,
transformed observations (`shear_rate_s_inv` in s⁻¹ and `shear_stress_pa` in Pa),
model/schema versions, and applicability limits. For the example, PV is
approximately `0.024947444 Pa·s` and YP is approximately `12.748119 Pa`. These
are independently calculated OpenOil values, not a reference-software runtime
result.

The pure function `openoil.domain.bingham_rheology.calculate` implements the
explicit transforms and two-point derivation documented in
[`research/rheology/boundary.md`](../research/rheology/boundary.md). The 300/600
RPM observations alone define PV and YP. Optional additional readings are
transformed and plotted but are not fit into a regression or used to change the
Bingham parameters. The study excludes gels, other rheology models, and hydraulics
integration. The frontend shows the measured points and derived Bingham line in
SI, with an accessible data table; displayed digits are not accuracy. There is no
claim of exact interface or numerical parity and this is not validated for field
decisions.

Success and rejection produce no handler output, leave saved hydraulic cases
unchanged, and consume no IDs. The existing hydraulic, nozzle-velocity,
torque/drag and bit/nozzle routes are unchanged. Rebuild because tests are copied
into the image, then run focused checks:

```bash
docker compose build backend
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_bingham_rheology.py' -v
docker compose run --rm --no-deps backend sh -c "cd /app/tests && uv run --frozen python -m unittest test_api.ApiTests.test_bingham_rheology_is_stateless_strict_and_does_not_change_sibling_routes -v"
```

The tests exercise public HTTP output/errors, strict rejection, unchanged saved
rows and IDs, handler silence, and sibling-route behavior with the new request
shape.

### API and full-suite verification (Docker only)

When the backend image is already provisioned, test the current checkout rather
than the image's copied tests with this read-only bind mount. The disposable
container uses a `/tmp` tmpfs for test databases, with no network or host caches:

```bash
MSYS_NO_PATHCONV=1 docker run --rm --network none --read-only --tmpfs /tmp --mount "type=bind,source=D:/Documents/GitHub/edt-drilling/backend,target=/work,readonly" --workdir /work --env PYTHONPATH=/work/src --env PYTHONDONTWRITEBYTECODE=1 edt-drilling-backend:latest /opt/venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Use `-p test_application.py`, `-p test_api.py`, or
`-p test_case_schema_compatibility.py` for focused checks. Case schema tests start
with an isolated original three-column SQLite fixture and check restart, migration
idempotence, unchanged JSON bytes/IDs, unknown historical provenance, no implicit
calculation, and rejection atomicity. Application tests use a fake port to check
write ordering, ID allocation, rejection silence, snapshot semantics and
propagation of infrastructure failures. API tests pin the `/api/v1` routes, JSON,
validation messages, persistence and Python helper interface.


This command provisions uv and locked dependencies only inside the disposable
container. Its workspace is read-only; environments, caches, and isolated test
databases are in container `/tmp`, never in host global caches. Network is used
for package provisioning, not by the tests. Run from Windows Git Bash:

```bash
MSYS_NO_PATHCONV=1 docker run --rm --mount "type=bind,source=D:/Documents/GitHub/edt-drilling/backend,target=/work,readonly" --workdir /work --env PYTHONPATH=/tmp/uv:/work/src --env PYTHONDONTWRITEBYTECODE=1 --env UV_CACHE_DIR=/tmp/uv-cache --env UV_PROJECT_ENVIRONMENT=/tmp/venv python:3.13-slim-bookworm sh -c 'python -m pip install --no-cache-dir --target /tmp/uv uv && python -m uv run --frozen python -m unittest discover -s tests -p test_api.py -v'
```

For the full suite, replace `-p test_api.py` with `-p "test_*.py"`. Allow 240
seconds for package downloads. HTTP tests assert exact JSON/status, rejection
silence, unchanged rows and ID sequence, persistence across app instances, and
agreement with the existing core for laminar and turbulent multi-section inputs.
