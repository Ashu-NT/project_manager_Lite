from __future__ import annotations

from collections.abc import Iterable


_PERMISSION_CONFLICTS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"approval.request", "approval.decide"}),
        "Users cannot both request and decide the same governed approvals.",
    ),
    (
        frozenset({"access.manage", "security.manage"}),
        "Users cannot both manage scoped access and manage login security controls.",
    ),
)


def find_separation_of_duties_conflicts(permission_codes: Iterable[str]) -> list[str]:
    normalized_permissions = {
        str(permission_code).strip()
        for permission_code in permission_codes
        if str(permission_code).strip()
    }
    messages: list[str] = []
    for required_permissions, message in _PERMISSION_CONFLICTS:
        if required_permissions.issubset(normalized_permissions):
            messages.append(message)
    return messages


__all__ = ["find_separation_of_duties_conflicts"]
