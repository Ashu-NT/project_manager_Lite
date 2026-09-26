from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth import ACCOUNT_TYPE_SERVICE
from src.core.platform.domain.security.identity.service_principal import (
    SERVICE_PRINCIPAL_STATUS_ACTIVE,
)


def resolve_execution_principal(*, name, scope, principal_repository, user_repository):
    """Trusted runtime identity resolution, never impersonation of a requesting user."""
    principal = principal_repository.get_by_name(name)
    if principal is None:
        raise BusinessRuleError(
            "Integration service principal is not configured.",
            code="INTEGRATION_SERVICE_PRINCIPAL_NOT_CONFIGURED",
        )
    if (principal.tenant_id, principal.organization_id) != (
        scope.tenant_id,
        scope.organization_id,
    ):
        raise BusinessRuleError(
            "Integration service principal is outside the active scope.",
            code="INTEGRATION_SERVICE_PRINCIPAL_SCOPE_MISMATCH",
        )
    if principal.status != SERVICE_PRINCIPAL_STATUS_ACTIVE:
        raise BusinessRuleError(
            "Integration service principal is disabled.",
            code="INTEGRATION_SERVICE_PRINCIPAL_DISABLED",
        )
    user = user_repository.get(principal.user_id)
    if user is None or not user.is_active or user.account_type != ACCOUNT_TYPE_SERVICE:
        raise BusinessRuleError(
            "Integration service account is inactive or invalid.",
            code="INTEGRATION_SERVICE_ACCOUNT_INVALID",
        )
    return principal
