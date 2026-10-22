# OpenOil — Product requirements

OpenOil is a drilling-engineering workbench for inspecting explicit calculation
assumptions, exploring hydraulic inputs, and retaining input/result snapshots.
Its hydraulic MVP supports engineering study, not operational authorization.

## Users and problems

| User | Need |
| --- | --- |
| Drilling engineer or analyst | Explore how geometry, fluid properties and circulation affect pressure and equivalent circulating density (ECD). |
| Technical reviewer | Inspect units, assumptions, section contributions and unsupported conditions instead of relying on an opaque total. |
| Model contributor | Evaluate a bounded calculation model through repeatable examples and explicit acceptance criteria. |

## Hydraulic MVP

The workbench accepts ordered surface-to-bottom sections and constant density,
dynamic viscosity and positive flow. Users can calculate without saving, inspect
summary and section results, and save/list/load local snapshots. Editing inputs
clears displayed results; loading a case displays its stored result, not a new
calculation. Tables accompany friction and annular pressure/depth plots.

### Applicability and safety boundary

- Steady, incompressible, single-phase Newtonian flow in a concentric vertical
  well; each section length is its vertical depth increment.
- Positive finite SI inputs; pipe ID < pipe OD < hole ID and pipe OD / hole ID
  ≤ 0.8. Both passages must have Re < 2300 or 4000 ≤ Re ≤ 100000.
- Laminar pipe and concentric-annulus calculations; smooth-wall Blasius
  turbulence with a hydraulic-diameter approximation for the annulus.
- Outputs include pipe/annular friction, hydrostatic and bottomhole annular gauge
  pressure, ECD, velocity, Reynolds number and Darcy friction factor. Surface
  annular gauge pressure is zero. Pipe friction is **not standpipe pressure**.

**Not validated for field decisions or safety-critical pressure limits.** Display
precision and passing software tests do not establish engineering accuracy.
Independent engineering validation is required before operational use.

The MVP excludes bit/nozzle and surface losses, roughness, eccentricity,
inclination, non-Newtonian rheology, cuttings, thermal/compressibility effects,
transients, swab/surge, torque/drag and real-time data. It is a trusted-local-data
application, not a multi-user or production service.

## Capability acceptance gates

These gates define expected behavior, not a claim of field validation. The
[technical requirements](../architecture/trd.md) distinguish implemented behavior
from architectural targets.

| Capability | Acceptance gate |
| --- | --- |
| Define a case | Ordered sections and fluid/flow inputs show SI units; sections can be added/removed while retaining at least one. |
| Calculate safely | Supported inputs yield finite, auditable results; unsupported geometry, regimes, types and numerical ranges are rejected with an actionable error and no false result. Calculate alone does not persist data. |
| Inspect results | Summary, section audit and plots refer to the same input snapshot; units and model limits remain visible; tabular plot data is keyboard accessible. Input edits invalidate displayed results. |
| Retain local cases | Each successful save creates a distinct ID and input/result snapshot. Invalid saves neither store a case nor consume an ID. List/load preserve stored values across application restarts. |
| Handle failures | Validation and network failures are visible; failed work does not appear as a successful calculation; users can retry. |
| Run locally | Docker Compose starts the UI on host loopback, keeps the API unpublished and persists cases in a named volume without host language dependencies. |

## Candidate capabilities, not commitments

Broader rheology and geometry, equipment losses, sensitivity comparisons,
import/export, additional drilling calculations and live-data integration are
candidates for separate study. None is promised or implied by the MVP.

Before accepting any extension, define its user problem, applicability limits,
unit contract, verification evidence and failure behavior. Changes affecting
saved calculations also require model identification and compatibility rules.
Feature-specific documentation belongs with that scoped design and implementation;
this PRD remains the product boundary rather than an implementation diary.
