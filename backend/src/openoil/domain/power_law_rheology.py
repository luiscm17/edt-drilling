"""Independent two-point Power Law study; no hydraulic or persistence coupling."""

from collections.abc import Sequence
from math import exp, isfinite, log

from openoil.domain.bingham_rheology import (
    FannReading,
    SHEAR_RATE_PER_RPM,
    STRESS_PA_PER_DIAL,
)


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def calculate(readings: Sequence[FannReading]) -> dict:
    """Derive SI n and K only from positive 300/600 RPM Fann dial readings."""
    if isinstance(readings, (str, bytes)):
        raise ValueError('readings must contain at least 300 and 600 rpm')
    try:
        source = tuple(readings)
    except TypeError:
        raise ValueError('readings must contain at least 300 and 600 rpm') from None
    if len(source) < 2:
        raise ValueError('readings must contain at least 300 and 600 rpm')
    for item in source:
        if not isinstance(item, FannReading):
            raise ValueError('each reading must be a FannReading')
        if not _finite_number(item.rpm) or item.rpm <= 0:
            raise ValueError('rpm must be positive and finite')
        if not _finite_number(item.dial) or item.dial < 0:
            raise ValueError('dial must be nonnegative and finite')
    if len({item.rpm for item in source}) != len(source):
        raise ValueError('rpm readings must be unique')
    by_rpm = {item.rpm: item for item in source}
    if 300 not in by_rpm or 600 not in by_rpm:
        raise ValueError('readings must include 300 and 600 rpm')
    dial300, dial600 = by_rpm[300].dial, by_rpm[600].dial
    if dial300 <= 0 or dial600 <= 0:
        raise ValueError('300 and 600 rpm dials must be positive')
    if dial600 <= dial300:
        raise ValueError('600 rpm dial must exceed 300 rpm dial')

    points = []
    for item in sorted(source, key=lambda reading: reading.rpm):
        rate = SHEAR_RATE_PER_RPM * item.rpm
        stress = STRESS_PA_PER_DIAL * item.dial
        if not isfinite(rate) or not isfinite(stress) or rate <= 0:
            raise ValueError('calculation outside finite numerical range')
        points.append({'rpm': item.rpm, 'dial': item.dial,
                       'shear_rate_s_inv': rate, 'shear_stress_pa': stress})

    # Subtract logs rather than dividing readings: even a finite ratio can overflow.
    n = (log(dial600) - log(dial300)) / log(2)
    stress300 = STRESS_PA_PER_DIAL * dial300
    try:
        k = exp(log(stress300) - n * log(SHEAR_RATE_PER_RPM * 300))
        curve = [
            {'rpm': point['rpm'], 'shear_rate_s_inv': point['shear_rate_s_inv'],
             'shear_stress_pa': k * point['shear_rate_s_inv'] ** n}
            for point in points
        ]
    except (OverflowError, ValueError, ZeroDivisionError):
        raise ValueError('calculation outside finite numerical range') from None
    if not isfinite(n) or not isfinite(k) or k <= 0 or any(
        not isfinite(point['shear_stress_pa']) or point['shear_stress_pa'] <= 0
        for point in curve
    ):
        raise ValueError('calculation outside finite numerical range')

    return {
        'readings': points,
        'model_curve': curve,
        'flow_behavior_index': {'quantity': 'flow_behavior_index', 'value': n, 'unit': '1'},
        'consistency_index': {'quantity': 'consistency_index', 'value': k, 'unit': 'Pa·s^n'},
        'model_id': 'openoil.rheology.fann-power-law',
        'model_version': '1.0.0',
        'input_schema_version': '1',
        'result_schema_version': '1',
        'applicability': {
            'status': 'supported',
            'assumptions': ('Two-point Power Law model from positive 300 and 600 rpm '
                            'Fann readings; other readings are observations only.'),
            'limitations': ('No regression, gels, temperature/pressure prediction or '
                            'hydraulics integration; not validated for field decisions.'),
        },
    }
