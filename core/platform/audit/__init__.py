from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.audit.service import AuditService

__all__ = ["AuditService"]


def __getattr__(name: str):
    if name == "AuditService":
        from core.platform.audit.service import AuditService

        return AuditService
    raise AttributeError(name)
