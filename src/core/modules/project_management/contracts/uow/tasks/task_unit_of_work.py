from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class TaskUnitOfWork(UnitOfWork, Protocol):

    tasks: TaskRepository
    assignments: AssignmentRepository
    dependencies: DependencyRepository
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class TaskUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> TaskUnitOfWork: ...  # type: ignore[override]


__all__ = ["TaskUnitOfWork", "TaskUnitOfWorkFactory"]
