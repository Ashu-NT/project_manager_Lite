from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryStoreroomCreateCommand,
    InventoryStoreroomUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_text,
    require_text,
)


def suggest_storeroom_code(desktop_api, payload: dict[str, Any]) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {
        str(getattr(row, "storeroom_code", "") or "").upper()
        for row in desktop_api.list_storerooms(active_only=None)
    }
    name = str(payload.get("name") or "").strip()
    return CodeGenerator().generate(
        "storeroom",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )


def create_storeroom(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryStoreroomCreateCommand(
        storeroom_code=require_text(payload, "storeroomCode", "Storeroom code is required."),
        name=require_text(payload, "name", "Storeroom name is required."),
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        description=optional_text(payload, "description") or "",
        status=require_text(payload, "status", "Choose a storeroom status before saving."),
        storeroom_type=optional_text(payload, "storeroomType") or "",
        is_internal_supplier=optional_bool(payload, "isInternalSupplier", default=False),
        allows_issue=optional_bool(payload, "allowsIssue", default=True),
        allows_transfer=optional_bool(payload, "allowsTransfer", default=True),
        allows_receiving=optional_bool(payload, "allowsReceiving", default=True),
        requires_reservation_for_issue=optional_bool(
            payload, "requiresReservationForIssue", default=False
        ),
        requires_supplier_reference_for_receipt=optional_bool(
            payload, "requiresSupplierReferenceForReceipt", default=False
        ),
        default_currency_code=optional_text(payload, "defaultCurrencyCode"),
        manager_party_id=optional_text(payload, "managerPartyId"),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_storeroom(command)


def update_storeroom(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryStoreroomUpdateCommand(
        storeroom_id=require_text(
            payload, "storeroomId", "Storeroom ID is required for updates."
        ),
        storeroom_code=require_text(payload, "storeroomCode", "Storeroom code is required."),
        name=require_text(payload, "name", "Storeroom name is required."),
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        description=optional_text(payload, "description") or "",
        status=require_text(payload, "status", "Choose a storeroom status before saving."),
        storeroom_type=optional_text(payload, "storeroomType") or "",
        is_internal_supplier=optional_bool(payload, "isInternalSupplier", default=False),
        allows_issue=optional_bool(payload, "allowsIssue", default=True),
        allows_transfer=optional_bool(payload, "allowsTransfer", default=True),
        allows_receiving=optional_bool(payload, "allowsReceiving", default=True),
        requires_reservation_for_issue=optional_bool(
            payload, "requiresReservationForIssue", default=False
        ),
        requires_supplier_reference_for_receipt=optional_bool(
            payload, "requiresSupplierReferenceForReceipt", default=False
        ),
        default_currency_code=optional_text(payload, "defaultCurrencyCode"),
        manager_party_id=optional_text(payload, "managerPartyId"),
        notes=optional_text(payload, "notes") or "",
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_storeroom(command)


def toggle_storeroom_active(
    desktop_api,
    storeroom_id: str,
    expected_version: int | None = None,
) -> None:
    normalized_id = (storeroom_id or "").strip()
    if not normalized_id:
        raise ValueError("Storeroom ID is required to change active state.")
    desktop_api.toggle_storeroom_active(normalized_id, expected_version=expected_version)
