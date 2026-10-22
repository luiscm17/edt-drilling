# OpenOil — Technical requirements

OpenOil targets a **hexagonal modular monolith**: a pure calculation domain,
application use cases and explicit ports, with replaceable HTTP and persistence
adapters. The backend already isolates numerical calculations, but it is **not
yet a complete ports-and-adapters implementation**. This document separates
existing behavior from design requirements; it does not authorize runtime changes.

## Existing implementation

The Python modules below live under `backend/src/` in the existing hydraulics
package. Their current layout is not the target package structure.

| Responsibility | Source and behavior |
| --- | --- |
| Calculation domain | `physics.py`: immutable dataclasses and a standard-library-only `calculate` function; no HTTP, storage, output or input mutation. Domain validation raises `ValueError`. |
| HTTP and orchestration | `api.py`: strict Pydantic inputs, FastAPI routes and error translation. `CalculationInput.result()` invokes the domain; route closures directly use the concrete `CaseStore`. There is no separate application layer or repository port. |
| Persistence | `storage.py`: append-only SQLite records with an auto-increment ID and input/result JSON. Serialization rejects nonfinite numbers; each insertion is transactional. Lists are ID-ordered; reads do not recalculate. |
| UI and transport | `frontend/src/App.tsx`: React input state, fetch requests and save/list/load workflows. `frontend/src/types.ts` defines client contracts; `frontend/src/Results.tsx` renders tables and SVG plots, deriving section-boundary profile points for presentation. |
| Local runtime | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/vite.config.ts`: Python/FastAPI and React/TypeScript/Vite containers, `/api` proxy and SQLite named volume. |

Current request flow: UI → HTTP validation → calculation → response, with storage
only on save. Startup initializes the database schema. This separation is a useful
foundation, but direct HTTP-to-store coupling is not dependency inversion.

## Target boundaries and dependency direction

```text
React UI → HTTP adapter → application use cases → pure domain
                                  ↓
                           repository port
                                  ↑
                           SQLite adapter
```

- **Domain:** owns geometry, fluid/flow quantities, applicability checks and
  deterministic results. It must not import frameworks, databases or adapters.
- **Application:** owns calculate, save, list and load use cases, including
  validation-before-write and snapshot semantics. Defines the repository port
  around those operations; no SQL or HTTP concerns belong here.
- **Adapters:** HTTP validates transport shape and maps application/domain errors;
  SQLite implements the repository contract. A composition root wires concrete
  adapters to use cases. Dependencies point inward, not from domain to adapters.
- **UI:** owns editing and presentation, not authoritative hydraulic calculations.
  Display-derived plots must remain consistent with returned section results.

Keep one deployable backend with internal modules. Separate frontend/backend
containers do not imply microservices; service extraction is not a requirement.
Introduce abstractions only at actual use-case and external-system boundaries.

## Calculation and unit contracts

The supported hydraulic scope and exclusions are defined in the
[PRD](../product/prd.md#applicability-and-safety-boundary). Preserve section order,
immutable results and rejection of unsupported or nonfinite calculations.

| Quantity | Canonical unit |
| --- | --- |
| Length and diameters | m |
| Density and ECD | kg/m³ |
| Dynamic viscosity | Pa·s |
| Volumetric flow | m³/s |
| Pressure and friction loss | Pa |
| Velocity | m/s |
| Reynolds number and Darcy friction factor | Dimensionless |

SI is the domain and storage contract. Any future display-unit conversion belongs
at a boundary and must be explicit and tested; display rounding must not alter
stored values. Never substitute Fanning for Darcy factors or present pipe friction
as standpipe pressure. Unsupported regimes must fail, not silently extrapolate.

### Existing HTTP compatibility contract

| Route | Behavior to preserve |
| --- | --- |
| `POST /api/calculate` | 200 result; no persistence. |
| `POST /api/cases` | 201 `{id, input, result}`; validate and calculate before allocating an ID or writing. Duplicate successful submissions create distinct cases. |
| `GET /api/cases` | 200 array ordered by increasing ID, including stored snapshots. |
| `GET /api/cases/{id}` | 200 stored record; missing record returns 404 with `case not found`. |

Invalid bodies return 422 with `invalid request body`; malformed/out-of-range case
IDs return 422 with `invalid case id`. IDs are positive signed 64-bit integers.
Domain rejections return 422 with the domain message. These details are JSON
`detail` strings; validation must not echo untrusted payloads. Infrastructure
failures are server failures, not fabricated input errors.

## Persistence, model identity and provenance

**Existing:** SQLite stores only ID, normalized input JSON and result JSON. There
are no schema migrations, timestamps, model versions or provenance metadata. GET
returns the saved result unchanged. The Compose `case-data` volume mounts at
`/data`; data survives rebuilds and ordinary `docker compose down`.

**Target:** identify each calculation by model identifier/version, input/result
schema versions, canonical units, assumptions/correlation selection and software
revision. Save creation time and input origin with the snapshot; collect only
necessary, non-sensitive provenance. A stored result must remain distinguishable
from a recalculation under another model version.

Introduce explicit schema migrations before changing record shape. Preserve old
snapshots without inventing missing provenance; represent legacy metadata as
unknown. Define compatible reads and explicit recalculation behavior before
changing formulas or exposing versioned contracts. Storage adapters must preserve
atomic writes, finite JSON, ID ordering and rejection-without-write guarantees.

## Nonbreaking migration approach

1. Extract existing orchestration into application use cases without changing
   formulas, routes, response shapes, errors or save semantics.
2. Define the repository port from those use cases; adapt `CaseStore` and inject
   it through composition. Keep the pure calculation interface independent.
3. Add version/provenance storage through explicit migrations and compatibility
   tests; evolve public contracts deliberately rather than renaming them in place.

Keep each step independently verifiable. Package renaming is a separate
compatibility concern; documentation naming does not change import paths,
environment variables, persisted data or the running UI.

## Security and operational limits

The application is for small, trusted local datasets. It has no authentication,
authorization, pagination, update/delete API or defined multi-user concurrency
policy. Input validation is not a substitute for access control.

Compose publishes only `127.0.0.1:5173`; the backend has no host port. Source mounts
are read-only, dependencies live in images, and SQLite requires writable volume
storage. Vite is a development server, not a production serving architecture.
Do not expose this setup to a network or store sensitive operational data in it.

Production or shared use requires a separate design covering identity/access,
TLS, request/resource limits, error/log hygiene, backup/restore and recovery,
concurrency, deployment hardening and independent engineering validation. These
controls are requirements for that use, not implemented capabilities.

## Verification strategy

| Boundary | Evidence |
| --- | --- |
| Domain | `backend/tests/test_physics.py`: formula examples, section additivity, pressure/ECD, geometry, regime endpoints and finite-range rejection; check immutability and silent rejection. Software correctness is not field validation. |
| API/storage | `backend/tests/test_api.py`: public HTTP status/JSON, validation, unchanged rows and ID sequence after rejection, snapshot persistence across application instances and agreement with the core. |
| UI | `frontend/src/App.test.tsx`: rendered controls with mocked HTTP, SI edits, section actions, results, save/load, stale-result clearing and failure/retry behavior. These tests do not establish real browser/API integration. |
| Build/runtime | Docker-only tests, TypeScript/Vite build and Compose configuration checks in the [root README](../../README.md#container-checks). Manually exercise the running UI/API separately. |

As ports are introduced, add repository contract tests and application tests with
an in-memory test adapter while retaining real SQLite and HTTP integration tests.
Versioned calculations need reproducible fixtures tied to their assumptions and
model versions; broader engineering claims require independent reference evidence.
