"""Signature Matcher for Passive & Active Reconnaissance."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_SIGNATURES_PATH = Path(__file__).parent / "signatures" / "ai_stack.yaml"


class SignatureMatch(BaseModel):
    signature_id: str
    name: str
    category: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    implies: Dict[str, Any] = Field(default_factory=dict)


class SignatureMatcher:
    """
    Evaluates observed network, DOM, header, and payload indicators
    against versioned YAML signatures to identify AI technologies.
    """

    def __init__(self, signatures_path: Optional[Path] = None):
        self.signatures_path = signatures_path or DEFAULT_SIGNATURES_PATH
        self.signatures: List[Dict[str, Any]] = self._load_signatures()

    def _load_signatures(self) -> List[Dict[str, Any]]:
        if not self.signatures_path.exists():
            logger.warning(f"Signatures file not found at {self.signatures_path}")
            return []
        try:
            with open(self.signatures_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("signatures", [])
        except Exception as e:
            logger.error(f"Failed to load signatures YAML: {e}")
            return []

    def match(self, observed: Dict[str, Any]) -> List[SignatureMatch]:
        """
        Evaluate observed signals against loaded signatures.

        Args:
            observed: dict containing sets or lists of:
                - paths (e.g. ['/v1/chat/completions', '/openapi.json'])
                - headers (e.g. {'server': 'uvicorn', 'content-type': 'text/event-stream'})
                - websocket_paths (e.g. ['/_stcore/stream'])
                - dom (e.g. ['div.stApp', 'gradio-app'])
                - globals (e.g. ['__NEXT_DATA__', 'gradio_config'])
                - scripts (e.g. ['https://example.com/assets/streamlit.js'])
                - response_keys (e.g. ['sources', 'citations'])
                - payload_keys (e.g. ['messages', 'session_id'])

        Returns:
            List of SignatureMatch objects for matched signatures.
        """
        matches: List[SignatureMatch] = []

        obs_paths = {p.lower() for p in observed.get("paths", [])}
        obs_ws = {ws.lower() for ws in observed.get("websocket_paths", [])}
        obs_dom = {d.lower() for d in observed.get("dom", [])}
        obs_globals = {g for g in observed.get("globals", [])}
        obs_scripts = [s.lower() for s in observed.get("scripts", [])]
        obs_resp_keys = {k.lower() for k in observed.get("response_keys", [])}
        obs_payload_keys = {k.lower() for k in observed.get("payload_keys", [])}

        # Normalize headers to lowercase key: value and set of keys
        raw_headers = observed.get("headers", {})
        header_pairs = set()
        header_keys = set()
        if isinstance(raw_headers, dict):
            for k, v in raw_headers.items():
                k_lower = str(k).lower()
                v_lower = str(v).lower()
                header_keys.add(k_lower)
                header_pairs.add(f"{k_lower}: {v_lower}")
        elif isinstance(raw_headers, list):
            for h in raw_headers:
                header_pairs.add(str(h).lower())

        for sig in self.signatures:
            sig_id = sig.get("id", "unknown")
            sig_name = sig.get("name", "Unknown")
            sig_cat = sig.get("category", "general")
            confidence = float(sig.get("confidence", 0.8))
            implies = sig.get("implies", {})
            indicators = sig.get("indicators", {})

            matched_evidence: List[str] = []

            # 1. Match paths
            for path in indicators.get("paths", []):
                p_clean = path.lower()
                if any(p_clean in op for op in obs_paths):
                    matched_evidence.append(f"Matched path: {path}")

            # 2. Match websocket paths
            for ws_path in indicators.get("websocket_paths", []):
                w_clean = ws_path.lower()
                if any(w_clean in ow for ow in obs_ws):
                    matched_evidence.append(f"Matched websocket path: {ws_path}")

            # 3. Match headers
            for expected_header in indicators.get("headers", []):
                eh_lower = expected_header.lower()
                if ":" in eh_lower:
                    if any(eh_lower in hp for hp in header_pairs):
                        matched_evidence.append(f"Matched header: {expected_header}")
                else:
                    if eh_lower in header_keys or any(eh_lower in hp for hp in header_pairs):
                        matched_evidence.append(f"Matched header indicator: {expected_header}")

            # 4. Match DOM elements
            for dom_sel in indicators.get("dom", []):
                if dom_sel.lower() in obs_dom:
                    matched_evidence.append(f"Matched DOM selector: {dom_sel}")

            # 5. Match window globals
            for glob_name in indicators.get("globals", []):
                if glob_name in obs_globals:
                    matched_evidence.append(f"Matched window global: {glob_name}")

            # 6. Match script source patterns
            for script_pattern in indicators.get("scripts", []):
                sp_clean = script_pattern.lower()
                if any(sp_clean in s for s in obs_scripts):
                    matched_evidence.append(f"Matched script pattern: {script_pattern}")

            # 7. Match response JSON keys
            for rk in indicators.get("response_keys", []):
                if rk.lower() in obs_resp_keys:
                    matched_evidence.append(f"Matched response payload key: {rk}")

            # 8. Match request payload keys
            for pk in indicators.get("payload_keys", []):
                if pk.lower() in obs_payload_keys:
                    matched_evidence.append(f"Matched request payload key: {pk}")

            if matched_evidence:
                matches.append(SignatureMatch(
                    signature_id=sig_id,
                    name=sig_name,
                    category=sig_cat,
                    confidence=confidence,
                    evidence=matched_evidence,
                    implies=implies,
                ))

        return matches

