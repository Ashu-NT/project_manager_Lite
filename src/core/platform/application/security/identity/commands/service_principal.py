from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.core.platform.application.security.auth import UserRegistrationHandler
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.security.identity.credential_policy import (
    hash_api_key,
    record_service_principal_audit,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.contract.repositories.security.identity.contracts import (
    ApiKeyCredentialRepository,
    ServicePrincipalRepository,
)
from src.core.platform.domain.security.auth import (
    ACCOUNT_TYPE_SERVICE,
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.identity.service_principal import (
    SERVICE_PRINCIPAL_STATUS_ACTIVE,
    SERVICE_PRINCIPAL_STATUS_DISABLED,
    ApiKeyCredential,
    IssuedApiKey,
    ServicePrincipal,
)


class ServicePrincipalCommandHandler:
    """Administer service identities and credentials with atomic audit writes."""

    def __init__(
        self,
        *,
        session: Session,
        principal_repo: ServicePrincipalRepository,
        api_key_repo: ApiKeyCredentialRepository,
        user_repo: UserRepository,
        audit_repo: AuditRepository,
        registration: UserRegistrationHandler,
        principals: PrincipalBuilder,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._session = session
        self._principal_repo = principal_repo
        self._api_key_repo = api_key_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._registration = registration
        self._principals = principals
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_service_principal(
        self,
        *,
        name: str,
        description: str = "",
        initial_role_name: str = "viewer",
    ) -> ServicePrincipal:
        self._require_admin("create a service principal", include_role_assignment=True)
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="create a service principal"
        )
        actor = self._require_actor()
        username = self._service_username(ctx.tenant_id, name)
        try:
            user = self._registration.register_user(
                username=username,
                raw_password=self._unusable_random_password(),
                display_name=name,
                is_active=True,
                role_names=(initial_role_name,),
                tenant_id=ctx.tenant_id,
                commit=False,
                account_type=ACCOUNT_TYPE_SERVICE,
            )
            principal = ServicePrincipal.create(
                tenant_id=ctx.tenant_id,
                organization_id=ctx.organization_id,
                user_id=user.id,
                name=name,
                description=description,
                created_by_user_id=actor.user_id,
            )
            self._principal_repo.add(principal)
            record_service_principal_audit(self._audit_repo,
                principal=principal,
                operation="create",
                action="identity.service_principal.created",
                actor_user_id=actor.user_id,
                metadata={"initial_role_name": initial_role_name},
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return principal

    def disable_service_principal(self, principal_id: str) -> ServicePrincipal:
        self._require_admin("disable a service principal")
        principal = self._require_principal(principal_id)
        if principal.status == SERVICE_PRINCIPAL_STATUS_DISABLED:
            return principal
        actor = self._require_actor()
        now = datetime.now(UTC)
        principal.status = SERVICE_PRINCIPAL_STATUS_DISABLED
        principal.updated_at = now
        user = self._user_repo.get(principal.user_id)
        if user is None:
            raise NotFoundError("Service account not found.", code="SERVICE_ACCOUNT_NOT_FOUND")
        user.is_active = False
        user.session_revision += 1
        user.updated_at = now
        try:
            self._principal_repo.update(principal)
            self._user_repo.update(user)
            revoked_count = self._api_key_repo.revoke_all_for_principal(
                principal.id,
                revoked_at=now,
            )
            record_service_principal_audit(self._audit_repo,
                principal=principal,
                operation="disable",
                action="identity.service_principal.disabled",
                actor_user_id=actor.user_id,
                metadata={"revoked_api_key_count": revoked_count},
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return principal

    def issue_api_key(
        self,
        principal_id: str,
        *,
        name: str,
        permission_scopes: tuple[str, ...],
        expires_in_days: int = 90,
    ) -> IssuedApiKey:
        self._require_admin("issue a service-principal API key")
        principal = self._require_active_principal(principal_id)
        actor = self._require_actor()
        issued = self._build_api_key(
            principal,
            name=name,
            permission_scopes=permission_scopes,
            expires_in_days=expires_in_days,
            created_by_user_id=actor.user_id,
        )
        try:
            self._api_key_repo.add(issued.credential)
            record_service_principal_audit(self._audit_repo,
                principal=principal,
                operation="create",
                action="identity.api_key.issued",
                actor_user_id=actor.user_id,
                metadata={
                    "api_key_id": issued.credential.id,
                    "key_prefix": issued.credential.key_prefix,
                    "permission_scopes": list(issued.credential.permission_scopes),
                    "expires_at": issued.credential.expires_at.isoformat(),
                },
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return issued

    def rotate_api_key(
        self,
        credential_id: str,
        *,
        expires_in_days: int = 90,
    ) -> IssuedApiKey:
        self._require_admin("rotate a service-principal API key")
        current = self._require_credential(credential_id)
        principal = self._require_active_principal(current.service_principal_id)
        if current.revoked_at is not None:
            raise BusinessRuleError("Revoked API keys cannot be rotated.", code="API_KEY_REVOKED")
        actor = self._require_actor()
        issued = self._build_api_key(
            principal,
            name=current.name,
            permission_scopes=current.permission_scopes,
            expires_in_days=expires_in_days,
            created_by_user_id=actor.user_id,
        )
        current.revoked_at = datetime.now(UTC)
        try:
            self._api_key_repo.update(current)
            self._api_key_repo.add(issued.credential)
            record_service_principal_audit(self._audit_repo,
                principal=principal,
                operation="rotate",
                action="identity.api_key.rotated",
                actor_user_id=actor.user_id,
                metadata={
                    "previous_api_key_id": current.id,
                    "api_key_id": issued.credential.id,
                    "key_prefix": issued.credential.key_prefix,
                },
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return issued

    def revoke_api_key(self, credential_id: str) -> ApiKeyCredential:
        self._require_admin("revoke a service-principal API key")
        credential = self._require_credential(credential_id)
        if credential.revoked_at is not None:
            return credential
        principal = self._require_principal(credential.service_principal_id)
        actor = self._require_actor()
        credential.revoked_at = datetime.now(UTC)
        try:
            self._api_key_repo.update(credential)
            record_service_principal_audit(self._audit_repo,
                principal=principal,
                operation="revoke",
                action="identity.api_key.revoked",
                actor_user_id=actor.user_id,
                metadata={"api_key_id": credential.id},
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return credential

    def _build_api_key(
        self,
        principal: ServicePrincipal,
        *,
        name: str,
        permission_scopes: tuple[str, ...],
        expires_in_days: int,
        created_by_user_id: str,
    ) -> IssuedApiKey:
        try:
            lifetime_days = int(expires_in_days)
        except (TypeError, ValueError) as exc:
            raise ValidationError("API-key lifetime is invalid.", code="API_KEY_EXPIRY_INVALID") from exc
        if lifetime_days < 1 or lifetime_days > 365:
            raise ValidationError(
                "API-key lifetime must be between 1 and 365 days.",
                code="API_KEY_EXPIRY_INVALID",
            )
        user = self._user_repo.get(principal.user_id)
        if user is None:
            raise NotFoundError("Service account not found.", code="SERVICE_ACCOUNT_NOT_FOUND")
        effective = self._principals.build_for_context(
            user,
            tenant_id=principal.tenant_id,
            organization_id=principal.organization_id,
        )
        assignable_permissions = set(effective.permissions)
        for scope_rows in effective.scoped_access.values():
            for permissions in scope_rows.values():
                assignable_permissions.update(permissions)
        requested = tuple(
            sorted({str(code or "").strip().lower() for code in permission_scopes if str(code or "").strip()})
        )
        if not requested:
            raise ValidationError(
                "At least one API-key permission is required.",
                code="API_KEY_SCOPE_REQUIRED",
            )
        excess = set(requested) - assignable_permissions
        if excess:
            raise BusinessRuleError(
                "API-key permissions exceed the service principal's authority.",
                code="API_KEY_PERMISSION_CEILING_EXCEEDED",
            )
        prefix = secrets.token_hex(6)
        token = f"pmk_{principal.tenant_id}_{prefix}_{secrets.token_urlsafe(32)}"
        credential = ApiKeyCredential.create(
            tenant_id=principal.tenant_id,
            service_principal_id=principal.id,
            name=name,
            key_prefix=prefix,
            secret_hash=hash_api_key(token),
            permission_scopes=requested,
            expires_at=datetime.now(UTC) + timedelta(days=lifetime_days),
            created_by_user_id=created_by_user_id,
        )
        return IssuedApiKey(credential=credential, token=token)

    def _require_admin(self, operation_label: str, *, include_role_assignment: bool = False) -> None:
        require_permission(self._user_session, "auth.manage", operation_label=operation_label)
        if include_role_assignment:
            require_permission(
                self._user_session,
                "auth.role.assign",
                operation_label=operation_label,
            )

    def _require_actor(self) -> UserSessionPrincipal:
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError("Authentication is required.", code="AUTHENTICATION_REQUIRED")
        return principal

    def _require_principal(self, principal_id: str) -> ServicePrincipal:
        principal = self._principal_repo.get(principal_id)
        if principal is None:
            raise NotFoundError("Service principal not found.", code="SERVICE_PRINCIPAL_NOT_FOUND")
        return principal

    def _require_active_principal(self, principal_id: str) -> ServicePrincipal:
        principal = self._require_principal(principal_id)
        if principal.status != SERVICE_PRINCIPAL_STATUS_ACTIVE:
            raise BusinessRuleError("Service principal is disabled.", code="SERVICE_PRINCIPAL_DISABLED")
        return principal

    def _require_credential(self, credential_id: str) -> ApiKeyCredential:
        credential = self._api_key_repo.get(credential_id)
        if credential is None:
            raise NotFoundError("API key not found.", code="API_KEY_NOT_FOUND")
        return credential

    @staticmethod
    def _service_username(tenant_id: str, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")
        return f"svc-{tenant_id[:8]}-{slug[:48] or 'service'}-{secrets.token_hex(4)}"[:128]

    @staticmethod
    def _unusable_random_password() -> str:
        return f"Aa1!{secrets.token_urlsafe(48)}"

