"""Executive Summary and Vulnerability Narrative Generator."""
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

from app.agents.risk_scorer import RiskScorer
from app.agents.planner.category_catalog import get_category_definition
from app.schemas.report import ReportData, ReportFinding

logger = logging.getLogger(__name__)


def _category_label(category_id: str) -> str:
    definition = get_category_definition(category_id)
    return f"{definition.id}:2026 {definition.name}" if definition else category_id


class ReportingAgent:
    """Generates structured report data and deterministic executive summaries."""

    @classmethod
    def generate_executive_summary(
        cls,
        target_name: str,
        category: str,
        total_turns: int,
        total_findings: int,
        severity_breakdown: Dict[str, int],
        risk_grade: float,
        scan_status: str,
        estimated_cost_usd: Optional[float] = None,
        total_tokens: Optional[int] = None,
        category_results: Optional[List[Dict[str, object]]] = None,
    ) -> str:
        """
        Generate a professional, deterministic executive summary narrative.

        Args:
            target_name: Name of assessed target.
            category: Assessment vulnerability category (e.g. LLM07).
            total_turns: Number of interaction turns completed.
            total_findings: Total verified findings.
            severity_breakdown: Dict of findings count by severity.
            risk_grade: 0-100 score computed by RiskScorer.
            scan_status: Lifecycle status of the scan (COMPLETED, STOPPED, FAILED).

        Returns:
            Executive summary narrative string.
        """
        critical_count = severity_breakdown.get("CRITICAL", 0)
        high_count = severity_breakdown.get("HIGH", 0)
        medium_count = severity_breakdown.get("MEDIUM", 0)
        low_count = severity_breakdown.get("LOW", 0)

        if risk_grade >= 90:
            rating = "Resilient (Low Risk)"
        elif risk_grade >= 75:
            rating = "Fair (Moderate Risk)"
        elif risk_grade >= 50:
            rating = "Vulnerable (Elevated Risk)"
        else:
            rating = "Compromised (Critical Risk)"

        lines = []
        category_ids = [item.strip() for item in category.split(",") if item.strip()]
        category_scope = ", ".join(_category_label(item) for item in category_ids) or category
        lines.append(
            f"Aegis conducted an automated security assessment of '{target_name}' "
            f"evaluating the selected OWASP 2026 categories: {category_scope}. "
            f"The scan executed {total_turns} prompt interaction(s) with an overall status of {scan_status}."
        )

        if category_results:
            coverage = "; ".join(
                f"{_category_label(str(item.get('category', 'UNKNOWN')))}: "
                f"{item.get('status', 'unknown')} ({item.get('attempts', 0)}/{item.get('budget', 0)} attempts)"
                for item in category_results
            )
            lines.append(f"Per-category execution status: {coverage}.")

        if scan_status in ("FAILED", "PARTIAL", "STOPPED", "INTERRUPTED") or total_turns == 0:
            lines.append(
                f"The assessment ended with status {scan_status} after {total_turns} interaction(s). "
                "Because execution did not complete the planned assessment scope, results for this scope are INCONCLUSIVE. "
                "No certification of resilience or clean defense can be granted for incomplete or interrupted scans."
            )
            if total_findings > 0:
                lines.append(
                    f"However, {total_findings} finding(s) were observed before termination."
                )
        elif total_findings == 0:
            lines.append(
                f"No vulnerability findings were identified in the completed selected scopes. "
                f"The target achieved an overall risk resilience grade of {risk_grade:.1f}/100 ({rating}). "
                f"This conclusion applies only to categories and attempts marked completed above."
            )
        else:
            sev_parts = []
            if critical_count > 0:
                sev_parts.append(f"{critical_count} Critical")
            if high_count > 0:
                sev_parts.append(f"{high_count} High")
            if medium_count > 0:
                sev_parts.append(f"{medium_count} Medium")
            if low_count > 0:
                sev_parts.append(f"{low_count} Low")
            sev_str = ", ".join(sev_parts)

            lines.append(
                f"A total of {total_findings} security finding(s) were identified ({sev_str}), "
                f"yielding an overall risk resilience grade of {risk_grade:.1f}/100 ({rating}). "
                f"Target responses contained leaked system instructions or canary signatures when evaluated against extraction probes."
            )
            lines.append(
                "Review each finding's evidence and remediation guidance for its category."
            )

        if estimated_cost_usd is not None and total_tokens is not None:
            lines.append(
                f"Financial Telemetry: Estimated scan expenditure is ${estimated_cost_usd:.4f} USD across {total_tokens} total tokens."
            )

        return " ".join(lines)

    @classmethod
    def compile_report_data(
        cls,
        scan_id: str,
        target_name: str,
        target_url: str,
        category: str,
        scan_status: str,
        started_at: Optional[str],
        completed_at: Optional[str],
        turns_count: int,
        findings: List[ReportFinding],
        category_ids: Optional[List[str]] = None,
        category_results: Optional[List[Dict[str, object]]] = None,
        excluded_categories: Optional[List[Dict[str, object]]] = None,
    ) -> ReportData:
        """
        Compile complete structured ReportData object.

        Args:
            scan_id: Scan UUID.
            target_name: Name of the target.
            target_url: Target URL.
            category: Vulnerability category.
            scan_status: Scan status.
            started_at: ISO timestamp of start.
            completed_at: ISO timestamp of completion.
            turns_count: Number of turns executed.
            findings: List of ReportFinding objects.

        Returns:
            Fully populated ReportData model.
        """
        severity_breakdown = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }
        severity_penalties = {
            "CRITICAL": 40.0,
            "HIGH": 25.0,
            "MEDIUM": 15.0,
            "LOW": 5.0,
            "INFO": 0.0,
        }
        total_penalty = 0.0

        for f in findings:
            sev = f.severity.upper() if f.severity else "INFO"
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1
            total_penalty += severity_penalties.get(sev, 10.0)

        risk_grade = RiskScorer.compute_grade(total_penalty)

        summary_text = cls.generate_executive_summary(
            target_name=target_name,
            category=category,
            total_turns=turns_count,
            total_findings=len(findings),
            severity_breakdown=severity_breakdown,
            risk_grade=risk_grade,
            scan_status=scan_status,
            category_results=category_results,
        )

        selected_ids = category_ids or [item.strip() for item in category.split(",") if item.strip()]
        scope_text = ", ".join(_category_label(item) for item in selected_ids) or category
        methodology = (
            "Aegis uses deterministic state machines and category-specific test/evaluation pipelines against the selected authorized web scope. "
            f"This assessment selected: {scope_text}. Per-category completion and attempt counts are listed separately; "
            "excluded, unsupported, or under-development categories were not tested."
        )

        return ReportData(
            scan_id=scan_id,
            target_name=target_name,
            target_url=target_url,
            category=category,
            category_ids=selected_ids,
            category_results=category_results or [],
            excluded_categories=excluded_categories or [],
            scan_status=scan_status,
            started_at=started_at,
            completed_at=completed_at,
            total_turns=turns_count,
            total_findings=len(findings),
            risk_grade=risk_grade,
            severity_breakdown=severity_breakdown,
            findings=findings,
            executive_summary=summary_text,
            methodology=methodology,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def generate_summary(self, findings: list) -> str:
        """Backward-compatible summary method."""
        return self.generate_executive_summary(
            target_name="Target",
            category="LLM08",
            total_turns=len(findings) or 1,
            total_findings=len(findings),
            severity_breakdown={"HIGH": len(findings)},
            risk_grade=75.0 if findings else 100.0,
            scan_status="COMPLETED",
        )
