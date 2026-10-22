# Passive WellPlan runtime inventory

Scope: already-running local WellPlan; process discovery, one bounded REA read-only module-name observation, static PE/CLI metadata, and a Windows accessibility-tree shape check. No login, document navigation, data entry, calculation, database query, screenshot, or vendor file write was performed. No numeric reference output was captured.

## Observed

| Surface | Evidence | Observation | Limit |
| --- | --- | --- | --- |
| Running process | Host process inventory and REA `list_frida_processes` on `local` | `WellPlan.exe`, PID 19120, from `C:\Landmark\EDT\WellPlan\WellPlan.exe`; a separate `EDK.Wellplan.WCFWindowsService32Host.exe` was also listed by the host. | A PID is not proof of database access or calculation readiness. PID can change on restart. |
| Executable identity | REA `inspect_managed_artifact` summary `ev_da70754385d081cc553debd41154becd998219497b613db9d5b67df5260aa2d8` (parent `ev_ab7bfad09692e323b3795c254fb7dab3d423cb0ff4ad260edd76fbefbfb6065f`) | SHA-256 `784dc7ecea42dc7f1b71197db31dd8febc3f43175dd8cc374e7b559daadeb29f`; PE x64, IL-only, `.NETFramework,Version=v4.5.1`, assembly `WellPlan` version `5000.10.1.1`, complete reported metadata, MVID `c4083187-6710-4e50-b1f7-dd3a0342555d`. | Assembly version is not an independently verified product version. Static metadata does not execute calculations or establish UI behavior. |
| Loaded modules | REA `instrument_with_frida` attach to PID 19120, names and base addresses only; evidence `ev_bed0f39f38c8d45f09e5bb8203e76b09dd8a5312598b121ebf5ff7cd9f8f1ee0` | Of modules matching only `wellplan`, `edk.` or `edm`, returned `WellPlan.exe`, `EDM.Units32.dll`, `SharedMemory.dll`. The bounded ephemeral observation reported no cleanup error. | A name filter is not an exhaustive module list. Loaded unit support does not establish a chosen unit system or formula path. No argument values, memory contents or credentials were read. |
| Window shape | Host `Get-Process` and read-only Windows UI Automation | The process had a main window with a WellPlan-matching title; root is a Window with 14 immediate children and 167 descendant accessibility nodes. No password field or login/database label matched within that sampled tree. | REA's native UI observation tool is for an active Mach-O target, not this Windows executable. UIA snapshot does not prove the login has completed, identify a workspace, or establish whether demo/user data exist. No names or values from controls were persisted. |

Prior static evidence for the mixed-mode hydraulic assembly and documented nozzle equation is in [`research/hydraulics/003-wellplan-parity-evidence.md`](../hydraulics/003-wellplan-parity-evidence.md). Neither that equation nor the new module observation is a measured WellPlan output.

## Isolation gate before a reference run

The user reports a newly installed application and a database-access prompt at launch; the presence or absence of bundled/demo or user records has **not** been verified. The credentials shared in conversation were not submitted, retained, or written to tools or artifacts. Do not infer that a newly installed database is disposable.

Before any case creation, calculation or save: identify the active EDM database and whether it contains existing records; establish a separate disposable database or equivalent reversible test workspace and writable profile/output paths; enumerate whether WellPlan can write outside this repository (database, logs, settings, license/profile). Confirm the synthetic case is isolated from user wells. If those controls cannot be demonstrated, stop at passive inspection and ask for a specific disposable environment. `research/wellplan-reference/` holds **our evidence only**; it does not sandbox the vendor process.

Current status: passive process access confirmed; GUI command access, database access, calculation execution, reference outputs, model equivalence and numerical tolerance remain **unknown**.
