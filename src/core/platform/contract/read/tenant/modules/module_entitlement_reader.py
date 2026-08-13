"""Module-entitlement read contract — CQRS pilot (audit §15-17).

Separate from ``ModuleEntitlementRepository`` (the write-side contract in
``contracts.py``): a reader answers "what is this organization entitled to"
with exactly one query, returning an immutable snapshot the caller can reuse
for every module/derived question in one logical read — instead of calling
the write repository's ``list_all()`` once per module, which is the
confirmed 15-20-query N+1 this pilot exists to close (see the audit's
"P0 correctness/security remediation status" / §7 R7a / §17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


@dataclass(frozen=True, slots=True)
class ModuleEntitlementSnapshot:
    """One organization's entire entitlement state, fetched once.

    Callers that need per-module answers (building a `ModuleEntitlement`,
    computing licensed/enabled code sets, ...) should fetch one snapshot per
    logical read and derive every answer from it in Python, not re-query per
    module."""

    organization_id: str
    records: tuple[ModuleEntitlementRecord, ...]

    def record_for(self, module_code: str) -> ModuleEntitlementRecord | None:
        canonical_code = normalize_module_code(module_code)
        for record in self.records:
            if record.module_code == canonical_code:
                return record
        return None


class ModuleEntitlementReader(Protocol):
    def get_snapshot(self, *, tenant_id: str, organization_id: str) -> ModuleEntitlementSnapshot: ...


__all__ = ["ModuleEntitlementReader", "ModuleEntitlementSnapshot"]
