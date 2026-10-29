# WP-1.2 rheology coverage

This note compares the normative rheology scope in [`docs/gaps.md` (WP-1.2)](../../docs/gaps.md) with the current OpenOil implementations. It is an implementation-coverage snapshot, not a replacement for the normative roadmap, a solver specification, or engineering validation.

## Model-family coverage

| WP-1.2 model family | Current OpenOil implementation | Coverage |
|---|---|---|
| Newtonian | Simplified steady single-phase hydraulics plus a standalone Fann-derived viscosity study with explicit conversion and input limits. | Partial: the independent viscometer study does not establish a complete hydraulic rheology workflow. |
| Bingham plastic | Standalone study transforms Fann readings to SI shear-rate/stress points and derives plastic viscosity and yield point from the 300/600 RPM pair. Additional readings are observations, not fit inputs. | Partial: the two-point derivation is implemented; gel strengths and hydraulic coupling are not. |
| Power Law | Standalone study derives flow-behavior index and consistency from positive 300/600 RPM Fann readings. Additional readings do not participate in a fit. | Partial: the two-point derivation and modeled SI curve are implemented; broader fitting workflows are not. |
| Herschel–Bulkley | Standalone SI evaluator and separately defined conventional fit of Fann readings with diagnostics. The fit is OpenOil-defined, not a recovered vendor algorithm. | Partial: independent fitting is implemented; vendor parity, generalized fitting and hydraulic/gel coupling are not. |
| Generalized Herschel–Bulkley | Standalone SI evaluator computes a curve from supplied generalized-model parameters and shear rates. It does not fit Fann readings. | Partial: parameter evaluation is implemented; fitting and hydraulic/foam workflows are not. |

The two parameter-evaluation studies return model identity and explicit SI quantities. Their curve outputs do not imply that parameters have been derived from measured viscometer data.

## Associated WP-1.2 workflows

| Required capability named by WP-1.2 | Current support | Coverage |
|---|---|---|
| Derive rheology quantities from viscometer data | Bingham provides the 300/600 RPM PV/YP derivation; Power Law provides a two-point 300/600 RPM parameter derivation; Newtonian derives viscosity; conventional HB fits multiple Fann readings with an independent objective. | Partial: generalized HB fitting and vendor-defined fitting remain unsupported. |
| Plastic viscosity | Derived by the Bingham study from the 300/600 RPM pair. | Partial. |
| Yield point | Derived by the Bingham study from the 300/600 RPM pair. | Partial. |
| Gel strengths | A bounded zero-second gel study converts a 3 rpm Fann dial reading to SI stress. Other gel times are not implemented. | Partial: zero-second only. |
| Shear rate and shear stress | Converted from readings in the Bingham and Power Law studies; HB and generalized HB produce modeled stress at explicitly supplied shear rates. | Partial: measured-data conversions and parameterized curves exist, but not as one complete derivation workflow across the model family. |
| Pressure to break gel | A bounded string-interior calculation uses the documented `4 τ_g Σ(L_c/d_i)` relation with per-component pressure. No annular or full hydraulic analysis is implemented. | Partial: string interior only. |
| Explicit selected model and units in results | The rheology studies identify their model and label returned quantities with units; the hydraulic model separately declares its Newtonian scope. | Present in the bounded implemented results; this does not close the other WP-1.2 workflows. |

## Coverage conclusion and boundaries

All five named model families have some representation in OpenOil, but **WP-1.2 is not complete**. Newtonian Fann viscosity and a conventional HB fit now have standalone studies; the latter uses a documented OpenOil-defined fitting objective, not the unspecified WellPlan algorithm. Bingham and Power Law use bounded two-point derivations, and generalized HB remains a parameter evaluator without a Fann fit. Zero-second gel derivation and string-interior break-gel pressure are implemented, but timed gels, annular break-gel pressure and complete hydraulic analysis are not.

The installed help names 0-second, 10-second, 10-minute and 30-minute gel fields, but does not define a timed Fann acquisition/conversion protocol. Its break-gel equation is `4 τ_g Σ(L_c/d_i)` for drillstring inside diameter only. Read-only managed metadata/CIL inspection of installed `DSWE.Hydraulics.DomainModel.dll` (SHA-256 `48669184323fc5f0950fcfcec0e7a4e20aced9cdb5a7b3edffcbbb6c2b9c1822`, REA evidence `ev_27657e363947b0da7e7218eaf6dfc5da06d97316ce182acc8c45cf811d536923`) found `BreakGelInputs..ctor` initializes gel strengths and conditionally appends a 3-rpm Fann reading converted by `180/π`; input assembly does not establish timed measurement or annular calculation semantics. The inspected calculation assembly acts as a proxy; the underlying solver was not inspected or executed. Obtaining authoritative timed inputs and annular geometry/equation, units, applicability and outputs remains required before implementation. No numerical parity or field suitability is claimed.

## Evidence in this repository

- Normative scope: [`docs/gaps.md`, WP-1.2](../../docs/gaps.md).
- Documented capability summary: [`docs/reference/drilling-capabilities.md`](../../docs/reference/drilling-capabilities.md#1-hydraulics-rheology-and-hole-cleaning).
- Current source: `backend/src/openoil/domain/bingham_rheology.py`, `power_law_rheology.py`, `newtonian_rheology.py`, `herschel_bulkley_rheology.py`, `herschel_bulkley_fit.py`, and `generalized_hb_rheology.py`; `backend/src/openoil/domain/physics.py` and `backend/src/openoil/application/model_identity.py` for the bounded Newtonian hydraulic model.
- Study boundaries: `research/rheology/boundary.md`, `power-law-boundary.md`, `newtonian-boundary.md`, `herschel-bulkley-boundary.md`, `herschel-bulkley-fit-boundary.md`, `generalized-hb-boundary.md`, and `gel-break-boundary.md`.
