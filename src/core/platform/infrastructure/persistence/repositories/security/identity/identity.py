from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.security.identity.contracts import (
    ApiKeyCredentialRepository,
    ServicePrincipalRepository,
)
from src.core.platform.domain.security.identity.service_principal import ApiKeyCredential, ServicePrincipal
from src.core.platform.infrastructure.persistence.orm.security.identity.identity import (
    ApiKeyCredentialORM,
    ServicePrincipalORM,
)
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


def _principal_from_orm(row: ServicePrincipalORM) -> ServicePrincipal:
    return ServicePrincipal(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        status=row.status,
        created_by_user_id=row.created_by_user_id,
        created_at=ensure_utc_datetime(row.created_at),
        updated_at=ensure_utc_datetime(row.updated_at),
    )


def _credential_from_orm(row: ApiKeyCredentialORM) -> ApiKeyCredential:
    return ApiKeyCredential(
        id=row.id,
        tenant_id=row.tenant_id,
        service_principal_id=row.service_principal_id,
        name=row.name,
        key_prefix=row.key_prefix,
        secret_hash=row.secret_hash,
        permission_scopes=tuple(json.loads(row.permission_scopes_json or "[]")),
        expires_at=ensure_utc_datetime(row.expires_at),
        last_used_at=ensure_utc_datetime(row.last_used_at),
        revoked_at=ensure_utc_datetime(row.revoked_at),
        created_by_user_id=row.created_by_user_id,
        created_at=ensure_utc_datetime(row.created_at),
    )


class SqlAlchemyServicePrincipalRepository(
    TenantScopedRepositorySupport,
    ServicePrincipalRepository,
):
    _repository_label = "ServicePrincipalRepository"

    def __init__(self, session: Session, *, tenant_context_service: TenantContextService | None) -> None:
        self.session = session
        self._tenant_context_service = tenant_context_service

    def add(self, principal: ServicePrincipal) -> None:
        ctx = self._context(operation_label="create service principal")
        self._require_scope(principal, ctx.tenant_id, ctx.organization_id)
        self.session.add(
            ServicePrincipalORM(
                id=principal.id,
                tenant_id=principal.tenant_id,
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                name=principal.name,
                description=principal.description,
                status=principal.status,
                created_by_user_id=principal.created_by_user_id,
                created_at=principal.created_at,
                updated_at=principal.updated_at,
            )
        )
        self.session.flush()

    def update(self, principal: ServicePrincipal) -> None:
        ctx = self._context(operation_label="update service principal")
        self._require_scope(principal, ctx.tenant_id, ctx.organization_id)
        row = self._get_in_scope(
            ServicePrincipalORM,
            principal.id,
            operation_label="update service principal",
        )
        if row is None:
            return
        row.name = principal.name
        row.description = principal.description
        row.status = principal.status
        row.updated_at = principal.updated_at
        self.session.flush()

    def get(self, principal_id: str) -> ServicePrincipal | None:
        row = self._get_in_scope(
            ServicePrincipalORM,
            principal_id,
            operation_label="view service principal",
        )
        return _principal_from_orm(row) if row is not None else None

    def get_for_authentication(
        self,
        principal_id: str,
        tenant_id: str,
    ) -> ServicePrincipal | None:
        self._prepare_authentication_scope(tenant_id)
        row = self.session.execute(
            select(ServicePrincipalORM).where(
                ServicePrincipalORM.id == principal_id,
                ServicePrincipalORM.tenant_id == tenant_id,
            )
        ).scalars().first()
        return _principal_from_orm(row) if row is not None else None

    def _prepare_authentication_scope(self, tenant_id: str) -> None:
        _prepare_postgresql_authentication_scope(self.session, tenant_id)

    def list_all(self) -> list[ServicePrincipal]:
        ctx = self._context(operation_label="list service principals")
        rows = self.session.execute(
            self._apply_scope(select(ServicePrincipalORM), ServicePrincipalORM, ctx)
            .order_by(ServicePrincipalORM.name.asc())
        ).scalars().all()
        return [_principal_from_orm(row) for row in rows]

    @staticmethod
    def _require_scope(
        principal: ServicePrincipal,
        tenant_id: str,
        organization_id: str,
    ) -> None:
        if principal.tenant_id != tenant_id or principal.organization_id != organization_id:
            raise BusinessRuleError(
                "Service principal is outside the active tenant scope.",
                code="SERVICE_PRINCIPAL_SCOPE_VIOLATION",
            )


class SqlAlchemyApiKeyCredentialRepository(
    TenantScopedRepositorySupport,
    ApiKeyCredentialRepository,
):
    _repository_label = "ApiKeyCredentialRepository"

    def __init__(self, session: Session, *, tenant_context_service: TenantContextService | None) -> None:
        self.session = session
        self._tenant_context_service = tenant_context_service

    def add(self, credential: ApiKeyCredential) -> None:
        ctx = self._tenant_context(operation_label="create service-principal API key")
        self._require_tenant(credential, ctx.tenant_id)
        self.session.add(
            ApiKeyCredentialORM(
                id=credential.id,
                tenant_id=credential.tenant_id,
                service_principal_id=credential.service_principal_id,
                name=credential.name,
                key_prefix=credential.key_prefix,
                secret_hash=credential.secret_hash,
                permission_scopes_json=json.dumps(list(credential.permission_scopes)),
                expires_at=credential.expires_at,
                last_used_at=credential.last_used_at,
                revoked_at=credential.revoked_at,
                created_by_user_id=credential.created_by_user_id,
                created_at=credential.created_at,
            )
        )
        self.session.flush()

    def update(self, credential: ApiKeyCredential) -> None:
        ctx = self._tenant_context(operation_label="update service-principal API key")
        self._require_tenant(credential, ctx.tenant_id)
        row = self.session.execute(
            select(ApiKeyCredentialORM).where(
                ApiKeyCredentialORM.id == credential.id,
                ApiKeyCredentialORM.tenant_id == ctx.tenant_id,
            )
        ).scalars().first()
        if row is None:
            return
        row.name = credential.name
        row.permission_scopes_json = json.dumps(list(credential.permission_scopes))
        row.expires_at = credential.expires_at
        row.last_used_at = credential.last_used_at
        row.revoked_at = credential.revoked_at
        self.session.flush()

    def update_for_authentication(self, credential: ApiKeyCredential) -> None:
        row = self.session.execute(
            select(ApiKeyCredentialORM).where(
                ApiKeyCredentialORM.id == credential.id,
                ApiKeyCredentialORM.tenant_id == credential.tenant_id,
            )
        ).scalars().first()
        if row is None:
            return
        row.last_used_at = credential.last_used_at
        self.session.flush()

    def get(self, credential_id: str) -> ApiKeyCredential | None:
        ctx = self._tenant_context(operation_label="view service-principal API key")
        row = self.session.execute(
            select(ApiKeyCredentialORM).where(
                ApiKeyCredentialORM.id == credential_id,
                ApiKeyCredentialORM.tenant_id == ctx.tenant_id,
            )
        ).scalars().first()
        return _credential_from_orm(row) if row is not None else None

    def get_for_authentication(
        self,
        tenant_id: str,
        key_prefix: str,
    ) -> ApiKeyCredential | None:
        _prepare_postgresql_authentication_scope(self.session, tenant_id)
        row = self.session.execute(
            select(ApiKeyCredentialORM).where(
                ApiKeyCredentialORM.tenant_id == tenant_id,
                ApiKeyCredentialORM.key_prefix == key_prefix,
            )
        ).scalars().first()
        return _credential_from_orm(row) if row is not None else None

    def list_for_principal(self, principal_id: str) -> list[ApiKeyCredential]:
        ctx = self._tenant_context(operation_label="list service-principal API keys")
        rows = self.session.execute(
            select(ApiKeyCredentialORM)
            .where(
                ApiKeyCredentialORM.service_principal_id == principal_id,
                ApiKeyCredentialORM.tenant_id == ctx.tenant_id,
            )
            .order_by(ApiKeyCredentialORM.created_at.desc())
        ).scalars().all()
        return [_credential_from_orm(row) for row in rows]

    def revoke_all_for_principal(self, principal_id: str, *, revoked_at: datetime) -> int:
        ctx = self._tenant_context(operation_label="revoke service-principal API keys")
        result = self.session.execute(
            update(ApiKeyCredentialORM)
            .where(
                ApiKeyCredentialORM.service_principal_id == principal_id,
                ApiKeyCredentialORM.tenant_id == ctx.tenant_id,
                ApiKeyCredentialORM.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)

    @staticmethod
    def _require_tenant(credential: ApiKeyCredential, tenant_id: str) -> None:
        if credential.tenant_id != tenant_id:
            raise BusinessRuleError(
                "API key is outside the active tenant scope.",
                code="API_KEY_SCOPE_VIOLATION",
            )


def _prepare_postgresql_authentication_scope(session: Session, tenant_id: str) -> None:
    """Select only the token-declared tenant partition before secret verification."""
    normalized_tenant_id = str(tenant_id or "").strip()
    if not normalized_tenant_id:
        raise BusinessRuleError(
            "API-key authentication requires a tenant locator.",
            code="API_KEY_TENANT_REQUIRED",
        )
    if session.get_bind().dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": normalized_tenant_id},
    )


__all__ = [
    "SqlAlchemyApiKeyCredentialRepository",
    "SqlAlchemyServicePrincipalRepository",
]
