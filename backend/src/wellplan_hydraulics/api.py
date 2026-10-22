"""Local JSON API for the independent simplified hydraulics model."""
from contextlib import asynccontextmanager
from dataclasses import asdict
import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from wellplan_hydraulics.physics import Section, calculate
from wellplan_hydraulics.storage import CaseStore


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

    def result(self):
        try:
            return asdict(calculate(
                [Section(**section.model_dump()) for section in self.sections],
                self.density_kg_m3, self.viscosity_pa_s, self.flow_m3_s))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None


def create_app(db_path=None):
    """Create an app backed by a file; schema initialization occurs at startup."""
    store = CaseStore(db_path if db_path is not None
                      else os.environ.get('WELLPLAN_DB_PATH', 'cases.sqlite3'))

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        yield

    app = FastAPI(title='Independent simplified hydraulics', lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo untrusted input, nonfinite floats, or framework-specific errors.
        detail = ('invalid case id' if request.url.path.startswith('/api/cases/')
                  else 'invalid request body')
        return JSONResponse(status_code=422, content={'detail': detail})

    @app.post('/api/calculate')
    def calculate_case(inputs: CalculationInput):
        return inputs.result()

    @app.post('/api/cases', status_code=201)
    def save_case(inputs: CalculationInput):
        result = inputs.result()  # Reject before any storage operation or ID allocation.
        return store.save(inputs.model_dump(), result)

    @app.get('/api/cases')
    def list_cases():
        return store.list()

    @app.get('/api/cases/{case_id}')
    def get_case(case_id: int):
        if not 1 <= case_id <= 9223372036854775807:
            raise HTTPException(status_code=422, detail='invalid case id')
        record = store.get(case_id)
        if record is None:
            raise HTTPException(status_code=404, detail='case not found')
        return record

    return app


app = create_app()
