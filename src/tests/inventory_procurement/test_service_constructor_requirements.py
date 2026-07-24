from __future__ import annotations

import inspect

import pytest

from src.core.modules.inventory_procurement.application.catalog.category_service import (
    ItemCategoryService,
)
from src.core.modules.inventory_procurement.application.catalog.service import (
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.inventory.foundation_service import (
    InventoryFoundationService,
)
from src.core.modules.inventory_procurement.application.inventory.reservation_service import (
    ReservationService,
)
from src.core.modules.inventory_procurement.application.inventory.service import (
    InventoryService,
)
from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_service import (
    PurchasingService,
)
from src.core.modules.inventory_procurement.application.procurement.service import (
    ProcurementService,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _construct_without_tenant_context(cls):
    signature = inspect.signature(cls.__init__)
    positional_args = []
    keyword_args = {}
    for name, parameter in list(signature.parameters.items())[1:]:
        if name == "tenant_context_service":
            keyword_args[name] = None
            continue
        if parameter.default is not inspect._empty:
            continue
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_args.append(object())
            continue
        if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
            keyword_args[name] = object()
            continue
        raise AssertionError(f"Unsupported constructor parameter shape: {cls.__name__}.{name}")
    return cls(*positional_args, **keyword_args)


@pytest.mark.parametrize(
    "service_cls",
    [
        ItemCategoryService,
        ItemMasterService,
        InventoryFoundationService,
        ReservationService,
        InventoryService,
        StockControlService,
        PurchasingService,
        ProcurementService,
    ],
)
def test_inventory_services_require_tenant_context_service(service_cls) -> None:
    with pytest.raises(
        BusinessRuleError,
        match=rf"{service_cls.__name__} requires TenantContextService",
    ):
        _construct_without_tenant_context(service_cls)
