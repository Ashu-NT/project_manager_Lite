from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.modules.repository import ModuleEntitlementRecord, ModuleEntitlementRepository
from infra.platform.db.models import ModuleEntitlementORM


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlAlchemyModuleEntitlementRepository(ModuleEntitlementRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, module_code: str) -> ModuleEntitlementRecord | None:
        obj = self.session.get(ModuleEntitlementORM, module_code)
        if obj is None:
            return None
        return ModuleEntitlementRecord(
            module_code=obj.module_code,
            licensed=bool(obj.licensed),
            enabled=bool(obj.enabled and obj.licensed),
        )

    def list_all(self) -> list[ModuleEntitlementRecord]:
        rows = self.session.execute(
            select(ModuleEntitlementORM).order_by(ModuleEntitlementORM.module_code.asc())
        ).scalars().all()
        return [
            ModuleEntitlementRecord(
                module_code=row.module_code,
                licensed=bool(row.licensed),
                enabled=bool(row.enabled and row.licensed),
            )
            for row in rows
        ]

    def upsert(self, record: ModuleEntitlementRecord) -> None:
        obj = self.session.get(ModuleEntitlementORM, record.module_code)
        if obj is None:
            self.session.add(
                ModuleEntitlementORM(
                    module_code=record.module_code,
                    licensed=bool(record.licensed),
                    enabled=bool(record.enabled and record.licensed),
                    updated_at=_utc_now_naive(),
                )
            )
            return
        obj.licensed = bool(record.licensed)
        obj.enabled = bool(record.enabled and record.licensed)
        obj.updated_at = _utc_now_naive()


__all__ = ["SqlAlchemyModuleEntitlementRepository"]
