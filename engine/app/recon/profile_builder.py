"""Deterministic Profile Builder.

Merges passive network signals, YAML signature matches, active benign probe results,
LLM fuzzy classification, and localhost discovery tiers into a normalized TargetProfile.
Enforces the core rule: 'Unknown is not absent'.
"""
import logging
from typing import Any, Dict, List, Literal, Optional

from app.recon.classifier import ClassifierOutput
from app.recon.fingerprint import SignatureMatch
from app.recon.local_discovery import LocalTarget
from app.recon.network_collector import PassiveReconData
from app.recon.probe_runner import ProbeRunResult
from app.recon.schemas import FieldEvidence, TargetProfile, ReconStageDetail
from app.recon.static_scanner import StaticScanResult

logger = logging.getLogger(__name__)

EvidenceSource = Literal[
    "passive",
    "probe",
    "classifier",
    "tier2_psutil",
    "tier3_static",
    "corroborated",
    "fallback",
]

StageStatus = Literal["completed", "partial", "skipped", "failed", "unknown"]


def _coerce_stage_status(val: Any) -> StageStatus:
    """Safely coerce any status string to a valid StageStatus literal."""
    if val == "partial":
        return "partial"
    if val == "skipped":
        return "skipped"
    if val == "failed":
        return "failed"
    if val == "unknown":
        return "unknown"
    return "completed"


def combine_confidences(c1: float, c2: float) -> float:
    """Combine two independent probabilistic signals."""
    return min(0.99, 1.0 - (1.0 - c1) * (1.0 - c2))


class ProfileBuilder:
    """
    Synthesizes multi-source evidence into a normalized TargetProfile.
    """

    def __init__(
        self,
        target_id: str,
        target_url: Optional[str] = None,
        passive_data: Optional[PassiveReconData] = None,
        signature_matches: Optional[List[SignatureMatch]] = None,
        probe_result: Optional[ProbeRunResult] = None,
        classifier_output: Optional[ClassifierOutput] = None,
        local_target: Optional[LocalTarget] = None,
        static_result: Optional[StaticScanResult] = None,
    ):
        self.target_id = target_id
        self.target_url = target_url
        self.passive_data = passive_data
        self.signature_matches = signature_matches or []
        self.probe_result = probe_result
        self.classifier_output = classifier_output
        self.local_target = local_target
        self.static_result = static_result

    def build(self) -> TargetProfile:
        frameworks: List[str] = []
        endpoints: List[str] = []
        evidence_rag: List[str] = []
        evidence_vdb: List[str] = []
        evidence_tools: List[str] = []
        evidence_memory: List[str] = []
        evidence_streaming: List[str] = []
        evidence_html: List[str] = []
        evidence_md: List[str] = []

        # 1. Frameworks and Endpoints extraction
        for sig in self.signature_matches:
            if sig.implies.get("framework"):
                frameworks.append(sig.implies["framework"])
            if sig.implies.get("endpoint"):
                endpoints.append(sig.implies["endpoint"])

        if self.static_result:
            frameworks.extend(self.static_result.detected_frameworks)

        if self.local_target and self.local_target.inferred_technology:
            frameworks.append(self.local_target.inferred_technology)

        if self.passive_data:
            endpoints.extend(self.passive_data.well_known_found)

        # Deduplicate
        frameworks = sorted(list(set(frameworks)))
        endpoints = sorted(list(set(endpoints)))

        # 2. Site Type & Primary Domain (from Classifier)
        if self.classifier_output:
            site_type = FieldEvidence(
                detected=True,
                value=self.classifier_output.site_type,
                confidence=self.classifier_output.confidence,
                evidence=[self.classifier_output.reasoning] if self.classifier_output.reasoning else [],
                source="classifier",
            )
            primary_domain = FieldEvidence(
                detected=True,
                value=self.classifier_output.primary_domain,
                confidence=self.classifier_output.confidence,
                evidence=[f"Classified domain: {self.classifier_output.primary_domain}"],
                source="classifier",
            )
        else:
            site_type = FieldEvidence(
                detected=True,
                value="general_assistant",
                confidence=0.5,
                evidence=["Default baseline site classification"],
                source="fallback",
            )
            primary_domain = FieldEvidence(
                detected=True,
                value="general",
                confidence=0.5,
                evidence=["Default domain"],
                source="fallback",
            )

        # 3. RAG Capabilities
        rag_detected = False
        rag_confidence = 0.0
        rag_source: EvidenceSource = "fallback"

        if self.static_result and self.static_result.has_rag:
            rag_detected = True
            rag_confidence = 0.95
            rag_source = "tier3_static"
            evidence_rag.extend(self.static_result.evidence)

        sig_rag = [s for s in self.signature_matches if s.implies.get("rag")]
        if sig_rag:
            for s in sig_rag:
                evidence_rag.extend(s.evidence)
            if rag_detected:
                rag_confidence = combine_confidences(rag_confidence, 0.85)
                rag_source = "corroborated"
            else:
                rag_detected = True
                rag_confidence = 0.85
                rag_source = "passive"

        if self.probe_result and self.probe_result.analysis.rag_detected:
            evidence_rag.extend(self.probe_result.analysis.evidence)
            if rag_detected:
                rag_confidence = combine_confidences(rag_confidence, self.probe_result.analysis.rag_confidence)
                rag_source = "corroborated"
            else:
                rag_detected = True
                rag_confidence = self.probe_result.analysis.rag_confidence
                rag_source = "probe"

        if not rag_detected:
            # Affirmative negative ONLY if static scan completed without RAG AND active probe completed without RAG
            tier3_clean = (
                self.static_result is not None
                and getattr(self.static_result, "status", None) == "completed"
                and not self.static_result.has_rag
            )
            probe_clean = (
                self.probe_result is not None
                and getattr(self.probe_result, "status", None) == "completed"
                and not self.probe_result.analysis.rag_detected
            )
            if tier3_clean and probe_clean:
                rag_confidence = 0.88
                evidence_rag.append("Tier 3 static scan and active probes completed and found no RAG components.")
            else:
                rag_confidence = 0.40  # Unknown, low confidence per safe-fallback principle
                evidence_rag.append("No affirmative RAG signals observed (unknown; insufficient negative evidence).")

        has_rag = FieldEvidence(
            detected=rag_detected,
            confidence=round(rag_confidence, 2),
            evidence=evidence_rag,
            source=rag_source if rag_detected else "fallback",
        )

        # 4. Vector DB Capabilities
        vdb_detected = False
        vdb_name = None
        vdb_confidence = 0.0
        vdb_source: EvidenceSource = "fallback"

        if self.static_result and self.static_result.has_vector_db:
            vdb_detected = True
            vdb_confidence = 0.95
            vdb_name = ", ".join(self.static_result.vector_db_names)
            vdb_source = "tier3_static"
            evidence_vdb.extend(self.static_result.evidence)
        elif rag_detected:
            vdb_detected = True
            vdb_confidence = 0.60
            vdb_source = "corroborated"
            evidence_vdb.append("Inferred from RAG retrieval architecture presence.")
        else:
            vdb_confidence = 0.40
            evidence_vdb.append("No vector DB identified.")

        has_vector_db = FieldEvidence(
            detected=vdb_detected,
            value=vdb_name,
            confidence=round(vdb_confidence, 2),
            evidence=evidence_vdb,
            source=vdb_source if vdb_detected else "fallback",
        )

        # 5. Tools & Function Calling
        tools_detected = False
        tools_confidence = 0.0
        tools_source: EvidenceSource = "fallback"

        if self.static_result and self.static_result.has_tools:
            tools_detected = True
            tools_confidence = 0.90
            tools_source = "tier3_static"
            evidence_tools.extend(self.static_result.evidence)

        if self.probe_result and self.probe_result.analysis.tools_detected:
            evidence_tools.extend(self.probe_result.analysis.evidence)
            if tools_detected:
                tools_confidence = combine_confidences(tools_confidence, self.probe_result.analysis.tools_confidence)
                tools_source = "corroborated"
            else:
                tools_detected = True
                tools_confidence = self.probe_result.analysis.tools_confidence
                tools_source = "probe"

        if not tools_detected:
            tools_confidence = 0.40
            evidence_tools.append("No tool-calling capabilities detected.")

        has_tools = FieldEvidence(
            detected=tools_detected,
            confidence=round(tools_confidence, 2),
            evidence=evidence_tools,
            source=tools_source if tools_detected else "fallback",
        )

        # 6. Conversation Memory
        mem_detected = False
        mem_confidence = 0.0
        mem_source: EvidenceSource = "fallback"

        if self.probe_result:
            mem_detected = self.probe_result.analysis.memory_detected
            mem_confidence = self.probe_result.analysis.memory_confidence
            mem_source = "probe"
            evidence_memory.extend(self.probe_result.analysis.evidence)

        sig_mem = [s for s in self.signature_matches if s.implies.get("memory")]
        if sig_mem:
            for s in sig_mem:
                evidence_memory.extend(s.evidence)
            if mem_detected:
                mem_confidence = combine_confidences(mem_confidence, 0.85)
                mem_source = "corroborated"
            else:
                mem_detected = True
                mem_confidence = 0.85
                mem_source = "passive"

        if not mem_detected and mem_confidence == 0.0:
            mem_confidence = 0.50
            evidence_memory.append("Conversation memory could not be verified.")

        has_conversation_memory = FieldEvidence(
            detected=mem_detected,
            confidence=round(mem_confidence, 2),
            evidence=evidence_memory,
            source=mem_source if mem_detected else "fallback",
        )

        # 7. Streaming
        stream_detected = False
        stream_value = None
        stream_confidence = 0.0
        stream_source: EvidenceSource = "fallback"

        for s in self.signature_matches:
            if s.implies.get("streaming"):
                stream_detected = True
                stream_value = s.implies["streaming"]
                stream_confidence = s.confidence
                stream_source = "passive"
                evidence_streaming.extend(s.evidence)
                break

        if not stream_detected:
            stream_confidence = 0.50
            evidence_streaming.append("Streaming mode undetermined.")

        has_streaming = FieldEvidence(
            detected=stream_detected,
            value=stream_value,
            confidence=round(stream_confidence, 2),
            evidence=evidence_streaming,
            source=stream_source if stream_detected else "fallback",
        )

        # 8. Rendering (HTML / Markdown)
        html_detected = False
        html_evidence = []
        md_detected = False
        md_evidence = []

        if self.probe_result:
            if self.probe_result.analysis.html_rendered:
                html_detected = True
                html_evidence.append("Active rendering probe: HTML markup parsed by target.")
            if self.probe_result.analysis.markdown_rendered:
                md_detected = True
                md_evidence.append("Active rendering probe: Markdown syntax formatted by target.")

        renders_html = FieldEvidence(
            detected=html_detected,
            confidence=0.85 if html_detected else 0.50,
            evidence=html_evidence or ["HTML tags escaped or not observed."],
            source="probe" if html_detected else "fallback",
        )
        renders_markdown = FieldEvidence(
            detected=md_detected,
            confidence=0.85 if md_detected else 0.50,
            evidence=md_evidence or ["Standard text response."],
            source="probe" if md_detected else "fallback",
        )

        stages: Dict[str, ReconStageDetail] = {}
        all_warnings: List[str] = []

        # Tier 1 stage
        if self.passive_data:
            p_status = _coerce_stage_status(getattr(self.passive_data, "status", "completed"))
            p_warns = getattr(self.passive_data, "warnings", [])
            stages["tier1_passive"] = ReconStageDetail(
                status=p_status,
                warning="; ".join(p_warns) if p_warns else None,
                details={"well_known_count": len(self.passive_data.well_known_found)},
            )
            all_warnings.extend(p_warns)
        else:
            stages["tier1_passive"] = ReconStageDetail(status="skipped")

        # Tier 2 stage
        if self.local_target:
            stages["tier2_local"] = ReconStageDetail(
                status="completed",
                details={"pid": self.local_target.pid, "port": self.local_target.port},
            )
        else:
            stages["tier2_local"] = ReconStageDetail(status="skipped")

        # Tier 3 stage
        if self.static_result:
            s_status = _coerce_stage_status(getattr(self.static_result, "status", "completed"))
            s_warns = getattr(self.static_result, "warnings", [])
            stages["tier3_static"] = ReconStageDetail(
                status=s_status,
                warning="; ".join(s_warns) if s_warns else None,
                details={"project_path": self.static_result.project_path},
            )
            all_warnings.extend(s_warns)
        else:
            stages["tier3_static"] = ReconStageDetail(status="skipped")

        # Active probes stage
        if self.probe_result:
            pr_status = _coerce_stage_status(getattr(self.probe_result, "status", "completed"))
            pr_warns = getattr(self.probe_result, "warnings", [])
            stages["active_probes"] = ReconStageDetail(
                status=pr_status,
                warning="; ".join(pr_warns) if pr_warns else None,
                details={"turns_count": len(self.probe_result.turns)},
            )
            all_warnings.extend(pr_warns)
        else:
            stages["active_probes"] = ReconStageDetail(status="skipped")

        # Classifier stage
        if self.classifier_output:
            stages["classifier"] = ReconStageDetail(
                status="completed",
                details={"site_type": self.classifier_output.site_type},
            )
        else:
            stages["classifier"] = ReconStageDetail(status="skipped")

        return TargetProfile(
            target_id=self.target_id,
            target_url=self.target_url,
            site_type=site_type,
            primary_domain=primary_domain,
            has_rag=has_rag,
            has_vector_db=has_vector_db,
            has_tools=has_tools,
            has_conversation_memory=has_conversation_memory,
            has_streaming=has_streaming,
            renders_html=renders_html,
            renders_markdown=renders_markdown,
            detected_frameworks=frameworks,
            detected_endpoints=endpoints,
            raw_signals={
                "well_known": self.passive_data.well_known_found if self.passive_data else [],
                "signature_count": len(self.signature_matches),
            },
            stages=stages,
            warnings=all_warnings,
        )

