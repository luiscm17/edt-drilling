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

## JSON API and saved cases

The FastAPI app is `wellplan_hydraulics.api:app`; `create_app(db_path)` allows
an isolated file database. Set `WELLPLAN_DB_PATH` before startup to choose the
SQLite file (default `cases.sqlite3` in the working directory). Its parent
folder must already exist and be writable. Startup creates the schema; importing
the module alone does not open a database. Run with uv inside a provisioned
container: `uv run --frozen uvicorn wellplan_hydraulics.api:app --host 0.0.0.0
--port 8000`, with `PYTHONPATH=/work/src`. Publish to host loopback only in the
later Docker setup; this API has **no authentication or network security**.

Both POST routes accept this exact shape (all values use the SI units above):

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
pagination, schema migration, model-version tracking, or multi-user concurrency
policy. Lists return all records; use only small trusted local datasets. SQLite
transactions commit each new record atomically and close each connection.
Filesystem/DB failures are server errors, not input-validation errors. Existing
core applicability limits still apply; table/plot presentation belongs to the UI.

### API and full-suite verification (Docker only)

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
