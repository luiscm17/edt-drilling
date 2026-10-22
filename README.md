# OpenOil

OpenOil is a drilling-engineering workbench for exploring calculations with
explicit assumptions, auditable section results and saved input/result snapshots.
The hydraulic MVP models steady, incompressible, single-phase Newtonian flow in
a concentric vertical well.

**Not validated for field decisions or safety-critical pressure limits.** Passing
tests and display precision do not establish engineering accuracy. Independent
engineering validation is required before operational use.

## Quickstart

Docker Desktop (Linux containers) or Docker Engine with Compose is the only host
prerequisite. The first build needs network access; Python, uv, Node and npm
dependencies are provisioned inside Docker, not on the host.

From the repository root:

```bash
docker compose up --build
```

Open **http://127.0.0.1:5173**. Stop the foreground app with Ctrl+C.

1. Edit sections in surface-to-bottom order. Lengths and diameters use **m**;
   section length equals its vertical depth increment.
2. Enter density (**kg/m³**), dynamic viscosity (**Pa·s**) and flow (**m³/s**).
   The initial inputs provide a supported example.
3. Select **Calculate** to inspect pressure/ECD totals, section audits, friction
   bars and annular pressure/depth plots without saving. Input edits clear results.
4. Select **Save case** to calculate and store a new snapshot. **Load case**
   restores stored inputs/results without recalculation; **Refresh cases** reloads
   the ledger. Each successful save creates a distinct ID.

Errors appear in an alert without displaying a false result. Tables accompany
plots for keyboard and screen-reader access; wide tables scroll on narrow screens.

## Model boundary

| Topic | Supported scope |
| --- | --- |
| Geometry and inputs | Positive finite SI quantities; pipe ID < pipe OD < hole ID; pipe OD / hole ID ≤ 0.8; constant properties and positive flow. |
| Regimes in both passages | Re < 2300: laminar; 4000 ≤ Re ≤ 100000: smooth-wall Blasius approximation. All other regimes are rejected. Annular turbulence uses a hydraulic-diameter approximation. |
| Outputs | Pressure in **Pa**, ECD in **kg/m³**; bottomhole annular pressure includes hydrostatic pressure and annular friction. Surface annular gauge pressure is zero. Pipe friction is **not standpipe pressure**. |
| Exclusions | Bit/nozzle and surface losses, roughness, eccentricity, inclination, non-Newtonian rheology, cuttings, thermal/compressibility effects, transients, swab/surge, torque/drag and real-time data. |

Pressure-profile lines interpolate section-boundary values. Hydrostatic and
circulating curves can overlap when friction is small. Rounding is presentation,
not an accuracy guarantee.

## Product and architecture

- [Product requirements](docs/product/prd.md): user outcomes, scope, safety
  boundary and capability acceptance criteria.
- [Technical requirements](docs/architecture/trd.md): normative architecture,
  engineering contracts, storage, security and verification requirements.

The backend separates pure physics from FastAPI and SQLite, but HTTP handlers
still orchestrate calculations and directly access the concrete store. Explicit
application use cases and repository ports are a **target**, not an as-built
claim. No microservice decomposition is required.

## Local runtime and data

- React/TypeScript runs on Vite, which proxies `/api` to the FastAPI backend.
  Only **127.0.0.1:5173** is published; the API has no published host port.
- Images use `python:3.13-slim-bookworm` and `node:24-bookworm-slim`.
  Backend dependencies use frozen `uv.lock`; frontend dependencies use `npm ci`.
  Source mounts are read-only; dependencies remain in image layers.
- SQLite is stored at `/data/cases.sqlite3` in the **case-data** named volume.
  Cases survive restarts, rebuilds and ordinary `docker compose down`.
- This is a trusted-local-data development setup: no authentication, pagination,
  schema migrations, model-version metadata, update/delete API or defined
  multi-user concurrency policy. Lists return all cases; keep datasets small.
  Vite is **not a production server**. Do not expose this setup to a network or
  use it to store sensitive operational data.

## Container checks

Run from the repository root; no host language tools are required:

```bash
docker compose build
docker compose run --rm --no-deps frontend npm test -- --reporter=dot
docker compose run --rm --no-deps frontend npm run build
docker compose run --rm --no-deps backend uv run --frozen python -m unittest discover -s tests -p 'test_*.py' -v
docker compose config --quiet
```

UI tests use mocked HTTP and do not replace a real browser/API integration check.
Backend tests cover numerical behavior, HTTP validation and snapshot persistence,
not real-well accuracy. Test caches and build output remain in containers rather
than host `node_modules` or `.venv`. Rebuild after changes to package manifests or
configuration not mounted by Compose.
