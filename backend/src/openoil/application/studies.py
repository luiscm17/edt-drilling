"""Calculate-only use cases; no repository access or transport dependencies."""

from collections.abc import Sequence

from openoil.application.hydraulics import UnsupportedInput
from openoil.domain import (
    bingham_rheology,
    bit_nozzle_pressure_loss,
    generalized_hb_rheology,
    gel_break_pressure,
    herschel_bulkley_rheology,
    herschel_bulkley_fit,
    newtonian_rheology,
    nozzle_velocity,
    power_law_rheology,
    torque_drag,
)


def calculate_gel_break_pressure(
    dial_3_rpm: float, components: Sequence[gel_break_pressure.Component],
) -> dict:
    try:
        return gel_break_pressure.calculate(dial_3_rpm, components)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_newtonian_rheology(
    readings: Sequence[bingham_rheology.FannReading],
) -> dict:
    try:
        return newtonian_rheology.calculate(readings)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_bingham_rheology(
    readings: Sequence[bingham_rheology.FannReading],
) -> dict:
    try:
        return bingham_rheology.calculate(readings)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_generalized_hb_rheology(**parameters) -> dict:
    try:
        return generalized_hb_rheology.calculate(**parameters)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_herschel_bulkley_fit(readings: Sequence[bingham_rheology.FannReading]) -> dict:
    try:
        return herschel_bulkley_fit.calculate(readings)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_herschel_bulkley_rheology(**parameters) -> dict:
    try:
        return herschel_bulkley_rheology.calculate(**parameters)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


def calculate_power_law_rheology(
    readings: Sequence[power_law_rheology.FannReading],
) -> dict:
    try:
        return power_law_rheology.calculate(readings)
    except ValueError as error:
        raise UnsupportedInput(str(error)) from None


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
