from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class ServicePrincipalCreateCommand:
    name: str
    description: str = ""
    initial_role_name: str = "viewer"


@dataclass(frozen=True)
class ApiKeyIssueCommand:
    service_principal_id: str
    name: str
    permission_scopes: tuple[str, ...] = field(default_factory=tuple)
    expires_in_days: int = 90


__all__ = [
    "ApiKeyCredentialDto",
    "ApiKeyIssueCommand",
    "IssuedApiKeyDto",
    "ServicePrincipalCreateCommand",
    "ServicePrincipalDto",
]
