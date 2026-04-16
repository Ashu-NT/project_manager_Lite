from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.platform import (
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogService,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from core.platform.access import AccessControlService, ScopedRolePolicy, ScopedRolePolicyRegistry
from core.platform.approval import ApprovalService
from core.platform.audit import AuditService
from core.platform.auth import AuthService
from core.platform.auth.session import UserSessionContext
from core.platform.documents import DocumentIntegrationService, DocumentService
from core.platform.data_exchange import MasterDataExchangeService
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.org.access_policy import (
    SITE_SCOPE_ROLE_CHOICES,
    normalize_site_scope_role,
    resolve_site_scope_permissions,
)
from core.platform.org import DepartmentService, EmployeeService, OrganizationService, SiteService
from core.platform.party import PartyService
from core.platform.party.interfaces import PartyRepository
from src.core.platform.runtime_tracking import RuntimeExecutionService
from src.infra.persistence.db.platform.modules import SqlAlchemyModuleEntitlementRepository
from src.infra.persistence.db.platform.runtime_tracking import SqlAlchemyRuntimeExecutionRepository
from src.infra.composition.repositories import RepositoryBundle


@dataclass(frozen=True)
class PlatformServiceBundle:
    session: Session
    user_session: UserSessionContext
    organization_repo: OrganizationRepository
    site_repo: SiteRepository
    party_repo: PartyRepository
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
    module_catalog_service: ModuleCatalogService
    auth_service: AuthService
    organization_service: OrganizationService
    document_service: DocumentService
    document_integration_service: DocumentIntegrationService
    party_service: PartyService
    department_service: DepartmentService
    site_service: SiteService
    employee_service: EmployeeService
    master_data_exchange_service: MasterDataExchangeService
    runtime_execution_service: RuntimeExecutionService
    access_service: AccessControlService
    audit_service: AuditService
    approval_service: ApprovalService


def build_platform_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
) -> PlatformServiceBundle:
    user_session = UserSessionContext()
    audit_service = AuditService(
        session=session,
        audit_repo=repositories.audit_repo,
        user_session=user_session,
    )
    approval_service = ApprovalService(
        session=session,
        approval_repo=repositories.approval_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    auth_service = AuthService(
        session=session,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        user_role_repo=repositories.user_role_repo,
        role_permission_repo=repositories.role_permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        scoped_access_repo=repositories.scoped_access_repo,
        project_membership_repo=repositories.project_membership_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    user_session.set_validator(auth_service.validate_session_principal)
    auth_service.bootstrap_defaults()

    organization_service = OrganizationService(
        session=session,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    organization_service.bootstrap_defaults()

    document_service = DocumentService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    document_integration_service = DocumentIntegrationService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    party_service = PartyService(
        session=session,
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    site_service = SiteService(
        session=session,
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    department_service = DepartmentService(
        session=session,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        employee_repo=repositories.employee_repo,
        user_session=user_session,
        audit_service=audit_service,
    )

    def _active_organization():
        return repositories.organization_repo.get_active()

    def _active_organization_id() -> str | None:
        organization = _active_organization()
        return organization.id if organization is not None else None

    module_entitlement_repo = SqlAlchemyModuleEntitlementRepository(
        session,
        organization_id_provider=_active_organization_id,
    )
    module_catalog_service = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(os.getenv("PM_ENABLED_MODULES")),
        licensed_codes=parse_licensed_module_codes(
            os.getenv("PM_LICENSED_MODULES")
            if os.getenv("PM_LICENSED_MODULES") is not None
            else os.getenv("PM_ENABLED_MODULES")
        ),
        entitlement_repo=module_entitlement_repo,
        session=session,
        user_session=user_session,
        audit_service=audit_service,
        organization_context_provider=_active_organization,
    )
    module_catalog_service.bootstrap_defaults()
    module_runtime_service = ModuleRuntimeService(module_catalog_service)
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_runtime_service=module_runtime_service,
        organization_service=organization_service,
    )
    runtime_execution_service = RuntimeExecutionService(
        runtime_execution_repo=SqlAlchemyRuntimeExecutionRepository(session),
        user_session=user_session,
    )
    access_service = AccessControlService(
        session=session,
        membership_repo=repositories.project_membership_repo,
        user_repo=repositories.user_repo,
        auth_service=auth_service,
        policy_registry=ScopedRolePolicyRegistry(
            (
                ScopedRolePolicy(
                    scope_type="site",
                    role_choices=SITE_SCOPE_ROLE_CHOICES,
                    normalize_role=normalize_site_scope_role,
                    resolve_permissions=resolve_site_scope_permissions,
                ),
            )
        ),
        scoped_access_repo=repositories.scoped_access_repo,
        scope_exists_resolvers={
            "site": lambda site_id: repositories.site_repo.get(site_id) is not None,
        },
        user_session=user_session,
        audit_service=audit_service,
    )
    employee_service = EmployeeService(
        session=session,
        employee_repo=repositories.employee_repo,
        resource_repo=repositories.resource_repo,
        site_repo=repositories.site_repo,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    master_data_exchange_service = MasterDataExchangeService(
        site_service=site_service,
        party_service=party_service,
        user_session=user_session,
    )

    return PlatformServiceBundle(
        session=session,
        user_session=user_session,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        party_repo=repositories.party_repo,
        platform_runtime_application_service=platform_runtime_application_service,
        module_runtime_service=module_runtime_service,
        module_catalog_service=module_catalog_service,
        auth_service=auth_service,
        organization_service=organization_service,
        document_service=document_service,
        document_integration_service=document_integration_service,
        party_service=party_service,
        department_service=department_service,
        site_service=site_service,
        employee_service=employee_service,
        master_data_exchange_service=master_data_exchange_service,
        runtime_execution_service=runtime_execution_service,
        access_service=access_service,
        audit_service=audit_service,
        approval_service=approval_service,
    )


__all__ = ["PlatformServiceBundle", "build_platform_service_bundle"]
