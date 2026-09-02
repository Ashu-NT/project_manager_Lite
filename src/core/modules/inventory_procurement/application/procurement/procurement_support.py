from __future__ import annotations

from uuid import uuid4

from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain._validation import (
    normalize_procurement_priority as domain_normalize_procurement_priority,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseRequisition,
    PurchaseRequisitionStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.party import Party


def build_requisition_number() -> str:
    return f"INV-REQ-{uuid4().hex[:10].upper()}"


def normalize_priority(value: str | None) -> str:
    return domain_normalize_procurement_priority(value)


class ProcurementSupportMixin:
    def _require_draft_requisition(self, requisition_id: str) -> PurchaseRequisition:
        requisition = self.get_requisition(requisition_id)
        if requisition.status != PurchaseRequisitionStatus.DRAFT:
            raise ValidationError(
                "Only draft purchase requisitions can be edited.",
                code="INVENTORY_REQUISITION_EDIT_FORBIDDEN",
            )
        return requisition

    def _validate_supplier_reference(self, party_id: str | None) -> str | None:
        normalized = normalize_optional_text(party_id)
        if not normalized:
            return None
        # P29 §16: `PartyService.get_party` already scopes its own lookup to the active
        # organization (raises `NotFoundError` for a party belonging to a different one) --
        # confirmed by a real cross-org regression test
        # (`test_add_requisition_line_rejects_cross_organization_supplier`) before touching
        # anything here. P27A/P28A/P28B's "unverified"/"never validated" reading of
        # `_ensure_business_supplier_scope` examined that method in isolation, not what its sole
        # caller already guarantees one line above -- the flagged gap does not exist; no
        # additional check was needed.
        party = self._party_service.get_party(normalized)
        self._ensure_business_supplier_scope(party)
        return party.id

    @staticmethod
    def _ensure_business_supplier_scope(party: Party) -> None:
        if not party.is_active:
            raise ValidationError("Suggested supplier must be active.", code="INVENTORY_PARTY_INACTIVE")
        if party.party_type not in BUSINESS_PARTY_TYPES:
            raise ValidationError(
                "Suggested supplier must be a supplier, vendor, contractor, or service provider.",
                code="INVENTORY_PARTY_SCOPE_INVALID",
            )

    def _require_requisition_uow_factory(self):
        if self._requisition_submission_uow_factory is None:
            raise BusinessRuleError(
                "Purchase requisition commands require a configured transaction owner.",
                code="INVENTORY_REQUISITION_UOW_REQUIRED",
            )
        return self._requisition_submission_uow_factory

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="inventory procurement"
        ).organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ProcurementSupportMixin", "build_requisition_number", "normalize_priority"]
