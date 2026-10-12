from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
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
    ) -> None:
        self._project_repo: ProjectRepository = project_repo
        self._register_repo: RegisterEntryRepository = register_repo
        self._user_session: UserSessionContext | None = user_session
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._register_catalog_reader = register_catalog_reader


__all__ = ["RegisterService"]
