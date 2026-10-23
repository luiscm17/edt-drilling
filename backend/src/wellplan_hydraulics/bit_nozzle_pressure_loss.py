"""Stateless documented bit/nozzle contribution, not a system pressure model.

Source/derivation: research/hydraulics/004-bit-nozzle-pressure-loss.md.
The installed-help velocity relation retains literal 2.96 via nozzle_velocity;
the pressure relation in coherent SI is rho * v**2 / (2 * Cd**2).
No vendor runtime or proprietary implementation is used.
"""
from math import isfinite

from wellplan_hydraulics.nozzle_velocity import calculate as nozzle_velocity


CD = 0.95


def calculate(density_kg_m3: float, flow_m3_s: float,
              total_nozzle_area_m2: float) -> dict:
    """Return one independently identified pressure loss and model provenance.

    Inputs describe steady incompressible single-phase flow with constant
    density and a supplied total effective nozzle area (sum of nozzle areas).
    No aggregate with the base hydraulics model is defined.
    """
    for name, value in (('density_kg_m3', density_kg_m3),
                        ('flow_m3_s', flow_m3_s),
                        ('total_nozzle_area_m2', total_nozzle_area_m2)):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value <= 0):
            raise ValueError(f'{name} must be positive and finite')
    velocity = nozzle_velocity(flow_m3_s, total_nozzle_area_m2)
    try:
        pressure_pa = density_kg_m3 * velocity ** 2 / (2 * CD ** 2)
    except OverflowError:
        raise ValueError('calculation outside finite numerical range') from None
    if not isfinite(pressure_pa) or pressure_pa <= 0:
        raise ValueError('calculation outside finite numerical range')
    return {
        'pressure_loss': {'quantity': 'bit_nozzle_pressure_loss',
                          'value': pressure_pa, 'unit': 'Pa'},
        'model_id': 'openoil.hydraulics.documented-bit-nozzle-pressure-loss',
        'model_version': '1.0.0',
        'input_schema_version': '1', 'result_schema_version': '1',
        'coefficient': {'symbol': 'Cd', 'value': CD, 'unit': '1',
                        'selection': 'fixed documented coefficient'},
        'applicability': {
            'status': 'supported',
            'assumptions': 'Steady incompressible single-phase flow; constant density and effective total nozzle area.',
            'limitations': 'One contribution only; no aggregate or standpipe pressure. Excludes system optimization, parasitic/tool-joint and surface losses, erosion, non-Newtonian, compressible, transient and multiphase effects. Not validated for field decisions.',
        },
    }
