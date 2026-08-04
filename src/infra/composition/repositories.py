from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

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
from src.core.modules.project_management.infrastructure.persistence.repositories.cost import (
    SqlAlchemyCostRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.financial_configuration import (
    SqlAlchemyProjectCostCodeRepository,
    SqlAlchemyProjectFinancialProfileRepository,
)
from src.core.platform.infrastructure.persistence.repositories.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.register import SqlAlchemyRegisterEntryRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.resource import SqlAlchemyResourceRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.skills import (
    SqlAlchemyResourceCertificationRepository,
    SqlAlchemyResourceSkillRepository,
    SqlAlchemyTaskSkillRequirementRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import SqlAlchemyActivityRepository
from src.core.platform.infrastructure.persistence.repositories.approval import SqlAlchemyApprovalRepository
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import SqlAlchemyAuditRepository
from src.core.platform.infrastructure.persistence.repositories.notification import SqlAlchemyNotificationRepository
from src.core.platform.infrastructure.persistence.repositories.platform_events import SqlAlchemyPlatformEventRepository
from src.core.platform.infrastructure.persistence.repositories.auth import (
    SqlAlchemyAuthPolicyReconciliationRepository,
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleBindingRepository,
    SqlAlchemyRoleDelegationPolicyRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.documents import (
    SqlAlchemyDocumentLinkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentStructureRepository,
)
from src.core.platform.infrastructure.persistence.repositories.departments import SqlAlchemyDepartmentRepository
from src.core.platform.infrastructure.persistence.repositories.employee import SqlAlchemyEmployeeRepository
from src.core.platform.infrastructure.persistence.repositories.org import SqlAlchemyOrganizationRepository
from src.core.platform.infrastructure.persistence.repositories.tenant import SqlAlchemyTenantRepository
from src.core.platform.infrastructure.persistence.repositories.user_tenant import SqlAlchemyUserTenantMembershipRepository
from src.core.platform.infrastructure.persistence.repositories.party import SqlAlchemyPartyRepository
from src.core.platform.infrastructure.persistence.repositories.sites import SqlAlchemySiteRepository
from src.core.platform.infrastructure.persistence.repositories.time import (
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
)
from src.core.platform.infrastructure.persistence.repositories.identity import (
    SqlAlchemyApiKeyCredentialRepository,
    SqlAlchemyServicePrincipalRepository,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepositoryBundle:
    project_repo: SqlAlchemyProjectRepository
    task_repo: SqlAlchemyTaskRepository
    resource_repo: SqlAlchemyResourceRepository
    employee_repo: SqlAlchemyEmployeeRepository
    tenant_repo: SqlAlchemyTenantRepository
    user_tenant_repo: SqlAlchemyUserTenantMembershipRepository
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
    project_financial_profile_repo: SqlAlchemyProjectFinancialProfileRepository
    project_cost_code_repo: SqlAlchemyProjectCostCodeRepository
    platform_calendar_repo: SqlAlchemyPlatformCalendarRepository
    calendar_working_rule_repo: SqlAlchemyCalendarWorkingRuleRepository
    calendar_exception_repo: SqlAlchemyCalendarExceptionRepository
    calendar_recurring_event_repo: SqlAlchemyCalendarRecurringEventRepository
    shift_pattern_repo: SqlAlchemyShiftPatternRepository
    calendar_assignment_repo: SqlAlchemyCalendarAssignmentRepository
    project_calendar_assignment_repo: SqlAlchemyProjectCalendarAssignmentRepository
    resource_calendar_assignment_repo: SqlAlchemyResourceCalendarAssignmentRepository
    baseline_repo: SqlAlchemyBaselineRepository
    project_resource_repo: SqlAlchemyProjectResourceRepository
    user_repo: SqlAlchemyUserRepository
    auth_session_repo: SqlAlchemyAuthSessionRepository
    auth_policy_reconciliation_repo: SqlAlchemyAuthPolicyReconciliationRepository
    role_repo: SqlAlchemyRoleRepository
    role_binding_repo: SqlAlchemyRoleBindingRepository
    role_delegation_policy_repo: SqlAlchemyRoleDelegationPolicyRepository
    permission_repo: SqlAlchemyPermissionRepository
    role_permission_repo: SqlAlchemyRolePermissionRepository
    activity_repo: SqlAlchemyActivityRepository
    audit_entry_repo: SqlAlchemyAuditRepository
    notification_repo: SqlAlchemyNotificationRepository
    platform_event_repo: SqlAlchemyPlatformEventRepository
    approval_repo: SqlAlchemyApprovalRepository
    register_repo: SqlAlchemyRegisterEntryRepository
    task_comment_repo: SqlAlchemyTaskCommentRepository
    task_presence_repo: SqlAlchemyTaskPresenceRepository
    portfolio_intake_repo: SqlAlchemyPortfolioIntakeRepository
    portfolio_project_dependency_repo: SqlAlchemyPortfolioProjectDependencyRepository
    portfolio_scoring_template_repo: SqlAlchemyPortfolioScoringTemplateRepository
    portfolio_scenario_repo: SqlAlchemyPortfolioScenarioRepository
    resource_skill_repo: SqlAlchemyResourceSkillRepository
    resource_cert_repo: SqlAlchemyResourceCertificationRepository
    task_skill_req_repo: SqlAlchemyTaskSkillRequirementRepository
    service_principal_repo: SqlAlchemyServicePrincipalRepository
    api_key_credential_repo: SqlAlchemyApiKeyCredentialRepository


def build_repository_bundle(session: Session) -> RepositoryBundle:
    started = perf_counter()
    logger.debug("Repository bundle build begin session_type=%s", type(session).__name__)
    bundle = RepositoryBundle(
        project_repo=SqlAlchemyProjectRepository(session),
        task_repo=SqlAlchemyTaskRepository(session),
        resource_repo=SqlAlchemyResourceRepository(session),
        employee_repo=SqlAlchemyEmployeeRepository(session),
        tenant_repo=SqlAlchemyTenantRepository(session),
        user_tenant_repo=SqlAlchemyUserTenantMembershipRepository(session),
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
        project_financial_profile_repo=SqlAlchemyProjectFinancialProfileRepository(session),
        project_cost_code_repo=SqlAlchemyProjectCostCodeRepository(session),
        platform_calendar_repo=SqlAlchemyPlatformCalendarRepository(session),
        calendar_working_rule_repo=SqlAlchemyCalendarWorkingRuleRepository(session),
        calendar_exception_repo=SqlAlchemyCalendarExceptionRepository(session),
        calendar_recurring_event_repo=SqlAlchemyCalendarRecurringEventRepository(session),
        shift_pattern_repo=SqlAlchemyShiftPatternRepository(session),
        calendar_assignment_repo=SqlAlchemyCalendarAssignmentRepository(session),
        project_calendar_assignment_repo=SqlAlchemyProjectCalendarAssignmentRepository(session),
        resource_calendar_assignment_repo=SqlAlchemyResourceCalendarAssignmentRepository(session),
        baseline_repo=SqlAlchemyBaselineRepository(session),
        project_resource_repo=SqlAlchemyProjectResourceRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        auth_session_repo=SqlAlchemyAuthSessionRepository(session),
        auth_policy_reconciliation_repo=SqlAlchemyAuthPolicyReconciliationRepository(
            session
        ),
        role_repo=SqlAlchemyRoleRepository(session),
        role_binding_repo=SqlAlchemyRoleBindingRepository(session),
        role_delegation_policy_repo=SqlAlchemyRoleDelegationPolicyRepository(
            session
        ),
        permission_repo=SqlAlchemyPermissionRepository(session),
        role_permission_repo=SqlAlchemyRolePermissionRepository(session),
        activity_repo=SqlAlchemyActivityRepository(session),
        audit_entry_repo=SqlAlchemyAuditRepository(session),
        notification_repo=SqlAlchemyNotificationRepository(session),
        platform_event_repo=SqlAlchemyPlatformEventRepository(session),
        approval_repo=SqlAlchemyApprovalRepository(session),
        register_repo=SqlAlchemyRegisterEntryRepository(session),
        task_comment_repo=SqlAlchemyTaskCommentRepository(session),
        task_presence_repo=SqlAlchemyTaskPresenceRepository(session),
        portfolio_intake_repo=SqlAlchemyPortfolioIntakeRepository(session),
        portfolio_project_dependency_repo=SqlAlchemyPortfolioProjectDependencyRepository(session),
        portfolio_scoring_template_repo=SqlAlchemyPortfolioScoringTemplateRepository(session),
        portfolio_scenario_repo=SqlAlchemyPortfolioScenarioRepository(session),
        resource_skill_repo=SqlAlchemyResourceSkillRepository(session),
        resource_cert_repo=SqlAlchemyResourceCertificationRepository(session),
        task_skill_req_repo=SqlAlchemyTaskSkillRequirementRepository(session),
        service_principal_repo=SqlAlchemyServicePrincipalRepository(
            session,
            tenant_context_service=None,
        ),
        api_key_credential_repo=SqlAlchemyApiKeyCredentialRepository(
            session,
            tenant_context_service=None,
        ),
    )
    logger.debug(
        "Repository bundle build complete duration_ms=%.1f repository_count=%s",
        (perf_counter() - started) * 1000,
        len(bundle.__dataclass_fields__),
    )
    return bundle


__all__ = ["RepositoryBundle", "build_repository_bundle"]
