# OpenOil torque and drag study
Objective: Add a bounded independent straight-well torque-and-drag study to OpenOil; static WellPlan evidence is contextual, never a numerical oracle.
Branch: `feat/torque-drag` | Delivery: `auto-chain`, `chain_strategy=feature-branch-chain` (forecast ~600–900 authored lines; no push/PR authorized) | Runner: Docker Compose backend unittest, frontend Vitest/build and local browser smoke.

## Specs
S1. "crea una nueva rama e implementa una nueva funcionalidad, tienes autorizacion durante toda la implementacion de usar mcp rea e invetigar el directorio de wellplan, mediante odd implementa otra funcioanldiad. dale". Check: work on a new feature branch, use ODD and bounded static REA investigation of the authorized WellPlan directory; no execution or modification of the installed application, no vendor parity claim.
S2. "Torque y arrastre (recomendada)". Check: an independently specified torque-and-drag study calculates inspectable engineering outputs in OpenOil with explicit units, limits, rejection behavior and a usable browser interface.
S3. Assumption (not a user requirement): first slice is a straight, uniformly inclined well and string; constant per-section air weight and outer diameter, fluid buoyancy and simple Coulomb contact. Report pickup/slackoff surface tension and rotating-contact torque by section; no doglegs, buckling, distributed tension-dependent normal force, bit load, or field suitability. Tests use independent hand calculations and reject unsupported inputs rather than imply WellPlan equivalence.
S4. Assumption (preserve existing product contracts): add a separate API route and UI panel without changing hydraulic V1/V2 schemas, storage or calculations. Provision and run dependencies exclusively inside existing Docker images; no new persistent cases until separately scoped.

## Tasks
T1 [S1-S3] Establish static evidence and model boundaries; route: inline; done; commit: da5bf57 (structural diff check passed; static REA evidence logged).
T2 [S2-S3] Implement independent calculation and RED/GREEN numerical/rejection tests; route: delegated (context backstop); done (focused 10/10 and full backend 36/36); commit: pending.
T3 [S2-S4] Add validated calculate-only HTTP route and preservation tests; route: inline; pending; commit: pending.
T4 [S2-S4] Add accessible UI study inputs/results and interaction tests; route: inline; pending; commit: pending.
T5 [S1-S4] Run Docker checks, functional integration, risk assessment and reconcile ODD; route: inline; pending; commit: pending.

## Log
L1 (original request, verbatim): hey hola de nuevo, tuviste problema de conexcion pero ahora volvimos, estamos en main, crea una nueva rama e implementa una nueva funcionalidad, tienes autorizacion durante toda la implementacion de usar mcp rea e invetigar el directorio de wellplan, mediante odd implementa otra funcioanldiad. dale
L2 (selected capability, verbatim): Torque y arrastre (recomendada)
L3: Started from clean main 42b2497 on feat/torque-drag. Static REA inspected C:\Landmark\EDT\WellPlan\plugins\DSWE.TorqueDrag\DSWE.TorqueDrag.Calculation.dll, SHA-256 09c6d80252bdac6d7cd59149e63f6bb5d2bff0d750eb16a73d85cdd7c6e7a014; evidence ev_d1ac69763b27b61e0b59d486b6e4904fa27edb607ef4e603e2b919fe9df9599e. Observed .NET Framework 4.5.1 CIL assembly metadata, not formulas or behavior. No target execution. User choice settles capability; S3-S4 are explicit bounded implementation assumptions.
L4 (delivery decision): User selected "Cadena en rama de funcionalidad (recomendada)". Delivery strategy auto-chain with feature-branch-chain; no push or PR authorized. Research boundary at research/torque-drag/boundary.md; a straight inclined string is an explicitly constrained study assumption.
L5: T2 worker added standalone torque_drag.py and ten rule-focused tests. RED focused and post-write focused/full Docker commands all exited 1 before running Python: missing npipe dockerDesktopLinuxEngine. Parent reviewed both files and independently confirmed Docker server connection fails (exit 1); no RED/GREEN or numerical validity claim. Two untracked source/test files are retained, no T2 commit or API/UI integration. Resume after Docker Desktop Linux engine is available; run focused test then full backend suite, resolve any observed failure before proceeding.
L6 (user environment update, verbatim): ufff perdon, ya inicie docker, puedes continuar
L7: First Docker focused command exited 5 with 0 tests because the backend image had not been rebuilt and tests are copied into the image (src alone is mounted). After docker compose build backend, focused suite exit 0 (10 tests); full backend suite exit 0 (36 tests). Original RED was unavailable: before implementation Docker pipe missing, not an assertion failure. No RED claim. Hand-calculated and invalid-input tests now pass; independent physical validation still absent. Risk: none (new isolated calculation, no shared code or persisted state changed).
