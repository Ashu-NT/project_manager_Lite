from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
    SqlAlchemyApprovalRepository,
)
from src.core.platform.infrastructure.persistence.repositories.finance import (
    SqlAlchemyFinancialPeriodRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import (
    SqlAlchemyActivityRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.platform_events.platform_events import (
    SqlAlchemyPlatformEventRepository,
)
from src.core.platform.infrastructure.persistence.repositories.integration.procurement_financial_outbox import (
    SqlAlchemyProcurementFinancialOutboxRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.department.departments import (
    SqlAlchemyDepartmentRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.documents.documents import (
    SqlAlchemyDocumentLinkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentStructureRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.employee.employee import (
    SqlAlchemyEmployeeRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.party.party import (
    SqlAlchemyPartyRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
    SqlAlchemySiteRepository,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
    SqlAlchemyNotificationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyAuthPolicyReconciliationRepository,
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleBindingRepository,
    SqlAlchemyRoleDelegationPolicyRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.identity.identity import (
    SqlAlchemyApiKeyCredentialRepository,
    SqlAlchemyServicePrincipalRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.calendar.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.time.time import (
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.time_financial_outbox import (
    SqlAlchemyTimeFinancialOutboxRepository,
)


@dataclass(frozen=True)
class PlatformRepositories:
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
    time_entry_repo: SqlAlchemyTimeEntryRepository
    timesheet_period_repo: SqlAlchemyTimesheetPeriodRepository
    financial_period_repo: SqlAlchemyFinancialPeriodRepository
    platform_calendar_repo: SqlAlchemyPlatformCalendarRepository
    calendar_working_rule_repo: SqlAlchemyCalendarWorkingRuleRepository
    calendar_exception_repo: SqlAlchemyCalendarExceptionRepository
    calendar_recurring_event_repo: SqlAlchemyCalendarRecurringEventRepository
    shift_pattern_repo: SqlAlchemyShiftPatternRepository
    calendar_assignment_repo: SqlAlchemyCalendarAssignmentRepository
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
    service_principal_repo: SqlAlchemyServicePrincipalRepository
    api_key_credential_repo: SqlAlchemyApiKeyCredentialRepository
    time_financial_outbox_repo: SqlAlchemyTimeFinancialOutboxRepository
    procurement_financial_outbox_repo: SqlAlchemyProcurementFinancialOutboxRepository


def build_platform_repositories(session: Session) -> PlatformRepositories:
    return PlatformRepositories(
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
        time_entry_repo=SqlAlchemyTimeEntryRepository(session),
        timesheet_period_repo=SqlAlchemyTimesheetPeriodRepository(session),
        financial_period_repo=SqlAlchemyFinancialPeriodRepository(session),
        platform_calendar_repo=SqlAlchemyPlatformCalendarRepository(session),
        calendar_working_rule_repo=SqlAlchemyCalendarWorkingRuleRepository(session),
        calendar_exception_repo=SqlAlchemyCalendarExceptionRepository(session),
        calendar_recurring_event_repo=SqlAlchemyCalendarRecurringEventRepository(session),
        shift_pattern_repo=SqlAlchemyShiftPatternRepository(session),
        calendar_assignment_repo=SqlAlchemyCalendarAssignmentRepository(session),
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
        service_principal_repo=SqlAlchemyServicePrincipalRepository(
                    session,
                    tenant_context_service=None,
                ),
        api_key_credential_repo=SqlAlchemyApiKeyCredentialRepository(
                    session,
                    tenant_context_service=None,
                ),
        time_financial_outbox_repo=SqlAlchemyTimeFinancialOutboxRepository(session),
        procurement_financial_outbox_repo=SqlAlchemyProcurementFinancialOutboxRepository(session),
    )
