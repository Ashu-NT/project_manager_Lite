from __future__ import annotations

from src.core.platform.access.application.dto.responses.scoped_access import (
    ScopedAccessGrantDto,
)
from src.core.platform.access.domain import ScopedAccessGrant


def serialize_grant(grant: ScopedAccessGrant) -> ScopedAccessGrantDto:
    return ScopedAccessGrantDto(
        id=grant.id,
        scope_type=grant.scope_type,
        scope_id=grant.scope_id,
        user_id=grant.user_id,
        scope_role=grant.scope_role,
        permission_codes=tuple(grant.permission_codes or ()),
        created_at=grant.created_at,
    )
