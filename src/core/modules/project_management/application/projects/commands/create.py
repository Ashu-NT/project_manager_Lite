from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)
from src.core.modules.project_management.application.financials.configuration.events import (
    ProjectFinancialProfileCreated,
)
from src.core.modules.project_management.application.projects.commands.support import (
    ProjectSupportMixin,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
)
from src.core.modules.project_management.contracts.reads.projects import (
    ProjectCatalogReader,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.uow.projects.project_unit_of_work import (
    ProjectUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext

logger = logging.getLogger(__name__)

class ProjectCreateHandler(ProjectSupportMixin):
    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        project_catalog_reader: ProjectCatalogReader,
        uow_factory: ProjectUnitOfWorkFactory,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None,
        party_repo: PartyRepository | None,
        department_repo: DepartmentRepository | None,
    ) -> None:
        self._project_repo = project_repo
        self._project_catalog_reader = project_catalog_reader
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._party_repo = party_repo
        self._department_repo = department_repo

    @staticmethod
    def _new_context() -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

    def create_project(
        self,
        name: str,
        description: str = "",
        client_name: str | None = None,
        client_contact: str | None = None,
        financial_currency_code: str | None = None,
        status: ProjectStatus = ProjectStatus.PLANNED,
        start_date: date | None = None,
        end_date: date | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str = "",
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="create project")
        resolved_organization_id = self._resolve_project_organization_id(
            organization_id,
            operation_label="create project",
        )
        self._validate_client_party(client_party_id, resolved_organization_id)
        self._validate_department_reference(department_id, resolved_organization_id)
        self._validate_manager_user_id(manager_user_id, resolved_organization_id)
        resolved_currency = resolve_pm_currency(
            tenant_context_service=getattr(self, "_tenant_context_service", None),
            operation_label="create project",
            explicit=financial_currency_code,
        )
        project = Project.create(
            name=name,
            description=description,
            client_name=client_name,
            client_contact=client_contact,
            status=status,
            start_date=start_date,
            end_date=end_date,
            organization_id=resolved_organization_id,
            site_id=site_id,
            department_id=department_id,
            client_party_id=client_party_id,
            manager_user_id=manager_user_id,
        )
        scope = self._require_project_scope_ids(operation_label="create project")

        try:
            with self._require_project_uow_factory().create(context=self._new_context()) as uow:
                self._validate_project_name(
                    project.name, organization_id=resolved_organization_id, project_repo=uow.projects
                )
                project.code = self._resolve_project_code(
                    code,
                    project.name,
                    organization_id=resolved_organization_id,
                    project_repo=uow.projects,
                )
                uow.projects.add(project)
                profile = ProjectFinancialProfile.create(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=project.id,
                    currency_code=resolved_currency,
                    financial_start_date=project.start_date,
                    financial_end_date=project.end_date,
                )
                uow.financial_profiles.add(profile)
                self._record_financial_profile_audit(uow, "create", profile)
                uow.record_event(
                    ProjectFinancialProfileCreated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=project.id,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="project",
                    entity_id=project.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"name": project.name, "status": project.status.value},
                    workspace_id=project.id,
                    metadata={"action": "project.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="project.create",
                    entity_type="project",
                    entity_id=project.id,
                    module="project_management",
                    workspace_id=project.id,
                    message=f"Created project {project.name}",
                    details={"name": project.name},
                    commit=False,
                )
                uow.record_event(
                    ProjectCreated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=project.id,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            if self._is_project_code_integrity_error(exc):
                self._raise_project_code_duplicate(project.code, exc)
            logger.error("Error creating project: %s", exc)
            raise
        logger.info("Created project %s - %s", project.id, project.name)
        return project
