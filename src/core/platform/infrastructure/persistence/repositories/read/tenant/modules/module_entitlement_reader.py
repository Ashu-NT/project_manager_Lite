"""Concrete, tenant-scoped single-query read for module entitlements.

One dedicated read-side adapter — not the write repository's ``list_all()``
called once per module. ``ModuleCatalogService`` depends on
``ModuleEntitlementReader`` (``contract/tenant/modules/read/
module_entitlement_reader.py``), never on this concrete class directly.
Takes ``tenant_id``/``organization_id`` explicitly rather than resolving
them from ambient session state, mirroring PM's ``SqlAlchemyRateResolutionReader``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.contract.tenant.modules.read.module_entitlement_reader import (
    ModuleEntitlementSnapshot,
)
from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import ModuleEntitlementORM


class SqlAlchemyModuleEntitlementReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_snapshot(self, *, tenant_id: str, organization_id: str) -> ModuleEntitlementSnapshot:
        rows = self._session.execute(
            select(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.organization_id == organization_id)
            .where(ModuleEntitlementORM.tenant_id == tenant_id)
            .order_by(ModuleEntitlementORM.module_code.asc())
        ).scalars().all()

        # A legacy-aliased code (module_storage_codes) and its canonical
        # counterpart can both be present as separate rows -- keep exactly
        # one record per canonical code, same precedence rule as the write
        # repository's _preferred_record (prefer the row already stored
        # under the canonical code).
        records_by_code: dict[str, ModuleEntitlementRecord] = {}
        for row in rows:
            canonical_code = normalize_module_code(row.module_code)
            existing = records_by_code.get(canonical_code)
            if existing is not None and row.module_code != canonical_code:
                continue
            records_by_code[canonical_code] = ModuleEntitlementRecord(
                module_code=canonical_code,
                licensed=bool(row.licensed),
                enabled=bool(row.enabled and row.licensed),
                lifecycle_status=row.lifecycle_status,
            )

        records = tuple(records_by_code[code] for code in sorted(records_by_code))
        return ModuleEntitlementSnapshot(organization_id=organization_id, records=records)


__all__ = ["SqlAlchemyModuleEntitlementReader"]
