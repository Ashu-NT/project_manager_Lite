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
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _inventory_repo(repo_factory, services):
    repo = repo_factory(services["session"])
    repo._tenant_context_service = services["tenant_context_service"]
    return repo


def _seed_inventory_scope_rows(services) -> dict[str, str]:
    organization_service = services["organization_service"]
    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="INV-TENANT-OPS",
        display_name="Inventory Tenant Operations",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )

    assert current_org is not None
    assert other_org is not None

    category_service = services["inventory_item_category_service"]
    item_service = services["inventory_item_service"]
    inventory_service = services["inventory_service"]
    stock_service = services["inventory_stock_service"]
    foundation_service = services["inventory_foundation_service"]
    site_service = services["site_service"]

    def build_rows(prefix: str) -> dict[str, str]:
        site = site_service.create_site(
            site_code=f"{prefix}-SITE",
            name=f"{prefix} Site",
            city="Berlin",
            currency_code="EUR",
        )
        category = category_service.create_category(
            category_code=f"{prefix}-CAT",
            name=f"{prefix} Category",
            category_type="SPARE",
        )
        item = item_service.create_item(
            item_code=f"{prefix}-ITEM",
            name=f"{prefix} Item",
            status="ACTIVE",
            stock_uom="EA",
            category_code=category.category_code,
        )
        storeroom = inventory_service.create_storeroom(
            storeroom_code=f"{prefix}-STORE",
            name=f"{prefix} Storeroom",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
        stock_service.post_opening_balance(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=10,
            uom="EA",
            unit_cost=5.0,
        )
        balance = stock_service.get_balance_for_stock_position(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
        )
        transactions = stock_service.list_transactions(limit=20)
        location = foundation_service.create_storage_location(
            storeroom_id=storeroom.id,
            location_code=f"{prefix}-BIN",
            name=f"{prefix} Bin",
            location_type="BIN",
        )
        policy = foundation_service.upsert_reorder_policy(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            policy_name=f"{prefix} Policy",
            min_qty=2,
            max_qty=10,
            reorder_point=4,
            reorder_qty=6,
        )
        cycle_count = foundation_service.schedule_cycle_count(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            scheduled_count_date="2026-06-01",
            notes=f"{prefix} count",
        )

        assert balance is not None
        assert transactions

        transaction = transactions[0]
        return {
            "category_id": category.id,
            "category_code": category.category_code,
            "item_id": item.id,
            "item_code": item.item_code,
            "storeroom_id": storeroom.id,
            "storeroom_code": storeroom.storeroom_code,
            "balance_id": balance.id,
            "transaction_id": transaction.id,
            "transaction_number": transaction.transaction_number,
            "location_id": location.id,
            "location_code": location.location_code,
            "policy_id": policy.id,
            "cycle_count_id": cycle_count.id,
            "cycle_count_number": cycle_count.cycle_count_number,
        }

    current_rows = build_rows("CUR")
    organization_service.set_active_organization(other_org.id)
    other_rows = build_rows("OTH")
    organization_service.set_active_organization(current_org.id)

    return {
        "current_org_id": current_org.id,
        "other_org_id": other_org.id,
        "current_category_id": current_rows["category_id"],
        "current_category_code": current_rows["category_code"],
        "current_item_id": current_rows["item_id"],
        "current_item_code": current_rows["item_code"],
        "current_storeroom_id": current_rows["storeroom_id"],
        "current_storeroom_code": current_rows["storeroom_code"],
        "current_balance_id": current_rows["balance_id"],
        "current_transaction_id": current_rows["transaction_id"],
        "current_transaction_number": current_rows["transaction_number"],
        "current_location_id": current_rows["location_id"],
        "current_location_code": current_rows["location_code"],
        "current_policy_id": current_rows["policy_id"],
        "current_cycle_count_id": current_rows["cycle_count_id"],
        "current_cycle_count_number": current_rows["cycle_count_number"],
        "other_category_id": other_rows["category_id"],
        "other_category_code": other_rows["category_code"],
        "other_item_id": other_rows["item_id"],
        "other_item_code": other_rows["item_code"],
        "other_storeroom_id": other_rows["storeroom_id"],
        "other_storeroom_code": other_rows["storeroom_code"],
        "other_balance_id": other_rows["balance_id"],
        "other_transaction_id": other_rows["transaction_id"],
        "other_transaction_number": other_rows["transaction_number"],
        "other_location_id": other_rows["location_id"],
        "other_location_code": other_rows["location_code"],
        "other_policy_id": other_rows["policy_id"],
        "other_cycle_count_id": other_rows["cycle_count_id"],
        "other_cycle_count_number": other_rows["cycle_count_number"],
    }


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (
            SqlAlchemyInventoryItemCategoryRepository,
            lambda repo: repo.get("category-1"),
        ),
        (SqlAlchemyStockItemRepository, lambda repo: repo.get("item-1")),
        (SqlAlchemyStoreroomRepository, lambda repo: repo.get("storeroom-1")),
        (SqlAlchemyStockBalanceRepository, lambda repo: repo.get("balance-1")),
        (
            SqlAlchemyStockTransactionRepository,
            lambda repo: repo.get("transaction-1"),
        ),
        (
            SqlAlchemyStockReservationRepository,
            lambda repo: repo.get("reservation-1"),
        ),
        (
            SqlAlchemyStorageLocationRepository,
            lambda repo: repo.get("location-1"),
        ),
        (SqlAlchemyReorderPolicyRepository, lambda repo: repo.get("policy-1")),
        (SqlAlchemyCycleCountRepository, lambda repo: repo.get("cycle-count-1")),
        (
            SqlAlchemyPurchaseRequisitionRepository,
            lambda repo: repo.get("requisition-1"),
        ),
        (
            SqlAlchemyPurchaseOrderRepository,
            lambda repo: repo.get("purchase-order-1"),
        ),
        (
            SqlAlchemyReceiptHeaderRepository,
            lambda repo: repo.get("receipt-1"),
        ),
    ],
)
def test_inventory_repositories_require_tenant_context_service(
    session,
    repo_factory,
    operation,
) -> None:
    repo = repo_factory(session)
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        operation(repo)


def test_inventory_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_inventory_scope_rows(services)

    category_repo = _inventory_repo(SqlAlchemyInventoryItemCategoryRepository, services)
    item_repo = _inventory_repo(SqlAlchemyStockItemRepository, services)
    storeroom_repo = _inventory_repo(SqlAlchemyStoreroomRepository, services)
    balance_repo = _inventory_repo(SqlAlchemyStockBalanceRepository, services)
    transaction_repo = _inventory_repo(SqlAlchemyStockTransactionRepository, services)
    location_repo = _inventory_repo(SqlAlchemyStorageLocationRepository, services)
    policy_repo = _inventory_repo(SqlAlchemyReorderPolicyRepository, services)
    cycle_count_repo = _inventory_repo(SqlAlchemyCycleCountRepository, services)

    assert category_repo.get(seeded["other_category_id"]) is None
    assert item_repo.get(seeded["other_item_id"]) is None
    assert storeroom_repo.get(seeded["other_storeroom_id"]) is None
    assert balance_repo.get(seeded["other_balance_id"]) is None
    assert transaction_repo.get(seeded["other_transaction_id"]) is None
    assert location_repo.get(seeded["other_location_id"]) is None
    assert policy_repo.get(seeded["other_policy_id"]) is None
    assert cycle_count_repo.get(seeded["other_cycle_count_id"]) is None

    assert category_repo.get_by_code(seeded["other_org_id"], seeded["current_category_code"]) is None
    assert item_repo.get_by_code(seeded["other_org_id"], seeded["current_item_code"]) is None
    assert storeroom_repo.get_by_code(seeded["other_org_id"], seeded["current_storeroom_code"]) is None
    assert (
        balance_repo.get_for_stock_position(
            seeded["other_org_id"],
            seeded["current_item_id"],
            seeded["current_storeroom_id"],
        )
        is None
    )
    assert transaction_repo.get_by_number(
        seeded["other_org_id"],
        seeded["current_transaction_number"],
    ) is None
    assert (
        location_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_storeroom_id"],
            seeded["current_location_code"],
        )
        is None
    )
    assert (
        policy_repo.get_for_scope(
            seeded["other_org_id"],
            seeded["current_item_id"],
            seeded["current_storeroom_id"],
            seeded["current_location_id"],
        )
        is None
    )
    assert cycle_count_repo.get_by_number(
        seeded["other_org_id"],
        seeded["current_cycle_count_number"],
    ) is None

    current_category_ids = {
        row.id
        for row in category_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_item_ids = {
        row.id
        for row in item_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_storeroom_ids = {
        row.id
        for row in storeroom_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_balance_ids = {
        row.id for row in balance_repo.list_for_organization(seeded["current_org_id"])
    }
    current_transaction_ids = {
        row.id
        for row in transaction_repo.list_for_organization(
            seeded["current_org_id"],
            limit=200,
        )
    }
    current_location_ids = {
        row.id
        for row in location_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_policy_ids = {
        row.id
        for row in policy_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_cycle_count_ids = {
        row.id
        for row in cycle_count_repo.list_for_organization(
            seeded["current_org_id"],
            limit=200,
        )
    }

    assert category_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert item_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert storeroom_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert balance_repo.list_for_organization(seeded["other_org_id"]) == []
    assert transaction_repo.list_for_organization(seeded["other_org_id"], limit=200) == []
    assert location_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert policy_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert cycle_count_repo.list_for_organization(seeded["other_org_id"], limit=200) == []

    assert seeded["current_category_id"] in current_category_ids
    assert seeded["other_category_id"] not in current_category_ids
    assert seeded["current_item_id"] in current_item_ids
    assert seeded["other_item_id"] not in current_item_ids
    assert seeded["current_storeroom_id"] in current_storeroom_ids
    assert seeded["other_storeroom_id"] not in current_storeroom_ids
    assert seeded["current_balance_id"] in current_balance_ids
    assert seeded["other_balance_id"] not in current_balance_ids
    assert seeded["current_transaction_id"] in current_transaction_ids
    assert seeded["other_transaction_id"] not in current_transaction_ids
    assert seeded["current_location_id"] in current_location_ids
    assert seeded["other_location_id"] not in current_location_ids
    assert seeded["current_policy_id"] in current_policy_ids
    assert seeded["other_policy_id"] not in current_policy_ids
    assert seeded["current_cycle_count_id"] in current_cycle_count_ids
    assert seeded["other_cycle_count_id"] not in current_cycle_count_ids
