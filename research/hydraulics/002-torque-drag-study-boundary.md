# EDR-002 — Straight-well torque-and-drag study boundary

**Decision:** OpenOil provides an *independent*, quasi-static weight-and-contact study for a straight, uniformly inclined drillstring. It estimates pickup and slackoff surface tension and rotating wall-contact torque, with section contributions. It is **not** a general soft-string simulator, a reconstruction of WellPlan's calculations, or a validated operating limit. **Status:** implemented as a bounded study; field fitness and WellPlan parity unverified.

## What the reference investigation established

Read-only REA inspection identified an installed `DSWE.TorqueDrag.Calculation.dll` managed calculation assembly under WellPlan, SHA-256 `09c6d80252bdac6d7cd59149e63f6bb5d2bff0d750eb16a73d85cdd7c6e7a014` (evidence `ev_d1ac69763b27b61e0b59d486b6e4904fa27edb607ef4e603e2b919fe9df9599e`). Its .NET Framework 4.5.1 CIL metadata establishes an artifact associated with the *topic*, not a recovered vendor force balance, friction law, buoyancy definition, unit convention, acceptance range or numerical result. No WellPlan run or reference case was obtained; no vendor equation was copied. The independent assumptions below are OpenOil decisions, not inferences of WellPlan behavior. See the initial [study boundary](../torque-drag/boundary.md).

| Engineering question | This OpenOil slice answers | It does not answer |
| --- | --- | --- |
| How much does the string weigh in the selected fluid? | Idealized buoyant weight per measured metre, given an **assumed closed-pipe outer-diameter displacement envelope**. | Actual buoyancy of open-ended or fluid-filled assemblies, tool joints and pressure-dependent conditions. |
| How do inclination and assumed contact coefficients affect axial loads? | Straight-well gravity projection and Coulomb sliding-contact contributions to pickup/slackoff **surface** tension, with freely suspended bottom. | Drag at bends/doglegs, differential sticking, buckling, bit load, or measured hookload. |
| What rotating torque arises from this contact? | A wall-friction *magnitude* using a radius of half the pipe OD. | Bit or motor torque, viscous torque, tool-joint torque, direction/sign or a rig torque limit. |

## Engineering system and applicability

Represent the drillstring by sections ordered from surface to bottom. Section *i* has measured length `Lᵢ > 0` (**m**), outside diameter `Dᵢ > 0` (**m**) and air weight `wᵢ > 0` (**N/m**). The **entire** well and string are straight at one constant inclination `θ` measured **from vertical**, `0 ≤ θ < 90°`; sections may change weight and OD, not angle. One nonnegative fluid density `ρ` (**kg/m³**) and nonnegative dimensionless axial and rotational Coulomb coefficients `μa`, `μr` apply throughout. All inputs and derived quantities must be finite. Gravity is fixed at `g = 9.80665 m/s²`.

The model represents idealized wall contact in a straight bore, with the pipe OD also defining a closed displaced cylinder; it does not solve for eccentricity or clearance. There is no internal-fluid/open-end correction, bottom weight-on-bit or axial-rotation friction coupling. It assumes tension rather than compression throughout the slackoff approximation. These are *model restrictions*, not a physical assertion that a real drillstring meets them.

## Force balance and outputs

For each section compute the displaced volume per measured metre `V′ᵢ = πDᵢ²/4` (**m³/m**) and effective submerged weight `bᵢ = wᵢ − ρgV′ᵢ` (**N/m**). Reject `bᵢ ≤ 0`: this study cannot represent neutral or upward net buoyancy. The following are **section contributions**, not loads at the section interfaces:

| Quantity | OpenOil expression | Unit / interpretation |
| --- | --- | --- |
| Axial gravity | `Gᵢ = bᵢ Lᵢ cos θ` | N, gravity projected along the straight string. |
| Straight-wall normal force | `Nᵢ = bᵢ Lᵢ sin θ` | N, contact from projected submerged weight only; **no curvature force**. |
| Axial sliding friction magnitude | `Fa,ᵢ = μa Nᵢ` | N, added in pickup and subtracted in slackoff. |
| Rotating contact friction magnitude | `Fr,ᵢ = μr Nᵢ` | N, a separate idealized rotating-contact assumption. |
| Pickup / slackoff contributions | `Pᵢ = Gᵢ + Fa,ᵢ`; `Sᵢ = Gᵢ − Fa,ᵢ` | N; reject any `Sᵢ < 0` instead of displaying a compression prediction. |
| Rotating contact torque | `Tᵢ = Fr,ᵢ Dᵢ/2` | N·m, friction magnitude at the assumed OD radius. |

With a freely suspended bottom, surface pickup tension is `ΣPᵢ`, surface slackoff tension is `ΣSᵢ`, and rotating contact torque magnitude is `ΣTᵢ`. The UI displays these totals and ordered per-section contributions; it does **not** report a distributed hookload profile. At `θ = 0°`, this straight-wall model has `Nᵢ = Fa,ᵢ = Fr,ᵢ = Tᵢ = 0`; pickup and slackoff equal total submerged string weight. Unsupported geometry, negative slackoff contribution or nonfinite arithmetic rejects the whole request; it never saves a partial case. Torque-and-drag results are calculate-only and do not alter hydraulic snapshots.

## Reproducible OpenOil study case — not a WellPlan benchmark

One straight section: `L = 100 m`, `D = 0.10 m`, `w = 300 N/m`, `θ = 30°`, `ρ = 1000 kg/m³`, `μa = 0.20`, `μr = 0.30`. The idealized displacement is `0.00785398 m³/m`, giving `b ≈ 222.97875 N/m`. With the model equations above:

| Quantity | OpenOil result (rounded) | Reading |
| --- | ---: | --- |
| Axial gravity / wall normal | 19,310.53 N / 11,148.94 N | Two projections of the same submerged section weight, not two extra weights. |
| Axial / rotating friction magnitude | 2,229.79 N / 3,344.68 N | Assumed Coulomb coefficients times the normal estimate. |
| Pickup / slackoff surface tension | 21,540.31 N / 17,080.74 N | Idealized freely suspended boundary, no bit load. |
| Rotating contact torque | 167.23 N·m | Excludes bit, motor, viscous and other torque sources. |

These values were recomputed using the Docker-provisioned OpenOil calculation and are software-model outputs, **not** measured loads, WellPlan outputs or an accuracy tolerance. UI rounding to two decimals can conceal small nonzero contributions.

## Appropriate use and forbidden inferences

Use the study only to compare *within this model* the direction and relative contribution of changes in measured length, OD, air weight, fluid density, inclination and assumed friction coefficients. Inspect section totals and the domain rejection before interpreting a result. The hydraulic pressure/ECD capability is separate: its vertical-well sections and saved case IDs are not torque/drag inputs, and neither calculation supplies the other's missing physics.

**Do not use** these estimates to specify a rig hookload/torque envelope, define casing wear or a stuck-pipe margin, design a directional trajectory, decide on tripping/rotation limits or certify drillstring integrity. Dogleg severity, curvature-induced normal load, local clearance/eccentricity, bending, buckling, axial/rotational coupling, changing fluid columns, temperature/pressure, elastic effects, acceleration, bit/WOB and downhole motor torque are absent. Software tests pin these equations but do not validate field suitability.

## Evidence required before comparison or operational use

A WellPlan comparison would need a separately authorized controlled reference run with exact product/solver version, trajectory and doglegs, tubular geometry and weights, fluid/buoyancy setup, contact/friction definitions, bottom boundary, units, input/output pairs and predeclared tolerances. A field-use claim additionally needs independent engineering review and validation against appropriate measurements across straight and deviated wells, including conditions this slice explicitly rejects. Until then, **topic overlap is the only established relationship** to WellPlan.
