"""FastAPI App Router mounting all V1 endpoints."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import health, targets, scans, findings, reports, proxy, websocket

app = FastAPI(
    title="Aegis Red-Teaming Engine",
    version="0.1.0",
    description="Automated red-teaming engine and MCP controller for LLM vulnerability assessments",
)

# CORS middleware for local desktop Electron renderer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(targets.router, prefix="/api/v1/targets", tags=["Targets"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["Scans"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["Findings"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(proxy.router, prefix="/api/v1/proxy", tags=["Proxy (Later)"])
app.include_router(websocket.router, prefix="/api/v1", tags=["Telemetry"])
