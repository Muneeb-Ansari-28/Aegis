"""PDF Report Generation and Download Endpoints."""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.services.report_service import ReportService

router = APIRouter()

@router.get("/{scan_id}/pdf")
async def get_report_pdf(scan_id: str):
    pdf_path = await ReportService.generate_report(scan_id)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"report_{scan_id}.pdf")
