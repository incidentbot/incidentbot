from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from incidentbot.platform.base import PlatformAdapter

_adapter: PlatformAdapter | None = None


def get_adapter() -> PlatformAdapter:
    if _adapter is None:
        raise RuntimeError(
            "Platform adapter not initialized. Call init_adapter() first."
        )
    return _adapter


def init_adapter(adapter: PlatformAdapter) -> None:
    global _adapter
    _adapter = adapter
