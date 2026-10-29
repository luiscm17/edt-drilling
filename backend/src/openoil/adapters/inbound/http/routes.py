"""Inbound HTTP adapter: invoke use cases and serialize their results."""

from dataclasses import asdict

from fastapi import APIRouter

from openoil.adapters.inbound.http.schemas import (
    BinghamFannRheologyInput,
    BinghamFannRheologyResult,
    BitNozzlePressureLossInput,
    BitNozzlePressureLossResult,
    CalculationInput,
    GeneralizedHBInput,
    GeneralizedHBResult,
    GelBreakPressureInput,
    GelBreakPressureResult,
    HerschelBulkleyFitInput,
    HerschelBulkleyFitResult,
    HerschelBulkleyInput,
    HerschelBulkleyResult,
    NewtonianFannRheologyInput,
    NewtonianFannRheologyResult,
    NozzleVelocityInput,
    NozzleVelocityResult,
    PowerLawRheologyResult,
    TorqueDragInput,
    TorqueDragResult,
)
from openoil.application import studies
from openoil.domain import (
    bingham_rheology,
    gel_break_pressure,
    herschel_bulkley_rheology,
    power_law_rheology,
    torque_drag,
)


def register_routes(app, service):
    router = APIRouter(prefix="/api/v1")

    @router.post(
        "/rheology/gel-break-pressure/calculate",
        response_model=GelBreakPressureResult,
    )
    def calculate_gel_break_pressure(inputs: GelBreakPressureInput):
        """Independent 3 rpm zero-second gel study; string interior only.

        Lengths/inner diameters in m; gel stress and component/total pressure in Pa.
        Excludes annulus, timed gels and tool joints; no persistence or WellPlan parity.
        """
        return studies.calculate_gel_break_pressure(
            inputs.dial_3_rpm,
            [gel_break_pressure.Component(**component.model_dump())
             for component in inputs.components],
        )

    @router.post(
        "/rheology/newtonian/calculate",
        response_model=NewtonianFannRheologyResult,
    )
    def calculate_newtonian_rheology(inputs: NewtonianFannRheologyInput):
        """Stateless zero-yield Newtonian assumption; no vendor parity or field validation."""
        return studies.calculate_newtonian_rheology([
            bingham_rheology.FannReading(**reading.model_dump())
            for reading in inputs.readings
        ])

    @router.post(
        "/rheology/bingham/calculate",
        response_model=BinghamFannRheologyResult,
    )
    def calculate_bingham_rheology(inputs: BinghamFannRheologyInput):
        readings = [
            bingham_rheology.FannReading(**reading.model_dump())
            for reading in inputs.readings
        ]
        return studies.calculate_bingham_rheology(readings)

    @router.post(
        "/rheology/herschel-bulkley-fit/calculate",
        response_model=HerschelBulkleyFitResult,
    )
    def calculate_herschel_bulkley_fit(inputs: HerschelBulkleyFitInput):
        """Calculate-only bounded conventional fit; diagnostics are not accuracy or uniqueness certification."""
        return studies.calculate_herschel_bulkley_fit([
            bingham_rheology.FannReading(**p.model_dump()) for p in inputs.readings
        ])

    @router.post(
        "/rheology/herschel-bulkley/calculate",
        response_model=HerschelBulkleyResult,
    )
    def calculate_herschel_bulkley_rheology(inputs: HerschelBulkleyInput):
        return studies.calculate_herschel_bulkley_rheology(**inputs.model_dump())

    @router.post(
        "/rheology/generalized-hb/calculate",
        response_model=GeneralizedHBResult,
    )
    def calculate_generalized_hb_rheology(inputs: GeneralizedHBInput):
        return studies.calculate_generalized_hb_rheology(**inputs.model_dump())

    @router.post(
        "/rheology/power-law/calculate",
        response_model=PowerLawRheologyResult,
    )
    def calculate_power_law_rheology(inputs: BinghamFannRheologyInput):
        readings = [
            power_law_rheology.FannReading(**reading.model_dump())
            for reading in inputs.readings
        ]
        return studies.calculate_power_law_rheology(readings)

    @router.post(
        "/bit-nozzle-pressure-loss/calculate",
        response_model=BitNozzlePressureLossResult,
    )
    def calculate_bit_nozzle_pressure_loss(inputs: BitNozzlePressureLossInput):
        return studies.calculate_bit_nozzle_pressure_loss(**inputs.model_dump())

    @router.post("/nozzle-velocity/calculate", response_model=NozzleVelocityResult)
    def calculate_nozzle_velocity(inputs: NozzleVelocityInput):
        velocity = studies.calculate_nozzle_velocity(
            inputs.flow_m3_s, inputs.total_nozzle_area_m2
        )
        return {"velocity_m_s": velocity}

    @router.post("/torque-drag/calculate", response_model=TorqueDragResult)
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

    @router.post("/calculate")
    def calculate_case(inputs: CalculationInput):
        return service.calculate(inputs.to_case())

    @router.post("/cases", status_code=201)
    def save_case(inputs: CalculationInput):
        return service.save(inputs.to_case())

    @router.get("/cases")
    def list_cases():
        return service.list()

    @router.get("/cases/{case_id}")
    def get_case(case_id: int):
        return service.load(case_id)

    app.include_router(router)
