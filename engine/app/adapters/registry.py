"""Adapter Registry mapping target_type to implementation."""
from typing import Dict, Type
from app.adapters.base import BaseAdapter
from app.adapters.playwright_web import PlaywrightWebAdapter

_REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "web": PlaywrightWebAdapter,
}

def get_adapter_class(target_type: str) -> Type[BaseAdapter]:
    if target_type not in _REGISTRY:
        raise ValueError(f"No adapter registered for target type: {target_type}")
    return _REGISTRY[target_type]
