"""Target Registration & Configuration Schemas."""
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any

class TargetCalibrationConfig(BaseModel):
    input_selector: str
    submit_selector: str
    response_selector: str
    wait_timeout_ms: int = 15000

class TargetCreate(BaseModel):
    name: str
    target_type: str = "web"
    url: str
    calibration_config: Optional[TargetCalibrationConfig] = None

class TargetResponse(BaseModel):
    id: str
    name: str
    target_type: str
    url: str
    calibration_config: Optional[TargetCalibrationConfig] = None
