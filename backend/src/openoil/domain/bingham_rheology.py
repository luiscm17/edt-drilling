"""Independent Bingham study derived from rotational-viscometer readings."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

LB_FT2_TO_PA = 47.88025898033584
SHEAR_RATE_PER_RPM = 1.70333
STRESS_LB_FT2_PER_DIAL = 0.01065
STRESS_PA_PER_DIAL = STRESS_LB_FT2_PER_DIAL * LB_FT2_TO_PA


@dataclass(frozen=True)
class FannReading:
    rpm: float
    dial: float


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
    )


def calculate(readings: Sequence[FannReading]) -> dict:
    """Calculate SI Bingham parameters and transformed observation points.

    Plastic viscosity is the line slope between the 300 and 600 rpm readings;
    yield point follows 2*theta_300 - theta_600. Extra readings are sorted for
    display but are not used in a fit. This standalone study has no persistence
    or hydraulic coupling.
    """
    if isinstance(readings, (str, bytes)):
        raise ValueError("readings must contain at least 300 and 600 rpm")
    try:
        source = tuple(readings)
    except TypeError:
        raise ValueError("readings must contain at least 300 and 600 rpm") from None
    if len(source) < 2:
        raise ValueError("readings must contain at least 300 and 600 rpm")

    checked: list[FannReading] = []
    for reading in source:
        if not isinstance(reading, FannReading):
            raise ValueError("each reading must be a FannReading")
        if not _finite_number(reading.rpm) or reading.rpm <= 0:
            raise ValueError("rpm must be positive and finite")
        if not _finite_number(reading.dial) or reading.dial < 0:
            raise ValueError("dial must be nonnegative and finite")
        checked.append(reading)

    rpms = [reading.rpm for reading in checked]
    if len(set(rpms)) != len(rpms):
        raise ValueError("rpm readings must be unique")
    by_rpm = {reading.rpm: reading for reading in checked}
    if 300 not in by_rpm or 600 not in by_rpm:
        raise ValueError("readings must include 300 and 600 rpm")

    points = []
    for reading in sorted(checked, key=lambda item: item.rpm):
        shear_rate = SHEAR_RATE_PER_RPM * reading.rpm
        shear_stress = STRESS_PA_PER_DIAL * reading.dial
        if not isfinite(shear_rate) or not isfinite(shear_stress):
            raise ValueError("calculation outside finite numerical range")
        points.append(
            {
                "rpm": reading.rpm,
                "dial": reading.dial,
                "shear_rate_s_inv": shear_rate,
                "shear_stress_pa": shear_stress,
            }
        )

    reading_300 = by_rpm[300]
    reading_600 = by_rpm[600]
    rate_delta = SHEAR_RATE_PER_RPM * (reading_600.rpm - reading_300.rpm)
    stress_300 = STRESS_PA_PER_DIAL * reading_300.dial
    stress_600 = STRESS_PA_PER_DIAL * reading_600.dial
    plastic_viscosity = (stress_600 - stress_300) / rate_delta
    yield_dial = 2 * reading_300.dial - reading_600.dial
    yield_point = STRESS_PA_PER_DIAL * yield_dial
    if not isfinite(plastic_viscosity) or not isfinite(yield_point):
        raise ValueError("calculation outside finite numerical range")
    if plastic_viscosity < 0:
        raise ValueError("derived plastic viscosity must be nonnegative")
    if yield_dial < 0:
        raise ValueError("derived yield point must be nonnegative")

    return {
        "readings": points,
        "plastic_viscosity": {
            "quantity": "plastic_viscosity",
            "value": plastic_viscosity,
            "unit": "Pa·s",
        },
        "yield_point": {
            "quantity": "yield_point",
            "value": yield_point,
            "unit": "Pa",
        },
        "model_id": "openoil.rheology.fann-bingham",
        "model_version": "1.0.0",
        "input_schema_version": "1",
        "result_schema_version": "1",
        "applicability": {
            "status": "supported",
            "assumptions": (
                "Bingham plastic model derived from 300 and 600 rpm readings; "
                "additional readings are transformed observations."
            ),
            "limitations": (
                "Additional readings are not included in a regression. Excludes "
                "gel strengths, other rheology models and hydraulics integration; "
                "not validated for field decisions."
            ),
        },
    }
