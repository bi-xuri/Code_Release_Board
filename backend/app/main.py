from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.public import router as public_router
from app.core.config import settings
from app.db.init_db import init_db
from app.tasks.scheduler import start_scheduler, stop_scheduler


app = FastAPI(title="Code Release Board", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router, prefix="/api/public", tags=["public"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
