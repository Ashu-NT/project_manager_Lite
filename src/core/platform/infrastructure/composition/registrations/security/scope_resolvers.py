"""Register Platform scope-existence and organization-ownership lookups."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.access.application.access_control_service import (
    ScopeExistsResolver as AccessScopeExistsResolver,
)
from src.core.platform.application.security.authorization.roles.role_governance_service import (
    OrganizationOwnerResolver,
)
from src.core.platform.application.security.authorization.roles.role_governance_service import (
    ScopeExistsResolver as GovernanceScopeExistsResolver,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
    SqlAlchemySiteRepository,
)


@dataclass(frozen=True)
class ScopeResolvers:
    access: dict[str, AccessScopeExistsResolver]
    governance: dict[str, GovernanceScopeExistsResolver]
    organization_owner: dict[str, OrganizationOwnerResolver]


def build_scope_resolvers(
    *,
    organization_repo: SqlAlchemyOrganizationRepository,
    site_repo: SqlAlchemySiteRepository,
) -> ScopeResolvers:
    return ScopeResolvers(
        access={
            "organization": lambda tenant_id, organization_id: (
                organization_repo.get_for_tenant(organization_id, tenant_id) is not None
            ),
            "site": lambda tenant_id, site_id: (
                site_repo.get_for_tenant(site_id, tenant_id) is not None
            ),
        },
        governance={
            "organization": lambda session, tenant_id, organization_id: (
                SqlAlchemyOrganizationRepository(session).get_for_tenant(
                    organization_id, tenant_id
                )
                is not None
            ),
            "site": lambda session, tenant_id, site_id: (
                SqlAlchemySiteRepository(session).get_for_tenant(site_id, tenant_id) is not None
            ),
        },
        organization_owner={
            "organization": lambda _session, _tenant_id, organization_id: organization_id,
            "site": lambda session, tenant_id, site_id: getattr(
                SqlAlchemySiteRepository(session).get_for_tenant(site_id, tenant_id),
                "organization_id",
                None,
            ),
        },
    )
