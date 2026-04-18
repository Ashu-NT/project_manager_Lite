from __future__ import annotations

from uuid import uuid4

from core.modules.inventory_procurement.domain import PurchaseRequisition, PurchaseRequisitionStatus
from core.modules.inventory_procurement.support import BUSINESS_PARTY_TYPES, normalize_optional_text
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.org.domain import Organization
from src.core.platform.party.domain import Party


def build_requisition_number() -> str:
    return f"INV-REQ-{uuid4().hex[:10].upper()}"


def normalize_priority(value: str | None) -> str:
    normalized = normalize_optional_text(value).upper()
    return normalized or "NORMAL"


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

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ProcurementSupportMixin", "build_requisition_number", "normalize_priority"]
