"""
Aegis Engine Main Entry Point
FastAPI engine and packaged sidecar runner on port :8765.
"""

import uvicorn
import asyncio
import sys
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.paths import ensure_app_dirs

def main() -> None:
    setup_logging()
    ensure_app_dirs()
    settings = get_settings()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run(
        "app.api.v1.router:app",
        host=settings.HOST,
        port=settings.PORT,
        # Uvicorn's Windows reload process uses a selector loop, which cannot
        # launch Playwright's browser subprocess.
        reload=settings.DEBUG and sys.platform != "win32",
        log_level="info",
    )

if __name__ == "__main__":
    main()
