"""Scan Orchestration Service."""
import uuid
from app.schemas.scan import ScanCreate, ScanResponse, ScanStatusResponse

class ScanService:
    _scans = {}

    @classmethod
    async def start_scan(cls, data: ScanCreate) -> ScanResponse:
        scan_id = str(uuid.uuid4())
        resp = ScanResponse(
            scan_id=scan_id,
            target_id=data.target_id,
            status="RUNNING",
            category=data.category,
            budget=data.budget,
        )
        cls._scans[scan_id] = resp
        return resp

    @classmethod
    async def get_scan_status(cls, scan_id: str) -> ScanStatusResponse:
        return ScanStatusResponse(
            scan_id=scan_id,
            status="RUNNING",
            current_attempt=1,
            budget=10,
            exploited=False
        )

    @classmethod
    async def stop_scan(cls, scan_id: str):
        if scan_id in cls._scans:
            cls._scans[scan_id].status = "STOPPED"
        return {"status": "stopped", "scan_id": scan_id}
