from __future__ import annotations

import src.core.platform.application.security.identity.mappers.identity as response_mapper
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.security.identity.dto.responses.identity import (
    ApiKeyCredentialDto,
    ServicePrincipalDto,
)
from src.core.platform.application.security.identity.execution_principal import (
    resolve_execution_principal,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
)
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.contract.repositories.security.identity.contracts import (
    ApiKeyCredentialRepository,
    ServicePrincipalRepository,
)
from src.core.platform.domain.security.auth import (
    UserSessionContext,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)


class ServicePrincipalQueryHandler:
    """Scoped operator reads and trusted non-interactive worker lookup."""

    def __init__(
        self, *, principal_repo: ServicePrincipalRepository,
        api_key_repo: ApiKeyCredentialRepository,
        user_repo: UserRepository, user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._principal_repo = principal_repo
        self._api_key_repo = api_key_repo
        self._user_repo = user_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def list_service_principals(self) -> list[ServicePrincipalDto]:
        require_permission(self._user_session, "auth.manage", operation_label="list service principals")
        return [response_mapper.serialize_principal(row) for row in (self._principal_repo.list_all())]

    def list_api_keys(self, principal_id: str) -> list[ApiKeyCredentialDto]:
        require_permission(self._user_session, "auth.manage", operation_label="list service-principal API keys")
        self._require_principal(principal_id)
        return [response_mapper.serialize_credential(row) for row in (self._api_key_repo.list_for_principal(principal_id))]

    def resolve_execution_principal(self, *, name: str) -> ServicePrincipal:
        """Resolve a configured non-human principal without interactive RBAC.

        This is an internal worker trust boundary, not an operator command. It
        validates the durable principal, owning organization, and service
        account while leaving transaction ownership with the caller.
        """
        ctx = self._tenant_context_service.require_active_scope_ids(
            operation_label="resolve integration worker identity"
        )
        return resolve_execution_principal(
            name=name, scope=ctx, principal_repository=self._principal_repo,
            user_repository=self._user_repo,
        )

    def _require_principal(self, principal_id: str) -> ServicePrincipal:
        principal = self._principal_repo.get(principal_id)
        if principal is None:
            raise NotFoundError("Service principal not found.", code="SERVICE_PRINCIPAL_NOT_FOUND")
        return principal

