from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from core.platform.common.exceptions import ValidationError


RoleNormalizer = Callable[[str], str]
PermissionResolver = Callable[[str], Iterable[str]]


@dataclass(frozen=True)
class ScopedRolePolicy:
    scope_type: str
    role_choices: tuple[str, ...]
    normalize_role: RoleNormalizer
    resolve_permissions: PermissionResolver


class ScopedRolePolicyRegistry:
    def __init__(self, policies: Iterable[ScopedRolePolicy] | None = None) -> None:
        self._policies: dict[str, ScopedRolePolicy] = {}
        for policy in policies or ():
            self.register(policy)

    def register(self, policy: ScopedRolePolicy) -> None:
        scope_type = self.normalize_scope_type(policy.scope_type)
        self._policies[scope_type] = ScopedRolePolicy(
            scope_type=scope_type,
            role_choices=tuple(
                str(choice or "").strip().lower()
                for choice in policy.role_choices
                if str(choice or "").strip()
            ),
            normalize_role=policy.normalize_role,
            resolve_permissions=policy.resolve_permissions,
        )

    def get(self, scope_type: str) -> ScopedRolePolicy:
        normalized_scope_type = self.normalize_scope_type(scope_type)
        try:
            return self._policies[normalized_scope_type]
        except KeyError as exc:
            raise ValidationError(
                f"Unsupported scope type '{normalized_scope_type}'.",
                code="UNSUPPORTED_SCOPE_TYPE",
            ) from exc

    def has(self, scope_type: str) -> bool:
        return self.normalize_scope_type(scope_type) in self._policies

    def list_scope_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._policies.keys()))

    @staticmethod
    def normalize_scope_type(scope_type: str) -> str:
        normalized = str(scope_type or "").strip().lower()
        if not normalized:
            raise ValidationError("Scope type is required.", code="SCOPE_TYPE_REQUIRED")
        return normalized


__all__ = [
    "PermissionResolver",
    "RoleNormalizer",
    "ScopedRolePolicy",
    "ScopedRolePolicyRegistry",
]
