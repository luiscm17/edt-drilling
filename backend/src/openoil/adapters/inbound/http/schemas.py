"""Strict HTTP payloads and transport-to-core conversion helpers."""

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from openoil.application.hydraulics import (
    CaseInput,
    HydraulicsApplication,
    UnsupportedInput,
)
from openoil.domain.physics import Section


class FannReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    rpm: float = Field(gt=0)
    dial: float = Field(ge=0)


class BinghamFannRheologyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    readings: list[FannReadingInput] = Field(min_length=2)


class BinghamFannReadingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    rpm: float
    dial: float = Field(ge=0)
    shear_rate_s_inv: float = Field(gt=0)
    shear_stress_pa: float = Field(ge=0)


class PlasticViscosityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    quantity: Literal["plastic_viscosity"]
    value: float = Field(ge=0)
    unit: Literal["Pa·s"]


class YieldPointResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    quantity: Literal["yield_point"]
    value: float = Field(ge=0)
    unit: Literal["Pa"]


class BinghamFannApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["supported"]
    assumptions: str
    limitations: str


class BinghamFannRheologyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    readings: list[BinghamFannReadingResult]
    plastic_viscosity: PlasticViscosityResult
    yield_point: YieldPointResult
    model_id: Literal["openoil.rheology.fann-bingham"]
    model_version: Literal["1.0.0"]
    input_schema_version: Literal["1"]
    result_schema_version: Literal["1"]
    applicability: BinghamFannApplicability


class NozzleVelocityInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    flow_m3_s: float = Field(gt=0)
    total_nozzle_area_m2: float = Field(gt=0)


class NozzleVelocityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    velocity_m_s: float = Field(gt=0)


class BitNozzlePressureLossInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    density_kg_m3: float = Field(gt=0)
    flow_m3_s: float = Field(gt=0)
    total_nozzle_area_m2: float = Field(gt=0)


class BitNozzlePressureQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    quantity: Literal["bit_nozzle_pressure_loss"]
    value: float = Field(gt=0)
    unit: Literal["Pa"]


class BitNozzleCoefficient(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    symbol: Literal["Cd"]
    value: float = Field(ge=0.95, le=0.95)
    unit: Literal["1"]
    selection: Literal["fixed documented coefficient"]


class BitNozzleApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["supported"]
    assumptions: str
    limitations: str


class BitNozzlePressureLossResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    pressure_loss: BitNozzlePressureQuantity
    model_id: Literal["openoil.hydraulics.documented-bit-nozzle-pressure-loss"]
    model_version: Literal["1.0.0"]
    input_schema_version: Literal["1"]
    result_schema_version: Literal["1"]
    coefficient: BitNozzleCoefficient
    applicability: BitNozzleApplicability


class SectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    length_m: float
    pipe_id_m: float
    pipe_od_m: float
    hole_id_m: float


class CalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    sections: list[SectionInput]
    density_kg_m3: float
    viscosity_pa_s: float
    flow_m3_s: float

    def to_case(self):
        return CaseInput(
            tuple(Section(**section.model_dump()) for section in self.sections),
            self.density_kg_m3,
            self.viscosity_pa_s,
            self.flow_m3_s,
        )

    def result(self):
        # Preserve the existing Python helper as well as the HTTP contract.
        try:
            return HydraulicsApplication.calculate(self.to_case())
        except UnsupportedInput as error:
            raise HTTPException(status_code=422, detail=str(error)) from None


class TorqueDragSectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    length_m: float
    pipe_od_m: float
    air_weight_n_m: float


class TorqueDragInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    sections: list[TorqueDragSectionInput]
    inclination_deg: float
    density_kg_m3: float
    axial_friction_coefficient: float
    rotational_friction_coefficient: float


class TorqueDragTotals(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    pickup_tension_n: float
    slackoff_tension_n: float
    rotating_torque_nm: float


class TorqueDragSectionResult(TorqueDragTotals):
    submerged_weight_n_m: float
    axial_gravity_n: float
    normal_force_n: float
    axial_friction_n: float
    rotational_friction_n: float


class TorqueDragResult(TorqueDragTotals):
    sections: list[TorqueDragSectionResult]
