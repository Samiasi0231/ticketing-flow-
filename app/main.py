from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  (registers tables)
from app.api.router import api_router
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Quick start only. For real projects, switch to Alembic migrations.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="TicketFlow", version="1.0.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
