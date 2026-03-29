from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.backend.api.routes.auth import router as auth_router
from app.backend.api.routes.categories import router as categories_router
from app.backend.api.routes.materials import router as materials_router
from app.backend.api.routes.search import router as search_router
from config import settings


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="Geotech Knowledge Base",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(materials_router)
app.include_router(search_router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "Geotech Knowledge Base API",
        "mini_app": settings.mini_app_url,
    }


@app.get("/app")
async def serve_mini_app() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
