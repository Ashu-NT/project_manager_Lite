from __future__ import annotations

import hmac
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.identity.credential_policy import (
    hash_api_key,
    parse_api_key_locator,
    record_service_principal_audit,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ValidationError,
)
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.contract.repositories.security.identity.contracts import (
    ApiKeyCredentialRepository,
    ServicePrincipalRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.domain.master_data.org import ORGANIZATION_STATUS_ACTIVE
from src.core.platform.domain.security.auth import (
    ACCOUNT_TYPE_SERVICE,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.identity.service_principal import (
    SERVICE_PRINCIPAL_STATUS_ACTIVE,
)


class ApiKeyAuthenticationHandler:
    """Authenticate API keys and atomically persist use and audit evidence."""

    def __init__(
        self,
        *,
        session: Session,
        principal_repo: ServicePrincipalRepository,
        api_key_repo: ApiKeyCredentialRepository,
        user_repo: UserRepository,
        tenant_repo: TenantRepository,
        organization_repo: OrganizationRepository,
        membership_repo: UserTenantMembershipRepository,
        audit_repo: AuditRepository,
        principals: PrincipalBuilder,
    ) -> None:
        self._session = session
        self._principal_repo = principal_repo
        self._api_key_repo = api_key_repo
        self._user_repo = user_repo
        self._tenant_repo = tenant_repo
        self._organization_repo = organization_repo
        self._membership_repo = membership_repo
        self._audit_repo = audit_repo
        self._principals = principals

    def authenticate_api_key(self, token: str) -> UserSessionPrincipal:
        tenant_id, prefix = parse_api_key_locator(token)
        credential = self._api_key_repo.get_for_authentication(tenant_id, prefix)
        if credential is None or not hmac.compare_digest(
            credential.secret_hash,
            hash_api_key(token),
        ):
            raise ValidationError("Invalid API key.", code="API_KEY_AUTH_FAILED")
        now = datetime.now(UTC)
        if credential.revoked_at is not None:
            raise ValidationError("API key is revoked.", code="API_KEY_REVOKED")
        if credential.expires_at is None or credential.expires_at <= now:
            raise ValidationError("API key has expired.", code="API_KEY_EXPIRED")
        principal_record = self._principal_repo.get_for_authentication(
            credential.service_principal_id,
            credential.tenant_id,
        )
        if (
            principal_record is None
            or principal_record.tenant_id != credential.tenant_id
            or principal_record.status != SERVICE_PRINCIPAL_STATUS_ACTIVE
        ):
            raise ValidationError(
                "Service principal is inactive.", code="SERVICE_PRINCIPAL_INACTIVE"
            )
        tenant = self._tenant_repo.get(principal_record.tenant_id)
        if tenant is None or not tenant.is_active:
            raise ValidationError("Tenant is inactive.", code="TENANT_INACTIVE")
        if not self._membership_repo.is_active_member(
            principal_record.user_id,
            principal_record.tenant_id,
        ):
            raise ValidationError(
                "Service membership is inactive.", code="TENANT_ACCESS_DENIED"
            )
        organization = self._organization_repo.get_for_tenant(
            principal_record.organization_id,
            principal_record.tenant_id,
        )
        if organization is None or organization.status != ORGANIZATION_STATUS_ACTIVE:
            raise ValidationError(
                "Organization is inactive.", code="ORGANIZATION_INACTIVE"
            )
        user = self._user_repo.get(principal_record.user_id)
        if (
            user is None
            or not user.is_active
            or user.account_type != ACCOUNT_TYPE_SERVICE
        ):
            raise ValidationError(
                "Service account is inactive.", code="SERVICE_ACCOUNT_INACTIVE"
            )
        principal = self._principals.build_for_context(
            user,
            tenant_id=principal_record.tenant_id,
            organization_id=principal_record.organization_id,
            session_id=credential.id,
        )
        allowed = frozenset(credential.permission_scopes)
        scoped_access = {
            scope_type: {
                scope_id: frozenset(permissions).intersection(allowed)
                for scope_id, permissions in scope_rows.items()
            }
            for scope_type, scope_rows in principal.scoped_access.items()
        }
        credential.last_used_at = now
        try:
            self._api_key_repo.update_for_authentication(credential)
            record_service_principal_audit(
                self._audit_repo,
                principal=principal_record,
                operation="authenticate",
                action="identity.api_key.authenticated",
                actor_user_id=principal_record.user_id,
                metadata={
                    "api_key_id": credential.id,
                    "key_prefix": credential.key_prefix,
                },
            )
            self._session.commit()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            raise BusinessRuleError(
                "API-key authentication audit could not be persisted.",
                code="AUTH_AUDIT_UNAVAILABLE",
            )
        return replace(
            principal,
            permissions=principal.permissions.intersection(allowed),
            scoped_access=scoped_access,
            project_access=dict(scoped_access.get("project", {})),
            identity_provider="api_key",
            last_login_auth_method="api_key",
            session_id=credential.id,
            session_expires_at=min(
                value
                for value in (principal.session_expires_at, credential.expires_at)
                if value is not None
            ),
        )
