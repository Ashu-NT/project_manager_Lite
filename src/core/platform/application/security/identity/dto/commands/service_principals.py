from __future__ import annotations

from dataclasses import dataclass, field


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
