"""Independent zero-yield-stress Newtonian derivation, not a fluid classifier."""

from collections.abc import Sequence
from math import isclose, isfinite

from openoil.domain.bingham_rheology import (
    FannReading, SHEAR_RATE_PER_RPM, STRESS_PA_PER_DIAL,
)


def calculate(readings: Sequence[FannReading]) -> dict:
    """Use the lowest-RPM viscosity; require every other ratio to agree.

    Relative tolerance 1e-9 is numerical roundoff allowance only (no absolute
    tolerance, noise allowance, regression, or automatic model selection).
    One observation derives viscosity under an assumption, not proof of behavior.
    """
    if isinstance(readings, (str, bytes)):
        raise ValueError("readings must not be empty")
    try:
        source = tuple(readings)
    except TypeError:
        raise ValueError("readings must not be empty") from None
    if not source:
        raise ValueError("readings must not be empty")
    def finite_number(value: object) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return isfinite(value)
        except OverflowError:
            return False

    for reading in source:
        if not isinstance(reading, FannReading):
            raise ValueError("each reading must be a FannReading")
        for value, positive, message in [
            (reading.rpm, True, "rpm must be positive and finite"),
            (reading.dial, False, "dial must be nonnegative and finite"),
        ]:
            if (not finite_number(value) or value < 0 or (positive and value == 0)):
                raise ValueError(message)
    if len({r.rpm for r in source}) != len(source):
        raise ValueError("rpm readings must be unique")

    points, viscosities = [], []
    for reading in sorted(source, key=lambda r: r.rpm):
        rate = SHEAR_RATE_PER_RPM * reading.rpm
        stress = STRESS_PA_PER_DIAL * reading.dial
        if not isfinite(rate) or rate <= 0 or not isfinite(stress) or (reading.dial > 0 and stress == 0):
            raise ValueError("calculation outside finite numerical range")
        viscosity = stress / rate
        if not isfinite(viscosity) or (reading.dial > 0 and viscosity == 0):
            raise ValueError("calculation outside finite numerical range")
        viscosities.append(viscosity)
        points.append(dict(rpm=reading.rpm, dial=reading.dial,
                           shear_rate_s_inv=rate, shear_stress_pa=stress))
    viscosity = viscosities[0]
    if any(not isclose(value, viscosity, rel_tol=1e-9, abs_tol=0) for value in viscosities[1:]):
        raise ValueError("readings are inconsistent with a Newtonian model")
    return {
        "readings": points,
        "dynamic_viscosity": {"quantity": "dynamic_viscosity", "value": viscosity, "unit": "Pa·s"},
        "model_id": "openoil.rheology.fann-newtonian",
        "model_version": "1.0.0", "input_schema_version": "1", "result_schema_version": "1",
        "applicability": {
            "status": "supported",
            "assumptions": "Newtonian tau = mu * gamma, zero yield stress; constant viscosity. "
                           "Lowest-RPM ratio defines mu; all ratios agree within relative 1e-9, absolute 0.",
            "limitations": "One reading assumes, not establishes, Newtonian behavior. No noise fit, "
                           "hydraulic coupling or persistence; no WellPlan/vendor parity; "
                           "not validated for field decisions.",
        },
    }
