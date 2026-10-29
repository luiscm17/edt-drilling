# WP-1.2 rheology coverage

This note compares the normative rheology scope in [`docs/gaps.md` (WP-1.2)](../../docs/gaps.md) with the current OpenOil implementations. It is an implementation-coverage snapshot, not a replacement for the normative roadmap, a solver specification, or engineering validation.

## Model-family coverage

| WP-1.2 model family | Current OpenOil implementation | Coverage |
|---|---|---|
| Newtonian | Used by the simplified, steady, single-phase hydraulic model. There is no separate Newtonian rheology study deriving viscosity from viscometer data. | Partial: the model is present within a bounded hydraulic calculation, not as the full rheology workflow. |
| Bingham plastic | Standalone study transforms Fann readings to SI shear-rate/stress points and derives plastic viscosity and yield point from the 300/600 RPM pair. Additional readings are observations, not fit inputs. | Partial: the two-point derivation is implemented; gel strengths and hydraulic coupling are not. |
| Power Law | Standalone study derives flow-behavior index and consistency from positive 300/600 RPM Fann readings. Additional readings do not participate in a fit. | Partial: the two-point derivation and modeled SI curve are implemented; broader fitting workflows are not. |
| Herschel–Bulkley | Standalone SI evaluator computes a curve from supplied yield stress, consistency index, flow index, and shear rates. It does not fit Fann readings. | Partial: parameter evaluation is implemented; viscometer fitting and gel workflows are not. |
| Generalized Herschel–Bulkley | Standalone SI evaluator computes a curve from supplied generalized-model parameters and shear rates. It does not fit Fann readings. | Partial: parameter evaluation is implemented; fitting and hydraulic/foam workflows are not. |

The two parameter-evaluation studies return model identity and explicit SI quantities. Their curve outputs do not imply that parameters have been derived from measured viscometer data.

## Associated WP-1.2 workflows

| Required capability named by WP-1.2 | Current support | Coverage |
|---|---|---|
| Derive rheology quantities from viscometer data | Bingham provides the 300/600 RPM PV/YP derivation; Power Law provides a two-point 300/600 RPM parameter derivation. | Partial. No general multi-reading fitting workflow is established for the HB models. |
| Plastic viscosity | Derived by the Bingham study from the 300/600 RPM pair. | Partial. |
| Yield point | Derived by the Bingham study from the 300/600 RPM pair. | Partial. |
| Gel strengths | A bounded zero-second gel study converts a 3 rpm Fann dial reading to SI stress. Other gel times are not implemented. | Partial: zero-second only. |
| Shear rate and shear stress | Converted from readings in the Bingham and Power Law studies; HB and generalized HB produce modeled stress at explicitly supplied shear rates. | Partial: measured-data conversions and parameterized curves exist, but not as one complete derivation workflow across the model family. |
| Pressure to break gel | A bounded string-interior calculation uses the documented `4 τ_g Σ(L_c/d_i)` relation with per-component pressure. No annular or full hydraulic analysis is implemented. | Partial: string interior only. |
| Explicit selected model and units in results | The rheology studies identify their model and label returned quantities with units; the hydraulic model separately declares its Newtonian scope. | Present in the bounded implemented results; this does not close the other WP-1.2 workflows. |

## Coverage conclusion and boundaries

All five named model families have some representation in OpenOil, but **WP-1.2 is not complete**. The current implementation set is several bounded studies, not an end-to-end rheology package: Newtonian behavior is confined to simplified hydraulics; Bingham and Power Law derive parameters from two Fann points; and conventional/generalized Herschel–Bulkley evaluate supplied parameters without fitting readings. Zero-second gel derivation and string-interior break-gel pressure have bounded implementations, but timed gels, annular break-gel pressure and the complete hydraulic analysis remain unimplemented.

The conventional Herschel–Bulkley help says that three or more Fann readings use a nonlinear fit but does not specify its algorithm. Static metadata and model names do not resolve that gap. Do not claim or implement a particular fitting objective, numerical parity, or generalized-model fitting behavior without authoritative engineering semantics. The bounded gel and break-gel study follows the published zero-second and string-interior equations; other gel times and the full hydraulic break-gel analysis still require their equations, input semantics, units, applicability domain, and output meaning to be established before implementation.

## Evidence in this repository

- Normative scope: [`docs/gaps.md`, WP-1.2](../../docs/gaps.md).
- Documented capability summary: [`docs/reference/drilling-capabilities.md`](../../docs/reference/drilling-capabilities.md#1-hydraulics-rheology-and-hole-cleaning).
- Current source: `backend/src/openoil/domain/bingham_rheology.py`, `power_law_rheology.py`, `herschel_bulkley_rheology.py`, and `generalized_hb_rheology.py`; `backend/src/openoil/domain/physics.py` and `backend/src/openoil/application/model_identity.py` for the bounded Newtonian hydraulic model.
- Study boundaries: `research/rheology/boundary.md`, `power-law-boundary.md`, `herschel-bulkley-boundary.md`, `generalized-hb-boundary.md`, and `gel-break-boundary.md`.
