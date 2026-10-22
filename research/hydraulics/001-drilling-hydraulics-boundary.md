# EDR-001 — Drilling-hydraulics study boundary

**Decision:** This ODD delivers an *independent*, steady, vertical-well hydraulics study for OpenOil: section-by-section pipe and annular friction, annular bottomhole pressure, and equivalent circulating density (ECD). It is not an implementation, reconstruction, or numerical validation of WellPlan's hydraulics solver. **Status:** implemented as a bounded study model; field fitness and WellPlan parity unverified.

## What the WellPlan investigation established

Static inspection identified a pressure-profile analysis executor, an ECD calculation service, and a call through `ManHYDPRESSPROFILE` to a declared native `HYDPRESSPROFILE` boundary. This establishes a **call relationship and engineering topic**, not the solver's equations, parameter semantics, units, outputs, correlations, coefficients, validity range, or runtime behavior. No WellPlan calculation was executed and no reference input/output pair was obtained. Artifact hashes, exact member evidence IDs, and inspection limits are recorded in [the bounded static evidence](evidence.md).

| Engineering topic | Covered in this OpenOil slice | Relationship to WellPlan evidence |
| --- | --- | --- |
| Circulating pressure profile | Annular gauge-pressure values at the surface and section boundaries of a vertical well, with hydrostatic and friction contributions distinguished. | A pressure-profile path was identified by name and static call edges only; the vendor profile's definition and values remain unknown. |
| Equivalent circulating density | One bottomhole ECD derived from the OpenOil annular-pressure estimate. | An ECD service was identified; equivalence of its ECD definition, datum, and numerical result is **not established**. |
| Drillstring and annular friction | Separate loss magnitudes and regime indicators for each constant-geometry section. | No vendor friction law or section interpretation was recovered. |
| Other named analyses | **Not covered:** bit optimization, cuttings, flow-rate analysis, surge/swab. | Names observed in the inspected calculation assembly are not evidence of a reproduced capability. |

## Engineering system and input domain

For each ordered section *i*, specify vertical length `Lᵢ`, pipe inner diameter `Dₚ,ᵢ`, pipe outer diameter `Dₒ,ᵢ`, and hole inner diameter `Dₕ,ᵢ`, all in **m**. One positive volumetric flow `Q` (**m³/s**), fluid density `ρ` (**kg/m³**) and dynamic viscosity `μ` (**Pa·s**) apply throughout. Fluid is single-phase, Newtonian, incompressible, at constant properties; the well is vertical and the pipe is concentric. Each section's length is its vertical-depth increment. The model presumes steady, fully developed passage flow. Surface annular **gauge** pressure is defined as zero; no surface backpressure is supplied.

All quantities must be finite and positive, with at least one section and `0 < Dₚ < Dₒ < Dₕ`. The additional `Dₒ/Dₕ ≤ 0.8` restriction avoids thin-gap numerical cancellation; it does **not** certify accuracy for the remaining annular geometries. Static/no-flow cases (`Q = 0`) are outside this calculation.

## Calculation decision

For passage area `A` and hydraulic diameter `Dhyd`, compute mean velocity `v = Q/A`, Reynolds number `Re = ρ v Dhyd/μ`, and a **Darcy** friction factor `f` (not Fanning). The pipe uses `Aₚ = πDₚ²/4` and `Dhyd,ₚ = Dₚ`; the annulus uses `Aₐ = π(Dₕ² − Dₒ²)/4` and `Dhyd,ₐ = Dₕ − Dₒ`. Friction losses below are positive pressure **magnitudes**, in Pa, for section length `L`.

| Passage and regime | Engineering expression and interpretation |
| --- | --- |
| Circular pipe, laminar `Re < 2300` | `f = 64/Re`; `Δpₚ = f (L/Dₚ) ρvₚ²/2 = 128 μLQ/(πDₚ⁴)` (fully developed Newtonian pipe flow). |
| Concentric annulus, laminar `Re < 2300` | Define `K = Dₕ⁴ − Dₒ⁴ − (Dₕ² − Dₒ²)²/ln(Dₕ/Dₒ)` in m⁴. Then `Δpₐ = 128 μLQ/(πK)` for fully developed Newtonian flow in this concentric geometry. The displayed effective Darcy factor is *back-calculated* as `fₐ = 2 Δpₐ Dhyd,ₐ/(ρvₐ² L)`; it is not `64/Re`. |
| Either passage, smooth-wall turbulent `4000 ≤ Re ≤ 100000` | `f = 0.3164/Re^0.25`; `Δp = f (L/Dhyd) ρv²/2`. In the annulus, substituting the hydraulic diameter into this smooth-pipe Blasius expression is an **approximation**, not an exact annular correlation. |
| Either passage, `2300 ≤ Re < 4000` or `Re > 100000` | Reject the *entire case* rather than interpolate or extrapolate. All passages in all sections must satisfy a supported regime. These cutoffs are model rules, **not** universal annular transition thresholds. |

With `H = ΣLᵢ` and `g = 9.80665 m/s²`, the outputs are:

- Pipe friction total: `Δpₚ,total = ΣΔpₚ,ᵢ` (**Pa**). This is **not standpipe pressure**: no bit/nozzle, surface, connection, or acceleration losses are added.
- Annular friction total: `Δpₐ,total = ΣΔpₐ,ᵢ` (**Pa**).
- Hydrostatic bottomhole pressure: `pₕ = ρgH` (**Pa**).
- Annular bottomhole gauge pressure: `pₐ,bh = ρgH + Δpₐ,total` (**Pa**), given the zero-gauge surface boundary.
- Bottomhole ECD: `ρECD = pₐ,bh/(gH) = ρ + Δpₐ,total/(gH)` (**kg/m³**). ECD is an equivalent density for this **bottomhole pressure and datum**, not a measured fluid density or a pore/fracture-pressure safety margin.

The displayed annular profile connects section-boundary points: at accumulated depth `zⱼ = Σᵢ≤ⱼ Lᵢ`, hydrostatic `pₕ(zⱼ) = ρg zⱼ` and circulating `pₐ(zⱼ) = ρg zⱼ + Σᵢ≤ⱼ Δpₐ,ᵢ`. The chart uses boundary values derived from the same returned totals; its connecting lines do not add a separately validated downhole model.

## Worked study case — not a WellPlan benchmark

One 100 m vertical section: `Dₚ = 0.08 m`, `Dₒ = 0.10 m`, `Dₕ = 0.20 m`; `ρ = 1000 kg/m³`, `μ = 0.1 Pa·s`, `Q = 0.001 m³/s`. Both passages classify as laminar (`Reₚ ≈ 159.15`, `Reₐ ≈ 42.44`). OpenOil produces:

| Quantity | Model result (rounded for display) | Engineering reading |
| --- | ---: | --- |
| Pipe mean velocity / friction | 0.19894 m/s / 9,947.18 Pa | Drillstring passage loss only; do not treat as pump or standpipe pressure. |
| Annular mean velocity / friction | 0.04244 m/s / 2,021.27 Pa | Circulating friction added to the bottomhole annular gauge pressure. |
| Hydrostatic / bottomhole annular pressure | 980,665 Pa / 982,686.27 Pa | Zero surface annular gauge datum; bottomhole value includes annular friction, **not** pipe friction. |
| Mud density / bottomhole ECD | 1000 / 1002.06 kg/m³ | About 2.06 kg/m³ above the entered density for this idealized circulation. |

These are reproducible outputs of the **OpenOil equations above**, not WellPlan measurements or field observations. More digits from floating-point calculation would not imply greater engineering accuracy.

## Appropriate studies and non-decisions

Use a saved, identified study case to compare **within this model** how `Q`, `ρ`, `μ`, section length, and concentric diameters change pipe/annular friction and ECD. Inspect each section's contribution and whether it falls in a supported regime; distinguish static density from circulating equivalent density. Loading a historical result preserves its original snapshot: a case with unknown model provenance stays **unknown**, not silently assigned the current model or recalculated.

**Do not use this slice** to set mud weight, select pumps/nozzles, predict standpipe pressure, assert a pore/fracture window, quantify kick/loss risk, or certify a casing/formation pressure limit. It excludes non-Newtonian mud rheology, eccentricity, roughness, inclination, rotation, cuttings loading, bit/surface losses, temperature, compressibility, transient flow, swab/surge, and real-time conditions. Neither software tests nor this example validate field accuracy.

## Evidence needed before any comparison claim

A WellPlan comparison would require **separately authorized** controlled runs: exact solver/product version and configuration, fluid/rheology definition, well and string geometry, pressure datum, units, circulating conditions, input/output pairs, and an engineering tolerance agreed *before* comparing results. Test laminar and turbulent cases, regime boundaries, multiple sections, and explicitly excluded physics; record mismatches without retuning this simplified model by inference from static names. Until such evidence exists, the only established overlap is the **topic** of drilling-hydraulics pressure/ECD analysis, not formula or numerical parity.
