from __future__ import annotations

from sqlalchemy.orm import Session

from core.modules.project_management.interfaces import ProjectRepository, RegisterEntryRepository
from core.platform.audit.service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.register.lifecycle import RegisterLifecycleMixin
from core.modules.project_management.services.register.query import RegisterQueryMixin


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
