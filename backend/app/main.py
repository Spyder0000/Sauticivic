from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.session import init_db
from .routers import intake


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB schema init on startup; nothing to tear down on shutdown."""
    await init_db()
    yield


app = FastAPI(title="SautiCivic Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

