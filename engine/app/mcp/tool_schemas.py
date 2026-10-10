"""Shared MCP Input/Output Models re-using schemas/."""
from pydantic import BaseModel
from app.schemas.turn_record import TurnRecord
from app.schemas.verdict import JudgeVerdict

class OpenTargetInput(BaseModel):
    target_url: str

class SendPromptInput(BaseModel):
    prompt: str
    attempt: int
