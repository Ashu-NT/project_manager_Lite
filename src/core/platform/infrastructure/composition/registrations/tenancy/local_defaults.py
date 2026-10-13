"""Explicit local-desktop tenant defaults; hosted SaaS never invokes these."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.domain.master_data.org import ORGANIZATION_STATUS_ACTIVE
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.tenant.tenancy import Tenant, UserTenantMembership
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)

logger = logging.getLogger(__name__)


def bootstrap_local_single_tenant_context(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    organization_service: OrganizationService,
) -> None:
    """Preserve explicit local-desktop defaults outside hosted SaaS mode."""
    default_tenant = repositories.tenant_repo.get_default()
    if default_tenant is None:
        existing_organizations = repositories.organization_repo.list_all()
        tenant_code = (
            existing_organizations[0].organization_code
            if existing_organizations
            else "DEFAULT"
        )
        tenant_name = (
            existing_organizations[0].display_name
            if existing_organizations
            else "Default Tenant"
        )
        default_tenant = Tenant.create(
            tenant_code=tenant_code,
            display_name=tenant_name,
        )
        repositories.tenant_repo.add(default_tenant)
        session.flush()
        for organization in existing_organizations:
            if not organization.tenant_id:
                organization.tenant_id = default_tenant.id
                repositories.organization_repo.update(organization)
        session.commit()
        logger.debug(
            "Platform local default tenant bootstrapped tenant_id=%s",
            default_tenant.id,
        )

    user_session.set_active_tenant_id(default_tenant.id)
    organization_service.bootstrap_defaults()

    organizations = repositories.organization_repo.list_for_tenant(
        default_tenant.id,
        status=ORGANIZATION_STATUS_ACTIVE,
    )
    if not organizations:
        organizations = repositories.organization_repo.list_for_tenant(
            default_tenant.id
        )
    if organizations:
        user_session.set_active_organization_id(organizations[0].id)

    for user in repositories.user_repo.list_all():
        if repositories.user_tenant_repo.get(
            user.id,
            default_tenant.id,
        ) is not None:
            continue
        repositories.user_tenant_repo.add(
            UserTenantMembership.create(
                user_id=user.id,
                tenant_id=default_tenant.id,
            )
        )
    session.commit()
