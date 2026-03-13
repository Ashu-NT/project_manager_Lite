from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.access.service import AccessControlService

__all__ = ["AccessControlService"]


def __getattr__(name: str):
    if name == "AccessControlService":
        from core.platform.access.service import AccessControlService

        return AccessControlService
    raise AttributeError(name)
