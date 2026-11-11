"""Reconnaissance Service Orchestrator (Step 0a)."""
import logging
import uuid
from typing import Optional
from urllib.parse import urlparse
from app.recon.local_discovery import is_loopback_host

from app.adapters.playwright_web import PlaywrightWebAdapter
from app.core.database import SessionLocal
from datetime import datetime, timezone
from app.models.entities import TargetEntity, TargetProfileEntity, ReconRunEntity
from app.recon import (
    LocalDiscovery,
    PassiveNetworkCollector,
    ProfileBuilder,
    ProbeRunner,
    SignatureMatcher,
    SiteTypeClassifier,
    StaticProjectScanner,
    TargetProfile,
)

logger = logging.getLogger(__name__)


class ReconService:
    """
    Coordinates passive fingerprinting, active benign probing, localhost discovery,
    fuzzy classification, and Target Profile persistence.
    """

    @classmethod
    async def run_recon(
        cls,
        target_id: str,
        project_path: Optional[str] = None,
        run_probes: bool = False,
        authorized: bool = False,
    ) -> TargetProfile:
        """
        Execute full pre-scan recon for a target and persist its TargetProfile.
        """
        if run_probes and not authorized:
            raise PermissionError("Explicit authorization is required before active recon probes.")
        with SessionLocal() as session:
            target = session.get(TargetEntity, target_id)
            if not target:
                raise LookupError(f"Target '{target_id}' not found.")
            target_url = target.url
            calibration_config = target.calibration_config
            target_project_path = project_path

        recon_run_id = str(uuid.uuid4())
        passive_data = None
        sig_matches = []
        local_target = None
        static_result = None
        probe_result = None
        classifier_output = None

        matcher = SignatureMatcher()

        # 1. Passive Reconnaissance (Playwright)
        if target_url:
            try:
                collector = PassiveNetworkCollector(target_url=target_url)
                passive_data = await collector.collect()
                sig_matches = matcher.match(passive_data.observed_signals)
            except Exception as e:
                logger.warning(f"Passive recon failed for {target_url}: {e}")

        # 2. Tier 2 Localhost Discovery (strictly loopback host, single target port)
        if target_url:
            parsed = urlparse(target_url)
            if is_loopback_host(parsed.hostname) and parsed.port:
                try:
                    local_target = LocalDiscovery.inspect_port(parsed.port)
                except Exception as e:
                    logger.debug(f"Local discovery failed for port {parsed.port}: {e}")

        # 3. Tier 3 Static Analysis (opt-in; strictly if project_path explicitly provided)
        if target_project_path:
            try:
                scanner = StaticProjectScanner(target_project_path)
                static_result = scanner.scan()
            except Exception as e:
                logger.debug(f"Static project scan failed for {target_project_path}: {e}")

        # 4. Active Benign Probing (requires calibrated web adapter)
        if run_probes and target_url and calibration_config:
            adapter = None
            try:
                adapter = PlaywrightWebAdapter(
                    target_url=target_url,
                    selectors=calibration_config,
                    headless=True,
                )
                await adapter.open()
                probe_runner = ProbeRunner(adapter=adapter, recon_run_id=recon_run_id)
                probe_result = await probe_runner.run_probes(persist_turns=True)
            except Exception as e:
                logger.warning(f"Active probe execution failed for target {target_id}: {e}")
            finally:
                if adapter:
                    try:
                        await adapter.close()
                    except Exception:
                        pass

        # 5. Site-Type Fuzzy Classification
        try:
            classifier = SiteTypeClassifier()
            page_title = passive_data.page_title if passive_data else ""
            page_text = passive_data.page_text_sample if passive_data else ""
            scope_reply = (
                probe_result.analysis.scope_summary if probe_result else ""
            )
            classifier_output = await classifier.classify(
                page_title=page_title,
                page_text=page_text,
                scope_reply=scope_reply,
            )
        except Exception as e:
            logger.debug(f"Classifier invocation failed: {e}")

        # 6. Build Consolidated Target Profile
        builder = ProfileBuilder(
            target_id=target_id,
            target_url=target_url,
            passive_data=passive_data,
            signature_matches=sig_matches,
            probe_result=probe_result,
            classifier_output=classifier_output,
            local_target=local_target,
            static_result=static_result,
        )
        profile = builder.build()

        # 7. Persist to Database
        cls.save_target_profile(target_id, profile)

        # 8. Persist Recon Run Entity
        try:
            with SessionLocal() as session:
                stages_dict = {
                    k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v
                    for k, v in profile.stages.items()
                }
                prof_dict = (
                    profile.model_dump(mode="json")
                    if hasattr(profile, "model_dump")
                    else profile
                )
                run_entity = ReconRunEntity(
                    id=recon_run_id,
                    target_id=target_id,
                    status="COMPLETED" if not profile.warnings else "PARTIAL",
                    stages_data=stages_dict,
                    profile_data=prof_dict,
                    warnings=profile.warnings,
                    completed_at=datetime.now(timezone.utc),
                )
                session.add(run_entity)
                session.commit()
        except Exception as e:
            logger.debug(f"Could not persist recon run entity: {e}")

        return profile

    @classmethod
    def save_target_profile(
        cls,
        target_id: str,
        profile: TargetProfile,
        session_factory=SessionLocal,
    ) -> None:
        """Persist or update TargetProfile in database."""
        with session_factory() as session:
            existing = (
                session.query(TargetProfileEntity)
                .filter(TargetProfileEntity.target_id == target_id)
                .first()
            )
            data = (
                profile.model_dump(mode="json")
                if hasattr(profile, "model_dump")
                else profile
            )
            if existing is not None:
                existing.profile_data = data  # type: ignore # pyrefly: ignore[read-only]
            else:
                entity = TargetProfileEntity(
                    id=str(uuid.uuid4()),
                    target_id=target_id,
                    profile_data=data,
                )
                session.add(entity)
            session.commit()

    @classmethod
    def get_target_profile(
        cls,
        target_id: str,
        session_factory=SessionLocal,
    ) -> Optional[TargetProfile]:
        """Fetch saved TargetProfile from database."""
        with session_factory() as session:
            entity = (
                session.query(TargetProfileEntity)
                .filter(TargetProfileEntity.target_id == target_id)
                .first()
            )
            if not entity or not entity.profile_data:
                return None
            return TargetProfile.model_validate(entity.profile_data)

