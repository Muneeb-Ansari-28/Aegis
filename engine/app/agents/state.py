"""Scan States, Budgets, and Transition Definitions."""
from enum import Enum

class ScanState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
