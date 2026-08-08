from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.tenant.modules import (
    ModuleEntitlementRecord,
    module_storage_codes,
    normalize_module_code,
)
from src.core.platform.contract.tenant.modules.contracts import ModuleEntitlementRepository
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import ModuleEntitlementORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlAlchemyModuleEntitlementRepository(
    TenantScopedRepositorySupport,
    ModuleEntitlementRepository,
):
    _repository_label = "ModuleEntitlementRepository"
    session: Session

    def __init__(
        self,
        session: Session,
        *,
        tenant_context_service: TenantContextService,
    ) -> None:
        self.session = session
        self._tenant_context_service = tenant_context_service

    def _preferred_record(
        self, rows: list[ModuleEntitlementORM], canonical_code: str
    ) -> ModuleEntitlementORM | None:
        if not rows:
            return None
        for row in rows:
            if row.module_code == canonical_code:
                return row
        return rows[0]

    def _to_record(self, row: ModuleEntitlementORM, canonical_code: str) -> ModuleEntitlementRecord:
        return ModuleEntitlementRecord(
            module_code=row.module_code,
            licensed=bool(row.licensed),
            enabled=bool(row.enabled and row.licensed),
            lifecycle_status=row.lifecycle_status,
        )

    def _list_rows_for_codes(
        self,
        organization_id: str,
        module_code: str,
    ) -> list[ModuleEntitlementORM]:
        tenant_id = self._require_organization_scope(
            organization_id,
            operation_label="view organization module entitlement",
        )
        candidate_codes = module_storage_codes(module_code)
        return self.session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .where(ModuleEntitlementORM.tenant_id == tenant_id)
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
        tenant_id = self._require_organization_scope(
            organization_id,
            operation_label="list organization module entitlements",
        )
        rows = self.session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .where(ModuleEntitlementORM.tenant_id == tenant_id)
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

    def upsert_for_organization(
        self,
        organization_id: str,
        record: ModuleEntitlementRecord,
    ) -> None:
        tenant_id = self._require_organization_scope(
            organization_id,
            operation_label="update organization module entitlement",
        )
        canonical_code = record.module_code
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
                    tenant_id=tenant_id,
                    licensed=bool(record.licensed),
                    enabled=bool(record.enabled and record.licensed),
                    lifecycle_status=record.lifecycle_status,
                    updated_at=_utc_now_naive(),
                )
            )
            return
        obj.tenant_id = tenant_id
        obj.module_code = canonical_code
        obj.licensed = bool(record.licensed)
        obj.enabled = bool(record.enabled and record.licensed)
        obj.lifecycle_status = record.lifecycle_status
        obj.updated_at = _utc_now_naive()

    def get(self, module_code: str) -> ModuleEntitlementRecord | None:
        ctx = self._context(operation_label="view module entitlement")
        return self.get_for_organization(ctx.organization_id, module_code)

    def list_all(self) -> list[ModuleEntitlementRecord]:
        ctx = self._context(operation_label="list module entitlements")
        return self.list_all_for_organization(ctx.organization_id)

    def upsert(self, record: ModuleEntitlementRecord) -> None:
        ctx = self._context(operation_label="update module entitlement")
        self.upsert_for_organization(ctx.organization_id, record)

    def _require_organization_scope(
        self,
        organization_id: str,
        *,
        operation_label: str,
    ) -> str:
        ctx = self._context(operation_label=operation_label)
        normalized_id = str(organization_id or "").strip()
        if normalized_id != ctx.organization_id:
            raise NotFoundError(
                "Organization not found in the active tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        return ctx.tenant_id


__all__ = ["SqlAlchemyModuleEntitlementRepository"]
