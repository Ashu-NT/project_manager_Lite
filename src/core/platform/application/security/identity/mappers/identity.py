from __future__ import annotations

from datetime import datetime
from typing import cast

from src.core.platform.application.security.identity.dto.responses.identity import (
    ApiKeyCredentialDto,
    IssuedApiKeyDto,
    ServicePrincipalDto,
)
from src.core.platform.domain.security.identity.service_principal import (
    ApiKeyCredential,
    IssuedApiKey,
    ServicePrincipal,
)


def serialize_principal(row: ServicePrincipal) -> ServicePrincipalDto:
    return ServicePrincipalDto(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def serialize_credential(row: ApiKeyCredential) -> ApiKeyCredentialDto:
    return ApiKeyCredentialDto(
        id=row.id,
        service_principal_id=row.service_principal_id,
        name=row.name,
        key_prefix=row.key_prefix,
        permission_scopes=row.permission_scopes,
        expires_at=cast(datetime, row.expires_at),
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
    )


def serialize_issued(row: IssuedApiKey) -> IssuedApiKeyDto:
    return IssuedApiKeyDto(
        credential=serialize_credential(row.credential),
        token=row.token,
    )
