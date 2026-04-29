from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.register import RegisterEntryRepository
from src.core.platform.audit.application.audit_service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleMixin,
)
from src.core.modules.project_management.application.risk.queries.register_query import (
    RegisterQueryMixin,
)


class RegisterService(ProjectManagementModuleGuardMixin, RegisterLifecycleMixin, RegisterQueryMixin):
    def __init__(
        self,
        *,
        session: Session,
        project_repo: ProjectRepository,
        register_repo: RegisterEntryRepository,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        module_catalog_service=None,
    ) -> None:
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._register_repo: RegisterEntryRepository = register_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["RegisterService"]

