"""
Aegis Engine Main Entry Point
FastAPI engine and packaged sidecar runner on port :8765.
"""

import uvicorn
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.paths import ensure_app_dirs

def main() -> None:
    setup_logging()
    ensure_app_dirs()
    settings = get_settings()
    uvicorn.run(
        "app.api.v1.router:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

if __name__ == "__main__":
    main()
