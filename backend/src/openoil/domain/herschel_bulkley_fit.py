"""OpenOil bounded, discrete-exponent conventional HB fit (not vendor parity)."""
from collections.abc import Sequence
from math import exp, fsum, isfinite, log, sqrt

from openoil.domain.bingham_rheology import FannReading, SHEAR_RATE_PER_RPM, STRESS_PA_PER_DIAL


def _number(value: object) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        return False


def _profile(n: float, rates: list[float], stresses: list[float]):
    """Exact two-variable nonnegative least squares at fixed n; normalized units."""
    z = [exp(n * r) for r in rates]
    zm, ym = fsum(z) / len(z), fsum(stresses) / len(z)
    variance = fsum((x-zm)**2 for x in z)
    slope = fsum((x-zm)*(y-ym) for x, y in zip(z, stresses)) / variance
    candidates = [(ym, 0.0), (0.0, max(0.0, fsum(x*y for x, y in zip(z, stresses)) / fsum(x*x for x in z)))]
    intercept = ym - slope * zm
    if intercept >= 0 and slope >= 0:
        candidates.append((intercept, slope))
    return min((fsum((a+b*x-y)**2 for x, y in zip(z, stresses))/len(z), a, b, n)
               for a, b in candidates)


def calculate(readings: Sequence[FannReading]) -> dict:
    """Fit all observations; see research/rheology/herschel-bulkley-fit-boundary.md."""
    try:
        source = tuple(readings) if not isinstance(readings, (str, bytes)) else ()
    except TypeError:
        source = ()
    if not 3 <= len(source) <= 1000:
        raise ValueError('readings must contain 3 to 1000 Fann readings')
    for p in source:
        if not isinstance(p, FannReading):
            raise ValueError('each reading must be a FannReading')
        if not _number(p.rpm) or p.rpm <= 0:
            raise ValueError('rpm must be positive and finite')
        if not _number(p.dial) or p.dial < 0:
            raise ValueError('dial must be nonnegative and finite')
    if len({p.rpm for p in source}) != len(source):
        raise ValueError('rpm readings must be unique')
    source = sorted(source, key=lambda p: p.rpm)
    rates = [p.rpm * SHEAR_RATE_PER_RPM for p in source]
    stresses = [p.dial * STRESS_PA_PER_DIAL for p in source]
    if not all(isfinite(v) for v in rates + stresses) or min(rates) <= 0:
        raise ValueError('calculation outside finite numerical range')
    if (rates[-1] - rates[0]) / rates[-1] <= 1e-6:
        raise ValueError('degenerate readings: insufficient RPM separation')
    scale = max(stresses)
    if scale == 0 or (scale - min(stresses)) / scale <= 1e-10:
        raise ValueError('degenerate readings: insufficient stress variation')
    # Log differences avoid underflow in a direct min/max ratio.
    logs = [log(r) - log(rates[-1]) for r in rates]
    y = [s / scale for s in stresses]
    try:
        profiles = [_profile((10+i)/200, logs, y) for i in range(391)]
        objective, a, b, n = min(profiles, key=lambda fit: (fit[0], fit[3]))
        if b <= 1e-10:
            raise ValueError('degenerate readings: no identifiable positive consistency')
        tau0 = a * scale
        consistency = exp(log(b) + log(scale) - n*log(rates[-1]))
        points = []
        for p, rate, stress, r in zip(source, rates, stresses, logs):
            predicted = (a + b*exp(n*r)) * scale
            points.append(dict(rpm=p.rpm, dial=p.dial, shear_rate_s_inv=rate,
                               shear_stress_pa=stress, predicted_stress_pa=predicted,
                               residual_pa=predicted-stress))
        sse = fsum(p['residual_pa']**2 for p in points)
        rmse = sqrt(sse / len(points))
        if (consistency <= 0 or not all(isfinite(v) for v in [tau0, consistency, sse, rmse]
                + [v for p in points for v in p.values()])):
            raise ValueError('calculation outside finite numerical range')
    except (OverflowError, ZeroDivisionError):
        raise ValueError('calculation outside finite numerical range') from None
    near = [fit[3] for fit in profiles if fit[0] <= objective + 1e-6]
    return {
        'parameters': {
            'yield_stress_pa': {'value': tau0, 'unit': 'Pa'},
            'consistency_index_pa_s_n': {'value': consistency, 'unit': 'Pa·s^n'},
            'flow_behavior_index': {'value': n, 'unit': '1'},
        },
        'points': points,
        'diagnostics': {
            'objective': 'unweighted stress least squares; discrete n grid',
            'sse_pa2': sse, 'rmse_pa': rmse,
            'max_abs_residual_pa': max(abs(p['residual_pa']) for p in points),
            'evaluations': 391, 'n_min': 0.05, 'n_max': 2.0, 'n_step': 0.005,
            'near_optimal_n_min': min(near), 'near_optimal_n_max': max(near),
            'near_optimal_count': len(near), 'at_n_bound': n in (0.05, 2.0),
            'warning': 'Finite grid selection is not proof of uniqueness. Near-optimal range is not a confidence interval; boundary optima may be truncated.',
        },
        'model_id': 'openoil.rheology.fann-herschel-bulkley-fit',
        'model_version': '1.0.0', 'input_schema_version': '1', 'result_schema_version': '1',
        'applicability': {
            'status': 'supported',
            'assumptions': 'Conventional HB tau=tau0+K*gamma^n; all readings equally weighted in SI stress; nonnegative tau0 and K; bounded discrete positive n.',
            'limitations': 'No WellPlan/vendor parity, generalized-HB fitting, hydraulic coupling or field validation. Grid resolution is not parameter accuracy; three points provide no residual degrees of freedom.',
        },
    }
