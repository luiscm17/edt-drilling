# Independent hydraulics workbench

```bash
docker compose up --build
```

Open **http://127.0.0.1:5173**. Docker Desktop (Linux containers) or Docker Engine
with Compose is the only host prerequisite. The first build needs network access.
Python, uv, Node and npm dependencies are provisioned **inside Docker only**;
do not install them on the host. Stop the foreground app with Ctrl+C.

This first-sprint engineering study calculates simplified steady-state drilling
hydraulics. It is an independent model: **no WellPlan parity, numerical
equivalence, or operational accuracy is claimed**. Do not use it for field
decisions or safety-critical pressure limits without independent engineering
validation.

## Use the workbench

1. Edit sections from surface to bottom. Enter length and diameters in **m**;
   each length is also its vertical depth increment. Add or remove sections as needed.
2. Enter density (**kg/m³**), dynamic viscosity (**Pa·s**) and flow (**m³/s**).
   The initial 100 m, 1000 kg/m³, 0.1 Pa·s, 0.001 m³/s example is supported.
3. **Calculate** calls `POST /api/calculate` without saving. Read the pressure/ECD
   summary, section audit, friction bars and annular pressure/depth profile.
   Input edits clear the previous results so they cannot masquerade as current.
4. **Save case** calls `POST /api/cases`, validating and calculating before
   storing a new input/result snapshot. Each successful save creates a new ID.
   The case ledger lists saved cases; **Load case** restores the inputs and stored
   snapshot. **Refresh cases** fetches the current list.

Backend rejection detail appears verbatim in an alert, with no false result.
All values are SI; pressures are **Pa**, not MPa, and ECD is **kg/m³**.
The tables provide plot data for keyboard and screen-reader access; narrow
screens can scroll wide audit tables. Gauge annular pressure is zero at surface.

## Validation and model limits

| Boundary | First-sprint behavior |
| --- | --- |
| Fluid and well | Newtonian, incompressible, single phase; concentric vertical geometry; constant properties and flow |
| Geometry | Positive dimensions, pipe ID < pipe OD < hole ID; pipe OD / hole ID ≤ 0.8 |
| Flow regimes | Re < 2300: laminar; 4000 ≤ Re ≤ 100000: smooth-wall Blasius approximation; other regimes rejected in either passage |
| Annular turbulence | Hydraulic-diameter approximation, not an exact annular correlation |
| Pressure | Hydrostatic plus annular friction gives bottomhole annular pressure and ECD; pipe friction is **not standpipe pressure** |
| Exclusions | Bit/nozzle and surface losses, roughness, eccentricity, inclination, non-Newtonian rheology, cuttings, thermal/compressibility effects, bit optimization, swab/surge, real-time data, torque/drag |

Display rounding is not accuracy certification. Pressure-profile lines interpolate
between section boundaries; the dashed hydrostatic and solid circulating lines
can overlap at small friction. See [backend/README.md](backend/README.md) for
independent formulas, API details, exact restrictions and the reference boundary.

## Container checks

Run from the repository root; no host language tools are required:

```bash
docker compose build
docker compose run --rm --no-deps frontend npm test -- --reporter=dot
docker compose run --rm --no-deps frontend npm run build
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_*.py' -v
docker compose config --quiet
```

UI tests exercise the rendered public controls with a mocked HTTP boundary:
SI edits, section operations, calculate-only behavior, tables/plots, save/list/load,
exact rejection text, stale-result clearing and network retry. They do not replace
a real browser/API integration check. Build output and test caches stay in
containers, never in host `node_modules` or `.venv`. Rebuild after changing
package manifests or configuration not mounted by Compose.

## Local architecture and data

- Exact bases: `python:3.13-slim-bookworm` and `node:24-bookworm-slim`.
  The backend uses frozen `uv.lock`; frontend uses `npm ci` with `package-lock.json`.
- Vite serves the React/TypeScript development workbench and proxies `/api` to
  `http://backend:8000`. Only UI port **127.0.0.1:5173** is published; the API
  has no published host port. Source mounts are read-only and dependencies stay
  in image layers. No host environment/cache volumes are used.
- SQLite lives at `/data/cases.sqlite3` on the Compose **case-data** named volume.
  Cases survive restarts, rebuilds and ordinary `docker compose down`.
  No destructive volume-reset command is needed for normal use.
- This is a trusted-local-data prototype: no authentication, pagination,
  schema migrations, model-version tracking, delete/update or concurrency policy.
  Lists return all cases; use small datasets. The Vite server is for local
  development, **not production deployment**. Do not expose it to a network.
