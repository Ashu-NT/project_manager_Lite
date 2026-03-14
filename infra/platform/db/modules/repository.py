from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.modules.repository import ModuleEntitlementRecord, ModuleEntitlementRepository
from infra.platform.db.models import ModuleEntitlementORM


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlAlchemyModuleEntitlementRepository(ModuleEntitlementRepository):
    def __init__(
        self,
        session: Session,
        *,
        organization_id_provider: Callable[[], str | None],
    ):
        self.session = session
        self._organization_id_provider = organization_id_provider

    def _current_organization_id(self) -> str | None:
        return self._organization_id_provider()

    def get_for_organization(
        self,
        organization_id: str,
        module_code: str,
    ) -> ModuleEntitlementRecord | None:
        obj = self.session.get(
            ModuleEntitlementORM,
            {
                "organization_id": organization_id,
                "module_code": module_code,
            },
        )
        if obj is None:
            return None
        return ModuleEntitlementRecord(
            module_code=obj.module_code,
            licensed=bool(obj.licensed),
            enabled=bool(obj.enabled and obj.licensed),
            lifecycle_status=str(obj.lifecycle_status or "inactive").strip().lower() or "inactive",
        )

    def list_all_for_organization(self, organization_id: str) -> list[ModuleEntitlementRecord]:
        rows = self.session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .order_by(ModuleEntitlementORM.module_code.asc())
        ).scalars().all()
        return [
            ModuleEntitlementRecord(
                module_code=row.module_code,
                licensed=bool(row.licensed),
                enabled=bool(row.enabled and row.licensed),
                lifecycle_status=str(row.lifecycle_status or "inactive").strip().lower() or "inactive",
            )
            for row in rows
        ]

    def upsert_for_organization(self, organization_id: str, record: ModuleEntitlementRecord) -> None:
        obj = self.session.get(
            ModuleEntitlementORM,
            {
                "organization_id": organization_id,
                "module_code": record.module_code,
            },
        )
        if obj is None:
            self.session.add(
                ModuleEntitlementORM(
                    organization_id=organization_id,
                    module_code=record.module_code,
                    licensed=bool(record.licensed),
                    enabled=bool(record.enabled and record.licensed),
                    lifecycle_status=str(record.lifecycle_status or "inactive").strip().lower() or "inactive",
                    updated_at=_utc_now_naive(),
                )
            )
            return
        obj.licensed = bool(record.licensed)
        obj.enabled = bool(record.enabled and record.licensed)
        obj.lifecycle_status = str(record.lifecycle_status or "inactive").strip().lower() or "inactive"
        obj.updated_at = _utc_now_naive()

    def get(self, module_code: str) -> ModuleEntitlementRecord | None:
        organization_id = self._current_organization_id()
        if not organization_id:
            return None
        return self.get_for_organization(organization_id, module_code)

    def list_all(self) -> list[ModuleEntitlementRecord]:
        organization_id = self._current_organization_id()
        if not organization_id:
            return []
        return self.list_all_for_organization(organization_id)

    def upsert(self, record: ModuleEntitlementRecord) -> None:
        organization_id = self._current_organization_id()
        if not organization_id:
            raise RuntimeError("Active organization context is required for module entitlements.")
        self.upsert_for_organization(organization_id, record)


__all__ = ["SqlAlchemyModuleEntitlementRepository"]
