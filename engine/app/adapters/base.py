"""Base Connector Interface."""
from abc import ABC, abstractmethod
from app.schemas.turn_record import TurnRecord

class BaseAdapter(ABC):
    """Base interface for all Aegis target adapters."""

    @abstractmethod
    async def open(self) -> None:
        """Initialize session and open connection."""
        pass

    @abstractmethod
    async def send_prompt(self, prompt: str, attempt: int) -> TurnRecord:
        """Send prompt to target and return a Unified Turn Record."""
        pass

    @abstractmethod
    async def reset_session(self) -> None:
        """Clear conversation history or reload target page."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up sessions and resources."""
        pass
