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

Errors appear in an alert without displaying a false result. The navy/oxide/cream
instrument panel uses Recharts for comparable friction bars and pressure traverses,
with Tailwind CSS v4 utilities and custom instrument styling. Every chart has a
tabular equivalent; wide tables scroll on narrow screens. No external font service
or decorative component library is required.

The browser uses `POST /api/v2/calculate`, `POST /api/v2/cases`,
`GET /api/v2/cases` and `GET /api/v2/cases/{id}`. Both POST routes receive exactly
`{"input_schema_version":"1","input":{...}}`, with numeric SI inputs. Results
show the returned model identifier/version, schema versions, creation time and
recorded assumptions. Legacy snapshots with null provenance are visibly labelled
**Unknown model · legacy snapshot**, never attributed to the current model.
Calculate explicitly to obtain a new result; loading never recalculates.

## Model boundary

| Topic | Supported scope |
| --- | --- |
| Geometry and inputs | Positive finite SI quantities; pipe ID < pipe OD < hole ID; pipe OD / hole ID ≤ 0.8; constant properties and positive flow. |
| Regimes in both passages | Re < 2300: laminar; 4000 ≤ Re ≤ 100000: smooth-wall Blasius approximation. All other regimes are rejected. Annular turbulence uses a hydraulic-diameter approximation. |
| Outputs | Pressure in **Pa**, ECD in **kg/m³**; bottomhole annular pressure includes hydrostatic pressure and annular friction. Surface annular gauge pressure is zero. Pipe friction is **not standpipe pressure**. |
| Exclusions | Bit/nozzle and surface losses, roughness, eccentricity, inclination, non-Newtonian rheology, cuttings, thermal/compressibility effects, transients, swab/surge, torque/drag and real-time data. |

Pressure-profile lines interpolate section-boundary values from the returned
hydrostatic total, section lengths and cumulative returned annular losses; the UI
contains no hydraulic model or gravity constant. Hydrostatic and circulating
curves can overlap when friction is small. Tables and charts use the same snapshot.
Rounding is presentation, not an accuracy guarantee.

## Product and architecture

- [Product requirements](docs/product/prd.md): user outcomes, scope, safety
  boundary and capability acceptance criteria.
- [Technical requirements](docs/architecture/trd.md): normative architecture,
  engineering contracts, storage, security and verification requirements.

The UI presents inputs and returned snapshots; authoritative engineering
calculations remain in the backend domain. FastAPI invokes application use cases
behind a case-repository port, implemented by SQLite. No microservice
decomposition is required.

## Local runtime and data

- React/TypeScript runs on Vite, which proxies `/api` to the FastAPI backend.
  Only **127.0.0.1:5173** is published; the API has no published host port.
- Images use `python:3.13-slim-bookworm` and `node:24-bookworm-slim`.
  Backend dependencies use frozen `uv.lock`; frontend dependencies use `npm ci`.
  Source mounts are read-only; dependencies remain in image layers.
- SQLite is stored at `/data/cases.sqlite3` in the **case-data** named volume.
  Cases survive restarts, rebuilds and ordinary `docker compose down`.
- This is a trusted-local-data development setup: no authentication, pagination,
  update/delete API or defined multi-user concurrency policy. Lists return all
  cases; keep datasets small. V2 snapshots retain model-version metadata; the
  additive legacy migration leaves absent historical provenance unknown.
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

For dependency updates, mount only the two manifest files, never the whole
frontend directory, into a disposable Node container. For example, from a POSIX
shell at the repository root (Git Bash on Windows: prefix with
`MSYS_NO_PATHCONV=1` and use `pwd -W` instead of `pwd`):

```bash
docker run --rm \
  --mount "type=bind,source=$(pwd)/frontend/package.json,target=/app/package.json" \
  --mount "type=bind,source=$(pwd)/frontend/package-lock.json,target=/app/package-lock.json" \
  -w /app node:24-bookworm-slim npm install --package-lock-only --ignore-scripts --no-audit --no-fund
docker compose build frontend
```

This writes the lockfile back but keeps npm caches and any container filesystem
state off the host. The image then installs locked dependencies using `npm ci`.
`npm run build` emits a production bundle inside the disposable container; it does
not turn the Compose Vite development service into production hosting.

UI tests use mocked HTTP and do not replace a real browser/API integration check.
Backend tests cover numerical behavior, HTTP validation and snapshot persistence,
not real-well accuracy. Test caches and build output remain in containers rather
than host `node_modules` or `.venv`. Rebuild after changes to package manifests or
configuration not mounted by Compose.
