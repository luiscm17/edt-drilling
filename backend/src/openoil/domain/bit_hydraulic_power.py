"""Bounded hydraulic power from an explicitly supplied pipe or annulus loss.

The installed-help API equation is Q[gpm] * P_loss[psi] / 1714 [hp].
See docs/reference/drilling-capabilities.md. This is not bit nozzle power.
"""

from math import isfinite

GALLON_M3 = 0.003785411784
PSI_PA = 6894.757293168


def calculate(flow_m3_s: float, pressure_loss_pa: float, pressure_boundary: str) -> dict:
    for name, value in (("flow_m3_s", flow_m3_s), ("pressure_loss_pa", pressure_loss_pa)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")
    if pressure_boundary not in ("pipe", "annulus"):
        raise ValueError("pressure_boundary must be pipe or annulus")
    power_hp = ((flow_m3_s * 60 / GALLON_M3) * (pressure_loss_pa / PSI_PA)) / 1714
    if not isfinite(power_hp) or power_hp <= 0:
        raise ValueError("calculation outside finite numerical range")
    return {
        "power": {"quantity": "hydraulic_power", "value": power_hp, "unit": "hp"},
        "pressure_boundary": pressure_boundary,
        "model_id": "openoil.hydraulics.documented-pressure-loss-power",
        "model_version": "1.0.0", "input_schema_version": "1", "result_schema_version": "1",
        "applicability": {
            "status": "supported",
            "assumptions": "User-supplied circulation rate and loss in the selected pipe or annulus passage; documented API-unit conversion and divisor 1714.",
            "limitations": "The loss is supplied, not calculated; not bit/nozzle loss or a standpipe pressure model. No optimization, system aggregate, vendor parity, or field validation.",
        },
    }
