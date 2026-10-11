from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.risk.queries.register_query import (
    RegisterQueryMixin,
)
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReader,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.register.register import (
    RegisterEntryRepository,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class RegisterService(ProjectManagementModuleGuardMixin, RegisterQueryMixin):
    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        register_repo: RegisterEntryRepository,
        user_session: UserSessionContext | None = None,
        module_catalog_service=None,
        tenant_context_service=None,
        register_catalog_reader: RegisterCatalogReader | None = None,
        lifecycle_handler: RegisterLifecycleHandler,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo
        self._register_repo: RegisterEntryRepository = register_repo
        self._user_session: UserSessionContext | None = user_session
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._register_catalog_reader = register_catalog_reader
        self._lifecycle = lifecycle_handler

    def create_entry(
        self,
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date=None,
        impact_summary: str = "",
        response_plan: str = "",
        code: str = "",
    ) -> RegisterEntry:
        return self._lifecycle.create_entry(
            project_id,
            entry_type=entry_type,
            title=title,
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
            code=code,
        )

    def update_entry(
        self,
        entry_id: str,
        *,
        expected_version: int | None = None,
        entry_type: RegisterEntryType | None = None,
        title: str | None = None,
        description: str | None = None,
        severity: RegisterEntrySeverity | None = None,
        status: RegisterEntryStatus | None = None,
        owner_name: str | None = None,
        due_date: Any = RegisterLifecycleHandler._UNSET,
        impact_summary: str | None = None,
        response_plan: str | None = None,
        code: str | None = None,
    ) -> RegisterEntry:
        return self._lifecycle.update_entry(
            entry_id,
            expected_version=expected_version,
            entry_type=entry_type,
            title=title,
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
            code=code,
        )

    def bulk_set_entry_status(
        self, entry_ids: Sequence[str], status: RegisterEntryStatus
    ) -> list[RegisterEntry]:
        return self._lifecycle.bulk_set_entry_status(entry_ids, status)

    def delete_entry(self, entry_id: str) -> None:
        self._lifecycle.delete_entry(entry_id)


__all__ = ["RegisterService"]
