# WellPlan engineering capabilities

This reference summarizes engineering workflows documented in WellPlan help for OpenOil developers. It describes target capabilities, not OpenOil's current implementation. The summaries are written for this repository; they are not a copy of vendor help. A named workflow does not, by itself, define its full equations, supported domain, or numerical accuracy. Unknown details remain explicit rather than inferred.

## 1. Hydraulics, rheology, and hole cleaning

WellPlan's hydraulics scope includes circulating-system pressure calculations and analyses, annular pressure, pressure profiles and equivalent circulating density (ECD), pressure versus pump rate, bit hydraulics, pump power, and hydraulic optimization. Rheology workflows include Newtonian, Bingham plastic, power-law, Herschel–Bulkley, and generalized Herschel–Bulkley models, plus deriving plastic viscosity, yield point, and gel strengths from viscometer readings, shear rate and shear stress, and pressure to break gel.

The documented calculation family also includes maximum backreaming rate, minimum flow rate for hole cleaning, cuttings transport and rate-of-penetration effects, tool-joint pressure loss, nozzle velocity, bit pressure loss, bit hydraulic power, and optimization by hydraulic horsepower, impact force, nozzle velocity, bit-pressure-loss fraction, or a specified pressure/rate method. These are distinct engineering outputs and optimization criteria; one must not be substituted for another without an explicit contract.

The help documents these API-unit equations for bit/nozzle calculations:

- Nozzle velocity: `v_n = C_d Q / (2.96 A_bit)`, with velocity in ft/s, `Q` in gpm, and total bit flow area `A_bit` in in².
- Bit pressure loss: `ΔP_lossbit = ρ v_f² / (2 g_c C_d²)`, where the help defines fluid density `ρ`, fluid velocity `v_f`, gravitational constant `g_c`, and `C_d = 0.95`. The equation page does not state the density unit inline. A dimensionally consistent API calculation using `ρ` in lbm/ft³ and `v_f` in ft/s yields pressure in lbf/ft²; conversion to psi divides by 144. Implementations must pin down the units from the complete calculation contract rather than silently assume them.
- Bit hydraulic power: `P_bitHP = Q P_loss / 1714`, where the help defines `Q` as circulation rate and `P_loss` as pressure loss in pipe or annulus. Preserve that documented variable definition; do not silently substitute bit pressure loss without a specified contract.

The divisor and velocity conversion are for the documented API-unit convention. These relationships do not alone calculate a complete circulating-system or standpipe-pressure result.

Hole cleaning is a separate workflow that uses fluid rheology and drilling/geometry conditions to determine flow requirements and transport behavior. The help names minimum-flow-rate and cuttings-transport calculations, but the complete model equations and applicability limits must be established from their engineering specifications before implementation.

## 2. Swab, surge, and reciprocation

The swab/surge module models transient pressure changes associated with axial drillstring movement, including tripping and reciprocation. Its documentation describes mass and momentum conservation with fluid compressibility and drillstring/wellbore elasticity, changing fluid properties with pressure and temperature, and a method-of-characteristics solution. The documented calculation divides the problem into propagation along the string and the return path from the string end toward bottomhole; outputs include transient pressure and ECD profiles.

The operational workflows include pressure-versus-depth/run-depth analysis and trip schedules constrained by pore- and fracture-pressure limits. Reciprocation is an operation within this dynamic context, not a synonym for a static pressure-loss calculation. Well geometry, string configuration, fluid properties, motion schedule, depth, and pressure limits must be represented according to the specific calculation contract. The full numerical scheme and its edge conditions must not be reconstructed from a feature name alone.

## 3. Torque and drag

Torque-and-drag analysis predicts measured loads and torque during drilling operations. The documented analysis family includes coefficient-of-friction calibration, discrete torque and drag, normal analysis, drag charts, and stress charts. Its technical calculation topics include buoyed weight, axial force by buoyancy or pressure methods, straight-string and curvilinear models, side force, drag force, torque, viscous drag, buckling-related additional side force, loading/unloading, pipe-wall class adjustment, stress, stretch, twist, fatigue, and sheave-friction correction.

The help documents a local friction relation for a moving string segment. With axial velocity `v_a`, tangential velocity `v_t`, resultant speed `v_r = sqrt(v_a² + v_t²)`, wall-normal force `F_N`, friction coefficient `μ`, and contact radius `r`, the axial drag component is proportional to `μ F_N |v_t / v_r|` and the torque component to `r μ F_N |v_a / v_r|`. This is a component-level relation, not a complete well-force balance. A parity implementation still needs the selected string model, force balance, buoyancy/pressure treatment, buckling behavior, friction conventions, boundary conditions, and output definitions.

## 4. Well control, kick tolerance, and kill sheets

Well-control workflows cover influx estimation and circulation for kicks while drilling, after pump shutdown, and from swabbing; kick classification; kill sheets; and pressure, volume, temperature, and depth calculations. Documented outputs include bottomhole and kick-interval pressures, allowable kick volume, pit gain over time, temperature profiles, maximum annular pressure, formation-breakdown gradient, full gas evacuation, safe drilling depth, pressure at a depth of interest, circulating pressure profiles, and animated influx circulation.

Kill-sheet workflows calculate and present the information needed for a selected kill method and include annular-capacity calculations. The help describes a methane-bubble gas model and methane-specific viscosity/compressibility calculations; its temperature profile is used for gas pressure and volume, not to alter mud density or rheology. This is a material model boundary: the documented gas representation must not be generalized to arbitrary or dispersed influx without separate evidence. The calculation equations, influx assumptions, kick/kill procedures, and operational applicability must be specified independently before implementation or parity claims.

## 5. Underbalanced hydraulics

Underbalanced hydraulics covers gas/liquid multiphase flow and foam/air-mist drilling. The documented inputs include wellbore geometry and deviation, string dimensions, injection rates, pressure-loss choices, temperature, fluid properties, and calculation options. Workflows include pressure, ECD, velocity and cuttings-transport profiles, foam quality versus measured depth, and an operating envelope relating liquid and gas injection rates to bottomhole pressure.

The documented operating-envelope method evaluates five liquid rates across a gas-rate range and identifies hydrostatic-, transitional-, and friction-dominated behavior. Its help states that increasing gas injection can first lower bottomhole pressure, then have little effect in a transitional zone, and eventually raise pressure as friction dominates. It also documents different rheology requirements for multiphase fluids versus foam/air, and warns that a minimum vertical annular-velocity assumption may be inaccurate in highly deviated sections. These method-specific conditions are not universal multiphase-flow rules; OpenOil must reproduce a documented model and its declared applicability rather than treating the plot as a generic optimizer.

## 6. Critical speed, stuck pipe, and related operations

The critical-speed roadmap evaluates a range of rotary speeds over selected measured-depth intervals and identifies recurring critical speeds from peaks in lateral displacement and equivalent resultant stress. Its documented inputs include speed range/increment and analysis settings; the roadmap can present up to ten frequent critical speeds. A critical-speed result is not, without additional evidence, a general vibration or fatigue-life prediction.

The stuck-pipe workflow estimates stuck location and supports overpull, jar-setting and back-off decisions. The documented analysis uses torque/drag-related forces, pipe stretch and yield considerations. Its stated assumptions include sound pipe without fatigue damage and limited significance of bending stress; fatigue damage is not included in that stated pipe-strength evaluation. These assumptions and the distinction between modeled loads and field diagnosis must be visible in any reconstruction.

Reciprocation has documented support within swab/surge operations. An agitator model is also named in the WellPlan calculation surface, but the help material inspected here does not establish enough of its physical model or result semantics to specify more than that target workflow. Its equations, inputs, and outputs remain an explicit evidence gap.

## Evidence and implementation boundary

This reference is based on WellPlan help topics for the Hydraulics, Swab & Surge, Torque & Drag, Well Control, Underbalanced Hydraulics, Critical Speed, and Stuck Pipe modules, supplemented by repository-local hydraulic research. The summaries identify documented capabilities and selected equations; they do not establish complete solver implementations, runtime selection, numerical parity, or operational suitability. Before implementing any workflow, developers must define its inputs, units, equations, model options, supported domain, limitations, error behavior, output semantics, and independently justified numerical verification cases.

The repository's [technical requirements](../architecture/trd.md) and [bit/nozzle pressure-loss design](../architecture/hydraulics-capability-design.md) define shared implementation constraints. The [normative roadmap](../gaps.md) defines the OpenOil target.
