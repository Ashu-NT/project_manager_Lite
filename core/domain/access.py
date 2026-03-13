from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from core.domain.identifiers import generate_id


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


__all__ = ["ProjectMembership"]
