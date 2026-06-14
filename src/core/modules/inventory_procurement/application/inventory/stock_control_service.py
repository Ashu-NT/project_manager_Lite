from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.inventory.service import InventoryService
from src.core.modules.inventory_procurement.application.inventory.stock_control_adjustments import (
    StockControlAdjustmentMixin,
)
from src.core.modules.inventory_procurement.application.inventory.stock_control_movements import (
    StockControlMovementMixin,
)
from src.core.modules.inventory_procurement.application.inventory.stock_control_queries import (
    StockControlQueryMixin,
)
from src.core.modules.inventory_procurement.application.inventory.stock_control_support import (
    StockControlSupportMixin,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockBalanceRepository,
    StockTransactionRepository,
)
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)


class StockControlService(
    StockControlSupportMixin,
    StockControlQueryMixin,
    StockControlAdjustmentMixin,
    StockControlMovementMixin,
):
    """Inventory stock control service composed from focused mixins."""

    def __init__(
        self,
        session: Session,
        balance_repo: StockBalanceRepository,
        transaction_repo: StockTransactionRepository,
        *,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ):
        self._session = session
        self._balance_repo = balance_repo
        self._transaction_repo = transaction_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="StockControlService",
        )
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._user_session = user_session
        self._activity_service = activity_service


__all__ = ["StockControlService"]
