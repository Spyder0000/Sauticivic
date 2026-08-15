"""FastAPI app entry point: wires routers, DB session, and startup config."""
from fastapi import FastAPI

from .routers import intake

app = FastAPI(title="SautiCivic Bridge")
app.include_router(intake.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
