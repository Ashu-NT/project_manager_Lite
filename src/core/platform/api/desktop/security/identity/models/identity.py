from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ServicePrincipalDto:
    id: str
    tenant_id: str
    organization_id: str
    user_id: str
    name: str
    description: str
    status: str
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class ApiKeyCredentialDto:
    id: str
    service_principal_id: str
    name: str
    key_prefix: str
    permission_scopes: tuple[str, ...]
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime | None


@dataclass(frozen=True)
class IssuedApiKeyDto:
    credential: ApiKeyCredentialDto
    token: str


__all__ = [
    "ApiKeyCredentialDto",
    "IssuedApiKeyDto",
    "ServicePrincipalDto",
]
