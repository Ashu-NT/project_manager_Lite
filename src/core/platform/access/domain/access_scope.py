from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from src.core.platform.common.ids import generate_id


@dataclass
class ScopedAccessGrant:
    id: str
    scope_type: str
    scope_id: str
    user_id: str
    scope_role: str
    permission_codes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        scope_role: str,
        permission_codes: Iterable[str] | None = None,
    ) -> "ScopedAccessGrant":
        return ScopedAccessGrant(
            id=generate_id(),
            scope_type=(scope_type or "").strip().lower() or "scope",
            scope_id=(scope_id or "").strip(),
            user_id=user_id,
            scope_role=(scope_role or "").strip().lower() or "viewer",
            permission_codes=sorted(
                {
                    str(code).strip()
                    for code in (permission_codes or [])
                    if str(code).strip()
                }
            ),
        )


@dataclass
class ProjectMembership:
    id: str
    project_id: str
    user_id: str
    scope_role: str
    permission_codes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        project_id: str,
        user_id: str,
        scope_role: str,
        permission_codes: Iterable[str] | None = None,
    ) -> "ProjectMembership":
        return ProjectMembership(
            id=generate_id(),
            project_id=project_id,
            user_id=user_id,
            scope_role=(scope_role or "").strip().lower() or "viewer",
            permission_codes=sorted(
                {
                    str(code).strip()
                    for code in (permission_codes or [])
                    if str(code).strip()
                }
            ),
        )

    @property
    def scope_type(self) -> str:
        return "project"

    @property
    def scope_id(self) -> str:
        return self.project_id

    def as_scoped_access_grant(self) -> ScopedAccessGrant:
        return ScopedAccessGrant(
            id=self.id,
            scope_type=self.scope_type,
            scope_id=self.project_id,
            user_id=self.user_id,
            scope_role=self.scope_role,
            permission_codes=list(self.permission_codes or []),
            created_at=self.created_at,
        )

    @staticmethod
    def from_scoped_access_grant(grant: ScopedAccessGrant) -> "ProjectMembership":
        if (grant.scope_type or "").strip().lower() != "project":
            raise ValueError("ProjectMembership can only be created from a project-scoped grant.")
        return ProjectMembership(
            id=grant.id,
            project_id=grant.scope_id,
            user_id=grant.user_id,
            scope_role=grant.scope_role,
            permission_codes=list(grant.permission_codes or []),
            created_at=grant.created_at,
        )


__all__ = ["ProjectMembership", "ScopedAccessGrant"]
