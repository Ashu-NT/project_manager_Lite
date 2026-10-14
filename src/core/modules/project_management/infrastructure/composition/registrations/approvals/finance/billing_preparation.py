from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.invoicing.commands.preparation_approval import (
    BillingPreparationApprovalCommandHandler,
)
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)


def build_billing_preparation_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> BillingPreparationApprovalDeps:

    bundle = build_approval_repository_context(session, tenant_context_service)
    billing_repo = wire_tenant_context_service(bundle.pm.project_billing_repo, tenant_context_service)
    clock = SystemClock()
    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    billing_preparation_commands = BillingPreparationApprovalCommandHandler(
        session=session,
        billing_repo=billing_repo,
        tenant_context_service=tenant_context_service,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        approval_repo=None,
    )
    return BillingPreparationApprovalDeps(
        billing_preparation_commands=billing_preparation_commands,
        user_session=user_session,
    )


__all__ = ["build_billing_preparation_approval_deps"]
