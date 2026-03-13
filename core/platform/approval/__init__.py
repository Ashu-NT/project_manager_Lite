from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.approval.service import ApprovalService

__all__ = ["ApprovalService"]


def __getattr__(name: str):
    if name == "ApprovalService":
        from core.platform.approval.service import ApprovalService

        return ApprovalService
    raise AttributeError(name)
