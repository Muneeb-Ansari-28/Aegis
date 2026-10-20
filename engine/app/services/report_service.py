"""Report generation service using Jinja2 templates and xhtml2pdf."""
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.agents.reporting_agent import ReportingAgent
from app.core.database import SessionLocal
from app.core.paths import get_app_data_dir
from app.models.entities import FindingEntity, ScanEntity, ScanTurnEntity, TargetEntity
from app.schemas.report import ReportData, ReportFinding, ReportMeta

logger = logging.getLogger(__name__)


class ReportService:
    """Compiles assessment scan findings into styled executive PDF reports."""

    @classmethod
    def get_template_dir(cls) -> Path:
        """Resolve the path to the report templates directory."""
        return Path(__file__).resolve().parent.parent / "templates"

    @classmethod
    def get_report_path(cls, scan_id: str) -> Path:
        """Resolve the output destination path for a scan's PDF report."""
        reports_dir = get_app_data_dir() / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir / f"report_{scan_id}.pdf"

    @classmethod
    async def compile_report_data(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> ReportData:
        """
        Extract scan, target, turn, and finding data to compile a ReportData schema.

        Args:
            scan_id: UUID of the assessment scan.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            Fully populated ReportData model.

        Raises:
            LookupError: If the scan does not exist.
        """
        with session_factory() as session:
            scan = session.get(ScanEntity, scan_id)
            if scan is None:
                raise LookupError(f"Scan '{scan_id}' was not found.")

            if scan.status in ("QUEUED", "RUNNING"):
                raise ValueError(
                    f"Scan '{scan_id}' is still in progress ({scan.status}). Wait for completion before generating a report."
                )

            target: Optional[TargetEntity] = None
            if scan.target_id:
                target = session.get(TargetEntity, scan.target_id)

            target_name = target.name if target else "Target System"
            target_url = target.url if target else "http://localhost"

            turns = (
                session.query(ScanTurnEntity)
                .filter(ScanTurnEntity.scan_id == scan_id)
                .order_by(ScanTurnEntity.turn_index)
                .all()
            )
            turn_map = {turn.id: turn for turn in turns}

            finding_entities = (
                session.query(FindingEntity)
                .filter(FindingEntity.scan_id == scan_id)
                .order_by(FindingEntity.created_at)
                .all()
            )

            report_findings: List[ReportFinding] = []
            for f in finding_entities:
                linked_turn = turn_map.get(f.turn_id)
                report_findings.append(
                    ReportFinding(
                        id=f.id,
                        category=f.category,
                        severity=f.severity,
                        confidence=f.confidence,
                        description=f.description,
                        remediation=f.remediation,
                        turn_index=linked_turn.turn_index if linked_turn else 1,
                        prompt=linked_turn.prompt if linked_turn else "(Evidence prompt not recorded)",
                        response=linked_turn.response if linked_turn else "(Evidence response not recorded)",
                        latency_ms=linked_turn.latency_ms if linked_turn else 0,
                        strategy=linked_turn.strategy if linked_turn else None,
                    )
                )

            return ReportingAgent.compile_report_data(
                scan_id=scan.id,
                target_name=target_name,
                target_url=target_url,
                category=scan.category or "LLM07",
                scan_status=scan.status or "COMPLETED",
                started_at=scan.created_at.isoformat() if scan.created_at else None,
                completed_at=scan.completed_at.isoformat() if scan.completed_at else None,
                turns_count=len(turns),
                findings=report_findings,
            )

    @classmethod
    async def generate_report(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> Path:
        """
        Compile and render a styled PDF report for a scan, saving it to user AppData.

        Args:
            scan_id: UUID of the assessment scan.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            Path to the generated PDF file.

        Raises:
            LookupError: If the scan does not exist.
            RuntimeError: If PDF compilation fails.
        """
        report_data = await cls.compile_report_data(scan_id, session_factory=session_factory)

        def format_timestamp(ts: Optional[str]) -> str:
            if not ts:
                return "N/A"
            try:
                dt = datetime.fromisoformat(ts)
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                if len(ts) >= 19 and "T" in ts:
                    return f"{ts[:10]} {ts[11:19]} UTC"
                return ts

        template_dir = cls.get_template_dir()
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["format_timestamp"] = format_timestamp
        env.globals["format_timestamp"] = format_timestamp
        template = env.get_template("report.html")
        rendered_html = template.render(report=report_data)

        out_path = cls.get_report_path(scan_id)

        with open(out_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_file)
            if pisa_status.err:
                raise RuntimeError(
                    f"xhtml2pdf encountered errors rendering PDF for scan '{scan_id}': {pisa_status.err}"
                )

        logger.info("Successfully generated PDF report for scan '%s' at %s", scan_id, out_path)
        return out_path

    @classmethod
    async def get_report_metadata(cls, scan_id: str) -> ReportMeta:
        """
        Inspect generated PDF report file on disk and return metadata.

        Args:
            scan_id: UUID of the assessment scan.

        Returns:
            ReportMeta schema with file size and timestamp.

        Raises:
            LookupError: If the report file does not exist on disk.
        """
        report_path = cls.get_report_path(scan_id)
        if not report_path.exists():
            raise LookupError(f"Report for scan '{scan_id}' has not been generated yet.")

        stat = report_path.stat()
        file_bytes = report_path.read_bytes()
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        return ReportMeta(
            scan_id=scan_id,
            report_path=str(report_path),
            file_size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            sha256=sha256,
        )
