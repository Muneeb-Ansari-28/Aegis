"""Typed Domain Errors for Aegis Pipeline."""
class AegisError(Exception):
    """Base exception for Aegis."""
    pass

class ConnectorTimeout(AegisError):
    """Raised when target adapter fails to receive response within timeout."""
    pass

class JudgeJSONError(AegisError):
    """Raised when LLM judge returns unparseable JSON after retries."""
    pass

class TargetCalibrationError(AegisError):
    """Raised when target UI elements cannot be found or calibrated."""
    pass
