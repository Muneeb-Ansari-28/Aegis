"""PDF Report Generation, Metadata, and Download Endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.report import ReportMeta
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{scan_id}/pdf")
async def get_report_pdf(scan_id: str):
    """
    Download the generated PDF assessment report for a scan.
    If the report has not yet been generated, it is automatically generated.

    Args:
        scan_id: The UUID of the assessment scan.

    Returns:
        FileResponse containing application/pdf stream.

    Raises:
        HTTPException: 404 if scan not found, 409 if scan in progress, 500 on generation error.
    """
    try:
        pdf_path = ReportService.get_report_path(scan_id)
        if not pdf_path.exists():
            pdf_path = await ReportService.generate_report(scan_id)
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            filename=f"aegis_report_{scan_id[:8]}.pdf",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to deliver PDF report for scan '%s': %s", scan_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}") from exc


@router.get("/{scan_id}/meta", response_model=ReportMeta)
async def get_report_metadata(scan_id: str) -> ReportMeta:
    """
    Retrieve metadata regarding a scan's generated PDF report.

    Args:
        scan_id: The UUID of the assessment scan.

    Returns:
        ReportMeta schema with file size and timestamp.

    Raises:
        HTTPException: 404 if report has not yet been generated.
    """
    try:
        return await ReportService.get_report_metadata(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get report metadata for scan '%s': %s", scan_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{scan_id}/generate", response_model=ReportMeta)
async def generate_report(scan_id: str) -> ReportMeta:
    """
    Explicitly trigger or refresh PDF report generation for a completed scan.

    Args:
        scan_id: The UUID of the assessment scan.

    Returns:
        ReportMeta describing the newly generated PDF report.

    Raises:
        HTTPException: 404 if scan not found, 409 if in progress, 500 on generation error.
    """
    try:
        await ReportService.generate_report(scan_id)
        return await ReportService.get_report_metadata(scan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to trigger report generation for scan '%s': %s", scan_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}") from exc
