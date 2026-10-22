# WellPlan reference evidence

This directory holds bounded, text-only observations and synthetic reference-case results for the WellPlan comparison. It is not a copy of the vendor installation, EDM database, credentials, user cases, raw process captures, or binary artifacts. Do not place any of those here.

- [Initial passive runtime inventory](01-passive-runtime-inventory.md): what was directly observed and what remains unproved.
- Future measurements, if isolation is established: separate input/configuration/output records with units, version, timestamp, artifact identity and declared tolerances. Label observed, inferred and unknown facts separately.

The task and decision gates are in [`odd/tasks/wellplan-reference-validation.md`](../../odd/tasks/wellplan-reference-validation.md). A repository-local output directory does **not** redirect or isolate WellPlan's own database, profile, logs or license writes.
