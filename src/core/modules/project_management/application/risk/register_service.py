from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.register.register import RegisterEntryRepository
from src.core.modules.project_management.contracts.reads.register import RegisterCatalogReader
from src.core.modules.project_management.contracts.uow.register.register_unit_of_work import (
    RegisterUnitOfWorkFactory,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.common.ids import generate_id
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleMixin,
)
from src.core.modules.project_management.application.risk.queries.register_query import (
    RegisterQueryMixin,
)
from src.core.shared.events.domain_event_context import DomainEventContext


class RegisterService(ProjectManagementModuleGuardMixin, RegisterLifecycleMixin, RegisterQueryMixin):
    def __init__(
        self,
        *,
        session: Session,
        project_repo: ProjectRepository,
        register_repo: RegisterEntryRepository,
        user_session: UserSessionContext | None = None,
        activity_service: ActivityService | None = None,
        module_catalog_service=None,
        tenant_context_service=None,
        register_catalog_reader: RegisterCatalogReader | None = None,
        uow_factory: RegisterUnitOfWorkFactory | None = None,
    ) -> None:
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._register_repo: RegisterEntryRepository = register_repo
        self._user_session: UserSessionContext | None = user_session
        self._activity_service: ActivityService | None = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._register_catalog_reader = register_catalog_reader
        self._uow_factory: RegisterUnitOfWorkFactory | None = uow_factory

    def _require_uow_factory(self) -> RegisterUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Register unit of work is not configured.")
        return self._uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["RegisterService"]
