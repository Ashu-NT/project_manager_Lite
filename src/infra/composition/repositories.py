from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration import (
    SqlAlchemyTaskCommentRepository,
    SqlAlchemyTaskPresenceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioProjectDependencyRepository,
    SqlAlchemyPortfolioScoringTemplateRepository,
    SqlAlchemyPortfolioScenarioRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.baseline import SqlAlchemyBaselineRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.cost_calendar import (
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyWorkingCalendarRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.register import SqlAlchemyRegisterEntryRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.resource import SqlAlchemyResourceRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from src.core.platform.infrastructure.persistence.access import (
    SqlAlchemyProjectMembershipRepository,
    SqlAlchemyScopedAccessGrantRepository,
)
from src.core.platform.infrastructure.persistence.approval.repository import SqlAlchemyApprovalRepository
from src.core.platform.infrastructure.persistence.audit.repository import SqlAlchemyAuditLogRepository
from src.core.platform.infrastructure.persistence.auth.repository import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserRoleRepository,
)
from src.core.platform.infrastructure.persistence.documents import (
    SqlAlchemyDocumentLinkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentStructureRepository,
)
from src.core.platform.infrastructure.persistence.org.repository import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyEmployeeRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemySiteRepository,
)
from src.core.platform.infrastructure.persistence.party import SqlAlchemyPartyRepository
from src.core.platform.infrastructure.persistence.time import (
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
)


@dataclass(frozen=True)
class RepositoryBundle:
    project_repo: SqlAlchemyProjectRepository
    task_repo: SqlAlchemyTaskRepository
    resource_repo: SqlAlchemyResourceRepository
    employee_repo: SqlAlchemyEmployeeRepository
    organization_repo: SqlAlchemyOrganizationRepository
    document_repo: SqlAlchemyDocumentRepository
    document_link_repo: SqlAlchemyDocumentLinkRepository
    document_structure_repo: SqlAlchemyDocumentStructureRepository
    party_repo: SqlAlchemyPartyRepository
    department_repo: SqlAlchemyDepartmentRepository
    site_repo: SqlAlchemySiteRepository
    assignment_repo: SqlAlchemyAssignmentRepository
    time_entry_repo: SqlAlchemyTimeEntryRepository
    timesheet_period_repo: SqlAlchemyTimesheetPeriodRepository
    dependency_repo: SqlAlchemyDependencyRepository
    cost_repo: SqlAlchemyCostRepository
    calendar_repo: SqlAlchemyCalendarEventRepository
    work_calendar_repo: SqlAlchemyWorkingCalendarRepository
    baseline_repo: SqlAlchemyBaselineRepository
    project_resource_repo: SqlAlchemyProjectResourceRepository
    user_repo: SqlAlchemyUserRepository
    auth_session_repo: SqlAlchemyAuthSessionRepository
    role_repo: SqlAlchemyRoleRepository
    permission_repo: SqlAlchemyPermissionRepository
    user_role_repo: SqlAlchemyUserRoleRepository
    role_permission_repo: SqlAlchemyRolePermissionRepository
    project_membership_repo: SqlAlchemyProjectMembershipRepository
    scoped_access_repo: SqlAlchemyScopedAccessGrantRepository
    audit_repo: SqlAlchemyAuditLogRepository
    approval_repo: SqlAlchemyApprovalRepository
    register_repo: SqlAlchemyRegisterEntryRepository
    task_comment_repo: SqlAlchemyTaskCommentRepository
    task_presence_repo: SqlAlchemyTaskPresenceRepository
    portfolio_intake_repo: SqlAlchemyPortfolioIntakeRepository
    portfolio_project_dependency_repo: SqlAlchemyPortfolioProjectDependencyRepository
    portfolio_scoring_template_repo: SqlAlchemyPortfolioScoringTemplateRepository
    portfolio_scenario_repo: SqlAlchemyPortfolioScenarioRepository


def build_repository_bundle(session: Session) -> RepositoryBundle:
    return RepositoryBundle(
        project_repo=SqlAlchemyProjectRepository(session),
        task_repo=SqlAlchemyTaskRepository(session),
        resource_repo=SqlAlchemyResourceRepository(session),
        employee_repo=SqlAlchemyEmployeeRepository(session),
        organization_repo=SqlAlchemyOrganizationRepository(session),
        document_repo=SqlAlchemyDocumentRepository(session),
        document_link_repo=SqlAlchemyDocumentLinkRepository(session),
        document_structure_repo=SqlAlchemyDocumentStructureRepository(session),
        party_repo=SqlAlchemyPartyRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        site_repo=SqlAlchemySiteRepository(session),
        assignment_repo=SqlAlchemyAssignmentRepository(session),
        time_entry_repo=SqlAlchemyTimeEntryRepository(session),
        timesheet_period_repo=SqlAlchemyTimesheetPeriodRepository(session),
        dependency_repo=SqlAlchemyDependencyRepository(session),
        cost_repo=SqlAlchemyCostRepository(session),
        calendar_repo=SqlAlchemyCalendarEventRepository(session),
        work_calendar_repo=SqlAlchemyWorkingCalendarRepository(session),
        baseline_repo=SqlAlchemyBaselineRepository(session),
        project_resource_repo=SqlAlchemyProjectResourceRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        auth_session_repo=SqlAlchemyAuthSessionRepository(session),
        role_repo=SqlAlchemyRoleRepository(session),
        permission_repo=SqlAlchemyPermissionRepository(session),
        user_role_repo=SqlAlchemyUserRoleRepository(session),
        role_permission_repo=SqlAlchemyRolePermissionRepository(session),
        project_membership_repo=SqlAlchemyProjectMembershipRepository(session),
        scoped_access_repo=SqlAlchemyScopedAccessGrantRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        approval_repo=SqlAlchemyApprovalRepository(session),
        register_repo=SqlAlchemyRegisterEntryRepository(session),
        task_comment_repo=SqlAlchemyTaskCommentRepository(session),
        task_presence_repo=SqlAlchemyTaskPresenceRepository(session),
        portfolio_intake_repo=SqlAlchemyPortfolioIntakeRepository(session),
        portfolio_project_dependency_repo=SqlAlchemyPortfolioProjectDependencyRepository(session),
        portfolio_scoring_template_repo=SqlAlchemyPortfolioScoringTemplateRepository(session),
        portfolio_scenario_repo=SqlAlchemyPortfolioScenarioRepository(session),
    )


__all__ = ["RepositoryBundle", "build_repository_bundle"]
