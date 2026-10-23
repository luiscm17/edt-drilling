"""Composition root and ASGI entrypoint; concrete adapters are selected here."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from openoil.adapters.config.settings import Settings
from openoil.adapters.inbound.http.errors import register_error_handlers
from openoil.adapters.inbound.http.routes import register_routes
from openoil.adapters.outbound.case_store import CaseStore
from openoil.application.hydraulics import HydraulicsApplication


def create_app(db_path=None):
    """Create an app backed by a file; schema initialization occurs at startup."""
    settings = Settings()
    store = CaseStore(db_path if db_path is not None else settings.database_path)
    service = HydraulicsApplication(store)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title='Independent simplified hydraulics', lifespan=lifespan)
    register_error_handlers(app)
    register_routes(app, service)
    return app


app = create_app()
