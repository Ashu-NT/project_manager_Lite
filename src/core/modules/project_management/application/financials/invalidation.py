from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinanceInvalidationScope:
    tenant_id: str
    organization_id: str
    project_id: str | None


def invalidation_scope(entity, *, project_id: str | None = None) -> FinanceInvalidationScope:
    return FinanceInvalidationScope(
        tenant_id=str(entity.tenant_id),
        organization_id=str(entity.organization_id),
        project_id=(
            str(project_id)
            if project_id is not None
            else (str(entity.project_id) if getattr(entity, "project_id", None) else None)
        ),
    )


__all__ = ["FinanceInvalidationScope", "invalidation_scope"]
