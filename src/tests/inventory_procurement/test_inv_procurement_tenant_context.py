from __future__ import annotations

import pytest

from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.catalog import (
    SqlAlchemyInventoryItemCategoryRepository,
    SqlAlchemyStockItemRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyCycleCountRepository,
    SqlAlchemyReorderPolicyRepository,
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockReservationRepository,
    SqlAlchemyStockTransactionRepository,
    SqlAlchemyStorageLocationRepository,
    SqlAlchemyStoreroomRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (SqlAlchemyInventoryItemCategoryRepository, lambda repo: repo.get("category-1")),
        (SqlAlchemyStockItemRepository, lambda repo: repo.get("item-1")),
        (SqlAlchemyStoreroomRepository, lambda repo: repo.get("storeroom-1")),
        (SqlAlchemyStockBalanceRepository, lambda repo: repo.get("balance-1")),
        (SqlAlchemyStockTransactionRepository, lambda repo: repo.get("transaction-1")),
        (SqlAlchemyStockReservationRepository, lambda repo: repo.get("reservation-1")),
        (SqlAlchemyStorageLocationRepository, lambda repo: repo.get("location-1")),
        (SqlAlchemyReorderPolicyRepository, lambda repo: repo.get("policy-1")),
        (SqlAlchemyCycleCountRepository, lambda repo: repo.get("cycle-count-1")),
        (SqlAlchemyPurchaseRequisitionRepository, lambda repo: repo.get("requisition-1")),
        (SqlAlchemyPurchaseRequisitionLineRepository, lambda repo: repo.get("requisition-line-1")),
        (SqlAlchemyPurchaseOrderRepository, lambda repo: repo.get("purchase-order-1")),
        (SqlAlchemyPurchaseOrderLineRepository, lambda repo: repo.get("purchase-order-line-1")),
        (SqlAlchemyReceiptHeaderRepository, lambda repo: repo.get("receipt-1")),
        (SqlAlchemyReceiptLineRepository, lambda repo: repo.get("receipt-line-1")),
    ],
)
def test_inventory_repositories_require_tenant_context_service(
    session,
    repo_factory,
    operation,
) -> None:
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        repo_factory(session)
