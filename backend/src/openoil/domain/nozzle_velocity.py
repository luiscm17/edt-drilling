"""Documented API-unit nozzle equation with an SI interface; no I/O."""

from math import isfinite


def calculate(flow_m3_s: float, total_nozzle_area_m2: float) -> float:
    """Return the documented 0.95 * Q_gpm / (2.96 * A_in2), converted to m/s.

    Exact US-gallon, inch and foot conversions retain the installed help's
    literal 2.96 constant; this is not the coherent-SI identity 0.95 * Q/A.
    Documentation is not a recovered implementation or a runtime oracle.
    """
    for name, value in (
        ("flow_m3_s", flow_m3_s),
        ("total_nozzle_area_m2", total_nozzle_area_m2),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be positive and finite")
    flow_gpm = flow_m3_s * 60 / 0.003785411784
    area_in2 = total_nozzle_area_m2 / 0.0254**2
    velocity_ft_s = 0.95 * flow_gpm / (2.96 * area_in2)
    velocity_m_s = velocity_ft_s * 0.3048
    if not isfinite(velocity_m_s) or velocity_m_s <= 0:
        raise ValueError("calculation outside finite numerical range")
    return velocity_m_s
