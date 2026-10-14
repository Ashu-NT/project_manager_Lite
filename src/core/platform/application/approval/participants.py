from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest

ApplyHandler = Callable[[ApprovalRequest, Any], ApprovalHandlerResult | None]
DependenciesFactory = Callable[[Session], Any]


class ApprovalParticipantRegistry:
    """Composition-owned participant registration; factories receive the deciding session."""

    def __init__(self) -> None:
        self.apply_handlers: dict[str, tuple[ApplyHandler, DependenciesFactory]] = {}
        self.reject_handlers: dict[str, tuple[ApplyHandler, DependenciesFactory]] = {}
        self.review_permissions: dict[str, str] = {}

    def register_apply_handler(
        self,
        request_type: str,
        handler: ApplyHandler,
        *,
        dependencies_factory: DependenciesFactory,
        reviewer_permission: str = "approval.decide",
    ) -> None:
        request_type = request_type.strip().lower()
        self.apply_handlers[request_type] = (handler, dependencies_factory)
        self.review_permissions[request_type] = reviewer_permission.strip().lower()

    def register_reject_handler(
        self,
        request_type: str,
        handler: ApplyHandler,
        *,
        dependencies_factory: DependenciesFactory,
    ) -> None:
        self.reject_handlers[request_type.strip().lower()] = (handler, dependencies_factory)
