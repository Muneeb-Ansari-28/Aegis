"""Request schema for staged reconnaissance."""
from typing import Optional
from pydantic import BaseModel, model_validator


class ReconRequest(BaseModel):
    project_path: Optional[str] = None
    run_probes: bool = False
    authorized: bool = False

    @model_validator(mode="after")
    def require_authorization_for_active_probes(self) -> "ReconRequest":
        if self.run_probes and not self.authorized:
            raise ValueError("Explicit authorization is required before active recon probes.")
        return self
