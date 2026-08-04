from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.core.platform.contract.history.audit.contracts import AuditRepository
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.auth import AuthService
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.contracts import UserRepository
from src.core.platform.auth.domain import (
    ACCOUNT_TYPE_SERVICE,
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.identity.contracts import (
    ApiKeyCredentialRepository,
    ServicePrincipalRepository,
)
from src.core.platform.identity.domain import (
    ApiKeyCredential,
    IssuedApiKey,
    SERVICE_PRINCIPAL_STATUS_ACTIVE,
    SERVICE_PRINCIPAL_STATUS_DISABLED,
    ServicePrincipal,
)
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.tenancy.tenant_context import TenantContextService

_TOKEN_PATTERN = re.compile(
    r"^pmk_([A-Za-z0-9-]{1,64})_([A-Za-z0-9]{12})_([A-Za-z0-9_-]{32,})$"
)


class ServicePrincipalService:
    """Tenant-scoped non-human identities using canonical memberships and RBAC."""

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
        auth_service: AuthService,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._session = session
        self._principal_repo = principal_repo
        self._api_key_repo = api_key_repo
        self._user_repo = user_repo
        self._tenant_repo = tenant_repo
        self._organization_repo = organization_repo
        self._membership_repo = membership_repo
        self._audit_repo = audit_repo
        self._auth_service = auth_service
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
            user = self._auth_service.register_user(
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
            self._add_audit(
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

    def list_service_principals(self) -> list[ServicePrincipal]:
        self._require_admin("list service principals")
        return self._principal_repo.list_all()

    def disable_service_principal(self, principal_id: str) -> ServicePrincipal:
        self._require_admin("disable a service principal")
        principal = self._require_principal(principal_id)
        if principal.status == SERVICE_PRINCIPAL_STATUS_DISABLED:
            return principal
        actor = self._require_actor()
        now = datetime.now(timezone.utc)
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
            self._add_audit(
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

    def list_api_keys(self, principal_id: str) -> list[ApiKeyCredential]:
        self._require_admin("list service-principal API keys")
        self._require_principal(principal_id)
        return self._api_key_repo.list_for_principal(principal_id)

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
            self._add_audit(
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
        current.revoked_at = datetime.now(timezone.utc)
        try:
            self._api_key_repo.update(current)
            self._api_key_repo.add(issued.credential)
            self._add_audit(
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
        credential.revoked_at = datetime.now(timezone.utc)
        try:
            self._api_key_repo.update(credential)
            self._add_audit(
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

    def authenticate_api_key(self, token: str) -> UserSessionPrincipal:
        tenant_id, prefix = self._parse_locator(token)
        credential = self._api_key_repo.get_for_authentication(tenant_id, prefix)
        if credential is None or not hmac.compare_digest(
            credential.secret_hash,
            self._hash_token(token),
        ):
            raise ValidationError("Invalid API key.", code="API_KEY_AUTH_FAILED")
        now = datetime.now(timezone.utc)
        if credential.revoked_at is not None:
            raise ValidationError("API key is revoked.", code="API_KEY_REVOKED")
        if credential.expires_at <= now:
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
            raise ValidationError("Service principal is inactive.", code="SERVICE_PRINCIPAL_INACTIVE")
        tenant = self._tenant_repo.get(principal_record.tenant_id)
        if tenant is None or not tenant.is_active:
            raise ValidationError("Tenant is inactive.", code="TENANT_INACTIVE")
        if not self._membership_repo.is_active_member(
            principal_record.user_id,
            principal_record.tenant_id,
        ):
            raise ValidationError("Service membership is inactive.", code="TENANT_ACCESS_DENIED")
        organization = self._organization_repo.get_for_tenant(
            principal_record.organization_id,
            principal_record.tenant_id,
        )
        if organization is None or not organization.is_active:
            raise ValidationError("Organization is inactive.", code="ORGANIZATION_INACTIVE")
        user = self._user_repo.get(principal_record.user_id)
        if (
            user is None
            or not user.is_active
            or user.account_type != ACCOUNT_TYPE_SERVICE
        ):
            raise ValidationError("Service account is inactive.", code="SERVICE_ACCOUNT_INACTIVE")
        principal = self._auth_service.build_principal_for_context(
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
            self._add_audit(
                principal=principal_record,
                operation="authenticate",
                action="identity.api_key.authenticated",
                actor_user_id=principal_record.user_id,
                metadata={"api_key_id": credential.id, "key_prefix": credential.key_prefix},
            )
            self._session.commit()
        except Exception:
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
        effective = self._auth_service.build_principal_for_context(
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
            secret_hash=self._hash_token(token),
            permission_scopes=requested,
            expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime_days),
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

    def _add_audit(
        self,
        *,
        principal: ServicePrincipal,
        operation: str,
        action: str,
        actor_user_id: str,
        metadata: dict[str, object],
    ) -> None:
        entry = AuditEntry.create(
            operation=operation,
            entity_type="service_principal",
            entity_id=principal.id,
            entity_parent_id=principal.tenant_id,
            module="identity",
            actor_id=actor_user_id,
            actor_type="user" if actor_user_id != principal.user_id else "service_principal",
            tenant_id=principal.tenant_id,
            organization_id=principal.organization_id,
            source="identity",
            severity="high",
            compliance_tag="SOC2",
            metadata={"action": action, **metadata},
        )
        self._audit_repo.add_for_tenant(entry, principal.tenant_id)

    @staticmethod
    def _service_username(tenant_id: str, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")
        return f"svc-{tenant_id[:8]}-{slug[:48] or 'service'}-{secrets.token_hex(4)}"[:128]

    @staticmethod
    def _unusable_random_password() -> str:
        return f"Aa1!{secrets.token_urlsafe(48)}"

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_locator(token: str) -> tuple[str, str]:
        match = _TOKEN_PATTERN.fullmatch(str(token or "").strip())
        if match is None:
            raise ValidationError("Invalid API key.", code="API_KEY_AUTH_FAILED")
        return match.group(1), match.group(2)


__all__ = ["ServicePrincipalService"]
