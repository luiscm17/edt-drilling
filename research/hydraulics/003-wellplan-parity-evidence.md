# WellPlan hydraulic parity: evidence boundary

This is a bounded, read-only investigation of the authorized installed
`C:\Landmark\EDT` tree. It is not a claim of numerical equivalence or a
specification of vendor algorithms. No installed program was executed or
modified, and no proprietary implementation was copied.

## What was observed

| Artifact | Identity and REA evidence | Established fact |
| --- | --- | --- |
| `WellPlan/plugins/DSWE.Shared/EDK.Hydraulics.dll` | SHA-256 `bb81bf7f4543fa02645332ce750078f5cc85eb44a8bacbe1213ce2177c3a0ae3`; `ev_b0b91f3d1899a4f687be8a9f26e2b162cbf6800112baafe41d5ee871decf67ed` | .NET Framework 4.5.1 mixed C++/CLI and native x64 assembly, version 17.100.1.9; static metadata complete. |
| `WellPlan/plugins/DSWE.Shared/EDK.WebService.Wellplan.dll` | SHA-256 `9f058b5259c79049bea68be527ac2c8f2ad6c16248622b0a44a4ca286c41974f`; member evidence `ev_e3fc7c6e1f25ee6feae581ef82e80f9a494cbbf7b8064ab453b58728f0761717` | Static managed call edges connect orchestration to hydraulic calculations; they do not define numerical behavior. |

The prior [call-path study](evidence.md) traces the pressure-profile
entry to a mixed-mode native declaration, but does not recover its body.
REA's current `binary_session` reports the Ghidra provider unavailable:
`GHIDRA_INSTALL_DIR` is unset, the corresponding native decompiler is
missing, and the Windows Java probe fails. This is a provider limitation,
not evidence that the formula does not exist. Managed metadata inspection
is static and never runs the calculation.

## Documented equations are not runtime parity

The installed `WellPlan/webhelp/Topics/c_plot_noz_vel_calcs.html` explicitly
states `v_n = c_d Q / (2.96 A_bit)` in API units (velocity ft/s, circulation
gpm, total nozzle area in², `c_d = 0.95`). Adjacent shipped topics
`c_bit_press_loss_calc.html` and `c_ecd_calc.html` contain separate bit-loss
and ECD equations. These are vendor **documentation observations**, not
REA-recovered native bodies or measured output. They support a scoped,
independently coded dynamic nozzle-velocity calculation with explicit units,
but cannot establish which runtime options invoke them or claim full parity.

## What parity would require

A controlled reference suite must record WellPlan version/configuration,
units, input case, full output, failure behavior and numerical tolerances.
At least distinct laminar/turbulent and unsupported-boundary cases would
need comparison against independent OpenOil calculations; no such observed
reference outputs exist in this investigation. Therefore **no runtime parity
fixture or field-use claim is justified**. OpenOil's calculations remain
dynamic, independently specified and bounded by documented assumptions.
Full numerical reconstruction is pending a usable native-analysis provider
or controlled reference cases; avoid hardcoded example outputs.
