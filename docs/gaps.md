# OpenOil engineering capability roadmap

## Purpose and scope

This roadmap defines the documented drilling-engineering capabilities OpenOil SHALL reconstruct. Every capability below is in scope regardless of current implementation status. **MUST**, **SHALL**, and **MUST NOT** are normative. The work packages are grouped by shared engineering inputs and model boundaries; their order is a dependency-oriented roadmap, not a promise of delivery dates or any product's interface order.

The repository's [engineering capability reference](reference/drilling-capabilities.md) summarizes documented workflows, equations, outputs, and known model limits in developer-readable form. A feature name alone does not establish its equation, applicability domain, runtime behavior, or numerical parity. Where the reference identifies details as unknown, implementation MUST wait for authoritative engineering definitions rather than infer behavior from names or static call relationships.

## Roadmap

### WP-0 — Shared well, fluid, and operating inputs

**WP-0.1** OpenOil SHALL represent well path and survey stations, wellbore sections, strings, fluids and rheology, temperature, and calculation-specific operating conditions as typed inputs. Each value SHALL retain its physical quantity, unit, source or derivation, and applicable depth/rate basis.

**WP-0.2** Each calculation SHALL declare which of those inputs it consumes, the supported models and operating domain, and its validation and error behavior. OpenOil MUST NOT silently replace missing, unsupported, or out-of-domain inputs with an undocumented assumption.

### WP-1 — Hydraulics, rheology, and hole cleaning

**WP-1.1 Circulating hydraulics.** OpenOil SHALL provide distinct calculations for pressure profiles and ECD, pressure analysis, annulus pressure analysis and single annulus pressure, pressure versus pump rate, pump power, tool-joint pressure loss, and maximum backreaming rate. Results SHALL identify the modeled pressure boundary and included loss contributions.

**WP-1.2 Rheology.** OpenOil SHALL support documented Newtonian, Bingham plastic, power-law, Herschel–Bulkley, and generalized Herschel–Bulkley workflows. It SHALL provide the associated rheology derivations from viscometer data, including plastic viscosity, yield point, gel strengths, shear rate, shear stress, and pressure to break gel. The calculation's selected rheology model and units MUST be explicit in every result.

**WP-1.2 implementation boundary (open).** The current bounded studies include a Newtonian Fann viscosity derivation and an independently defined conventional Herschel–Bulkley fit, alongside the earlier model studies, zero-second gel derivation, and drillstring-interior break-gel pressure. This does **not** complete WP-1.2 or establish numerical parity with WellPlan. Timed gel strengths and annular break-gel pressure remain specification tasks: obtain an authoritative timed measurement/input protocol and conversion, and an annular geometry/equation with units, applicability, and output semantics before implementation. Installed WellPlan help names timed gel fields and specifies only the string-interior relation `4 τ_g Σ(L_c/d_i)`. Static inspection of the installed `DSWE.Hydraulics.DomainModel.dll` found break-gel input assembly that optionally converts a 3-rpm Fann reading to strength using `reading × 180/π`; this does not establish a timed acquisition protocol or an annular pressure solver. See the [WP-1.2 coverage audit](../research/rheology/wp-1.2-coverage.md) for implementation status and evidence boundaries.

**WP-1.3 Bit hydraulics and optimization.** OpenOil SHALL provide nozzle velocity, bit pressure loss, bit hydraulic power, impact-force, and hydraulics-optimization workflows. Optimization SHALL preserve the distinct documented objectives: maximum hydraulic horsepower, impact force, nozzle velocity, selected bit-loss fraction, or the specified pressure/rate method. The documented bit/nozzle equations and their API-unit conventions are summarized in the [engineering reference](reference/drilling-capabilities.md#1-hydraulics-rheology-and-hole-cleaning). Bit/nozzle loss MUST remain distinguishable from complete circulating-system or standpipe pressure unless that larger physical boundary is modeled.

**WP-1.3 implementation boundary (open).** A standalone pressure-loss hydraulic-power study accepts positive circulation rate in m³/s, an explicitly user-supplied positive pipe or annulus loss in Pa, and its passage identity. It converts to US gpm and psi and applies the documented `Q P_loss / 1714` hp relation; it neither computes the supplied loss nor substitutes the separate bit/nozzle loss. The result is temporary, versioned, and not a standpipe pressure, system aggregate, optimization, WellPlan-parity claim or field-validated result. Impact force and the distinct bit-hydraulics optimization objectives remain unimplemented.

**WP-1.4 Hole cleaning.** OpenOil SHALL provide minimum flow rate for hole cleaning, minimum-flow-rate versus rate-of-penetration analysis, and cuttings-transport calculations as distinct workflows. Their contracts SHALL specify the applicable rheology, hole and string geometry, cuttings properties, rate of penetration, rotation, flow, and depth interval; exact requirements and correlations MUST follow the authoritative model specification.

### WP-2 — Transient swab, surge, and reciprocation

**WP-2.1** OpenOil SHALL calculate transient swab/surge pressure and ECD profiles for supported string movement, including tripping and reciprocation. It SHALL provide run-depth and trip-schedule analyses, including schedules constrained by declared pore- and fracture-pressure limits.

**WP-2.2** A calculation's contract SHALL define well and string geometry, fluid compressibility and pressure/temperature dependence, movement direction and schedule, depth convention, boundary conditions, numerical method, and output semantics. OpenOil MUST NOT substitute a static pressure-loss calculation for the documented transient behavior.

### WP-3 — Torque and drag

**WP-3.1** OpenOil SHALL provide coefficient-of-friction calibration, discrete torque-and-drag calculation, normal analysis, drag-chart calculation, and stress-chart calculation as separate workflows.

**WP-3.2** The model set SHALL specify straight-string and curvilinear formulations and the applicable buoyed weight, axial force, side force, frictional drag, torque, viscous drag, buckling, loading/unloading, stress, stretch, twist, pipe-wall class, fatigue, and sheave-friction behavior. The [engineering reference](reference/drilling-capabilities.md#3-torque-and-drag) records documented component relations and distinguishes them from a complete force balance.

**WP-3.3** OpenOil MUST NOT treat a local friction relation or an independent study equation as a complete reference solver. Each workflow's force balance, options, boundary conditions, supported domain, and result contract SHALL be independently specified before implementation or parity claims.

### WP-4 — Well control, kick tolerance, and kill sheets

**WP-4.1 Kick analysis.** OpenOil SHALL provide kick-class determination and class ranges, and separately address influx estimation and circulation for kicks while drilling, after pump shutdown, and from swabbing. It SHALL calculate allowable kick volume, pit gain, temperature profile, maximum annular pressure, formation-breakdown gradient, full gas evacuation, safe drilling depth, and pressure at a depth of interest.

**WP-4.2 Kill and volume workflows.** OpenOil SHALL provide generic and deviated-well kill sheets, kill graphs, annular capacity, annulus volume, string volume, and volume from string and wellbore. Each contract SHALL make the applicable kill method, influx representation, circulation and kill-fluid conditions, rates, choke mode, well configuration, and line geometry explicit.

**WP-4.3 Model boundaries.** Pressure, pressure-gradient, pressure/volume, temperature, and depth results SHALL retain their depth association and units. The documented methane-bubble gas representation and its limitations SHALL be explicit; it MUST NOT be generalized to arbitrary or dispersed influx without evidence and a separate model contract.

### WP-5 — Underbalanced hydraulics

**WP-5.1** OpenOil SHALL provide underbalanced hydraulics for documented multiphase and foam/air-mist cases, including pressure, ECD, velocity, and cuttings-transport profiles; foam-quality versus depth; and an operating envelope relating liquid/gas injection rates to bottomhole pressure.

**WP-5.2** The implementation SHALL preserve the model's declared rheology requirements, gas/liquid injection assumptions, hydrostatic/friction behavior, geometry and deviation inputs, boundary conditions, and applicability limitations. The documented operating-envelope behavior and its near-vertical minimum-velocity limitation are summarized in the [engineering reference](reference/drilling-capabilities.md#5-underbalanced-hydraulics). OpenOil MUST NOT present that workflow as a universal multiphase optimizer.

### WP-6 — Critical speed, stuck pipe, and agitator

**WP-6.1 Critical-speed roadmap.** OpenOil SHALL evaluate critical-speed behavior across a declared rotary-speed range and measured-depth interval, with documented displacement/stress criteria and a reproducible presentation of recurring critical speeds. A critical-speed roadmap MUST NOT be represented as general vibration or fatigue-life prediction without additional validated models.

**WP-6.2 Stuck pipe.** OpenOil SHALL provide stuck-location and overpull/jar/back-off analysis with explicit pipe-strength and force assumptions. The documented assumptions concerning undamaged pipe, fatigue, and bending stress SHALL be exposed as limitations; the result MUST NOT be presented as a field diagnosis or operational authorization.

**WP-6.3 Agitator model.** OpenOil SHALL include the documented agitator-model workflow. Its equations, input semantics, and output meaning remain to be specified from authoritative engineering documentation before implementation; names alone are insufficient to choose a physical model.

## Acceptance requirements across all work packages

- Every calculation MUST have an explicit versioned input/output contract, quantity and unit definitions, equations and model options, applicability domain, assumptions, limitations, and invalid-input/error behavior.
- Shared engines MAY be used only when each workflow's equations, options, and result semantics remain explicit and independently testable.
- Deterministic tests MUST cover specified examples, unit/dimensional behavior, model boundaries, unsupported conditions, error behavior, and result provenance. Numerical expectations MUST have an independent technical basis and predeclared tolerances.
- Software tests establish implementation conformance, not engineering accuracy. Numerical parity with the documented calculations and operational suitability require separate, independently justified reference evidence and validation; neither may be claimed from names, static metadata, or matching outputs from an unvalidated model.
- Additional target capabilities SHALL be added only when supported by readable technical documentation. Unknown behavior remains an explicit specification task until resolved.
