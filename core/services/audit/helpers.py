from __future__ import annotations

from typing import Any


def record_audit(
    owner: object,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    project_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    audit_service = getattr(owner, "_audit_service", None)
    if audit_service is None:
        return
    audit_service.record(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        details=details or {},
        commit=True,
    )


__all__ = ["record_audit"]
