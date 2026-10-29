"""Independent zero-second Fann gel / string-interior pressure study, SI only."""
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

from openoil.domain.bingham_rheology import (
    LB_FT2_TO_PA,
    STRESS_LB_FT2_PER_DIAL,
    STRESS_PA_PER_DIAL,
)


@dataclass(frozen=True)
class Component:
    length_m: float
    inner_diameter_m: float


def calculate(dial_3_rpm: float, components: Sequence[Component]) -> dict:
    """Use tau_g = converted 3-rpm dial and p = 4*tau_g*sum(L/ID).

    Components retain input order. No storage, hydraulic coupling or input mutation.
    """
    def finite_number(value):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and isfinite(value))

    if not finite_number(dial_3_rpm) or dial_3_rpm < 0:
        raise ValueError("dial_3_rpm must be nonnegative and finite")
    if isinstance(components, (str, bytes)):
        raise ValueError("components must not be empty")
    try:
        source = tuple(components)
    except TypeError:
        raise ValueError("components must not be empty") from None
    if not source:
        raise ValueError("components must not be empty")
    for component in source:
        if not isinstance(component, Component):
            raise ValueError("each component must be a Component")
        for field in ("length_m", "inner_diameter_m"):
            value = getattr(component, field)
            if not finite_number(value) or value <= 0:
                raise ValueError(f"{field} must be positive and finite")

    stress = STRESS_PA_PER_DIAL * dial_3_rpm
    breakdown = []
    total = 0.0
    for component in source:
        ratio = component.length_m / component.inner_diameter_m
        pressure = stress * ratio * 4
        total += pressure
        if not all(isfinite(value) for value in (stress, ratio, pressure, total)):
            raise ValueError("calculation outside finite numerical range")
        breakdown.append({"length_m": component.length_m,
                          "inner_diameter_m": component.inner_diameter_m,
                          "pressure_pa": pressure})
    return {
        "gel_stress": {"quantity": "zero_second_gel_stress", "value": stress, "unit": "Pa"},
        "pressure": {"quantity": "interior_break_gel_pressure", "value": total, "unit": "Pa"},
        "components": breakdown,
        "source": {"rpm": 3, "dial": dial_3_rpm,
                   "stress_lb_ft2_per_dial": STRESS_LB_FT2_PER_DIAL,
                   "lb_ft2_to_pa": LB_FT2_TO_PA},
        "scope": "string interior only",
        "model_id": "openoil.rheology.fann-zero-second-gel-break-pressure",
        "model_version": "1.0.0",
        "input_schema_version": "1",
        "result_schema_version": "1",
        "applicability": {
            "status": "supported",
            "assumptions": "Uniform zero-second gel stress from the 3 rpm Fann dial; "
                           "constant circular inner diameter in each component; string interior only.",
            "limitations": "Excludes annulus, timed gels, tool joints, Herschel–Bulkley fitting "
                           "and hydraulic coupling. No WellPlan parity; not validated for field decisions.",
        },
    }
