from __future__ import annotations

from core.modules.inventory_procurement.domain import PurchaseRequisition, PurchaseRequisitionLine
from core.modules.inventory_procurement.support import normalize_optional_text
from core.platform.common.exceptions import NotFoundError


class ProcurementQueryMixin:
    def list_requisitions(
        self,
        *,
        status: str | None = None,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseRequisition]:
        self._require_read("list purchase requisitions")
        organization = self._active_organization()
        return self._requisition_repo.list_for_organization(
            organization.id,
            status=normalize_optional_text(status).upper() or None,
            site_id=normalize_optional_text(site_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def get_requisition(self, requisition_id: str) -> PurchaseRequisition:
        self._require_read("view purchase requisition")
        organization = self._active_organization()
        requisition = self._requisition_repo.get(requisition_id)
        if requisition is None or requisition.organization_id != organization.id:
            raise NotFoundError(
                "Purchase requisition not found in the active organization.",
                code="INVENTORY_REQUISITION_NOT_FOUND",
            )
        return requisition

    def find_requisition_by_number(self, requisition_number: str) -> PurchaseRequisition | None:
        self._require_read("resolve purchase requisition")
        organization = self._active_organization()
        normalized_number = normalize_optional_text(requisition_number)
        if not normalized_number:
            return None
        return self._requisition_repo.get_by_number(organization.id, normalized_number)

    def list_requisition_lines(self, requisition_id: str) -> list[PurchaseRequisitionLine]:
        requisition = self.get_requisition(requisition_id)
        return self._requisition_line_repo.list_for_requisition(requisition.id)


__all__ = ["ProcurementQueryMixin"]
