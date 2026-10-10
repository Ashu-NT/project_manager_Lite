from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetReviewReader,
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_timesheet_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    approved_time_outbox_service: IntegrationOutboxService | None,
) -> TimesheetService:
    def scope_organization_id(scope_type: str, scope_id: str) -> str | None:
        normalized_scope_type = str(scope_type or "").strip().lower()
        normalized_scope_id = str(scope_id or "").strip()
        if not normalized_scope_id:
            return None
        if normalized_scope_type == "project":
            project = repositories.pm.project_repo.get(normalized_scope_id)
            return getattr(project, "organization_id", None) if project is not None else None
        if normalized_scope_type == "site":
            site = platform_services.site_repo.get(normalized_scope_id)
            return getattr(site, "organization_id", None) if site is not None else None
        return None

    return TimesheetService(
        session=session,
        assignment_repo=repositories.pm.assignment_repo,
        task_repo=repositories.pm.task_repo,
        resource_repo=repositories.pm.resource_repo,
        employee_repo=repositories.platform.employee_repo,
        time_entry_repo=repositories.platform.time_entry_repo,
        timesheet_period_repo=repositories.platform.timesheet_period_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        scope_organization_resolver=scope_organization_id,
        approved_time_outbox_service=approved_time_outbox_service,
        timesheet_workspace_reader=SqlAlchemyTimesheetWorkspaceReader(
            session=session,
            resource_identity_reader=SqlAlchemyResourceIdentityReader(session=session),
        ),
        timesheet_review_reader=SqlAlchemyTimesheetReviewReader(session=session),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
    )
