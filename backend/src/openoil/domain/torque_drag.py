"""Independent quasi-static, straight, uniformly inclined torque/drag study.

SI units are encoded in field names; coefficients are dimensionless and inclination
is degrees from vertical. Sections run surface to bottom. OD is a closed-pipe
buoyancy envelope, not an open-ended/internal-fluid model. The bottom is freely
suspended: no bit load. Outputs are section contributions, not interface tensions.

Only buoyant weight and simple Coulomb contact are included. No doglegs, bending,
buckling, tension-dependent contact, axial/rotation coupling, viscous drag,
clearance, hardware or field-suitability prediction. This does not claim parity
with any external solver or operational safety model. See research/torque-drag/boundary.md.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

GRAVITY_M_S2 = 9.80665
_RANGE_ERROR = "calculation outside finite numerical range"


@dataclass(frozen=True)
class Section:
    length_m: float
    pipe_od_m: float
    air_weight_n_m: float


@dataclass(frozen=True)
class SectionResult:
    submerged_weight_n_m: float
    axial_gravity_n: float
    normal_force_n: float
    axial_friction_n: float
    rotational_friction_n: float
    pickup_tension_n: float
    slackoff_tension_n: float
    rotating_torque_nm: float


@dataclass(frozen=True)
class Result:
    sections: tuple[SectionResult, ...]
    pickup_tension_n: float
    slackoff_tension_n: float
    rotating_torque_nm: float


def _finite_input(name: str, value: float) -> None:
    try:
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number")


def _finite_derived(*values: float) -> None:
    if any(not math.isfinite(value) for value in values):
        raise ValueError(_RANGE_ERROR)


def calculate(
    sections: Sequence[Section],
    inclination_deg: float,
    density_kg_m3: float,
    axial_friction_coefficient: float,
    rotational_friction_coefficient: float,
) -> Result:
    """Return immutable, dataclasses.asdict/JSON-serializable SI results.

    Inputs must be finite numbers (not booleans). Length, OD and air weight must
    be positive; density and friction coefficients may be zero but not negative.
    Inclination must satisfy 0 <= angle < 90 degrees. Every section must retain
    positive submerged weight and nonnegative slackoff tension. Unsupported or
    unrepresentable cases raise ValueError without printing or mutating inputs.
    """
    for name, value in [
        ("inclination_deg", inclination_deg),
        ("density_kg_m3", density_kg_m3),
        ("axial_friction_coefficient", axial_friction_coefficient),
        ("rotational_friction_coefficient", rotational_friction_coefficient),
    ]:
        _finite_input(name, value)
    if not 0 <= inclination_deg < 90:
        raise ValueError("inclination_deg must satisfy 0 <= angle < 90")
    for name, value in [
        ("density_kg_m3", density_kg_m3),
        ("axial_friction_coefficient", axial_friction_coefficient),
        ("rotational_friction_coefficient", rotational_friction_coefficient),
    ]:
        if value < 0:
            raise ValueError(f"{name} must be nonnegative")
    sections = tuple(sections)
    if not sections:
        raise ValueError("sections must not be empty")
    for section in sections:
        for name in ["length_m", "pipe_od_m", "air_weight_n_m"]:
            value = getattr(section, name)
            _finite_input(name, value)
            if value <= 0:
                raise ValueError(f"{name} must be positive")

    try:
        angle = math.radians(inclination_deg)
        cosine, sine = math.cos(angle), math.sin(angle)
        rows = []
        for section in sections:
            area = math.pi * section.pipe_od_m**2 / 4
            submerged = section.air_weight_n_m - density_kg_m3 * GRAVITY_M_S2 * area
            _finite_derived(area, submerged)
            if submerged <= 0:
                raise ValueError("submerged weight must be positive in every section")
            weight = submerged * section.length_m
            gravity, normal = weight * cosine, weight * sine
            axial = axial_friction_coefficient * normal
            rotational = rotational_friction_coefficient * normal
            pickup, slackoff = gravity + axial, gravity - axial
            torque = rotational * (section.pipe_od_m / 2)
            _finite_derived(
                weight, gravity, normal, axial, rotational, pickup, slackoff, torque
            )
            if slackoff < 0:
                raise ValueError(
                    "slackoff tension must be nonnegative in every section"
                )
            rows.append(
                SectionResult(
                    submerged,
                    gravity,
                    normal,
                    axial,
                    rotational,
                    pickup,
                    slackoff,
                    torque,
                )
            )
        pickup = sum(row.pickup_tension_n for row in rows)
        slackoff = sum(row.slackoff_tension_n for row in rows)
        torque = sum(row.rotating_torque_nm for row in rows)
        _finite_derived(pickup, slackoff, torque)
        return Result(tuple(rows), pickup, slackoff, torque)
    except OverflowError:
        raise ValueError(_RANGE_ERROR) from None
