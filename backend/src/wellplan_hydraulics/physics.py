"""Independent simplified vertical-well model. See backend/README.md for limits."""
from dataclasses import dataclass
import math
from typing import Sequence

GRAVITY_M_S2 = 9.80665
_RANGE_ERROR = 'calculation outside finite numerical range'


@dataclass(frozen=True)
class Section:
    length_m: float
    pipe_id_m: float
    pipe_od_m: float
    hole_id_m: float


@dataclass(frozen=True)
class PassageResult:
    velocity_m_s: float
    reynolds: float
    regime: str
    darcy_factor: float
    pressure_loss_pa: float


@dataclass(frozen=True)
class SectionResult:
    pipe: PassageResult
    annulus: PassageResult


@dataclass(frozen=True)
class Result:
    sections: tuple[SectionResult, ...]
    depth_m: float
    pipe_friction_pa: float
    annular_friction_pa: float
    hydrostatic_pa: float
    bottomhole_annular_pa: float
    ecd_kg_m3: float


def _positive(name, value):
    try:
        valid = (isinstance(value, (int, float)) and not isinstance(value, bool)
                 and math.isfinite(value) and value > 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{name} must be a positive finite number')


def _finite_positive(*values):
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError(_RANGE_ERROR)


def _passage(length, diameter, area, density, viscosity, flow, annular_shape=None):
    _finite_positive(diameter, area)
    velocity = flow / area
    reynolds = density * velocity * diameter / viscosity
    _finite_positive(velocity, reynolds)
    if reynolds < 2300:
        regime = 'laminar'
        if annular_shape is None:
            factor = 64 / reynolds
            loss = factor * (length / diameter) * density * velocity**2 / 2
        else:
            _finite_positive(annular_shape)
            loss = 128 * viscosity * length * flow / (math.pi * annular_shape)
            factor = 2 * loss * diameter / (density * velocity**2 * length)
    elif 4000 <= reynolds <= 100000:
        regime = 'turbulent'
        factor = 0.3164 / reynolds**0.25
        loss = factor * (length / diameter) * density * velocity**2 / 2
    else:
        raise ValueError('Reynolds number outside supported regimes')
    _finite_positive(factor, loss)
    return PassageResult(velocity, reynolds, regime, factor, loss)


def calculate(sections: Sequence[Section], density_kg_m3: float,
              viscosity_pa_s: float, flow_m3_s: float) -> Result:
    """Return SI friction magnitudes, bottom annular gauge pressure and ECD.

    No printing, persistence or input mutation. Invalid inputs raise ValueError.
    Section lengths equal vertical depths; surface annular gauge pressure is zero.
    """
    for name, value in [('density_kg_m3', density_kg_m3),
                        ('viscosity_pa_s', viscosity_pa_s), ('flow_m3_s', flow_m3_s)]:
        _positive(name, value)
    sections = tuple(sections)
    if not sections:
        raise ValueError('sections must not be empty')
    for section in sections:
        for name in ['length_m', 'pipe_id_m', 'pipe_od_m', 'hole_id_m']:
            _positive(name, getattr(section, name))
        if not section.pipe_id_m < section.pipe_od_m < section.hole_id_m:
            raise ValueError('geometry requires pipe_id_m < pipe_od_m < hole_id_m')
        if section.pipe_od_m / section.hole_id_m > 0.8:
            raise ValueError('annular diameter ratio must be <= 0.8')
    try:
        rows = []
        for section in sections:
            inner, outer = section.pipe_od_m, section.hole_id_m
            # Exact fully developed concentric Newtonian laminar annulus solution.
            shape = outer**4 - inner**4 - (outer**2 - inner**2)**2 / math.log(outer / inner)
            pipe = _passage(section.length_m, section.pipe_id_m,
                            math.pi * section.pipe_id_m**2 / 4,
                            density_kg_m3, viscosity_pa_s, flow_m3_s)
            annulus = _passage(section.length_m, outer - inner,
                               math.pi * (outer**2 - inner**2) / 4,
                               density_kg_m3, viscosity_pa_s, flow_m3_s, shape)
            rows.append(SectionResult(pipe, annulus))
        depth = sum(s.length_m for s in sections)
        pipe_loss = sum(row.pipe.pressure_loss_pa for row in rows)
        annular_loss = sum(row.annulus.pressure_loss_pa for row in rows)
        hydrostatic = density_kg_m3 * GRAVITY_M_S2 * depth
        bottomhole = hydrostatic + annular_loss
        ecd = bottomhole / (GRAVITY_M_S2 * depth)
        _finite_positive(depth, pipe_loss, annular_loss, hydrostatic, bottomhole, ecd)
        return Result(tuple(rows), depth, pipe_loss, annular_loss,
                      hydrostatic, bottomhole, ecd)
    except (OverflowError, ZeroDivisionError):
        raise ValueError(_RANGE_ERROR) from None
