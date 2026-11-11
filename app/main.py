
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.models  # noqa: F401 (registers tables)
from app.api.router import api_router
from app.core.database import Base, engine
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Quick start only. For real projects, switch to Alembic migrations.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="TicketFlow",
    version="1.0.0",
    lifespan=lifespan,
)

# Register global error handlers
app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "message": "TicketFlow API is running successfully",
    }
