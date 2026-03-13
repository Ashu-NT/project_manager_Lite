from __future__ import annotations

from core.platform.common.models import RegisterEntry
from infra.platform.db.models import RegisterEntryORM


def register_entry_to_orm(entry: RegisterEntry) -> RegisterEntryORM:
    return RegisterEntryORM(
        id=entry.id,
        project_id=entry.project_id,
        entry_type=entry.entry_type,
        title=entry.title,
        description=entry.description,
        severity=entry.severity,
        status=entry.status,
        owner_name=entry.owner_name,
        due_date=entry.due_date,
        impact_summary=entry.impact_summary,
        response_plan=entry.response_plan,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        version=getattr(entry, "version", 1),
    )


def register_entry_from_orm(obj: RegisterEntryORM) -> RegisterEntry:
    return RegisterEntry(
        id=obj.id,
        project_id=obj.project_id,
        entry_type=obj.entry_type,
        title=obj.title,
        description=obj.description,
        severity=obj.severity,
        status=obj.status,
        owner_name=obj.owner_name,
        due_date=obj.due_date,
        impact_summary=obj.impact_summary,
        response_plan=obj.response_plan,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


__all__ = ["register_entry_from_orm", "register_entry_to_orm"]
