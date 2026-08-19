"""FastAPI app entry point: wires routers, DB session, and startup config."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db.session import init_db
from .routers import intake


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB schema init on startup; nothing to tear down on shutdown."""
    await init_db()
    yield


app = FastAPI(title="SautiCivic Bridge", lifespan=lifespan)
app.include_router(intake.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
