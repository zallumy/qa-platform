"""FastAPI app entrypoint — mounts routers."""
from __future__ import annotations
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, files, reports, admin
from app.storage import ensure_bucket

app = FastAPI(title="Print QA Check API", version="1.0.0")

_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_bucket()


@app.get("/health")
def health():
    return {"status": "ok"}
