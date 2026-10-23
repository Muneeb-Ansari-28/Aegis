"""Target Registration & Configuration Schemas."""
import ipaddress
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from urllib.parse import urlsplit


class TargetCalibrationConfig(BaseModel):
    """Captured or manually provided CSS selectors for chatbot DOM elements."""
    input_selector: str
    submit_selector: str
    response_selector: str
    wait_timeout_ms: int = Field(default=15000, ge=1000, le=120000)


class CalibrationSessionResponse(BaseModel):
    """Progress returned while the user selects controls in the target browser."""
    session_id: str
    target_id: str
    status: str
    step: int
    input_selected: bool = False
    enter_selected: bool = False
    calibration_config: Optional[TargetCalibrationConfig] = None
    error: Optional[str] = None


ALLOWED_TARGET_TYPES = {"web", "api", "app"}


class TargetCreate(BaseModel):
    """Request body for POST /targets with validation."""
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable target name.")
    target_type: str = Field(default="web", description="Target connector type: web, api, or app.")
    url: str = Field(..., min_length=1, description="Target URL (must start with http:// or https://).")
    calibration_config: Optional[TargetCalibrationConfig] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        """Reject whitespace-only names."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Target name must not be blank.")
        return stripped

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        """Restrict target_type to the supported connector types."""
        lower = v.lower().strip()
        if lower not in ALLOWED_TARGET_TYPES:
            raise ValueError(f"target_type must be one of {sorted(ALLOWED_TARGET_TYPES)}, got '{v}'.")
        return lower

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Require an HTTP(S) URL with a host name."""
        stripped = v.strip()
        parsed = urlsplit(stripped)
        host = (parsed.hostname or "").lower().rstrip(".")
        is_local_hostname = (
            host in {"localhost", "host.docker.internal"}
            or host.endswith((".localhost", ".local", ".test"))
            or ("." not in host and ":" not in host)
        )
        try:
            address = ipaddress.ip_address(host)
            is_local_address = address.is_loopback or address.is_private or address.is_link_local
        except ValueError:
            is_local_address = False
        if parsed.scheme.lower() not in {"http", "https"} or not host:
            raise ValueError("URL must be a valid http:// or https:// URL with a host.")
        if parsed.username or parsed.password:
            raise ValueError("Local target URLs must not contain embedded credentials.")
        if not (is_local_hostname or is_local_address):
            raise ValueError("Aegis pre-deployment scans only accept local or private-network target URLs.")
        return stripped


class TargetResponse(BaseModel):
    """Response body for target endpoints."""
    id: str
    name: str
    target_type: str = "web"
    url: Optional[str] = None
    calibration_config: Optional[TargetCalibrationConfig] = None
