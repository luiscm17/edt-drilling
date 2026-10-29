"""Stable SI evaluation of supplied conventional Herschel–Bulkley parameters."""

from collections.abc import Sequence
from math import exp, isfinite, log, log1p
from sys import float_info


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def calculate(
    yield_stress_pa: float,
    consistency_index_pa_s_n: float,
    flow_behavior_index: float,
    shear_rates_s_inv: Sequence[float],
) -> dict:
    """Evaluate τ = τ₀ + Kγⁿ for explicit SI parameters, without a Fann fit."""
    for name, value in (
        ('flow_behavior_index', flow_behavior_index),
    ):
        if not _finite_number(value) or value <= 0:
            raise ValueError(f'{name} must be positive and finite')
    for name, value in (
        ('yield_stress_pa', yield_stress_pa),
        ('consistency_index_pa_s_n', consistency_index_pa_s_n),
    ):
        if not _finite_number(value) or value < 0:
            raise ValueError(f'{name} must be nonnegative and finite')

    if isinstance(shear_rates_s_inv, (str, bytes)):
        raise ValueError('shear_rates_s_inv must not be empty')
    try:
        rates = tuple(shear_rates_s_inv)
    except TypeError:
        raise ValueError('shear_rates_s_inv must not be empty') from None
    if not rates:
        raise ValueError('shear_rates_s_inv must not be empty')
    if any(not _finite_number(rate) or rate < 0 for rate in rates):
        raise ValueError('shear rates must be nonnegative and finite')
    if len(set(rates)) != len(rates):
        raise ValueError('shear rates must be unique')

    try:
        log_yield = log(yield_stress_pa) if yield_stress_pa > 0 else float('-inf')
        curve = []
        for rate in sorted(rates):
            if consistency_index_pa_s_n == 0 or rate == 0:
                stress = yield_stress_pa
            else:
                try:
                    power = rate ** flow_behavior_index
                    direct_stress = yield_stress_pa + consistency_index_pa_s_n * power
                except OverflowError:
                    direct_stress = float('inf')
                if isfinite(direct_stress) and (direct_stress > 0 or yield_stress_pa > 0):
                    stress = direct_stress
                else:
                    log_power = log(consistency_index_pa_s_n) + flow_behavior_index * log(rate)
                    if log_yield == float('-inf'):
                        log_stress = log_power
                    else:
                        high, low = max(log_yield, log_power), min(log_yield, log_power)
                        log_stress = high + log1p(exp(low - high))
                    if log_stress > log(float_info.max):
                        raise ValueError('calculation outside finite numerical range')
                    stress = exp(log_stress)
            if not isfinite(stress) or (stress == 0 and consistency_index_pa_s_n > 0 and rate > 0):
                raise ValueError('calculation outside finite numerical range')
            curve.append({'shear_rate_s_inv': rate, 'shear_stress_pa': stress})
    except (OverflowError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == 'calculation outside finite numerical range':
            raise
        raise ValueError('calculation outside finite numerical range') from None

    return {
        'parameters': {
            'yield_stress_pa': {'value': yield_stress_pa, 'unit': 'Pa'},
            'consistency_index_pa_s_n': {
                'value': consistency_index_pa_s_n, 'unit': 'Pa·s^n',
            },
            'flow_behavior_index': {'value': flow_behavior_index, 'unit': '1'},
        },
        'curve': curve,
        'model_id': 'openoil.rheology.herschel-bulkley-parametric',
        'model_version': '1.0.0',
        'input_schema_version': '1',
        'result_schema_version': '1',
        'applicability': {
            'status': 'supported',
            'assumptions': 'Parametric evaluation of supplied SI values; no parameters are fitted.',
            'limitations': ('No Fann fit, hydraulic integration or saved case; '
                            'not validated for field decisions.'),
        },
    }
