"""Stable SI evaluation of supplied generalized Herschel–Bulkley parameters."""

from collections.abc import Sequence
from math import exp, isfinite, log, log1p


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def calculate(
    reference_stress_pa: float,
    zero_shear_stress_pa: float,
    high_shear_viscosity_pa_s: float,
    stress_exponent: float,
    rate_exponent: float,
    shear_rates_s_inv: Sequence[float],
) -> dict:
    """Evaluate the documented dimensionless relation, without a Fann fit."""
    for name, value in (
        ('reference_stress_pa', reference_stress_pa),
        ('stress_exponent', stress_exponent),
        ('rate_exponent', rate_exponent),
    ):
        if not _finite_number(value) or value <= 0:
            raise ValueError(f'{name} must be positive and finite')
    for name, value in (
        ('zero_shear_stress_pa', zero_shear_stress_pa),
        ('high_shear_viscosity_pa_s', high_shear_viscosity_pa_s),
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
        log_reference = log(reference_stress_pa)
        a = (stress_exponent * (log(zero_shear_stress_pa) - log_reference)
             if zero_shear_stress_pa > 0 else float('-inf'))
        curve = []
        for rate in sorted(rates):
            b = (rate_exponent * (log(high_shear_viscosity_pa_s) + log(rate) - log_reference)
                 if high_shear_viscosity_pa_s > 0 and rate > 0 else float('-inf'))
            if b == float('-inf'):
                stress = zero_shear_stress_pa
            elif a == float('-inf'):
                stress = exp(log_reference + b / stress_exponent)
            else:
                high, low = max(a, b), min(a, b)
                stress = exp(log_reference + (high + log1p(exp(low - high))) / stress_exponent)
            if not isfinite(stress) or (stress == 0 and b != float('-inf')):
                raise ValueError('calculation outside finite numerical range')
            curve.append({'shear_rate_s_inv': rate, 'shear_stress_pa': stress})
    except (OverflowError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == 'calculation outside finite numerical range':
            raise
        raise ValueError('calculation outside finite numerical range') from None

    return {
        'parameters': {
            'reference_stress_pa': {'value': reference_stress_pa, 'unit': 'Pa'},
            'zero_shear_stress_pa': {'value': zero_shear_stress_pa, 'unit': 'Pa'},
            'high_shear_viscosity_pa_s': {'value': high_shear_viscosity_pa_s, 'unit': 'Pa·s'},
            'stress_exponent': {'value': stress_exponent, 'unit': '1'},
            'rate_exponent': {'value': rate_exponent, 'unit': '1'},
        },
        'curve': curve,
        'model_id': 'openoil.rheology.generalized-herschel-bulkley-parametric',
        'model_version': '1.0.0',
        'input_schema_version': '1',
        'result_schema_version': '1',
        'applicability': {
            'status': 'supported',
            'assumptions': 'Parametric evaluation of supplied SI values; no parameters are fitted.',
            'limitations': ('No Fann fit, foam-pressure model, hydraulic integration or saved case; '
                            'not validated for field decisions.'),
        },
    }
