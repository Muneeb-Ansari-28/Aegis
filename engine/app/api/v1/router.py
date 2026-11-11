from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import health, targets, scans, findings, reports, proxy, websocket, assistant, security
from app.core.database import Base, engine
from app.models import entities as _entities
from app.core.paths import ensure_app_dirs
from app.services.scan_service import ScanService
from app.core.api_auth import LocalAPIAuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the declared SQLAlchemy tables and recover any interrupted scans on startup."""
    ensure_app_dirs()
    Base.metadata.create_all(bind=engine)
    ScanService.recover_interrupted_scans()
    yield


app = FastAPI(
    title="Aegis Red-Teaming Engine",
    version="0.1.0",
    description="Automated red-teaming engine and MCP controller for LLM vulnerability assessments",
    lifespan=lifespan,
)

# CORS middleware: Restricted to loopback origins and packaged desktop renderers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LocalAPIAuthMiddleware)

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(targets.router, prefix="/api/v1/targets", tags=["Targets"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["Scans"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["Findings"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(proxy.router, prefix="/api/v1/proxy", tags=["Proxy (Later)"])
app.include_router(websocket.router, prefix="/api/v1", tags=["Telemetry"])
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["Assistant"])
app.include_router(security.router, prefix="/api/v1/security", tags=["Security"])
