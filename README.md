# OpenOil

OpenOil is a browser-based drilling-engineering workbench for transparent, bounded calculation studies. It pairs a React interface with a Python API and keeps engineering assumptions, units, and limitations visible instead of presenting estimates as field-validated predictions.

## Current studies

- **Drilling hydraulics:** steady, single-phase Newtonian flow in a vertical well, with explicitly supported flow regimes.
- **Bit/nozzle pressure loss:** a separate calculation contribution; it is not a complete circulating-system or standpipe-pressure result.
- **Torque and drag:** a quasi-static straight-well weight-and-contact study, not a directional-well simulator.
- **Bingham rheology:** standalone plastic-viscosity/yield-point derivation from 300/600 RPM readings, with an SI shear curve; not a full rheology or hydraulics model.
- **Power Law rheology:** standalone flow-behavior/consistency derivation from positive 300/600 RPM Fann readings, with an SI curve and observed points; not a hydraulic or full-fluid fit.
- **Generalized Herschel–Bulkley rheology:** evaluate explicitly supplied SI parameters and inspect a modeled shear curve; no Fann fitting, foam-pressure solver or hydraulic coupling.

See the [capability roadmap](docs/gaps.md) for the reconstruction target and the [engineering reference](docs/reference/drilling-capabilities.md) for documented workflows, equations, and unknowns. The [backend guide](backend/README.md) describes the current models, API behavior, and supported domains.

## Run locally

Requires Docker Compose and a running Docker engine.

```bash
docker compose up --build
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Stop the services with `Ctrl+C` or `docker compose down`. Saved cases persist in the Compose `case-data` volume.

## Engineering and security limits

OpenOil is for engineering study, not operational authorization. The implemented models are intentionally limited and have not been independently validated for field use. Do not use their results to set safety-critical pressure limits or make field decisions.

The local Compose setup binds the web interface to loopback, but the application does not provide authentication. Do not expose it to an untrusted network.

## Documentation

| Start here | What it covers |
| --- | --- |
| [Product requirements](docs/product/prd.md) | Product goals and user-facing requirements. |
| [Capability roadmap](docs/gaps.md) | Normative target workflows OpenOil is intended to reconstruct. |
| [Engineering capability reference](docs/reference/drilling-capabilities.md) | Documented workflows, equations, unknowns, and model boundaries. |
| [Technical requirements](docs/architecture/trd.md) | Shared architecture and implementation constraints. |
| [Bit/nozzle design](docs/architecture/hydraulics-capability-design.md) | Technical contract for that calculation capability. |
| [Backend guide](backend/README.md) | API, model details, persistence behavior, and backend checks. |
