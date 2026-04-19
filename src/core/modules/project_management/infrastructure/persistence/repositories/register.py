from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.project_management.interfaces import RegisterEntryRepository
from core.modules.project_management.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.register import register_entry_from_orm, register_entry_to_orm


class SqlAlchemyRegisterEntryRepository(RegisterEntryRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, entry: RegisterEntry) -> None:
        self.session.add(register_entry_to_orm(entry))

    def update(self, entry: RegisterEntry) -> None:
        entry.version = update_with_version_check(
            self.session,
            RegisterEntryORM,
            entry.id,
            getattr(entry, "version", 1),
            {
                "project_id": entry.project_id,
                "entry_type": entry.entry_type,
                "title": entry.title,
                "description": entry.description,
                "severity": entry.severity,
                "status": entry.status,
                "owner_name": entry.owner_name,
                "due_date": entry.due_date,
                "impact_summary": entry.impact_summary,
                "response_plan": entry.response_plan,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            },
            not_found_message="Register entry not found.",
            stale_message="Register entry was updated by another user.",
        )

    def delete(self, entry_id: str) -> None:
        self.session.query(RegisterEntryORM).filter_by(id=entry_id).delete()

    def get(self, entry_id: str) -> RegisterEntry | None:
        obj = self.session.get(RegisterEntryORM, entry_id)
        return register_entry_from_orm(obj) if obj else None

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[RegisterEntry]:
        stmt = select(RegisterEntryORM)
        if project_id:
            stmt = stmt.where(RegisterEntryORM.project_id == project_id)
        if entry_type is not None:
            stmt = stmt.where(RegisterEntryORM.entry_type == entry_type)
        if status is not None:
            stmt = stmt.where(RegisterEntryORM.status == status)
        if severity is not None:
            stmt = stmt.where(RegisterEntryORM.severity == severity)
        stmt = stmt.order_by(
            RegisterEntryORM.due_date.is_(None),
            RegisterEntryORM.due_date.asc(),
            RegisterEntryORM.updated_at.desc(),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [register_entry_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyRegisterEntryRepository"]
