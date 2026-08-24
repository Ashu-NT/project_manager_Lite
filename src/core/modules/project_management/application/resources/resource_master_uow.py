from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TypeVar

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.resource_master_events import (
    ResourceMasterChanged,
    ResourceMasterChangeType,
    resource_master_changed,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.shared.events.domain_events import domain_events


T = TypeVar("T", bound=Resource)
logger = logging.getLogger(__name__)


class ResourceMasterUnitOfWork:
    """Own one resource-master mutation, audit record, and commit boundary."""

    def __init__(self, session: Session, tenant_context_service) -> None:
        self._session = session
        self._tenant_context_service = tenant_context_service

    def execute(
        self,
        operation: Callable[[], T],
        *,
        change_type: ResourceMasterChangeType,
    ) -> T:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mutate resource master"
        )
        try:
            resource = operation()
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        event = ResourceMasterChanged(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=resource.id,
            version=resource.version,
            change_type=change_type,
        )
        try:
            resource_master_changed.emit(event)
            domain_events.resources_changed.emit(resource.id)
        except Exception:
            logger.exception(
                "Resource master post-commit event dispatch failed",
                extra={"resource_id": resource.id, "change_type": change_type.value},
            )
        return resource


__all__ = ["ResourceMasterUnitOfWork"]
