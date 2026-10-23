# OpenOil hydraulic calculation model

This is a **simplified steady incompressible single-phase Newtonian
vertical-well model**, not a validated operational well-design tool. Do not
use it for safety-critical pressure limits or field decisions without
independent engineering validation. The equations and applicability boundaries
below define this model; unsupported conditions are rejected rather than
silently extrapolated.

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

## Application and adapter boundaries

`physics.py` remains the pure domain model and retains its existing imports.
`application.py` owns calculate/save/list/load orchestration and accepts a
`CaseRepository` protocol from `ports.py`; neither module depends on FastAPI,
SQLite or filesystem APIs. `storage.py` supplies the existing structural port
implementation, `CaseStore`. `create_app` in `api.py` is the composition edge:
it selects the store, initializes it at startup and wires the application.
HTTP handlers validate transport shape and translate application errors; they
contain no persistence operations or engineering formulas.

For non-HTTP callers, construct `CaseInput` with an ordered tuple of `Section`
values and the three SI fluid/flow quantities, then pass it to
`HydraulicsApplication(repository).calculate(inputs)` or `.save(inputs)`.
Calculate returns a result dictionary without touching the port. Save validates
and calculates before one atomic repository save. `.list()` and `.load(id)`
return stored snapshots without recalculation. `UnsupportedInput`,
`InvalidCaseId` and `MissingCase` distinguish application errors; infrastructure
exceptions propagate rather than becoming input errors. The existing
`CalculationInput.result()` helper remains available for compatibility.

`calculate_versioned`, `save_versioned`, `list_versioned` and `load_versioned`
expose the provenance-bearing contract described below. Existing application
methods preserve their original result/record shapes.

## JSON API and saved cases

The FastAPI app is `wellplan_hydraulics.api:app`; `create_app(db_path)` allows
an isolated file database. Set `WELLPLAN_DB_PATH` before startup to choose the
SQLite file (default `cases.sqlite3` in the working directory). Its parent
folder must already exist and be writable. Startup creates the schema; importing
the module alone does not open a database. Run with uv inside a provisioned
container: `uv run --frozen uvicorn wellplan_hydraulics.api:app --host 0.0.0.0
--port 8000`, with `PYTHONPATH=/work/src`. Publish to host loopback only in the
later Docker setup; this API has **no authentication or network security**.

Both V1 hydraulic POST routes accept this exact shape (all values use the SI units above):

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
| `POST /api/calculate` | 200: result object with section results and totals described above; never saves |
| `POST /api/cases` | 201: `{"id": 1, "input": {...}, "result": {...}}`; validates and calculates before inserting |
| `GET /api/cases` | 200: array of saved records ordered by increasing ID, initially `[]` |
| `GET /api/cases/{id}` | 200: saved record, or 404 `{"detail":"case not found"}` |

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

### Versioned snapshots and compatibility

V1 routes above keep their exact request/response/error contracts. V2 POST routes
require a strict envelope: `{"input_schema_version":"1","input":{...}}`, where
`input` is the same SI calculation input shown above. Other schema versions,
extra fields (including client-supplied provenance), or malformed envelopes return
422 `{"detail":"invalid request body"}`. Model selection is server-owned.

| Route | Success JSON |
| --- | --- |
| `POST /api/v2/calculate` | 200: `{"input":{...},"result":{...},"provenance":{...}}`; no write |
| `POST /api/v2/cases` | 201: the same snapshot plus a stable distinct `id` |
| `GET /api/v2/cases` | 200: snapshots ordered by increasing ID |
| `GET /api/v2/cases/{id}` | 200: stored snapshot |

V2 uses the same engineering rejection messages, invalid-ID 422 and missing-case
404 bodies as V1. Infrastructure failures remain 500 `Internal Server Error`,
not input errors. Rejected requests neither change snapshots nor consume IDs.

New saves through **either** version atomically retain provenance; V1 responses
omit it. Provenance contains `model_id` =
`openoil.hydraulics.newtonian-concentric-vertical`, `model_version` = `1.0.0`,
`units` = `SI`, `input_schema_version` = `1`, `result_schema_version` = `1`
(all version values are strings), `assumptions` (applicability, correlations and
exclusions), and `created_at` (UTC ISO-8601 snapshot creation time). This is an independently defined OpenOil model identity, not an accuracy
certification. Calculation timestamps are metadata, not part of deterministic
engineering values.

Startup performs an idempotent additive migration, adding nullable
`provenance_json` to `cases`. Existing IDs and input/result JSON bytes are not
rewritten; existing rows expose `provenance: null` in V2, meaning **unknown**,
not inferred legacy model identity. The original three-column schema and migrated
schema are both accepted at startup. Back up local databases before migration;
no downgrade or concurrent-migration policy is offered for this local prototype.
List/load never recalculate, including historical inputs unsupported today.
To recalculate explicitly, submit the desired input to a calculate route; save
again to retain a new distinct snapshot under the current model. No operation
replaces the original result or backfills its provenance.

### Calculate-only torque and drag study

`POST /api/torque-drag/calculate` is separate from hydraulic V1/V2. It uses
`torque_drag.calculate` and never saves a case or allocates a case ID. Startup
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
viscous drag. It is not WellPlan parity or a field-suitability prediction.
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

`POST /api/nozzle-velocity/calculate` is an independent calculation, not an
addition to hydraulic V1/V2 snapshots or torque/drag. It accepts only positive
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

The pure Python function `wellplan_hydraulics.nozzle_velocity.calculate(flow_m3_s,
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
migration, provenance envelope or alteration of V1/V2 or torque/drag contracts.
Request and response schemas are available in `/openapi.json` and `/docs`.

**Formula provenance and unit caveat:** the installed, read-only WellPlan help
at `C:\Landmark\EDT\WellPlan\webhelp\Topics\c_plot_noz_vel_calcs.html`
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
There is **no numerical parity claim about executed WellPlan**. Documentation
establishes an equation, not observed WellPlan native/runtime output. No
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
exact public HTTP results/errors, handler silence, unchanged V1/V2 snapshots and
ID allocation, and sibling routes' rejection of the new input shape.

### Calculate-only bit/nozzle pressure-loss study

`POST /api/bit-nozzle-pressure-loss/calculate` is an independent, stateless
calculation. It does not extend hydraulic V1/V2, nozzle-velocity or torque/drag
requests; it neither saves cases nor allocates IDs. Request and response are raw
JSON objects without a V2 or saved-case envelope. The request requires exactly
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
applicability status, assumptions and limitations. The example derives
approximately `556612.8 Pa` from the documented equations; it is not a WellPlan
runtime result or field validation.

The pure function `wellplan_hydraulics.bit_nozzle_pressure_loss.calculate`
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
retain their behavior. See the [WellPlan documentation, static REA evidence and
SI derivation](../research/hydraulics/004-bit-nozzle-pressure-loss.md).

Rebuild because tests are copied into the image, then run the focused checks:

```bash
docker compose build backend
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_bit_nozzle_pressure_loss.py' -v
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_api.py' -v
```

### API and full-suite verification (Docker only)

When the backend image is already provisioned, test the current checkout rather
than the image's copied tests with this read-only bind mount. The disposable
container uses a `/tmp` tmpfs for test databases, with no network or host caches:

```bash
MSYS_NO_PATHCONV=1 docker run --rm --network none --read-only --tmpfs /tmp --mount "type=bind,source=D:/Documents/GitHub/edt-drilling/backend,target=/work,readonly" --workdir /work --env PYTHONPATH=/work/src --env PYTHONDONTWRITEBYTECODE=1 edt-drilling-backend:latest /opt/venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Use `-p test_application.py`, `-p test_api.py`, or `-p test_versioned_cases.py`
for focused checks. Versioned tests start with an isolated original three-column
SQLite fixture and check restart, migration idempotence, unchanged JSON bytes/IDs,
unknown historical provenance, no implicit calculation, and rejection atomicity. Application
tests use a fake port to check write ordering, ID allocation, rejection silence,
snapshot semantics and propagation of infrastructure failures. API tests preserve
the existing routes, JSON, validation messages, persistence and helper interface.


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
