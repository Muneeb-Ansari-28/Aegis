"""Findings query and aggregation service for scan results."""
import logging
from typing import List, Optional

from app.agents.risk_scorer import RiskScorer
from app.core.database import SessionLocal
from app.models.entities import FindingEntity, ScanEntity, ScanTurnEntity, TargetEntity
from app.schemas.finding import FindingDetail, FindingResponse, FindingsSummary

logger = logging.getLogger(__name__)

# Severity deductions used for deterministic risk grade calculation
SEVERITY_PENALTIES = {
    "CRITICAL": 40.0,
    "HIGH": 25.0,
    "MEDIUM": 15.0,
    "LOW": 5.0,
    "INFO": 0.0,
}


class FindingsService:
    """Service for querying persisted security findings and calculating risk metrics."""

    @classmethod
    async def get_findings_by_scan(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> List[FindingResponse]:
        """
        Retrieve all persisted security findings for a scan ordered by creation time.

        Args:
            scan_id: UUID of the scan.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            List of FindingResponse models.

        Raises:
            LookupError: If the scan does not exist.
        """
        with session_factory() as session:
            scan = session.get(ScanEntity, scan_id)
            if scan is None:
                raise LookupError(f"Scan '{scan_id}' was not found.")

            findings = (
                session.query(FindingEntity)
                .filter(FindingEntity.scan_id == scan_id)
                .order_by(FindingEntity.created_at)
                .all()
            )

            return [
                FindingResponse(
                    id=row.id,
                    scan_id=row.scan_id,
                    turn_id=row.turn_id,
                    category=row.category,
                    severity=row.severity,
                    confidence=row.confidence,
                    description=row.description,
                    remediation=row.remediation,
                    created_at=row.created_at.isoformat() if row.created_at else None,
                )
                for row in findings
            ]

    @classmethod
    async def get_finding_detail(
        cls, finding_id: str, session_factory=SessionLocal
    ) -> FindingDetail:
        """
        Retrieve a single finding with its linked turn evidence.

        Args:
            finding_id: UUID of the finding.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            FindingDetail containing finding attributes and prompt/response evidence.

        Raises:
            LookupError: If the finding or its linked turn does not exist.
        """
        with session_factory() as session:
            finding = session.get(FindingEntity, finding_id)
            if finding is None:
                raise LookupError(f"Finding '{finding_id}' was not found.")

            turn = session.get(ScanTurnEntity, finding.turn_id)
            if turn is None:
                raise LookupError(
                    f"Turn evidence for finding '{finding_id}' (turn '{finding.turn_id}') was not found."
                )

            return FindingDetail(
                id=finding.id,
                scan_id=finding.scan_id,
                turn_id=finding.turn_id,
                category=finding.category,
                severity=finding.severity,
                confidence=finding.confidence,
                description=finding.description,
                remediation=finding.remediation,
                created_at=finding.created_at.isoformat() if finding.created_at else None,
                prompt=turn.prompt,
                response=turn.response,
                turn_index=turn.turn_index,
                latency_ms=turn.latency_ms or 0,
                strategy=turn.strategy,
            )

    @classmethod
    async def get_findings_summary(
        cls, scan_id: str, session_factory=SessionLocal
    ) -> FindingsSummary:
        """
        Calculate aggregate finding counts by severity and overall risk grade for a scan.

        Args:
            scan_id: UUID of the scan.
            session_factory: Injectable SQLAlchemy session factory.

        Returns:
            FindingsSummary with severity distribution and computed risk grade.

        Raises:
            LookupError: If the scan does not exist.
        """
        with session_factory() as session:
            scan = session.get(ScanEntity, scan_id)
            if scan is None:
                raise LookupError(f"Scan '{scan_id}' was not found.")

            target: Optional[TargetEntity] = None
            if scan.target_id:
                target = session.get(TargetEntity, scan.target_id)

            findings = (
                session.query(FindingEntity)
                .filter(FindingEntity.scan_id == scan_id)
                .all()
            )

            by_severity = {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0,
            }
            total_penalty = 0.0

            for f in findings:
                sev = f.severity.upper() if f.severity else "INFO"
                by_severity[sev] = by_severity.get(sev, 0) + 1
                total_penalty += SEVERITY_PENALTIES.get(sev, 10.0)

            risk_grade = RiskScorer.compute_grade(total_penalty)

            return FindingsSummary(
                scan_id=scan.id,
                total_findings=len(findings),
                by_severity=by_severity,
                risk_grade=risk_grade,
                scan_status=scan.status,
                scan_category=scan.category,
                target_name=target.name if target else None,
                target_url=target.url if target else None,
                started_at=scan.created_at.isoformat() if scan.created_at else None,
                completed_at=scan.completed_at.isoformat() if scan.completed_at else None,
            )
