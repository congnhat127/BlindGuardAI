"""BlindGuard AI - Web cai dat tai xe (Tier 1).

Mot process FastAPI lam ba viec: REST API, luong MJPEG, va phuc vu SPA tinh.
Chay duoc tren laptop o che do mock (khong can camera / GPS) va tren Jetson o
che do that chi bang cach doi BLINDGUARD_DEVICE_BACKEND.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .adapters.cameras import get_camera_source
from .api import routes_cameras, routes_geometry, routes_profiles, routes_system
from .core.settings import settings

DESCRIPTION = """
Cong cu cai dat va cang chinh tai xe cho he thong vung mu dong BlindGuard AI.

**Che do thiet bi**: `mock` sinh khung hinh tu dung mo hinh camera (K + [R|T]) nen
toan bo quy trinh cang chinh chay duoc khi chua co phan cung. `jetson` doc camera
va GPS that. Frontend giong nhau o ca hai che do.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        get_camera_source().release()
    except Exception:
        pass


app = FastAPI(
    title="BlindGuard AI - Local Setup Web",
    version="0.1.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.dev_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_system.router, prefix="/api")
app.include_router(routes_geometry.router, prefix="/api")
app.include_router(routes_profiles.router, prefix="/api")
app.include_router(routes_cameras.router, prefix="/api")


@app.get("/api")
def api_root() -> dict:
    return {
        "service": "blindguard-local-setup",
        "version": app.version,
        "device_backend": settings.device_backend,
        "docs": "/api/docs",
    }


# --- SPA -------------------------------------------------------------------
_static = Path(settings.static_dir)
if _static.is_dir():
    assets = _static / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """Tra index.html cho moi duong dan khong phai API (client-side routing)."""
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = _static / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")

else:

    @app.get("/", include_in_schema=False)
    def no_frontend() -> JSONResponse:
        return JSONResponse(
            {
                "detail": "Chua build frontend.",
                "huong_dan": [
                    "cd 7_Local_Setup_Web/frontend",
                    "npm install",
                    "npm run dev   (che do phat trien, mo http://localhost:5173)",
                    "npm run build (sinh ban tinh vao backend/static de chay tren Jetson)",
                ],
                "api_docs": "/api/docs",
            },
            status_code=503,
        )
