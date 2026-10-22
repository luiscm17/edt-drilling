# OpenOil — Technical requirements

OpenOil shall use a **hexagonal modular-monolith architecture**. Calculation
models and use cases form the core; transport and persistence are adapters.
Dependencies point toward the core. The [product requirements](../product/prd.md)
define user outcomes and the safety boundary; this document defines technical
constraints that apply as capabilities are delivered.

## Architecture and ownership

```text
User interface → inbound transport adapter → application use cases → domain
                                           │
                                     outbound ports
                                           ↑
                                persistence adapters
```

| Boundary | Required responsibility | Forbidden dependency |
| --- | --- | --- |
| Domain | Typed engineering quantities, applicability rules and deterministic calculations. | HTTP, UI, database, filesystem and framework APIs. |
| Application | Use cases for calculation and case lifecycle; validation-before-write, result provenance and transaction intent. Define outbound ports from use-case needs. | SQL, HTTP request objects and presentation formatting. |
| Inbound adapters | Validate transport shape, invoke use cases and translate errors into a documented public contract. | Engineering formulas or direct database access. |
| Outbound adapters | Implement ports for case storage or other external systems. | Business rules that bypass application validation. |
| Composition root | Select concrete adapters and wire use cases at startup. | Engineering decisions based on deployment wiring. |
| User interface | Edit inputs, invoke use cases and present results with units, limits and accessible data. | Authoritative calculation of engineering results. |

Capabilities shall be isolated by domain and application boundaries within one
backend deployment. Shared contracts shall contain only genuinely cross-capability
concepts; a capability must not import another capability's adapter. Adding a
transport or database must not change a calculation model. Do not introduce
microservices or a port for every function; ports represent external-system
boundaries required by use cases.

## Engineering contracts

- Use SI units in the domain and persisted records. Public inputs and outputs
  shall name the physical quantity and unit; any display-unit conversion occurs
  at a boundary and shall be reversible within declared precision.
- Models shall declare their applicability domain, assumptions, correlation
  selection and unsupported conditions. Reject nonfinite quantities and inputs
  outside the declared domain before producing or saving a result.
- Results shall be deterministic for a given input, model identifier/version
  and declared configuration. Calculations must not mutate their inputs, emit
  output or access external state. Presentation rounding must not modify values
  used by calculations or saved snapshots.
- Every result shall identify its model and contract versions and retain enough
  section-level contributions to audit totals. A visualization shall derive from
  that same result, not introduce an independent engineering calculation.
- Calculation-specific equations, ranges and tolerances belong in the scoped
  capability specification, not in shared architecture rules. The hydraulic
  capability must preserve the product boundary in the PRD, including the
  distinction between pipe friction and standpipe pressure.

## Case and interface contracts

The application shall distinguish **calculate** (no write), **save** (validate,
calculate, then commit one input/result snapshot), **list** and **load** (return
the stored snapshot without implicit recalculation). Successful saves receive
stable distinct identifiers. Rejected requests shall neither modify stored
cases nor consume an identifier. Recalculation, if offered, must be an explicit
operation with its model/version recorded separately from the original result.

Inbound adapters shall reject malformed input and preserve documented error
categories: transport validation, unsupported engineering input, missing case
and infrastructure failure. An infrastructure failure must not be presented as
an input error. Error responses must not disclose submitted sensitive values.
Published interface contracts shall be versioned; incompatible changes require
an explicit migration path rather than silent reinterpretation of old clients.

## Storage and provenance

A stored case shall associate normalized inputs, unrounded results, units,
model identifier/version, input/result schema versions, assumptions or
correlation selection and creation time. Input origin may be retained only when
needed for traceability and without collecting unnecessary sensitive data.
Persist the input and result atomically; load shall never recalculate or invent
missing provenance. Storage schema changes require explicit, tested migrations
and a defined read policy for older snapshots. Provenance absent from older
records is **unknown**, never inferred from a newer model.

Storage adapters shall enforce finite serialization and stable record ordering.
Ports must express the atomic operations needed by the application, not expose
SQL or storage-specific cursors to use cases. Backup, restoration and retention
policies are prerequisites for any deployment that relies on stored cases.

## Runtime and security boundaries

The local workbench shall bind its user-facing port to host loopback and shall
not publish the backend directly. Container builds shall install Python and
frontend dependencies inside their respective images; the host needs only a
container runtime. A development server is not a production serving solution.

Local use assumes trusted users and small datasets. Multi-user or networked use
requires a separate design for identity, authorization, TLS, resource limits,
concurrency, backup/recovery, log hygiene and deployment hardening. Input
validation does not replace access control. The workbench must not be described
as suitable for safety-critical operation without independent engineering
validation appropriate to the capability.

## Verification requirements

| Boundary | Required evidence |
| --- | --- |
| Domain | Numerical examples with independently justified expected values, dimensional checks, applicability limits, finite-range rejection and deterministic non-mutation. |
| Application | Use-case tests with a port implementation that exposes accepted and rejected writes, model identity and snapshot semantics. |
| Adapters | Public-interface contract tests for status, response, errors and invalid-input side effects; persistence tests for atomicity, compatibility and older snapshot reads. |
| User interface | Interaction and accessibility tests for input edits, results, errors and save/load; real browser-to-API checks for critical flows. |
| Runtime | Container build and configuration checks, host-exposure checks and isolated persistence/restart tests where durability is claimed. |

Software tests verify contract behavior, not field accuracy. Each new capability
shall have reproducible fixtures with documented source, units, assumptions and
tolerances, plus independent engineering validation before operational claims.
