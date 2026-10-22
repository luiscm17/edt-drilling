# Hydraulics capability design: bit/nozzle pressure loss

## 1. Purpose and scope

This document specifies the technical architecture and implementation requirements for the bit/nozzle pressure-loss capability defined by P6 in [`docs/product/prd.md`](../product/prd.md). The product requirements govern user outcomes and safety; the technical requirements in [`trd.md`](trd.md) govern shared architectural constraints. This document defines the capability-specific technical contract.

The capability extends a supported hydraulic calculation with an explicitly requested bit/nozzle pressure-loss contribution. It provides an independently inspectable contribution and, only when defined by the approved engineering model, an aggregate with an explicit pressure boundary and included components.

The capability does not include surface-equipment losses, a general hydraulic network solver, nozzle erosion or wear prediction, blockage prediction, non-Newtonian flow, compressible/transient/multiphase flow, cuttings transport, thermal effects, or operational authorization. File import/export is outside this capability and requires a separately specified contract.

This capability is for engineering study only. It MUST NOT be represented as suitable for field decisions or safety-critical pressure limits without independent engineering validation.

## 2. Normative language

**MUST** and **MUST NOT** state mandatory requirements. **SHOULD** and **SHOULD NOT** state recommended requirements; any deviation requires an explicit technical rationale and review. **MAY** states an option.

## 3. Engineering model contract

The implementation MUST use an independently specified physical model. It MUST NOT infer an equation, coefficient, applicability domain, or operating behavior from software structure or undocumented behavior.

Before implementation, the model specification MUST define:

- equations, symbol definitions, dimensions and conversions to and from SI;
- nozzle geometry inputs and how total flow area is established;
- each coefficient's physical meaning, source, valid range and selection policy;
- fluid, flow, geometry and operating assumptions;
- applicable and unsupported conditions, including their validation and error behavior;
- independently justified examples with complete inputs, units, intermediate values, expected results, precision and tolerance; and
- provenance, limitations and engineering approval for each reference used.

Inputs MUST be finite and physically valid. Conditions outside the approved applicability domain MUST be rejected before a result is reported or persisted. Calculations MUST be deterministic, side-effect free and non-mutating. Full-precision values MUST feed any aggregate; display rounding MUST NOT affect calculations or persisted values. Every result value MUST identify its physical quantity and unit, and the result MUST identify its model version and applicability status.

A documented equation, software test or mathematical example alone MUST NOT be represented as field validation. Model changes that alter assumptions, coefficients, applicability or results MUST receive a new model version and independently reviewed evidence.

## 4. Architecture and dependency rules

The system MUST remain a single deployable modular monolith. Engineering calculations belong to a framework-independent domain core. Application use cases coordinate validation, calculations and case lifecycle operations. Inbound transport and outbound persistence are replaceable adapters. Dependencies MUST point inward toward domain contracts.

The bit/nozzle calculation MUST be a deterministic domain operation. The application layer MUST validate the request, invoke the approved model, combine only the contributions defined by that model, and attach model and schema provenance. Transport adapters MUST validate and translate public request/response contracts but MUST NOT contain engineering equations or directly perform persistence. Persistence adapters MUST implement application-defined storage operations but MUST NOT determine engineering applicability or recalculate results on load. A composition boundary wires implementations without altering model behavior.

User-interface code MUST present inputs, invoke the public application interface and render its result; it MUST NOT implement authoritative engineering equations. Tables, summaries and plots MUST derive from the same returned result. A capability MUST NOT depend on another capability's transport or persistence adapter. Shared contracts MUST be limited to concepts genuinely used across capabilities.

Structural decomposition MUST be incremental and justified by cohesive responsibilities or dependency boundaries. It MUST preserve unrelated capability behavior and public contracts; a wholesale restructuring is not a prerequisite for this capability.

## 5. Public behavior and compatibility

The extension MUST be explicitly requested. Requests that do not request the extension MUST preserve their established meaning and results. Adding the extension MUST NOT silently add a pressure contribution to any request contract or change the defined meaning of an aggregate.

A result that includes the extension MUST return the bit/nozzle contribution separately, with quantity, unit, model version and applicability/status. Any aggregate MUST identify its included pressure contributions and physical boundary. It MUST NOT be labelled standpipe pressure unless the modeled system includes the complete path to the standpipe measurement boundary.

Request and result contracts MUST be explicitly versioned when their meaning or shape is incompatible. Omitted inputs MUST NOT be used to infer a coefficient or model version. Errors MUST distinguish malformed transport input, unsupported engineering conditions, missing resources and infrastructure failures. A failure MUST NOT be presented as a successful result or expose unnecessary submitted values.

## 6. Persistence and provenance

A saved calculation MUST be an immutable association of normalized inputs, unrounded results, units, model identity/version, input/result schema versions, assumptions or coefficient selection, and creation time. Validation and calculation MUST precede one atomic persistence operation. A rejected save MUST create neither a partial record nor a consumed identifier.

Loading a saved calculation MUST return its stored snapshot without implicit recalculation. Any recalculation MUST create a separately identifiable result linked to its source calculation and record the model version used; it MUST NOT overwrite the original result. Missing provenance MUST remain unknown and MUST NOT be inferred from default model settings.

Any schema migration MUST have a separate reviewed design defining transaction and rollback behavior, backup and restoration, compatibility and read policy for prior snapshots, idempotence, and recovery verification before the migration is implemented. A capability requirement MUST NOT be treated as authorization to migrate data.

## 7. User-interface behavior

The user interface MUST identify supported inputs and units, the active model's applicability and limitations, and each result contribution. Editing an input MUST invalidate any result that no longer corresponds to the visible inputs. A failed or unsupported calculation MUST leave no stale result presented as current. Inputs and results MUST be keyboard accessible; information conveyed by plots MUST also be available in a non-graphical form.

## 8. Verification requirements

Acceptance evidence MUST cover:

- every approved numerical example, including dimensional and unit-conversion checks;
- applicability limits, limiting behavior and unsupported conditions;
- finite outputs, determinism and non-mutation of inputs;
- public request/response behavior, including unchanged behavior for requests that omit the extension;
- calculate-without-save, atomic save, rejection without partial data or consumed identifiers, and snapshot load without recalculation;
- provenance and model-version visibility; and
- user interaction, accessibility, stale-result invalidation, error presentation and consistency between tables, summaries and plots.

Numerical expectations MUST be independently justified and carry declared precision and tolerance. Software verification establishes conformance to the specified implementation contract; engineering validation establishes the suitability of the model for its intended domain. Those conclusions MUST be reported separately.
