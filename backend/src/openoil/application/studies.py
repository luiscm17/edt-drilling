"""Calculate-only use cases; no repository access or transport dependencies."""

from collections.abc import Sequence

from openoil.application.hydraulics import UnsupportedInput
from openoil.domain import (
    bit_nozzle_pressure_loss,
    nozzle_velocity,
    torque_drag,
)


def calculate_bit_nozzle_pressure_loss(
    density_kg_m3: float, flow_m3_s: float, total_nozzle_area_m2: float
) -> dict:
    try:
        return bit_nozzle_pressure_loss.calculate(
            density_kg_m3, flow_m3_s, total_nozzle_area_m2
        )
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_nozzle_velocity(flow_m3_s: float, total_nozzle_area_m2: float) -> float:
    try:
        return nozzle_velocity.calculate(flow_m3_s, total_nozzle_area_m2)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_torque_drag(
    sections: Sequence[torque_drag.Section],
    inclination_deg: float,
    density_kg_m3: float,
    axial_friction_coefficient: float,
    rotational_friction_coefficient: float,
) -> torque_drag.Result:
    try:
        return torque_drag.calculate(
            sections,
            inclination_deg,
            density_kg_m3,
            axial_friction_coefficient,
            rotational_friction_coefficient,
        )
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None
