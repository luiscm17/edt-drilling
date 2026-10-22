# Hydraulics: bounded static evidence

This note records facts from read-only inspection of an authorized installed
build. It is **not** a specification for OpenOil formulas, a numerical oracle or
permission to redistribute vendor software. No target code was executed,
decompiled into this repository or copied into the implementation.

## Artifact identity and trace

| Layer | Exact artifact identity | REA evidence | Observation |
| --- | --- | --- | --- |
| Managed service proxy | `C:\Landmark\EDT\WellPlan\plugins\DSWE.Hydraulics\DSWE.Hydraulics.Calculation.dll` · SHA-256 `f07e1b6963db1bfd22f0367f7a113b39e400db94d86cbd6484812f5cc31a9111` | `ev_99ea63b0a413ca63099a89f4e13eb70f34f45029118fc047bbbe7797b5b9c0db`; members `ev_8a8906017245066f18ac732da02f92cd93c553cf154b4a72b793fd36b0711ace` | The pressure-profile executor has a static call edge to an ECD calculation service. The proxy does not establish the underlying equations. |
| Service orchestration | `C:\Landmark\EDT\WellPlan\plugins\DSWE.Shared\EDK.WebService.Wellplan.dll` · SHA-256 `9f058b5259c79049bea68be527ac2c8f2ad6c16248622b0a44a4ca286c41974f` | `ev_dbaaa3701d677abea0925851fc91ada8879b62283874746e58f2f78e29b6f8fa`; members `ev_e3fc7c6e1f25ee6feae581ef82e80f9a494cbbf7b8064ab453b58728f0761717` | The ECD service reaches a helper that statically calls `EDK.Hydraulics.Calculations.ManHYDPRESSPROFILE`. Its selected method accepts many input parameters; names alone do not define their semantics. |
| Mixed managed/native boundary | `C:\Landmark\EDT\WellPlan\plugins\DSWE.Shared\EDK.Hydraulics.dll` · SHA-256 `bb81bf7f4543fa02645332ce750078f5cc85eb44a8bacbe1213ce2177c3a0ae3` | `ev_b0b91f3d1899a4f687be8a9f26e2b162cbf6800112baafe41d5ee871decf67ed`; members `ev_17ebfda2e6cd6454aba3a97c674a06ba820111ff346fbba0be9e62a9458b2946`; boundary `ev_9d2fa77812c8ef7a9529159ea2fe23bd2896d4fbb63a88ef8a96d212b1d974b5` | Mixed C++/CLI x64 assembly. `ManHYDPRESSPROFILE` has a file-backed managed body that calls `<Module>.HYDPRESSPROFILE`; the latter is a native/unmanaged declaration at token `0x06000061`. This is a declaration, not a verified native export or recovered implementation. |

The call path is a **static relationship**, not an observed execution trace.
The calculation assembly also names pressure analysis, bit optimization,
cuttings, flow-rate and surge/swab services. Their presence does not make those
capabilities part of this OpenOil hydraulic slice.

## Boundaries and open questions

- No coefficients, numerical method, units, transition rules, correlation
  selection or error behavior were established by these metadata observations.
- REA's managed parser did not load or execute assemblies. Native deep-analysis
  methods were unavailable on this host (`provider_missing` in `binary_session`);
  mixed-mode native bodies remain outside inspected coverage. No fallback
  provider or unapproved target execution was substituted.
- A fidelity claim would require independently authorized, controlled reference
  cases with inputs, outputs, version, configuration, units and tolerances, or
  separately available native analysis. Until then OpenOil's numerical model is
  independent and governed by its own documented applicability limits.
- The next research question is the input/output behavior of one bounded
  pressure-profile case; collect a controlled, isolated observation before
  turning it into a conformance fixture. Do not infer behavior from names.
