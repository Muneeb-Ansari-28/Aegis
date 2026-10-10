"""ReportLab & Jinja2 PDF Compilation Service."""
from pathlib import Path
from app.core.paths import get_app_data_dir

class ReportService:
    @classmethod
    async def generate_report(cls, scan_id: str) -> Path:
        out_path = get_app_data_dir() / "reports" / f"report_{scan_id}.pdf"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Touch file if not existing for stub
        if not out_path.exists():
            out_path.write_bytes(b"%PDF-1.4 sample stub")
        return out_path
