# ODD — OpenOil engineering documentation slice

Objective: Use ODD to produce and verify the product and architecture documents for a bounded bit/nozzle pressure-loss capability. The normative product requirements belong in `docs/product/prd.md`; the normative technical design belongs in `docs/architecture/hydraulics-capability-design.md`. This file tracks ODD execution only.

## Specs

S1 (user direction, verbatim): "ok, realiza el odd, recuerda q esa doc es de caracter normativo, no es un hictorial o bitacora, se entiende? dale imagino q al ser documental no ejecutaras codigo, al contrario investigaras con rea para diseno de implementacion y arquitectura. dale" Check: use read-only REA research to inform design; do not execute application code or change runtime/data.
S2 (correction, verbatim): "buena documentacion, pero confundiste dos conceptos vitales para un dev. Odd es un metodologia de implementacion asi como lo es SDD, es mas odd es una mejora a sdd y tu como gentle-shell usas odd para implementar cosas. Por otro lado la tarea q dijiste hacer mediante odd era documentacion core normativo y eso deberia estar en docs/ pero lo q tu hiciste es mezclar ambos conceptos. entiendes lo que hiciste mal?" Check: keep ODD process tracking separate from normative product and architecture artifacts.
S3 (corrective instruction, verbatim): "exacto, incluso quizas esta doc q hiciste ahora parece una mejora al prd actual. de cualquier forma corrige tu error" Check: move product requirements to the PRD where appropriate, keep technical architecture in `docs/architecture/`, and restore this file to workflow tracking.

## Tasks

T1 [S1-S3] Inspect PRD/TRD and classify requirements by product versus technical architecture; route: parent; done.
T2 [S1-S3] Use read-only REA inspection to inform the technical boundary; route: parent; done (managed metadata and native-boundary evidence only; vendor artifacts not executed).
T3 [S1-S3] Add P6 product acceptance to `docs/product/prd.md` and add focused technical design to `docs/architecture/hydraulics-capability-design.md`; route: parent; done (documentation only; no application code or DB changes).
T4 [S1-S3] Restore ODD task tracking here, validate document scope/evidence and links, mirror the corrected structure, and commit; route: parent; done (structure, source paths and REA IDs checked; commit follows).

## Log

L1 (initial ODD authorization, verbatim): ok, realiza el odd, recuerda q esa doc es de caracter normativo, no es un hictorial o bitacora, se entiende? dale imagino q al ser documental no ejecutaras codigo, al contrario investigaras con rea para diseno de implementacion y arquitectura. dale
L2: The prior commit `8bd1506` put normative product/technical requirements in this ODD task file. This conflated ODD as an implementation methodology with the normative documentation deliverable. The user clarified the distinction; that document was split into product requirements and a technical design under `docs/`, and this file was restored to an ODD workflow record.
L3: Read-only REA inspections were used for the two installed WellPlan assemblies. The binaries were not loaded or executed. Existing application code and databases were not changed; no application tests were run because the deliverable is documentation.
