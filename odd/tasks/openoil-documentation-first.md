# OpenOil engineering workbench — normative architecture and delivery requirements

**Status:** Normative design for the first incremental capability. This document governs future implementation; it is not an implementation record or a WellPlan-parity claim.

## 1. Purpose and scope

OpenOil is an independent engineering workbench informed by public engineering principles and observations of WellPlan's installed documentation and architecture. It shall deliver bounded capabilities, not replicate the WellPlan suite. Its first product remains a study tool, not an operational authority.

The first candidate vertical slice is **bit/nozzle pressure loss integrated into the existing hydraulic calculation**, with a separate auditable bit-loss contribution and an explicitly reported total. Before implementation, a drilling engineer shall approve the selected model, its applicability, coefficient treatment, supported inputs and verification examples. If that review rejects or narrows the candidate, this specification shall be revised before code changes.

This is documentation and design work only. It authorizes no application-code edits, database migration, dependency installation, dataset import, vendor execution, case entry, or delivery to a remote. A later implementation requires explicit approval of this specification and its engineering model contract.

## 2. Normative language and governing documents

**MUST**, **MUST NOT**, **SHOULD**, and **MAY** express requirements. MUST/MUST NOT are release gates; SHOULD deviations require a documented rationale and review. Capability-specific equations, tolerances and applicability limits belong in a reviewed capability specification, not in generic architecture rules.

`docs/product/prd.md` defines user outcomes and the safety boundary. `docs/architecture/trd.md` governs hexagonal boundaries, SI units, provenance, saved-case semantics and verification. This document narrows those requirements for the first hydraulics extension. In a conflict, the PRD governs product scope and safety; the TRD governs shared technical constraints; this document governs this capability's design.

## 3. Product and engineering contract

### 3.1 User outcome

A user shall be able to calculate the existing supported hydraulic case with an explicitly enabled bit/nozzle contribution, inspect the bit loss separately from pipe friction, annular friction and hydrostatic pressure, and trace the reported combined pressure to the same calculation inputs and model provenance. Existing calculations that do not request the extension shall retain their established request, response and saved-snapshot behavior.

The result MUST distinguish:

- bit/nozzle pressure loss;
- pipe friction and annular friction;
- hydrostatic pressure;
- any aggregate pressure quantity, with an explicit definition of included contributions and boundary location.

The aggregate MUST NOT be labelled standpipe pressure unless surface equipment and every intervening loss are actually modeled. An absent, disabled or unsupported contribution MUST NOT be represented as zero without an explicit status that makes that meaning clear.

### 3.2 Engineering model gate

The implementation MUST use an independently specified physical model, not a guessed reconstruction of vendor internals. The domain specification MUST state, before implementation:

1. equation(s), symbol definitions, dimensions and unit conversions;
2. whether total flow area is supplied or derived from nozzle count and diameter, including dimensional checks;
3. the meaning, source and permitted range of every discharge/coefficient value, and whether it is fixed, user supplied, or correlated;
4. fluid, flow, geometry and operating assumptions, including steady state, compressibility, erosion/rounding, blockage and discharge behavior where applicable;
5. applicability domain, explicit unsupported cases and rejection behavior;
6. an independently calculated example with source, full inputs, units, expected intermediate quantities, output precision and tolerance;
7. sensitivity or limiting checks sufficient to detect wrong unit conversion, area scaling, sign or quadratic-flow behavior;
8. engineering reviewer and provenance of each reference.

The generic ideal-orifice relation `Δp = ρ v² / 2`, with `v = Q/A`, is dimensional background only; it is not by itself an approved operational model or a substitute for a justified discharge coefficient and applicability statement. If the shipped help or independent references differ in convention, coefficient, unit system or boundary definition, the capability specification MUST expose and resolve that difference rather than silently selecting one. The vendor equation MUST NOT be claimed as runtime-validated merely because it is documented.

Inputs MUST be finite and positive where physics requires positivity. Unsupported physical regimes MUST be rejected before a result is created or persisted. Calculations MUST be deterministic, side-effect free and non-mutating. Full precision feeds downstream sums; display rounding never feeds calculation or storage. Every returned number MUST carry quantity and unit. Software tests establish implementation consistency, not field accuracy.

### 3.3 Explicit non-goals

The first slice does not add a full surface-to-bit hydraulic network, surface equipment loss, drillstring/nozzle erosion or wear modeling, non-Newtonian flow, compressible/transient/multiphase flow, cuttings transport, thermal effects, surge/swab, live data, field authorization, or blanket WellPlan equivalence. Any such capability requires its own reviewed model contract and acceptance criteria.

LAS, vendor-native formats, spreadsheets and other import adapters are not part of this slice. LAS is an industry exchange format, not evidence of support for any Landmark proprietary format. Parser selection and dependencies require a later, sample-driven and license-aware design.

## 4. Target architecture

OpenOil MUST remain a single deployable hexagonal modular monolith. Engineering concepts form the domain core; application use cases coordinate them; inbound HTTP and outbound persistence are adapters. Dependencies point inward. WellPlan's observed plugin/binary boundaries are evidence about that product only, not a module map to copy.

```text
React study UI
    │ versioned HTTP DTOs
    ▼
HTTP/API adapter ──► hydraulic application use case ──► hydraulic domain model
                              │                               │
                              └── case-store port              └── pure bit-loss function
                                      ▲
                                      │
                              SQLite adapter
```

### 4.1 Backend ownership

- **Domain:** typed SI quantities/contracts, hydraulic applicability and deterministic calculations. It MUST NOT import FastAPI, SQLite, filesystem or UI modules.
- **Application:** calculate and case lifecycle use cases; validate before writes; combine only explicitly defined contributions; attach model/schema provenance. It owns ports expressed in use-case terms.
- **Inbound adapter:** request parsing, API-version compatibility, error translation and response serialization. It MUST NOT contain engineering equations or write storage directly.
- **Persistence adapter:** SQLite implementation of case-store operations, serialization and migrations. It MUST NOT decide model applicability or calculate results.
- **Composition root:** selects adapters and wires the use cases. It MUST NOT change engineering behavior based on deployment details.

The current backend has `physics.py`, `application.py`, `api.py`, `ports.py`, `storage.py`, `model_identity.py`, `nozzle_velocity.py` and `torque_drag.py` under `backend/src/wellplan_hydraulics/`. Introduce a hydraulics capability boundary incrementally: add the bit-loss domain model alongside existing physics; route it through the existing application/use-case seam; preserve the existing API seam; keep SQLite behind the existing port. Move files or rename packages only when a concrete boundary requires it and public behavior can be preserved with regression evidence. Do not perform a wholesale directory rewrite first.

A capability MUST NOT import another capability's adapter. Shared modules are limited to stable, genuinely cross-capability concepts such as units, error categories or provenance contracts. Do not create a class, service, port or package solely to mirror vendor naming or to satisfy a diagram.

### 4.2 Frontend ownership

The UI MUST remain a thin client of the public API and MUST NOT implement authoritative engineering formulas. The hydraulic study owns editing and submitting explicit bit/nozzle inputs; result components render the server's single result and preserve the distinction between bit loss and other contributions. A visualization MUST derive from the same response as its table and summary.

The current `frontend/src/App.tsx` composes navigation, hydraulic case editing, API requests, status and saved cases; `Results.tsx`, `types.ts`, `NozzleVelocityStudy.tsx` and `TorqueDragStudy.tsx` establish existing study boundaries. Extract or reorganize only the request/DTO and hydraulics study/result responsibilities needed for this slice. Keep navigation, accessibility, input invalidation, save/load snapshot behavior and the independent temporary-study workflows unchanged. Avoid a broad UI architecture refactor as a prerequisite.

### 4.3 Public contract and compatibility

Existing API versions and requests MUST remain valid and retain their observable semantics. The bit-loss extension MUST be opt-in through a clearly versioned and validated request contract; an old request MUST NOT acquire a new hidden loss, changed total, or changed saved result. The API MUST return a distinct bit-loss value, model identity/version, unit, applicability/status and a precisely defined aggregate when requested. Errors MUST preserve documented categories and disclose no unnecessary submitted values.

A new input/result contract version is required when the meaning or shape becomes incompatible; versioning MUST be explicit rather than inferred from omitted fields. Successful and rejected behavior, including exact status/error category and absence of partial writes, is part of compatibility. Existing consumers and snapshots MUST NOT be silently reinterpreted.

## 5. Persistence design — no migration in this work

SQLite remains the initial local adapter. The conceptual persisted record associates normalized input, unrounded result, units, model identifier/version, input and result schema versions, assumptions/coefficient selection, and creation time. The input and result form one immutable calculation snapshot. Loading returns that snapshot without recalculation. Recalculation, if later offered, creates a separately identified result linked to its source case and records the new model/version; it never overwrites the historical result.

Current `CaseStore` uses append-only `cases` rows with `input_json`, `result_json` and nullable `provenance_json`; the adapter performs an additive column migration. Older rows with absent provenance remain **unknown**; no model/version may be inferred from current code. New fields MUST serialize finite values only, and persistence MUST be atomic after validation and calculation. A rejected calculation/save MUST leave stored cases and generated identifiers unchanged.

This document specifies the conceptual data contract, not a migration. Before any storage change, a separate design MUST define migration steps, transaction/rollback behavior, backup and restore, old-row read policy, idempotent startup, compatibility fixtures and recovery verification. This work MUST NOT run migrations or alter database files.

## 6. Evidence, provenance and clean-room boundary

Engineering documentation, independent references, software artifacts and runtime observations are different evidence classes. A documented formula is not a measured output; a static call edge is not a dynamic execution; a test fixture is not field validation. Every model claim and fixture MUST identify its evidence class, source/version/date where available, assumptions, transformations and known limitations. Only appropriately licensed, provenance-complete public datasets may be used; operational datasets MUST NOT be added by default.

REA static inspection of installed artifacts was performed without loading or executing the target code. For the 231,424-byte `EDK.WebService.Wellplan.dll` (SHA-256 `9f058b5259c79049bea68be527ac2c8f2ad6c16248622b0a44a4ca286c41974f`), REA reported complete managed metadata and 122 types, 701 methods, 6,056 static call edges and 142 user-string literals. For `EDK.Hydraulics.dll` (128,512 bytes; SHA-256 `bb81bf7f4543fa02645332ce750078f5cc85eb44a8bacbe1213ce2177c3a0ae3`), REA reported complete metadata, 482 types, 550 methods and a non-IL/native entry boundary (`il_only=false`, `native_entry_point=true`). These observations support a mixed managed/native integration boundary and orchestration separation; they do not disclose the native equation implementation, runtime behavior, deployment plugin contract or full application topology. OpenOil MUST use its own engineering model and contracts and MUST NOT copy vendor code, schemas, proprietary data or identifiers as an implementation shortcut.

Evidence references: REA `ev_dbaaa3701d677abea0925851fc91ada8879b62283874746e58f2f78e29b6f8fa` and `ev_e3fc7c6e1f25ee6feae581ef82e80f9a494cbbf7b8064ab453b58728f0761717` (WellPlan orchestration assembly); `ev_b0b91f3d1899a4f687be8a9f26e2b162cbf6800112baafe41d5ee871decf67ed`, `ev_ab0bd41249ce678e0a7f957e5e6bcf56a6208c70bd62e7b85b45ba973e349547` and `ev_9d2fa77812c8ef7a9529159ea2fe23bd2896d4fbb63a88ef8a96d212b1d974b5` (WellPlan hydraulics assembly). The installed help topics `C:\Landmark\EDT\WellPlan\webhelp\Topics\c_bit_press_loss_calc.html` and `c_ecd_calc.html` document bit-loss and ECD equations. These are documentation observations only; they do not establish runtime use, output, or parity.

## 7. Required implementation sequence and release gates

1. **Approve the model contract.** A drilling engineer reviews the equation, inputs, units, coefficient, applicability, unsupported cases, examples and tolerances. No implementation begins while any item is unresolved.
2. **Specify a public acceptance contract.** Define request/response examples, legacy behavior, error semantics, result contributions, persistence expectations and non-goals. Identify any existing command/endpoint sharing code that requires a compatibility test.
3. **Implement domain first.** Add the pure calculation and validations. Tests MUST cover every named example, unit/dimensional conversion, limiting/boundary and rejection case, deterministic result and input non-mutation, with independently justified expected values.
4. **Integrate through application and API.** Use a test port for accepted/rejected storage; verify calculate does not write, save is atomic, unsupported input does not consume an identifier, and legacy requests/responses remain unchanged.
5. **Integrate the UI.** Use server results only. Verify editing invalidates stale results, errors never appear as success, keyboard/accessibility behavior remains available, and visible units/status/applicability match the API result.
6. **Defer persistence migration.** Any proposed schema change follows the separate migration design gate in Section 5. No migration is implicit in adding the model.
7. **Verify before claims.** Run applicable backend/frontend suites and public API/browser flows. Report software correctness separately from engineering validation. No passing test, documented WellPlan equation or static REA result authorizes field-use or parity claims.

A release candidate is acceptable only when the model gate is approved; old API behavior is preserved; errors/rejections have no unintended effects; the result is traceable and unit-labelled; and applicable tests pass. Missing engineering approval or unavailable required evidence is a blocker, not a waiver.

## 8. Explicitly deferred decisions

The drilling engineer must review and decide: the exact bit-loss equation and source edition; whether nozzle count/diameter or total area is the user-facing input; the coefficient source and override policy; accepted flow/fluid range; whether combined pressure is meaningful for the initial product; and the independent example dataset/reference. Later design must separately decide API version shape, persistence schema/migration and any import formats from real licensed use cases. This specification makes no unsupported choice on those questions.
