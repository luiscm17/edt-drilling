# OpenOil — Product requirements

OpenOil is a drilling-engineering workbench for exploring calculations with
explicit assumptions, inspectable results and reusable cases. Its first product
capability is drilling hydraulics. The workbench supports engineering study; it
does not authorize operational decisions.

## Users and outcomes

| User | Required outcome |
| --- | --- |
| Drilling engineer or analyst | Compare the effects of well geometry, fluid properties and circulation on pressure and equivalent circulating density (ECD). |
| Technical reviewer | Trace a result to its inputs, units, model limits and section contributions. |
| Model contributor | Evaluate a bounded capability against explicit examples and acceptance criteria. |

## Hydraulic capability

Users shall be able to:

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| P1 | Define an ordered well case with section geometry, fluid properties and positive circulation flow. | Inputs display their units; users can edit sections while retaining at least one. |
| P2 | Calculate without saving. | Supported cases produce finite pressure, friction and ECD results; calculation alone creates no saved case. |
| P3 | Inspect results and limitations. | A summary, section audit and pressure profile refer to the same input; plots have accessible tabular values; applicability limits remain visible. |
| P4 | Retain and revisit a local case. | Saving creates a distinct input/result snapshot; listing and loading preserve that snapshot without silently recalculating it. |
| P5 | Prevent misleading output. | Invalid or unsupported inputs and failed requests show an actionable error, leave no false result visible and never save a partial case. Editing inputs invalidates the displayed result until recalculation. |
| P6 | Calculate an explicitly requested bit/nozzle pressure-loss contribution. | The result identifies bit/nozzle loss separately from existing hydraulic contributions, shows units and applicability, and defines any aggregate and its pressure boundary. Unsupported conditions fail visibly; requests using the existing base contract retain their established behavior. |

### Applicability and safety boundary

The hydraulic capability addresses steady, incompressible, single-phase Newtonian
flow with constant properties in a concentric vertical well. It reports section
pipe and annular friction, hydrostatic and bottomhole annular pressure, and ECD.
Pipe friction is not a standpipe-pressure prediction. Units and supported input
ranges shall be explicit to users; unsupported conditions shall be rejected rather
than extrapolated without disclosure.

The base hydraulic calculation excludes bit/nozzle and surface losses, roughness,
eccentricity, inclination, non-Newtonian rheology, cuttings, thermal or
compressibility effects, transients, swab/surge, torque/drag and live-data
integration. The separately requested bit/nozzle extension is governed by P6 and
[`docs/architecture/hydraulics-capability-design.md`](../architecture/hydraulics-capability-design.md);
it does not silently change the base calculation. Surface losses and the other
listed effects remain out of scope. None is implied by a pressure or ECD result.

**OpenOil is not validated for field decisions or safety-critical pressure limits.**
Display precision and passing software tests do not establish engineering
accuracy. Independent engineering validation is required before operational use.

## Product quality requirements

- **Traceability:** every displayed value shall identify its quantity and unit;
  case inputs and results shall remain associated. A saved result must be
  distinguishable from a new calculation under a different model definition.
- **Clarity:** unsupported conditions, errors and calculation assumptions shall
  be visible in the user workflow; a failure must not look like success.
- **Accessibility:** primary controls shall be keyboard operable; information in
  plots shall also be available as data.
- **Local data boundary:** the initial workbench is for small, trusted local
  datasets, not shared access or production operation. Network exposure and
  sensitive operational data require separately defined product controls.

## Adding capabilities

Additional drilling calculations, richer rheology and geometry, sensitivity
comparisons, import/export and live-data integration are candidates, not product
commitments. Each capability requires its own user problem, applicability domain,
units, failure behavior, measurable acceptance criteria and evidence for any
engineering claims. The [technical requirements](../architecture/trd.md) govern
how capabilities remain interoperable; the [hydraulics capability design](../architecture/hydraulics-capability-design.md)
defines the technical boundary for P6.
