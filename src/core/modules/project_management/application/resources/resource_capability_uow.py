from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TypeVar

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.resource_capability_events import (
    ResourceCapabilityChanged,
    ResourceCapabilityChangeType,
    resource_capability_changed,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)
from src.core.shared.events.domain_events import domain_events


TCapability = TypeVar("TCapability", ResourceSkill, ResourceCertification)
logger = logging.getLogger(__name__)


class ResourceCapabilityUnitOfWork:
    """Commit a child capability mutation once, then publish targeted changes."""

    def __init__(self, session: Session, tenant_context_service) -> None:
        self._session = session
        self._tenant_context_service = tenant_context_service

    def execute(
        self,
        operation: Callable[[], TCapability],
        *,
        change_type: ResourceCapabilityChangeType,
    ) -> TCapability:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mutate resource capability"
        )
        try:
            child = operation()
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        event = ResourceCapabilityChanged(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=child.resource_id,
            child_id=child.id,
            child_version=child.version,
            child_type=type(child).__name__,
            change_type=change_type,
        )
        try:
            resource_capability_changed.emit(event)
            domain_events.resources_changed.emit(child.resource_id)
        except Exception:
            logger.exception(
                "Resource capability post-commit event dispatch failed",
                extra={
                    "resource_id": child.resource_id,
                    "child_id": child.id,
                    "change_type": change_type.value,
                },
            )
        return child


__all__ = ["ResourceCapabilityUnitOfWork"]
