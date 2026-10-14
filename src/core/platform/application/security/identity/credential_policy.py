from __future__ import annotations

import hashlib
import re

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)

_TOKEN_PATTERN = re.compile(
    r"^pmk_([A-Za-z0-9-]{1,64})_([A-Za-z0-9]{12})_([A-Za-z0-9_-]{32,})$"
)


def record_service_principal_audit(
    audit_repo: AuditRepository,
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
        category="SECURITY",
        metadata={"action": action, **metadata},
    )
    audit_repo.add_for_tenant(entry, principal.tenant_id)


def hash_api_key(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def parse_api_key_locator(token: str) -> tuple[str, str]:
    match = _TOKEN_PATTERN.fullmatch(str(token or "").strip())
    if match is None:
        raise ValidationError("Invalid API key.", code="API_KEY_AUTH_FAILED")
    return match.group(1), match.group(2)

