from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.modules import (
    ModuleEntitlementRecord,
    ModuleEntitlementRepository,
    module_storage_codes,
    normalize_module_code,
)
from src.core.platform.infrastructure.persistence.orm.models import ModuleEntitlementORM


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

    def _preferred_record(self, rows: list[ModuleEntitlementORM], canonical_code: str) -> ModuleEntitlementORM | None:
        if not rows:
            return None
        for row in rows:
            if row.module_code == canonical_code:
                return row
        return rows[0]

    def _to_record(self, row: ModuleEntitlementORM, canonical_code: str) -> ModuleEntitlementRecord:
        return ModuleEntitlementRecord(
            module_code=canonical_code,
            licensed=bool(row.licensed),
            enabled=bool(row.enabled and row.licensed),
            lifecycle_status=str(row.lifecycle_status or "inactive").strip().lower() or "inactive",
        )

    def _list_rows_for_codes(
        self,
        organization_id: str,
        module_code: str,
    ) -> list[ModuleEntitlementORM]:
        candidate_codes = module_storage_codes(module_code)
        return self.session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .where(ModuleEntitlementORM.module_code.in_(candidate_codes))
            .order_by(ModuleEntitlementORM.module_code.asc())
        ).scalars().all()

    def get_for_organization(
        self,
        organization_id: str,
        module_code: str,
    ) -> ModuleEntitlementRecord | None:
        canonical_code = normalize_module_code(module_code)
        rows = self._list_rows_for_codes(organization_id, canonical_code)
        obj = self._preferred_record(rows, canonical_code)
        if obj is None:
            return None
        return self._to_record(obj, canonical_code)

    def list_all_for_organization(self, organization_id: str) -> list[ModuleEntitlementRecord]:
        rows = self.session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .order_by(ModuleEntitlementORM.module_code.asc())
        ).scalars().all()
        records_by_code: dict[str, ModuleEntitlementRecord] = {}
        for row in rows:
            canonical_code = normalize_module_code(row.module_code)
            existing = records_by_code.get(canonical_code)
            if existing is not None and row.module_code != canonical_code:
                continue
            records_by_code[canonical_code] = self._to_record(row, canonical_code)
        return [records_by_code[code] for code in sorted(records_by_code)]

    def upsert_for_organization(self, organization_id: str, record: ModuleEntitlementRecord) -> None:
        canonical_code = normalize_module_code(record.module_code)
        rows = self._list_rows_for_codes(organization_id, canonical_code)
        obj = self._preferred_record(rows, canonical_code)
        extra_rows = [row for row in rows if row is not obj]
        for extra_row in extra_rows:
            self.session.delete(extra_row)
        if obj is None:
            self.session.add(
                ModuleEntitlementORM(
                    organization_id=organization_id,
                    module_code=canonical_code,
                    licensed=bool(record.licensed),
                    enabled=bool(record.enabled and record.licensed),
                    lifecycle_status=str(record.lifecycle_status or "inactive").strip().lower() or "inactive",
                    updated_at=_utc_now_naive(),
                )
            )
            return
        obj.module_code = canonical_code
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
