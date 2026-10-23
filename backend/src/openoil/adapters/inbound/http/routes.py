"""Inbound HTTP adapter: invoke use cases and serialize their results."""

from dataclasses import asdict

from openoil.application import studies
from openoil.domain import torque_drag
from openoil.adapters.inbound.http.schemas import (
    BitNozzlePressureLossInput,
    BitNozzlePressureLossResult,
    CalculationInput,
    NozzleVelocityInput,
    NozzleVelocityResult,
    TorqueDragInput,
    TorqueDragResult,
    VersionedCalculationInput,
)


def register_routes(app, service):
    @app.post(
        "/api/bit-nozzle-pressure-loss/calculate",
        response_model=BitNozzlePressureLossResult,
    )
    def calculate_bit_nozzle_pressure_loss(inputs: BitNozzlePressureLossInput):
        return studies.calculate_bit_nozzle_pressure_loss(**inputs.model_dump())

    @app.post("/api/nozzle-velocity/calculate", response_model=NozzleVelocityResult)
    def calculate_nozzle_velocity(inputs: NozzleVelocityInput):
        velocity = studies.calculate_nozzle_velocity(
            inputs.flow_m3_s, inputs.total_nozzle_area_m2
        )
        return {"velocity_m_s": velocity}

    @app.post("/api/torque-drag/calculate", response_model=TorqueDragResult)
    def calculate_torque_drag(inputs: TorqueDragInput):
        result = studies.calculate_torque_drag(
            sections=[
                torque_drag.Section(**section.model_dump())
                for section in inputs.sections
            ],
            inclination_deg=inputs.inclination_deg,
            density_kg_m3=inputs.density_kg_m3,
            axial_friction_coefficient=inputs.axial_friction_coefficient,
            rotational_friction_coefficient=inputs.rotational_friction_coefficient,
        )
        body = asdict(result)
        body["sections"] = list(body["sections"])
        return body

    @app.post("/api/calculate")
    def calculate_case(inputs: CalculationInput):
        return service.calculate(inputs.to_case())

    @app.post("/api/cases", status_code=201)
    def save_case(inputs: CalculationInput):
        return service.save(inputs.to_case())

    @app.get("/api/cases")
    def list_cases():
        return service.list()

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: int):
        return service.load(case_id)

    @app.post("/api/v2/calculate")
    def calculate_versioned(inputs: VersionedCalculationInput):
        return service.calculate_versioned(inputs.input.to_case())

    @app.post("/api/v2/cases", status_code=201)
    def save_versioned(inputs: VersionedCalculationInput):
        return service.save_versioned(inputs.input.to_case())

    @app.get("/api/v2/cases")
    def list_versioned():
        return service.list_versioned()

    @app.get("/api/v2/cases/{case_id}")
    def get_versioned(case_id: int):
        return service.load_versioned(case_id)
