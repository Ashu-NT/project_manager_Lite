from __future__ import annotations

from typing import Iterable

from src.core.platform.auth.policy import DEFAULT_ROLE_PERMISSIONS
from src.core.platform.common.exceptions import ValidationError


def enforce_separation_of_duties(service, role_names: Iterable[str]) -> None:
    normalized = tuple(
        str(r or "").strip().lower()
        for r in role_names
        if str(r or "").strip()
    )
    if "admin" in normalized:
        return
    permission_codes: set[str] = set()
    for role_name in normalized:
        role = service._require_role_by_name(role_name)
        permission_codes.update(DEFAULT_ROLE_PERMISSIONS.get(role.name, set()))
    conflicts = service._sod_policy.find_conflicts(permission_codes)
    if conflicts:
        raise ValidationError(
            f"Role assignment violates separation of duties. {conflicts[0]}",
            code="ROLE_CONFLICT",
        )


__all__ = ["enforce_separation_of_duties"]
