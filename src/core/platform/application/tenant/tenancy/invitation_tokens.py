from __future__ import annotations

import hashlib
from dataclasses import dataclass

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.tenant.tenancy import UserTenantMembership

_MINIMUM_INVITATION_TOKEN_LENGTH = 32


@dataclass(frozen=True)
class IssuedTenantInvitation:
    """Raw token returned only to the external delivery boundary after commit."""

    membership: UserTenantMembership
    token: str


def hash_invitation_token(token: str) -> str:
    normalized = str(token or "").strip()
    if len(normalized) < _MINIMUM_INVITATION_TOKEN_LENGTH:
        raise BusinessRuleError(
            "The tenant invitation token is invalid.",
            code="TENANT_INVITATION_INVALID",
        )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
