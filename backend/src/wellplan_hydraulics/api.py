"""Local JSON API for the independent simplified hydraulics model."""
from contextlib import asynccontextmanager
from dataclasses import asdict
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wellplan_hydraulics.application import (
    CaseInput, HydraulicsApplication, InvalidCaseId, MissingCase, UnsupportedInput,
)
from wellplan_hydraulics.physics import Section, calculate
from wellplan_hydraulics.storage import CaseStore
from wellplan_hydraulics import nozzle_velocity, torque_drag


class NozzleVelocityInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    flow_m3_s: float = Field(gt=0)
    total_nozzle_area_m2: float = Field(gt=0)


class NozzleVelocityResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    velocity_m_s: float = Field(gt=0)


class SectionInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    length_m: float
    pipe_id_m: float
    pipe_od_m: float
    hole_id_m: float


class CalculationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    sections: list[SectionInput]
    density_kg_m3: float
    viscosity_pa_s: float
    flow_m3_s: float

    def to_case(self):
        return CaseInput(
            tuple(Section(**section.model_dump()) for section in self.sections),
            self.density_kg_m3, self.viscosity_pa_s, self.flow_m3_s)

    def result(self):
        # Preserve the existing Python helper as well as the HTTP contract.
        try:
            return HydraulicsApplication.calculate(self.to_case())
        except UnsupportedInput as error:
            raise HTTPException(status_code=422, detail=str(error)) from None


class VersionedCalculationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    input_schema_version: Literal['1']
    input: CalculationInput


class TorqueDragSectionInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    length_m: float
    pipe_od_m: float
    air_weight_n_m: float


class TorqueDragInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    sections: list[TorqueDragSectionInput]
    inclination_deg: float
    density_kg_m3: float
    axial_friction_coefficient: float
    rotational_friction_coefficient: float


class TorqueDragTotals(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
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


def create_app(db_path=None):
    """Create an app backed by a file; schema initialization occurs at startup."""
    store = CaseStore(db_path if db_path is not None
                      else os.environ.get('WELLPLAN_DB_PATH', 'cases.sqlite3'))
    service = HydraulicsApplication(store)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        yield

    app = FastAPI(title='Independent simplified hydraulics', lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo untrusted input, nonfinite floats, or framework-specific errors.
        detail = ('invalid case id' if request.url.path.startswith(('/api/cases/', '/api/v2/cases/'))
                  else 'invalid request body')
        return JSONResponse(status_code=422, content={'detail': detail})

    @app.exception_handler(UnsupportedInput)
    @app.exception_handler(InvalidCaseId)
    async def invalid_case(request, error):
        return JSONResponse(status_code=422, content={'detail': str(error)})

    @app.exception_handler(MissingCase)
    async def missing_case(request, error):
        return JSONResponse(status_code=404, content={'detail': str(error)})

    @app.post('/api/nozzle-velocity/calculate', response_model=NozzleVelocityResult)
    def calculate_nozzle_velocity(inputs: NozzleVelocityInput):
        try:
            velocity = nozzle_velocity.calculate(
                inputs.flow_m3_s, inputs.total_nozzle_area_m2)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return {'velocity_m_s': velocity}

    @app.post('/api/torque-drag/calculate', response_model=TorqueDragResult)
    def calculate_torque_drag(inputs: TorqueDragInput):
        try:
            result = torque_drag.calculate(
                sections=[torque_drag.Section(**section.model_dump())
                          for section in inputs.sections],
                inclination_deg=inputs.inclination_deg,
                density_kg_m3=inputs.density_kg_m3,
                axial_friction_coefficient=inputs.axial_friction_coefficient,
                rotational_friction_coefficient=inputs.rotational_friction_coefficient,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        body = asdict(result)
        body['sections'] = list(body['sections'])
        return body

    @app.post('/api/calculate')
    def calculate_case(inputs: CalculationInput):
        return service.calculate(inputs.to_case())

    @app.post('/api/cases', status_code=201)
    def save_case(inputs: CalculationInput):
        return service.save(inputs.to_case())

    @app.get('/api/cases')
    def list_cases():
        return service.list()

    @app.get('/api/cases/{case_id}')
    def get_case(case_id: int):
        return service.load(case_id)

    @app.post('/api/v2/calculate')
    def calculate_versioned(inputs: VersionedCalculationInput):
        return service.calculate_versioned(inputs.input.to_case())

    @app.post('/api/v2/cases', status_code=201)
    def save_versioned(inputs: VersionedCalculationInput):
        return service.save_versioned(inputs.input.to_case())

    @app.get('/api/v2/cases')
    def list_versioned():
        return service.list_versioned()

    @app.get('/api/v2/cases/{case_id}')
    def get_versioned(case_id: int):
        return service.load_versioned(case_id)

    return app


app = create_app()
