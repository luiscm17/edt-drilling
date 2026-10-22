# Hydraulics capability design: bit/nozzle pressure loss

**Status:** Normative technical design for the P6 product capability in [`docs/product/prd.md`](../product/prd.md). It defines implementation boundaries and verification gates, not a record of the work that produced it. The product requirements govern user outcomes and safety; [`trd.md`](trd.md) governs cross-capability architecture. This document specializes those rules for P6.

## 1. Scope and safety boundary

Add an explicitly requested bit/nozzle pressure-loss contribution to the existing hydraulics calculation. Preserve a separately inspectable bit-loss result and define the physical location and exact components of any aggregate. The aggregate MUST NOT be called standpipe pressure unless surface equipment and every intervening pressure loss are modeled.

This capability does not add surface-equipment losses, a full network solver, erosion/wear or blockage prediction, non-Newtonian flow, compressible/transient/multiphase flow, cuttings transport, thermal effects, operational authorization, or general WellPlan parity. LAS, vendor-native files, spreadsheets and other import adapters are also out of scope. LAS is an industry exchange format; its presence does not establish compatibility with a proprietary Landmark format.

The capability is for engineering study, not field decisions or safety-critical pressure limits. Software tests establish implementation consistency, not field accuracy.

## 2. Engineering-model contract

No equation or coefficient is selected by this architecture document. Before implementation, a drilling engineer MUST approve a capability-specific model contract that states:

- equations, symbols, dimensions and conversions to/from SI;
- whether inputs are total flow area or nozzle count and diameter, including how total area is derived;
- coefficient meaning, source, range, and whether fixed, user-supplied or correlated;
- assumptions and applicability limits for fluid, flow, nozzle geometry and operating conditions;
- supported and rejected conditions, with explicit error behavior;
- at least one independently calculated, provenance-complete example with intermediate values, precision and justified tolerance;
- unit, sign, area-scaling and flow-sensitivity checks; and
- reviewer, reference edition/version and evidence limitations.

The ideal-orifice relation `Δp = ρv²/2`, with `v = Q/A`, is dimensional background, not an approved operational model. It does not establish discharge coefficient, physical applicability or vendor-runtime behavior. A formula documented in WellPlan help is documentation evidence only; it MUST NOT be described as a measured output or runtime-validated model. Conflicting formula conventions or assumptions must be resolved in the reviewed model contract rather than hidden in conversion code.

Inputs MUST be finite and physically valid. Unsupported conditions MUST be rejected before presenting or storing a result. Calculations MUST be deterministic, pure and non-mutating. Full-precision values feed aggregates; display rounding MUST NOT feed calculations or persistence. Every result value carries a quantity and unit, model identity/version, and applicability/status.

## 3. Modular-monolith boundaries

OpenOil remains one deployable hexagonal modular monolith. Dependencies point toward the engineering core:

```text
React study UI → HTTP/API adapter → hydraulics application use case → hydraulics domain
                                              │                          │
                                              └── case-store port         └── pure bit-loss model
                                                       ▲
                                                       └── SQLite adapter
```

- **Hydraulics domain:** owns SI-oriented contracts, applicability, validation and pure calculations. It MUST NOT import HTTP, UI, SQLite, filesystem or framework APIs.
- **Application:** coordinates calculation and case use cases, applies validation before writes, combines only explicitly defined contributions and attaches model/schema provenance. Ports express application needs, not SQL operations.
- **HTTP/API adapter:** validates transport DTOs and versions, invokes use cases, and translates documented error categories. It MUST NOT own equations or write storage directly.
- **SQLite adapter:** implements persistence ports, serialization and separately authorized migrations. It MUST NOT determine engineering validity or recalculate on load.
- **Frontend:** submits user inputs and renders the API result. It MUST NOT implement authoritative engineering equations. Tables, summaries and plots use the same returned result.
- **Composition root:** wires adapters and use cases; deployment choices MUST NOT alter model behavior.

The existing backend package is `backend/src/wellplan_hydraulics/`, with current physics, application, API, ports, storage, model identity, nozzle-velocity and torque/drag modules. The first change SHOULD add the bit-loss calculation at the existing domain seam and integrate through existing application/API/port boundaries. New package boundaries or file moves are justified only by a concrete cohesion or dependency problem and MUST be incremental, with existing behavior pinned by regression checks. Do not undertake a wholesale directory refactor first. A capability MUST NOT depend on another capability's adapter; shared code is limited to genuinely cross-capability contracts.

The current frontend composes navigation, hydraulics and saved cases in `frontend/src/App.tsx`; it has study/result/type boundaries in `Results.tsx`, `types.ts`, `NozzleVelocityStudy.tsx` and `TorqueDragStudy.tsx`. Add the P6 input and results within the hydraulics workflow. Extract request/DTO or study components only as needed for this capability. Preserve navigation, accessibility, input invalidation, saved-case interactions and independent temporary studies. Avoid a broad UI rewrite as a prerequisite.

WellPlan's plugin and binary topology MUST NOT be copied as OpenOil's module structure. REA static inspection found the orchestration assembly has managed metadata and the hydraulics assembly crosses a managed/native boundary; this supports separating orchestration from calculation, but does not reveal OpenOil's domain model or justify mirroring vendor components.

## 4. Public contract and compatibility

P6 is explicitly opt-in. Existing request versions and payloads MUST remain valid and retain their current observable results and save/load behavior. An old request MUST NOT acquire a hidden bit loss or changed aggregate. The API returns the bit-loss contribution separately, along with units, model identity/version, applicability/status and any precisely defined aggregate.

Request and result versions MUST be explicit whenever a contract meaning or shape is incompatible. Omitted optional input MUST NOT be used to guess a model version or coefficient. Errors retain documented categories (transport validation, unsupported engineering input, missing case, infrastructure failure); infrastructure failure MUST NOT appear as input rejection. Responses disclose no unnecessary submitted values. Rejections MUST NOT produce partial results, persisted records or consumed identifiers.

## 5. Persistence boundary — design only, no migration

SQLite remains the local persistence adapter. A saved calculation is an immutable input/result snapshot associated with normalized input, unrounded output, units, model identity/version, input/result schema versions, assumptions or coefficient selection, and creation time. Save validation and calculation precede one atomic write. Loading returns the stored snapshot without implicit recalculation. A future recalculation creates a separately identifiable result linked to the source case and records its model version; it does not overwrite historical output.

The current `CaseStore` stores `input_json`, `result_json` and nullable `provenance_json` in append-only `cases` rows. Missing provenance on older snapshots remains unknown and MUST NOT be inferred from current code. Persisted JSON rejects nonfinite values.

This design authorizes no migration and no database-file changes. Any later schema change requires a separate migration design specifying transaction/rollback, backup/restore, idempotent startup, old-snapshot read policy, recovery and compatibility fixtures before implementation. A database migration is not implied by the P6 feature.

## 6. Verification and acceptance gates

Before implementation, the model contract in Section 2 is approved and the public request/response and backward-compatibility examples are specified. Implementation proceeds domain-first, then application/API, persistence adapter only if required, and UI.

Required evidence includes:

- independently justified numerical examples and dimensional/unit checks;
- model applicability, limiting and unsupported-input cases;
- determinism, finite results and input non-mutation;
- public API tests for legacy requests and P6 opt-in results/errors;
- proof calculate performs no write, successful save is atomic, and rejection changes neither stored records nor identifiers;
- snapshot load without recalculation and preservation of legacy unknown provenance;
- UI interaction/accessibility checks for edits, stale-result invalidation, errors, units and result contributions; and
- applicable frontend/backend suites and real browser-to-API flow.

No acceptance claim substitutes passing tests for engineering validation. If engineering review or required evidence is unavailable, the capability is not released and the gap is reported explicitly.

## 7. Design evidence and limits

REA inspected the following installed artifacts statically; it did not load or execute them:

| Artifact | Identity | Observation | Limitation |
| --- | --- | --- | --- |
| `EDK.WebService.Wellplan.dll` | SHA-256 `9f058b5259c79049bea68be527ac2c8f2ad6c16248622b0a44a4ca286c41974f` | Complete managed metadata; 122 types, 701 methods, 6,056 static call edges and 142 user-string literals. | Static metadata/call edges do not establish runtime behavior or the complete application/plugin contract. |
| `EDK.Hydraulics.dll` | SHA-256 `bb81bf7f4543fa02645332ce750078f5cc85eb44a8bacbe1213ce2177c3a0ae3` | Complete metadata; 482 types, 550 methods and a non-IL/native entry boundary. | Native equation bodies and numerical behavior were not recovered. |

REA Evidence IDs: orchestration artifact `ev_dbaaa3701d677abea0925851fc91ada8879b62283874746e58f2f78e29b6f8fa`, managed members `ev_e3fc7c6e1f25ee6feae581ef82e80f9a494cbbf7b8064ab453b58728f0761717`; hydraulics artifact `ev_b0b91f3d1899a4f687be8a9f26e2b162cbf6800112baafe41d5ee871decf67ed`, managed members `ev_ab0bd41249ce678e0a7f957e5e6bcf56a6208c70bd62e7b85b45ba973e349547`, native boundary `ev_9d2fa77812c8ef7a9529159ea2fe23bd2896d4fbb63a88ef8a96d212b1d974b5`. The installed WellPlan help topic is `C:\Landmark\EDT\WellPlan\webhelp\Topics\c_bit_press_loss_calc.html`; it documents an equation but does not provide a runtime oracle. Static REA and help evidence inform architectural boundaries only; they do not authorize copying vendor code, schemas, identifiers or data.
