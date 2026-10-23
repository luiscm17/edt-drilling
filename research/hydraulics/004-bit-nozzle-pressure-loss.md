# WellPlan bit/nozzle pressure-loss evidence

## Purpose and boundary

This research note records a bounded investigation of the installed WellPlan help and the corresponding static calculation artifacts. It informs OpenOil P6; it is not a claim of runtime parity or field validation. No WellPlan target was launched, no case data was accessed or changed, and no proprietary implementation was copied.

## Installed documentation

The installed help topics identify themselves as WellPlan 5000 documentation (the inspected topics include 5000.11 / 5000.15 revisions):

- `C:\Landmark\EDT\WellPlan\webhelp\Topics\c_bit_press_loss_calc.html` documents the bit pressure-loss equation in API units:

  `ΔP_lossbit = ρ v_f² / (2 g_c C_d²)`

  It defines `ρ` as fluid density, `v_f` as fluid velocity, `g_c` as the gravitational constant, `C_d` as nozzle coefficient (0.95), and `ΔP_lossbit` as bit pressure loss. The equation page does not state the density unit inline.
- `c_plot_noz_vel_calcs.html` independently documents `v_n = C_d Q / (2.96 A_bit)`, with `v_n` in ft/s, `C_d = 0.95`, circulation rate `Q` in gpm and total bit flow area (TFA) `A_bit` in in².
- `r_ub_nomenclature.html` defines `g_c = 32.174 lb·ft/(lbf·s²)`.
- `c_plot_bit_pressure_loss_ov.html` describes the full WellPlan plot as dependent on its selected fluid rheology, rig maximum pump pressure and string/fluid/hole-section information; it also describes parasitic losses and automatic tool-joint losses. Those are broader system-optimization behaviors, not implemented by this bounded P6 contribution.
- `c_plot_press_loss_calcs.html` lists the bit hydraulic-power, impact-force and nozzle-velocity equations for that plot. `c_plot_press_loss_refs.html` points to the general technical references; that list includes F. M. White, *Fluid Mechanics* (1979).

The documentation distinguishes bit pressure loss from the nozzle-velocity study. The API-unit calculation uses the documented coefficient and velocity equations; the 2.96 conversion is retained as printed rather than silently replaced with another conversion constant.

## REA static observations

REA inspected the authorized installation without loading or executing its code:

| Artifact | SHA-256 | REA evidence | Relevant static observation |
| --- | --- | --- | --- |
| `plugins/DSWE.Hydraulics/DSWE.Hydraulics.Calculation.dll` | `f07e1b6963db1bfd22f0367f7a113b39e400db94d86cbd6484812f5cc31a9111` | `ev_ed33a5f9e1054048d3ff7b19d1b7d8066f617f1a969104f4d6be8e41beae3b70` | `PressureProfileCalculationExecutor.RunAnalysis` maps domain inputs and calls the `IHydraulicsEcdCalculationService` interface. This is orchestration, not the numerical pressure-loss equation. |
| `plugins/DSWE.Shared/EDK.WebService.Wellplan.dll` | `9f058b5259c79049bea68be527ac2c8f2ad6c16248622b0a44a4ca286c41974f` | artifact `ev_dbaaa3701d677abea0925851fc91ada8879b62283874746e58f2f78e29b6f8fa`; selected members `ev_6828bc13884b9c57ed48ce870249e3256074f6b18cc8763bb741b5da3c62fe2f` | The pressure-analysis service passes `TotalFlowArea` through its helper to the hydraulics calculation; the bit-optimization service invokes the bit-optimization calculation. This shows the calculation pathways and TFA's role, not the bit-loss equation. |
| `plugins/DSWE.Shared/EDK.Hydraulics.dll` | `bb81bf7f4543fa02645332ce750078f5cc85eb44a8bacbe1213ce2177c3a0ae3` | artifact `ev_b0b91f3d1899a4f687be8a9f26e2b162cbf6800112baafe41d5ee871decf67ed`; selected member `ev_17ebfda2e6cd6454aba3a97c674a06ba820111ff346fbba0be9e62a9458b2946` | Mixed C++/CLI/native. Managed wrappers `ManHYDPRESSPROFILE` and `ManHYDGRAPHBITOPT` call native-module routines `HYDPRESSPROFILE` and `HYDGRAPHBITOPT`. The provider did not expose their native calculation bodies. |

A fresh `binary_session` reported Ghidra unconfigured (`GHIDRA_INSTALL_DIR` unset), with the Windows Java probe unavailable; Hopper is unsupported on this host and IDA/Kuna are not configured. Thus REA corroborates relevant artifact identity, API/service paths and native boundary but cannot independently inspect the native equation body on this host. This limitation does not negate or replace the installed documentation equation; it limits what the binary investigation can confirm.

## Engineering derivation and example

The documented pressure relation is the standard incompressible nozzle/orifice energy-loss form: pressure drop is kinetic energy per volume divided by the squared discharge coefficient. In consistent SI units:

`ΔP_lossbit [Pa] = ρ [kg/m³] · v_f² [m²/s²] / (2 · C_d²)`

For API units, using the documented `g_c = 32.174 lb·ft/(lbf·s²)`, density in lbm/ft³, velocity in ft/s and `C_d` dimensionless yields pressure in lbf/ft²; divide by 144 for psi. Density conversion is `1 ppg = 7.4805194805 lbm/ft³`. These unit transformations are dimensional conversions, not recovered implementation details.

Independent example derived from the two documented equations, not a WellPlan output: with `Q=296 gpm`, `TFA=1 in²`, `C_d=0.95`, and fluid density `10 ppg`, the documented velocity equation gives `v_f=95 ft/s`; the pressure-loss equation gives approximately `80.7299 psi` (`556.613 kPa`). The calculation is reproducible directly from the documented constants and unit conversions.

For OpenOil P6, the bounded capability should accept an explicitly supplied single-phase fluid density, circulation rate and total effective nozzle flow area; calculate one bit/nozzle pressure-loss contribution under the documented coefficient/model version; return it separately from base hydraulic losses; and define no aggregate with the base system pressure unless an explicit physical boundary is modeled. It does not reproduce WellPlan's system-wide pressure optimization, rheology-dependent parasitic losses, tool-joint losses or plot behavior.

The documented API units for `ρ` are not printed on the bit-loss page itself. The implementation can avoid importing that ambiguity by calculating in SI with explicit kg/m³, m³/s and m² inputs, while the UI displays units and cites the documented API equations. The API example above still records the exact documented conversion path as an independent engineering check.
