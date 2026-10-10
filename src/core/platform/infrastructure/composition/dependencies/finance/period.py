"""Build Platform financial-period governance."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)


def build_financial_period_service(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
) -> FinancialPeriodService:
    return FinancialPeriodService(
        session=session,
        period_repo=repositories.financial_period_repo,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
    )
